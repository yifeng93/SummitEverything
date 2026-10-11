"""Validated provider boundary, configuration and secret storage contracts."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from summit_everything.integrations.settings import CredentialVault, SecretBackend

if TYPE_CHECKING:
    from summit_everything.integrations.feishu.tasks import (
        FeishuTask,
        TaskExecutionEvidence,
        TaskPage,
    )

CALLBACK_PATH = "/api/v1/integrations/feishu/callback"


class FeishuError(Exception):
    MESSAGES = {
        "authorization_denied": (403, "授权已取消，请重新授权或使用文字导入。"),
        "token_expired": (401, "飞书授权已过期，请重新授权。"),
        "not_authorized": (401, "请先授权飞书，或使用文字导入。"),
        "missing_scope": (403, "缺少飞书读取权限，请检查应用权限并重新授权。"),
        "not_found": (404, "材料不存在或已不可见，请刷新列表。"),
        "malformed_response": (502, "飞书返回的材料格式无法读取，请使用 UTF-8 TXT 或 Markdown。"),
        "provider_timeout": (503, "飞书读取超时，请稍后重试。"),
        "provider_unavailable": (503, "飞书暂不可用，请稍后重试。"),
        "invalid_state": (400, "授权链接无效、已使用或已过期，请重新发起授权。"),
        "invalid_redirect": (400, "授权回调地址与配置不一致，请检查本机启动地址。"),
        "invalid_cursor": (422, "分页标记无效，请刷新列表。"),
        "credential_missing": (503, "尚未在本机保存飞书应用密钥，请先在设置中配置。"),
        "credential_unreadable": (
            401,
            "本机保存的飞书用户凭据无法读取，请重新授权。",
        ),
        "unsupported_capability": (
            422,
            "该筛选条件在真实飞书接口中没有对应参数，请清空筛选后重试。",
        ),
        "result_proof_unavailable": (
            409,
            "真实飞书任务写缺少可独立核实的结果证明，当前保持禁用。",
        ),
        "no_primary_calendar": (404, "未找到可用的主日历，请在本机设置中指定日历 ID。"),
        "ambiguous_calendar": (409, "主日历返回多个候选，无法唯一确定，请指定日历 ID。"),
    }

    def __init__(self, code: str) -> None:
        self.code = code if code in self.MESSAGES else "provider_unavailable"
        self.status_code, self.message = self.MESSAGES[self.code]
        super().__init__(self.message)


class FeishuConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: Literal["fake", "real"] = "fake"
    app_id: str = Field(default="synthetic-fake-app", min_length=1, max_length=200)
    redirect_uri: str = "http://127.0.0.1:5173" + CALLBACK_PATH
    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://127.0.0.1:8793")
    state_ttl_seconds: int = Field(default=300, ge=1, le=600)
    # Application identity is preferred; user identity is used only for the
    # endpoints that document user_access_token as the required token.
    identity: Literal["app", "user"] = "app"
    user_scopes: tuple[str, ...] = (
        "offline_access",
        "minutes:minutes.search:read",
        "minutes:minutes.transcript:export",
        "minutes:minutes.artifacts:read",
        "calendar:calendar.event:read",
        "task:task:read",
        "task:task:write",
    )
    calendar_id: str = ""
    material_content: Literal["transcript", "artifacts"] = "transcript"
    # Scope required by each capability. Fake uses the simulated scope names;
    # real mode swaps in the exact documented scope strings.
    scope_materials: str = "minutes:read"
    scope_calendar: str = "calendar:read"
    # Body download scopes. Real mode swaps in the exact documented values; the
    # transcript and artifacts endpoints carry different scopes, so a user
    # identity is accepted when it holds either one.
    scope_material_body: str = "minutes:read"
    scope_material_artifacts: str = "minutes:read"
    scope_tasks: str = "task:task:read"

    @field_validator("redirect_uri")
    @classmethod
    def safe_redirect(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"127.0.0.1", "::1", "localhost"}
            or parts.username
            or parts.password
            or parts.path not in {CALLBACK_PATH, "/callback"}
            or parts.query
            or parts.fragment
            or not parts.port
        ):
            raise ValueError("A registered loopback callback URI is required")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def safe_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            parts = urlsplit(value)
            if (
                parts.scheme != "http"
                or parts.hostname not in {"127.0.0.1", "::1", "localhost"}
                or parts.username
                or parts.password
                or parts.path
                or parts.query
                or parts.fragment
                or not parts.port
            ):
                raise ValueError("Only explicit loopback origins are allowed")
        return values


class AppCredentials(BaseModel):
    """Backend-only application identity and secret, separate from user tokens."""

    model_config = ConfigDict(extra="forbid")
    app_id: str = Field(min_length=1, max_length=200)
    app_secret: SecretStr = Field(repr=False)

    @field_validator("app_secret")
    @classmethod
    def nonempty_secret(cls, secret: SecretStr) -> SecretStr:
        if not secret.get_secret_value().strip():
            raise ValueError("Application secret must not be empty")
        return secret


class UserCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token_type: Literal["user"] = "user"
    access_token: str = Field(repr=False, min_length=1)
    refresh_token: str = Field(repr=False, min_length=1)
    expires_at: float
    scopes: list[str]


class CredentialStore(Protocol):
    def get(self) -> UserCredentials | None: ...
    def put(self, credentials: UserCredentials) -> None: ...
    def delete(self) -> None: ...
    def get_app(self) -> AppCredentials | None: ...
    def put_app(self, credentials: AppCredentials) -> None: ...


class MemoryCredentialStore:
    """Process-only fake credentials; never writes to workspace/profile."""

    def __init__(self) -> None:
        self._credentials: UserCredentials | None = None
        self._app_credentials: AppCredentials | None = None

    def get(self) -> UserCredentials | None:
        return self._credentials

    def put(self, credentials: UserCredentials) -> None:
        self._credentials = credentials

    def delete(self) -> None:
        self._credentials = None

    def get_app(self) -> AppCredentials | None:
        return self._app_credentials

    def put_app(self, credentials: AppCredentials) -> None:
        self._app_credentials = credentials


class VaultCredentialStore:
    """Feishu user tokens and app secret inside the shared CredentialVault.

    This is the single credential slot system: the app secret occupies the same
    ``feishu_app:<account hash>`` slot that the settings UI writes, and user
    tokens occupy ``feishu_user:<account hash>`` in the same profile namespace.
    The account identity is the Feishu app ID, so a different app or profile can
    never read another identity's tokens. No plaintext or in-memory fallback
    exists: the underlying SecretBackend fails closed on its own.
    """

    USER_PROVIDER = "feishu_user"
    APP_PROVIDER = "feishu_app"

    def __init__(self, vault: CredentialVault, app_id: str) -> None:
        if not app_id.strip() or len(app_id) > 200:
            raise ValueError("Feishu credential identity is invalid")
        self.vault = vault
        self.app_id = app_id
        self.account_id = app_id or "default"
        account_hash = hashlib.sha256(self.account_id.encode("utf-8")).hexdigest()
        self.user_item_key = f"{self.USER_PROVIDER}:{account_hash}"
        self.app_item_key = f"{self.APP_PROVIDER}:{account_hash}"

    def get(self) -> UserCredentials | None:
        value = self.vault.get_secret(self.USER_PROVIDER, account_id=self.account_id)
        if value is None:
            return None
        try:
            return UserCredentials.model_validate_json(value)
        except Exception:
            raise ValueError("stored Feishu credentials are invalid") from None

    def put(self, credentials: UserCredentials) -> None:
        self.vault.put(
            self.USER_PROVIDER, credentials.model_dump_json(), account_id=self.account_id
        )

    def delete(self) -> None:
        self.vault.delete(self.USER_PROVIDER, account_id=self.account_id)

    def get_app(self) -> AppCredentials | None:
        value = self.vault.get_secret(self.APP_PROVIDER, account_id=self.account_id)
        if value is None:
            return None
        try:
            return AppCredentials(app_id=self.account_id, app_secret=SecretStr(value))
        except Exception:
            raise ValueError("stored Feishu application credentials are invalid") from None

    def put_app(self, credentials: AppCredentials) -> None:
        if credentials.app_id != self.account_id:
            raise ValueError("Feishu application identity does not match this store")
        self.vault.put(
            self.APP_PROVIDER,
            credentials.app_secret.get_secret_value(),
            account_id=self.account_id,
        )


class KeychainCredentialStore:
    """Standalone Feishu token store over a SecretBackend.

    Retained as the offline contract for a private profile-scoped backend; the
    application itself uses :class:`VaultCredentialStore` so that the app
    secret and user token share one slot system with the settings secrets.
    """

    def __init__(self, profile: str, app_id: str, backend: SecretBackend) -> None:
        if not profile.strip() or len(profile) > 200:
            raise ValueError("Feishu credential identity is invalid")
        digest = hashlib.sha256(profile.encode("utf-8")).hexdigest()
        self.namespace = f"com.summiteverything.credentials.feishu.{digest}"
        self._store = VaultCredentialStore(CredentialVault(self.namespace, backend), app_id)
        self.user_item_key = self._store.user_item_key
        self.app_item_key = self._store.app_item_key

    def get(self) -> UserCredentials | None:
        return self._store.get()

    def put(self, credentials: UserCredentials) -> None:
        self._store.put(credentials)

    def delete(self) -> None:
        self._store.delete()

    def get_app(self) -> AppCredentials | None:
        return self._store.get_app()

    def put_app(self, credentials: AppCredentials) -> None:
        self._store.put_app(credentials)


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    kind: Literal["minute"] = "minute"
    visibility: Literal["owner", "shared"]
    # The documented search response carries no modification time; keep it
    # optional instead of inventing one.
    updated_at: datetime | None = None


class MaterialPage(BaseModel):
    items: list[Material]
    next_cursor: str | None = None


class MaterialBody(BaseModel):
    raw: bytes = Field(repr=False)
    filename: str
    content_type: str


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    start: datetime
    end: datetime


class CalendarPage(BaseModel):
    items: list[CalendarEvent]
    next_cursor: str | None = None
    timezone: str
    # True when the explicit range returned more events than the caller asked
    # for. A real explicit-range query cannot page, so this is a display hint,
    # never a promise that a next page exists.
    truncated: bool = False


class FeishuProvider(Protocol):
    def authorization_url(self, redirect_uri: str, state: str) -> str: ...
    def exchange(
        self, code: str, redirect_uri: str, app_credentials: AppCredentials | None = None
    ) -> UserCredentials: ...
    def refresh(self, credentials: UserCredentials) -> UserCredentials: ...
    def materials(
        self,
        credentials: UserCredentials,
        query: str,
        visibility: str | None,
        cursor: str | None,
        limit: int,
    ) -> MaterialPage: ...
    def body(self, credentials: UserCredentials | None, material_id: str) -> MaterialBody: ...
    def calendar(
        self,
        credentials: UserCredentials | None,
        start: datetime,
        end: datetime,
        timezone: str,
        cursor: str | None,
        limit: int,
    ) -> CalendarPage: ...

    def tasks(self, credentials: UserCredentials, cursor: str | None, limit: int) -> TaskPage: ...
    def task_get(self, credentials: UserCredentials | None, guid: str) -> FeishuTask: ...
    def task_create(
        self, credentials: UserCredentials | None, body: dict[str, Any]
    ) -> FeishuTask: ...
    def task_patch(
        self,
        credentials: UserCredentials | None,
        guid: str,
        body: dict[str, Any],
        token: str,
    ) -> FeishuTask: ...
    def task_result(
        self, credentials: UserCredentials, token: str
    ) -> TaskExecutionEvidence | None: ...
