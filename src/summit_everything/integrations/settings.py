"""Local non-secret provider settings and fail-closed credential storage."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Literal, Protocol, TypeVar, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SettingsError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeishuSettings(_SettingsModel):
    app_id: str = Field(default="", max_length=200)
    redirect_uri: str = Field(default="", max_length=500)

    @field_validator("redirect_uri")
    @classmethod
    def registered_loopback_uri(cls, value: str) -> str:
        if not value:
            return value
        parts = urlsplit(value)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"127.0.0.1", "::1", "localhost"}
            or not parts.port
            or parts.username
            or parts.password
            or parts.path not in {"/api/v1/integrations/feishu/callback", "/callback"}
            or parts.query
            or parts.fragment
        ):
            raise ValueError("A registered local callback URI is required")
        return value


class LLMSettings(_SettingsModel):
    provider: Literal["fake", "deepseek"] = "fake"
    model: Literal["deepseek-flash"] | None = None
    account_id: str = Field(default="default", min_length=1, max_length=200)
    enabled: bool = False

    @field_validator("model")
    @classmethod
    def model_matches_provider(cls, value: str | None, info):  # type: ignore[no-untyped-def]
        provider = info.data.get("provider", "fake")
        if provider == "fake" and value is not None:
            raise ValueError("Fake mode does not select a remote model")
        if provider == "deepseek" and value is None:
            raise ValueError("Select the supported DeepSeek model")
        return value


class ModelStudioSettings(_SettingsModel):
    provider: Literal["fake", "dashscope"] = "fake"
    model: Literal["qwen3.7-text-embedding", "qwen3.7-text-rerank"] | None = None
    # Only the Mainland endpoint is implemented and source-checked in this candidate.
    region: Literal["cn"] = "cn"
    dimensions: int = Field(default=1024, ge=1, le=4096)
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    enabled: bool = False

    @field_validator("base_url")
    @classmethod
    def alibaba_model_studio_endpoint(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or not (parts.hostname == "aliyuncs.com" or parts.hostname.endswith(".aliyuncs.com"))
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.port
        ):
            raise ValueError("Model Studio base URL must use an Alibaba Cloud HTTPS host")
        if parts.path not in {"/api/v1", "/compatible-mode/v1"}:
            raise ValueError("Model Studio base URL path is not supported")
        return value.rstrip("/")

    @field_validator("dimensions")
    @classmethod
    def documented_dimension(cls, value: int) -> int:
        if value != 1024:
            raise ValueError("Only the documented 1024 dimension is supported")
        return value


class EmbeddingSettings(ModelStudioSettings):
    model: Literal["qwen3.7-text-embedding"] | None = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    expected_model: ClassVar[str] = "qwen3.7-text-embedding"

    @model_validator(mode="after")
    def validate_selection(self) -> EmbeddingSettings:
        _validate_model_selection(self.provider, self.model, self.expected_model)
        if urlsplit(self.base_url).path != "/compatible-mode/v1":
            raise ValueError("Embedding requires the Model Studio compatible-mode base URL")
        return self


class RerankSettings(ModelStudioSettings):
    model: Literal["qwen3.7-text-rerank"] | None = None
    expected_model: ClassVar[str] = "qwen3.7-text-rerank"

    @model_validator(mode="after")
    def validate_selection(self) -> RerankSettings:
        _validate_model_selection(self.provider, self.model, self.expected_model)
        if urlsplit(self.base_url).path != "/api/v1":
            raise ValueError("Rerank requires the Model Studio API base URL")
        return self


def _validate_model_selection(provider: str, model: str | None, expected_model: str) -> None:
    if provider == "fake" and model is not None:
        raise ValueError("Fake mode does not select a remote model")
    if provider == "dashscope" and model != expected_model:
        raise ValueError("Selected model does not match the provider capability")


class ProviderSettings(_SettingsModel):
    mode: Literal["fake", "real"] = "fake"
    model_studio_account_id: str = Field(default="default", min_length=1, max_length=200)
    feishu: FeishuSettings = Field(default_factory=FeishuSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)


class CapabilityState(_SettingsModel):
    available: bool
    configured: bool
    disabled_reason: str | None


class SettingsSummary(_SettingsModel):
    mode: Literal["fake", "real"]
    model_studio_account_id: str
    feishu: FeishuSettings
    llm: LLMSettings
    embedding: EmbeddingSettings
    rerank: RerankSettings
    capabilities: dict[str, CapabilityState]
    credential_status: dict[str, bool]
    keychain_available: bool
    embedding_fingerprint: str


class FeishuSettingsPatch(_SettingsModel):
    app_id: str | None = Field(default=None, max_length=200)
    redirect_uri: str | None = Field(default=None, max_length=500)


class LLMSettingsPatch(_SettingsModel):
    provider: Literal["fake", "deepseek"] | None = None
    model: Literal["deepseek-flash"] | None = None
    account_id: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None


class ModelStudioSettingsPatch(_SettingsModel):
    provider: Literal["fake", "dashscope"] | None = None
    model: Literal["qwen3.7-text-embedding", "qwen3.7-text-rerank"] | None = None
    region: Literal["cn"] | None = None
    dimensions: int | None = Field(default=None, ge=1, le=4096)
    base_url: str | None = None
    enabled: bool | None = None


class ProviderSettingsPatch(_SettingsModel):
    mode: Literal["fake", "real"] | None = None
    model_studio_account_id: str | None = Field(default=None, min_length=1, max_length=200)
    feishu: FeishuSettingsPatch | None = None
    llm: LLMSettingsPatch | None = None
    embedding: ModelStudioSettingsPatch | None = None
    rerank: ModelStudioSettingsPatch | None = None


class SettingsStore:
    """Atomic local profile settings store. It never performs network I/O."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> ProviderSettings:
        try:
            if not self.path.exists():
                return ProviderSettings()
            return ProviderSettings.model_validate_json(self.path.read_bytes())
        except (OSError, ValueError) as exc:
            raise SettingsError("settings_unavailable") from exc

    def update(self, patch: dict[str, object]) -> ProviderSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                return self._update_locked(patch)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _update_locked(self, patch: dict[str, object]) -> ProviderSettings:
        current = self.read().model_dump(mode="json")
        merged = _merge(current, patch)
        settings = ProviderSettings.model_validate(merged)
        fd, temp_name = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(settings.model_dump_json(indent=2).encode())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return settings


