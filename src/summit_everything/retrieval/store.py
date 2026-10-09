"""Small SQLite index with fingerprint-scoped, atomic generation replacement."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from summit_everything.retrieval.chunking import TextChunk


class IndexStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS active_generations (
                    workspace_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    workspace_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    heading TEXT NOT NULL,
                    text TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, fingerprint, chunk_id)
                );
                CREATE INDEX IF NOT EXISTS chunks_page
                    ON chunks (workspace_id, fingerprint, page_id);
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def active_fingerprint(self, workspace_id: UUID) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT fingerprint FROM active_generations WHERE workspace_id = ?",
                (str(workspace_id),),
            ).fetchone()
        return str(row["fingerprint"]) if row else None

    def existing_chunks(self, workspace_id: UUID, fingerprint: str) -> dict[str, list[float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, vector_json FROM chunks
                WHERE workspace_id = ? AND fingerprint = ?
                """,
                (str(workspace_id), fingerprint),
            ).fetchall()
        return {str(row["chunk_id"]): json.loads(row["vector_json"]) for row in rows}

    def replace_generation(
        self,
        workspace_id: UUID,
        fingerprint: str,
        chunks: list[tuple[TextChunk, list[float]]],
    ) -> None:
        with self._connect() as connection:
            with connection:
                connection.execute(
                    "DELETE FROM chunks WHERE workspace_id = ? AND fingerprint = ?",
                    (str(workspace_id), fingerprint),
                )
                connection.executemany(
                    """
                    INSERT INTO chunks (
                        workspace_id, fingerprint, page_id, content_sha256,
                        chunk_id, heading, text, vector_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(workspace_id),
                            fingerprint,
                            str(chunk.page_id),
                            chunk.content_sha256,
                            chunk.chunk_id,
                            chunk.heading,
                            chunk.text,
                            json.dumps(vector, separators=(",", ":")),
                        )
                        for chunk, vector in chunks
                    ],
                )
                connection.execute(
                    """
                    INSERT INTO active_generations (workspace_id, fingerprint)
                    VALUES (?, ?)
                    ON CONFLICT(workspace_id) DO UPDATE SET fingerprint = excluded.fingerprint
                    """,
                    (str(workspace_id), fingerprint),
                )

    def get_chunks(self, workspace_id: UUID, fingerprint: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT page_id, content_sha256, chunk_id, heading, text, vector_json
                FROM chunks WHERE workspace_id = ? AND fingerprint = ?
                """,
                (str(workspace_id), fingerprint),
            ).fetchall()
        return [
            {
                "page_id": UUID(row["page_id"]),
                "content_sha256": str(row["content_sha256"]),
                "chunk_id": str(row["chunk_id"]),
                "heading": str(row["heading"]),
                "text": str(row["text"]),
                "vector": json.loads(row["vector_json"]),
            }
            for row in rows
        ]
