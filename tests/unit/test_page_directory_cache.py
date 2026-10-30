"""页目录缓存：同一目录在文件未变时不再重复读取。"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import summit_everything.workspace.reader as page_reader
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.reader import formal_pages_revision, list_pages
from summit_everything.workspace.writer import PageWriter


def _workspace(root: Path) -> tuple[Path, str, str]:
    create_workspace(root, "缓存模拟库", root.parent / "profile", "workspace")
    line = create_line(root, "模拟线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    return root, str(line.id), str(project.id)


def _page(root: Path, line_id: str, project_id: str, body: str, title: str = "模拟事实") -> UUID:
    metadata = {
        "id": str(uuid4()),
        "title": title,
        "role": "knowledge",
        "kind": "topic",
        "line_id": line_id,
        "project_id": project_id,
    }
    PageWriter().confirm(
        root,
        metadata=metadata,
        body=body,
        confirmation_id=f"confirm-{title}-{body[:8]}",
        operation_id=f"write-{title}-{body[:8]}",
    )
    return UUID(str(metadata["id"]))


def test_list_pages_reuses_snapshots_until_a_file_changes(tmp_path: Path, monkeypatch) -> None:
    root, line_id, project_id = _workspace(tmp_path / "workspace")
    _page(root, line_id, project_id, "第一页正文。")

    reads = 0
    original = Path.read_bytes

    def counting(self: Path) -> bytes:
        nonlocal reads
        reads += 1
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", counting)

    first = list_pages(root)
    assert first and reads > 0
    first_reads = reads

    # 没有文件变化：命中缓存，不再读文件。
    second = list_pages(root)
    assert [page.page_id for page in second] == [page.page_id for page in first]
    assert reads == first_reads

    # 新增一页：签名变化，重新读。
    _page(root, line_id, project_id, "第二页正文。", title="另一项事实")
    third = list_pages(root)
    assert len(third) == len(first) + 1
    assert reads > first_reads


def test_page_revision_tracks_atomic_add_replace_delete_without_markdown_parse(
    tmp_path: Path, monkeypatch
) -> None:
    root, line_id, project_id = _workspace(tmp_path / "workspace")
    page_id = _page(root, line_id, project_id, "旧正文")
    source = next((root / "模拟线" / "模拟项目").glob("*.md"))
    monkeypatch.setattr(
        page_reader,
        "_split_markdown",
        lambda _raw: (_ for _ in ()).throw(AssertionError("parsed markdown")),
    )
    original = formal_pages_revision(root)
    staged = source.with_suffix(".tmp")
    staged.write_text(
        source.read_text(encoding="utf-8").replace("旧正文", "新正文"), encoding="utf-8"
    )
    staged.replace(source)
    replaced = formal_pages_revision(root)
    source.unlink()
    deleted = formal_pages_revision(root)
    assert page_id
    assert len({original, replaced, deleted}) == 3
