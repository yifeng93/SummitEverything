import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from summit_everything.integrations.settings import (
    CredentialVault,
    MemorySecretBackend,
    ProviderSettings,
    SettingsError,
    SettingsStore,
    embedding_fingerprint,
)


def test_settings_default_offline_and_atomic_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")

    initial = store.read()
    assert initial.mode == "fake"
    assert initial.llm.provider == "fake"

    updated = store.update({"llm": {"provider": "deepseek", "model": "deepseek-flash"}})
    assert updated.llm.provider == "deepseek"
    assert store.read() == updated
    assert json.loads((tmp_path / "settings.json").read_text())["mode"] == "fake"


def test_settings_reject_unknown_fields_and_arbitrary_endpoint(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")

    with pytest.raises(ValidationError):
        store.update({"llm": {"provider": "deepseek", "model": "deepseek-flash", "api_key": "no"}})
    with pytest.raises(ValidationError):
        store.update({"deepseek_base_url": "http://127.0.0.1:9999"})


def test_settings_rejects_non_allowlisted_model_and_dimension(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    with pytest.raises(ValidationError):
        store.update({"llm": {"provider": "deepseek", "model": "some-other-model"}})
    with pytest.raises(ValidationError):
        store.update(
            {
                "embedding": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-embedding",
                    "dimensions": 7,
                }
            }
        )
    with pytest.raises(ValidationError):
        store.update({"embedding": {"region": "us"}})
    with pytest.raises(ValidationError):
        store.update(
            {
                "embedding": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-rerank",
                }
            }
        )


def test_settings_rejects_non_loopback_callback(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    with pytest.raises(ValidationError):
        store.update(
            {
                "feishu": {
                    "redirect_uri": "https://example.invalid/api/v1/integrations/feishu/callback"
                }
            }
        )


def test_settings_accepts_user_registered_loopback_callback():
    settings = ProviderSettings.model_validate(
        {"feishu": {"app_id": "synthetic-app", "redirect_uri": "http://localhost:8765/callback"}}
    )
    assert settings.feishu.redirect_uri == "http://localhost:8765/callback"


def test_settings_updates_merge_across_concurrent_requests(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    patches = [
        {"llm": {"provider": "deepseek", "model": "deepseek-flash"}},
        {"feishu": {"app_id": "synthetic-app"}},
    ]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(store.update, patches))

    saved = SettingsStore(tmp_path / "settings.json").read()
    assert saved.llm.provider == "deepseek"
    assert saved.feishu.app_id == "synthetic-app"


def test_embedding_fingerprint_changes_with_provider_configuration():
    fake = ProviderSettings.model_validate({})
    real = ProviderSettings.model_validate(
        {"embedding": {"provider": "dashscope", "model": "qwen3.7-text-embedding"}}
    )
    assert embedding_fingerprint(fake.embedding) != embedding_fingerprint(real.embedding)
    assert embedding_fingerprint(real.embedding) == embedding_fingerprint(real.embedding)
    assert embedding_fingerprint(real.embedding, mode="fake") == "summit-fake-embedding-v1"


def test_model_studio_custom_account_hosts_are_local_settings_and_fingerprint_inputs():
    settings = ProviderSettings.model_validate(
        {
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "base_url": "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            },
            "rerank": {
                "provider": "dashscope",
                "model": "qwen3.7-text-rerank",
                "base_url": "https://workspace.cn-beijing.maas.aliyuncs.com/api/v1",
            },
        }
    )
    assert settings.embedding.base_url.endswith("/compatible-mode/v1")
    assert settings.rerank.base_url.endswith("/api/v1")
    assert embedding_fingerprint(settings.embedding) != embedding_fingerprint(
        ProviderSettings.model_validate(
            {
                "embedding": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-embedding",
                }
            }
        ).embedding
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        "https://attacker.invalid/compatible-mode/v1",
        "https://dashscope.aliyuncs.com/compatible-mode/v1?token=secret",
        "https://dashscope.aliyuncs.com/api/v1",
    ],
)
def test_embedding_endpoint_rejects_untrusted_or_wrong_paths(endpoint: str):
    with pytest.raises(ValidationError):
        ProviderSettings.model_validate(
            {
                "embedding": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-embedding",
                    "base_url": endpoint,
                }
            }
        )


def test_credential_vault_is_namespaced_and_never_reads_secret_for_status():
    backend = MemorySecretBackend()
    vault_a = CredentialVault("profile-a", backend)
    vault_b = CredentialVault("profile-b", backend)

    vault_a.put("deepseek", "synthetic-secret", account_id="work")

    assert vault_a.has("deepseek", account_id="work") is True
    assert vault_a.has("deepseek", account_id="personal") is False
    assert vault_b.has("deepseek", account_id="work") is False
    vault_a.delete("deepseek", account_id="work")
    assert vault_a.has("deepseek", account_id="work") is False


def test_credential_vault_rejects_unknown_provider_and_empty_secret():
    vault = CredentialVault("profile-a", MemorySecretBackend())
    with pytest.raises(SettingsError):
        vault.put("arbitrary", "synthetic-secret", account_id="work")
    with pytest.raises(SettingsError):
        vault.put("deepseek", "   ", account_id="work")
    with pytest.raises(SettingsError):
        vault.put("deepseek", "synthetic-secret", account_id=" ")
