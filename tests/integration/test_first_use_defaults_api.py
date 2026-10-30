"""Integration tests: injected non-secret defaults reach the settings API."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.first_use_defaults import (
    DEFAULTS_ENV_VAR,
    FirstUseDefaults,
    FirstUseDefaultsError,
)
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "synthetic-first-use-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
APP_ID = "cli_synthetic_app_0001"
CALLBACK_URI = "http://127.0.0.1:18793/api/v1/integrations/feishu/callback"
EMBEDDING_BASE_URL = (
    "https://ws-synthetic0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)
RERANK_BASE_URL = "https://ws-synthetic0000000000.cn-beijing.maas.aliyuncs.com/api/v1"


def write_defaults(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def open_workspace(client: TestClient, root: Path) -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(root),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-first-use-defaults-test",
        },
    )
    assert opened.status_code == 201


def test_injected_defaults_prefill_settings_and_keep_offline_defaults(tmp_path, monkeypatch):
    source = write_defaults(
        tmp_path / "defaults.json",
        {
            "feishu_app_id": APP_ID,
            "feishu_redirect_uri": CALLBACK_URI,
            "embedding_base_url": EMBEDDING_BASE_URL,
            "rerank_base_url": RERANK_BASE_URL,
        },
    )
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(source))
    app = create_app(
        session_token=TOKEN,
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    open_workspace(client, tmp_path / "workspace")

    payload = client.get("/api/v1/settings", headers=HEADERS).json()
    assert payload["mode"] == "real"
    assert payload["llm"]["provider"] == "deepseek"
    assert payload["llm"]["enabled"] is True
    assert payload["embedding"]["provider"] == "local"
    assert payload["feishu"]["app_id"] == APP_ID
    assert payload["feishu"]["redirect_uri"] == CALLBACK_URI
    assert payload["embedding"]["base_url"] == EMBEDDING_BASE_URL
    assert payload["rerank"]["base_url"] == RERANK_BASE_URL

    fake_patch = client.patch("/api/v1/settings", headers=HEADERS, json={"mode": "fake"})
    assert fake_patch.status_code == 422, fake_patch.text


def test_user_saved_setting_overrides_the_injected_default(tmp_path, monkeypatch):
    source = write_defaults(
        tmp_path / "defaults.json", {"feishu_app_id": APP_ID, "rerank_base_url": RERANK_BASE_URL}
    )
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(source))
    app = create_app(
        session_token=TOKEN,
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    open_workspace(client, tmp_path / "workspace")

    patched = client.patch(
        "/api/v1/settings", headers=HEADERS, json={"feishu": {"app_id": "cli_user_override"}}
    )
    assert patched.status_code == 200
    after = client.get("/api/v1/settings", headers=HEADERS).json()
    assert after["feishu"]["app_id"] == "cli_user_override"
    assert after["rerank"]["base_url"] == RERANK_BASE_URL

    persisted = list(tmp_path.rglob("provider-settings.json"))
    assert persisted, "the workspace profile must persist provider settings"
    stored = json.loads(persisted[0].read_text(encoding="utf-8"))
    assert stored["feishu"]["app_id"] == "cli_user_override"
    # The field the user never overrode is not written at all, so it keeps
    # following the injected default across builds.
    assert "base_url" not in stored["rerank"]


def test_saving_never_persists_injected_defaults(tmp_path, monkeypatch):
    source = write_defaults(
        tmp_path / "defaults.json",
        {
            "feishu_app_id": APP_ID,
            "feishu_redirect_uri": CALLBACK_URI,
            "embedding_base_url": EMBEDDING_BASE_URL,
            "rerank_base_url": RERANK_BASE_URL,
        },
    )
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(source))
    app = create_app(
        session_token=TOKEN,
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    open_workspace(client, tmp_path / "workspace")

    patched = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={"llm": {"provider": "deepseek", "model": "deepseek-flash"}},
    )
    assert patched.status_code == 200, patched.text

    stored = json.loads(
        next(iter(tmp_path.rglob("provider-settings.json"))).read_text(encoding="utf-8")
    )
    assert "app_id" not in stored["feishu"]
    assert "redirect_uri" not in stored["feishu"]
    assert "base_url" not in stored["embedding"]
    assert "base_url" not in stored["rerank"]
    assert stored["llm"]["provider"] == "deepseek"

    after = client.get("/api/v1/settings", headers=HEADERS).json()
    assert after["feishu"]["app_id"] == APP_ID
    assert after["feishu"]["redirect_uri"] == CALLBACK_URI
    assert after["embedding"]["base_url"] == EMBEDDING_BASE_URL
    assert after["rerank"]["base_url"] == RERANK_BASE_URL


def test_create_app_fails_closed_on_a_secret_shaped_key(tmp_path, monkeypatch):
    leaked = "synthetic-value-that-must-not-leak"
    source = write_defaults(tmp_path / "defaults.json", {"dashscope_api_key": leaked})
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(source))
    with pytest.raises(FirstUseDefaultsError) as error:
        create_app(session_token=TOKEN, profile_root=tmp_path / "profile")
    assert error.value.code == "first_use_defaults_secret_key"
    assert leaked not in str(error.value)


def test_create_app_fails_closed_on_an_invalid_injected_value(tmp_path, monkeypatch):
    source = write_defaults(
        tmp_path / "defaults.json", {"embedding_base_url": "http://not-aliyuncs.invalid/v1"}
    )
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(source))
    with pytest.raises(FirstUseDefaultsError) as error:
        create_app(session_token=TOKEN, profile_root=tmp_path / "profile")
    assert error.value.code == "first_use_defaults_value_invalid"
    assert "not-aliyuncs.invalid" not in str(error.value)


def test_create_app_reads_no_implicit_local_source(tmp_path, monkeypatch):
    # No explicit defaults argument and no environment variable: the repository's
    # Git-ignored .local/first-use/defaults.json must never be consulted, so this
    # result is identical on a developer machine and on CI.
    monkeypatch.delenv(DEFAULTS_ENV_VAR, raising=False)
    app = create_app(
        session_token=TOKEN,
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    assert isinstance(app.state.first_use_defaults, FirstUseDefaults)
    assert app.state.first_use_defaults.values == {}
    assert app.state.first_use_defaults.source is None

    client = TestClient(app)
    open_workspace(client, tmp_path / "workspace")
    payload = client.get("/api/v1/settings", headers=HEADERS).json()
    assert payload["feishu"]["app_id"] == ""
    assert payload["feishu"]["redirect_uri"] == ""
    assert payload["embedding"]["provider"] == "local"
    assert payload["rerank"]["provider"] == "local"
    assert payload["embedding"]["base_url"] == ""
    assert payload["rerank"]["base_url"] == ""
