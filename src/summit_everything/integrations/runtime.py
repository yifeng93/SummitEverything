"""Select model providers only when an explicit business operation is invoked."""

from __future__ import annotations

from summit_everything.integrations.embedding import FakeEmbedding, LocalBgeEmbedding
from summit_everything.integrations.llm import DeepSeekLLM, FakeLLM, LLMProviderError
from summit_everything.integrations.rerank import FakeReranker, LocalSemanticReranker
from summit_everything.integrations.settings import (
    CredentialVault,
    MacOSKeychainBackend,
    ProviderSettings,
    SettingsError,
)
from summit_everything.local.retrieval_model import LocalRetrievalModelStore


class ModelRuntime:
    def __init__(
        self,
        settings: ProviderSettings,
        vault: CredentialVault,
        local_models: LocalRetrievalModelStore | None = None,
    ) -> None:
        self.settings = settings
        self.vault = vault
        self.local_models = local_models

    def llm(self, *, max_tokens: int | None = None) -> FakeLLM | DeepSeekLLM:
        selected = self.settings.llm
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeLLM()
        if not selected.enabled:
            raise LLMProviderError("selected model provider is disabled")
        return DeepSeekLLM(
            self._credential("deepseek", selected.account_id),
            max_tokens=max_tokens or selected.max_output_tokens,
            reasoning_effort=selected.reasoning_effort,
        )

    def embedding(self) -> FakeEmbedding | LocalBgeEmbedding:
        selected = self.settings.embedding
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeEmbedding()
        if selected.provider == "dashscope":
            raise SettingsError("legacy_provider_migration_required")
        if not selected.enabled:
            raise SettingsError("provider_disabled")
        if self.local_models is None:
            raise SettingsError("local_model_not_ready")
        try:
            return self.local_models.embedding()
        except RuntimeError as exc:
            code = getattr(exc, "code", "local_model_not_ready")
            raise SettingsError(str(code)) from exc

    def reranker(self) -> FakeReranker | LocalSemanticReranker:
        selected = self.settings.rerank
        if self.settings.mode == "fake" or selected.provider == "fake":
            return FakeReranker()
        if selected.provider == "dashscope":
            raise SettingsError("legacy_provider_migration_required")
        if not selected.enabled:
            raise SettingsError("provider_disabled")
        if self.local_models is None:
            raise SettingsError("local_model_not_ready")
        try:
            embedding = self.local_models.embedding()
        except RuntimeError as exc:
            code = getattr(exc, "code", "local_model_not_ready")
            raise SettingsError(str(code)) from exc
        return LocalSemanticReranker(embedding)

    def _credential(self, provider: str, account_id: str) -> str:
        if not isinstance(self.vault.backend, MacOSKeychainBackend):
            raise SettingsError("credential_store_unavailable")
        secret = self.vault.get_secret(provider, account_id=account_id)
        if secret is None:
            raise SettingsError("credential_missing")
        return secret
