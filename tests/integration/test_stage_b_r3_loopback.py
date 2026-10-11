"""R3-05 deadline tests over a real loopback socket.

MockTransport and a fake clock cannot prove that the transfer is really
cancelled, so these tests run a local HTTP server on 127.0.0.1 and a real
``httpx.Client`` with ``trust_env=False`` (no local proxy). Only synthetic data
is served. Each test stops its own server.
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from summit_everything.integrations.http_boundary import bounded_call
from summit_everything.integrations.transport import DeadlineTransport


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:  # silence test output
        pass

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        cfg = self.server.cfg  # type: ignore[attr-defined]
        cfg["requests"] += 1
        time.sleep(cfg["header_delay"])
        if cfg["redirect"]:
            self.send_response(302)
            self.send_header("Location", cfg["redirect_to"])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = cfg["body"]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        size = max(1, len(body) // cfg["chunks"])
        pieces = [body[i : i + size] for i in range(0, len(body), size)] or [b""]
        try:
            for index, piece in enumerate(pieces):
                if index == 0:
                    time.sleep(cfg["body_delay"])
                elif index == len(pieces) - 1:
                    # Hold the final bytes back so the client waits mid-body.
                    time.sleep(cfg["stall"])
                else:
                    time.sleep(cfg["chunk_delay"])
                self.wfile.write(piece)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            cfg["aborted"] = True


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # noqa: ANN001
        # A client that aborts on its deadline resets the connection; that is the
        # expected outcome of these tests and not a server error.
        import sys

        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class LoopbackServer:
    """A local HTTP server with controllable header and body timing."""

    def __init__(self, **cfg: object) -> None:
        defaults = {
            "header_delay": 0.0,
            "body_delay": 0.0,
            "body": b"{}",
            "chunks": 1,
            "chunk_delay": 0.0,
            "stall": 0.0,
            "redirect": False,
            "redirect_to": "http://127.0.0.1:1/elsewhere",
            "requests": 0,
            "aborted": False,
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
    # trust_env=False keeps the request off any locally configured proxy.
    return httpx.Client(
        transport=DeadlineTransport(), trust_env=False, follow_redirects=True, timeout=None
    )


def test_r3_05_slow_response_headers_respect_the_overall_deadline(loopback):
    server = loopback(header_delay=0.5, body=b"{}")
    client = _client()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            bounded_call(
                client,
                "GET",
                server.url,
                headers={},
                deadline_seconds=0.2,
            )
        elapsed = time.monotonic() - started
    finally:
        client.close()
    assert elapsed < 0.35, elapsed
    assert server.cfg["requests"] == 1, server.cfg["requests"]


def test_r3_05_body_wait_after_late_headers_does_not_get_a_fresh_budget(loopback):
    """Headers at ~220 ms, body pause 250 ms, deadline 300 ms.

    The old implementation clamped the phase timeout once at request start, so
    this finished at roughly 470 ms. The operation must now end near the
    deadline, and the tolerance must not admit the old behaviour.
    """
    server = loopback(header_delay=0.22, body=b"{}", body_delay=0.25)
    client = _client()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            bounded_call(
                client,
                "GET",
                server.url,
                headers={},
                deadline_seconds=0.3,
            )
        elapsed = time.monotonic() - started
    finally:
        client.close()
    assert elapsed < 0.45, elapsed
    assert elapsed < 0.47, elapsed  # the measured old behaviour


def test_r3_05_trickle_then_stall_crosses_the_deadline(loopback):
    server = loopback(header_delay=0.02, body=b"xxxxxxxx", chunks=4, chunk_delay=0.02, stall=0.6)
    client = _client()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            bounded_call(
                client,
                "GET",
                server.url,
                headers={},
                deadline_seconds=0.25,
                max_response_bytes=10_000,
            )
        elapsed = time.monotonic() - started
    finally:
        client.close()
    assert elapsed < 0.4, elapsed


def test_r3_05_normal_response_and_empty_body_are_accepted(loopback):
    server = loopback(header_delay=0.01, body=b'{"code":0}', chunks=1)
    client = _client()
    try:
        status, body = bounded_call(
            client,
            "GET",
            server.url,
            headers={},
            deadline_seconds=5.0,
        )
        assert status == 200 and body == b'{"code":0}'
    finally:
        client.close()


def test_r3_05_oversized_response_is_rejected_not_sliced(loopback):
    server = loopback(body=b"x" * 5000)
    client = _client()
    try:
        with pytest.raises(ValueError, match="size limit"):
            bounded_call(
                client,
                "GET",
                server.url,
                headers={},
                max_response_bytes=1000,
                deadline_seconds=5.0,
            )
    finally:
        client.close()


def test_r3_05_redirect_is_not_followed_even_with_a_redirecting_client(loopback):
    target = loopback(body=b"{}")
    server = loopback(redirect=True, redirect_to=f"http://127.0.0.1:{target.port}/elsewhere")
    client = _client()  # follow_redirects=True on the client
    try:
        status, body = bounded_call(
            client,
            "GET",
            server.url,
            headers={},
            deadline_seconds=5.0,
        )
        assert status == 302 and body == b""
    finally:
        client.close()
    assert server.cfg["requests"] == 1
    assert target.cfg["requests"] == 0, "the redirect target must not be contacted"


def test_r3_05_no_request_continues_after_the_deadline(loopback):
    """After the timeout the connection is aborted and nothing retries."""
    server = loopback(header_delay=0.4, body=b"{}")
    client = _client()
    try:
        with pytest.raises(TimeoutError):
            bounded_call(client, "GET", server.url, headers={}, deadline_seconds=0.15)
        time.sleep(0.5)
    finally:
        client.close()
    assert server.cfg["requests"] == 1, server.cfg["requests"]
