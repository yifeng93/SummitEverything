"""Real Feishu / Lark OpenAPI HTTP adapter.

Wire shapes are taken only from first-party documentation reviewed on
2026-10-10 (see ``docs/architecture/PROVIDER-PROTOCOL-MATRIX.md``). Every call
is single-attempt, bounded, non-redirecting and mapped to a sanitized
``FeishuError``. No request body, header or provider payload is logged.

Identity policy: application (tenant) identity is preferred wherever the
documented endpoint accepts it. The two endpoints that document
``user_access_token`` only -- minutes search and task list -- require the
one-time user authorization and fail closed with a readable reason otherwise.
"""

from __future__ import annotations

import json
import math
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import Lock
from time import time
from typing import Any
from urllib.parse import urlencode

import httpx

from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    CalendarEvent,
    CalendarPage,
    FeishuConfig,
    FeishuError,
    Material,
    MaterialBody,
    MaterialPage,
    UserCredentials,
)
from summit_everything.integrations.feishu.tasks import (
    FeishuTask,
    ProviderDue,
    TaskExecutionEvidence,
    TaskPage,
)
from summit_everything.integrations.http_boundary import bounded_call, bounded_json_call
from summit_everything.integrations.transport import create_http_client

OPEN_API_BASE = "https://open.feishu.cn"
ACCOUNTS_BASE = "https://accounts.feishu.cn"

AUTHORIZE_PATH = "/open-apis/authen/v1/authorize"
TOKEN_PATH = "/open-apis/authen/v2/oauth/token"
TENANT_TOKEN_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
USER_INFO_PATH = "/open-apis/authen/v1/user_info"
MINUTES_SEARCH_PATH = "/open-apis/minutes/v1/minutes/search"
MINUTES_ARTIFACTS_PATH = "/open-apis/minutes/v1/minutes/{token}/artifacts"
MINUTES_TRANSCRIPT_PATH = "/open-apis/minutes/v1/minutes/{token}/transcript"
CALENDAR_EVENTS_PATH = "/open-apis/calendar/v4/calendars/{calendar_id}/events"
CALENDAR_PRIMARY_PATH = "/open-apis/calendar/v4/calendars/primary"
TASKS_PATH = "/open-apis/task/v2/tasks"
TASK_PATH = "/open-apis/task/v2/tasks/{guid}"

# Documented Feishu business codes mapped to product-readable failures.
_TOKEN_CODES = {99991661, 99991663, 99991664, 99991668, 99991677, 20005, 20037}
_PERMISSION_CODES = {99991672, 99991679, 20027, 1061045}
_MINUTES_TOKEN_CODES = {2094011, 2094012}
_MINUTES_SCOPE_CODES = {2091005}

_app_secret_source = Callable[[], AppCredentials | None]


class _LeaseContext:
    """Identity of one business operation currently holding a provider lease."""

    __slots__ = ()


