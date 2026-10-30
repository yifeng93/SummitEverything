"""R3 integrated regressions (synthetic only).

Every test drives the real FastAPI route through the real service, credential
adapter and identity/refresh/lifecycle logic, replacing only the external HTTP
boundary with a synthetic remote. No real provider, keychain item or business
data is touched.
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from authorized_feishu_client import AuthorizedFeishuReadClient
from fastapi.testclient import TestClient
from pydantic import SecretStr

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    FeishuError,
    UserCredentials,
)
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-r3-session"}
APP_ID = "cli_synthetic_r3_app"
CALLBACK = "http://localhost:8765/callback"
SEARCH_SCOPE = "minutes:minutes.search:read"

TENANT = "/open-apis/auth/v3/tenant_access_token/internal"
TOKEN = "/open-apis/authen/v2/oauth/token"
SEARCH = "/open-apis/minutes/v1/minutes/search"
PRIMARY = "/open-apis/calendar/v4/calendars/primary"


class InstrumentedStore:
    """Synthetic credential store that counts reads and can simulate corruption."""

    def __init__(
        self,
        user: UserCredentials | None = None,
        app: AppCredentials | None = None,
        *,
        corrupt_user: bool = False,
        deny_user_read: bool = False,
    ) -> None:
        self.user = user
        self.app = app
        self.corrupt_user = corrupt_user
        self.deny_user_read = deny_user_read
        self.user_reads = 0
        self.app_reads = 0
        self.puts = 0

    def get(self) -> UserCredentials | None:
        self.user_reads += 1
        if self.deny_user_read:
            raise PermissionError("synthetic keychain denial")
        if self.corrupt_user:
            raise ValueError("stored Feishu credentials are invalid")
        return self.user

    def put(self, credentials: UserCredentials) -> None:
        self.puts += 1
        self.corrupt_user = False
        self.user = credentials

    def delete(self) -> None:
        self.user = None

    def get_app(self) -> AppCredentials | None:
        self.app_reads += 1
        return self.app

    def put_app(self, credentials: AppCredentials) -> None:
        self.app = credentials


def _user_token(
    access: str = "synthetic-access",
    refresh: str = "synthetic-refresh",
    *,
    expires_in: float = 3600,
    scopes: list[str] | None = None,
) -> UserCredentials:
    return UserCredentials(
        access_token=access,
        refresh_token=refresh,
        expires_at=time.time() + expires_in,
        scopes=scopes if scopes is not None else [SEARCH_SCOPE, "task:task:read"],
    )


def _app_credentials() -> AppCredentials:
    return AppCredentials(app_id=APP_ID, app_secret=SecretStr("synthetic-app-secret"))


class RemoteStub:
    """Synthetic remote that can pause specific phases with events."""

    def __init__(self, *, search_items: int = 1) -> None:
        self.search_items = search_items
        self.paths: list[str] = []
        self.refresh_tokens_seen: list[str] = []
        self.search_calls = 0
        self.refresh_calls = 0
        self.exchange_calls = 0
        self.on_search: Any = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == SEARCH:
            self.search_calls += 1
            if self.on_search is not None:
                self.on_search()
            items = [
                {"token": f"obc{index:021d}", "display_info": f"合成妙记 {index}"}
                for index in range(self.search_items)
            ]
            return httpx.Response(200, json={"code": 0, "data": {"items": items}})
        return httpx.Response(404, json={"code": 99991672, "msg": "synthetic unexpected path"})


class ServiceRemote(FakeFeishu):
    """FakeFeishu with controllable refresh/exchange, used for service-level races."""

    def __init__(
        self,
        remote: Path,
        *,
        refresh_gate: tuple[Event, Event] | None = None,
        refresh_sequence: int = 1,
        exchange_access: str = "synthetic-access-new",
        exchange_refresh: str = "synthetic-refresh-new",
        exchange_scopes: list[str] | None = None,
        refresh_error: Exception | None = None,
        refresh_omits_token: bool = False,
    ) -> None:
        super().__init__(remote)
        self.refresh_calls = 0
        self.refresh_tokens_seen: list[str] = []
        self.exchange_calls = 0
        self.refresh_gate = refresh_gate
        self.refresh_sequence = refresh_sequence
        self.exchange_access = exchange_access
        self.exchange_refresh = exchange_refresh
        self.exchange_scopes = exchange_scopes or [SEARCH_SCOPE]
        self.refresh_error = refresh_error
        self.refresh_omits_token = refresh_omits_token

    def refresh(self, credentials):  # type: ignore[no-untyped-def]
        self.refresh_calls += 1
        self.refresh_tokens_seen.append(credentials.refresh_token)
        if self.refresh_gate is not None:
            entered, release = self.refresh_gate
            entered.set()
            assert release.wait(15)
        if self.refresh_error is not None:
            raise self.refresh_error
        return UserCredentials(
            access_token=f"synthetic-access-r{self.refresh_sequence}",
            refresh_token=f"synthetic-refresh-r{self.refresh_sequence}",
            expires_at=time.time() + 3600,
            scopes=credentials.scopes,
        )

    def exchange(self, code, redirect_uri, app_credentials=None):  # type: ignore[no-untyped-def]
        self.exchange_calls += 1
        return UserCredentials(
            access_token=self.exchange_access,
            refresh_token=self.exchange_refresh,
            expires_at=time.time() + 3600,
            scopes=self.exchange_access and self.exchange_scopes or [],
        )


def _client(tmp_path: Path, store: InstrumentedStore, provider: Any) -> TestClient:
    app = create_app(
        session_token="synthetic-r3-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        feishu_provider=provider,
        credential_store=store,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    response = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "Synthetic R3",
            "operation_id": "open",
        },
    )
    assert response.status_code == 201, response.text
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
    return client


def _parallel(call, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Run a callable in a thread, returning the thread and a result box that
    records any exception so a leaked worker failure cannot pass silently."""
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = call(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - reported below, never swallowed
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


# --- R3-01: an in-flight refresh must never overwrite a newer authorization ---


def test_r3_01_concurrent_readers_share_one_refresh_and_both_use_new_credentials(tmp_path):
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(tmp_path / "remote", refresh_gate=(entered, release))
    client = _client(tmp_path, store, provider)

    first_thread, first_box = _parallel(
        client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS
    )
    assert entered.wait(10), "refresh never entered the remote"
    second_thread, second_box = _parallel(
        client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS
    )
    release.set()
    first = _join(first_thread, first_box)
    second = _join(second_thread, second_box)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert provider.refresh_calls == 1, provider.refresh_calls
    assert store.user is not None
    assert store.user.refresh_token == "synthetic-refresh-r1"


def test_r3_01_logout_during_refresh_does_not_resurrect_credentials(tmp_path):
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(tmp_path / "remote", refresh_gate=(entered, release))
    client = _client(tmp_path, store, provider)

    thread, box = _parallel(client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert entered.wait(10)
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    release.set()
    response = _join(thread, box)
    assert response.status_code in {401, 403}, response.text

    assert store.user is None, store.user
    status = client.get("/api/v1/integrations/feishu/status", headers=HEADERS).json()
    assert status["authorized"] is False


def test_r3_01_logout_then_new_authorization_during_refresh_is_preserved(tmp_path):
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(
        tmp_path / "remote",
        refresh_gate=(entered, release),
        exchange_access="synthetic-access-reauthorized",
        exchange_refresh="synthetic-refresh-reauthorized",
        exchange_scopes=[SEARCH_SCOPE],
    )
    client = _client(tmp_path, store, provider)

    thread, box = _parallel(client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert entered.wait(10)

    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    assert issued.status_code == 200, issued.text
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    callback = client.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert callback.status_code == 200, callback.text

    release.set()
    # The in-flight read may fail or succeed, but the newer authorization must win.
    try:
        _join(thread, box)
    except FeishuError:
        pass

    assert store.user is not None
    assert store.user.access_token == "synthetic-access-reauthorized"
    assert store.user.refresh_token == "synthetic-refresh-reauthorized"
    assert provider.refresh_calls == 1


def test_r3_01_old_configuration_refresh_cannot_overwrite_new_configuration_login(
    tmp_path, monkeypatch
):
    """A service built under the old configuration must not clobber a login made
    through a service built under the new configuration."""
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(
        tmp_path / "remote",
        refresh_gate=(entered, release),
        exchange_access="synthetic-access-newconfig",
        exchange_refresh="synthetic-refresh-newconfig",
        exchange_scopes=[SEARCH_SCOPE],
    )
    client = _client(tmp_path, store, provider)

    thread, box = _parallel(client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert entered.wait(10)

    # A configuration change builds a second service for the same profile/app.
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"calendar_id": "cal-rotated"}},
        ).status_code
        == 200
    )
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    callback = client.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert callback.status_code == 200, callback.text

    release.set()
    try:
        _join(thread, box)
    except FeishuError:
        pass

    assert store.user is not None
    assert store.user.access_token == "synthetic-access-newconfig"
    assert store.user.refresh_token == "synthetic-refresh-newconfig"


