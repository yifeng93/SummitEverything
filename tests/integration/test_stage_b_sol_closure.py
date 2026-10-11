"""Sol closure regressions: isolated cancellation and atomic lease admission."""

from __future__ import annotations

import asyncio
import inspect
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aiodns
import httpx
import pytest
from pydantic import SecretStr

from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.feishu.provider import AppCredentials, FeishuConfig
from summit_everything.integrations.http_boundary import bounded_call, live_transfer_workers
from summit_everything.integrations.transport import DeadlineTransport


@pytest.fixture
def remote():
    entered = threading.Event()
    received = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):  # noqa: N802
            received.set()
            try:
                if self.path == "/trickle":
                    self.wfile.write(b"HTTP/1.1 200 OK\r\nX-Synthetic: ")
                    self.wfile.flush()
                    entered.set()
                    for _ in range(30):
                        time.sleep(0.03)
                        self.wfile.write(b"x")
                        self.wfile.flush()
                else:
                    time.sleep(0.25)
                    self.send_response(200)
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"{}")
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", entered, received
    server.shutdown()
    server.server_close()
    thread.join(3)
    assert not thread.is_alive()


def test_timeout_does_not_cancel_another_request_on_the_same_client(remote):
    base, entered, _ = remote
    errors = []
    with httpx.Client(transport=DeadlineTransport(), trust_env=False) as client:

        def slow():
            try:
                bounded_call(client, "GET", base + "/trickle", headers={}, deadline_seconds=0.15)
            except TimeoutError:
                pass
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=slow)
        thread.start()
        try:
            assert entered.wait(3)
            assert bounded_call(
                client, "GET", base + "/normal", headers={}, deadline_seconds=1
            ) == (200, b"{}")
        finally:
            thread.join(3)
        assert not thread.is_alive()
        assert not errors
    assert live_transfer_workers() == 0


def test_dns_timeout_cannot_dispatch_http_after_return(monkeypatch, remote):
    base, _, received = remote
    port = base.rsplit(":", 1)[1]
    release = threading.Event()
    futures = []
    original = socket.getaddrinfo

    def paused_system_dns(host, *args, **kwargs):
        if host in ("synthetic-sol.invalid", b"synthetic-sol.invalid"):
            assert release.wait(5)
            return original("127.0.0.1", *args, **kwargs)
        return original(host, *args, **kwargs)

    def paused_async_dns(self, *args, **kwargs):
        future = asyncio.get_running_loop().create_future()
        futures.append(future)
        return future

    monkeypatch.setattr(socket, "getaddrinfo", paused_system_dns)
    monkeypatch.setattr(aiodns.DNSResolver, "getaddrinfo", paused_async_dns)
    with httpx.Client(transport=DeadlineTransport(), trust_env=False) as client:
        started = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                bounded_call(
                    client,
                    "GET",
                    f"http://synthetic-sol.invalid:{port}/normal",
                    headers={},
                    deadline_seconds=0.15,
                )
            assert time.monotonic() - started <= 0.25
            assert live_transfer_workers() == 0
            assert futures and all(future.cancelled() for future in futures)
        finally:
            release.set()
            for thread in threading.enumerate():
                if thread.name.endswith("(transfer)"):
                    thread.join(3)
        assert not received.wait(0.1), "HTTP was sent after the deadline returned"


def test_retire_cannot_close_between_lease_check_and_registration():
    class Client(httpx.Client):
        close_count = 0

        def close(self):
            self.close_count += 1
            super().close()

    client = Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id="cli_synthetic_sol"),
        lambda: AppCredentials(app_id="cli_synthetic_sol", app_secret=SecretStr("synthetic")),
        client_factory=lambda: client,
    )
    lines, first = inspect.getsourcelines(provider.operation.__wrapped__)
    pause_line = first + next(
        i for i, line in enumerate(lines) if "context = _LeaseContext()" in line
    )
    checked, resume, holding, finish = (threading.Event() for _ in range(4))
    errors = []

    def trace(frame, event, arg):
        if event == "line" and frame.f_code.co_name == "operation" and frame.f_lineno == pause_line:
            checked.set()
            assert resume.wait(3)
        return trace

    def owner():
        sys.settrace(trace)
        try:
            with provider.operation():
                holding.set()
                assert finish.wait(3)
        except BaseException as exc:
            errors.append(exc)
        finally:
            sys.settrace(None)

    thread = threading.Thread(target=owner)
    thread.start()
    retiring = threading.Thread(target=provider.retire)
    try:
        assert checked.wait(3)
        retiring.start()
        retiring.join(0.05)
        resume.set()
        assert holding.wait(3)
        retiring.join(3)
        assert not retiring.is_alive()
        assert not provider.closed, "retire closed a client before its admitted lease finished"
        assert client.close_count == 0
    finally:
        resume.set()
        finish.set()
        thread.join(3)
        if retiring.ident is not None:
            retiring.join(3)
        provider.close()
    assert not errors
    assert client.close_count == 1


