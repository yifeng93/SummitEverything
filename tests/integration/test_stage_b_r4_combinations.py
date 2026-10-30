"""R4 combination regressions over the real product chain.

1. callback credential read paused + logout + new authorization + an old refresh
   returning + a configuration switch: only the legitimate new authorization
   survives.
2. an old multi-request read holding a lease + retire/configuration switch + a
   new request arriving + the old request trickling past its deadline: the old
   transfer is terminated, both requests use the right identity/configuration and
   the retired client closes exactly once.
"""

from __future__ import annotations

import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from authorized_feishu_client import AuthorizedFeishuReadClient
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.integrations.transport import DeadlineTransport

HEADERS = {"Authorization": "Bearer synthetic-r4-session"}
APP_ID = "cli_synthetic_r4_app"
CALLBACK = "http://localhost:8765/callback"
SEARCH_SCOPE = "minutes:minutes.search:read"

TOKEN_PATH = "/open-apis/authen/v2/oauth/token"
TENANT_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
SEARCH_PATH = "/open-apis/minutes/v1/minutes/search"
APP_ITEM_PREFIX = "feishu_app:"
USER_ITEM_PREFIX = "feishu_user:"


class Backend(MemorySecretBackend):
    def __init__(self, *, pause_prefix: str | None = None, pause_at: int = 1) -> None:
        super().__init__()
        self._pause_prefix = pause_prefix
        self._pause_at = pause_at
        self._armed: dict[str, int] = {}
        self.entered = Event()
        self.release = Event()

    def arm(self, prefix: str, *, at: int = 1) -> None:
        self._pause_prefix = prefix
        self._pause_at = at
        self._armed = {}
        self.entered = Event()
        self.release = Event()

    def disarm(self) -> None:
        self._pause_prefix = None

    def get(self, namespace: str, key: str) -> str | None:
        if self._pause_prefix is not None and key.startswith(self._pause_prefix):
            self._armed[key] = self._armed.get(key, 0) + 1
            if self._armed[key] == self._pause_at:
                self.entered.set()
                assert self.release.wait(15)
        return super().get(namespace, key)

    def user_items(self) -> list[str]:
        return sorted(key for _ns, key in self._values if key.startswith(USER_ITEM_PREFIX))


def _user_items(backend: MemorySecretBackend) -> list[str]:
    return sorted(key for _ns, key in backend._values if key.startswith(USER_ITEM_PREFIX))


class TokenRemote:
    """Serves tenant, token (exchange and refresh), search and calendar events."""

    def __init__(self, *, refresh_gate: tuple[Event, Event] | None = None) -> None:
        self.refresh_gate = refresh_gate
        self.token_calls = 0
        self.refresh_calls = 0
        self.exchange_calls = 0
        self.search_calls = 0
        self.events: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == TENANT_PATH:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == TOKEN_PATH:
            self.token_calls += 1
            body = request.read().decode()
            if "refresh_token" in body:
                self.refresh_calls += 1
                if self.refresh_gate is not None:
                    entered, release = self.refresh_gate
                    entered.set()
                    assert release.wait(15)
                return httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "access_token": "synthetic-refreshed-access",
                        "refresh_token": "synthetic-refreshed-refresh",
                        "expires_in": 7200,
                        "scope": SEARCH_SCOPE,
                        "token_type": "Bearer",
                    },
                )
            self.exchange_calls += 1
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "synthetic-authorized-access",
                    "refresh_token": "synthetic-authorized-refresh",
                    "expires_in": 7200,
                    "scope": SEARCH_SCOPE,
                    "token_type": "Bearer",
                },
            )
        if path == SEARCH_PATH:
            self.search_calls += 1
            return httpx.Response(
                200, json={"code": 0, "data": {"items": [{"token": "obc" + "0" * 21}]}}
            )
        if path.endswith("/events"):
            self.events.append(path)
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


class CloseTrackingClient(httpx.Client):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("transport", DeadlineTransport())
        super().__init__(**kwargs)
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        super().close()


