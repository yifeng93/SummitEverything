"""The real Feishu adapter is reachable only behind the server-side gate.

Only a stub provider and an in-memory backend are used; no real request,
credential or Keychain item exists in this test.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.acceptance_plans import AcceptancePlanLedger
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    CalendarPage,
    FeishuConfig,
    MemoryCredentialStore,
    UserCredentials,
)
from summit_everything.integrations.feishu.service import FeishuService
from summit_everything.integrations.settings import (
    CredentialVault,
    FeishuSettings,
    MemorySecretBackend,
    ProviderSettings,
    provider_settings_payload,
)
from summit_everything.retrieval.store import IndexStore

HEADERS = {"Authorization": "Bearer synthetic-gate-session"}
APP_ID = "cli_synthetic_gate_app"
CALLBACK = "http://localhost:8765/callback"


def _client(tmp_path: Path, provider=None) -> TestClient:
    app = create_app(
        session_token="synthetic-gate-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        feishu_provider=provider or FakeFeishu(tmp_path / "synthetic-remote"),
    )
    return TestClient(app)


def _open(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "Synthetic Gate",
            "operation_id": "open",
        },
    )
    assert response.status_code == 201


def _configure_real(client: TestClient) -> None:
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={
                "mode": "real",
                "feishu": {"app_id": APP_ID, "redirect_uri": CALLBACK},
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


def test_expired_user_calendar_token_needs_matching_app_secret_to_be_ready(tmp_path: Path) -> None:
    credentials = UserCredentials(
        access_token="synthetic-expired-access",
        refresh_token="synthetic-refresh",
        expires_at=900,
        scopes=["calendar:read", "calendar:calendar.event:read"],
    )
    credential_store = MemoryCredentialStore()
    credential_store.put(credentials)
    config = FeishuConfig(mode="real", app_id=APP_ID, identity="user")
    service = FeishuService(
        FakeFeishu(tmp_path / "synthetic-remote"),
        credential_store,
        config,
        "synthetic-session",
        clock=lambda: 1000,
    )
    backend = MemorySecretBackend()
    vault = CredentialVault("synthetic-profile", backend)
    settings = ProviderSettings(
        mode="real",
        feishu=FeishuSettings(app_id=APP_ID, identity="user"),
    )
    vault.put("feishu_user", credentials.model_dump_json(), account_id=APP_ID)

    before = service.status()
    summary = provider_settings_payload(
        settings, vault, feishu_calendar_ready=before.calendar_ready
    )
    assert before.refreshable is True
    assert before.calendar_ready is False
    assert before.app_configured is False
    assert before.credential_error == "application_credential_missing"
    assert summary.capabilities["feishu_calendar_read"].disabled_reason == "provider_not_configured"

    app_credentials = AppCredentials(app_id=APP_ID, app_secret="synthetic-app-secret")
    credential_store.put_app(app_credentials)
    vault.put("feishu_app", "synthetic-app-secret", account_id=APP_ID)

    after = service.status()
    summary = provider_settings_payload(settings, vault, feishu_calendar_ready=after.calendar_ready)
    assert after.refreshable is True
    assert after.calendar_ready is True
    assert after.app_configured is True
    assert after.credential_error is None
    assert summary.capabilities["feishu_calendar_read"].available is True


def test_real_data_routes_are_disabled_until_explicitly_authorized(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    _configure_real(client)

    capabilities = client.get("/api/v1/settings", headers=HEADERS).json()["capabilities"]
    assert capabilities["feishu_material_read"]["available"] is False
    assert capabilities["feishu_material_read"]["configured"] is True
    reason = capabilities["feishu_material_read"]["disabled_reason"]
    assert reason == "acceptance_plan_required"

    for path in (
        "/api/v1/integrations/feishu/materials",
        "/api/v1/integrations/feishu/tasks",
    ):
        response = client.get(path, headers=HEADERS)
        assert response.status_code == 409, (path, response.text)
        assert response.json()["error"]["code"] == "acceptance_plan_required"


def test_calendar_read_is_direct_bounded_and_workspace_bound_for_agent(tmp_path):
    class CalendarProvider:
        calls = []

        def calendar(self, credentials, start, end, timezone, cursor, limit):
            self.calls.append((credentials, start, end, timezone, cursor, limit))
            return CalendarPage(items=[], next_cursor=None, timezone=timezone, truncated=False)

    provider = CalendarProvider()
    client = _client(tmp_path, provider)
    _open(client, tmp_path)
    _configure_real(client)
    current = client.get("/api/v1/workspaces/current", headers=HEADERS).json()
    path = (
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai&limit=20"
    )

    direct = client.get(path, headers=HEADERS)
    assert direct.status_code == 200, direct.text
    assert direct.json()["items"] == []
    assert len(provider.calls) == 1

    agent = client.get(
        "/api/v1/agent/calendar?" + path.split("?", 1)[1],
        headers={**HEADERS, "X-Summit-Workspace-Id": current["workspace_id"]},
    )
    assert agent.status_code == 200, agent.text
    assert agent.json() == direct.json()
    assert len(provider.calls) == 2

    isolated = client.get(
        "/api/v1/agent/calendar?" + path.split("?", 1)[1],
        headers={**HEADERS, "X-Summit-Workspace-Id": "00000000-0000-0000-0000-000000000001"},
    )
    assert isolated.status_code == 409
    assert isolated.json()["error"]["code"] == "workspace_changed"
    assert len(provider.calls) == 2


def test_calendar_provider_failure_is_not_retried_or_reported_as_empty(tmp_path):
    class FailingCalendarProvider:
        calls = 0

        def calendar(self, credentials, start, end, timezone, cursor, limit):
            self.calls += 1
            raise TimeoutError("synthetic timeout")

    provider = FailingCalendarProvider()
    client = _client(tmp_path, provider)
    _open(client, tmp_path)
    _configure_real(client)
    response = client.get(
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai",
        headers=HEADERS,
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_timeout"
    assert provider.calls == 1


def test_user_calendar_requires_authorization_and_scope_but_accepts_legacy_readonly_scope(tmp_path):
    class CalendarProvider:
        calls = []

        def calendar(self, credentials, start, end, timezone, cursor, limit):
            self.calls.append(credentials)
            return CalendarPage(items=[], next_cursor=None, timezone=timezone)

    provider = CalendarProvider()
    client = _client(tmp_path, provider)
    _open(client, tmp_path)
    _configure_real(client)
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"identity": "user"}}
        ).status_code
        == 200
    )
    path = (
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai"
    )

    missing_authorization = client.get(path, headers=HEADERS)
    assert missing_authorization.status_code == 401
    assert missing_authorization.json()["error"]["code"] == "not_authorized"
    assert (
        client.get("/api/v1/settings", headers=HEADERS).json()["capabilities"][
            "feishu_calendar_read"
        ]["available"]
        is False
    )

    credential = UserCredentials(
        access_token="synthetic-user-token",
        refresh_token="synthetic-refresh-token",
        expires_at=2_000_000_000,
        scopes=["calendar:unrelated:read"],
    )
    assert (
        client.put(
            "/api/v1/credentials/feishu_user",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": credential.model_dump_json()},
        ).status_code
        == 200
    )
    missing_scope = client.get(path, headers=HEADERS)
    assert missing_scope.status_code == 403
    assert missing_scope.json()["error"]["code"] == "missing_scope"
    assert provider.calls == []

    legacy = credential.model_copy(update={"scopes": ["calendar:calendar:readonly"]})
    assert (
        client.put(
            "/api/v1/credentials/feishu_user",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": legacy.model_dump_json()},
        ).status_code
        == 200
    )
    allowed = client.get(path, headers=HEADERS)
    assert allowed.status_code == 200, allowed.text
    assert len(provider.calls) == 1
    assert provider.calls[0].scopes == ["calendar:calendar:readonly"]
    assert (
        client.get("/api/v1/settings", headers=HEADERS).json()["capabilities"][
            "feishu_calendar_read"
        ]["available"]
        is True
    )


def test_real_mode_without_an_app_id_is_reported_as_unconfigured(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    assert (
        client.patch("/api/v1/settings", headers=HEADERS, json={"mode": "real"}).status_code == 200
    )
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_configured"
    calendar = client.get(
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai",
        headers=HEADERS,
    )
    assert calendar.status_code == 409
    assert calendar.json()["error"]["code"] == "provider_not_configured"


def test_settings_flag_does_not_report_capability_as_enabled(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    _configure_real(client)
    assert (
        client.patch(
            "/api/v1/settings", headers=HEADERS, json={"feishu": {"real_data_enabled": True}}
        ).status_code
        == 200
    )

    capabilities = client.get("/api/v1/settings", headers=HEADERS).json()["capabilities"]
    assert capabilities["feishu_material_read"]["available"] is False

    # Provider injection does not grant a read. Every real-mode attempt still
    # needs its own itemized acceptance plan.
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "acceptance_plan_required"


def test_settings_api_cannot_select_fake_feishu_mode(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    rejected = client.patch("/api/v1/settings", headers=HEADERS, json={"mode": "fake"})
    assert rejected.status_code == 422
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_configured"


def test_real_feishu_read_plan_binds_configuration_scope_and_is_one_shot(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    _configure_real(client)
    scope = {"query": "指定合成关键词", "visibility": "owner", "cursor": None, "limit": 20}
    created = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "feishu.materials.read", "scope": scope},
    )
    assert created.status_code == 201, created.text
    plan = created.json()["plan"]
    assert plan["request_limit"] == 2  # one list request + one possible token refresh
    assert "query" not in created.text or "指定合成关键词" in created.text

    unplanned = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert unplanned.status_code == 409
    assert unplanned.json()["error"]["code"] == "acceptance_plan_required"

    confirmed = client.post(
        f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": plan["scope_sha256"]},
    )
    assert confirmed.status_code == 200
    changed = client.get(
        "/api/v1/integrations/feishu/materials?query=another&visibility=owner&plan_id="
        + plan["plan_id"],
        headers=HEADERS,
    )
    assert changed.status_code == 409

    attempted = client.get(
        "/api/v1/integrations/feishu/materials?query=%E6%8C%87%E5%AE%9A%E5%90%88%E6%88%90%E5%85%B3%E9%94%AE%E8%AF%8D"
        "&visibility=owner&limit=20&plan_id=" + plan["plan_id"],
        headers=HEADERS,
    )
    assert attempted.status_code == 401  # synthetic FakeFeishu refuses real identity
    status = client.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS).json()
    assert status["state"] == "unknown"
    assert status["requests_reserved"] == 2

    retry = client.get(
        "/api/v1/integrations/feishu/materials?query=%E6%8C%87%E5%AE%9A%E5%90%88%E6%88%90%E5%85%B3%E9%94%AE%E8%AF%8D"
        "&visibility=owner&limit=20&plan_id=" + plan["plan_id"],
        headers=HEADERS,
    )
    assert retry.status_code == 409


def test_live_acceptance_plan_owner_remains_executing(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    _configure_real(client)
    plan = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "feishu.tasks.read", "scope": {"cursor": None, "limit": 20}},
    ).json()["plan"]
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": plan["scope_sha256"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    ledger_path = next((tmp_path / "profile").rglob("acceptance-plans.json"))
    ledger = AcceptancePlanLedger(ledger_path.parent)
    executing = ledger.begin_execution(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        config_sha256=plan["config_sha256"],
        scope_sha256=plan["scope_sha256"],
        run_id=client.app.state.acceptance_run_id,
    )
    reserved = ledger.reserve_requests(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        count=2,
    )

    status = client.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS)

    assert status.status_code == 200, status.text
    assert status.json()["state"] == "executing"
    assert status.json()["execution_run_id"] == str(executing.execution_run_id)
    assert status.json()["requests_reserved"] == 2
    assert reserved.state == "executing"


def test_interrupted_acceptance_plan_is_reported_unknown_without_replay(tmp_path):
    profile = tmp_path / "profile"
    workspace = tmp_path / "workspace"
    first = _client(tmp_path)
    _open(first, tmp_path)
    _configure_real(first)
    plan = first.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "feishu.tasks.read", "scope": {"cursor": None, "limit": 20}},
    ).json()["plan"]
    confirmed = first.post(
        f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": plan["scope_sha256"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    ledger_path = next(profile.rglob("acceptance-plans.json"))
    ledger = AcceptancePlanLedger(ledger_path.parent)
    original_run_id = uuid4()
    ledger.begin_execution(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        config_sha256=plan["config_sha256"],
        scope_sha256=plan["scope_sha256"],
        run_id=original_run_id,
    )
    ledger.reserve_requests(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        count=2,
    )

    restarted = _client(tmp_path)
    opened = restarted.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(workspace),
            "mode": "open",
            "name": "Synthetic Gate",
            "operation_id": "reopen-after-restart",
        },
    )
    assert opened.status_code == 201, opened.text
    operation_retry = restarted.get(
        f"/api/v1/integrations/feishu/tasks?limit=20&plan_id={plan['plan_id']}",
        headers=HEADERS,
    )
    assert operation_retry.status_code == 409, operation_retry.text

    first_status = restarted.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS)
    second_status = restarted.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS)

    assert first_status.status_code == 200, first_status.text
    assert second_status.status_code == 200, second_status.text
    assert first_status.json()["state"] == second_status.json()["state"] == "unknown"
    assert (
        first_status.json()["requests_reserved"] == second_status.json()["requests_reserved"] == 2
    )
    assert first_status.json()["execution_run_id"] == str(original_run_id)
    assert second_status.json()["execution_run_id"] == str(original_run_id)
    assert first_status.json()["finished_at"] is not None
    assert ledger.get(UUID(plan["plan_id"])).requests_reserved == 2


def test_real_query_plan_binds_context_settings_and_sources_without_persisting_prompt(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={
                "mode": "real",
                "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
                "embedding": {
                    "provider": "local",
                    "model": "BAAI/bge-small-zh-v1.5",
                    "enabled": True,
                },
                "rerank": {
                    "provider": "local",
                    "model": "BAAI/bge-small-zh-v1.5",
                    "enabled": True,
                },
            },
        ).status_code
        == 200
    )
    fingerprint = client.get("/api/v1/settings", headers=HEADERS).json()["embedding_fingerprint"]
    workspace = client.get("/api/v1/workspaces/current", headers=HEADERS).json()
    profile = Path(workspace["local_profile_dir"]).resolve()

    class PreparedModelStatus:
        def status(self) -> dict[str, object]:
            return {
                "model": "BAAI/bge-small-zh-v1.5",
                "revision": "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59",
                "dimensions": 512,
                "token_limit": 512,
                "download_size_bytes": 95_330_972,
                "state": "ready",
                "downloaded_bytes": 95_330_972,
                "progress_percent": 100,
                "error_code": None,
            }

    # Planning tests only inspect readiness; no inference is invoked here.
    client.app.state.local_model_stores[str(profile)] = PreparedModelStatus()
    # Seed an empty but structurally valid synthetic LanceDB generation for the
    # configured model. This test exercises plan binding and stale-plan
    # rejection; it must not require a provider call or bypass the new index gate.
    index = IndexStore(profile / "index.sqlite3")
    generation = index.replace_generation(
        UUID(workspace["workspace_id"]),
        fingerprint,
        [],
        expected_generation=None,
        vector_dimension=512,
    )
    assert index.active_generation(UUID(workspace["workspace_id"])) == generation
    query_id = str(uuid4())
    scope = {
        "question": "合成问题不得存入账本",
        "fingerprint": fingerprint,
        "purpose": "current",
        "answer_mode": "fact",
        "role_id": None,
        "request_id": query_id,
        "conversation_id": None,
    }
    created = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.query", "scope": scope},
    )
    assert created.status_code == 201, created.text
    plan = created.json()["plan"]
    assert plan["request_limit"] == 1
    assert created.json()["scope"]["question"] == scope["question"]
    ledger = next((tmp_path / "profile").rglob("acceptance-plans.json"))
    assert scope["question"] not in ledger.read_text()
    assert (
        client.post(
            f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
            headers=HEADERS,
            json={"scope_sha256": plan["scope_sha256"], "scope": created.json()["scope"]},
        ).status_code
        == 200
    )

    changed = client.patch(
        "/api/v1/settings", headers=HEADERS, json={"llm": {"max_output_tokens": 4096}}
    )
    assert changed.status_code == 200
    execution = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={**scope, "acceptance_plan_id": plan["plan_id"]},
    )
    assert execution.status_code == 409
    assert execution.json()["error"]["code"] == "acceptance_plan_conflict"
    assert (
        client.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS).json()["state"]
        == "confirmed"
    )
