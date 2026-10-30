"""Local non-secret provider settings and fail-closed credential storage."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol, TypeVar, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from .first_use_defaults import FirstUseDefaults


class SettingsError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeishuSettings(_SettingsModel):
    app_id: str = Field(default="", max_length=200)
    redirect_uri: str = Field(default="", max_length=500)
    # Application identity is preferred; user identity is used only where the
    # documented endpoint requires user_access_token.
    identity: Literal["app", "user"] = "app"
    calendar_id: str = Field(default="", max_length=200)
    material_content: Literal["transcript", "artifacts"] = "transcript"
    # Kept for settings-file compatibility. This flag never authorizes a real read;
    # one-shot acceptance plans are required by the server routes.
    real_data_enabled: bool = False

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
    provider: Literal["fake", "deepseek"] = "deepseek"
    model: Literal["deepseek-flash"] | None = "deepseek-flash"
    account_id: str = Field(default="default", min_length=1, max_length=200)
    enabled: bool = True
    max_output_tokens: int = Field(default=2048, ge=256, le=16384)
    reasoning_effort: Literal["low", "high"] = "low"

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
    # ``dashscope`` remains readable for old profiles but is never a runtime
    # provider in the new local-retrieval path.
    provider: Literal["fake", "local", "dashscope"] = "local"
    model: (
        Literal["BAAI/bge-small-zh-v1.5", "qwen3.7-text-embedding", "qwen3.7-text-rerank"] | None
    ) = "BAAI/bge-small-zh-v1.5"
    # Only the Mainland endpoint is implemented and source-checked in this candidate.
    region: Literal["cn"] = "cn"
    dimensions: int = Field(default=512, ge=1, le=4096)
    base_url: str = ""
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def alibaba_model_studio_endpoint(cls, value: str) -> str:
        if not value:
            return value
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
    def supported_dimension(cls, value: int) -> int:
        if value not in {512, 1024}:
            raise ValueError("Only the supported local or legacy dimension is allowed")
        return value


class EmbeddingSettings(ModelStudioSettings):
    model: Literal["BAAI/bge-small-zh-v1.5", "qwen3.7-text-embedding"] | None = (
        "BAAI/bge-small-zh-v1.5"
    )
    base_url: str = ""
    expected_model: ClassVar[str] = "qwen3.7-text-embedding"

    @model_validator(mode="before")
    @classmethod
    def legacy_profile_defaults(cls, value: object) -> object:
        if isinstance(value, dict) and value.get("provider") == "dashscope":
            compatible = dict(value)
            compatible.setdefault("dimensions", 1024)
            compatible.setdefault("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            return compatible
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> EmbeddingSettings:
        if self.provider == "local":
            if self.model != "BAAI/bge-small-zh-v1.5" or self.dimensions != 512:
                raise ValueError("Select the pinned 512-dimensional local retrieval model")
            return self
        _validate_model_selection(self.provider, self.model, self.expected_model)
        if self.provider == "dashscope" and self.dimensions != 1024:
            raise ValueError("The legacy embedding configuration requires 1024 dimensions")
        if self.provider == "dashscope" and urlsplit(self.base_url).path != "/compatible-mode/v1":
            raise ValueError("Embedding requires the Model Studio compatible-mode base URL")
        return self


class RerankSettings(ModelStudioSettings):
    model: Literal["BAAI/bge-small-zh-v1.5", "qwen3.7-text-rerank"] | None = (
        "BAAI/bge-small-zh-v1.5"
    )
    expected_model: ClassVar[str] = "qwen3.7-text-rerank"

    @model_validator(mode="before")
    @classmethod
    def legacy_profile_defaults(cls, value: object) -> object:
        if isinstance(value, dict) and value.get("provider") == "dashscope":
            compatible = dict(value)
            compatible.setdefault("dimensions", 1024)
            compatible.setdefault("base_url", "https://dashscope.aliyuncs.com/api/v1")
            return compatible
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> RerankSettings:
        if self.provider == "local":
            if self.model != "BAAI/bge-small-zh-v1.5" or self.dimensions != 512:
                raise ValueError("Select the pinned local semantic ranking model")
            return self
        _validate_model_selection(self.provider, self.model, self.expected_model)
        if self.provider == "dashscope" and self.dimensions != 1024:
            raise ValueError("The legacy rerank configuration requires 1024 dimensions")
        if self.provider == "dashscope" and urlsplit(self.base_url).path != "/api/v1":
            raise ValueError("Rerank requires the Model Studio API base URL")
        return self


def _validate_model_selection(provider: str, model: str | None, expected_model: str) -> None:
    if provider == "fake" and model is not None:
        raise ValueError("Fake mode does not select a remote model")
    if provider == "dashscope" and model != expected_model:
        raise ValueError("Selected model does not match the legacy provider capability")


class ProviderSettings(_SettingsModel):
    mode: Literal["fake", "real"] = "real"
    # Runtime-only marker: legacy Fake profiles are surfaced as unconfigured
    # real settings and are never allowed to select a simulated provider.
    legacy_provider_migration_required: bool = Field(default=False, exclude=True)
    model_studio_account_id: str = Field(default="default", min_length=1, max_length=200)
    feishu: FeishuSettings = Field(default_factory=FeishuSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)


class CapabilityState(_SettingsModel):
    available: bool
    configured: bool
    disabled_reason: str | None


class ModelCallStatus(_SettingsModel):
    state: Literal["none", "succeeded", "failed", "unknown", "unreadable"] = "none"
    has_success: bool = False
    last_attempt_at: str | None = None
    last_success_at: str | None = None


class LocalModelStatus(_SettingsModel):
    model: str
    revision: str
    dimensions: int
    token_limit: int
    download_size_bytes: int
    state: Literal["not_prepared", "preparing", "ready", "failed", "incomplete"]
    downloaded_bytes: int
    progress_percent: int
    error_code: str | None


class SettingsSummary(_SettingsModel):
    mode: Literal["fake", "real"]
    legacy_provider_migration_required: bool = False
    model_studio_account_id: str
    feishu: FeishuSettings
    llm: LLMSettings
    embedding: EmbeddingSettings
    rerank: RerankSettings
    capabilities: dict[str, CapabilityState]
    credential_status: dict[str, bool]
    keychain_available: bool
    embedding_fingerprint: str
    model_call_status: ModelCallStatus = Field(default_factory=ModelCallStatus)
    local_model: LocalModelStatus


class FeishuSettingsPatch(_SettingsModel):
    app_id: str | None = Field(default=None, max_length=200)
    redirect_uri: str | None = Field(default=None, max_length=500)
    identity: Literal["app", "user"] | None = None
    calendar_id: str | None = Field(default=None, max_length=200)
    material_content: Literal["transcript", "artifacts"] | None = None
    real_data_enabled: bool | None = None


class LLMSettingsPatch(_SettingsModel):
    provider: Literal["deepseek"] | None = None
    model: Literal["deepseek-flash"] | None = None
    account_id: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    max_output_tokens: int | None = Field(default=None, ge=256, le=16384)
    reasoning_effort: Literal["low", "high"] | None = None


class ModelStudioSettingsPatch(_SettingsModel):
    # Legacy DashScope and Fake choices remain readable in stored profiles,
    # but new settings writes can select only the local model.
    provider: Literal["local"] | None = None
    model: Literal["BAAI/bge-small-zh-v1.5"] | None = None
    region: Literal["cn"] | None = None
    dimensions: int | None = Field(default=None, ge=1, le=4096)
    base_url: str | None = None
    enabled: bool | None = None


class ProviderSettingsPatch(_SettingsModel):
    mode: Literal["real"] | None = None
    model_studio_account_id: str | None = Field(default=None, min_length=1, max_length=200)
    feishu: FeishuSettingsPatch | None = None
    llm: LLMSettingsPatch | None = None
    embedding: ModelStudioSettingsPatch | None = None
    rerank: ModelStudioSettingsPatch | None = None


class SettingsStore:
    """Atomic local profile settings store. It never performs network I/O.

    ``defaults`` optionally supplies injected non-secret first-use values. They
    fill fields that the stored profile leaves absent or empty, and the profile
    stores only explicit user overrides: a value equal to the current injected
    default is dropped on save, so an untouched profile keeps following later
    default changes while an explicit override stays fixed.
    """

    def __init__(
        self,
        path: Path,
        *,
        defaults: FirstUseDefaults | None = None,
        allow_test_fake: bool = False,
    ) -> None:
        self.path = path
        self._defaults = defaults
        self._allow_test_fake = allow_test_fake

    def read(self) -> ProviderSettings:
        raw = self._read_raw()
        if self._defaults is not None:
            raw = self._defaults.apply(raw)
        legacy_provider = not self._allow_test_fake and _contains_legacy_provider_configuration(raw)
        if legacy_provider:
            raw = _migrate_legacy_provider_configuration(raw)
        try:
            settings = ProviderSettings.model_validate(raw)
            return settings.model_copy(
                update={"legacy_provider_migration_required": legacy_provider}
            )
        except (OSError, ValueError) as exc:
            raise SettingsError("settings_unavailable") from exc

    def _read_raw(self) -> object:
        try:
            if not self.path.exists():
                return {}
            return json.loads(self.path.read_bytes())
        except (OSError, ValueError) as exc:
            raise SettingsError("settings_unavailable") from exc

    def update(self, patch: dict[str, object]) -> ProviderSettings:
        if not self._allow_test_fake and _contains_non_delivery_provider_selection(patch):
            raise SettingsError("provider_not_allowed")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                return self._update_locked(patch)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _update_locked(self, patch: dict[str, object]) -> ProviderSettings:
        # Imported here because first_use_defaults imports this module.
        from .first_use_defaults import stored_document

        # read() keeps its stored+injected semantics and also preserves the
        # existing error behaviour for a corrupted profile.
        effective = self.read().model_dump(mode="json")
        merged = _merge(effective, patch)
        if self._defaults is not None:
            # Submitting "" for an injectable field means "not set": fall back to
            # the injected default before validation, exactly like a read would.
            merged = cast(dict[str, object], self._defaults.apply(merged))
        settings = ProviderSettings.model_validate(merged)
        # The profile stores only explicit user overrides: injected-equal and
        # empty injectable fields are dropped, never written as "".
        persisted = stored_document(settings.model_dump(mode="json"), defaults=self._defaults)
        ProviderSettings.model_validate(persisted)
        fd, temp_name = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(json.dumps(persisted, ensure_ascii=False, indent=2).encode())
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


def _contains_legacy_provider_configuration(raw: object) -> bool:
    if not isinstance(raw, dict):
        return False
    if raw.get("mode") == "fake":
        return True
    llm = raw.get("llm")
    if isinstance(llm, dict) and llm.get("provider") == "fake":
        return True
    return any(
        isinstance(raw.get(section), dict) and raw[section].get("provider") in {"fake", "dashscope"}
        for section in ("embedding", "rerank")
    )


def _contains_non_delivery_provider_selection(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("mode") == "fake":
        return True
    if isinstance(value.get("llm"), dict) and value["llm"].get("provider") == "fake":
        return True
    return any(
        isinstance(value.get(section), dict)
        and value[section].get("provider") in {"fake", "dashscope"}
        for section in ("embedding", "rerank")
    )


def _migrate_legacy_provider_configuration(raw: object) -> object:
    """Map stored non-delivery providers to real providers that report setup gaps."""
    if not isinstance(raw, dict):
        return raw
    migrated = {
        key: dict(value) if isinstance(value, dict) else value for key, value in raw.items()
    }
    migrated["mode"] = "real"
    llm = migrated.get("llm")
    llm = dict(llm) if isinstance(llm, dict) else {}
    if llm.get("provider") == "fake":
        llm.update(provider="deepseek", model="deepseek-flash", enabled=True)
    migrated["llm"] = llm
    for section in ("embedding", "rerank"):
        model_settings = migrated.get(section)
        model_settings = dict(model_settings) if isinstance(model_settings, dict) else {}
        if model_settings.get("provider") in {"fake", "dashscope"}:
            model_settings.update(
                provider="local",
                model="BAAI/bge-small-zh-v1.5",
                dimensions=512,
                enabled=True,
                base_url="",
            )
        migrated[section] = model_settings
    return migrated


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
    PROVIDERS = {"feishu_app", "feishu_user", "deepseek", "dashscope"}

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
    settings: ProviderSettings,
    vault: CredentialVault,
    *,
    local_model_status: dict[str, object] | None = None,
    legacy_provider_migration_required: bool = False,
    feishu_calendar_ready: bool | None = None,
    model_call_status: dict[str, object] | None = None,
) -> SettingsSummary:
    """Build a safe, user-facing status summary without exposing secret metadata."""
    keychain_available = isinstance(vault.backend, (MemorySecretBackend, MacOSKeychainBackend))
    credential_status: dict[str, bool] = {}
    # Only user-entered secrets are reported in the settings UI. The Feishu
    # user token lives in the same vault but is created by the OAuth flow.
    reported_providers = ("feishu_app", "deepseek", "dashscope")
    accounts = {
        "feishu_app": settings.feishu.app_id or "default",
        "deepseek": settings.llm.account_id,
        "dashscope": settings.model_studio_account_id,
    }
    for provider in reported_providers:
        try:
            credential_status[provider] = vault.has(provider, account_id=accounts[provider])
        except SettingsError:
            keychain_available = False
            credential_status[provider] = False
    disabled = {"available": False, "configured": False}
    feishu_app_configured = bool(settings.feishu.app_id) and credential_status.get(
        "feishu_app", False
    )
    feishu_ready = settings.mode == "real" and feishu_app_configured
    feishu_reason = (
        "stage_c_authorization_required"
        if feishu_ready
        else "offline_default"
        if settings.mode == "fake"
        else "provider_not_configured"
    )
    llm_configured = settings.llm.provider == "deepseek" and credential_status.get(
        "deepseek", False
    )
    local_model = LocalModelStatus.model_validate(
        local_model_status
        or {
            "model": "BAAI/bge-small-zh-v1.5",
            "revision": "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59",
            "dimensions": 512,
            "token_limit": 512,
            "download_size_bytes": 95_330_972,
            "state": "not_prepared",
            "downloaded_bytes": 0,
            "progress_percent": 0,
            "error_code": None,
        }
    )
    local_model_ready = local_model.state == "ready"

    def local_capability(provider: str, enabled: bool) -> tuple[bool, str | None]:
        if provider == "dashscope":
            return False, "legacy_provider_migration_required"
        if provider != "local":
            return False, "local_model_not_selected"
        if not local_model_ready:
            return False, {
                "not_prepared": "local_model_not_prepared",
                "preparing": "local_model_preparing",
                "failed": "local_model_failed",
                "incomplete": "local_model_incomplete",
            }.get(local_model.state, "local_model_not_prepared")
        if not enabled:
            return True, "local_provider_disabled"
        return True, None

    embedding_configured, embedding_reason = local_capability(
        settings.embedding.provider, settings.embedding.enabled
    )
    rerank_configured, rerank_reason = local_capability(
        settings.rerank.provider, settings.rerank.enabled
    )
    capabilities = {
        key: CapabilityState(**disabled, disabled_reason=reason)
        for key, reason in {
            "feishu_material_read": feishu_reason,
            "feishu_calendar_read": feishu_reason,
            "feishu_task_read": feishu_reason,
            "feishu_task_write": feishu_reason,
            "llm": (
                "acceptance_plan_required"
                if llm_configured and settings.mode == "real" and settings.llm.enabled
                else "provider_disabled"
                if llm_configured and not settings.llm.enabled
                else "offline_default"
                if settings.llm.provider == "fake"
                else "provider_not_configured"
            ),
            "embedding": embedding_reason,
            "rerank": rerank_reason,
        }.items()
    }
    capabilities["llm"] = CapabilityState(
        available=False,
        configured=llm_configured,
        disabled_reason=capabilities["llm"].disabled_reason,
    )
    capabilities["embedding"] = CapabilityState(
        available=embedding_configured and settings.embedding.enabled,
        configured=embedding_configured,
        disabled_reason=capabilities["embedding"].disabled_reason,
    )
    capabilities["rerank"] = CapabilityState(
        available=rerank_configured and settings.rerank.enabled,
        configured=rerank_configured,
        disabled_reason=capabilities["rerank"].disabled_reason,
    )
    # Calendar is a bounded, read-only capability guarded by the configured
    # Feishu identity and scopes at the provider boundary. Other data reads
    # still require a matching confirmed one-shot acceptance plan. For user
    # identity, inspect only the local vault record needed to avoid claiming
    # connectivity from app configuration alone.
    feishu_executable = False
    for name in ("feishu_material_read", "feishu_task_read"):
        capabilities[name] = CapabilityState(
            available=feishu_executable,
            configured=feishu_ready,
            disabled_reason=(None if feishu_executable else "acceptance_plan_required"),
        )
    calendar_user_ready = False
    calendar_user_configured = False
    calendar_user_refreshable = False
    if settings.mode == "real" and settings.feishu.identity == "user" and settings.feishu.app_id:
        try:
            from summit_everything.integrations.feishu.provider import UserCredentials

            raw = vault.get_secret("feishu_user", account_id=settings.feishu.app_id)
            credentials = UserCredentials.model_validate_json(raw) if raw else None
            if credentials is not None:
                has_calendar_scope = bool(
                    {
                        "calendar:calendar.event:read",
                        "calendar:calendar:read",
                        "calendar:calendar:readonly",
                    }
                    & set(credentials.scopes)
                )
                calendar_user_configured = has_calendar_scope
                calendar_user_refreshable = bool(credentials.refresh_token) and not (
                    credentials.refresh_consumed
                )
                current_or_refreshable = credentials.expires_at > time.time() or (
                    calendar_user_refreshable and feishu_app_configured
                )
                calendar_user_ready = has_calendar_scope and current_or_refreshable
        except Exception:
            calendar_user_ready = False
    calendar_configured = settings.mode == "real" and (
        feishu_calendar_ready is True
        or (
            bool(settings.feishu.app_id)
            and (
                feishu_app_configured
                if settings.feishu.identity == "app"
                else calendar_user_configured
            )
        )
    )
    calendar_enabled = (
        feishu_calendar_ready
        if feishu_calendar_ready is not None
        else (feishu_ready if settings.feishu.identity == "app" else calendar_user_ready)
    ) and settings.mode == "real"
    if calendar_enabled:
        calendar_disabled_reason = None
    elif settings.mode == "fake":
        calendar_disabled_reason = "offline_default"
    elif (
        not settings.feishu.app_id
        or (settings.feishu.identity == "app" and not feishu_app_configured)
        or (
            settings.feishu.identity == "user"
            and calendar_user_configured
            and calendar_user_refreshable
            and not feishu_app_configured
        )
    ):
        calendar_disabled_reason = "provider_not_configured"
    else:
        calendar_disabled_reason = "stage_c_authorization_required"
    capabilities["feishu_calendar_read"] = CapabilityState(
        available=calendar_enabled,
        configured=calendar_configured,
        disabled_reason=calendar_disabled_reason,
    )
    # Task writes additionally require an independently verifiable result, which
    # no documented endpoint provides, so they stay unavailable.
    capabilities["feishu_task_write"] = CapabilityState(
        available=False,
        configured=feishu_ready,
        disabled_reason="result_proof_unavailable" if feishu_ready else feishu_reason,
    )
    return SettingsSummary(
        mode=settings.mode,
        legacy_provider_migration_required=legacy_provider_migration_required,
        model_studio_account_id=settings.model_studio_account_id,
        feishu=settings.feishu,
        llm=settings.llm,
        embedding=settings.embedding,
        rerank=settings.rerank,
        capabilities=capabilities,
        credential_status=credential_status,
        keychain_available=keychain_available,
        embedding_fingerprint=embedding_fingerprint(settings.embedding, mode=settings.mode),
        local_model=local_model,
        model_call_status=ModelCallStatus.model_validate(model_call_status or {}),
    )


CredentialProvider = Literal["feishu_app", "deepseek", "dashscope"]


def embedding_fingerprint(settings: EmbeddingSettings, *, mode: str = "real") -> str:
    if mode == "fake" or settings.provider == "fake":
        return "summit-fake-embedding-v1"
    if settings.provider == "local":
        identity = {
            "provider": "local",
            "model": "BAAI/bge-small-zh-v1.5",
            "revision": "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59",
            "dimensions": 512,
            "token_window": 480,
            "token_overlap": 64,
            "window_aggregation": "token_weighted_mean_l2_v1",
            "chunking": "chunk_markdown_v1",
        }
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()
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