def test_r3_01_callback_in_flight_logout_is_rejected(tmp_path):
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=None)

    class SlowExchange(ServiceRemote):
        def exchange(self, code, redirect_uri, app_credentials=None):  # type: ignore[no-untyped-def]
            entered.set()
            assert release.wait(15)
            return super().exchange(code, redirect_uri, app_credentials)

    provider = SlowExchange(tmp_path / "remote")
    client = _client(tmp_path, store, provider)

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    thread, box = _parallel(client.get, CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert entered.wait(10)
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    release.set()
    response = _join(thread, box)

    assert response.status_code in {400, 403}, response.text
    assert store.user is None, store.user


def test_r3_01_failed_refresh_never_reuses_the_consumed_token(tmp_path):
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(
        tmp_path / "remote",
        refresh_error=FeishuError("provider_timeout"),
    )
    client = _client(tmp_path, store, provider)

    first = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert first.status_code == 503, first.text
    assert provider.refresh_calls == 1

    second = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert second.status_code in {401, 403}, second.text
    assert provider.refresh_calls == 1, provider.refresh_calls


# --- R3-02: strict parsing of the OAuth token response ----------------------


class TokenRemote:
    """Serves the token endpoint with a configurable response, plus a search call."""

    def __init__(
        self,
        token_payload: Any = None,
        *,
        token_status: int = 200,
        token_timeout: bool = False,
        search_items: int = 1,
        token_gate: tuple[Event, Event] | None = None,
    ) -> None:
        self.token_payload = token_payload
        self.token_status = token_status
        self.token_timeout = token_timeout
        self.search_items = search_items
        self.token_gate = token_gate
        self.token_calls = 0
        self.search_calls = 0
        self.paths: list[str] = []
        self.refresh_tokens_seen: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == TOKEN:
            self.token_calls += 1
            if self.token_gate is not None:
                entered, release = self.token_gate
                entered.set()
                assert release.wait(15)
            body = request.read().decode()
            if "refresh_token" in body:
                import json as _json

                self.refresh_tokens_seen.append(_json.loads(body).get("refresh_token", ""))
            if self.token_timeout:
                raise httpx.ReadTimeout("synthetic lost response")
            return httpx.Response(self.token_status, json=self.token_payload)
        if path == SEARCH:
            self.search_calls += 1
            items = [
                {"token": f"obc{index:021d}", "display_info": f"合成妙记 {index}"}
                for index in range(self.search_items)
            ]
            return httpx.Response(200, json={"code": 0, "data": {"items": items}})
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


def _http_client(tmp_path: Path, monkeypatch, store: InstrumentedStore, remote: TokenRemote):
    from datetime import timedelta

    import summit_everything.api.app as app_module

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        client = httpx.Client(transport=httpx.MockTransport(remote.handler), follow_redirects=False)
        client.timeout = httpx.Timeout(connect=5.0, read=timedelta(seconds=10), write=5.0, pool=5.0)
        return FeishuHttpProvider(config, app_credentials, client=client, **kwargs)

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r3-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        credential_store=store,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R3",
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
    return client


def _valid_token_payload(refresh: str = "synthetic-refresh-new") -> dict[str, Any]:
    return {
        "code": 0,
        "access_token": "synthetic-access-new",
        "refresh_token": refresh,
        "expires_in": 7200,
        "scope": SEARCH_SCOPE,
        "token_type": "Bearer",
    }


def test_r3_02_valid_rotation_updates_credentials_and_keeps_one_request(tmp_path, monkeypatch):
    remote = TokenRemote(_valid_token_payload())
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    client = _http_client(tmp_path, monkeypatch, store, remote)

    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 200, response.text
    assert remote.token_calls == 1, remote.token_calls
    assert store.user is not None
    assert store.user.access_token == "synthetic-access-new"
    assert store.user.refresh_token == "synthetic-refresh-new"
    assert store.user.scopes == [SEARCH_SCOPE]


@pytest.mark.parametrize(
    "mutate,label",
    [
        (lambda p: p.pop("refresh_token"), "missing_refresh"),
        (lambda p: p.__setitem__("refresh_token", "synthetic-refresh"), "reused_refresh"),
        (lambda p: p.pop("token_type"), "missing_token_type"),
        (lambda p: p.__setitem__("token_type", "mac"), "wrong_token_type"),
        (lambda p: p.pop("scope"), "missing_scope"),
        (lambda p: p.__setitem__("scope", ""), "empty_scope"),
        (lambda p: p.pop("expires_in"), "missing_expiry"),
        (lambda p: p.__setitem__("expires_in", True), "bool_expiry"),
        (lambda p: p.__setitem__("expires_in", float("nan")), "nan_expiry"),
        (lambda p: p.__setitem__("expires_in", float("inf")), "inf_expiry"),
        (lambda p: p.__setitem__("expires_in", 0), "zero_expiry"),
        (lambda p: p.__setitem__("expires_in", -1), "negative_expiry"),
        (lambda p: p.__setitem__("expires_in", "7200"), "string_expiry"),
    ],
)
def test_r3_02_invalid_refresh_response_never_writes_credentials(
    tmp_path, monkeypatch, mutate, label
):
    payload = _valid_token_payload()
    mutate(payload)
    remote = TokenRemote(payload)
    original = _user_token(expires_in=5)
    store = InstrumentedStore(app=_app_credentials(), user=original)
    client = _http_client(tmp_path, monkeypatch, store, remote)

    first = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert first.status_code in {400, 401, 403, 502, 503}, (label, first.text)
    assert remote.token_calls == 1, (label, remote.token_calls)
    # The corrupt response must not replace the stored credential.
    assert store.user is not None
    assert store.user.access_token == original.access_token
    assert store.user.refresh_token == original.refresh_token

    # The consumed single-use token is never resent.
    second = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert second.status_code in {401, 403}, (label, second.text)
    assert remote.token_calls == 1, (label, remote.token_calls)


def test_r3_02_lost_response_does_not_write_credentials_or_retry(tmp_path, monkeypatch):
    remote = TokenRemote(None, token_timeout=True)
    original = _user_token(expires_in=5)
    store = InstrumentedStore(app=_app_credentials(), user=original)
    client = _http_client(tmp_path, monkeypatch, store, remote)

    first = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert first.status_code in {502, 503}, first.text
    assert remote.token_calls == 1
    assert store.user is not None and store.user.refresh_token == original.refresh_token

    second = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert second.status_code in {401, 403}, second.text
    assert remote.token_calls == 1, remote.token_calls
    assert remote.refresh_tokens_seen == [original.refresh_token]


@pytest.mark.parametrize(
    "payload,label,expected",
    [
        ({"code": 20037, "msg": "refresh token expired"}, "expired", "token_expired"),
        ({"code": 20002, "msg": "bad secret"}, "bad_secret", "provider_unavailable"),
    ],
)
def test_r3_02_business_errors_are_mapped_and_sanitized(
    tmp_path, monkeypatch, payload, label, expected
):
    remote = TokenRemote(payload)
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    client = _http_client(tmp_path, monkeypatch, store, remote)

    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code in {401, 403, 502, 503}, (label, response.text)
    assert "synthetic" not in response.text or "合成" in response.text
    assert remote.token_calls == 1


# --- R3-03: a retired provider must finish a complete business operation ----


class PausingRemote:
    """Synth remote that can pause between the steps of one business operation."""

    def __init__(
        self,
        *,
        calendar_id: str = "cal-a",
        pause_path: str | None = None,
        pause_at: int = 1,
        transcript_fallback: bool = False,
        body_error: Exception | None = None,
        error_on_body_call: int | None = None,
    ) -> None:
        self.calendar_id = calendar_id
        self.pause_path = pause_path
        self.pause_at = pause_at
        self.transcript_fallback = transcript_fallback
        self.body_error = body_error
        self.error_on_body_call = error_on_body_call
        self.body_calls = 0
        self.entered = Event()
        self.release = Event()
        self.paths: list[str] = []
        self.events: list[str] = []
        self.bodies: list[str] = []

    def _maybe_pause(self, path: str) -> None:
        if self.pause_path is not None and path.endswith(self.pause_path):
            if sum(1 for p in self.paths if p.endswith(self.pause_path)) >= self.pause_at:
                self.entered.set()
                assert self.release.wait(15)

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path.startswith("/open-apis/calendar/v4/calendars/") and path.endswith("/events"):
            self.events.append(path)
            self._maybe_pause("/events")
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        if path == PRIMARY:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"calendars": [{"calendar": {"calendar_id": self.calendar_id}}]},
                },
            )
        if path.endswith("/transcript"):
            self._maybe_pause("/transcript")
            self.body_calls += 1
            if self.error_on_body_call == self.body_calls:
                raise httpx.ReadTimeout("synthetic mid-operation body timeout")
            if self.body_error is not None:
                raise self.body_error
            if self.transcript_fallback:
                return httpx.Response(200, json={"code": 2091005, "msg": "permission deny"})
            self.bodies.append("transcript")
            return httpx.Response(200, content=b"synthetic transcript")
        if path.endswith("/artifacts"):
            self._maybe_pause("/artifacts")
            self.bodies.append("artifacts")
            return httpx.Response(200, json={"code": 0, "data": {"transcript": "合成逐字稿"}})
        if path == SEARCH:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"items": [{"token": "obc" + "0" * 21}]}},
            )
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


