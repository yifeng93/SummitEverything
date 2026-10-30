import hashlib
import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.acceptance_plans import AcceptancePlanLedger, ProviderUsage
from summit_everything.integrations.credential_generations import CredentialGenerationStore
from summit_everything.integrations.provider_smoke import record_smoke_result
from summit_everything.integrations.settings import (
    CredentialVault,
    MemorySecretBackend,
    ProviderSettings,
    SettingsStore,
    provider_settings_payload,
)


def open_workspace(client: TestClient, headers: dict[str, str], tmp_path, *, create: bool):
    return client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create" if create else "open",
            "name": "模型状态模拟库" if create else None,
            "operation_id": "model-call-status",
        },
    )


def record_model_plan(
    workspace: dict[str, str], state: str, *, include_usage: bool, legacy_binding: bool = False
):
    profile = workspace["local_profile_dir"]
    profile_id = hashlib.sha256(profile.encode()).hexdigest()
    settings = SettingsStore(Path(profile) / "provider-settings.json").read()
    encoded = json.dumps(settings.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    config_sha256 = hashlib.sha256(encoded.encode()).hexdigest()
    if not legacy_binding:
        generation = CredentialGenerationStore(Path(profile)).get("deepseek")
        composite = json.dumps(
            {"settings": config_sha256, "deepseek_credential_generation": generation},
            sort_keys=True,
            separators=(",", ":"),
        )
        config_sha256 = hashlib.sha256(composite.encode()).hexdigest()
    scope_sha256 = "a" * 64
    ledger = AcceptancePlanLedger(Path(profile))
    plan = ledger.create(
        operation="model.query",
        workspace_id=workspace["workspace_id"],
        profile_id=profile_id,
        config_sha256=config_sha256,
        scope_sha256=scope_sha256,
        scope={},
        request_limit=1,
    )
    ledger.confirm(
        plan.plan_id,
        workspace_id=workspace["workspace_id"],
        profile_id=profile_id,
        config_sha256=config_sha256,
        scope_sha256=scope_sha256,
    )
    ledger.begin_execution(
        plan.plan_id,
        workspace_id=workspace["workspace_id"],
        profile_id=profile_id,
        config_sha256=config_sha256,
        scope_sha256=scope_sha256,
        run_id=uuid4(),
    )
    ledger.reserve_request(
        plan.plan_id, workspace_id=workspace["workspace_id"], profile_id=profile_id
    )
    if include_usage:
        ledger.record_usage(
            plan.plan_id,
            [
                ProviderUsage(
                    provider="deepseek", usage_reported=True, input_tokens=1, total_tokens=1
                )
            ],
        )
    ledger.finish(plan.plan_id, state=state)


def test_matching_legacy_success_survives_settings_read_and_app_restart(tmp_path):
    profile_root = tmp_path / "profile"
    backend = MemorySecretBackend()
    app = create_app(
        session_token="status-session", profile_root=profile_root, secret_backend=backend
    )
    headers = {"Authorization": "Bearer status-session"}
    with TestClient(app) as client:
        opened = open_workspace(client, headers, tmp_path, create=True)
        assert opened.status_code == 201
        workspace = opened.json()
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"llm": {"provider": "deepseek", "account_id": "default", "enabled": True}},
        )
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-secret-00000000"},
        )
        # Recreate the pre-generation ledger shape for the verified historical path.
        generation_store = CredentialGenerationStore(Path(workspace["local_profile_dir"]))
        generation_store.path.unlink()
        record_model_plan(workspace, "succeeded", include_usage=True, legacy_binding=True)
        status = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert status["state"] == "succeeded"
        assert status["has_success"] is True
        assert status["last_success_at"]

    restarted = create_app(
        session_token="status-session", profile_root=profile_root, secret_backend=backend
    )
    with TestClient(restarted) as client:
        reopened = open_workspace(client, headers, tmp_path, create=False)
        assert reopened.status_code == 201
        status = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert status["state"] == "succeeded"
        assert status["has_success"] is True


def test_credential_replacement_hides_old_success_and_unknown_without_usage_is_not_success(
    tmp_path,
):
    app = create_app(
        session_token="status-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    headers = {"Authorization": "Bearer status-session"}
    with TestClient(app) as client:
        opened = open_workspace(client, headers, tmp_path, create=True)
        workspace = opened.json()
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"llm": {"provider": "deepseek", "account_id": "default", "enabled": True}},
        )
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-secret-00000000"},
        )
        record_model_plan(workspace, "succeeded", include_usage=True)
        assert client.get("/api/v1/settings", headers=headers).json()["model_call_status"][
            "has_success"
        ]

        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-secret-11111111"},
        )
        status = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert status["state"] == "none"
        assert status["has_success"] is False

        # A terminal plan without DeepSeek usage cannot be presented as success.
        record_model_plan(workspace, "unknown", include_usage=False)
        status = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert status["state"] == "unknown"
        assert status["has_success"] is False


