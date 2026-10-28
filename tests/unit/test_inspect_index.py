"""Unit tests for the read-only index inspector."""

from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from summit_everything.retrieval.chunking import TextChunk
from summit_everything.retrieval.store import IndexStore

INSPECT = Path(__file__).resolve().parents[2] / "scripts" / "inspect_index.py"


def load_inspect() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_inspect_index_under_test", INSPECT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_collect_and_render_active_index(tmp_path: Path) -> None:
    module = load_inspect()
    profile = tmp_path / "profile"
    workspace = tmp_path / "workspace"
    page_id = uuid4()
    page_dir = workspace / "客户与交付" / "书法首客"
    page_dir.mkdir(parents=True)
    (page_dir / "首客纪要.md").write_text(
        "---\n"
        f"id: {page_id}\n"
        "title: 首客纪要\n"
        "role: knowledge\n"
        "kind: log\n"
        "---\n"
        "# 本次沟通结论\n\n场地确认。\n",
        encoding="utf-8",
    )
    store = IndexStore(profile / str(uuid4()) / "index.sqlite3")
    store.replace_generation(
        uuid4(),
        "summit-fake-embedding-v1",
        [
            (
                TextChunk(
                    page_id=page_id,
                    content_sha256="a" * 64,
                    chunk_id="chunk-1",
                    heading="本次沟通结论",
                    text="场地确认。",
                ),
                [3.0, 4.0],
            )
        ],
        expected_generation=None,
        vector_dimension=2,
    )

    report = module.collect(profile, workspace, limit=10, preview=3)
    assert report["files"], "应找到 index.sqlite3"
    generation = report["files"][0]["generations"][0]
    assert generation["fingerprint"] == "summit-fake-embedding-v1"
    assert generation["page_count"] == 1
    assert generation["chunk_count"] == 1
    chunk = generation["chunks"][0]
    assert chunk["page_title"] == "首客纪要"
    assert chunk["heading"] == "本次沟通结论"
    assert chunk["vector"]["dimension"] == 2
    assert chunk["vector"]["norm"] == 5.0
    assert chunk["vector"]["preview"] == [3.0, 4.0]

    rendered = module.render(report, full=False, preview=3)
    assert "首客纪要" in rendered
    assert "本次沟通结论" in rendered
    assert "向量 2 维" in rendered
    assert "范数 5.000" in rendered


def test_collect_reports_missing_index(tmp_path: Path) -> None:
    module = load_inspect()
    report = module.collect(tmp_path / "missing-profile", None, limit=10, preview=3)
    assert report["files"] == []
    assert "没有找到索引库" in module.render(report, full=False, preview=3)


def _index_material_hash(path: Path) -> dict[str, str]:
    files = [path, *path.with_suffix(".lancedb").rglob("*")]
    return {
        str(item.relative_to(path.parent)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in files
        if item.is_file()
    }


def test_inspector_is_read_only_for_lancedb_and_handles_empty_generation(tmp_path: Path) -> None:
    module = load_inspect()
    profile = tmp_path / "profile"
    index_path = profile / str(uuid4()) / "index.sqlite3"
    store = IndexStore(index_path)
    workspace_id = uuid4()
    generation = store.replace_generation(
        workspace_id,
        "summit-fake-embedding-v1",
        [
            (
                TextChunk(
                    page_id=uuid4(),
                    content_sha256="a" * 64,
                    chunk_id="chunk-1",
                    heading="empty table fixture",
                    text="synthetic fixture",
                ),
                [1.0, 0.0],
            )
        ],
        expected_generation=None,
        vector_dimension=2,
    )
    store._db.open_table(generation.table_name).delete("true")
    assert store._db.open_table(generation.table_name).count_rows() == 0

    before = _index_material_hash(index_path)
    report = module.collect(profile, None, limit=0, preview=3)
    after = _index_material_hash(index_path)
    assert before == after
    entry = report["files"][0]["generations"][0]
    assert entry["chunk_count"] == 0
    assert entry["chunks"] == []


def test_inspector_only_reports_legacy_sqlite_vectors_without_reading_them(tmp_path: Path) -> None:
    module = load_inspect()
    profile = tmp_path / "profile"
    index_path = profile / str(uuid4()) / "index.sqlite3"
    index_path.parent.mkdir(parents=True)
    with sqlite3.connect(index_path) as connection:
        connection.execute(
            """CREATE TABLE active_generations (
                 workspace_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE chunks (
                 workspace_id TEXT, fingerprint TEXT, page_id TEXT, content_sha256 TEXT,
                 chunk_id TEXT, heading TEXT, text TEXT, vector_json TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO active_generations VALUES (?, ?)", ("legacy-workspace", "legacy-v1")
        )
        connection.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-workspace",
                "legacy-v1",
                "page",
                "a" * 64,
                "chunk",
                "heading",
                "private text",
                "[1,2]",
            ),
        )

    before = _index_material_hash(index_path)
    report = module.collect(profile, None, limit=10, preview=3)
    after = _index_material_hash(index_path)
    assert before == after
    generation = report["files"][0]["generations"][0]
    assert generation["status"] == "legacy_vectors_require_rebuild"
    assert generation["chunks"] == []
    assert "private text" not in module.render(report, full=True, preview=3)