class CloseTrackingClient(httpx.Client):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        super().close()


def _lease_client(tmp_path: Path, monkeypatch, remote: PausingRemote):
    import summit_everything.api.app as app_module

    holder: dict[str, CloseTrackingClient] = {}

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        def make() -> CloseTrackingClient:
            client = CloseTrackingClient(
                transport=httpx.MockTransport(remote.handler), follow_redirects=False
            )
            holder["client"] = client
            return client

        return FeishuHttpProvider(config, app_credentials, client_factory=make, **kwargs)

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    store = InstrumentedStore(app=_app_credentials(), user=None)
    app = create_app(
        session_token="synthetic-r3-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        credential_store=store,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R3",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    return client, holder


def _patch_calendar(client: TestClient, calendar_id: str) -> None:
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
                    "calendar_id": calendar_id,
                },
            },
        ).status_code
        == 200
    )


def test_r3_03_calendar_operation_survives_a_config_change_between_primary_and_events(
    tmp_path, monkeypatch
):
    remote = PausingRemote(pause_path="/events")
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")

    thread, box = _parallel(
        client.get,
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert remote.entered.wait(10), "the old operation never reached the events step"
    old_client = holder["client"]

    # Rotate the configuration while the first operation is mid-flight.
    _patch_calendar(client, "cal-b")
    assert old_client.close_calls == 0, "retired client closed mid-operation"

    remote.release.set()
    first = _join(thread, box)
    assert first.status_code == 200, first.text
    assert remote.events and remote.events[-1].startswith(
        "/open-apis/calendar/v4/calendars/cal-a/"
    ), remote.events
    # Closed only after the complete operation (primary then events) finished.
    assert old_client.close_calls == 1, old_client.close_calls

    # A new operation must immediately use the new configuration.
    assert _calendar_request_id(client, "cal-b") == 200
    assert remote.events[-1].startswith("/open-apis/calendar/v4/calendars/cal-b/"), remote.events


def _calendar_request_id(client: TestClient, calendar_id: str) -> int:
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert response.status_code == 200, (calendar_id, response.text)
    return response.status_code


def test_r3_03_retired_provider_closes_only_after_the_operation_finishes(tmp_path, monkeypatch):
    remote = PausingRemote(pause_path="/events")
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")

    thread, box = _parallel(
        client.get,
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert remote.entered.wait(10)
    old_client = holder["client"]

    _patch_calendar(client, "cal-b")
    # Retired, but its operation still holds a lease: the real client stays open.
    assert old_client.close_calls == 0, "client closed while an operation was in flight"

    remote.release.set()
    assert _join(thread, box).status_code == 200
    assert old_client.close_calls == 1, old_client.close_calls


def test_r3_03_body_fallback_across_two_endpoints_is_not_cut_short(tmp_path, monkeypatch):
    remote = PausingRemote(pause_path="/transcript", transcript_fallback=True)
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"material_content": "transcript"}},
        ).status_code
        == 200
    )
    old_client = holder["client"]

    thread, box = _parallel(
        client.post,
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "0" * 21], "operation_id": "imp-fallback"},
    )
    assert remote.entered.wait(10), "import never reached the transcript step"

    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"calendar_id": "cal-b"}},
        ).status_code
        == 200
    )
    assert old_client.close_calls == 0, "retired client closed mid-operation"
    remote.release.set()
    result = _join(thread, box)

    assert result.status_code == 200, result.text
    assert result.json()["state"] == "succeeded", result.text
    assert remote.bodies == ["artifacts"], remote.bodies
    # The fallback ran inside the same lease, so the client outlived it.
    assert old_client.close_calls == 1, old_client.close_calls