def _api(
    tmp_path: Path,
    monkeypatch,
    backend: MemorySecretBackend,
    remote: Any,
    *,
    open_api_base: str | None = None,
    use_mock: bool = True,
    identity: str = "app",
):
    import summit_everything.api.app as app_module

    clients: list[CloseTrackingClient] = []

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        def make() -> CloseTrackingClient:
            kwargs: dict[str, Any] = {"follow_redirects": False}
            if use_mock:
                kwargs["transport"] = httpx.MockTransport(remote.handler)
            client = CloseTrackingClient(**kwargs)
            clients.append(client)
            return client

        if open_api_base is not None:
            kwargs["open_api_base"] = open_api_base
        return FeishuHttpProvider(config, app_credentials, client_factory=make, **kwargs)

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r4-session",
        profile_root=tmp_path / "profile",
        secret_backend=backend,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R4",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={
                "mode": "real",
                "feishu": {
                    "app_id": APP_ID,
                    "redirect_uri": CALLBACK,
                    "real_data_enabled": True,
                    "identity": identity,
                    "calendar_id": "cal-a",
                },
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/credentials/feishu_app",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": "synthetic-app-secret"},
        ).status_code
        == 200
    )
    return client, clients


def _parallel(call, *args, **kwargs):  # type: ignore[no-untyped-def]
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = call(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - surfaced by _join
            box["error"] = exc

    thread = Thread(target=run)
    thread.start()
    return thread, box


def _join(thread: Thread, box: dict[str, Any], timeout: float = 20.0) -> Any:
    thread.join(timeout)
    assert not thread.is_alive(), "worker thread did not finish"
    if "error" in box:
        raise box["error"]
    return box["value"]


def _authorize(client: TestClient) -> str:
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    assert issued.status_code == 200, issued.text
    return parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]


def test_r4_combo_1_new_authorization_survives_an_old_refresh_and_a_config_switch(
    tmp_path, monkeypatch
):
    entered, release = Event(), Event()
    backend = Backend()
    remote = TokenRemote(refresh_gate=(entered, release))
    client, _clients = _api(tmp_path, monkeypatch, backend, remote, identity="user")

    state = _authorize(client)
    assert client.get(CALLBACK, params={"state": state, "code": "first"}).status_code == 200
    # Force the next read into the refresh window by shortening the stored expiry.
    credentials = client.app.state.feishu_service.credentials.get()
    assert credentials is not None
    client.app.state.feishu_service.credentials.put(
        credentials.model_copy(update={"expires_at": time.time() + 5})
    )

    read_thread, read_box = _parallel(
        client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS
    )
    assert entered.wait(10), "the refresh never started"

    # logout, then a fresh authorization, then a configuration switch
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    fresh_state = _authorize(client)
    fresh = client.get(CALLBACK, params={"state": fresh_state, "code": "second"})
    assert fresh.status_code == 200, fresh.text
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-b"}}
        ).status_code
        == 200
    )

    release.set()
    try:
        _join(read_thread, read_box)
    except Exception:
        pass  # the in-flight read may be rejected; the credential state is what matters

    stored = client.app.state.feishu_service.credentials.get()
    assert stored is not None
    assert stored.access_token == "synthetic-authorized-access", stored.access_token
    assert stored.refresh_token == "synthetic-authorized-refresh"
    status = client.get("/api/v1/integrations/feishu/status", headers=HEADERS).json()
    assert status["authorized"] is True, status
    assert remote.refresh_calls == 1, remote.refresh_calls
    assert remote.exchange_calls == 2, remote.exchange_calls


