"""R2 regressions for the Stage B follow-up review findings (synthetic only).

Each test is written to fail on the round-1 tree and pass after the R2 fix.
Only ``httpx.MockTransport``, in-memory backends, stub providers and synthetic
workspaces are used. No real provider, Keychain item or business data is touched.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from authorized_feishu_client import AuthorizedFeishuReadClient
from fastapi.testclient import TestClient
from pydantic import SecretStr

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    FeishuConfig,
    FeishuError,
    UserCredentials,
)
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-r2-session"}
APP_ID = "cli_synthetic_r2_app"
CALLBACK = "http://localhost:8765/callback"


class StubCredentialStore:
    """Holds synthetic app + user credentials; never touches a real keychain."""

    def __init__(
        self,
        user: UserCredentials | None = None,
        app: AppCredentials | None = None,
    ) -> None:
        self.user = user
        self.app = app

    def get(self) -> UserCredentials | None:
        return self.user

    def put(self, credentials: UserCredentials) -> None:
        self.user = credentials

    def delete(self) -> None:
        self.user = None

    def get_app(self) -> AppCredentials | None:
        return self.app

    def put_app(self, credentials: AppCredentials) -> None:
        self.app = credentials


def _user_token(scopes: list[str]) -> UserCredentials:
    return UserCredentials(
        access_token="synthetic-user-access",
        refresh_token="synthetic-user-refresh",
        expires_at=4_000_000_000,
        scopes=scopes,
    )


def _app_credentials() -> AppCredentials:
    return AppCredentials(app_id=APP_ID, app_secret=SecretStr("synthetic-app-secret"))


class RecordingFake(FakeFeishu):
    """FakeFeishu plus provider-call counters for absolute-zero write assertions."""

    def __init__(self, remote: Path, store: StubCredentialStore) -> None:
        super().__init__(remote)
        self.store = store
        self.calls: dict[str, int] = {}

    def _count(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    def task_create(self, credentials, body):  # type: ignore[no-untyped-def]
        self._count("task_create")
        return super().task_create(credentials, body)

    def task_patch(self, credentials, guid, body, token):  # type: ignore[no-untyped-def]
        self._count("task_patch")
        return super().task_patch(credentials, guid, body, token)

    def exchange(self, code, redirect_uri, app_credentials=None):  # type: ignore[no-untyped-def]
        self._count("exchange")
        return super().exchange(code, redirect_uri, app_credentials)

    def refresh(self, credentials):  # type: ignore[no-untyped-def]
        self._count("refresh")
        return super().refresh(credentials)

    def body(self, credentials, material_id):  # type: ignore[no-untyped-def]
        self._count("body")
        return super().body(credentials, material_id)

    def calendar(self, credentials, start, end, timezone, cursor, limit):  # type: ignore[no-untyped-def]
        self._count("calendar")
        return super().calendar(credentials, start, end, timezone, cursor, limit)

    def materials(self, credentials, query, visibility, cursor, limit):  # type: ignore[no-untyped-def]
        self._count("materials")
        return super().materials(credentials, query, visibility, cursor, limit)


def _client(
    tmp_path: Path,
    *,
    user_scopes: list[str] | None = None,
    with_app: bool = True,
) -> tuple[TestClient, RecordingFake, StubCredentialStore]:
    store = StubCredentialStore(
        user=_user_token(user_scopes or ["task:task:read", "task:task:write"]),
        app=_app_credentials() if with_app else None,
    )
    provider = RecordingFake(tmp_path / "synthetic-remote", store)
    app = create_app(
        session_token="synthetic-r2-session",
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
            "name": "Synthetic R2",
            "operation_id": "open",
        },
    )
    assert response.status_code == 201, response.text
    return client, provider, store


def _configure_real(client: TestClient, *, real_data: bool = True) -> None:
    response = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "mode": "real",
            "feishu": {"app_id": APP_ID, "redirect_uri": CALLBACK, "real_data_enabled": real_data},
        },
    )
    assert response.status_code == 200, response.text


def _propose(client: TestClient, kind: str = "feishu_task_create", payload=None) -> dict:
    response = client.post(
        "/api/v1/actions",
        headers=HEADERS,
        json={
            "action_id": str(uuid4()),
            "kind": kind,
            "payload": payload or {"summary": "合成任务", "due": None},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _confirm(client: TestClient, action: dict) -> dict:
    response = client.post(
        f"/api/v1/actions/{action['action_id']}/confirmations",
        headers=HEADERS,
        json={"payload_sha256": action["payload_sha256"], "confirmation_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _execute(client: TestClient, action: dict):
    return client.post(
        f"/api/v1/actions/{action['action_id']}/executions",
        headers=HEADERS,
        json={
            "payload_sha256": action["payload_sha256"],
            "confirmation_id": action["confirmation_id"],
        },
    )


def _confirm_and_execute(client: TestClient, action: dict):
    return _execute(client, _confirm(client, action))


# --- R2-01: real task writes stay disabled ---------------------------------


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("feishu_task_create", {"summary": "合成任务", "due": None}),
        (
            "feishu_task_update",
            {
                "task_guid": "task-synthetic-1",
                "task": {"summary": "合成改名"},
                "update_fields": ["summary"],
            },
        ),
        ("feishu_task_complete", {"task_guid": "task-synthetic-1"}),
    ],
)
def test_r2_01_real_task_write_is_rejected_and_never_calls_the_provider(tmp_path, kind, payload):
    client, provider, _store = _client(tmp_path)
    _configure_real(client, real_data=True)

    action = _propose(client, kind, payload)
    response = _confirm_and_execute(client, action)

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "result_proof_unavailable"
    # The provider must never have been asked to write.
    assert provider.calls.get("task_create", 0) == 0
    assert provider.calls.get("task_patch", 0) == 0
    assert provider.calls.get("exchange", 0) == 0
    assert provider.calls.get("refresh", 0) == 0


def test_r2_01_task_write_capability_summary_matches_the_route(tmp_path):
    client, _provider, _store = _client(tmp_path)
    _configure_real(client, real_data=True)
    assert (
        client.put(
            "/api/v1/credentials/feishu_app",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": "synthetic-app-secret"},
        ).status_code
        == 200
    )

    capabilities = client.get("/api/v1/settings", headers=HEADERS).json()["capabilities"]
    assert capabilities["feishu_task_write"]["available"] is False
    assert capabilities["feishu_task_write"]["disabled_reason"] == "result_proof_unavailable"
    assert capabilities["feishu_task_read"]["available"] is False
    assert capabilities["feishu_task_read"]["disabled_reason"] == "acceptance_plan_required"


def test_r2_01_local_progress_action_is_not_blocked_by_the_read_gate(tmp_path):
    client, _provider, _store = _client(tmp_path)
    _configure_real(client, real_data=False)

    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "合成线", "operation_id": "l1"}
    )
    assert line.status_code == 201, line.text
    ws = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line.json()["id"], "name": "合成项目", "operation_id": "p1"},
    )
    assert ws.status_code == 201, ws.text
    project_id = ws.json()["id"]

    action = _propose(
        client,
        "project_progress",
        {"project_id": project_id, "expected_version": 0, "progress": "合成进展"},
    )
    response = _confirm_and_execute(client, action)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "succeeded"


def test_r2_01_fake_task_flow_keeps_working(tmp_path):
    client, provider, _store = _client(tmp_path)
    # Default mode is fake; no real data gate applies.
    action = _propose(client)
    response = _confirm_and_execute(client, action)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "succeeded"
    assert provider.calls.get("task_create", 0) == 1


# --- R2-02: application identity must be usable through the service layer ---

import httpx  # noqa: E402

import summit_everything.api.app as app_module  # noqa: E402
from summit_everything.integrations.feishu.http import FeishuHttpProvider  # noqa: E402

TENANT = "/open-apis/auth/v3/tenant_access_token/internal"
PRIMARY = "/open-apis/calendar/v4/calendars/primary"
EVENTS = "/open-apis/calendar/v4/calendars/cal-explicit/events"
TRANSCRIPT = "/open-apis/minutes/v1/minutes/obc" + "0" * 21 + "/transcript"


class FeishuStub:
    """Official-shaped MockTransport responses with a request log."""

    def __init__(self) -> None:
        self.paths: list[str] = []
        self.auth: list[str] = []
        self.urls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        self.auth.append(request.headers.get("authorization", ""))
        self.urls.append(str(request.url))
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == PRIMARY:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"calendars": [{"calendar": {"calendar_id": "cal-explicit"}}]},
                },
            )
        if path == EVENTS:
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        if path == TRANSCRIPT:
            return httpx.Response(200, content=b"synthetic transcript")
        return httpx.Response(404, json={"code": 99991672, "msg": "synthetic unexpected path"})


def _real_client(
    tmp_path: Path,
    monkeypatch,
    *,
    calendar_id: str = "cal-explicit",
    stub: FeishuStub | None = None,
):
    stub = stub or FeishuStub()

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        return FeishuHttpProvider(
            config,
            app_credentials,
            client=httpx.Client(
                transport=httpx.MockTransport(stub.handler), follow_redirects=False
            ),
            **kwargs,
        )

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r2-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R2",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    response = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "mode": "real",
            "feishu": {
                "app_id": APP_ID,
                "redirect_uri": CALLBACK,
                "real_data_enabled": True,
                "identity": "app",
                "calendar_id": calendar_id,
            },
        },
    )
    assert response.status_code == 200, response.text
    assert (
        client.put(
            "/api/v1/credentials/feishu_app",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": "synthetic-app-secret"},
        ).status_code
        == 200
    )
    return client, stub


def _no_user_flow_requests(stub: FeishuStub) -> None:
    assert not any("/authen/v1/user_info" in p for p in stub.paths), stub.paths
    assert not any("oauth/token" in p for p in stub.paths), stub.paths


def test_r2_02_calendar_with_only_app_secret_reaches_the_calendar_endpoint(tmp_path, monkeypatch):
    client, stub = _real_client(tmp_path, monkeypatch)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert response.status_code == 200, response.text
    assert TENANT in stub.paths and EVENTS in stub.paths, stub.paths
    _no_user_flow_requests(stub)


def test_r2_02_selected_body_uses_application_identity(tmp_path, monkeypatch):
    client, stub = _real_client(tmp_path, monkeypatch)
    material = "obc" + "0" * 21
    response = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": [material], "operation_id": "imp-1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "succeeded", response.text
    assert TENANT in stub.paths and TRANSCRIPT in stub.paths, stub.paths
    _no_user_flow_requests(stub)


def test_r2_02_search_and_task_list_still_require_user_authorization(tmp_path, monkeypatch):
    client, stub = _real_client(tmp_path, monkeypatch)
    assert client.get("/api/v1/integrations/feishu/materials", headers=HEADERS).status_code == 401
    assert client.get("/api/v1/integrations/feishu/tasks", headers=HEADERS).status_code == 401
    # A missing user token must not trigger any token exchange or refresh attempt.
    assert stub.paths == [], stub.paths


def test_r2_02_missing_app_secret_is_reported_distinctly(tmp_path, monkeypatch):
    client, stub = _real_client(tmp_path, monkeypatch)
    removed = client.request(
        "DELETE",
        "/api/v1/credentials/feishu_app",
        headers=HEADERS,
        json={"account_id": APP_ID},
    )
    assert removed.status_code == 204, removed.text
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


# --- R2-03: official primary-calendar response shape ------------------------


class PrimaryStub(FeishuStub):
    """Primary-calendar stub with a configurable official-shaped payload."""

    def __init__(self, payload) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.payload = payload

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == PRIMARY:
            self.paths.append(request.url.path)
            self.auth.append(request.headers.get("authorization", ""))
            return httpx.Response(200, json=self.payload)
        return super().handler(request)


def _calendar_request(client: TestClient):
    return client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )


def test_r2_03_official_primary_calendar_shape_is_accepted(tmp_path, monkeypatch):
    payload = {
        "code": 0,
        "msg": "success",
        "data": {
            "calendars": [
                {
                    "calendar": {
                        "calendar_id": "cal-explicit",
                        "summary": "合成日历",
                        "type": "shared",
                        "role": "owner",
                        "is_deleted": False,
                    },
                    "user_id": "ou_synthetic",
                }
            ]
        },
    }
    client, stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 200, response.text
    assert PRIMARY in stub.paths and EVENTS in stub.paths, stub.paths


def test_r2_03_explicit_calendar_id_skips_the_primary_lookup(tmp_path, monkeypatch):
    client, stub = _real_client(tmp_path, monkeypatch, calendar_id="cal-explicit")
    response = _calendar_request(client)
    assert response.status_code == 200, response.text
    assert PRIMARY not in stub.paths, stub.paths
    assert EVENTS in stub.paths, stub.paths


def test_r2_03_empty_primary_calendar_is_reported(tmp_path, monkeypatch):
    payload = {"code": 0, "msg": "success", "data": {"calendars": []}}
    client, _stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "no_primary_calendar"


def test_r2_03_ambiguous_primary_calendar_is_refused(tmp_path, monkeypatch):
    def entry(calendar_id: str, user_id: str) -> dict:
        return {"calendar": {"calendar_id": calendar_id}, "user_id": user_id}

    payload = {
        "code": 0,
        "data": {"calendars": [entry("cal-a", "ou_a"), entry("cal-b", "ou_b")]},
    }
    client, _stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ambiguous_calendar"


def test_r2_03_deleted_calendar_is_not_selected(tmp_path, monkeypatch):
    payload = {
        "code": 0,
        "data": {
            "calendars": [
                {"calendar": {"calendar_id": "cal-deleted", "is_deleted": True}},
            ]
        },
    }
    client, _stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "no_primary_calendar"


@pytest.mark.parametrize(
    "payload",
    [
        {"code": 0, "data": {"calendars": [{"calendar": {"summary": "no id"}}]}},
        {"code": 0, "data": {"calendars": [{"calendar": {"calendar_id": 42}}]}},
        {"code": 0, "data": {"calendars": "not-a-list"}},
        {"code": 0, "data": {}},
    ],
)
def test_r2_03_malformed_primary_calendar_is_rejected(tmp_path, monkeypatch, payload):
    client, _stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "malformed_response"


def test_r2_03_primary_permission_error_is_surfaced(tmp_path, monkeypatch):
    payload = {"code": 99991672, "msg": "synthetic permission denied"}
    client, _stub = _real_client(tmp_path, monkeypatch, calendar_id="", stub=PrimaryStub(payload))
    response = _calendar_request(client)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "missing_scope"


# --- R2-04: settings changes must reach the execution path ------------------

ARTIFACTS_SUFFIX = "/artifacts"


class ConfigStub(FeishuStub):
    """Records paths and auth headers; serves both calendar ids and both bodies."""

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        self.auth.append(request.headers.get("authorization", ""))
        if path == TENANT:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path.startswith("/open-apis/calendar/v4/calendars/") and path.endswith("/events"):
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        if path.endswith("/transcript"):
            return httpx.Response(200, content=b"synthetic transcript")
        if path.endswith(ARTIFACTS_SUFFIX):
            return httpx.Response(200, json={"code": 0, "data": {"transcript": "合成逐字稿"}})
        return httpx.Response(404, json={"code": 99991672, "msg": "synthetic unexpected path"})


def _config_client(tmp_path: Path, monkeypatch, store: StubCredentialStore):
    stub = ConfigStub()

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        return FeishuHttpProvider(
            config,
            app_credentials,
            client=httpx.Client(
                transport=httpx.MockTransport(stub.handler), follow_redirects=False
            ),
            **kwargs,
        )

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r2-session",
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
                "name": "Synthetic R2",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    return client, stub


def _patch_feishu(client: TestClient, **feishu):
    response = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={"mode": "real", "feishu": {"app_id": APP_ID, "redirect_uri": CALLBACK, **feishu}},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _calendar_paths(stub: ConfigStub) -> list[str]:
    return [p for p in stub.paths if p.endswith("/events")]


def test_r2_04_identity_calendar_and_body_mode_change_take_effect_immediately(
    tmp_path, monkeypatch
):
    store = StubCredentialStore(
        user=_user_token(
            [
                "minutes:minutes.search:read",
                "minutes:minutes.transcript:export",
                "minutes:minutes.artifacts:read",
                "calendar:calendar.event:read",
                "task:task:read",
            ]
        ),
        app=_app_credentials(),
    )
    client, stub = _config_client(tmp_path, monkeypatch, store)
    _patch_feishu(
        client,
        real_data_enabled=True,
        identity="app",
        calendar_id="cal-a",
        material_content="transcript",
    )

    assert _calendar_request(client).status_code == 200
    assert _calendar_paths(stub)[-1].startswith("/open-apis/calendar/v4/calendars/cal-a/")

    import_response = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "0" * 21], "operation_id": "imp-a"},
    )
    assert import_response.status_code == 200, import_response.text
    assert stub.paths[-1].endswith("/transcript"), stub.paths

    _patch_feishu(
        client,
        real_data_enabled=True,
        identity="user",
        calendar_id="cal-b",
        material_content="artifacts",
    )

    assert _calendar_request(client).status_code == 200
    assert _calendar_paths(stub)[-1].startswith("/open-apis/calendar/v4/calendars/cal-b/"), (
        stub.paths
    )
    # identity=user must send the user token, not a fresh tenant token
    assert stub.auth[-1] == "Bearer synthetic-user-access", stub.auth[-1]

    second_import = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "1" * 21], "operation_id": "imp-b"},
    )
    assert second_import.status_code == 200, second_import.text
    assert stub.paths[-1].endswith(ARTIFACTS_SUFFIX), stub.paths


def test_r2_04_pending_oauth_state_is_not_accepted_by_a_new_configuration(tmp_path, monkeypatch):
    store = StubCredentialStore(app=_app_credentials())
    client, _stub = _config_client(tmp_path, monkeypatch, store)
    _patch_feishu(
        client, real_data_enabled=True, calendar_id="cal-a", material_content="transcript"
    )

    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    assert issued.status_code == 200, issued.text
    url = issued.json()["authorization_url"]

    _patch_feishu(client, real_data_enabled=True, calendar_id="cal-b", material_content="artifacts")

    from urllib.parse import parse_qs, urlsplit

    state = parse_qs(urlsplit(url).query)["state"][0]
    # The callback must keep the registered loopback URI.
    callback = client.get(
        "http://localhost:8765/callback",
        params={"state": state, "code": "synthetic-code"},
    )
    assert callback.status_code == 400, callback.text
    assert callback.json()["error"]["code"] == "invalid_state"


def test_r2_04_refresh_is_coordinated_across_rebuilt_services(tmp_path):
    """A rebuilt service must not consume a single-use refresh token twice."""
    import time
    from threading import Event, Lock, Thread

    from summit_everything.integrations.feishu.provider import FeishuConfig
    from summit_everything.integrations.feishu.service import FeishuService

    entered, release = Event(), Event()

    class RacingFake(FakeFeishu):
        count = 0

        def refresh(self, credentials):  # type: ignore[no-untyped-def]
            self.count += 1
            if self.count == 1:
                entered.set()
                assert release.wait(5)
            return UserCredentials(
                access_token="synthetic-access-rotated",
                refresh_token="synthetic-refresh-rotated",
                expires_at=time.time() + 3600,
                scopes=credentials.scopes,
            )

    store = StubCredentialStore(
        user=UserCredentials(
            access_token="synthetic-access-old",
            refresh_token="synthetic-refresh-old",
            expires_at=time.time() + 30,  # inside the 60 s refresh window
            scopes=["minutes:read"],
        ),
        app=_app_credentials(),
    )
    provider = RacingFake(tmp_path / "synthetic-remote")
    shared_lock = Lock()
    first = FeishuService(provider, store, FeishuConfig(), "session-a", refresh_lock=shared_lock)
    second = FeishuService(provider, store, FeishuConfig(), "session-b", refresh_lock=shared_lock)

    results: list[object] = []

    def run(service) -> None:  # type: ignore[no-untyped-def]
        results.append(service.materials("", None, None, 10))

    thread_a = Thread(target=run, args=(first,))
    thread_a.start()
    assert entered.wait(5)
    thread_b = Thread(target=run, args=(second,))
    thread_b.start()
    time.sleep(0.2)
    release.set()
    thread_a.join(10)
    thread_b.join(10)

    assert provider.count == 1, provider.count
    assert store.get().refresh_token == "synthetic-refresh-rotated"
    assert len(results) == 2


def test_r2_04_retired_provider_closes_only_after_its_last_inflight_call(tmp_path):
    from threading import Event, Thread

    from summit_everything.integrations.feishu.http import FeishuHttpProvider
    from summit_everything.integrations.feishu.provider import FeishuConfig

    entered, release = Event(), Event()

    class BlockingStream(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            entered.set()
            assert release.wait(5)
            yield b'{"code":0,"data":{"items":[]}}'

    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: _app_credentials(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, stream=BlockingStream())
            )
        ),
    )
    outcome: list[object] = []

    def call() -> None:
        outcome.append(provider.materials(_user_token(["minutes:read"]), "", None, None, 10))

    worker = Thread(target=call)
    worker.start()
    assert entered.wait(5)
    provider.retire()
    assert provider.closed is False  # an in-flight call must not be cut off
    release.set()
    worker.join(10)
    assert provider.closed is True

    idle = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: _app_credentials(),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"code": 0}))
        ),
    )
    idle.retire()
    assert idle.closed is True
    from summit_everything.integrations.feishu.provider import FeishuError

    with pytest.raises(FeishuError) as error:
        idle.materials(_user_token(["minutes:read"]), "", None, None, 10)
    assert error.value.code == "provider_unavailable"


# --- R2-05: calendar limit vs upstream cap and truncation -------------------


class CalendarStub(FeishuStub):
    def __init__(self, count: int, *, has_more: bool = False, malformed_index: int = -1) -> None:
        super().__init__()
        self.count = count
        self.has_more = has_more
        self.malformed_index = malformed_index

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == EVENTS:
            self.paths.append(request.url.path)
            self.auth.append(request.headers.get("authorization", ""))
            self.urls.append(str(request.url))
            items = []
            for index in range(self.count):
                if index == self.malformed_index:
                    items.append({"event_id": "evt-bad", "start_time": 5})
                    continue
                items.append(
                    {
                        "event_id": f"evt-{index}",
                        "summary": f"合成日程 {index}",
                        "start_time": {"timestamp": "1602504000", "timezone": "Asia/Shanghai"},
                        "end_time": {"timestamp": "1602507600", "timezone": "Asia/Shanghai"},
                    }
                )
            body: dict = {"code": 0, "data": {"items": items}}
            if self.has_more:
                body["data"]["has_more"] = True
                body["data"]["page_token"] = "upstream-page-2"
            return httpx.Response(200, json=body)
        return super().handler(request)


def _calendar_client(tmp_path, monkeypatch, stub: CalendarStub):
    return _real_client(tmp_path, monkeypatch, calendar_id="cal-explicit", stub=stub)


@pytest.mark.parametrize(
    "count,limit,expected_items,expected_truncated",
    [
        (0, 20, 0, False),
        (20, 20, 20, False),
        (21, 20, 20, True),
        (50, 30, 30, True),
        (5, 1, 1, True),
        (1, 1, 1, False),
        (3, 30, 3, False),
    ],
)
def test_r2_05_calendar_returns_at_most_limit_and_reports_truncation(
    tmp_path, monkeypatch, count, limit, expected_items, expected_truncated
):
    stub = CalendarStub(count)
    client, _stub = _calendar_client(tmp_path, monkeypatch, stub)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "limit": limit,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == expected_items, body
    assert body["truncated"] is expected_truncated, body
    # A real explicit range can never offer a usable next-page cursor.
    assert body["next_cursor"] is None, body


def test_r2_05_upstream_has_more_reports_truncation(tmp_path, monkeypatch):
    stub = CalendarStub(3, has_more=True)
    client, _stub = _calendar_client(tmp_path, monkeypatch, stub)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "limit": 20,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["truncated"] is True
    assert response.json()["next_cursor"] is None


def test_r2_05_malformed_item_is_still_rejected(tmp_path, monkeypatch):
    stub = CalendarStub(21, malformed_index=7)
    client, _stub = _calendar_client(tmp_path, monkeypatch, stub)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "limit": 20,
        },
    )
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "malformed_response"


def test_r2_05_explicit_range_never_paginates(tmp_path, monkeypatch):
    stub = CalendarStub(50)
    client, _stub = _calendar_client(tmp_path, monkeypatch, stub)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "limit": 20,
        },
    )
    assert response.status_code == 200, response.text
    # Exactly one upstream range request: no auto expansion or extra paging.
    assert stub.paths.count(EVENTS) == 1, stub.paths


def test_r2_05_upstream_page_size_respects_the_documented_minimum(tmp_path, monkeypatch):
    stub = CalendarStub(0)
    client, _stub = _calendar_client(tmp_path, monkeypatch, stub)
    response = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=HEADERS,
        params={
            "start": "2026-10-09T00:00:00+08:00",
            "end": "2026-10-10T00:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "limit": 5,
        },
    )
    assert response.status_code == 200, response.text
    events_url = next(url for url in stub.urls if "/events" in url)
    assert "page_size=50" in events_url, events_url


# --- Status and source attribution -----------------------------------------


def test_status_reports_the_actual_mode_and_separates_app_from_user(tmp_path, monkeypatch):
    store = StubCredentialStore(app=_app_credentials(), user=None)
    client, _stub = _config_client(tmp_path, monkeypatch, store)
    _patch_feishu(
        client, real_data_enabled=True, calendar_id="cal-a", material_content="transcript"
    )

    status = client.get("/api/v1/integrations/feishu/status", headers=HEADERS).json()
    assert status["mode"] == "real", status
    assert status["authorized"] is False, status
    assert status["app_configured"] is True, status
    assert status["token_type"] == "user"
    assert status["scopes"] == []


def test_status_in_fake_mode_is_labelled_fake(tmp_path, monkeypatch):
    store = StubCredentialStore(app=_app_credentials())
    client, _stub = _config_client(tmp_path, monkeypatch, store)
    status = client.get("/api/v1/integrations/feishu/status", headers=HEADERS).json()
    assert status["mode"] == "fake", status
    assert status["app_configured"] is False, status


def test_real_import_source_is_not_labelled_fake(tmp_path, monkeypatch):
    store = StubCredentialStore(app=_app_credentials())
    client, stub = _config_client(tmp_path, monkeypatch, store)
    _patch_feishu(
        client, real_data_enabled=True, calendar_id="cal-a", material_content="transcript"
    )

    response = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["obc" + "0" * 21], "operation_id": "imp-real"},
    )
    assert response.status_code == 200, response.text
    assert stub.paths[-1].endswith("/transcript")
    items = client.get("/api/v1/intake/items", headers=HEADERS).json()
    source = client.get(f"/api/v1/sources/{items[0]['source_id']}", headers=HEADERS).json()
    identity = source["source"]["external_identity"]
    assert identity["provider"] == "feishu", identity
    assert identity["token_type"] == "app", identity


def test_fake_import_source_is_labelled_fake(tmp_path, monkeypatch):
    store = StubCredentialStore(user=_user_token(["minutes:read", "calendar:read"]))
    client, _stub = _config_client(tmp_path, monkeypatch, store)
    # Fake mode uses the simulated provider with its own synthetic material ids.
    response = client.post(
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": ["minute-1"], "operation_id": "imp-fake"},
    )
    assert response.status_code == 200, response.text
    items = client.get("/api/v1/intake/items", headers=HEADERS).json()
    source = client.get(f"/api/v1/sources/{items[0]['source_id']}", headers=HEADERS).json()
    identity = source["source"]["external_identity"]
    assert identity["provider"] == "feishu-fake", identity
    assert identity["token_type"] == "user", identity


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {"access_token": "a", "scope": "task:task:read", "refresh_token": "r"},
            "malformed_response",
        ),
        ({"access_token": "a", "expires_in": 7200, "refresh_token": "r"}, "malformed_response"),
        (
            {
                "access_token": "a",
                "expires_in": 7200,
                "scope": "task:task:read",
                "refresh_token": "r",
                "token_type": "mac",
            },
            "malformed_response",
        ),
        ({"access_token": "a", "expires_in": 0, "scope": "task:task:read"}, "malformed_response"),
        (
            {
                "access_token": "a",
                "expires_in": 7200,
                "scope": "task:task:read",
                "token_type": "Bearer",
            },
            "missing_scope",
        ),
    ],
)
def test_oauth_exchange_rejects_missing_documented_fields(tmp_path, payload, expected):
    """A token response must carry expires_in, an effective scope and Bearer."""
    from summit_everything.integrations.feishu.http import TOKEN_PATH, FeishuHttpProvider

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TOKEN_PATH
        return httpx.Response(200, json={"code": 0, **payload})

    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: _app_credentials(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(FeishuError) as error:
        provider.exchange("synthetic-code", CALLBACK)
    assert error.value.code == expected, error.value.code


def test_oauth_exchange_accepts_the_documented_success_shape(tmp_path):
    from summit_everything.integrations.feishu.http import TOKEN_PATH, FeishuHttpProvider

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TOKEN_PATH
        return httpx.Response(
            200,
            json={
                "code": 0,
                "access_token": "synthetic-access",
                "refresh_token": "synthetic-refresh",
                "expires_in": 7200,
                "scope": "offline_access task:task:read",
                "token_type": "Bearer",
            },
        )

    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: _app_credentials(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    credentials = provider.exchange("synthetic-code", CALLBACK)
    assert credentials.scopes == ["offline_access", "task:task:read"]
    assert credentials.expires_at > 0


def test_oauth_refresh_keeps_rotation_and_rejects_invented_values(tmp_path):
    from summit_everything.integrations.feishu.http import TOKEN_PATH, FeishuHttpProvider

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TOKEN_PATH
        return httpx.Response(
            200,
            json={
                "code": 0,
                "access_token": "synthetic-rotated",
                "refresh_token": "synthetic-rotated-refresh",
                "expires_in": 3600,
                "scope": "offline_access task:task:read",
                "token_type": "Bearer",
            },
        )

    provider = FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: _app_credentials(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    rotated = provider.refresh(_user_token(["offline_access", "task:task:read"]))
    assert rotated.refresh_token == "synthetic-rotated-refresh"
    assert rotated.access_token == "synthetic-rotated"