def test_r3_03_multi_item_import_keeps_one_snapshot_across_a_config_change(tmp_path, monkeypatch):
    remote = PausingRemote(pause_path="/transcript", pause_at=2)
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"material_content": "transcript"}},
        ).status_code
        == 200
    )
    old_client = holder["client"]
    materials = ["obc" + "0" * 21, "obc" + "1" * 21, "obc" + "2" * 21]

    thread, box = _parallel(
        client.post,
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": materials, "operation_id": "imp-multi"},
    )
    assert remote.entered.wait(10), "import never reached the second body step"

    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"calendar_id": "cal-b"}},
        ).status_code
        == 200
    )
    assert old_client.close_calls == 0, "retired client closed mid-operation"
    remote.release.set()
    result = _join(thread, box)

    assert result.status_code == 200, result.text
    body = result.json()
    assert body["state"] == "succeeded", body
    assert len(body["outcomes"]) == 3
    assert old_client.close_calls == 1, old_client.close_calls
    items = client.get("/api/v1/intake/items", headers=HEADERS).json()
    assert len(items) == 3
    for item in items:
        source = client.get(f"/api/v1/sources/{item['source_id']}", headers=HEADERS).json()
        identity = source["source"]["external_identity"]
        assert identity["provider"] == "feishu", identity
        assert identity["token_type"] == "app", identity