class FeishuHttpProvider:
    """HTTP implementation of the Feishu provider protocol."""

    def __init__(
        self,
        config: FeishuConfig,
        app_credentials: _app_secret_source,
        *,
        client: httpx.Client | None = None,
        client_factory: Callable[[], httpx.Client] | None = None,
        clock: Callable[[], float] = time,
        open_api_base: str = OPEN_API_BASE,
        accounts_base: str = ACCOUNTS_BASE,
        max_response_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        if client is not None and client_factory is not None:
            raise ValueError("provide either client or client_factory, not both")
        self.config = config
        self._app_credentials = app_credentials
        self._clock = clock
        self.open_api_base = open_api_base.rstrip("/")
        self.accounts_base = accounts_base.rstrip("/")
        self.max_response_bytes = max_response_bytes
        self._owned_client = client is None
        if client is not None:
            self.client = client
        elif client_factory is not None:
            self.client = client_factory()
        else:
            self.client = create_http_client()
        self._tenant_token: tuple[str, float] | None = None
        # A superseded provider must finish every *complete business operation*
        # before its client is closed: ``_active_ops`` counts operation leases
        # (a calendar read spans primary + events, an import spans many body
        # downloads), while ``_inflight`` counts individual HTTP calls.
        self._lifecycle_lock = Lock()
        self._lease_local = threading.local()
        self._inflight = 0
        self._active_ops = 0
        self._retired = False
        self._closed = False

    @contextmanager
    def operation(self) -> Iterator[FeishuHttpProvider]:
        """Hold a lease for one complete business operation.

        Ownership is per calling thread: a lease established before retirement
        keeps working (including nested steps), while a brand-new operation from
        any thread is refused. The global counter is only used to decide when the
        client may be closed; it never authorises an unrelated caller.
        """
        context = getattr(self._lease_local, "context", None)
        depth = getattr(self._lease_local, "depth", 0)
        with self._lifecycle_lock:
            if context is None:
                if self._retired:
                    raise FeishuError("provider_unavailable")
                context = _LeaseContext()
            self._lease_local.context = context
            self._lease_local.depth = depth + 1
            self._active_ops += 1
        try:
            yield self
        finally:
            with self._lifecycle_lock:
                self._active_ops = max(0, self._active_ops - 1)
                self._maybe_close_locked()
            if depth == 0:
                self._lease_local.__dict__.pop("context", None)
            self._lease_local.depth = depth

    def _enter(self) -> None:
        with self._lifecycle_lock:
            # Only a thread that owns a lease (the operation itself, or a nested
            # step it performed) may keep using a retired provider. A direct call
            # from an unrelated thread is refused even while another operation is
            # still running.
            if self._retired and getattr(self._lease_local, "context", None) is None:
                raise FeishuError("provider_unavailable")
            self._inflight += 1

    def _leave(self) -> None:
        with self._lifecycle_lock:
            self._inflight = max(0, self._inflight - 1)
            self._maybe_close_locked()

    def _maybe_close_locked(self) -> None:
        if self._retired and self._active_ops == 0 and self._inflight == 0:
            self._close_locked()

    def retire(self) -> None:
        """Stop accepting new operations; close once the last lease ends."""
        with self._lifecycle_lock:
            self._retired = True
            self._maybe_close_locked()

    def _close_locked(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owned_client:
            self.client.close()

    @property
    def closed(self) -> bool:
        with self._lifecycle_lock:
            return self._closed

    def close(self) -> None:
        with self._lifecycle_lock:
            self._retired = True
            self._maybe_close_locked()

    def __enter__(self) -> FeishuHttpProvider:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- identity ---------------------------------------------------------

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.config.app_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(self.config.user_scopes),
                "state": state,
            }
        )
        return f"{self.accounts_base}{AUTHORIZE_PATH}?{query}"

    def _require_app(self) -> AppCredentials:
        credentials = self._app_credentials()
        if credentials is None:
            raise FeishuError("credential_missing")
        if credentials.app_id != self.config.app_id:
            raise FeishuError("malformed_response")
        return credentials

    def _application_token(self) -> str:
        cached = self._tenant_token
        if cached is not None and cached[1] > self._clock() + 60:
            return cached[0]
        app = self._require_app()
        # Wrapped like every other call so a timeout or transport failure is
        # sanitized into a FeishuError instead of escaping as a raw exception.
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{TENANT_TOKEN_PATH}",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json_body={
                    "app_id": app.app_id,
                    "app_secret": app.app_secret.get_secret_value(),
                },
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("malformed_response")
        expire = data.get("expire")
        lifetime = float(expire) if isinstance(expire, (int, float)) else 6900.0
        self._tenant_token = (token, self._clock() + lifetime)
        return token

    def _auth_header(self, credentials: UserCredentials | None) -> dict[str, str]:
        if credentials is not None:
            return {"Authorization": f"Bearer {credentials.access_token}"}
        return {"Authorization": f"Bearer {self._application_token()}"}

    def _user_header(self, credentials: UserCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {credentials.access_token}"}

    def _app_or_user(self, credentials: UserCredentials | None) -> dict[str, str]:
        """Application identity first; user token only when required.

        Endpoints that document ``tenant_access_token`` or ``user_access_token``
        use the application token. Only the two user-only endpoints call
        :meth:`_user_header` directly.
        """
        if self.config.identity == "app":
            return {"Authorization": f"Bearer {self._application_token()}"}
        return self._auth_header(credentials)

    # -- errors -----------------------------------------------------------

    def _envelope(self, status: int, payload: Any) -> dict[str, Any]:
        if status in {401, 403} or status == 404:
            raise FeishuError(
                {401: "token_expired", 403: "missing_scope", 404: "not_found"}[status]
            )
        if status == 429 or status >= 500:
            raise FeishuError("provider_unavailable")
        if not isinstance(payload, dict):
            raise FeishuError("malformed_response")
        code = payload.get("code")
        if code in (None, 0):
            data = payload.get("data")
            return data if isinstance(data, dict) else payload
        if not isinstance(code, int):
            raise FeishuError("malformed_response")
        if code in _TOKEN_CODES or code in _MINUTES_TOKEN_CODES:
            raise FeishuError("token_expired")
        if code in _PERMISSION_CODES or code in _MINUTES_SCOPE_CODES:
            raise FeishuError("missing_scope")
        raise FeishuError("provider_unavailable")

    def _call(self, call: Callable[[], Any]) -> Any:
        """Translate transport failures without leaking provider payloads."""
        self._enter()
        try:
            return call()
        except FeishuError:
            raise
        except TimeoutError:
            raise FeishuError("provider_timeout") from None
        except (httpx.HTTPError, OSError):
            raise FeishuError("provider_unavailable") from None
        except (ValueError, TypeError, KeyError):
            raise FeishuError("malformed_response") from None
        finally:
            self._leave()

    # -- OAuth ------------------------------------------------------------

    def exchange(
        self, code: str, redirect_uri: str, app_credentials: AppCredentials | None = None
    ) -> UserCredentials:
        app = app_credentials or self._require_app()
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{TOKEN_PATH}",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json_body={
                    "grant_type": "authorization_code",
                    "client_id": app.app_id,
                    "client_secret": app.app_secret.get_secret_value(),
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                max_response_bytes=self.max_response_bytes,
            )
        )
        return self._tokens(
            status,
            payload,
            require_refresh="offline_access" in self.config.user_scopes,
        )

    def refresh(self, credentials: UserCredentials) -> UserCredentials:
        app = self._require_app()
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{TOKEN_PATH}",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json_body={
                    "grant_type": "refresh_token",
                    "client_id": app.app_id,
                    "client_secret": app.app_secret.get_secret_value(),
                    "refresh_token": credentials.refresh_token,
                },
                max_response_bytes=self.max_response_bytes,
            )
        )
        return self._tokens(
            status,
            payload,
            require_refresh=True,
            consumed_refresh=credentials.refresh_token,
        )

    def _tokens(
        self,
        status: int,
        payload: Any,
        *,
        require_refresh: bool,
        consumed_refresh: str | None = None,
    ) -> UserCredentials:
        """Parse the documented token response strictly.

        The documented ``access_token``, ``token_type=Bearer``, integer positive
        ``expires_in`` and effective ``scope`` are required; a missing or
        malformed field is an error rather than an invented default or a reuse of
        the previous scope. A refresh grant always requires a *new*
        ``refresh_token``: the documented refresh token is single-use and the
        previous value is immediately invalid, so a response that omits it or
        returns the consumed value is rejected instead of being written back.
        """
        if status >= 400:
            # OAuth failures return RFC 6749 fields rather than an envelope.
            error = payload.get("error") if isinstance(payload, dict) else None
            if error in {"invalid_grant", "invalid_request"}:
                raise FeishuError("token_expired")
            self._envelope(status, payload)
        if not isinstance(payload, dict):
            raise FeishuError("malformed_response")
        code = payload.get("code")
        if isinstance(code, int) and code != 0:
            self._envelope(200, payload)
        access = payload.get("access_token")
        if not isinstance(access, str) or not access:
            raise FeishuError("malformed_response")
        if payload.get("token_type") != "Bearer":
            # Documented fixed value; a missing value is not accepted.
            raise FeishuError("malformed_response")
        expires_in = payload.get("expires_in")
        if isinstance(expires_in, bool):
            raise FeishuError("malformed_response")
        if isinstance(expires_in, int):
            lifetime = float(expires_in)
        elif (
            isinstance(expires_in, float) and math.isfinite(expires_in) and expires_in.is_integer()
        ):
            lifetime = expires_in
        else:
            raise FeishuError("malformed_response")
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise FeishuError("malformed_response")
        scopes_raw = payload.get("scope")
        if not isinstance(scopes_raw, str) or not scopes_raw.strip():
            # The effective scope of *this* response governs; the previous
            # scope is never reused to hide a missing field.
            raise FeishuError("malformed_response")
        scopes = scopes_raw.split()
        refresh_token = payload.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            refresh_token = None
        if require_refresh:
            if refresh_token is None:
                if consumed_refresh is None:
                    # A first-time exchange without offline_access cannot refresh.
                    raise FeishuError("missing_scope")
                raise FeishuError("malformed_response")
            if consumed_refresh is not None and refresh_token == consumed_refresh:
                # The documented refresh token is single-use; returning the
                # consumed value means the credential was not rotated.
                raise FeishuError("malformed_response")
        return UserCredentials(
            access_token=access,
            refresh_token=refresh_token or "",
            expires_at=self._clock() + lifetime,
            scopes=scopes,
        )

    def identity(self, credentials: UserCredentials) -> dict[str, Any]:
        """Minimal identity read; only open_id/union_id/name are retained."""
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "GET",
                f"{self.open_api_base}{USER_INFO_PATH}",
                headers=self._user_header(credentials),
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        open_id = data.get("open_id")
        if not isinstance(open_id, str) or not open_id:
            raise FeishuError("malformed_response")
        return {
            "open_id": open_id,
            "union_id": data.get("union_id") if isinstance(data.get("union_id"), str) else None,
            "name": data.get("name") if isinstance(data.get("name"), str) else None,
        }

    # -- materials --------------------------------------------------------

    def materials(
        self,
        credentials: UserCredentials,
        query: str,
        visibility: str | None,
        cursor: str | None,
        limit: int,
    ) -> MaterialPage:
        # The documented minutes search endpoint has no visibility parameter.
        # Refuse an unsupported filter instead of silently returning everything.
        if visibility is not None:
            raise FeishuError("unsupported_capability")
        page_size = max(1, min(limit, 30))
        params: dict[str, Any] = {"page_size": page_size}
        if cursor:
            params["page_token"] = cursor
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{MINUTES_SEARCH_PATH}",
                headers={
                    **self._user_header(credentials),
                    "Content-Type": "application/json; charset=utf-8",
                },
                params=params,
                json_body={"query": query} if query else {},
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise FeishuError("malformed_response")
        items: list[Material] = []
        for raw in raw_items[:page_size]:
            if not isinstance(raw, dict):
                raise FeishuError("malformed_response")
            token = raw.get("token")
            if not isinstance(token, str) or not token:
                raise FeishuError("malformed_response")
            display = raw.get("display_info")
            title = _plain_title(display) or token
            items.append(Material(material_id=token, title=title[:500], visibility="shared"))
        next_cursor = data.get("page_token") if data.get("has_more") is True else None
        return MaterialPage(items=items, next_cursor=next_cursor or None)

    def body(self, credentials: UserCredentials | None, material_id: str) -> MaterialBody:
        mode = self.config.material_content
        if mode == "artifacts":
            return self._artifacts_body(credentials, material_id)
        try:
            return self._transcript_body(credentials, material_id)
        except FeishuError as exc:
            if exc.code != "missing_scope":
                raise
            return self._artifacts_body(credentials, material_id)

    def _transcript_body(
        self, credentials: UserCredentials | None, material_id: str
    ) -> MaterialBody:
        path = MINUTES_TRANSCRIPT_PATH.format(token=material_id)
        status, raw = self._call(
            lambda: bounded_call(
                self.client,
                "GET",
                f"{self.open_api_base}{path}",
                headers=self._app_or_user(credentials),
                params={"file_format": "txt", "need_timestamp": "true"},
                max_response_bytes=self.max_response_bytes,
            )
        )
        if status >= 400:
            self._envelope(status, None)
        if not raw:
            raise FeishuError("malformed_response")
        # A denied or malformed transcript can arrive as a JSON body with 200.
        if raw.lstrip()[:1] == b"{":
            try:
                envelope = json.loads(raw)
            except (ValueError, TypeError):
                envelope = None
            if isinstance(envelope, dict) and envelope.get("code"):
                self._envelope(200, envelope)
            raise FeishuError("malformed_response")
        return MaterialBody(
            raw=raw, filename=f"{material_id}.txt", content_type="text/plain; charset=utf-8"
        )

    def _artifacts_body(
        self, credentials: UserCredentials | None, material_id: str
    ) -> MaterialBody:
        path = MINUTES_ARTIFACTS_PATH.format(token=material_id)
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "GET",
                f"{self.open_api_base}{path}",
                headers=self._app_or_user(credentials),
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        transcript = data.get("transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            raise FeishuError("malformed_response")
        return MaterialBody(
            raw=transcript.encode("utf-8"),
            filename=f"{material_id}.txt",
            content_type="text/plain; charset=utf-8",
        )

    # -- calendar ---------------------------------------------------------

    def calendar_id(self, credentials: UserCredentials | None) -> str:
        if self.config.calendar_id:
            return self.config.calendar_id
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{CALENDAR_PRIMARY_PATH}",
                headers={**self._app_or_user(credentials), "Content-Type": "application/json"},
                json_body={},
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        calendars = data.get("calendars")
        if not isinstance(calendars, list):
            raise FeishuError("malformed_response")
        candidates: list[tuple[str, Any]] = []
        for entry in calendars:
            if not isinstance(entry, dict):
                raise FeishuError("malformed_response")
            calendar = entry.get("calendar")
            if not isinstance(calendar, dict):
                raise FeishuError("malformed_response")
            if calendar.get("is_deleted") is True:
                continue
            calendar_id = calendar.get("calendar_id")
            if not isinstance(calendar_id, str) or not calendar_id:
                raise FeishuError("malformed_response")
            candidates.append((calendar_id, entry.get("user_id")))
        if not candidates:
            raise FeishuError("no_primary_calendar")
        if len(candidates) > 1:
            # The official response lists one calendar per identity. We do not
            # hold a verified identity (no user-info call is made), so an
            # ambiguous list is refused instead of picking the first entry.
            raise FeishuError("ambiguous_calendar")
        return candidates[0][0]

    def calendar(
        self,
        credentials: UserCredentials | None,
        start: datetime,
        end: datetime,
        timezone: str,
        cursor: str | None,
        limit: int,
    ) -> CalendarPage:
        # start_time/end_time cannot be combined with page_token per the official
        # documented constraint, so an explicit range is a single bounded page.
        if cursor:
            raise FeishuError("invalid_cursor")
        calendar_id = self.calendar_id(credentials)
        # The documented explicit range is a single bounded page with no usable
        # page_token, so the upstream size is the only lever and the range is
        # never widened or retried.
        page_size = max(50, min(limit, 1000))
        params = {
            "start_time": str(int(start.timestamp())),
            "end_time": str(int(end.timestamp())),
            "page_size": page_size,
        }
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "GET",
                f"{self.open_api_base}{CALENDAR_EVENTS_PATH.format(calendar_id=calendar_id)}",
                headers=self._app_or_user(credentials),
                params=params,
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise FeishuError("malformed_response")
        events: list[CalendarEvent] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise FeishuError("malformed_response")
            event_id = raw.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                raise FeishuError("malformed_response")
            events.append(
                CalendarEvent(
                    event_id=event_id,
                    title=str(raw.get("summary") or ""),
                    start=_time_info(raw.get("start_time")),
                    end=_time_info(raw.get("end_time")),
                )
            )
        # Validate every upstream item before deciding what to return; a
        # malformed entry is an error, never something slicing can hide.
        truncated = len(events) > limit or len(events) >= page_size or data.get("has_more") is True
        return CalendarPage(
            items=events[:limit],
            next_cursor=None,
            timezone=timezone,
            truncated=truncated,
        )

    # -- tasks ------------------------------------------------------------

    def tasks(self, credentials: UserCredentials, cursor: str | None, limit: int) -> TaskPage:
        params: dict[str, Any] = {"page_size": max(1, min(limit, 100)), "type": "my_tasks"}
        if cursor:
            params["page_token"] = cursor
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "GET",
                f"{self.open_api_base}{TASKS_PATH}",
                headers=self._user_header(credentials),
                params=params,
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            raise FeishuError("malformed_response")
        items = [_task(raw) for raw in raw_items]
        next_cursor = data.get("page_token") if data.get("has_more") is True else None
        return TaskPage(items=items, next_cursor=next_cursor or None)

    def task_get(self, credentials: UserCredentials | None, guid: str) -> FeishuTask:
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "GET",
                f"{self.open_api_base}{TASK_PATH.format(guid=guid)}",
                headers=self._app_or_user(credentials),
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        task = data.get("task")
        if not isinstance(task, dict):
            raise FeishuError("malformed_response")
        return _task(task, expected_guid=guid)

    def task_create(self, credentials: UserCredentials | None, body: dict[str, Any]) -> FeishuTask:
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "POST",
                f"{self.open_api_base}{TASKS_PATH}",
                headers={**self._app_or_user(credentials), "Content-Type": "application/json"},
                json_body=body,
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        task = data.get("task")
        if not isinstance(task, dict):
            raise FeishuError("malformed_response")
        return _task(task)

    def task_patch(
        self, credentials: UserCredentials | None, guid: str, body: dict[str, Any], token: str
    ) -> FeishuTask:
        status, payload = self._call(
            lambda: bounded_json_call(
                self.client,
                "PATCH",
                f"{self.open_api_base}{TASK_PATH.format(guid=guid)}",
                headers={**self._app_or_user(credentials), "Content-Type": "application/json"},
                json_body=body,
                max_response_bytes=self.max_response_bytes,
            )
        )
        data = self._envelope(status, payload)
        task = data.get("task")
        if not isinstance(task, dict):
            raise FeishuError("malformed_response")
        return _task(task, expected_guid=guid)

    def task_result(self, credentials: UserCredentials, token: str) -> TaskExecutionEvidence | None:
        """No documented endpoint proves a write by client token.

        Official search/list endpoints cannot bind a result to an idempotency
        token, so the adapter reports "no evidence" instead of guessing.
        """
        return None


def _plain_title(display: Any) -> str:
    if not isinstance(display, str):
        return ""
    return display.replace("<h>", "").replace("</h>", "").strip()


def _time_info(value: Any) -> datetime:
    if not isinstance(value, dict):
        raise FeishuError("malformed_response")
    if isinstance(value.get("timestamp"), str) and value["timestamp"].isdigit():
        return datetime.fromtimestamp(int(value["timestamp"]), tz=UTC)
    if isinstance(value.get("date"), str):
        return datetime.fromisoformat(value["date"]).replace(tzinfo=UTC)
    raise FeishuError("malformed_response")


def _due(value: Any) -> ProviderDue | None:
    if not isinstance(value, dict):
        return None
    timestamp = value.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp.isdigit():
        return None
    return ProviderDue(timestamp=int(timestamp), is_all_day=bool(value.get("is_all_day")))


def _task(raw: Any, expected_guid: str | None = None) -> FeishuTask:
    if not isinstance(raw, dict):
        raise FeishuError("malformed_response")
    guid = raw.get("guid")
    if not isinstance(guid, str) or not guid:
        raise FeishuError("malformed_response")
    if expected_guid is not None and guid != expected_guid:
        raise FeishuError("malformed_response")
    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise FeishuError("malformed_response")
    completed = raw.get("completed_at")
    completed_at = 0
    if isinstance(completed, str) and completed.isdigit():
        completed_at = int(completed)
    elif isinstance(completed, int) and completed > 0:
        completed_at = completed
    description = raw.get("description")
    if not isinstance(description, str):
        description = ""
    return FeishuTask(
        guid=guid,
        summary=summary,
        description=description,
        due=_due(raw.get("due")),
        completed_at=completed_at,
    )
