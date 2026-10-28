"""Read-only inspection of the local vector index.

Usage:
    uv run python scripts/inspect_index.py
    uv run python scripts/inspect_index.py \
        --profile .local/dev/profile --workspace .local/dev/workspace
    uv run python scripts/inspect_index.py --full --limit 5
    uv run python scripts/inspect_index.py --json

默认读取开发环境 `.local/dev/{profile,workspace}`。SQLite 位于 profile 的
`<profile>/<workspace-id>/index.sqlite3`，保存活动 generation 指针；正文和向量保存在相邻
`index.lancedb`。旧 SQLite-only 格式只报告需重建，不读取其 chunk 内容。本脚本以只读方式检查
SQLite 并读取 LanceDB 表，不会写入或重建索引。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys

import lancedb
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / ".local" / "dev" / "profile"
DEFAULT_WORKSPACE = ROOT / ".local" / "dev" / "workspace"
FRONTMATTER = re.compile(r"^(id|title):\s*(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    page_id: str
    heading: str
    text: str
    vector: list[float]


@dataclass(frozen=True)
class Generation:
    workspace_id: str
    fingerprint: str
    page_count: int
    chunk_count: int
    chunks: list[Chunk]
    status: str = "ready"


def page_titles(workspace: Path | None) -> dict[str, str]:
    """Map page id -> title from Markdown frontmatter.

    Only the first 40 lines of each Markdown file are read; this is a
    diagnostic helper, not a second page parser.
    """
    titles: dict[str, str] = {}
    if workspace is None or not workspace.is_dir():
        return titles
    for path in workspace.rglob("*.md"):
        try:
            head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:40])
        except OSError:
            continue
        found = {key: value.strip().strip("'\"") for key, value in FRONTMATTER.findall(head)}
        page_id, title = found.get("id"), found.get("title")
        if page_id and title:
            titles[page_id] = title
    return titles


def read_index(path: Path, limit: int) -> list[Generation]:
    """Read generation pointers and LanceDB rows without opening a writable store."""
    if not path.is_file():
        return []
    uri = f"file:{path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "active_generations" not in tables:
            return []
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(active_generations)")
        }
        if not {"generation_id", "table_name", "vector_dimension"}.issubset(columns):
            # The old format is deliberately not read: its chunks/vector_json rows stay untouched.
            rows = connection.execute(
                "SELECT workspace_id, fingerprint FROM active_generations ORDER BY workspace_id"
            ).fetchall()
            return [
                Generation(str(row["workspace_id"]), str(row["fingerprint"]), 0, 0, [],
                           "legacy_vectors_require_rebuild")
                for row in rows
            ]
        active = connection.execute(
            """SELECT workspace_id, fingerprint, generation_id, table_name, vector_dimension
               FROM active_generations ORDER BY workspace_id"""
        ).fetchall()
        result: list[Generation] = []
        for row in active:
            db_path = path.with_suffix(".lancedb")
            table_name = str(row["table_name"] or "")
            if not table_name or not db_path.exists():
                continue
            table = lancedb.connect(str(db_path)).open_table(table_name)
            total = table.count_rows()
            all_page_ids = table.search().select(["page_id"]).limit(None).to_list()
            page_count = len({str(item["page_id"]) for item in all_page_ids})
            rows = table.search().select(["page_id", "heading", "text", "vector"]).limit(
                min(limit, total)
            ).to_list()
            chunks = [
                Chunk(
                    page_id=str(item["page_id"]),
                    heading=str(item["heading"]),
                    text=str(item["text"]),
                    vector=[float(value) for value in item["vector"]],
                )
                for item in rows
            ]
            result.append(
                Generation(
                    workspace_id=str(row["workspace_id"]),
                    fingerprint=str(row["fingerprint"]),
                    page_count=page_count,
                    chunk_count=total,
                    chunks=chunks,
                )
            )
        return result
    finally:
        connection.close()


def vector_stats(values: list[float], preview: int) -> dict[str, Any]:
    norm = math.sqrt(sum(value * value for value in values)) if values else 0.0
    return {
        "dimension": len(values),
        "norm": round(norm, 6),
        "preview": [round(value, 6) for value in values[:preview]],
    }


def collect(profile: Path, workspace: Path | None, limit: int, preview: int) -> dict[str, Any]:
    databases = sorted(profile.rglob("index.sqlite3")) if profile.is_dir() else []
    titles = page_titles(workspace)
    files: list[dict[str, Any]] = []
    for path in databases:
        generations = []
        for generation in read_index(path, limit):
            chunks = []
            for chunk in generation.chunks:
                chunks.append(
                    {
                        "page_id": chunk.page_id,
                        "page_title": titles.get(chunk.page_id, "未命名页面"),
                        "heading": chunk.heading,
                        "text": chunk.text,
                        "vector": vector_stats(chunk.vector, preview),
                    }
                )
            generations.append(
                {
                    "workspace_id": generation.workspace_id,
                    "fingerprint": generation.fingerprint,
                    "page_count": generation.page_count,
                    "chunk_count": generation.chunk_count,
                    "status": generation.status,
                    "chunks": chunks,
                }
            )
        files.append({"path": str(path), "generations": generations})
    return {
        "profile": str(profile),
        "workspace": str(workspace) if workspace else None,
        "files": files,
    }


def render(report: dict[str, Any], full: bool, preview: int) -> str:
    lines: list[str] = []
    if not report["files"]:
        lines.append(f"没有找到索引库：{report['profile']}/**/index.sqlite3")
        lines.append("先在应用里完成一次正式内容确认，或到「审批 → 索引」建立首次索引。")
        return "\n".join(lines)

    for entry in report["files"]:
        lines.append(f"索引文件  {entry['path']}")
        if not entry["generations"]:
            lines.append("  尚无 active generation（还没有建立过可用索引）。")
            continue
        for generation in entry["generations"]:
            chunks = generation["chunks"]
            if generation["status"] == "legacy_vectors_require_rebuild":
                lines.append(f"  工作库 {generation['workspace_id']}  ·  旧 SQLite 向量需显式重建")
                continue
            lines.append(
                f"  工作库 {generation['workspace_id']}  ·  指纹 {generation['fingerprint']}"
            )
            shown = (
                f"（显示前 {len(chunks)} 个）" if generation["chunk_count"] > len(chunks) else ""
            )
            summary = (
                f"  页面 {generation['page_count']} 页  ·  "
                f"分块 {generation['chunk_count']} 个{shown}  ·  向量预览 {preview} 维"
            )
            lines.append(summary)
            current_page = None
            for index, chunk in enumerate(chunks, start=1):
                if chunk["page_id"] != current_page:
                    current_page = chunk["page_id"]
                    lines.append("")
                    lines.append(f"  [{chunk['page_title']}]  {chunk['page_id']}")
                vector = chunk["vector"]
                lines.append(
                    f"    {index}. {chunk['heading'] or '（无标题段）'}"
                    f"  ·  {len(chunk['text'])} 字"
                    f"  ·  向量 {vector['dimension']} 维"
                    f"  ·  范数 {vector['norm']:.3f}"
                )
                lines.append(f"       向量前几维  {vector['preview']}")
                text = chunk["text"] if full else chunk["text"].replace("\n", " ")[:80]
                if text:
                    lines.append(f"       正文  {text}{'' if full else '…'}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读查看本机索引库")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--limit", type=int, default=20, help="最多显示的 chunk 数（默认 20）")
    parser.add_argument("--preview", type=int, default=3, help="向量前几维（默认 3）")
    parser.add_argument("--full", action="store_true", help="显示完整 chunk 正文")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.profile.is_dir():
        print(f"profile 不存在：{args.profile}", file=sys.stderr)
        print("开发环境先运行：uv run python scripts/run_dev.py", file=sys.stderr)
        return 2

    report = collect(args.profile, args.workspace, max(args.limit, 1), max(args.preview, 0))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, args.full, max(args.preview, 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
