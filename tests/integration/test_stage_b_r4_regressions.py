"""R4 integrated regressions (synthetic only).

Chain exercised by every closure case:
    FastAPI route -> real FeishuService/auth coordinator -> real CredentialVault
    /VaultCredentialStore -> real FeishuHttpProvider -> synthetic remote.

Only the external HTTP boundary and the OS secret backend are replaced
(MockTransport / loopback server, and an in-memory backend). No real provider,
keychain item or business data is touched.
"""

from __future__ import annotations

from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-r4-session"}
APP_ID = "cli_synthetic_r4_app"
CALLBACK = "http://localhost:8765/callback"
SEARCH_SCOPE = "minutes:minutes.search:read"

TOKEN_PATH = "/open-apis/authen/v2/oauth/token"
TENANT_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
SEARCH_PATH = "/open-apis/minutes/v1/minutes/search"

USER_ITEM_PREFIX = "feishu_user:"
APP_ITEM_PREFIX = "feishu_app:"


class PausingSecretBackend(MemorySecretBackend):
    """In-memory backend whose app/user credential read can be paused.

    This is the real ``SecretBackend`` used by ``CredentialVault`` and
    ``VaultCredentialStore``; it only adds a controllable gate for the
    concurrency tests.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pause_prefix: str | None = None
        self._pause_at = 1
        self._armed_reads: dict[str, int] = {}
        self.reads: dict[str, int] = {}
        self.entered = Event()
        self.release = Event()

    def arm(self, prefix: str, *, at: int = 1) -> None:
        """Pause exactly once, on the ``at``-th read of a matching slot."""
        self._pause_prefix = prefix
        self._pause_at = at
        self._armed_reads = {}
        self.entered = Event()
        self.release = Event()

    def disarm(self) -> None:
        self._pause_prefix = None

    def get(self, namespace: str, key: str) -> str | None:
        self.reads[key] = self.reads.get(key, 0) + 1
        if self._pause_prefix is not None and key.startswith(self._pause_prefix):
            self._armed_reads[key] = self._armed_reads.get(key, 0) + 1
            if self._armed_reads[key] == self._pause_at:
                self.entered.set()
                assert self.release.wait(15)
        return super().get(namespace, key)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        return _keys_with_prefix(self, prefix)


class SyntheticRemote:
    """Serves the tenant, token and search endpoints with configurable pauses."""

    def __init__(
        self,
        *,
        token_gate: tuple[Event, Event] | None = None,
        exchange_access: str = "synthetic-access-1",
        exchange_refresh: str = "synthetic-refresh-1",
        exchange_scopes: list[str] | None = None,
        token_payload: dict[str, Any] | None = None,
    ) -> None:
        self.token_gate = token_gate
        self.exchange_access = exchange_access
        self.exchange_refresh = exchange_refresh
        self.exchange_scopes = exchange_scopes or [SEARCH_SCOPE]
        self.token_payload = token_payload
        self.paths: list[str] = []
        self.token_calls = 0
        self.search_calls = 0
        self.tenant_calls = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == TENANT_PATH:
            self.tenant_calls += 1
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == TOKEN_PATH:
            self.token_calls += 1
            if self.token_gate is not None:
                entered, release = self.token_gate
                entered.set()
                assert release.wait(15)
            if self.token_payload is not None:
                return httpx.Response(200, json=self.token_payload)
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": self.exchange_access,
                    "refresh_token": self.exchange_refresh,
                    "expires_in": 7200,
                    "scope": " ".join(self.exchange_scopes),
                    "token_type": "Bearer",
                },
            )
        if path == SEARCH_PATH:
            self.search_calls += 1
            return httpx.Response(
                200, json={"code": 0, "data": {"items": [{"token": "obc" + "0" * 21}]}}
            )
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


def _keys_with_prefix(backend: MemorySecretBackend, prefix: str) -> list[str]:
    """Inspect which vault slots exist, without going through the product API."""
    return sorted(key for _namespace, key in backend._values if key.startswith(prefix))


def _install_remote(monkeypatch, remote: SyntheticRemote) -> None:
    """Replace only the external HTTP boundary of the real adapter."""

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        client = httpx.Client(transport=httpx.MockTransport(remote.handler), follow_redirects=False)
        return FeishuHttpProvider(config, app_credentials, client=client, **kwargs)

    import summit_everything.api.app as app_module

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)


def _client(
    tmp_path: Path,
    monkeypatch,
    backend: MemorySecretBackend,
    remote: SyntheticRemote,
) -> TestClient:
    _install_remote(monkeypatch, remote)
    app = create_app(
        session_token="synthetic-r4-session",
        profile_root=tmp_path / "profile",
        secret_backend=backend,
    )
    client = TestClient(app, base_url="http://127.0.0.1:5173")
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
                    "identity": "user",
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
    return client


def _authorize_and_callback(client: TestClient, *, code: str = "synthetic-code"):
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    assert issued.status_code == 200, issued.text
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    return state, client.get(CALLBACK, params={"state": state, "code": code})


def _seed_authorization(client: TestClient) -> None:
    _state, response = _authorize_and_callback(client)
    assert response.status_code == 200, response.text


def _parallel(call, *args, **kwargs):  # type: ignore[no-untyped-def]
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = call(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - reported by _join, never swallowed
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


def _status(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/v1/integrations/feishu/status", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


# --- R4-01: logout must invalidate an old callback ---------------------------


def test_r4_01_a_logout_while_app_credential_read_blocks_rejects_the_old_callback(
    tmp_path, monkeypatch
):
    backend = PausingSecretBackend()
    remote = SyntheticRemote()
    client = _client(tmp_path, monkeypatch, backend, remote)

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]

    backend.arm(APP_ITEM_PREFIX)
    thread, box = _parallel(client.get, CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert backend.entered.wait(10), "callback never blocked in the app credential read"
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    backend.release.set()
    response = _join(thread, box)

    assert response.status_code in {400, 401, 403}, response.text
    assert remote.token_calls == 0, remote.token_calls
    assert _keys_with_prefix(backend, USER_ITEM_PREFIX) == [], _keys_with_prefix(
        backend, USER_ITEM_PREFIX
    )
    assert _status(client)["authorized"] is False


def test_r4_01_b_logout_and_new_authorization_win_over_the_old_callback(tmp_path, monkeypatch):
    backend = PausingSecretBackend()
    remote = SyntheticRemote(
        exchange_access="synthetic-access-new",
        exchange_refresh="synthetic-refresh-new",
    )
    client = _client(tmp_path, monkeypatch, backend, remote)

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    backend.arm(APP_ITEM_PREFIX)
    thread, box = _parallel(client.get, CALLBACK, params={"state": state, "code": "old-code"})
    assert backend.entered.wait(10)

    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    backend.disarm()  # let the new authorization through unpaused
    _state, fresh = _authorize_and_callback(client)
    assert fresh.status_code == 200, fresh.text

    backend.release.set()
    response = _join(thread, box)

    assert response.status_code in {400, 401, 403}, response.text
    assert remote.token_calls == 1, remote.token_calls  # only the new authorization exchanged
    status = _status(client)
    assert status["authorized"] is True, status


def test_r4_01_c_logout_while_the_token_request_is_in_flight_is_not_persisted(
    tmp_path, monkeypatch
):
    entered, release = Event(), Event()
    backend = MemorySecretBackend()
    remote = SyntheticRemote(token_gate=(entered, release))
    client = _client(tmp_path, monkeypatch, backend, remote)

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    thread, box = _parallel(client.get, CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert entered.wait(10), "the token request never started"
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    release.set()
    response = _join(thread, box)

    assert response.status_code in {400, 401, 403}, response.text
    assert remote.token_calls == 1, remote.token_calls
    assert _keys_with_prefix(backend, USER_ITEM_PREFIX) == []
    assert _status(client)["authorized"] is False


def test_r4_01_d_state_from_a_previous_service_instance_is_rejected(tmp_path, monkeypatch):
    backend = MemorySecretBackend()
    remote = SyntheticRemote()
    client = _client(tmp_path, monkeypatch, backend, remote)

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]

    # A configuration change builds another service instance for the same identity.
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-b"}}
        ).status_code
        == 200
    )
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-a"}}
        ).status_code
        == 200
    )

    response = client.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert response.status_code in {400, 401, 403}, response.text
    assert remote.token_calls == 0, remote.token_calls
    assert _keys_with_prefix(backend, USER_ITEM_PREFIX) == []


def test_r4_01_e_double_callback_exchanges_once_and_old_refresh_cannot_override(
    tmp_path, monkeypatch
):
    backend = MemorySecretBackend()
    remote = SyntheticRemote()
    client = _client(tmp_path, monkeypatch, backend, remote)

    state, first = _authorize_and_callback(client)
    assert first.status_code == 200, first.text
    second = client.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert second.status_code in {400, 401, 403}, second.text
    assert remote.token_calls == 1, remote.token_calls
    assert _status(client)["authorized"] is True