def _merge(current: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    merged = dict(current)
    for key, value in patch.items():
        previous = merged.get(key)
        if isinstance(previous, dict) and isinstance(value, dict):
            merged[key] = _merge(previous, value)
        else:
            merged[key] = value
    return merged


class SecretBackend(Protocol):
    def get(self, namespace: str, key: str) -> str | None: ...
    def set(self, namespace: str, key: str, value: str) -> None: ...
    def delete(self, namespace: str, key: str) -> None: ...


class MemorySecretBackend:
    """Test-only credential store. Never select this for real application mode."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], str] = {}

    def get(self, namespace: str, key: str) -> str | None:
        return self._values.get((namespace, key))

    def set(self, namespace: str, key: str, value: str) -> None:
        self._values[(namespace, key)] = value

    def delete(self, namespace: str, key: str) -> None:
        self._values.pop((namespace, key), None)


class UnavailableSecretBackend:
    def get(self, namespace: str, key: str) -> str | None:
        raise SettingsError("credential_store_unavailable")

    def set(self, namespace: str, key: str, value: str) -> None:
        raise SettingsError("credential_store_unavailable")

    def delete(self, namespace: str, key: str) -> None:
        raise SettingsError("credential_store_unavailable")


class MacOSKeychainBackend:
    """Explicit macOS Keychain backend; other platforms fail closed."""

    def __init__(self) -> None:
        if platform.system() != "Darwin":
            raise SettingsError("credential_store_unavailable")
        try:
            from keyring.backends.macOS import Keyring

            self._keyring = Keyring()  # type: ignore[no-untyped-call]
        except Exception as exc:
            raise SettingsError("credential_store_unavailable") from exc

    def get(self, namespace: str, key: str) -> str | None:
        return cast(str | None, self._run(lambda: self._keyring.get_password(namespace, key)))

    def set(self, namespace: str, key: str, value: str) -> None:
        self._run(lambda: self._keyring.set_password(namespace, key, value))

    def delete(self, namespace: str, key: str) -> None:
        try:
            self._run(lambda: self._keyring.delete_password(namespace, key))
        except SettingsError as exc:
            if exc.code != "credential_not_found":
                raise

    @staticmethod
    def _run(operation: Callable[[], _Result]) -> _Result:
        try:
            return operation()
        except Exception as exc:
            # Do not leak Keychain prompts, item names or underlying exception text.
            code = (
                "credential_not_found"
                if "not found" in str(exc).casefold()
                else "credential_access_denied"
            )
            raise SettingsError(code) from exc


_Result = TypeVar("_Result")


class CredentialVault:
    PROVIDERS = {"feishu_app", "deepseek", "dashscope"}

    def __init__(self, namespace: str, backend: SecretBackend) -> None:
        self.namespace = namespace
        self.backend = backend

    def has(self, provider: str, *, account_id: str = "default") -> bool:
        self._validate_provider(provider)
        return self.backend.get(self.namespace, self._item_key(provider, account_id)) is not None

    def get_secret(self, provider: str, *, account_id: str = "default") -> str | None:
        self._validate_provider(provider)
        return self.backend.get(self.namespace, self._item_key(provider, account_id))

    def put(self, provider: str, secret: str, *, account_id: str = "default") -> None:
        self._validate_provider(provider)
        self._validate_account_id(account_id)
        if not secret or not secret.strip() or len(secret) > 20_000:
            raise SettingsError("validation_error")
        self.backend.set(self.namespace, self._item_key(provider, account_id), secret)

    def delete(self, provider: str, *, account_id: str = "default") -> None:
        self._validate_provider(provider)
        self._validate_account_id(account_id)
        self.backend.delete(self.namespace, self._item_key(provider, account_id))

    @staticmethod
    def _item_key(provider: str, account_id: str) -> str:
        CredentialVault._validate_account_id(account_id)
        account_hash = hashlib.sha256(account_id.encode("utf-8")).hexdigest()
        return f"{provider}:{account_hash}"

    @staticmethod
    def _validate_account_id(account_id: str) -> None:
        if not account_id.strip() or len(account_id) > 200:
            raise SettingsError("validation_error")

    @staticmethod
    def _validate_provider(provider: str) -> None:
        if provider not in CredentialVault.PROVIDERS:
            raise SettingsError("validation_error")


def provider_settings_payload(
    settings: ProviderSettings, vault: CredentialVault
) -> SettingsSummary:
    """Build a safe, user-facing status summary without exposing secret metadata."""
    keychain_available = isinstance(vault.backend, (MemorySecretBackend, MacOSKeychainBackend))
    credential_status: dict[str, bool] = {}
    accounts = {
        "feishu_app": settings.feishu.app_id or "default",
        "deepseek": settings.llm.account_id,
        "dashscope": settings.model_studio_account_id,
    }
    for provider in sorted(CredentialVault.PROVIDERS):
        try:
            credential_status[provider] = vault.has(provider, account_id=accounts[provider])
        except SettingsError:
            keychain_available = False
            credential_status[provider] = False
    disabled = {"available": False, "configured": False}
    llm_configured = settings.llm.provider == "deepseek" and credential_status.get(
        "deepseek", False
    )
    embedding_configured = settings.embedding.provider == "dashscope" and credential_status.get(
        "dashscope", False
    )
    rerank_configured = settings.rerank.provider == "dashscope" and credential_status.get(
        "dashscope", False
    )
    capabilities = {
        key: CapabilityState(**disabled, disabled_reason=reason)
        for key, reason in {
            "feishu_material_read": "oauth_protocol_unverified",
            "feishu_calendar_read": "protocol_unverified",
            "feishu_task_read": "protocol_unverified",
            "feishu_task_write": "date_and_result_proof_unverified",
            "llm": (
                "limited_synthetic_smoke_only"
                if llm_configured and settings.mode == "real"
                else "offline_default"
                if settings.llm.provider == "fake"
                else "provider_not_configured"
            ),
            "embedding": (
                "limited_synthetic_smoke_only"
                if embedding_configured and settings.mode == "real"
                else "offline_default"
                if settings.embedding.provider == "fake"
                else "provider_not_configured"
            ),
            "rerank": (
                "limited_synthetic_smoke_only"
                if rerank_configured and settings.mode == "real"
                else "offline_default"
                if settings.rerank.provider == "fake"
                else "provider_not_configured"
            ),
        }.items()
    }
    capabilities["llm"] = CapabilityState(
        available=False,
        configured=llm_configured,
        disabled_reason=capabilities["llm"].disabled_reason,
    )
    capabilities["embedding"] = CapabilityState(
        available=False,
        configured=embedding_configured,
        disabled_reason=capabilities["embedding"].disabled_reason,
    )
    capabilities["rerank"] = CapabilityState(
        available=False,
        configured=rerank_configured,
        disabled_reason=capabilities["rerank"].disabled_reason,
    )
    return SettingsSummary(
        mode=settings.mode,
        model_studio_account_id=settings.model_studio_account_id,
        feishu=settings.feishu,
        llm=settings.llm,
        embedding=settings.embedding,
        rerank=settings.rerank,
        capabilities=capabilities,
        credential_status=credential_status,
        keychain_available=keychain_available,
        embedding_fingerprint=embedding_fingerprint(settings.embedding, mode=settings.mode),
    )


CredentialProvider = Literal["feishu_app", "deepseek", "dashscope"]


def embedding_fingerprint(settings: EmbeddingSettings, *, mode: str = "real") -> str:
    if mode == "fake" or settings.provider == "fake":
        return "summit-fake-embedding-v1"
    identity = {
        "provider": settings.provider,
        "model": settings.model or "fake-hash-v1",
        "region": settings.region,
        "dimensions": settings.dimensions,
        "base_url": settings.base_url.rstrip("/"),
        "protocol_version": 1,
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
