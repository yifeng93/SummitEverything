"""Independent route/service/vault tests; only HTTP and SecretBackend replaced."""

import json
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import summit_everything.api.app as app_module
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.settings import MemorySecretBackend, SettingsError

HEADERS = {"Authorization": "Bearer independent-synthetic-session"}
APP_ID = "cli_independent_synthetic"
CALLBACK = "http://localhost:19231/callback"
SCOPE = "minutes:minutes.search:read"


class Remote:
    def __init__(self, *, short_token=False):
        self.calls = []
        self.refresh_calls = 0
        self.short_token = short_token

    def handler(self, request):
        self.calls.append((request.method, request.url.path))
        if request.url.path.endswith("/oauth/token"):
            payload = json.loads(request.content)
            if payload["grant_type"] == "refresh_token":
                self.refresh_calls += 1
                raise httpx.ReadTimeout("synthetic lost refresh response")
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "synthetic-user-access",
                    "refresh_token": "synthetic-single-use-refresh",
                    "expires_in": 1 if self.short_token else 7200,
                    "scope": SCOPE,
                    "token_type": "Bearer",
                },
            )
        if request.url.path.endswith("tenant_access_token/internal"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "tenant_access_token": "synthetic-tenant",
                    "expire": 7200,
                },
            )
        if request.url.path.endswith("/events") or request.url.path.endswith("/search"):
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        raise AssertionError(f"unexpected external request: {request.method} {request.url.path}")


class Backend(MemorySecretBackend):
    deny_user = False
    user_reads = 0

    def get(self, namespace, key):
        if key.startswith("feishu_user:"):
            self.user_reads += 1
            if self.deny_user:
                raise SettingsError("credential_store_unavailable")
        return super().get(namespace, key)


def api(tmp_path, monkeypatch, backend, remote, *, create=True):
    def factory(config, app_credentials, **kwargs):
        return FeishuHttpProvider(
            config,
            app_credentials,
            client_factory=lambda: httpx.Client(
                transport=httpx.MockTransport(remote.handler),
                trust_env=False,
            ),
            **kwargs,
        )

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = app_module.create_app(
        session_token="independent-synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=backend,
    )
    client = TestClient(app, base_url="http://127.0.0.1:5173")
    response = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create" if create else "open",
            "name": "Independent synthetic workspace",
            "operation_id": "open",
        },
    )
    assert response.status_code == 201, response.text
    if create:
        response = client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={
                "mode": "real",
                "feishu": {
                    "app_id": APP_ID,
                    "redirect_uri": CALLBACK,
                    "identity": "app",
                    "calendar_id": "independent-calendar",
                    "real_data_enabled": True,
                },
            },
        )
        assert response.status_code == 200, response.text
        response = client.put(
            "/api/v1/credentials/feishu_app",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": "synthetic-app-secret"},
        )
        assert response.status_code == 200, response.text
    return client


def login(client):
    issued = client.post("/api/v1/integrations/feishu/authorizations", headers=HEADERS)
    assert issued.status_code == 200, issued.text
    parts = urlsplit(issued.json()["authorization_url"])
    state = parse_qs(parts.query)["state"][0]
    result = client.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
    assert result.status_code == 200, result.text
    return state


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("feishu_task_create", {"summary": "独立合成任务", "due": None}),
        (
            "feishu_task_update",
            {
                "task_guid": "synthetic-task",
                "task": {"summary": "更名"},
                "update_fields": ["summary"],
            },
        ),
        ("feishu_task_complete", {"task_guid": "synthetic-task"}),
    ],
)
@pytest.mark.parametrize("read_enabled", [False, True])
def test_independent_real_confirmed_write_rejects_before_any_http(
    tmp_path,
    monkeypatch,
    kind,
    payload,
    read_enabled,
):
    remote, backend = Remote(), Backend()
    with api(tmp_path, monkeypatch, backend, remote) as client:
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"real_data_enabled": read_enabled}},
        )
        proposal = client.post(
            "/api/v1/actions",
            headers=HEADERS,
            json={
                "action_id": str(uuid4()),
                "kind": kind,
                "payload": payload,
            },
        )
        assert proposal.status_code == 201, proposal.text
        action = proposal.json()
        proof = {"payload_sha256": action["payload_sha256"], "confirmation_id": str(uuid4())}
        confirmation = client.post(
            f"/api/v1/actions/{action['action_id']}/confirmations", headers=HEADERS, json=proof
        )
        assert confirmation.status_code == 200, confirmation.text
        for _ in range(2):
            result = client.post(
                f"/api/v1/actions/{action['action_id']}/executions", headers=HEADERS, json=proof
            )
            assert result.status_code == 409, result.text
            assert result.json()["error"]["code"] == "result_proof_unavailable"
        assert remote.calls == []
        assert (
            client.get(f"/api/v1/actions/{action['action_id']}", headers=HEADERS).json()["state"]
            == "confirmed"
        )


@pytest.mark.parametrize("fault", ["corrupt", "denied"])
def test_independent_app_calendar_avoids_faulty_user_slot_after_restart(
    tmp_path,
    monkeypatch,
    fault,
):
    remote, backend = Remote(), Backend()
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
    for (namespace, key), _value in list(backend._values.items()):
        if key.startswith("feishu_user:") and fault == "corrupt":
            backend.set(namespace, key, '{"access_token": "synthetic-corrupt-secret"}')
    backend.deny_user = fault == "denied"
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        reads = backend.user_reads
        result = restarted.get(
            "/api/v1/integrations/feishu/calendar",
            headers=HEADERS,
            params={
                "start": "2026-10-11T00:00:00+08:00",
                "end": "2026-10-12T00:00:00+08:00",
                "timezone": "Asia/Shanghai",
            },
        )
        assert result.status_code == 200, result.text
        assert backend.user_reads == reads
        search = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert search.status_code == 401, search.text
        assert search.json()["error"]["code"] == "credential_unreadable"
        status = restarted.get("/api/v1/integrations/feishu/status", headers=HEADERS)
        assert status.json()["authorized"] is False
        assert status.json()["app_configured"] is True
        assert "synthetic-corrupt-secret" not in status.text


def test_independent_unknown_refresh_is_not_resent_after_restart(tmp_path, monkeypatch):
    """A consumed single-use refresh cannot become eligible again on app restart."""
    remote, backend = Remote(short_token=True), Backend()
    with api(tmp_path, monkeypatch, backend, remote) as first:
        state = login(first)
        repeated = first.get(CALLBACK, params={"state": state, "code": "synthetic-code"})
        assert repeated.status_code == 400
        failed = first.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert failed.status_code == 503, failed.text
        assert failed.json()["error"]["code"] == "provider_timeout"
        assert remote.refresh_calls == 1
        again = first.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert again.status_code == 401, again.text
        assert remote.refresh_calls == 1
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        result = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert remote.refresh_calls == 1, (
            "single-use refresh was dispatched again after a lost response and restart; "
            f"calls={remote.refresh_calls}, status={result.status_code}"
        )
        assert result.status_code == 401, result.text
