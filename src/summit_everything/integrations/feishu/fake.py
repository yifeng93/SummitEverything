"""Deterministic synthetic fixtures with no network client or external endpoint."""

from datetime import datetime
from time import time
from urllib.parse import urlencode

from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    CalendarEvent,
    CalendarPage,
    FeishuError,
    Material,
    MaterialBody,
    MaterialPage,
    UserCredentials,
)


def _offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if not cursor.startswith("fake-page-") or not cursor[10:].isdigit():
        raise FeishuError("invalid_cursor")
    return int(cursor[10:])


class FakeFeishu:
    def authorization_url(self, redirect_uri: str, state: str) -> str:
        return redirect_uri + "?" + urlencode({"code": "fake-ok", "state": state})

    def exchange(
        self, code: str, redirect_uri: str, app_credentials: AppCredentials | None = None
    ) -> UserCredentials:
        if code == "denied":
            raise FeishuError("authorization_denied")
        if code != "fake-ok":
            raise FeishuError("malformed_response")
        return UserCredentials(
            access_token="synthetic-user-token",
            refresh_token="synthetic-refresh-token",
            expires_at=time() + 3600,
            scopes=["minutes:read", "calendar:read"],
        )

    def materials(
        self,
        credentials: UserCredentials,
        query: str,
        visibility: str | None,
        cursor: str | None,
        limit: int,
    ) -> MaterialPage:
        rows = [
            Material(
                material_id=f"minute-{i}",
                title=title,
                visibility="owner" if visible == "owner" else "shared",
                updated_at=datetime.fromisoformat("2026-10-09T08:00:00+08:00"),
            )
            for i, title, visible in [
                (1, "模拟会议", "owner"),
                (2, "模拟共享材料", "shared"),
                (3, "模拟项目讨论", "owner"),
            ]
        ]
        selected = [
            row
            for row in rows
            if query.casefold() in row.title.casefold()
            and (visibility is None or visibility == row.visibility)
        ]
        offset = _offset(cursor)
        next_cursor = f"fake-page-{offset + limit}" if offset + limit < len(selected) else None
        return MaterialPage(items=selected[offset : offset + limit], next_cursor=next_cursor)

    def body(self, credentials: UserCredentials, material_id: str) -> MaterialBody:
        errors = {
            "missing": "not_found",
            "scope": "missing_scope",
            "timeout": "provider_timeout",
            "unavailable": "provider_unavailable",
        }
        if material_id in errors:
            raise FeishuError(errors[material_id])
        if material_id == "malformed":
            return MaterialBody(
                raw=b'{"text":"not a transcript file"}',
                filename="bad.txt",
                content_type="application/json",
            )
        if material_id not in {"minute-1", "minute-2", "minute-3"}:
            raise FeishuError("not_found")
        return MaterialBody(
            raw="模拟会议：等待用户确认。\r\n".encode(),
            filename={
                "minute-1": "模拟会议.txt",
                "minute-2": "模拟共享材料.txt",
                "minute-3": "模拟项目讨论.txt",
            }[material_id],
            content_type="text/plain; charset=utf-8",
        )

    def calendar(
        self,
        credentials: UserCredentials,
        start: datetime,
        end: datetime,
        timezone: str,
        cursor: str | None,
        limit: int,
    ) -> CalendarPage:
        rows = [
            CalendarEvent(
                event_id=f"event-{i}",
                title=f"模拟日程 {i}",
                start=datetime.fromisoformat(f"2026-10-09T{hour}:00:00+08:00"),
                end=datetime.fromisoformat(f"2026-10-09T{hour}:30:00+08:00"),
            )
            for i, hour in [(1, "09"), (2, "14")]
        ]
        selected = [row for row in rows if row.start < end and row.end > start]
        offset = _offset(cursor)
        return CalendarPage(
            items=selected[offset : offset + limit],
            timezone=timezone,
            next_cursor=f"fake-page-{offset + limit}" if offset + limit < len(selected) else None,
        )
