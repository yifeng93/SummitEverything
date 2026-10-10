from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app

PREFIX = "/api/v1/integrations/feishu"


def client(tmp_path: Path) -> TestClient:
    app = create_app(session_token="local-test-session", profile_root=tmp_path / "profiles")
    c = TestClient(
        app,
        base_url="http://127.0.0.1:5173",
        headers={"Authorization": "Bearer local-test-session"},
    )
    assert (
        c.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "name": "模拟",
                "mode": "create",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    return c


def authorize(c: TestClient) -> str:
    response = c.post(PREFIX + "/authorizations", json={})
    assert response.status_code == 200
    url = response.json()["authorization_url"]
    callback = urlsplit(url)
    result = c.get(callback.path + "?" + callback.query, headers={"Authorization": ""})
    assert result.status_code == 200
    assert result.json()["authorized"] is True
    return parse_qs(callback.query)["state"][0]


def test_fake_default_authorization_and_selected_only_import(tmp_path: Path) -> None:
    c = client(tmp_path)
    response = c.get(PREFIX + "/status")
    assert response.status_code == 200
    assert response.json() == {
        "mode": "fake",
        "authorized": False,
        "token_type": "user",
        "scopes": [],
    }
    authorize(c)
    first = c.get(PREFIX + "/materials", params={"limit": 1}).json()
    assert len(first["items"]) == 1 and first["next_cursor"]
    second = c.get(
        PREFIX + "/materials", params={"cursor": first["next_cursor"], "limit": 1}
    ).json()
    assert len(second["items"]) == 1
    assert c.get(PREFIX + "/materials", params={"query": "no-matches"}).json()["items"] == []
    assert c.get("/api/v1/intake/items").json() == []
    payload = {"material_ids": [first["items"][0]["material_id"]], "operation_id": "import-one"}
    imported = c.post(PREFIX + "/imports", json=payload)
    assert imported.status_code == 200
    assert imported.json()["state"] == "succeeded"
    assert c.post(PREFIX + "/imports", json=payload).json() == imported.json()
    assert (
        c.post(PREFIX + "/imports", json={**payload, "material_ids": ["minute-2"]}).status_code
        == 409
    )
    items = c.get("/api/v1/intake/items").json()
    assert len(items) == 1 and items[0]["state"] == "pending"
    assert items[0]["title"] == "模拟会议"
    source = c.get("/api/v1/sources/" + items[0]["source_id"]).json()
    raw = (tmp_path / "workspace" / items[0]["original_relative_path"]).read_bytes()
    assert raw == "模拟会议：等待用户确认。\r\n".encode()
    assert source["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert source["source"]["external_identity"]["material_id"] == "minute-1"
    assert c.get("/api/v1/drafts").json() == []
    assert c.get("/api/v1/pages").json() == []
    assert c.app.state.review_service.provider.calls == 0


def test_oauth_invalid_replay_origin_and_cross_run(tmp_path: Path) -> None:
    c = client(tmp_path)
    state = authorize(c)
    assert (
        c.get(PREFIX + "/callback", params={"state": state, "code": "fake-ok"}).status_code == 400
    )
    for state_value in ["", "fabricated", "../invalid"]:
        assert (
            c.get(
                PREFIX + "/callback", params={"state": state_value, "code": "fake-ok"}
            ).status_code
            == 400
        )
    assert c.get(PREFIX + "/callback").status_code == 422
    assert (
        c.post(
            PREFIX + "/authorizations", json={}, headers={"Origin": "https://attacker.invalid"}
        ).status_code
        == 403
    )
    fresh = c.post(PREFIX + "/authorizations", json={}).json()["authorization_url"]
    other = TestClient(create_app(session_token="other"), base_url="http://127.0.0.1:5173")
    assert other.get(urlsplit(fresh).path + "?" + urlsplit(fresh).query).status_code == 400
    for method, route, data in [
        ("GET", "/status", None),
        ("POST", "/authorizations", {}),
        ("DELETE", "/authorizations", None),
        ("GET", "/materials", None),
        ("POST", "/imports", {}),
        ("GET", "/calendar", None),
    ]:
        assert (
            c.request(method, PREFIX + route, json=data, headers={"Authorization": ""}).status_code
            == 401
        )


def test_denied_authorization_never_reports_success(tmp_path: Path) -> None:
    c = client(tmp_path)
    url = urlsplit(c.post(PREFIX + "/authorizations", json={}).json()["authorization_url"])
    state = parse_qs(url.query)["state"][0]
    denied = c.get(PREFIX + "/callback", params={"state": state, "error": "access_denied"})
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "authorization_denied"
    assert c.get(PREFIX + "/status").json()["authorized"] is False
    assert c.get(PREFIX + "/materials").status_code == 401


def test_user_api_refreshes_near_expiry_and_persists_rotated_refresh_token(tmp_path: Path) -> None:
    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.integrations.feishu.provider import (
        FeishuConfig,
        MemoryCredentialStore,
        UserCredentials,
    )
    from summit_everything.integrations.feishu.service import FeishuService

    class RotatingFake(FakeFeishu):
        refresh_input: UserCredentials | None = None

        def refresh(self, credentials: UserCredentials) -> UserCredentials:
            self.refresh_input = credentials
            return UserCredentials(
                access_token="synthetic-access-2",
                refresh_token="synthetic-refresh-2",
                expires_at=2000,
                scopes=credentials.scopes,
            )

    store = MemoryCredentialStore()
    store.put(
        UserCredentials(
            access_token="synthetic-access-1",
            refresh_token="synthetic-refresh-1",
            expires_at=1050,
            scopes=["minutes:read"],
        )
    )
    provider = RotatingFake(tmp_path / "remote")
    service = FeishuService(provider, store, FeishuConfig(), "session", clock=lambda: 1000)

    service.materials("", None, None, 10)

    assert provider.refresh_input is not None
    assert provider.refresh_input.refresh_token == "synthetic-refresh-1"
    assert store.get() is not None
    assert store.get().access_token == "synthetic-access-2"
    assert store.get().refresh_token == "synthetic-refresh-2"


def test_logout_clears_user_authorization(tmp_path: Path) -> None:
    c = client(tmp_path)
    authorize(c)

    response = c.delete(PREFIX + "/authorizations")

    assert response.status_code == 204
    assert c.get(PREFIX + "/status").json()["authorized"] is False
    assert c.get(PREFIX + "/materials").status_code == 401


def test_calendar_range_timezone_and_pagination(tmp_path: Path) -> None:
    c = client(tmp_path)
    authorize(c)
    params = {
        "start": "2026-10-09T00:00:00+08:00",
        "end": "2026-10-10T00:00:00+08:00",
        "timezone": "Asia/Shanghai",
        "limit": 1,
    }
    response = c.get(PREFIX + "/calendar", params=params)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1 and response.json()["next_cursor"]
    assert c.get(
        PREFIX + "/calendar", params={**params, "cursor": response.json()["next_cursor"]}
    ).json()["items"]
    assert c.get(PREFIX + "/calendar", params={**params, "timezone": "bad-zone"}).status_code == 422
    assert c.get(PREFIX + "/calendar", params={**params, "end": params["start"]}).status_code == 422
    assert (
        c.get(
            PREFIX + "/calendar",
            params={**params, "start": "2027-01-01T00:00:00Z", "end": "2027-01-02T00:00:00Z"},
        ).json()["items"]
        == []
    )
    assert c.get("/api/v1/intake/items").json() == []


@pytest.mark.parametrize(
    "material_id,code",
    [
        ("missing", "not_found"),
        ("scope", "missing_scope"),
        ("malformed", "malformed_response"),
        ("timeout", "provider_timeout"),
        ("unavailable", "provider_unavailable"),
    ],
)
def test_import_partial_failure_is_explicit_and_replayed(
    tmp_path: Path, material_id: str, code: str
) -> None:
    c = client(tmp_path)
    authorize(c)
    payload = {"operation_id": "partial", "material_ids": ["minute-1", material_id]}
    result = c.post(PREFIX + "/imports", json=payload)
    assert result.status_code == 200
    assert result.json()["state"] == "partial"
    assert (
        next(row for row in result.json()["outcomes"] if row["material_id"] == material_id)[
            "error_code"
        ]
        == code
    )
    assert len(c.get("/api/v1/intake/items").json()) == 1
    assert c.post(PREFIX + "/imports", json=payload).json() == result.json()


def test_expiry_missing_scope_and_safe_provider_errors(tmp_path: Path) -> None:
    c = client(tmp_path)
    authorize(c)
    service = c.app.state.feishu_service
    credentials = service.credentials.get()
    service.credentials.put(
        credentials.model_copy(update={"expires_at": 0, "refresh_token": "expired"})
    )
    assert c.get(PREFIX + "/materials").json()["error"]["code"] == "token_expired"
    assert c.get(PREFIX + "/status").json()["authorized"] is False
    authorize(c)
    credentials = service.credentials.get()
    service.credentials.put(credentials.model_copy(update={"scopes": []}))
    assert c.get(PREFIX + "/materials").json()["error"]["code"] == "missing_scope"
    assert (
        c.get(
            PREFIX + "/calendar",
            params={
                "start": "2026-10-09T00:00:00Z",
                "end": "2026-10-10T00:00:00Z",
                "timezone": "UTC",
            },
        ).json()["error"]["code"]
        == "missing_scope"
    )
    authorize(c)

    def broken(*args):
        raise RuntimeError("sensitive-token-do-not-expose")

    service.provider.materials = broken
    response = c.get(PREFIX + "/materials")
    assert response.status_code == 503
    assert "sensitive-token" not in response.text


def test_oauth_expiry_and_wrong_redirect(tmp_path: Path) -> None:
    c = client(tmp_path)
    service = c.app.state.feishu_service
    service.clock = lambda: 1000
    url = urlsplit(c.post(PREFIX + "/authorizations", json={}).json()["authorization_url"])
    service.clock = lambda: 1301
    assert c.get(url.path + "?" + url.query).json()["error"]["code"] == "invalid_state"
    url = urlsplit(c.post(PREFIX + "/authorizations", json={}).json()["authorization_url"])
    wrong = c.get("http://127.0.0.1:8793" + url.path + "?" + url.query)
    assert wrong.json()["error"]["code"] == "invalid_redirect"
    assert (
        c.get(url.path + "?" + url.query, headers={"Origin": "http://evil.invalid"}).status_code
        == 403
    )


@pytest.mark.parametrize(
    "raw,filename,content_type",
    [
        (b"bad", "../escape.txt", "text/plain"),
        (b"bad", "file.txt", "application/json"),
        (b"\xff", "file.txt", "text/plain"),
        (b"bad\x00", "file.txt", "text/plain"),
        (b"bad", "file.txt", "text/plain; charset=gbk"),
        (b"", "file.txt", "text/plain"),
        (b"x" * (20 * 1024 * 1024 + 1), "file.txt", "text/plain"),
    ],
)
def test_untrusted_body_boundary(
    tmp_path: Path, raw: bytes, filename: str, content_type: str
) -> None:
    from summit_everything.integrations.feishu.provider import MaterialBody

    c = client(tmp_path)
    authorize(c)
    c.app.state.feishu_service.provider.body = lambda *_: MaterialBody(
        raw=raw, filename=filename, content_type=content_type
    )
    response = c.post(
        PREFIX + "/imports", json={"material_ids": ["minute-1"], "operation_id": "invalid-body"}
    )
    assert response.json()["state"] == "failed"
    assert response.json()["outcomes"][0]["error_code"] == "malformed_response"
    assert c.get("/api/v1/intake/items").json() == []


def test_selected_body_calls_and_restart_replay(tmp_path: Path) -> None:
    c = client(tmp_path)
    authorize(c)
    provider = c.app.state.feishu_service.provider
    calls = []
    original = provider.body

    def tracked(credentials, material_id):
        calls.append(material_id)
        return original(credentials, material_id)

    provider.body = tracked
    assert (
        c.get(PREFIX + "/materials", params={"visibility": "shared"}).json()["items"][0][
            "material_id"
        ]
        == "minute-2"
    )
    assert calls == []
    payload = {"material_ids": ["minute-2"], "operation_id": "restart"}
    result = c.post(PREFIX + "/imports", json=payload).json()
    assert calls == ["minute-2"]
    c2 = client(tmp_path)
    assert c2.post(PREFIX + "/imports", json=payload).json() == result
    assert len(c2.get("/api/v1/intake/items").json()) == 1


def test_import_recovers_captured_bytes_without_refetch_after_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import summit_everything.integrations.feishu.service as module

    c = client(tmp_path)
    authorize(c)
    calls = []
    provider = c.app.state.feishu_service.provider
    original_body = provider.body

    def tracked(credentials, material_id):
        calls.append(material_id)
        return original_body(credentials, material_id)

    provider.body = tracked
    original_write = module.atomic_write

    def interrupted(path, raw):
        import json

        if json.loads(raw).get("outcomes"):
            raise OSError("simulated interruption after source capture")
        original_write(path, raw)

    payload = {"material_ids": ["minute-1"], "operation_id": "interrupted"}
    monkeypatch.setattr(module, "atomic_write", interrupted)
    with pytest.raises(OSError):
        c.post(PREFIX + "/imports", json=payload)
    monkeypatch.setattr(module, "atomic_write", original_write)
    assert c.post(PREFIX + "/imports", json=payload).json()["state"] == "succeeded"
    assert calls == ["minute-1"]
    assert len(c.get("/api/v1/intake/items").json()) == 1


@pytest.mark.parametrize("route", ["materials", "calendar"])
@pytest.mark.parametrize(
    "failure,code",
    [
        ("timeout", "provider_timeout"),
        ("unavailable", "provider_unavailable"),
        ("malformed", "malformed_response"),
    ],
)
def test_list_provider_failures_safe(tmp_path: Path, route: str, failure: str, code: str) -> None:
    c = client(tmp_path)
    authorize(c)

    def failing(*args):
        if failure == "timeout":
            raise TimeoutError("synthetic-sensitive-secret")
        if failure == "unavailable":
            raise RuntimeError("synthetic-sensitive-secret")
        return {"not": "valid"}

    setattr(c.app.state.feishu_service.provider, route, failing)
    params = (
        {}
        if route == "materials"
        else {"start": "2026-10-09T00:00:00Z", "end": "2026-10-10T00:00:00Z", "timezone": "UTC"}
    )
    result = c.get(PREFIX + "/" + route, params=params)
    assert result.json()["error"]["code"] == code
    assert "synthetic-sensitive-secret" not in result.text
    assert c.get("/api/v1/intake/items").json() == []


def test_source_filename_rejection_is_per_item_and_continues(tmp_path: Path) -> None:
    from summit_everything.integrations.feishu.provider import MaterialBody

    c = client(tmp_path)
    authorize(c)
    provider = c.app.state.feishu_service.provider
    original = provider.body
    provider.body = lambda user, material_id: (
        MaterialBody(raw=b"synthetic text", filename=" .txt", content_type="text/plain")
        if material_id == "a-bad"
        else original(user, material_id)
    )
    result = c.post(
        PREFIX + "/imports",
        json={"material_ids": ["a-bad", "minute-1"], "operation_id": "invalid-name-batch"},
    )
    assert result.status_code == 200
    assert result.json()["state"] == "partial"
    assert result.json()["outcomes"][0]["error_code"] == "malformed_response"
    assert result.json()["outcomes"][1]["state"] == "succeeded"
    assert len(c.get("/api/v1/intake/items").json()) == 1


def test_configured_callback_other_port_and_cors_is_preserved(tmp_path: Path) -> None:
    from summit_everything.integrations.feishu.provider import FeishuConfig

    config = FeishuConfig(redirect_uri="http://127.0.0.1:8793" + PREFIX + "/callback")
    c = TestClient(
        create_app(session_token="local", feishu_config=config),
        base_url="http://127.0.0.1:5173",
        headers={"Authorization": "Bearer local"},
    )
    assert (
        c.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "name": "模拟",
                "mode": "create",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    url = c.post(PREFIX + "/authorizations", json={}).json()["authorization_url"]
    assert url.startswith(config.redirect_uri + "?")
    response = c.get(url, headers={"Authorization": "", "Origin": "http://127.0.0.1:5173"})
    assert response.status_code == 200 and response.json()["authorized"] is True
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_app_secret_boundary_isolated_from_user_tokens_and_responses(tmp_path: Path) -> None:
    import summit_everything.integrations.feishu.provider as module

    assert hasattr(module, "AppCredentials")
    assert hasattr(module.FeishuConfig(), "app_id")
    credentials = module.AppCredentials(app_id="synthetic-app", app_secret="synthetic-app-secret")
    assert "synthetic-app-secret" not in repr(credentials)
    store = module.MemoryCredentialStore()
    store.put_app(credentials)
    assert store.get_app() == credentials
    assert store.get() is None
    config = module.FeishuConfig(app_id="synthetic-app")
    assert "synthetic-app-secret" not in config.model_dump_json()
    c = TestClient(
        create_app(session_token="local", credential_store=store, feishu_config=config),
        base_url="http://127.0.0.1:5173",
        headers={"Authorization": "Bearer local"},
    )
    assert (
        c.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "name": "模拟",
                "mode": "create",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    authorize(c)
    for response in [
        c.get(PREFIX + "/status"),
        c.post(PREFIX + "/authorizations", json={}),
        c.get(PREFIX + "/materials"),
    ]:
        assert "synthetic-app-secret" not in response.text
    assert store.get_app() == credentials and store.get().token_type == "user"


def test_workspace_and_app_identity_scope_feishu_state(tmp_path: Path) -> None:
    c = client(tmp_path)
    first_service = c.app.state.feishu_service
    authorize(c)
    assert c.get(PREFIX + "/status").json()["authorized"] is True

    assert (
        c.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace-2"),
                "name": "另一个模拟库",
                "mode": "create",
                "operation_id": "open-2",
            },
        ).status_code
        == 201
    )
    assert c.app.state.feishu_service is not first_service
    assert c.get(PREFIX + "/status").json()["authorized"] is False

    c.post(
        "/api/v1/workspaces",
        json={"root": str(tmp_path / "workspace"), "mode": "open", "operation_id": "reopen-1"},
    )
    assert c.get(PREFIX + "/status").json()["authorized"] is True

    start = c.post(PREFIX + "/authorizations", json={}).json()
    old_url = urlsplit(start["authorization_url"])
    old_state = parse_qs(old_url.query)["state"][0]
    changed = c.patch(
        "/api/v1/settings",
        json={"feishu": {"app_id": "synthetic-different-app"}},
    )
    assert changed.status_code == 200
    rejected = c.get(
        PREFIX + "/callback",
        params={"state": old_state, "code": "fake-ok"},
    )
    assert rejected.status_code == 400
    assert c.get(PREFIX + "/status").json()["authorized"] is False


def test_capture_validation_failure_continues_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from summit_everything.intake.sources import SourceStore
    from summit_everything.workspace.manifest import WorkspaceError

    c = client(tmp_path)
    authorize(c)
    original = SourceStore.capture

    def rejected(self, root, raw, filename, operation_id, **kwargs):
        if filename == "模拟会议.txt":
            raise WorkspaceError("synthetic-rejected-source")
        return original(self, root, raw, filename, operation_id, **kwargs)

    monkeypatch.setattr(SourceStore, "capture", rejected)
    result = c.post(
        PREFIX + "/imports",
        json={"material_ids": ["minute-1", "minute-2"], "operation_id": "capture-validation"},
    )
    assert result.status_code == 200 and result.json()["state"] == "partial"
    assert result.json()["outcomes"][0]["error_code"] == "malformed_response"
    assert result.json()["outcomes"][1]["state"] == "succeeded"
    assert "synthetic-rejected-source" not in result.text


def test_logout_invalidates_pending_authorization_state(tmp_path: Path) -> None:
    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.integrations.feishu.provider import FeishuConfig, MemoryCredentialStore
    from summit_everything.integrations.feishu.service import FeishuService

    service = FeishuService(
        FakeFeishu(tmp_path / "remote"), MemoryCredentialStore(), FeishuConfig(), "session"
    )
    start = service.authorize()
    state = parse_qs(urlsplit(start.authorization_url).query)["state"][0]

    service.logout()

    from summit_everything.integrations.feishu.provider import FeishuError

    with pytest.raises(FeishuError) as exc_info:
        service.callback(state, "fake-ok", None, service.config.redirect_uri)
    assert exc_info.value.code == "invalid_state"


def test_logout_during_code_exchange_cannot_restore_old_token(tmp_path: Path) -> None:
    from threading import Event, Thread

    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.integrations.feishu.provider import (
        FeishuConfig,
        FeishuError,
        MemoryCredentialStore,
        UserCredentials,
    )
    from summit_everything.integrations.feishu.service import FeishuService

    entered = Event()
    release = Event()

    class DelayedExchange(FakeFeishu):
        def exchange(self, code: str, redirect_uri: str, app_credentials=None):
            entered.set()
            assert release.wait(2)
            return UserCredentials(
                access_token="synthetic-old-access",
                refresh_token="synthetic-old-refresh",
                expires_at=4_000_000_000,
                scopes=["minutes:read"],
            )

    store = MemoryCredentialStore()
    service = FeishuService(DelayedExchange(tmp_path / "remote"), store, FeishuConfig(), "session")
    state = parse_qs(urlsplit(service.authorize().authorization_url).query)["state"][0]
    errors: list[str] = []

    def callback() -> None:
        try:
            service.callback(state, "fake-ok", None, service.config.redirect_uri)
        except FeishuError as exc:
            errors.append(exc.code)

    thread = Thread(target=callback)
    thread.start()
    assert entered.wait(2)
    service.logout()
    release.set()
    thread.join(2)

    assert not thread.is_alive()
    assert errors == ["invalid_state"]
    assert store.get() is None