def test_tls_handshake_timeout_closes_the_connection_before_return():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(2)
    closed = threading.Event()
    errors = []

    def peer():
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(0.6)
                while connection.recv(8192):
                    pass  # accept ClientHello, never complete the TLS handshake
                closed.set()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=peer)
    thread.start()
    try:
        with httpx.Client(transport=DeadlineTransport(), trust_env=False) as client:
            started = time.monotonic()
            with pytest.raises(TimeoutError):
                bounded_call(
                    client,
                    "GET",
                    f"https://127.0.0.1:{listener.getsockname()[1]}/",
                    headers={},
                    deadline_seconds=0.15,
                )
            assert time.monotonic() - started < 0.25
            assert live_transfer_workers() == 0
            assert closed.wait(0.1), "TLS handshake left its TCP stream open"
    finally:
        listener.close()
        thread.join(2)
    assert not thread.is_alive()
    assert not errors


def test_normal_hostname_uses_real_pycares_numeric_result_without_system_dns(monkeypatch, remote):
    base, _, received = remote
    port = int(base.rsplit(":", 1)[1])
    original = aiodns.DNSResolver.getaddrinfo
    nodes = []

    async def synthetic_name(self, host, *args, **kwargs):
        # Real pycares parser and result shape; numeric loopback needs no DNS packet.
        result = await original(self, "127.0.0.1", *args, **kwargs)
        nodes.extend(result.nodes)
        return result

    def forbidden_system_dns(*args, **kwargs):
        raise AssertionError("numeric DNS results must never re-enter system DNS")

    monkeypatch.setattr(aiodns.DNSResolver, "getaddrinfo", synthetic_name)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_system_dns)
    with httpx.Client(transport=DeadlineTransport(), trust_env=False) as client:
        assert bounded_call(
            client,
            "GET",
            f"http://synthetic-sol.invalid:{port}/normal",
            headers={},
            deadline_seconds=1,
        ) == (200, b"{}")
    assert nodes and isinstance(nodes[0].addr[0], bytes)
    assert received.is_set()
    assert live_transfer_workers() == 0


def test_mounted_unsafe_transport_rejected_before_http(remote):
    base, _, received = remote
    with httpx.Client(
        transport=DeadlineTransport(),
        mounts={base: httpx.HTTPTransport(retries=0)},
        trust_env=False,
    ) as client:
        with pytest.raises(ValueError, match="requires DeadlineTransport"):
            bounded_call(client, "GET", base + "/trickle", headers={}, deadline_seconds=0.15)
    assert not received.is_set()
    assert live_transfer_workers() == 0


def test_compressed_remote_body_rejected_before_decoding():
    import gzip

    compressed = gzip.compress(b"x" * 16_000_000)
    headers_seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):  # noqa: N802
            headers_seen.append(self.headers.get("Accept-Encoding"))
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(compressed)))
            self.end_headers()
            try:
                self.wfile.write(compressed)
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        with httpx.Client(transport=DeadlineTransport(), trust_env=False) as client:
            with pytest.raises(ValueError, match="content encoding"):
                bounded_call(
                    client,
                    "GET",
                    f"http://127.0.0.1:{server.server_port}/",
                    headers={},
                    max_response_bytes=1024,
                )
        assert headers_seen == ["identity"]
        assert live_transfer_workers() == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


@pytest.mark.parametrize("kind", ["llm", "rerank"])
def test_full_json_wire_size_rejected_before_model_request(kind):
    from summit_everything.integrations.llm import DeepSeekLLM, LLMProviderError
    from summit_everything.integrations.rerank import ModelStudioReranker

    calls = []

    def handler(request):
        calls.append(len(request.content))
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises((ValueError, LLMProviderError)):
            if kind == "llm":
                DeepSeekLLM("synthetic", client=client)._request_content("system", "\n" * 600_000)
            else:
                ModelStudioReranker("synthetic", client=client).rank("query", ["x\n" * 350_000])
    assert calls == [], "oversized JSON must be rejected before HTTP"
