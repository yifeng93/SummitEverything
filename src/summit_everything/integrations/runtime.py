"""Select model providers only when an explicit business operation is invoked."""

from __future__ import annotations

from summit_everything.integrations.embedding import FakeEmbedding, ModelStudioEmbedding
from summit_everything.integrations.llm import DeepSeekLLM, FakeLLM, LLMProviderError
from summit_everything.integrations.rerank import FakeReranker, ModelStudioReranker
from summit_everything.integrations.settings import (
    CredentialVault,
    MacOSKeychainBackend,
    ProviderSettings,
    SettingsError,
)


class ModelRuntime:
    def __init__(self, settings: ProviderSettings, vault: CredentialVault) -> None:
        self.settings = settings
        self.vault = vault

    def llm(self) -> FakeLLM | DeepSeekLLM:
        selected = self.settings.llm
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeLLM()
        if not selected.enabled:
            raise LLMProviderError("selected model provider is disabled")
        return DeepSeekLLM(self._credential("deepseek", selected.account_id))

    def embedding(self) -> FakeEmbedding | ModelStudioEmbedding:
        selected = self.settings.embedding
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeEmbedding()
        if not selected.enabled:
            raise SettingsError("provider_disabled")
        return ModelStudioEmbedding(
            self._credential("dashscope", self.settings.model_studio_account_id),
            base_url=selected.base_url,
        )

    def reranker(self) -> FakeReranker | ModelStudioReranker:
        selected = self.settings.rerank
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeReranker()
        if not selected.enabled:
            raise SettingsError("provider_disabled")
        return ModelStudioReranker(
            self._credential("dashscope", self.settings.model_studio_account_id),
            base_url=selected.base_url,
        )

    def _credential(self, provider: str, account_id: str) -> str:
        if not isinstance(self.vault.backend, MacOSKeychainBackend):
            raise SettingsError("credential_store_unavailable")
        secret = self.vault.get_secret(provider, account_id=account_id)
        if secret is None:
            raise SettingsError("credential_missing")
        return secret
