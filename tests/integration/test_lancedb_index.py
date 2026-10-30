from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from summit_everything.retrieval.chunking import TextChunk
from summit_everything.retrieval.store import GenerationChanged, IndexBusy, IndexStore


def _chunks(count: int = 137) -> list[tuple[TextChunk, list[float]]]:
    page_id = uuid4()
    result = []
    for index in range(count):
        text = (
            f"云杉大厦消防验收方案和疏散通道复核，第 {index} 项。"
            if index == 7
            else f"样本文档内容编号 {index}，记录常规业务信息。"
        )
        chunk = TextChunk(
            page_id=page_id,
            content_sha256="a" * 64,
            chunk_id=f"chunk-{index:04d}",
            heading="中文验收" if index == 7 else "合成样本",
            text=text,
        )
        # The lexical target intentionally ranks last in dense search. Hybrid
        # retrieval must still surface it from the native Chinese FTS index.
        vector = [0.0, 1.0, 0.0] if index == 7 else [1.0, 0.0, 0.0]
        result.append((chunk, vector))
    return result


def test_lancedb_native_vector_and_chinese_fts_keep_more_than_default_rows(
    tmp_path: Path,
) -> None:
    store = IndexStore(tmp_path / "index.sqlite3")
    workspace_id = uuid4()
    chunks = _chunks()
    generation = store.replace_generation(
        workspace_id,
        "fake-v1",
        chunks,
        expected_generation=None,
        vector_dimension=3,
    )

    assert store.active_generation(workspace_id) == generation
    assert len(store.generation_chunks(generation)) == len(chunks)
    assert len(store.existing_generation_chunks(generation)) == len(chunks)
    assert store.generation_page_versions(generation) == [
        (str(chunks[0][0].page_id), "a" * 64)
    ] * len(chunks)
    dense, lexical = store.search(generation, [1.0, 0.0, 0.0], "消防验收疏散通道", limit=137)
    assert len(dense) == 137
    assert dense[-1]["chunk_id"] == "chunk-0007"
    assert lexical
    assert lexical[0]["chunk_id"] == "chunk-0007"
    assert "bm25_score" in lexical[0]