class _TrickleHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        cfg = self.server.cfg  # type: ignore[attr-defined]
        cfg["requests"] += 1
        cfg["sockets"].append(self.connection)
        request_path = self.path.split("?", 1)[0]
        if request_path.endswith("/transcript"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "100000")
            self.end_headers()
            try:
                for _ in range(200):
                    # Observe peer FIN/reset before producing another byte;
                    # write success alone can lag TCP closure by one buffered send.
                    if select.select([self.connection], [], [], 0.04)[0]:
                        if not self.connection.recv(1, socket.MSG_PEEK):
                            cfg["aborted"] = True
                            return
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    cfg["sent"] += 1
            except OSError:
                cfg["aborted"] = True
            return
        if "tenant_access_token" in request_path:
            payload = b'{"code":0,"tenant_access_token":"t-loopback","expire":7200}'
        elif request_path.endswith("/events"):
            payload = b'{"code":0,"data":{"items":[]}}'
        else:
            payload = b'{"code":0,"data":{}}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    do_POST = do_GET


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # noqa: ANN001
        exc = __import__("sys").exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, OSError)):
            return
        super().handle_error(request, client_address)


class TrickleServer:
    def __init__(self) -> None:
        self.cfg: dict[str, Any] = {"requests": 0, "sent": 0, "aborted": False, "sockets": []}
        self.server = _Server(("127.0.0.1", 0), _TrickleHandler)
        self.server.cfg = self.cfg  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)


def test_r4_combo_2_old_trickling_read_is_cancelled_while_a_new_request_uses_new_config(
    tmp_path, monkeypatch
):
    import summit_everything.integrations.feishu.http as feishu_http
    from summit_everything.integrations.http_boundary import live_transfer_workers

    server = TrickleServer()
    backend = MemorySecretBackend()
    remote = TokenRemote()
    client, clients = _api(
        tmp_path,
        monkeypatch,
        backend,
        remote,
        open_api_base=server.base,
        use_mock=False,
    )
    # Workspace opening may create a provider for the initial default
    # configuration; the latest provider is the one bound to this read.
    old_client = clients[-1]

    original_bounded_call = feishu_http.bounded_call

    def small_deadline(*args, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("deadline_seconds") is None:
            # Long enough that the configuration switch reliably lands while the
            # first trickling body read is still in flight.
            kwargs["deadline_seconds"] = 1.0
        return original_bounded_call(*args, **kwargs)

    monkeypatch.setattr(feishu_http, "bounded_call", small_deadline)

    try:
        materials = ["obc" + "0" * 21, "obc" + "1" * 21, "obc" + "2" * 21]
        thread, box = _parallel(
            client.post,
            "/api/v1/integrations/feishu/imports",
            headers=HEADERS,
            json={"material_ids": materials, "operation_id": "imp-combo"},
        )
        # Wait until the trickling body read is running, then switch config
        # while it is still in flight (its deadline is 1.0 s).
        deadline = time.monotonic() + 10
        while server.cfg["requests"] == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert thread.is_alive(), "the read finished before the configuration switch"

        assert (
            client.patch(
                "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-b"}}
            ).status_code
            == 200
        )
        assert old_client.close_calls == 0, "the retired client was closed mid-operation"

        result = _join(thread, box)
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["state"] in {"partial", "failed"}, body

        # A brand-new request uses the new configuration and the new provider.
        assert len(clients) >= 2, len(clients)
        new_client = clients[-1]
        calendar = client.get(
            "/api/v1/integrations/feishu/calendar",
            headers=HEADERS,
            params={
                "start": "2026-10-09T00:00:00+08:00",
                "end": "2026-10-10T00:00:00+08:00",
                "timezone": "Asia/Shanghai",
            },
        )
        assert calendar.status_code == 200, calendar.text

        assert live_transfer_workers() == 0, live_transfer_workers()
        assert old_client.close_calls == 1, old_client.close_calls
        assert new_client.close_calls == 0
        observation_deadline = time.monotonic() + 0.1
        while not server.cfg["aborted"] and time.monotonic() < observation_deadline:
            time.sleep(0.005)
        assert server.cfg["aborted"], "peer did not observe FIN/reset after cancellation"
        sent = server.cfg["sent"]
        time.sleep(0.3)
        assert server.cfg["sent"] == sent, "the trickling transfer continued after the call"
        assert server.cfg["aborted"] is True, "the server never observed the transfer ending"
    finally:
        client.close()
        server.stop()