def test_r3_03_idle_retire_closes_exactly_once_and_rejects_new_operations(tmp_path, monkeypatch):
    remote = PausingRemote()
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")
    assert _calendar_request_id(client, "cal-a") == 200
    first_client = holder["client"]

    # Rotating the configuration retires the idle provider exactly once.
    _patch_calendar(client, "cal-b")
    assert first_client.close_calls == 1, first_client.close_calls
    # A further rotation must not re-close an already closed client.
    _patch_calendar(client, "cal-c")
    assert first_client.close_calls == 1, first_client.close_calls


def _http_lease_client(
    tmp_path: Path,
    monkeypatch,
    store: InstrumentedStore,
    remote: TokenRemote,
    *,
    identity: str = "app",
):
    import summit_everything.api.app as app_module

    holder: dict[str, CloseTrackingClient] = {}

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        def make() -> CloseTrackingClient:
            client = CloseTrackingClient(
                transport=httpx.MockTransport(remote.handler), follow_redirects=False
            )
            holder["client"] = client
            return client

        return FeishuHttpProvider(config, app_credentials, client_factory=make, **kwargs)

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r3-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        credential_store=store,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R3",
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
                },
            },
        ).status_code
        == 200
    )
    return client, holder


def test_r3_03_refresh_then_read_survives_a_config_change_without_rerefreshing(
    tmp_path, monkeypatch
):
    """A lease must span refresh *and* the resource read that follows it."""
    entered, release = Event(), Event()
    remote = TokenRemote(_valid_token_payload(), token_gate=(entered, release))
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    client, holder = _http_lease_client(tmp_path, monkeypatch, store, remote, identity="user")
    old_client = holder["client"]

    thread, box = _parallel(client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert entered.wait(10), "refresh never reached the token endpoint"

    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-b"}}
        ).status_code
        == 200
    )
    assert old_client.close_calls == 0, "retired client closed mid-operation"
    release.set()
    response = _join(thread, box)

    assert response.status_code == 200, response.text
    assert remote.token_calls == 1, remote.token_calls
    assert remote.search_calls == 1, remote.search_calls
    assert store.user is not None and store.user.refresh_token == "synthetic-refresh-new"
    assert old_client.close_calls == 1, old_client.close_calls