def test_usage_free_terminal_attempt_does_not_erase_prior_success(tmp_path):
    app = create_app(
        session_token="status-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    headers = {"Authorization": "Bearer status-session"}
    with TestClient(app) as client:
        workspace = open_workspace(client, headers, tmp_path, create=True).json()
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"llm": {"provider": "deepseek", "account_id": "default", "enabled": True}},
        )
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-secret-00000000"},
        )
        record_model_plan(workspace, "succeeded", include_usage=True)
        record_model_plan(workspace, "succeeded", include_usage=False)
        status = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert status["state"] == "unknown"
        assert status["has_success"] is True
        assert status["last_success_at"]


def test_synthetic_smoke_success_is_durable_and_bound_to_current_configuration(tmp_path):
    profile_root = tmp_path / "profile"
    app = create_app(
        session_token="status-session",
        profile_root=profile_root,
        secret_backend=MemorySecretBackend(),
    )
    headers = {"Authorization": "Bearer status-session"}
    with TestClient(app) as client:
        workspace = open_workspace(client, headers, tmp_path, create=True).json()
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"llm": {"provider": "deepseek", "account_id": "default", "enabled": True}},
        )
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-secret-00000000"},
        )
        profile_path = Path(workspace["local_profile_dir"])
        settings = SettingsStore(profile_path / "provider-settings.json").read()
        raw_binding = hashlib.sha256(
            json.dumps(
                settings.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        generation = CredentialGenerationStore(profile_path).get("deepseek")
        binding = hashlib.sha256(
            json.dumps(
                {"settings": raw_binding, "deepseek_credential_generation": generation},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        record_smoke_result(
            profile_root,
            "deepseek_chat",
            workspace_id=workspace["workspace_id"],
            profile_id=hashlib.sha256(str(profile_path.resolve()).encode()).hexdigest(),
            config_sha256=binding,
            state="succeeded",
        )
        first = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert first["state"] == "succeeded" and first["has_success"] is True
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={"llm": {"max_output_tokens": 4096}},
        )
        changed = client.get("/api/v1/settings", headers=headers).json()["model_call_status"]
        assert changed["state"] == "none" and changed["has_success"] is False


def test_unreadable_acceptance_ledger_does_not_break_settings_read(tmp_path):
    app = create_app(
        session_token="status-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    headers = {"Authorization": "Bearer status-session"}
    with TestClient(app) as client:
        workspace = open_workspace(client, headers, tmp_path, create=True).json()
        assert client.get("/api/v1/settings", headers=headers).status_code == 200
        Path(workspace["local_profile_dir"], "acceptance-plans.json").write_text("not-json")
        response = client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 200
        assert response.json()["model_call_status"]["state"] == "unreadable"


def test_local_model_capabilities_require_ready_files_selected_provider_and_enabled_switch():
    settings = ProviderSettings.model_validate(
        {
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
            "embedding": {
                "provider": "local",
                "model": "BAAI/bge-small-zh-v1.5",
                "dimensions": 512,
                "enabled": True,
            },
            "rerank": {
                "provider": "local",
                "model": "BAAI/bge-small-zh-v1.5",
                "dimensions": 512,
                "enabled": True,
            },
        }
    )
    vault = CredentialVault("synthetic", MemorySecretBackend())
    vault.put("deepseek", "sk-synthetic-secret-00000000")
    local_status = {
        "model": "BAAI/bge-small-zh-v1.5",
        "revision": "rev",
        "dimensions": 512,
        "token_limit": 512,
        "download_size_bytes": 95_330_972,
        "state": "ready",
        "downloaded_bytes": 95_330_972,
        "progress_percent": 100,
        "error_code": None,
    }

    ready = provider_settings_payload(settings, vault, local_model_status=local_status)
    assert ready.local_model.state == "ready"
    assert ready.capabilities["embedding"].available is True
    assert ready.capabilities["rerank"].available is True

    disabled_settings = settings.model_copy(
        update={"embedding": settings.embedding.model_copy(update={"enabled": False})}
    )
    disabled = provider_settings_payload(disabled_settings, vault, local_model_status=local_status)
    assert disabled.capabilities["embedding"].configured is True
    assert disabled.capabilities["embedding"].available is False
    assert disabled.capabilities["embedding"].disabled_reason == "local_provider_disabled"
