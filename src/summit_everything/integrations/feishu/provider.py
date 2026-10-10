"""Validated provider boundary, configuration and secret storage contracts."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from summit_everything.integrations.settings import SecretBackend

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
    }

    def __init__(self, code: str) -> None:
        self.code = code if code in self.MESSAGES else "provider_unavailable"
        self.status_code, self.message = self.MESSAGES[self.code]
        super().__init__(self.message)


class FeishuConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: Literal["fake"] = "fake"
    app_id: str = Field(default="synthetic-fake-app", min_length=1, max_length=200)
    redirect_uri: str = "http://127.0.0.1:5173" + CALLBACK_PATH
    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://127.0.0.1:8793")
    state_ttl_seconds: int = Field(default=300, ge=1, le=600)

    @field_validator("redirect_uri")
    @classmethod
    def safe_redirect(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"127.0.0.1", "::1", "localhost"}
            or parts.username
            or parts.password
            or parts.path != CALLBACK_PATH
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


class KeychainCredentialStore:
    """Persist Feishu user tokens and app secret through a SecretBackend.

    The backend is expected to be an OS credential store in application mode.
    Account item names contain only a digest of the Feishu app ID so neither
    tokens nor app identity are written to ordinary workspace files.
    """

    def __init__(self, profile: str, app_id: str, backend: SecretBackend) -> None:
        if not profile.strip() or len(profile) > 200 or not app_id.strip() or len(app_id) > 200:
            raise ValueError("Feishu credential identity is invalid")
        self.namespace = f"{profile}:feishu"
        self.backend = backend
        app_hash = hashlib.sha256(app_id.encode("utf-8")).hexdigest()
        self.user_item_key = f"user:{app_hash}"
        self.app_item_key = f"app:{app_hash}"
        self._app_id = app_id

    def get(self) -> UserCredentials | None:
        value = self.backend.get(self.namespace, self.user_item_key)
        if value is None:
            return None
        try:
            return UserCredentials.model_validate_json(value)
        except Exception:
            raise ValueError("stored Feishu credentials are invalid") from None

    def put(self, credentials: UserCredentials) -> None:
        self.backend.set(
            self.namespace,
            self.user_item_key,
            credentials.model_dump_json(),
        )

    def delete(self) -> None:
        self.backend.delete(self.namespace, self.user_item_key)

    def get_app(self) -> AppCredentials | None:
        value = self.backend.get(self.namespace, self.app_item_key)
        if value is None:
            return None
        try:
            secret = SecretStr(value)
            return AppCredentials(app_id=self._app_id, app_secret=secret)
        except Exception:
            raise ValueError("stored Feishu application credentials are invalid") from None

    def put_app(self, credentials: AppCredentials) -> None:
        if credentials.app_id != self._app_id:
            raise ValueError("Feishu application identity does not match this store")
        self.backend.set(
            self.namespace,
            self.app_item_key,
            credentials.app_secret.get_secret_value(),
        )


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    kind: Literal["minute"] = "minute"
    visibility: Literal["owner", "shared"]
    updated_at: datetime


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
    def body(self, credentials: UserCredentials, material_id: str) -> MaterialBody: ...
    def calendar(
        self,
        credentials: UserCredentials,
        start: datetime,
        end: datetime,
        timezone: str,
        cursor: str | None,
        limit: int,
    ) -> CalendarPage: ...

    def tasks(self, credentials: UserCredentials, cursor: str | None, limit: int) -> TaskPage: ...
    def task_get(self, credentials: UserCredentials, guid: str) -> FeishuTask: ...
    def task_create(self, credentials: UserCredentials, body: dict[str, Any]) -> FeishuTask: ...
    def task_patch(
        self, credentials: UserCredentials, guid: str, body: dict[str, Any], token: str
    ) -> FeishuTask: ...
    def task_result(
        self, credentials: UserCredentials, token: str
    ) -> TaskExecutionEvidence | None: ...
