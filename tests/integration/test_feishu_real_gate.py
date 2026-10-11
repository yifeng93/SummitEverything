"""The real Feishu adapter is reachable only behind the server-side gate.

Only a stub provider and an in-memory backend are used; no real request,
credential or Keychain item exists in this test.
"""

from __future__ import annotations

from pathlib import Path

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
    assert reason == "stage_c_authorization_required"

    for path in (
        "/api/v1/integrations/feishu/materials",
        "/api/v1/integrations/feishu/tasks",
        "/api/v1/integrations/feishu/calendar?start=2026-10-09T00:00:00%2B08:00"
        "&end=2026-10-10T00:00:00%2B08:00&timezone=Asia%2FShanghai",
    ):
        response = client.get(path, headers=HEADERS)
        assert response.status_code == 409, (path, response.text)
        assert response.json()["error"]["code"] == "stage_c_authorization_required"


def test_real_mode_without_an_app_id_is_reported_as_unconfigured(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    assert (
        client.patch("/api/v1/settings", headers=HEADERS, json={"mode": "real"}).status_code == 200
    )
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_configured"


def test_enabling_real_data_opens_the_adapter_path(tmp_path):
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
    assert capabilities["feishu_material_read"]["available"] is True

    # The gate is open; the stub provider is reached and reports the missing
    # user authorization instead of the Stage C gate.
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authorized"


def test_fake_mode_keeps_working_offline(tmp_path):
    client = _client(tmp_path)
    _open(client, tmp_path)
    response = client.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authorized"
