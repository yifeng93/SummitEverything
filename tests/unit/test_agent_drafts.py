from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from summit_everything.domain.models import Draft, IntakeItem, LineRecord, ProjectRecord
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.workspace.manifest import (
    WorkspaceError,
    create_line,
    create_project,
    create_workspace,
)
from summit_everything.workspace.reader import read_page
from summit_everything.workspace.writer import PageWriter, WorkspaceWriteConflict


def _context(
    root: Path,
) -> tuple[Path, LineRecord, ProjectRecord, IntakeItem, UUID, IntakeReviewService]:
    create_workspace(root, "合成草稿库", root.parent / "profiles", "workspace-create")
    line = create_line(root, "主线 A", "line-a")
    project = create_project(root, line.id, "项目 A", "project-a")
    item = IntakeService().add_text(
        root, "未确认的原件内容。", filename="source.txt", operation_id="source"
    )
    review = IntakeReviewService()
    return root, line, project, item, uuid4(), review


def _create(
    review: IntakeReviewService,
    root: Path,
    line: LineRecord,
    project: ProjectRecord,
    item: IntakeItem,
    workspace_id: UUID,
    *,
    operation_id: str = "agent-draft",
    title: str = "拟议主题",
    body: str = "事实待确认。",
    target_page_id: UUID | None = None,
    expected_base_sha256: str | None = None,
) -> Draft:
    return review.create_agent_draft(
        root,
        operation_id=operation_id,
        item_ids=[item.item_id],
        line_id=line.id,
        project_id=project.id,
        title=title,
        kind="topic",
        body=body,
        target_page_id=target_page_id,
        expected_base_sha256=expected_base_sha256,
        workspace_id=workspace_id,
    )


def test_agent_draft_intent_recovers_without_overwriting_later_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, line, project, item, workspace_id, review = _context(tmp_path / "workspace")
    import summit_everything.intake.review as review_module

    original_atomic_write = review_module.atomic_write
    failed = False

    def crash_after_intent(path: Path, content: bytes) -> None:
        nonlocal failed
        if path.parent.name == "drafts" and not failed:
            failed = True
            raise OSError("simulated process interruption")
        original_atomic_write(path, content)

    monkeypatch.setattr(review_module, "atomic_write", crash_after_intent)
    with pytest.raises(OSError, match="simulated process interruption"):
        _create(review, root, line, project, item, workspace_id)
    assert IntakeService().list_items(root)[0].state == "reviewing"
    with pytest.raises(WorkspaceError):
        _create(
            review,
            root,
            line,
            project,
            item,
            workspace_id,
            operation_id="other-operation",
        )
    monkeypatch.setattr(review_module, "atomic_write", original_atomic_write)

    recovered = _create(review, root, line, project, item, workspace_id)
    assert recovered.version == 1 and recovered.body == "事实待确认。"
    edited = review.edit_draft(
        root, recovered.draft_id, expected_version=1, title="人工改稿", body="人工改过的内容。"
    )
    replay = _create(review, root, line, project, item, workspace_id)
    assert replay.draft_id == recovered.draft_id
    assert replay.version == edited.version and replay.body == edited.body
    assert item.item_id in replay.input_ids


def test_agent_draft_idempotency_binds_full_payload_and_confirmed_state(
    tmp_path: Path,
) -> None:
    root, line, project, item, workspace_id, review = _context(tmp_path / "workspace")
    draft = _create(review, root, line, project, item, workspace_id)
    assert IntakeService().list_items(root)[0].state == "reviewing"
    with pytest.raises(ValueError, match="different draft content"):
        _create(review, root, line, project, item, workspace_id, body="替换正文")
    result = review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=1,
        confirmation_id="explicit-user-confirmation",
        operation_id="user-confirm",
        conflict_resolutions={},
    )
    assert result.state == "succeeded"
    assert IntakeService().list_items(root)[0].state == "completed"
    replay = _create(review, root, line, project, item, workspace_id)
    assert replay.state == "confirmed"
    formal_page = read_page(root, draft.draft_id)
    assert formal_page.metadata.get("approval") is not None


def test_agent_draft_rejects_target_in_another_project_and_unpaired_base(
    tmp_path: Path,
) -> None:
    root, line, project, item, workspace_id, review = _context(tmp_path / "workspace")
    other_line = create_line(root, "主线 B", "line-b")
    other_project = create_project(root, other_line.id, "项目 B", "project-b")
    page_id = uuid4()
    page = PageWriter().confirm(
        root,
        metadata={
            "id": str(page_id),
            "role": "knowledge",
            "kind": "topic",
            "validity": "current",
            "title": "已有知识",
            "line_id": str(other_line.id),
            "project_id": str(other_project.id),
        },
        body="正式页面正文。",
        confirmation_id="user-confirmed-page",
        operation_id="page-create",
    )
    with pytest.raises(WorkspaceWriteConflict):
        _create(
            review,
            root,
            line,
            project,
            item,
            workspace_id,
            target_page_id=page_id,
            expected_base_sha256=page.page_versions[str(page_id)],
        )
    with pytest.raises(ValueError, match="paired"):
        _create(
            review,
            root,
            line,
            project,
            item,
            workspace_id,
            expected_base_sha256="a" * 64,
        )
