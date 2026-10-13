"""The real Feishu adapter is reachable only behind the server-side gate.

Only a stub provider and an in-memory backend are used; no real request,
credential or Keychain item exists in this test.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-gate-session"}
APP_ID = "cli_synthetic_gate_app"
CALLBACK = "http://localhost:8765/callback"


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        session_token="synthetic-gate-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        feishu_provider=FakeFeishu(tmp_path / "synthetic-remote"),
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
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai",
    ):
        response = client.get(path, headers=HEADERS)
        assert response.status_code == 409, (path, response.text)
        assert response.json()["error"]["code"] == "acceptance_plan_required"


def test_real_mode_without_an_app_id_is_reported_as_unconfigured(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    assert (
        client.patch("/api/v1/settings", headers=HEADERS, json={"mode": "real"}).status_code == 200
    )
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_configured"


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


def test_fake_mode_keeps_working_offline(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authorized"


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
                    "provider": "dashscope",
                    "model": "qwen3.7-text-embedding",
                    "enabled": True,
                },
                "rerank": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-rerank",
                    "enabled": True,
                },
            },
        ).status_code
        == 200
    )
    fingerprint = client.get("/api/v1/settings", headers=HEADERS).json()["embedding_fingerprint"]
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
    assert plan["request_limit"] == 3
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
