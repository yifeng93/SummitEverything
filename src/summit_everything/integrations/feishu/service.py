"""One-use local OAuth states and recoverable selected-material imports."""

from __future__ import annotations

import fcntl
import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path
from threading import Lock
from time import time
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationError

from summit_everything.intake.sources import IntakeConflict, SourceStore, safe_source_filename
from summit_everything.integrations.feishu.provider import (
    CalendarPage,
    CredentialStore,
    FeishuConfig,
    FeishuError,
    FeishuProvider,
    MaterialBody,
    MaterialPage,
    UserCredentials,
)
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.transactions import atomic_write


class FeishuStatus(BaseModel):
    mode: str = "fake"
    authorized: bool
    token_type: str = "user"
    scopes: list[str]


class AuthorizationStart(BaseModel):
    authorization_url: str
    expires_in_seconds: int


class ImportRequest(BaseModel):
    model_config = {"extra": "forbid"}
    material_ids: list[str] = Field(min_length=1, max_length=30)
    operation_id: str = Field(min_length=1, max_length=200)


class ImportOutcome(BaseModel):
    material_id: str
    state: str
    item_id: UUID | None = None
    source_id: UUID | None = None
    error_code: str | None = None
    message: str | None = None


class ImportResult(BaseModel):
    operation_id: str
    state: str
    outcomes: list[ImportOutcome]