def test_r3_03_failed_body_call_still_releases_the_lease_and_closes_once(tmp_path, monkeypatch):
    remote = PausingRemote(body_error=httpx.ReadTimeout("synthetic body failure"))
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")
    old_client = holder["client"]

    response = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "0" * 21], "operation_id": "imp-error"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "failed", body
    assert body["outcomes"][0]["state"] == "failed", body

    # Rotating now that the failed operation has released its lease closes once.
    _patch_calendar(client, "cal-b")
    assert old_client.close_calls == 1, old_client.close_calls


# --- R3-04: application identity must not depend on the user credential slot -


class IdentityRemote:
    """Serves every endpoint an application-identity operation needs."""

    def __init__(self, *, calendar_id: str = "cal-a", corrupt_item: bool = False) -> None:
        self.calendar_id = calendar_id
        self.corrupt_item = corrupt_item
        self.paths: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path.endswith("/events"):
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        if path == PRIMARY:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"calendars": [{"calendar": {"calendar_id": self.calendar_id}}]},
                },
            )
        if path.endswith("/transcript"):
            return httpx.Response(200, content=b"synthetic transcript")
        if path == SEARCH:
            return httpx.Response(
                200, json={"code": 0, "data": {"items": [{"token": "obc" + "0" * 21}]}}
            )
        if path.startswith("/open-apis/task/v2/tasks/"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "task": {
                            "guid": path.rsplit("/", 1)[-1],
                            "summary": "合成任务",
                            "description": "",
                            "completed_at": "0",
                        }
                    },
                },
            )
        if path == "/open-apis/task/v2/tasks":
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