def test_failed_fts_creation_keeps_previous_generation_and_prune_retains_one_previous(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = IndexStore(tmp_path / "index.sqlite3")
    workspace_id = uuid4()
    first = store.replace_generation(
        workspace_id,
        "fake-v1",
        _chunks(3),
        expected_generation=None,
        vector_dimension=3,
    )
    second = store.replace_generation(
        workspace_id,
        "fake-v1",
        _chunks(4),
        expected_generation=first,
        vector_dimension=3,
    )
    original = store._create_fts

    def fail_fts(_table_name: str) -> None:
        raise RuntimeError("synthetic FTS build failure")

    monkeypatch.setattr(store, "_create_fts", fail_fts)
    with pytest.raises(RuntimeError, match="synthetic FTS build failure"):
        store.replace_generation(
            workspace_id,
            "fake-v1",
            _chunks(5),
            expected_generation=second,
            vector_dimension=3,
        )
    assert store.active_generation(workspace_id) == second
    assert store._db.open_table(first.table_name).count_rows() == 3
    assert store._db.open_table(second.table_name).count_rows() == 4

    monkeypatch.setattr(store, "_create_fts", original)
    with pytest.raises(GenerationChanged):
        store.replace_generation(
            workspace_id,
            "fake-v1",
            _chunks(2),
            expected_generation=first,
            vector_dimension=3,
        )
    assert store.active_generation(workspace_id) == second
    third = store.replace_generation(
        workspace_id,
        "fake-v1",
        _chunks(5),
        expected_generation=second,
        vector_dimension=3,
    )
    assert store.active_generation(workspace_id) == third
    assert store.prune_old_generations(retain_previous=1) == {
        "removed_tables": 1,
        "retained_tables": 2,
    }


def test_new_store_does_not_create_legacy_sqlite_chunk_table(tmp_path: Path) -> None:
    path = tmp_path / "index.sqlite3"
    IndexStore(path)
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        columns = {row[1] for row in connection.execute("PRAGMA table_info(active_generations)")}
    assert "chunks" not in tables
    assert {
        "workspace_id",
        "fingerprint",
        "generation_id",
        "table_name",
        "vector_dimension",
    } <= columns


def test_legacy_vectors_are_not_read_and_failed_explicit_rebuild_preserves_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "index.sqlite3"
    workspace_id = uuid4()
    chunk = _chunks(1)[0][0]
    vector = [0.25, 0.5, 0.75]
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE active_generations (
                 workspace_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL
               )"""
        )
        connection.execute(
            """CREATE TABLE chunks (
                 workspace_id TEXT NOT NULL, fingerprint TEXT NOT NULL, page_id TEXT NOT NULL,
                 content_sha256 TEXT NOT NULL, chunk_id TEXT NOT NULL, heading TEXT NOT NULL,
                 text TEXT NOT NULL, vector_json TEXT NOT NULL,
                 PRIMARY KEY (workspace_id, fingerprint, chunk_id))"""
        )
        connection.execute(
            "INSERT INTO active_generations (workspace_id, fingerprint) VALUES (?, ?)",
            (str(workspace_id), "legacy-v1"),
        )
        connection.execute(
            """INSERT INTO chunks (workspace_id, fingerprint, page_id, content_sha256,
               chunk_id, heading, text, vector_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(workspace_id),
                "legacy-v1",
                str(chunk.page_id),
                chunk.content_sha256,
                chunk.chunk_id,
                chunk.heading,
                chunk.text,
                json.dumps(vector),
            ),
        )

    store = IndexStore(path)
    assert store.has_legacy_index(workspace_id)
    assert store.active_generation(workspace_id) is None
    assert store.active_fingerprint(workspace_id) is None
    assert store.status(workspace_id) == {"fingerprint": None, "pages": 0, "chunks": 0}
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(active_generations)")}
        source_count = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE workspace_id = ?", (str(workspace_id),)
        ).fetchone()[0]
        source = connection.execute(
            "SELECT vector_json FROM chunks WHERE workspace_id = ? AND chunk_id = ?",
            (str(workspace_id), chunk.chunk_id),
        ).fetchone()
    assert columns == {"workspace_id", "fingerprint"}
    assert source_count == 1
    assert source is not None and json.loads(source[0]) == vector

    def fail_fts(_table_name: str) -> None:
        raise RuntimeError("synthetic FTS build failure")

    monkeypatch.setattr(store, "_create_fts", fail_fts)
    with pytest.raises(RuntimeError, match="synthetic FTS build failure"):
        store.replace_generation(
            workspace_id,
            "fake-v1",
            _chunks(2),
            expected_generation=None,
            vector_dimension=3,
        )
    with sqlite3.connect(path) as connection:
        columns_after_failure = {
            row[1] for row in connection.execute("PRAGMA table_info(active_generations)")
        }
        pointer = connection.execute(
            "SELECT fingerprint FROM active_generations WHERE workspace_id = ?",
            (str(workspace_id),),
        ).fetchone()
    assert columns_after_failure == {"workspace_id", "fingerprint"}
    assert pointer == ("legacy-v1",)

    monkeypatch.undo()
    generation = store.replace_generation(
        workspace_id,
        "fake-v1",
        _chunks(2),
        expected_generation=None,
        vector_dimension=3,
    )
    assert store.active_generation(workspace_id) == generation
    assert not store.has_legacy_index(workspace_id)
    with sqlite3.connect(path) as connection:
        source = connection.execute(
            "SELECT vector_json FROM chunks WHERE workspace_id = ? AND chunk_id = ?",
            (str(workspace_id), chunk.chunk_id),
        ).fetchone()
    assert source is not None and json.loads(source[0]) == vector

    fresh = IndexStore(tmp_path / "fresh.sqlite3")
    fresh_generation = fresh.replace_generation(
        uuid4(), "fake-v1", _chunks(1), expected_generation=None, vector_dimension=3
    )
    with pytest.raises(ValueError, match="dimension"):
        fresh.search(fresh_generation, [1.0, 0.0], "synthetic", limit=1)


def test_pruning_requires_exclusive_generation_lease(tmp_path: Path) -> None:
    store = IndexStore(tmp_path / "index.sqlite3")
    with store.generation_lease():
        with pytest.raises(IndexBusy, match="index is in use"):
            store.prune_old_generations()


def test_separate_sqlite_indexes_have_isolated_lancedb_directories(tmp_path: Path) -> None:
    first_store = IndexStore(tmp_path / "first.sqlite3")
    second_store = IndexStore(tmp_path / "second.sqlite3")
    first = first_store.replace_generation(
        uuid4(), "fake-v1", _chunks(2), expected_generation=None, vector_dimension=3
    )
    second = second_store.replace_generation(
        uuid4(), "fake-v1", _chunks(3), expected_generation=None, vector_dimension=3
    )

    assert first_store.lance_path != second_store.lance_path
    first_store.prune_old_generations()
    assert second_store._db.open_table(second.table_name).count_rows() == 3
    assert first_store._db.open_table(first.table_name).count_rows() == 2
