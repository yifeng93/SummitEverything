"""Profile-local LanceDB generations with a SQLite atomic active pointer.

SQLite stores generation pointers and history only. Chunk text and vectors live
in embedded LanceDB tables.
Successful generations are immutable and retained so a reader that already
opened one cannot observe a concurrent replacement.
"""

from __future__ import annotations

import math
import os
import sqlite3
import struct
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, LOCK_UN, flock
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import lancedb
import pyarrow as pa  # type: ignore[import-untyped]
from lancedb.index import FTS

from summit_everything.retrieval.chunking import TextChunk

_FTS_TOKENIZER = "ngram"
_FTS_NGRAM_LENGTH = 2
_BATCH_SIZE = 4096


class GenerationChanged(RuntimeError):
    """Another index operation published a generation while this one built."""


class IndexBusy(RuntimeError):
    """The local index is currently held by another operation."""


@dataclass(frozen=True, slots=True)
class IndexGeneration:
    workspace_id: UUID
    fingerprint: str
    generation_id: str
    table_name: str
    vector_dimension: int


class IndexStore:
    """LanceDB data tables coordinated by a local SQLite generation pointer."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.lance_path = path.with_suffix(".lancedb")
        self._db: Any | None = None
        with self._connect() as connection:
            tables = {
                str(row["name"])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            active_columns = self._active_generation_columns(connection)
            has_legacy_pointer = "active_generations" in tables and not {
                "generation_id",
                "table_name",
                "vector_dimension",
            }.issubset(active_columns)
            self._legacy_schema = has_legacy_pointer
            if not self._legacy_schema:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS active_generations (
                        workspace_id TEXT PRIMARY KEY,
                        fingerprint TEXT NOT NULL,
                        generation_id TEXT,
                        table_name TEXT,
                        vector_dimension INTEGER
                    );
                    CREATE TABLE IF NOT EXISTS index_generation_history (
                        workspace_id TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        generation_id TEXT NOT NULL,
                        table_name TEXT NOT NULL UNIQUE,
                        vector_dimension INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (workspace_id, generation_id)
                    );
                    """
                )

    @staticmethod
    def _add_column(
        connection: sqlite3.Connection, table: str, column: str, declaration: str
    ) -> None:
        columns = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level="DEFERRED")
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def generation_lease(self, *, exclusive: bool = False, wait: bool = True) -> Iterator[None]:
        """Lease this profile's generations across reads/builds; prune needs exclusivity."""
        flags = LOCK_EX if exclusive else LOCK_SH
        if not wait:
            flags |= LOCK_NB
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                flock(descriptor, flags)
            except BlockingIOError as error:
                raise IndexBusy(
                    "The local index is in use; retry after active operations finish"
                ) from error
            yield
        finally:
            try:
                flock(descriptor, LOCK_UN)
            finally:
                os.close(descriptor)

    @staticmethod
    def _table_name(workspace_id: UUID, fingerprint: str, generation_id: str) -> str:
        import hashlib

        material = f"{workspace_id}:{fingerprint}:{generation_id}".encode()
        return "gen_" + hashlib.sha256(material).hexdigest()[:32]

    def _table_names(self) -> set[str]:
        result: set[str] = set()
        page_token: str | None = None
        while True:
            page = self._lance_db().list_tables(page_token=page_token, limit=1000)
            result.update(page.tables)
            page_token = page.page_token
            if page_token is None:
                return result

    def _lance_db(self) -> Any:
        if self._db is None:
            self._db = lancedb.connect(str(self.lance_path))
        return self._db

    def active_generation(self, workspace_id: UUID) -> IndexGeneration | None:
        with self._connect() as connection:
            columns = self._active_generation_columns(connection)
            if not {"generation_id", "table_name", "vector_dimension"}.issubset(columns):
                return None
            row = connection.execute(
                """SELECT fingerprint, generation_id, table_name, vector_dimension
                   FROM active_generations WHERE workspace_id = ?""",
                (str(workspace_id),),
            ).fetchone()
        if (
            row is None
            or not row["generation_id"]
            or not row["table_name"]
            or row["vector_dimension"] is None
        ):
            return None
        return IndexGeneration(
            workspace_id=workspace_id,
            fingerprint=str(row["fingerprint"]),
            generation_id=str(row["generation_id"]),
            table_name=str(row["table_name"]),
            vector_dimension=int(row["vector_dimension"]),
        )

    def active_fingerprint(self, workspace_id: UUID) -> str | None:
        generation = self.active_generation(workspace_id)
        if generation is not None:
            return generation.fingerprint
        return None

    @staticmethod
    def _active_generation_columns(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(active_generations)")
        }

    def has_legacy_index(self, workspace_id: UUID) -> bool:
        """Report old SQLite-vector control state without reading its chunks."""
        with self._connect() as connection:
            columns = self._active_generation_columns(connection)
            tables = {
                str(item["name"])
                for item in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "active_generations" not in tables:
                return False
            row = connection.execute(
                "SELECT fingerprint FROM active_generations WHERE workspace_id = ?",
                (str(workspace_id),),
            ).fetchone()
            if row is None:
                return False
            required = {"generation_id", "table_name", "vector_dimension"}
            if not required.issubset(columns):
                return True
            metadata = connection.execute(
                """SELECT generation_id, table_name, vector_dimension
                   FROM active_generations WHERE workspace_id = ?""",
                (str(workspace_id),),
            ).fetchone()
            return (
                metadata is None
                or not metadata["generation_id"]
                or not metadata["table_name"]
                or metadata["vector_dimension"] is None
            )

    def _ensure_generation_metadata(self, connection: sqlite3.Connection) -> None:
        """Add pointer columns only when an explicitly confirmed rebuild publishes."""
        connection.execute(
            """CREATE TABLE IF NOT EXISTS active_generations (
                   workspace_id TEXT PRIMARY KEY,
                   fingerprint TEXT NOT NULL
               )"""
        )
        self._add_column(connection, "active_generations", "generation_id", "TEXT")
        self._add_column(connection, "active_generations", "table_name", "TEXT")
        self._add_column(connection, "active_generations", "vector_dimension", "INTEGER")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS index_generation_history (
                   workspace_id TEXT NOT NULL,
                   fingerprint TEXT NOT NULL,
                   generation_id TEXT NOT NULL,
                   table_name TEXT NOT NULL UNIQUE,
                   vector_dimension INTEGER NOT NULL,
                   created_at TEXT NOT NULL,
                   PRIMARY KEY (workspace_id, generation_id)
               )"""
        )

    @staticmethod
    def _validate_rows(rows: list[dict[str, Any]]) -> int:
        if not rows:
            raise ValueError("Cannot create an index generation with no vectors")
        dimension = 0
        seen: set[str] = set()
        for row in rows:
            vector = row["vector"]
            if not isinstance(vector, list) or not vector:
                raise ValueError("Index vector must be a non-empty numeric list")
            if dimension == 0:
                dimension = len(vector)
            if len(vector) != dimension:
                raise ValueError("Index vectors have inconsistent dimensions")
            for value in vector:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Index vectors must contain only finite numbers")
                if not math.isfinite(value):
                    raise ValueError("Index vectors must contain only finite numbers")
                try:
                    packed = struct.pack("!f", value)
                except OverflowError as error:
                    raise ValueError("Index vector exceeds LanceDB float32 range") from error
                if not math.isfinite(struct.unpack("!f", packed)[0]):
                    raise ValueError("Index vector exceeds LanceDB float32 range")
            if row["chunk_id"] in seen:
                raise ValueError("Index generation contains duplicate chunk IDs")
            seen.add(row["chunk_id"])
        return dimension

    @staticmethod
    def _native_rows(chunks: list[tuple[TextChunk, list[float]]]) -> list[dict[str, Any]]:
        rows = [
            {
                "page_id": str(chunk.page_id),
                "content_sha256": chunk.content_sha256,
                "chunk_id": chunk.chunk_id,
                "heading": chunk.heading,
                "text": chunk.text,
                "vector": vector,
            }
            for chunk, vector in chunks
        ]
        IndexStore._validate_rows(rows)
        return rows

    def _create_table(
        self, table_name: str, rows: list[dict[str, Any]], vector_dimension: int
    ) -> None:
        if table_name in self._table_names():
            self._lance_db().drop_table(table_name)
        schema = pa.schema(
            [
                pa.field("page_id", pa.string()),
                pa.field("content_sha256", pa.string()),
                pa.field("chunk_id", pa.string()),
                pa.field("heading", pa.string()),
                pa.field("text", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), vector_dimension)),
            ]
        )
        first = pa.Table.from_pylist(rows[:_BATCH_SIZE], schema=schema)
        table = self._lance_db().create_table(table_name, first, mode="create")
        for offset in range(_BATCH_SIZE, len(rows), _BATCH_SIZE):
            table.add(pa.Table.from_pylist(rows[offset : offset + _BATCH_SIZE], schema=schema))

    @staticmethod
    def _record_generation(
        connection: sqlite3.Connection,
        workspace_id: UUID,
        fingerprint: str,
        generation_id: str,
        table_name: str,
        vector_dimension: int,
    ) -> None:
        connection.execute(
            """INSERT INTO index_generation_history
               (workspace_id, fingerprint, generation_id, table_name, vector_dimension, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(workspace_id),
                fingerprint,
                generation_id,
                table_name,
                vector_dimension,
                datetime.now(UTC).isoformat(),
            ),
        )

    def _create_fts(self, table_name: str) -> None:
        table = self._lance_db().open_table(table_name)
        table.create_index(
            "text",
            config=FTS(
                base_tokenizer=_FTS_TOKENIZER,
                ngram_min_length=_FTS_NGRAM_LENGTH,
                ngram_max_length=3,
                remove_stop_words=False,
            ),
            replace=True,
        )

    def existing_chunks(self, workspace_id: UUID, fingerprint: str) -> dict[str, list[float]]:
        generation = self.active_generation(workspace_id)
        if generation is None or generation.fingerprint != fingerprint:
            return {}
        return self.existing_generation_chunks(generation)

    def existing_generation_chunks(self, generation: IndexGeneration) -> dict[str, list[float]]:
        table = self._lance_db().open_table(generation.table_name)
        rows = table.search().select(["chunk_id", "vector"]).limit(None).to_list()
        return {str(row["chunk_id"]): list(row["vector"]) for row in rows}

    def replace_generation(
        self,
        workspace_id: UUID,
        fingerprint: str,
        chunks: list[tuple[TextChunk, list[float]]],
        *,
        expected_generation: IndexGeneration | None,
        vector_dimension: int,
    ) -> IndexGeneration:
        with self.generation_lease():
            return self._replace_generation(
                workspace_id,
                fingerprint,
                chunks,
                expected_generation=expected_generation,
                vector_dimension=vector_dimension,
            )

    def _replace_generation(
        self,
        workspace_id: UUID,
        fingerprint: str,
        chunks: list[tuple[TextChunk, list[float]]],
        *,
        expected_generation: IndexGeneration | None,
        vector_dimension: int,
    ) -> IndexGeneration:
        rows = self._native_rows(chunks) if chunks else []
        dimension = len(rows[0]["vector"]) if rows else vector_dimension
        if dimension < 1 or (rows and dimension != vector_dimension):
            raise ValueError("Index generation vector dimension is invalid")
        generation_id = str(uuid4())
        table_name = self._table_name(workspace_id, fingerprint, generation_id)
        try:
            self._create_table(table_name, rows, dimension)
            if rows:
                self._create_fts(table_name)
            table = self._lance_db().open_table(table_name)
            if table.count_rows() != len(rows):
                raise ValueError("LanceDB generation row count did not match source")
            if table.schema.field("vector").type.list_size != dimension:
                raise ValueError("LanceDB generation vector dimension did not match source")
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_generation_metadata(connection)
                current = connection.execute(
                    """SELECT fingerprint, generation_id, table_name, vector_dimension
                       FROM active_generations WHERE workspace_id = ?""",
                    (str(workspace_id),),
                ).fetchone()
                expected_id = expected_generation.generation_id if expected_generation else None
                current_id = (
                    str(current["generation_id"]) if current and current["generation_id"] else None
                )
                if current_id != expected_id:
                    raise GenerationChanged(
                        "Active index generation changed while replacement built"
                    )
                connection.execute(
                    """INSERT INTO active_generations
                       (workspace_id, fingerprint, generation_id, table_name, vector_dimension)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(workspace_id) DO UPDATE SET
                         fingerprint = excluded.fingerprint,
                         generation_id = excluded.generation_id,
                         table_name = excluded.table_name,
                         vector_dimension = excluded.vector_dimension""",
                    (str(workspace_id), fingerprint, generation_id, table_name, dimension),
                )
                self._record_generation(
                    connection, workspace_id, fingerprint, generation_id, table_name, dimension
                )
                connection.commit()
        except BaseException:
            if table_name in self._table_names():
                self._lance_db().drop_table(table_name)
            raise
        return IndexGeneration(workspace_id, fingerprint, generation_id, table_name, dimension)

    def prune_old_generations(self, *, retain_previous: int = 1) -> dict[str, int]:
        """Remove unreachable tables; caller must ensure the app is stopped."""
        if retain_previous < 0:
            raise ValueError("retain_previous cannot be negative")
        with self.generation_lease(exclusive=True, wait=False), self._connect() as connection:
            tables = {
                str(row["name"])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "index_generation_history" not in tables:
                return {"removed_tables": 0, "retained_tables": 0}
            connection.execute("BEGIN IMMEDIATE")
            columns = self._active_generation_columns(connection)
            active_rows = (
                connection.execute(
                    "SELECT workspace_id, table_name FROM active_generations "
                    "WHERE table_name IS NOT NULL"
                ).fetchall()
                if "table_name" in columns
                else []
            )
            active = {str(row["workspace_id"]): str(row["table_name"]) for row in active_rows}
            all_rows = connection.execute(
                """SELECT workspace_id, table_name FROM index_generation_history
                   ORDER BY created_at DESC"""
            ).fetchall()
            keep: set[str] = set(active.values())
            previous_by_workspace: dict[str, int] = {}
            for row in all_rows:
                workspace = str(row["workspace_id"])
                table_name = str(row["table_name"])
                if active.get(workspace) == table_name:
                    continue
                retained = previous_by_workspace.get(workspace, 0)
                if retained < retain_previous:
                    keep.add(table_name)
                    previous_by_workspace[workspace] = retained + 1
            for row in all_rows:
                table_name = str(row["table_name"])
                if table_name not in keep:
                    connection.execute(
                        "DELETE FROM index_generation_history WHERE table_name = ?", (table_name,)
                    )
            connection.commit()
            removed = 0
            for table_name in self._table_names():
                if table_name.startswith("gen_") and table_name not in keep:
                    self._lance_db().drop_table(table_name)
                    removed += 1
        retained = sum(
            1 for name in self._table_names() if name.startswith("gen_") and name in keep
        )
        return {"removed_tables": removed, "retained_tables": retained}

    def generation_chunks(self, generation: IndexGeneration) -> list[dict[str, Any]]:
        table = self._lance_db().open_table(generation.table_name)
        rows = (
            table.search()
            .select(["page_id", "content_sha256", "chunk_id", "heading", "text"])
            .limit(None)
            .to_list()
        )
        return [
            {
                "page_id": UUID(str(row["page_id"])),
                "content_sha256": str(row["content_sha256"]),
                "chunk_id": str(row["chunk_id"]),
                "heading": str(row["heading"]),
                "text": str(row["text"]),
            }
            for row in rows
        ]

    def generation_page_versions(self, generation: IndexGeneration) -> list[tuple[str, str]]:
        """Read only chunk ownership/version columns for status comparisons."""
        table = self._lance_db().open_table(generation.table_name)
        rows = table.search().select(["page_id", "content_sha256"]).limit(None).to_list()
        return [(str(row["page_id"]), str(row["content_sha256"])) for row in rows]

    def search(
        self,
        generation: IndexGeneration,
        query_vector: list[float],
        query_text: str,
        *,
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if len(query_vector) != generation.vector_dimension:
            raise ValueError(
                "Query embedding dimension does not match the active index; "
                "choose the matching model."
            )
        table = self._lance_db().open_table(generation.table_name)
        columns = ["page_id", "content_sha256", "chunk_id", "heading", "text"]
        dense = (
            table.search(query_vector, query_type="vector")
            .metric("dot")
            .select(columns)
            .limit(limit)
            .to_list()
        )
        lexical = (
            table.search(query_text, query_type="fts")
            .select(columns + ["_score"])
            .limit(limit)
            .to_list()
        )
        return self._to_chunks(dense), self._to_chunks(lexical, scores=True)

    def search_bm25(
        self, workspace_id: UUID, query_text: str, *, limit: int
    ) -> tuple[IndexGeneration | None, list[dict[str, Any]]]:
        """Search only the active LanceDB generation under its shared lease."""
        with self.generation_lease():
            generation = self.active_generation(workspace_id)
            if generation is None:
                return None, []
            table = self._lance_db().open_table(generation.table_name)
            rows = (
                table.search(query_text, query_type="fts")
                .select(["page_id", "content_sha256", "chunk_id", "heading", "text", "_score"])
                .limit(limit)
                .to_list()
            )
            return generation, self._to_chunks(rows, scores=True)

    @staticmethod
    def _to_chunks(rows: list[dict[str, Any]], *, scores: bool = False) -> list[dict[str, Any]]:
        result = [
            {
                "page_id": UUID(str(row["page_id"])),
                "content_sha256": str(row["content_sha256"]),
                "chunk_id": str(row["chunk_id"]),
                "heading": str(row["heading"]),
                "text": str(row["text"]),
            }
            for row in rows
        ]
        if scores:
            for item, row in zip(result, rows, strict=True):
                item["bm25_score"] = float(row["_score"])
        return result

    def get_chunks(self, workspace_id: UUID, fingerprint: str) -> list[dict[str, Any]]:
        generation = self.active_generation(workspace_id)
        if generation is None or generation.fingerprint != fingerprint:
            return []
        return self.generation_chunks(generation)

    def status(self, workspace_id: UUID) -> dict[str, int | str | None]:
        with self.generation_lease():
            return self._status_locked(workspace_id)

    def _status_locked(self, workspace_id: UUID) -> dict[str, int | str | None]:
        generation = self.active_generation(workspace_id)
        if generation is None:
            return {"fingerprint": None, "pages": 0, "chunks": 0}
        rows = self.generation_chunks(generation)
        return {
            "fingerprint": generation.fingerprint,
            "pages": len({str(row["page_id"]) for row in rows}),
            "chunks": len(rows),
        }