def _identity_client(tmp_path, monkeypatch, store, remote: IdentityRemote):
    client, _holder = _http_lease_client(tmp_path, monkeypatch, store, remote)  # type: ignore[arg-type]
    return client


@pytest.mark.parametrize("user_state", ["missing", "corrupt", "denied"])
def test_r3_04_application_identity_never_reads_a_broken_user_slot(
    tmp_path, monkeypatch, user_state
):
    store = InstrumentedStore(
        app=_app_credentials(),
        user=None if user_state == "missing" else _user_token(),
        corrupt_user=user_state == "corrupt",
        deny_user_read=user_state == "denied",
    )
    remote = IdentityRemote()
    client = _identity_client(tmp_path, monkeypatch, store, remote)
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
                    "calendar_id": "cal-a",
                    "identity": "app",
                },
            },
        ).status_code
        == 200
    )

    calendar = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert calendar.status_code == 200, (user_state, calendar.text)

    imported = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "0" * 21], "operation_id": f"imp-{user_state}"},
    )
    assert imported.status_code == 200, (user_state, imported.text)
    assert imported.json()["state"] == "succeeded", (user_state, imported.text)

    detail = client.get("/api/v1/integrations/feishu/tasks/task-1", headers=HEADERS)
    assert detail.status_code == 200, (user_state, detail.text)
    assert detail.json()["guid"] == "task-1"

    # The user credential slot was never read for these application operations.
    assert store.user_reads == 0, (user_state, store.user_reads)


def test_r3_04_missing_app_secret_is_reported_without_reading_the_user_slot(tmp_path, monkeypatch):
    store = InstrumentedStore(app=None, user=_user_token(), corrupt_user=True)
    remote = IdentityRemote()
    client = _identity_client(tmp_path, monkeypatch, store, remote)
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
                    "calendar_id": "cal-a",
                },
            },
        ).status_code
        == 200
    )
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "credential_missing"
    assert store.user_reads == 0, store.user_reads


@pytest.mark.parametrize("user_state", ["corrupt", "denied"])
def test_r3_04_user_only_endpoints_report_readably_when_the_user_slot_is_broken(
    tmp_path, monkeypatch, user_state
):
    store = InstrumentedStore(
        app=_app_credentials(),
        user=_user_token(),
        corrupt_user=user_state == "corrupt",
        deny_user_read=user_state == "denied",
    )
    remote = IdentityRemote()
    client = _identity_client(tmp_path, monkeypatch, store, remote)
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
                },
            },
        ).status_code
        == 200
    )
    for path in ("/api/v1/integrations/feishu/materials", "/api/v1/integrations/feishu/tasks"):
        response = client.get(path, headers=HEADERS)
        assert response.status_code in {401, 403, 502, 503}, (user_state, path, response.text)
        assert response.status_code != 500, (user_state, path, response.text)


