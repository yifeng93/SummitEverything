"""Profile-local answer roles and user-confirmed memory."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    instructions: str = Field(default="", max_length=4000)
    context_budget: int = Field(default=2000, ge=0, le=6000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("角色名称不能为空")
        return value


class AnswerRole(RoleInput):
    role_id: UUID
    created_at: datetime
    updated_at: datetime


class MemoryCandidate(BaseModel):
    candidate_id: UUID
    message_id: UUID
    text: str
    state: str
    created_at: datetime


class UserMemory(BaseModel):
    memory_id: UUID
    source_message_id: UUID
    text: str
    created_at: datetime
    updated_at: datetime


class AnswerContext(BaseModel):
    """Only response-affecting, bounded local context; no historical answers."""

    model_config = ConfigDict(extra="forbid")
    answer_mode: str = Field(default="fact", pattern="^(fact|comparison|plan)$")
    role_name: str = ""
    role_instructions: str = ""
    user_memories: list[str] = Field(default_factory=list)
    previous_user_questions: list[str] = Field(default_factory=list)


class ContextConflict(ValueError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


class AnswerContextStore:
    """SQLite storage under a local profile, keyed by workspace identity too."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS answer_roles (
                    workspace_id TEXT NOT NULL, role_id TEXT NOT NULL,
                    name TEXT NOT NULL, instructions TEXT NOT NULL,
                    context_budget INTEGER NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, role_id)
                );
                CREATE TABLE IF NOT EXISTS memory_items (
                    workspace_id TEXT NOT NULL, memory_id TEXT NOT NULL,
                    source_message_id TEXT NOT NULL, text TEXT NOT NULL,
                    state TEXT NOT NULL, confirmation_id TEXT,
                    confirmation_hash TEXT, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, memory_id)
                );
                CREATE INDEX IF NOT EXISTS memory_state
                    ON memory_items(workspace_id, state, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def list_roles(self, workspace_id: UUID) -> list[AnswerRole]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT role_id, name, instructions, context_budget, created_at, updated_at "
                "FROM answer_roles WHERE workspace_id=? ORDER BY created_at, role_id",
                (str(workspace_id),),
            ).fetchall()
        return [AnswerRole.model_validate(dict(row)) for row in rows]

    def role(self, workspace_id: UUID, role_id: UUID) -> AnswerRole | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT role_id, name, instructions, context_budget, created_at, updated_at "
                "FROM answer_roles WHERE workspace_id=? AND role_id=?",
                (str(workspace_id), str(role_id)),
            ).fetchone()
        return AnswerRole.model_validate(dict(row)) if row else None

    def save_role(
        self, workspace_id: UUID, payload: RoleInput, role_id: UUID | None = None
    ) -> AnswerRole:
        now = _now()
        role_id = role_id or uuid4()
        with self._connect() as db, db:
            exists = db.execute(
                "SELECT created_at FROM answer_roles WHERE workspace_id=? AND role_id=?",
                (str(workspace_id), str(role_id)),
            ).fetchone()
            created = str(exists["created_at"]) if exists else now
            db.execute(
                "INSERT INTO answer_roles VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id, role_id) DO UPDATE SET name=excluded.name, "
                "instructions=excluded.instructions, context_budget=excluded.context_budget, "
                "updated_at=excluded.updated_at",
                (
                    str(workspace_id),
                    str(role_id),
                    payload.name,
                    payload.instructions,
                    payload.context_budget,
                    created,
                    now,
                ),
            )
        return AnswerRole(
            role_id=role_id,
            **payload.model_dump(),
            created_at=datetime.fromisoformat(created),
            updated_at=datetime.fromisoformat(now),
        )

    def delete_role(self, workspace_id: UUID, role_id: UUID) -> bool:
        with self._connect() as db, db:
            result = db.execute(
                "DELETE FROM answer_roles WHERE workspace_id=? AND role_id=?",
                (str(workspace_id), str(role_id)),
            )
        return result.rowcount > 0

    def create_candidate(self, workspace_id: UUID, message_id: UUID, text: str) -> MemoryCandidate:
        candidate_id = uuid4()
        with self._connect() as db, db:
            existing = db.execute(
                "SELECT memory_id, state, created_at FROM memory_items "
                "WHERE workspace_id=? AND source_message_id=? AND text=? "
                "AND state='pending' ORDER BY created_at LIMIT 1",
                (str(workspace_id), str(message_id), text),
            ).fetchone()
            if existing is not None:
                return MemoryCandidate(
                    candidate_id=UUID(existing["memory_id"]),
                    message_id=message_id,
                    text=text,
                    state=existing["state"],
                    created_at=datetime.fromisoformat(existing["created_at"]),
                )
            now = _now()
            db.execute(
                "INSERT INTO memory_items(workspace_id, memory_id, source_message_id, text, "
                "state, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (str(workspace_id), str(candidate_id), str(message_id), text, now, now),
            )
        return MemoryCandidate(
            candidate_id=candidate_id,
            message_id=message_id,
            text=text,
            state="pending",
            created_at=datetime.fromisoformat(now),
        )

    def candidates(self, workspace_id: UUID) -> list[MemoryCandidate]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT memory_id, source_message_id, text, state, created_at "
                "FROM memory_items WHERE workspace_id=? AND state='pending' ORDER BY created_at",
                (str(workspace_id),),
            ).fetchall()
        return [
            MemoryCandidate(
                candidate_id=UUID(row["memory_id"]),
                message_id=UUID(row["source_message_id"]),
                text=row["text"],
                state=row["state"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def confirm_candidate(
        self, workspace_id: UUID, candidate_id: UUID, *, confirmation_id: str, text: str
    ) -> UserMemory:
        intent_hash = json.dumps(
            {"confirmation_id": confirmation_id, "text": text},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connect() as db, db:
            row = db.execute(
                "SELECT * FROM memory_items WHERE workspace_id=? AND memory_id=?",
                (str(workspace_id), str(candidate_id)),
            ).fetchone()
            if row is None:
                raise KeyError("找不到待确认的记忆候选。")
            if row["state"] == "active":
                if row["confirmation_hash"] != intent_hash:
                    raise ContextConflict("该记忆已用其他确认内容生效。")
            else:
                now = _now()
                db.execute(
                    "UPDATE memory_items SET state='active', text=?, confirmation_id=?, "
                    "confirmation_hash=?, updated_at=? WHERE workspace_id=? AND memory_id=? "
                    "AND state='pending'",
                    (text, confirmation_id, intent_hash, now, str(workspace_id), str(candidate_id)),
                )
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM memory_items WHERE workspace_id=? AND memory_id=?",
                (str(workspace_id), str(candidate_id)),
            ).fetchone()
        assert row is not None
        return UserMemory(
            memory_id=UUID(row["memory_id"]),
            source_message_id=UUID(row["source_message_id"]),
            text=row["text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def memories(self, workspace_id: UUID) -> list[UserMemory]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM memory_items WHERE workspace_id=? AND state='active' "
                "ORDER BY created_at, memory_id",
                (str(workspace_id),),
            ).fetchall()
        return [
            UserMemory(
                memory_id=UUID(row["memory_id"]),
                source_message_id=UUID(row["source_message_id"]),
                text=row["text"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def update_memory(self, workspace_id: UUID, memory_id: UUID, text: str) -> UserMemory | None:
        now = _now()
        with self._connect() as db, db:
            result = db.execute(
                "UPDATE memory_items SET text=?, updated_at=? WHERE workspace_id=? "
                "AND memory_id=? AND state='active'",
                (text, now, str(workspace_id), str(memory_id)),
            )
            if not result.rowcount:
                return None
        return next(
            (item for item in self.memories(workspace_id) if item.memory_id == memory_id), None
        )

    def delete_memory(self, workspace_id: UUID, memory_id: UUID) -> bool:
        with self._connect() as db, db:
            result = db.execute(
                "DELETE FROM memory_items WHERE workspace_id=? AND memory_id=? AND state='active'",
                (str(workspace_id), str(memory_id)),
            )
        return result.rowcount > 0

    def active_memory_text(self, workspace_id: UUID, budget: int = 6000) -> list[str]:
        entries = self.memories(workspace_id)
        result: list[str] = []
        used = 0
        for entry in entries:
            size = len(entry.text.encode("utf-8"))
            if used + size > budget:
                raise ContextConflict("已确认记忆超过问答预算，请先编辑或删除部分记忆。")
            result.append(entry.text)
            used += size
        return result
