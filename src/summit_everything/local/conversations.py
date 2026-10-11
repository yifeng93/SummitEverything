"""Durable, profile-local conversation history and query event journal."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from summit_everything.domain.models import Citation

QueryState = Literal["running", "completed", "error", "cancelled", "interrupted"]
EventType = Literal["status", "citation", "delta", "completed", "error"]
ACTIVE_QUERIES: set[tuple[str, str, str]] = set()


class QueryEvent(BaseModel):
    request_id: UUID
    seq: int = Field(ge=1)
    type: EventType
    data: dict[str, Any]


class ConversationMessage(BaseModel):
    request_id: UUID
    question: str
    answer: str
    state: QueryState
    purpose: Literal["current", "history"]
    citations: list[Citation] = Field(default_factory=list)
    events: list[QueryEvent] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ConversationSummary(BaseModel):
    conversation_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    state: QueryState


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None = None


class QueryStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    conversation_id: UUID | None = None
    question: str = Field(min_length=1)
    fingerprint: str = Field(min_length=1)
    purpose: Literal["current", "history"] = "current"


class QueryConflict(ValueError):
    """A stable request id was reused for different input or is still running."""


class ConversationNotFound(LookupError):
    """A query attempted to append to a conversation that is not in this workspace."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class ConversationStore:
    """SQLite state scoped by one app profile and keyed again by workspace identity."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS conversations (
                    workspace_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, conversation_id)
                );
                CREATE TABLE IF NOT EXISTS queries (
                    workspace_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    question TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    state TEXT NOT NULL,
                    answer TEXT NOT NULL DEFAULT '',
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    owner_pid INTEGER NOT NULL,
                    PRIMARY KEY (workspace_id, request_id),
                    FOREIGN KEY (workspace_id, conversation_id)
                        REFERENCES conversations(workspace_id, conversation_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS queries_conversation
                    ON queries (workspace_id, conversation_id, created_at, request_id);
                CREATE TABLE IF NOT EXISTS query_events (
                    workspace_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, request_id, seq),
                    FOREIGN KEY (workspace_id, request_id)
                        REFERENCES queries(workspace_id, request_id)
                        ON DELETE CASCADE
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
        finally:
            connection.close()

    def recover_interrupted(self, workspace_id: UUID) -> None:
        """Mark dead-process work interrupted; never rewrite a live process attempt."""
        with self._connect() as connection, connection:
            rows = connection.execute(
                "SELECT request_id, owner_pid FROM queries "
                "WHERE workspace_id=? AND state='running'",
                (str(workspace_id),),
            ).fetchall()
            for row in rows:
                pid = int(row["owner_pid"])
                active_key = (str(self.path.resolve()), str(workspace_id), str(row["request_id"]))
                if active_key in ACTIVE_QUERIES:
                    continue
                if pid == os.getpid():
                    connection.execute(
                        "UPDATE queries SET state='interrupted', completed_at=? "
                        "WHERE workspace_id=? AND request_id=? AND state='running'",
                        (_now(), str(workspace_id), str(row["request_id"])),
                    )
                    continue
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    connection.execute(
                        "UPDATE queries SET state='interrupted', completed_at=? "
                        "WHERE workspace_id=? AND request_id=? AND state='running'",
                        (_now(), str(workspace_id), str(row["request_id"])),
                    )
                except PermissionError:
                    continue

    def begin(self, workspace_id: UUID, payload: QueryStart) -> tuple[bool, UUID]:
        request_hash = _json(
            {
                "question": payload.question,
                "fingerprint": payload.fingerprint,
                "purpose": payload.purpose,
                "conversation_id": str(payload.conversation_id)
                if payload.conversation_id
                else None,
            }
        )
        with self._connect() as connection, connection:
            existing = connection.execute(
                "SELECT request_hash, conversation_id, state FROM queries "
                "WHERE workspace_id=? AND request_id=?",
                (str(workspace_id), str(payload.request_id)),
            ).fetchone()
            if existing is not None:
                if str(existing["request_hash"]) != request_hash:
                    raise QueryConflict("查询标识已用于其他问题，不能重复发送")
                if str(existing["state"]) == "running":
                    raise QueryConflict("该问题仍在处理中；请从历史查看状态，不会自动重发")
                return False, UUID(str(existing["conversation_id"]))

            conversation_id = payload.conversation_id or uuid4()
            now = _now()
            if payload.conversation_id is not None:
                existing_conversation = connection.execute(
                    "SELECT 1 FROM conversations WHERE workspace_id=? AND conversation_id=?",
                    (str(workspace_id), str(conversation_id)),
                ).fetchone()
                if existing_conversation is None:
                    raise ConversationNotFound("问答历史不属于当前工作库或本机 profile")
            connection.execute(
                "INSERT INTO conversations(workspace_id, conversation_id, title, created_at, "
                "updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(workspace_id, conversation_id) "
                "DO UPDATE SET updated_at=excluded.updated_at",
                (str(workspace_id), str(conversation_id), payload.question[:120], now, now),
            )
            connection.execute(
                "INSERT INTO queries(workspace_id, request_id, conversation_id, request_hash, "
                "question, fingerprint, purpose, state, created_at, owner_pid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)",
                (
                    str(workspace_id),
                    str(payload.request_id),
                    str(conversation_id),
                    request_hash,
                    payload.question,
                    payload.fingerprint,
                    payload.purpose,
                    now,
                    os.getpid(),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at=? WHERE workspace_id=? AND conversation_id=?",
                (now, str(workspace_id), str(conversation_id)),
            )
        return True, conversation_id

    def append_event(
        self,
        workspace_id: UUID,
        request_id: UUID,
        event_type: EventType,
        data: dict[str, Any],
    ) -> QueryEvent:
        with self._connect() as connection, connection:
            query = connection.execute(
                "SELECT state, conversation_id FROM queries WHERE workspace_id=? AND request_id=?",
                (str(workspace_id), str(request_id)),
            ).fetchone()
            if query is None or query["state"] != "running":
                raise QueryConflict("查询已进入终态，不能再追加事件")
            sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM query_events "
                    "WHERE workspace_id=? AND request_id=?",
                    (str(workspace_id), str(request_id)),
                ).fetchone()[0]
            )
            connection.execute(
                "INSERT INTO query_events(workspace_id, request_id, seq, type, data_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(workspace_id), str(request_id), sequence, event_type, _json(data)),
            )
            if event_type == "delta":
                connection.execute(
                    "UPDATE queries SET answer=answer || ? WHERE workspace_id=? AND request_id=?",
                    (str(data.get("text", "")), str(workspace_id), str(request_id)),
                )
            elif event_type == "citation":
                row = connection.execute(
                    "SELECT citations_json FROM queries WHERE workspace_id=? AND request_id=?",
                    (str(workspace_id), str(request_id)),
                ).fetchone()
                citations = json.loads(str(row["citations_json"]))
                citations.append(data)
                connection.execute(
                    "UPDATE queries SET citations_json=? WHERE workspace_id=? AND request_id=?",
                    (_json(citations), str(workspace_id), str(request_id)),
                )
            connection.execute(
                "UPDATE conversations SET updated_at=? WHERE workspace_id=? AND conversation_id=?",
                (_now(), str(workspace_id), str(query["conversation_id"])),
            )
        return QueryEvent(request_id=request_id, seq=sequence, type=event_type, data=data)

    def finish(
        self,
        workspace_id: UUID,
        request_id: UUID,
        state: Literal["completed", "error", "cancelled", "interrupted"],
        *,
        error: str | None = None,
    ) -> bool:
        with self._connect() as connection, connection:
            row = connection.execute(
                "SELECT state FROM queries WHERE workspace_id=? AND request_id=?",
                (str(workspace_id), str(request_id)),
            ).fetchone()
            if row is None or row["state"] != "running":
                return False
            connection.execute(
                "UPDATE queries SET state=?, error=?, completed_at=? "
                "WHERE workspace_id=? AND request_id=? AND state='running'",
                (state, error, _now(), str(workspace_id), str(request_id)),
            )
            return True

    def terminate(
        self,
        workspace_id: UUID,
        request_id: UUID,
        event_type: Literal["completed", "error"],
        data: dict[str, Any],
        state: Literal["completed", "error", "cancelled"],
        *,
        error: str | None = None,
    ) -> QueryEvent | None:
        """Atomically persist the sole terminal event and terminal state."""
        with self._connect() as connection, connection:
            query = connection.execute(
                "SELECT state, conversation_id FROM queries WHERE workspace_id=? AND request_id=?",
                (str(workspace_id), str(request_id)),
            ).fetchone()
            if query is None or query["state"] != "running":
                return None
            sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM query_events "
                    "WHERE workspace_id=? AND request_id=?",
                    (str(workspace_id), str(request_id)),
                ).fetchone()[0]
            )
            connection.execute(
                "INSERT INTO query_events(workspace_id, request_id, seq, type, data_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(workspace_id), str(request_id), sequence, event_type, _json(data)),
            )
            connection.execute(
                "UPDATE queries SET state=?, error=?, completed_at=? "
                "WHERE workspace_id=? AND request_id=? AND state='running'",
                (state, error, _now(), str(workspace_id), str(request_id)),
            )
            connection.execute(
                "UPDATE conversations SET updated_at=? WHERE workspace_id=? AND conversation_id=?",
                (_now(), str(workspace_id), str(query["conversation_id"])),
            )
        return QueryEvent(request_id=request_id, seq=sequence, type=event_type, data=data)

    def replay(self, workspace_id: UUID, request_id: UUID) -> tuple[str, list[QueryEvent]] | None:
        with self._connect() as connection:
            query = connection.execute(
                "SELECT state FROM queries WHERE workspace_id=? AND request_id=?",
                (str(workspace_id), str(request_id)),
            ).fetchone()
            if query is None:
                return None
            rows = connection.execute(
                "SELECT seq, type, data_json FROM query_events "
                "WHERE workspace_id=? AND request_id=? ORDER BY seq",
                (str(workspace_id), str(request_id)),
            ).fetchall()
        return str(query["state"]), [
            QueryEvent(
                request_id=request_id,
                seq=int(row["seq"]),
                type=row["type"],
                data=json.loads(row["data_json"]),
            )
            for row in rows
        ]

    def list(self, workspace_id: UUID, *, cursor: str | None, limit: int) -> ConversationPage:
        self.recover_interrupted(workspace_id)
        cursor_time = cursor_id = None
        if cursor:
            cursor_time, raw_cursor_id = cursor.split("|", 1)
            datetime.fromisoformat(cursor_time)
            cursor_id = str(UUID(raw_cursor_id))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT c.conversation_id, c.title, c.created_at, c.updated_at, "
                "COUNT(q.request_id) AS message_count, "
                "COALESCE((SELECT state FROM queries q2 WHERE q2.workspace_id=c.workspace_id "
                "AND q2.conversation_id=c.conversation_id "
                "ORDER BY q2.created_at DESC LIMIT 1), 'completed') AS state "
                "FROM conversations c LEFT JOIN queries q ON q.workspace_id=c.workspace_id "
                "AND q.conversation_id=c.conversation_id WHERE c.workspace_id=? AND "
                "(? IS NULL OR c.updated_at < ? OR (c.updated_at=? AND c.conversation_id < ?)) "
                "GROUP BY c.conversation_id ORDER BY c.updated_at DESC, "
                "c.conversation_id DESC LIMIT ?",
                (
                    str(workspace_id),
                    cursor_time,
                    cursor_time,
                    cursor_time,
                    cursor_id,
                    limit + 1,
                ),
            ).fetchall()
        has_more = len(rows) > limit
        page = [ConversationSummary.model_validate(dict(row)) for row in rows[:limit]]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = f"{last.updated_at.isoformat()}|{last.conversation_id}"
        return ConversationPage(items=page, next_cursor=next_cursor)

    def get(self, workspace_id: UUID, conversation_id: UUID) -> ConversationDetail | None:
        self.recover_interrupted(workspace_id)
        with self._connect() as connection:
            conversation = connection.execute(
                "SELECT c.conversation_id, c.title, c.created_at, c.updated_at, "
                "COUNT(q.request_id) AS message_count, "
                "COALESCE((SELECT state FROM queries q2 WHERE q2.workspace_id=c.workspace_id "
                "AND q2.conversation_id=c.conversation_id "
                "ORDER BY q2.created_at DESC LIMIT 1), 'completed') AS state "
                "FROM conversations c LEFT JOIN queries q ON q.workspace_id=c.workspace_id "
                "AND q.conversation_id=c.conversation_id "
                "WHERE c.workspace_id=? AND c.conversation_id=? "
                "GROUP BY c.conversation_id",
                (str(workspace_id), str(conversation_id)),
            ).fetchone()
            if conversation is None:
                return None
            queries = connection.execute(
                "SELECT request_id, question, answer, purpose, state, citations_json, error, "
                "created_at, completed_at "
                "FROM queries WHERE workspace_id=? AND conversation_id=? "
                "ORDER BY created_at, request_id",
                (str(workspace_id), str(conversation_id)),
            ).fetchall()
            messages = []
            for query in queries:
                events = connection.execute(
                    "SELECT seq, type, data_json FROM query_events "
                    "WHERE workspace_id=? AND request_id=? ORDER BY seq",
                    (str(workspace_id), str(query["request_id"])),
                ).fetchall()
                messages.append(
                    ConversationMessage(
                        request_id=UUID(str(query["request_id"])),
                        question=str(query["question"]),
                        answer=str(query["answer"]),
                        state=query["state"],
                        purpose=query["purpose"],
                        citations=[
                            Citation.model_validate(item)
                            for item in json.loads(query["citations_json"])
                        ],
                        events=[
                            QueryEvent(
                                request_id=UUID(str(query["request_id"])),
                                seq=int(event["seq"]),
                                type=event["type"],
                                data=json.loads(event["data_json"]),
                            )
                            for event in events
                        ],
                        error=query["error"],
                        created_at=datetime.fromisoformat(str(query["created_at"])),
                        completed_at=datetime.fromisoformat(str(query["completed_at"]))
                        if query["completed_at"]
                        else None,
                    )
                )
        return ConversationDetail(
            **dict(conversation),
            messages=messages,
        )

    def delete(self, workspace_id: UUID, conversation_id: UUID) -> bool:
        with self._connect() as connection, connection:
            result = connection.execute(
                "DELETE FROM conversations WHERE workspace_id=? AND conversation_id=?",
                (str(workspace_id), str(conversation_id)),
            )
            return result.rowcount > 0

    def running_requests(self, workspace_id: UUID, conversation_id: UUID) -> tuple[UUID, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT request_id FROM queries WHERE workspace_id=? AND conversation_id=? "
                "AND state='running'",
                (str(workspace_id), str(conversation_id)),
            ).fetchall()
        return tuple(UUID(str(row["request_id"])) for row in rows)
