"""R4-02 deadline tests over a real loopback socket.

The product path under test is the real Feishu HTTP adapter with a real
``httpx.Client`` with the product DeadlineTransport; only the remote is synthetic.
These tests assert both the wall-clock deadline and that the transfer has truly
stopped when the call returns.
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.feishu.provider import FeishuConfig, FeishuError
from summit_everything.integrations.http_boundary import bounded_call, live_transfer_workers
from summit_everything.integrations.transport import DeadlineTransport

# Fixed scheduling tolerance: a deadline case may overrun by at most this much.
TOLERANCE_SECONDS = 0.10
# Window used to confirm nothing continues after the call returns.
QUIET_WINDOW_SECONDS = 0.30


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        cfg = self.server.cfg  # type: ignore[attr-defined]
        cfg["requests"] += 1
        cfg["sockets"].append(self.connection)
        try:
            if cfg["mode"] == "incomplete_headers":
                self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                self.wfile.flush()
                self._trickle(cfg, b"X")
                return
            time.sleep(cfg["header_delay"])
            if cfg["redirect"]:
                self.send_response(302)
                self.send_header("Location", cfg["redirect_to"])
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = cfg["body"]
            declared = cfg["declared_length"]
            if declared is None:
                declared = len(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(declared))
            self.end_headers()
            if cfg["mode"] == "trickle_body":
                self._trickle(cfg, b"x")
                return
            pieces = _pieces(body, cfg["chunks"])
            for index, piece in enumerate(pieces):
                if index == 0:
                    time.sleep(cfg["body_delay"])
                elif index == len(pieces) - 1:
                    time.sleep(cfg["stall"])
                else:
                    time.sleep(cfg["chunk_delay"])
                self.wfile.write(piece)
                self.wfile.flush()
                cfg["sent"] += len(piece)
        except (BrokenPipeError, ConnectionResetError, OSError):
            cfg["aborted"] = True

    do_POST = do_GET

    def _trickle(self, cfg: dict, chunk: bytes) -> None:
        """Keep sending small chunks; only the connection break can stop it."""
        for _ in range(cfg["trickle_count"]):
            time.sleep(cfg["trickle_interval"])
            self.wfile.write(chunk)
            self.wfile.flush()
            cfg["sent"] += len(chunk)
        cfg["completed"] = True


def _pieces(body: bytes, chunks: int) -> list[bytes]:
    size = max(1, len(body) // max(1, chunks))
    return [body[i : i + size] for i in range(0, len(body), size)] or [b""]


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # noqa: ANN001
        exc = __import__("sys").exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, OSError)):
            return
        super().handle_error(request, client_address)


class LoopbackServer:
    def __init__(self, **cfg: object) -> None:
        defaults: dict[str, object] = {
            "mode": "normal",
            "header_delay": 0.0,
            "body_delay": 0.0,
            "body": b"{}",
            "chunks": 1,
            "chunk_delay": 0.0,
            "stall": 0.0,
            "redirect": False,
            "redirect_to": "http://127.0.0.1:1/elsewhere",
            "trickle_interval": 0.04,
            "trickle_count": 200,
            "declared_length": None,
            "requests": 0,
            "sent": 0,
            "aborted": False,
            "completed": False,
            "sockets": [],
        }
        defaults.update(cfg)
        self.cfg = defaults
        self.server = _Server(("127.0.0.1", 0), _Handler)
        self.server.cfg = self.cfg  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/synthetic"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)


@pytest.fixture
def loopback():
    servers: list[LoopbackServer] = []

    def make(**cfg: object) -> LoopbackServer:
        server = LoopbackServer(**cfg)
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.stop()


def _client() -> httpx.Client:
    return httpx.Client(
        transport=DeadlineTransport(), trust_env=False, follow_redirects=True, timeout=None
    )


def _assert_peer_closed(server: LoopbackServer) -> None:
    """The client side of the connection must terminate shortly after return.

    A FIN or reset can lag the product call by a few milliseconds, so the check
    polls within a bounded window; it never treats "no data readable yet" as
    terminated, and it fails if the connection is still open at the end.
    """
    wait_deadline = time.monotonic() + 1.0
    while not server.cfg["sockets"] and time.monotonic() < wait_deadline:
        time.sleep(0.01)
    sockets = list(server.cfg["sockets"])
    assert sockets, "the synthetic server never accepted a connection"
    for sock in sockets:
        sock.setblocking(False)
        terminated = False
        while time.monotonic() < wait_deadline:
            try:
                data = sock.recv(1)
            except (ConnectionResetError, BrokenPipeError):
                terminated = True
                break
            except BlockingIOError:
                time.sleep(0.02)
                continue
            except OSError:
                terminated = True
                break
            if data == b"":
                terminated = True
                break
            # Unexpected trailing bytes: keep draining within the window.
            time.sleep(0.02)
        assert terminated, "the connection was still open when the call returned"


def _assert_cancelled(
    server: LoopbackServer, client: httpx.Client, *, expect_no_further_traffic: bool = False
) -> None:
    """The transfer must be over when the product call returned."""
    assert live_transfer_workers() == 0, "a transfer worker outlived the call"
    _assert_peer_closed(server)
    if expect_no_further_traffic:
        # A single buffered write can still land after the peer closes; the
        # proof of cancellation is that the traffic settles and the endless
        # trickle loop was cut short instead of running to completion.
        time.sleep(QUIET_WINDOW_SECONDS)
        settled = server.cfg["sent"]
        time.sleep(QUIET_WINDOW_SECONDS)
        assert server.cfg["sent"] == settled, (
            f"the server kept sending after the call returned: {settled} -> {server.cfg['sent']}"
        )
        assert server.cfg["completed"] is False, "the trickle loop ran to completion"
    assert server.cfg["requests"] == 1, server.cfg["requests"]


def _deadline_case(
    loopback,
    client: httpx.Client,
    deadline: float,
    *,
    expect_no_further_traffic: bool = True,
    **cfg: object,
):
    server = loopback(**cfg)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        bounded_call(client, "GET", server.url, headers={}, deadline_seconds=deadline)
    elapsed = time.monotonic() - started
    _assert_cancelled(server, client, expect_no_further_traffic=expect_no_further_traffic)
    return elapsed


# --- R4-02: the overall deadline must cancel the transfer --------------------


def test_r4_02_a_trickling_incomplete_headers_are_cancelled(loopback):
    client = _client()
    try:
        elapsed = _deadline_case(loopback, client, 0.15, mode="incomplete_headers")
    finally:
        client.close()
    assert elapsed <= 0.15 + TOLERANCE_SECONDS, elapsed


def test_r4_02_b_slow_response_headers_are_cancelled(loopback):
    client = _client()
    try:
        elapsed = _deadline_case(
            loopback,
            client,
            0.15,
            expect_no_further_traffic=False,
            header_delay=0.5,
            body=b"{}",
        )
    finally:
        client.close()
    assert elapsed <= 0.15 + TOLERANCE_SECONDS, elapsed


def test_r4_02_c_body_wait_after_late_headers_is_cancelled(loopback):
    client = _client()
    try:
        elapsed = _deadline_case(
            loopback,
            client,
            0.3,
            expect_no_further_traffic=False,
            header_delay=0.22,
            body=b"{}",
            body_delay=0.25,
        )
    finally:
        client.close()
    assert elapsed <= 0.3 + TOLERANCE_SECONDS, elapsed


def test_r4_02_d_trickling_body_is_cancelled_without_a_single_read_timeout(loopback):
    client = _client()
    try:
        elapsed = _deadline_case(
            loopback,
            client,
            0.3,
            mode="trickle_body",
            trickle_interval=0.04,
            trickle_count=200,
            declared_length=100_000,
        )
    finally:
        client.close()
    assert elapsed <= 0.3 + TOLERANCE_SECONDS, elapsed


def test_r4_02_e_empty_body_before_and_after_the_deadline(loopback):
    fast = loopback(body=b"", header_delay=0.02)
    client = _client()
    try:
        status, body = bounded_call(client, "GET", fast.url, headers={}, deadline_seconds=1.0)
        assert status == 200 and body == b""
        elapsed = _deadline_case(
            loopback,
            client,
            0.12,
            expect_no_further_traffic=False,
            header_delay=0.4,
            body=b"",
        )
    finally:
        client.close()
    assert elapsed <= 0.12 + TOLERANCE_SECONDS, elapsed


def test_r4_02_f_normal_oversize_redirect_error_and_next_request(loopback):
    normal = loopback(body=b'{"code":0}')
    target = loopback(body=b"{}")
    redirect = loopback(redirect=True, redirect_to=f"http://127.0.0.1:{target.port}/elsewhere")
    large = loopback(body=b"x" * 5000)
    client = _client()
    try:
        assert bounded_call(client, "GET", normal.url, headers={}, deadline_seconds=1.0) == (
            200,
            b'{"code":0}',
        )
        with pytest.raises(ValueError, match="size limit"):
            bounded_call(
                client, "GET", large.url, headers={}, max_response_bytes=1000, deadline_seconds=1.0
            )
        assert bounded_call(client, "GET", redirect.url, headers={}, deadline_seconds=1.0)[0] == 302
        assert target.cfg["requests"] == 0
        with pytest.raises(ValueError):
            bounded_call(
                client,
                "GET",
                "http://127.0.0.1:1/closed",
                headers={},
                deadline_seconds=1.0,
            )
        # A deadline timeout must not poison the client for later requests.
        slow = loopback(header_delay=0.4, body=b"{}")
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            bounded_call(client, "GET", slow.url, headers={}, deadline_seconds=0.1)
        assert time.monotonic() - started <= 0.1 + TOLERANCE_SECONDS
        again = loopback(body=b"ok")
        assert bounded_call(client, "GET", again.url, headers={}, deadline_seconds=1.0) == (
            200,
            b"ok",
        )
    finally:
        client.close()


@pytest.mark.parametrize(
    "deadline,cfg,expect_no_further_traffic",
    [
        (0.15, {"mode": "incomplete_headers"}, True),
        (0.15, {"header_delay": 0.5, "body": b"{}"}, False),
        (0.3, {"mode": "trickle_body", "declared_length": 100_000}, True),
    ],
)
def test_r4_02_deadline_cases_hold_over_ten_consecutive_runs(
    loopback, deadline, cfg, expect_no_further_traffic
):
    client = _client()
    timings: list[float] = []
    try:
        for _ in range(10):
            timings.append(
                _deadline_case(
                    loopback,
                    client,
                    deadline,
                    expect_no_further_traffic=expect_no_further_traffic,
                    **cfg,
                )
            )
    finally:
        client.close()
    worst = max(timings)
    print(
        f"R4-02 timings deadline={deadline} cfg={cfg} "
        f"tolerance={TOLERANCE_SECONDS} worst={worst:.4f} "
        f"values={[round(value, 4) for value in timings]}"
    )
    assert all(value <= deadline + TOLERANCE_SECONDS for value in timings), timings
    assert worst <= deadline + TOLERANCE_SECONDS, (deadline, worst, timings)


# --- the same guarantee through the real adapter -----------------------------


def test_r4_02_adapter_deadline_cancels_a_trickling_header_response(loopback, monkeypatch):
    """The real FeishuHttpProvider must also stop a trickling header wait."""
    from pydantic import SecretStr

    import summit_everything.integrations.feishu.http as feishu_http
    from summit_everything.integrations.feishu.provider import AppCredentials

    server = loopback(mode="incomplete_headers")
    client = _client()
    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id="cli_synthetic_r4_app"),
        lambda: AppCredentials(
            app_id="cli_synthetic_r4_app", app_secret=SecretStr("synthetic-secret")
        ),
        client=client,
        open_api_base=f"http://127.0.0.1:{server.port}",
        max_response_bytes=100_000,
    )
    original = feishu_http.bounded_json_call

    def small_deadline(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("deadline_seconds", 0.15)
        return original(*args, **kwargs)

    monkeypatch.setattr(feishu_http, "bounded_json_call", small_deadline)
    started = time.monotonic()
    with pytest.raises(FeishuError):
        provider._application_token()
    elapsed = time.monotonic() - started
    client.close()
    assert elapsed <= 0.15 + TOLERANCE_SECONDS, elapsed
    _assert_cancelled(server, client, expect_no_further_traffic=True)
