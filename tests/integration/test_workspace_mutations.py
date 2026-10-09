from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from summit_everything.workspace.manifest import (
    WorkspaceError,
    create_line,
    create_project,
    create_workspace,
)
from summit_everything.workspace.reader import list_pages
from summit_everything.workspace.writer import (
    PageWriter,
    WorkspaceWriteConflict,
    WorkspaceWriter,
)


def make_workspace(root: Path) -> tuple[Path, str, str]:
    create_workspace(root, "模拟库", root.parent / "local-profile", "create-workspace")
    line = create_line(root, "模拟线", "create-line")
    project = create_project(root, line.id, "模拟项目", "create-project")
    return root, str(line.id), str(project.id)


def page_metadata(line_id: str, project_id: str) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "title": "模拟事实",
        "role": "knowledge",
        "kind": "object",
        "line_id": line_id,
        "project_id": project_id,
        "custom_field": {"preserve": True},
    }


def test_page_is_written_as_confirmed_only_through_explicit_confirmation(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    metadata = page_metadata(line_id, project_id)

    result = PageWriter().confirm(
        root,
        metadata=metadata,
        body="隔离模拟的已确认事实。\n",
        confirmation_id="user-confirmation-1",
        operation_id="write-page-1",
    )

    page = list_pages(root)[0]
    assert result.saved_locally is True
    assert page.approval_state == "confirmed"
    assert page.metadata["custom_field"] == {"preserve": True}
    assert page.metadata["approval"]["confirmation_id"] == "user-confirmation-1"
    transaction_receipts = (root / ".summit-everything" / "transactions").glob("mutation-*.json")
    assert all(
        "隔离模拟的已确认事实" not in receipt.read_text() for receipt in transaction_receipts
    )


def test_empty_page_cannot_receive_a_confirmation_proof(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")

    with pytest.raises(WorkspaceError, match="cannot be confirmed"):
        PageWriter().confirm(
            root,
            metadata=page_metadata(line_id, project_id),
            body="  \n",
            confirmation_id="empty-confirmation",
            operation_id="empty-page",
        )

    assert list_pages(root) == []


def test_changed_base_version_cannot_be_overwritten(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    writer = PageWriter()
    metadata = page_metadata(line_id, project_id)
    first = writer.confirm(
        root,
        metadata=metadata,
        body="第一版。\n",
        confirmation_id="confirm-v1",
        operation_id="write-v1",
    )
    page_path = root / first.changed_paths[0]
    page_path.write_text(
        page_path.read_text(encoding="utf-8").replace("第一版", "外部编辑"), encoding="utf-8"
    )

    with pytest.raises(WorkspaceWriteConflict, match="changed since it was reviewed"):
        writer.confirm(
            root,
            metadata=metadata,
            body="覆盖尝试。\n",
            confirmation_id="confirm-v2",
            operation_id="write-v2",
            expected_base_sha256=first.page_versions[str(metadata["id"])],
        )

    assert "外部编辑" in page_path.read_text(encoding="utf-8")


def test_confirmed_page_update_uses_the_reviewed_content_version(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    writer = PageWriter()
    metadata = page_metadata(line_id, project_id)
    first = writer.confirm(
        root,
        metadata=metadata,
        body="第一版。\n",
        confirmation_id="confirm-v1",
        operation_id="update-v1",
    )

    updated = writer.confirm(
        root,
        metadata=metadata,
        body="第二版。\n",
        confirmation_id="confirm-v2",
        operation_id="update-v2",
        expected_base_sha256=first.page_versions[str(metadata["id"])],
    )

    page = list_pages(root)[0]
    assert updated.page_versions[str(metadata["id"])] != first.page_versions[str(metadata["id"])]
    assert page.body == "第二版。\n"
    assert page.approval_state == "confirmed"


def test_page_confirmation_cannot_change_primary_project_silently(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    metadata = page_metadata(line_id, project_id)
    first = PageWriter().confirm(
        root,
        metadata=metadata,
        body="当前归属的事实。\n",
        confirmation_id="confirm-owner-v1",
        operation_id="write-owner-v1",
    )
    other_project = create_project(root, UUID(line_id), "另一项目", "other-project")
    moved_metadata = {**metadata, "project_id": str(other_project.id)}

    with pytest.raises(
        WorkspaceWriteConflict, match="ownership changes need structure confirmation"
    ):
        PageWriter().confirm(
            root,
            metadata=moved_metadata,
            body="改归属的事实。\n",
            confirmation_id="confirm-owner-v2",
            operation_id="write-owner-v2",
            expected_base_sha256=first.page_versions[str(metadata["id"])],
        )

    page = list_pages(root)[0]
    assert page.metadata["project_id"] == project_id
    assert page.body == "当前归属的事实。\n"


def test_same_write_intent_replays_result_and_rejects_different_payload(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    metadata = page_metadata(line_id, project_id)
    writer = PageWriter()
    first = writer.confirm(
        root,
        metadata=metadata,
        body="同一稿件。\n",
        confirmation_id="confirm-once",
        operation_id="stable-page-operation",
    )
    retry = writer.confirm(
        root,
        metadata=metadata,
        body="同一稿件。\n",
        confirmation_id="confirm-once",
        operation_id="stable-page-operation",
    )
    assert retry.operation_id == first.operation_id
    assert retry.page_versions == first.page_versions

    with pytest.raises(WorkspaceWriteConflict, match="different payload"):
        writer.confirm(
            root,
            metadata=metadata,
            body="改过的稿件。\n",
            confirmation_id="confirm-once",
            operation_id="stable-page-operation",
        )

    assert len(list_pages(root)) == 1


def test_same_project_move_updates_links_and_preserves_confirmed_pages(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    page_writer = PageWriter()
    target_metadata = page_metadata(line_id, project_id)
    target = page_writer.confirm(
        root,
        metadata=target_metadata,
        body="权威目标内容。\n",
        confirmation_id="target-confirmation",
        operation_id="create-target",
    )
    link_metadata = page_metadata(line_id, project_id)
    link_metadata["title"] = "链接页"
    page_writer.confirm(
        root,
        metadata=link_metadata,
        body=(
            f"正文引用 [权威页]({Path(target.changed_paths[0]).name}#合同)。\n"
            f"代码示例 `[权威页]({Path(target.changed_paths[0]).name})`\n"
            f"```md\n[代码块链接]({Path(target.changed_paths[0]).name})\n```\n"
        ),
        confirmation_id="link-confirmation",
        operation_id="create-link-page",
    )
    new_path = f"模拟线/模拟项目/历史/{target_metadata['title']}-old.md"

    moved = WorkspaceWriter().move_page(
        root,
        UUID(str(target_metadata["id"])),
        new_path,
        operation_id="move-target",
    )

    pages = {page.page_id: page for page in list_pages(root)}
    target_page = pages[UUID(str(target_metadata["id"]))]
    link_page = pages[UUID(str(link_metadata["id"]))]
    assert set(moved.changed_paths) == {
        target.changed_paths[0],
        new_path,
        "模拟线/模拟项目/链接页.md",
    }
    assert target_page.relative_path == new_path
    assert target_page.approval_state == "confirmed"
    assert link_page.approval_state == "confirmed"
    assert f"](历史/{target_metadata['title']}-old.md#合同)" in link_page.body
    assert f"`[权威页]({Path(target.changed_paths[0]).name})`" in link_page.body
    assert f"[代码块链接]({Path(target.changed_paths[0]).name})" in link_page.body
    assert not (root / target.changed_paths[0]).exists()


def test_page_cannot_move_across_projects_without_a_structure_confirmation(tmp_path: Path) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    metadata = page_metadata(line_id, project_id)
    PageWriter().confirm(
        root,
        metadata=metadata,
        body="内容。\n",
        confirmation_id="page-confirmation",
        operation_id="create-page",
    )
    create_project(root, UUID(line_id), "其他项目", "other-project")

    with pytest.raises(WorkspaceWriteConflict, match="(?i)cross-project move needs confirmation"):
        WorkspaceWriter().move_page(
            root,
            UUID(str(metadata["id"])),
            "模拟线/其他项目/已移动.md",
            operation_id="move-across-projects",
        )

    assert not (root / "模拟线/其他项目/已移动.md").exists()


def test_cross_project_move_with_structure_confirmation_updates_owner_and_proof(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = make_workspace(tmp_path / "workspace")
    metadata = page_metadata(line_id, project_id)
    PageWriter().confirm(
        root,
        metadata=metadata,
        body="需要移动的事实。\n",
        confirmation_id="page-confirmation",
        operation_id="create-page",
    )
    destination_project = create_project(root, UUID(line_id), "目标项目", "target-project")

    moved = WorkspaceWriter().move_page(
        root,
        UUID(str(metadata["id"])),
        f"{destination_project.directory}/移动后的页面.md",
        operation_id="confirmed-cross-project-move",
        structure_confirmation_id="structure-confirmation",
    )

    page = list_pages(root)[0]
    assert page.relative_path.endswith("/移动后的页面.md")
    assert page.metadata["project_id"] == str(destination_project.id)
    assert page.metadata["approval"]["confirmation_id"] == "structure-confirmation"
    assert page.page_id == UUID(str(metadata["id"]))
    assert page.approval_state == "confirmed"
    assert moved.page_versions[str(page.page_id)] == page.content_sha256


def test_interrupted_multi_file_write_recovers_without_losing_either_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = make_workspace(tmp_path / "workspace")
    first_path, second_path = root / "state" / "first.txt", root / "state" / "second.txt"
    changes = {
        "state/first.txt": b"first committed\n",
        "state/second.txt": b"second committed\n",
    }
    original_atomic_write = __import__(
        "summit_everything.workspace.writer", fromlist=["atomic_write"]
    ).atomic_write
    failed = False

    def fail_second_target(path: Path, content: bytes) -> None:
        nonlocal failed
        if path == second_path and not failed:
            failed = True
            raise OSError("simulated disk interruption")
        original_atomic_write(path, content)

    monkeypatch.setattr("summit_everything.workspace.writer.atomic_write", fail_second_target)
    writer = WorkspaceWriter()
    expected = {"state/first.txt": None, "state/second.txt": None}
    with pytest.raises(OSError, match="simulated disk interruption"):
        writer.apply("multi-write-1", root, expected, changes)

    monkeypatch.setattr("summit_everything.workspace.writer.atomic_write", original_atomic_write)
    list_pages(root)
    assert second_path.read_bytes() == b"second committed\n"
    result = writer.apply("multi-write-1", root, expected, changes)

    assert result.saved_locally is True
    assert first_path.read_bytes() == b"first committed\n"
    assert second_path.read_bytes() == b"second committed\n"


def test_recovery_preserves_an_unexpected_external_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = make_workspace(tmp_path / "workspace")
    first_path, second_path = root / "state" / "first.txt", root / "state" / "second.txt"
    original_atomic_write = __import__(
        "summit_everything.workspace.writer", fromlist=["atomic_write"]
    ).atomic_write

    def fail_second_target(path: Path, content: bytes) -> None:
        if path == second_path:
            raise OSError("simulated interruption")
        original_atomic_write(path, content)

    monkeypatch.setattr("summit_everything.workspace.writer.atomic_write", fail_second_target)
    writer = WorkspaceWriter()
    with pytest.raises(OSError, match="simulated interruption"):
        writer.apply(
            "external-edit-during-recovery",
            root,
            {"state/first.txt": None, "state/second.txt": None},
            {"state/first.txt": b"journal first", "state/second.txt": b"journal second"},
        )
    monkeypatch.setattr("summit_everything.workspace.writer.atomic_write", original_atomic_write)
    second_path.write_bytes(b"external edit")

    with pytest.raises(WorkspaceWriteConflict, match="interrupted operation was pending"):
        writer.recover(root)

    assert first_path.read_bytes() == b"journal first"
    assert second_path.read_bytes() == b"external edit"


def test_recovery_stops_on_a_corrupt_transaction_journal(tmp_path: Path) -> None:
    root, _, _ = make_workspace(tmp_path / "workspace")
    journal = root / ".summit-everything" / "transactions" / "mutation-corrupt.json"
    journal.write_text("not-json", encoding="utf-8")

    with pytest.raises(WorkspaceWriteConflict, match="transaction journal is invalid"):
        WorkspaceWriter().recover(root)


def test_conflicting_file_version_is_rejected_before_any_write(tmp_path: Path) -> None:
    root, _, _ = make_workspace(tmp_path / "workspace")
    first, second = root / "state" / "one.txt", root / "state" / "two.txt"
    first.parent.mkdir()
    first.write_bytes(b"external change")

    with pytest.raises(WorkspaceWriteConflict, match="changed since it was read"):
        WorkspaceWriter().apply(
            "operation-with-stale-input",
            root,
            {"state/one.txt": None, "state/two.txt": None},
            {"state/one.txt": b"overwrite", "state/two.txt": b"new"},
        )

    assert first.read_bytes() == b"external change"
    assert not second.exists()