@pytest.mark.parametrize(
    ("identity", "expected_error", "expected_calendar_ready"),
    [("app", None, True), ("user", "credential_unreadable", False)],
)
def test_r3_04_status_scopes_corrupt_user_slot_to_selected_identity(
    tmp_path, monkeypatch, identity, expected_error, expected_calendar_ready
):
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(), corrupt_user=True)
    remote = IdentityRemote()
    client = _identity_client(tmp_path, monkeypatch, store, remote)

    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"identity": identity}},
        ).status_code
        == 200
    )
    response = client.get("/api/v1/integrations/feishu/status", headers=HEADERS)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authorized"] is False, body
    assert body["app_configured"] is True, body
    assert body["credential_error"] == expected_error, body
    assert body["calendar_ready"] is expected_calendar_ready, body
    if identity == "app":
        assert store.user_reads == 0, store.user_reads
    else:
        assert store.user_reads > 0, store.user_reads
    assert "synthetic-access" not in response.text


# --- R3 combination regressions ---------------------------------------------


def test_r3_combo_config_switch_refresh_logout_and_new_authorization(tmp_path):
    """All four state changes interact: the newest authorization must survive."""
    entered, release = Event(), Event()
    store = InstrumentedStore(app=_app_credentials(), user=_user_token(expires_in=5))
    provider = ServiceRemote(
        tmp_path / "remote",
        refresh_gate=(entered, release),
        exchange_access="synthetic-access-final",
        exchange_refresh="synthetic-refresh-final",
        exchange_scopes=[SEARCH_SCOPE],
    )
    client = _client(tmp_path, store, provider)

    thread, box = _parallel(client.get, "/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert entered.wait(10), "refresh never entered the remote"

    # 1. configuration switch, 2. logout, 3. a fresh authorization
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-z"}}
        ).status_code
        == 200
    )
    assert (
        client.delete("/api/v1/integrations/feishu/authorizations", headers=HEADERS).status_code
        == 204
    )
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    state = parse_qs(urlsplit(issued.json()["authorization_url"]).query)["state"][0]
    assert (
        client.get(CALLBACK, params={"state": state, "code": "synthetic-code"}).status_code == 200
    )

    release.set()
    try:
        _join(thread, box)
    except FeishuError:
        pass

    assert provider.refresh_calls == 1, provider.refresh_calls
    assert store.user is not None
    assert store.user.access_token == "synthetic-access-final"
    assert store.user.refresh_token == "synthetic-refresh-final"
    status = client.get("/api/v1/integrations/feishu/status", headers=HEADERS).json()
    assert status["authorized"] is True
    assert status["mode"] == "real"


def test_r3_combo_multi_request_read_with_a_mid_operation_timeout_and_config_switch(
    tmp_path, monkeypatch
):
    """A timeout in the middle of a multi-item read does not corrupt the rest."""
    remote = PausingRemote(pause_path="/transcript", pause_at=2, error_on_body_call=2)
    client, holder = _lease_client(tmp_path, monkeypatch, remote)
    _patch_calendar(client, "cal-a")
    old_client = holder["client"]
    materials = ["obc" + "0" * 21, "obc" + "1" * 21, "obc" + "2" * 21]

    thread, box = _parallel(
        client.post,
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": materials, "operation_id": "imp-combo"},
    )
    assert remote.entered.wait(10), "import never reached the second body step"

    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"calendar_id": "cal-b"}}
        ).status_code
        == 200
    )
    assert old_client.close_calls == 0
    remote.release.set()
    result = _join(thread, box)

    assert result.status_code == 200, result.text
    body = result.json()
    assert body["state"] == "partial", body
    states = {row["material_id"]: row["state"] for row in body["outcomes"]}
    assert states[materials[0]] == "succeeded", states
    assert states[materials[1]] == "failed", states
    assert states[materials[2]] == "succeeded", states
    failed = next(row for row in body["outcomes"] if row["material_id"] == materials[1])
    assert failed["error_code"] == "provider_timeout", failed
    assert old_client.close_calls == 1, old_client.close_calls
