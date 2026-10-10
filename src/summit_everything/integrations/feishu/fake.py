"""Deterministic synthetic fixtures with no network client or external endpoint."""

import fcntl
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

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
from summit_everything.integrations.feishu.tasks import (
    FeishuTask,
    TaskExecutionEvidence,
    TaskPage,
)
from summit_everything.workspace.transactions import atomic_write


def _offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if not cursor.startswith("fake-page-") or not cursor[10:].isdigit():
        raise FeishuError("invalid_cursor")
    return int(cursor[10:])


class FakeFeishu:
    def __init__(self, simulated_remote_root: Path | None = None) -> None:
        self.simulated_remote_root = simulated_remote_root or Path(
            tempfile.mkdtemp(prefix="summit-simulated-feishu-remote-")
        )
        self.simulated_remote_root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _remote(self) -> Iterator[dict[str, Any]]:
        with (self.simulated_remote_root / "remote.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            path = self.simulated_remote_root / "simulated_remote_tasks.json"
            try:
                data = (
                    json.loads(path.read_bytes()) if path.exists() else {"tasks": {}, "results": {}}
                )
                yield data
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _save_remote(self, data: dict[str, Any]) -> None:
        atomic_write(
            self.simulated_remote_root / "simulated_remote_tasks.json", json.dumps(data).encode()
        )

    def tasks(self, credentials: UserCredentials, cursor: str | None, limit: int) -> TaskPage:
        with self._remote() as data:
            rows = [FeishuTask.model_validate(value) for _, value in sorted(data["tasks"].items())]
        offset = _offset(cursor)
        return TaskPage(
            items=rows[offset : offset + limit],
            next_cursor=f"fake-page-{offset + limit}" if offset + limit < len(rows) else None,
        )

    def task_get(self, credentials: UserCredentials, guid: str) -> FeishuTask:
        with self._remote() as data:
            if guid not in data["tasks"]:
                raise FeishuError("not_found")
            return FeishuTask.model_validate(data["tasks"][guid])

    def task_create(self, credentials: UserCredentials, body: dict[str, Any]) -> FeishuTask:
        with self._remote() as data:
            token = body["client_token"]
            if token in data["results"]:
                return FeishuTask.model_validate(data["results"][token]["task"])
            task = FeishuTask(
                guid=str(uuid4()),
                **{key: value for key, value in body.items() if key != "client_token"},
            )
            row = task.model_dump(mode="json")
            data["tasks"][task.guid] = row
            data["results"][token] = {
                "client_token": token,
                "kind": "feishu_task_create",
                "target_guid": None,
                "task": row,
            }
            self._save_remote(data)
            return task

    def task_patch(
        self, credentials: UserCredentials, guid: str, body: dict[str, Any], token: str
    ) -> FeishuTask:
        with self._remote() as data:
            if guid not in data["tasks"]:
                raise FeishuError("not_found")
            row = dict(data["tasks"][guid])
            for field in body["update_fields"]:
                row[field] = body["task"].get(field)
            task = FeishuTask.model_validate(row)
            data["tasks"][guid] = task.model_dump(mode="json")
            data["results"][token] = {
                "client_token": token,
                "kind": "feishu_task_complete"
                if body.get("update_fields") == ["completed_at"]
                else "feishu_task_update",
                "target_guid": guid,
                "task": task.model_dump(mode="json"),
            }
            self._save_remote(data)
            return task

    def task_result(
        self, credentials: UserCredentials, token: str
    ) -> TaskExecutionEvidence | None:
        with self._remote() as data:
            result = data["results"].get(token)
            return TaskExecutionEvidence.model_validate(result) if result else None

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
            scopes=["minutes:read", "calendar:read", "task:task:read", "task:task:write"],
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
