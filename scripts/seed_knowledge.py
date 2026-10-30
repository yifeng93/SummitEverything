"""Seed a real Markdown corpus into the development workspace.

This is a **development fixture**, not the normal user import flow. It writes
each Markdown file as an explicitly confirmed knowledge page directly into
`.local/dev/workspace`, then builds the local index once. The normal flow
(原件 → 待整理 → 稿件 → 确认) is intentionally not bypassed in production.

Typical use with DeepSeek Harness docs:

    git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/deepseek-ai/deepseek-harness.git /tmp/deepseek-harness
    cd /tmp/deepseek-harness && git sparse-checkout set docs

    uv run python scripts/seed_knowledge.py --source /tmp/deepseek-harness
    uv run python scripts/seed_knowledge.py --source /tmp/deepseek-harness --dry-run

The script prefers Chinese siblings (`*.zh.md`) when present, skips changelog /
upgrade / i18n folders, uses stable UUIDs (reruns skip existing pages), and
builds the index once at the end. It does not require the dev server to run.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import uuid
from pathlib import Path

from summit_everything.domain.models import LineRecord, ProjectRecord
from summit_everything.integrations.settings import SettingsStore, embedding_fingerprint
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    create_line,
    create_project,
    list_lines,
    list_projects,
    load_manifest,
)
from summit_everything.workspace.reader import list_pages
from summit_everything.workspace.writer import PageWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = ROOT / ".local" / "dev" / "workspace"
DEFAULT_PROFILE = ROOT / ".local" / "dev" / "profile"
SKIP_PARTS = {"persistence-changes", "upgrade-guide", "i18n", "node_modules", ".git"}
SKIP_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "THIRD_PARTY_NOTICES.md",
    "BRAND_GUIDELINES.md",
    "BRAND_GUIDELINES.zh.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.zh.md",
}
TITLE = re.compile(r"^#\s+(.+?)\s*#*\s*$")


def strip_frontmatter(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + 4 :].lstrip("\n")


def title_of(path: Path, body: str) -> str:
    for line in body.splitlines()[:80]:
        match = TITLE.match(line)
        if match:
            return match.group(1).strip()[:160]
    return path.stem.removesuffix(".zh").replace("-", " ").strip()[:160] or path.name


def relative_label(path: Path, root: Path) -> str:
    parent = path.parent.relative_to(root)
    return " / ".join(parent.parts) if parent.parts else "root"


def discover(source: Path) -> list[Path]:
    """Pick one language per document, skipping generated/changelog trees."""
    found: list[Path] = []
    for path in source.rglob("*.md"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name in SKIP_NAMES:
            continue
        if path.name.endswith(".zh.md"):
            sibling = path.with_name(path.name[:-6] + ".md")
            if sibling.exists():
                continue
            found.append(path)
            continue
        chinese = path.with_name(path.stem + ".zh.md")
        found.append(chinese if chinese.exists() else path)
    return sorted(set(found))


def ensure_line(root: Path, name: str) -> LineRecord:
    for line in list_lines(root):
        if line.name == name:
            return line
    return create_line(root, name, "seed-line-deepseek-harness")


def ensure_project(root: Path, line_id: uuid.UUID, name: str) -> ProjectRecord:
    for project in list_projects(root):
        if project.line_id == line_id and project.name == name:
            return project
    return create_project(root, line_id, name, "seed-project-deepseek-docs")


def build_index(root: Path, profile: Path) -> None:
    manifest = load_manifest(root)
    settings = SettingsStore(profile / "provider-settings.json").read()
    fingerprint = embedding_fingerprint(settings.embedding, mode=settings.mode)
    store = IndexStore(profile / str(manifest.workspace_id) / "index.sqlite3")
    service = QueryService(store)
    active = store.active_fingerprint(manifest.workspace_id)
    mode = "initial" if active is None else "incremental"
    plan = service.plan(root, fingerprint=fingerprint, mode=mode)
    print(f"[seed] 索引 {mode}：{len(plan.page_ids)} 页，约 {plan.estimated_tokens} token")
    result = service.execute_plan(root, plan)
    print(
        f"[seed] 索引完成：{result.indexed_pages} 页 / {result.indexed_chunks} 分块"
        f"（复用 {result.reused_chunks}）"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把 Markdown 文档灌入开发知识库")
    parser.add_argument("--source", type=Path, required=True, help="文档仓库根目录")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--line", default="DeepSeek Harness", help="主线名称")
    parser.add_argument("--project", default="官方文档", help="项目名称")
    parser.add_argument("--kind", default="topic", help="页面 kind（默认 topic）")
    parser.add_argument("--limit", type=int, default=0, help="只导入前 N 篇（0 = 全部）")
    parser.add_argument("--dry-run", action="store_true", help="只列出将导入的文档")
    parser.add_argument("--no-index", action="store_true", help="导入后不建立索引")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"文档目录不存在：{source}", file=sys.stderr)
        return 2
    workspace = args.workspace.expanduser().resolve()
    profile = args.profile.expanduser().resolve()
    if not (workspace / ".summit-everything" / "manifest.json").is_file():
        print(f"开发工作库不存在：{workspace}", file=sys.stderr)
        print("先运行：uv run python scripts/run_dev.py（会自动建开发库）", file=sys.stderr)
        return 2

    docs = discover(source)
    if args.limit > 0:
        docs = docs[: args.limit]
    if not docs:
        print("没有找到可导入的 Markdown。", file=sys.stderr)
        return 2

    print(f"[seed] 发现 {len(docs)} 篇文档；目标项目：{args.line} / {args.project}")
    if args.dry_run:
        for path in docs[:20]:
            body = strip_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            print(f"  - {path.relative_to(source)}  →  {title_of(path, body)}")
        if len(docs) > 20:
            print(f"  … 其余 {len(docs) - 20} 篇")
        return 0

    line = ensure_line(workspace, args.line)
    project = ensure_project(workspace, line.id, args.project)
    known = {str(page.page_id) for page in list_pages(workspace)}
    titles: set[str] = set()
    created = skipped = failed = 0
    started = time.monotonic()

    for index, path in enumerate(docs, start=1):
        raw = path.read_text(encoding="utf-8", errors="replace")
        body = strip_frontmatter(raw).strip()
        if not body:
            skipped += 1
            continue
        title = title_of(path, body)
        if title in titles:
            title = f"{title}（{relative_label(path, source)}）"
        titles.add(title)
        page_id = uuid.uuid5(uuid.NAMESPACE_URL, "dsh-docs:" + str(path.relative_to(source)))
        if str(page_id) in known:
            skipped += 1
            continue
        metadata = {
            "id": str(page_id),
            "title": title,
            "role": "knowledge",
            "kind": args.kind,
            "line_id": str(line.id),
            "project_id": str(project.id),
            "source": "deepseek-harness",
            "source_path": str(path.relative_to(source)),
            "language": "zh" if path.name.endswith(".zh.md") else "en",
        }
        try:
            PageWriter().confirm(
                workspace,
                metadata=metadata,
                body=body,
                confirmation_id=f"seed-{page_id}",
                operation_id=f"seed-op-{page_id}",
            )
            created += 1
        except Exception as exc:  # noqa: BLE001 - dev fixture reports the exact file
            failed += 1
            print(f"[seed] 失败：{path.relative_to(source)} → {exc}", file=sys.stderr)
        if index % 10 == 0 or index == len(docs):
            elapsed = time.monotonic() - started
            print(
                f"[seed] {index}/{len(docs)} · 新建 {created} · 跳过 {skipped}"
                f" · 失败 {failed} · {elapsed:.1f}s"
            )

    print(f"[seed] 页面完成：新建 {created}，跳过 {skipped}，失败 {failed}")
    if not args.no_index:
        build_index(workspace, profile)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