class FeishuService:
    def __init__(
        self,
        provider: FeishuProvider,
        credentials: CredentialStore,
        config: FeishuConfig,
        session_identity: str,
        clock: Callable[[], float] = time,
    ) -> None:
        self.provider = provider
        self.credentials = credentials
        self.config = config
        self.session_identity = session_identity
        self.clock = clock
        self._states: dict[str, tuple[str, float]] = {}
        self._state_lock = Lock()

    def status(self) -> FeishuStatus:
        credentials = self.credentials.get()
        authorized = credentials is not None and credentials.expires_at > self.clock()
        return FeishuStatus(
            authorized=authorized, scopes=credentials.scopes if authorized and credentials else []
        )

    def authorize(self) -> AuthorizationStart:
        state = secrets.token_urlsafe(32)
        with self._state_lock:
            self._states = {
                key: value for key, value in self._states.items() if value[1] > self.clock()
            }
            self._states[state] = (
                self.session_identity,
                self.clock() + self.config.state_ttl_seconds,
            )
        return AuthorizationStart(
            authorization_url=self.provider.authorization_url(self.config.redirect_uri, state),
            expires_in_seconds=self.config.state_ttl_seconds,
        )

    def callback(
        self, state: str, code: str | None, error: str | None, callback_uri: str
    ) -> FeishuStatus:
        if callback_uri != self.config.redirect_uri:
            raise FeishuError("invalid_redirect")
        with self._state_lock:
            entry = self._states.pop(state, None)
        if entry is None or entry[0] != self.session_identity or entry[1] <= self.clock():
            raise FeishuError("invalid_state")
        if error is not None:
            raise FeishuError("authorization_denied")
        if not code:
            raise FeishuError("malformed_response")
        app_credentials = self.credentials.get_app()
        if app_credentials is not None and app_credentials.app_id != self.config.app_id:
            raise FeishuError("malformed_response")
        credentials = self._call(
            lambda: self.provider.exchange(code, self.config.redirect_uri, app_credentials)
        )
        if not isinstance(credentials, UserCredentials) or credentials.expires_at <= self.clock():
            raise FeishuError("malformed_response")
        self.credentials.put(credentials)
        return self.status()

    def _user(self, scope: str) -> UserCredentials:
        credentials = self.credentials.get()
        if credentials is None:
            raise FeishuError("not_authorized")
        if credentials.expires_at <= self.clock():
            raise FeishuError("token_expired")
        if credentials.token_type != "user" or scope not in credentials.scopes:
            raise FeishuError("missing_scope")
        return credentials

    def _call[T](self, call: Callable[[], T]) -> T:
        try:
            return call()
        except FeishuError:
            raise
        except TimeoutError:
            raise FeishuError("provider_timeout") from None
        except (ValueError, ValidationError, TypeError):
            raise FeishuError("malformed_response") from None
        except Exception:
            raise FeishuError("provider_unavailable") from None

    def materials(
        self, query: str, visibility: str | None, cursor: str | None, limit: int
    ) -> MaterialPage:
        user = self._user("minutes:read")
        result = self._call(lambda: self.provider.materials(user, query, visibility, cursor, limit))
        if not isinstance(result, MaterialPage) or len(result.items) > limit:
            raise FeishuError("malformed_response")
        return result

    def calendar(
        self, start: datetime, end: datetime, timezone: str, cursor: str | None, limit: int
    ) -> CalendarPage:
        try:
            ZoneInfo(timezone)
            if start.tzinfo is None or end.tzinfo is None or start >= end:
                raise ValueError()
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("请选择有效的起止时间和时区。") from None
        user = self._user("calendar:read")
        result = self._call(
            lambda: self.provider.calendar(user, start, end, timezone, cursor, limit)
        )
        if not isinstance(result, CalendarPage) or len(result.items) > limit:
            raise FeishuError("malformed_response")
        return result

    def imports(self, root: Path, payload: ImportRequest) -> ImportResult:
        ids = sorted(set(payload.material_ids))
        if any(not value.strip() or len(value) > 200 for value in ids):
            raise ValueError("请选择有效的飞书材料。")
        request_hash = hashlib.sha256(json.dumps(ids, ensure_ascii=False).encode()).hexdigest()
        key = hashlib.sha256(payload.operation_id.encode()).hexdigest()
        journal = root / ".summit-everything" / "transactions" / f"feishu-import-{key}.json"
        lock_path = root / ".summit-everything" / "feishu-import.lock"
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                intent: dict[str, Any] = (
                    json.loads(journal.read_bytes())
                    if journal.exists()
                    else {"request_hash": request_hash, "outcomes": {}, "state": "running"}
                )
                if intent["request_hash"] != request_hash:
                    raise IntakeConflict("导入操作已用于另一组材料，请重新选择。")
                if intent["state"] == "completed":
                    return ImportResult.model_validate(intent["result"])
                user = self._user("minutes:read")
                atomic_write(journal, json.dumps(intent).encode())
                for material_id in ids:
                    if material_id in intent["outcomes"]:
                        continue
                    try:
                        source_operation = f"feishu:{key}:{material_id}"
                        expected_item = uuid5(
                            load_manifest(root).workspace_id, f"intake:{source_operation}"
                        )
                        store = SourceStore()
                        item = next(
                            (
                                item
                                for item in store.list_items(root)
                                if item.item_id == expected_item
                            ),
                            None,
                        )
                        if item is None:
                            body = self._call(partial(self.provider.body, user, material_id))
                            self._validate_body(body)
                            item = store.capture(
                                root,
                                body.raw,
                                body.filename,
                                source_operation,
                                external_identity={
                                    "provider": "feishu-fake",
                                    "material_id": material_id,
                                    "token_type": "user",
                                    "content_type": body.content_type,
                                },
                            )
                        outcome = ImportOutcome(
                            material_id=material_id,
                            state="succeeded",
                            item_id=item.item_id,
                            source_id=item.source_id,
                        )
                    except (FeishuError, WorkspaceError) as exc:
                        error = (
                            exc
                            if isinstance(exc, FeishuError)
                            else FeishuError("malformed_response")
                        )
                        outcome = ImportOutcome(
                            material_id=material_id,
                            state="failed",
                            error_code=error.code,
                            message=error.message,
                        )
                    intent["outcomes"][material_id] = outcome.model_dump(mode="json")
                    atomic_write(journal, json.dumps(intent).encode())
                outcomes = [ImportOutcome.model_validate(intent["outcomes"][i]) for i in ids]
                successes = sum(row.state == "succeeded" for row in outcomes)
                result = ImportResult(
                    operation_id=payload.operation_id,
                    outcomes=outcomes,
                    state="succeeded"
                    if successes == len(ids)
                    else "partial"
                    if successes
                    else "failed",
                )
                intent.update(state="completed", result=result.model_dump(mode="json"))
                atomic_write(journal, json.dumps(intent).encode())
                return result
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _validate_body(self, body: MaterialBody) -> None:
        if not isinstance(body, MaterialBody):
            raise FeishuError("malformed_response")
        content_type = body.content_type.lower().replace(" ", "")
        media, _, params = content_type.partition(";")
        if (
            media not in {"text/plain", "text/markdown", "application/octet-stream"}
            or (params and params != "charset=utf-8")
            or not body.raw
            or len(body.raw) > 20 * 1024 * 1024
            or "/" in body.filename
            or "\\" in body.filename
            or Path(body.filename).suffix.lower() not in {".txt", ".md"}
            or body.filename in {".", ".."}
            or len(body.filename) > 150
        ):
            raise FeishuError("malformed_response")
        try:
            safe_source_filename(body.filename)
            text = body.raw.decode("utf-8")
            if "\x00" in text:
                raise ValueError()
        except (UnicodeDecodeError, ValueError, WorkspaceError):
            raise FeishuError("malformed_response") from None


def callback_boundary(uri: str) -> str:
    parts = urlsplit(uri)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"
