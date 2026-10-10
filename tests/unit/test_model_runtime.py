import pytest

from summit_everything.integrations.embedding import FakeEmbedding, ModelStudioEmbedding
from summit_everything.integrations.llm import DeepSeekLLM, FakeLLM, LLMProviderError
from summit_everything.integrations.rerank import FakeReranker, ModelStudioReranker
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


def test_real_mode_constructs_selected_adapters_without_network_requests():
    settings = ProviderSettings.model_validate(
        {
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
        }
    )
    vault = CredentialVault("profile", StubKeychain({}))
    vault.put("deepseek", "synthetic-key")
    vault.put("dashscope", "synthetic-key")
    runtime = ModelRuntime(settings, vault)

    assert isinstance(runtime.llm(), DeepSeekLLM)
    assert isinstance(runtime.embedding(), ModelStudioEmbedding)
    assert isinstance(runtime.reranker(), ModelStudioReranker)


def test_real_mode_rejects_remote_provider_when_not_enabled():
    settings = ProviderSettings.model_validate(
        {"mode": "real", "llm": {"provider": "deepseek", "model": "deepseek-flash"}}
    )
    runtime = ModelRuntime(settings, CredentialVault("profile", StubKeychain({})))
    with pytest.raises(LLMProviderError, match="disabled"):
        runtime.llm()
