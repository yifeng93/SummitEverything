import pytest

from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.integrations.rerank import FakeReranker
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import (
    CredentialVault,
    MacOSKeychainBackend,
    MemorySecretBackend,
    ProviderSettings,
    SettingsError,
)


class StubKeychain(MacOSKeychainBackend):
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values

    def get(self, namespace: str, key: str) -> str | None:
        return self.values.get((namespace, key))

    def set(self, namespace: str, key: str, value: str) -> None:
        self.values[(namespace, key)] = value

    def delete(self, namespace: str, key: str) -> None:
        self.values.pop((namespace, key), None)


def test_fake_mode_never_selects_remote_providers_even_if_configured():
    settings = ProviderSettings.model_validate(
        {
            "mode": "fake",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
            "embedding": {
                "provider": "fake",
                "model": None,
                "enabled": True,
            },
            "rerank": {
                "provider": "fake",
                "model": None,
                "enabled": True,
            },
        }
    )
    runtime = ModelRuntime(settings, CredentialVault("profile", MemorySecretBackend()))

    assert isinstance(runtime.llm(), FakeLLM)
    assert isinstance(runtime.embedding(), FakeEmbedding)
    assert isinstance(runtime.reranker(), FakeReranker)


def test_real_mode_fails_closed_for_memory_backend_and_missing_credentials():
    settings = ProviderSettings.model_validate(
        {
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
        }
    )
    memory_runtime = ModelRuntime(settings, CredentialVault("profile", MemorySecretBackend()))
    with pytest.raises(SettingsError, match="credential_store_unavailable"):
        memory_runtime.llm()

    keychain_runtime = ModelRuntime(settings, CredentialVault("profile", StubKeychain({})))
    with pytest.raises(SettingsError, match="credential_missing"):
        keychain_runtime.llm()


def test_legacy_retrieval_provider_profiles_remain_readable_but_runtime_refuses_them():
    settings = ProviderSettings.model_validate(
        {
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "dimensions": 1024,
                "enabled": True,
            },
            "rerank": {
                "provider": "dashscope",
                "model": "qwen3.7-text-rerank",
                "dimensions": 1024,
                "enabled": True,
            },
        }
    )
    assert settings.embedding.provider == "dashscope"
    assert settings.rerank.provider == "dashscope"
    runtime = ModelRuntime(settings, CredentialVault("profile", StubKeychain({})))

    with pytest.raises(SettingsError, match="legacy_provider_migration_required"):
        runtime.embedding()
    with pytest.raises(SettingsError, match="legacy_provider_migration_required"):
        runtime.reranker()


def test_real_mode_rejects_remote_provider_when_not_enabled():
    settings = ProviderSettings.model_validate(
        {
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": False},
        }
    )
    runtime = ModelRuntime(settings, CredentialVault("profile", StubKeychain({})))
    with pytest.raises(LLMProviderError, match="disabled"):
        runtime.llm()
