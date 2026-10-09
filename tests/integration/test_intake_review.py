from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from summit_everything.api.app import create_app
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeConflict, IntakeService
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.workspace.manifest import create_line, create_project, create_workspace


def make_workspace(root: Path) -> Path:
    create_workspace(root, "模拟收件库", root.parent / "profiles", "create-intake-workspace")
    return root


def test_pasting_and_listing_intake_preserves_original_without_model_call(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path / "workspace")
    service = IntakeService()
    original = "合同进度：尚未签署。\r\n备注：等待确认。\n"

    item = service.add_text(root, original, filename="paste.txt", operation_id="paste-once")
    listed = service.list_items(root)
    raw_path = root / item.original_relative_path
    source_record = json.loads(
        (
            root / ".summit-everything" / "sources" / f"{item.created_at.strftime('%Y-%m')}.json"
        ).read_text(encoding="utf-8")
    )[0]

    assert item.state == "pending"
    assert listed == [item]
    assert raw_path.read_bytes() == original.encode("utf-8")
    assert source_record["sha256"] == hashlib.sha256(original.encode("utf-8")).hexdigest()
    assert not (root / ".summit-everything" / "drafts").exists()


def test_identical_intake_retry_reuses_item_and_source(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    service = IntakeService()
    original = "只保存，不整理。\n"

    first = service.add_text(root, original, filename="retry.txt", operation_id="same-input")
    retry = service.add_text(root, original, filename="retry.txt", operation_id="same-input")

    assert retry.item_id == first.item_id
    assert retry.source_id == first.source_id
    assert len(service.list_items(root)) == 1


def test_explicit_job_creates_reviewable_draft_and_partial_confirmation(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    first = intake.add_text(root, "事实甲", filename="a.txt", operation_id="a")
    second = intake.add_text(root, "事实乙", filename="b.txt", operation_id="b")
    provider = FakeLLM()
    review = IntakeReviewService(provider)

    job = review.create_job(
        root,
        [first.item_id, second.item_id],
        operation_id="organize-two",
        line_id=line.id,
        project_id=project.id,
    )
    drafts = review.list_drafts(root)

    assert job.state == "completed"
    assert len(drafts) == 2
    assert provider.calls == 1
    assert all("approval" not in draft.metadata for draft in drafts)
    assert all(draft.source_ids for draft in drafts)
    confirmed = review.confirm_draft(
        root,
        drafts[0].draft_id,
        expected_version=1,
        confirmation_id="yes-one",
        operation_id="confirm-one",
        conflict_resolutions={},
    )
    assert confirmed.state == "succeeded"
    assert len(review.list_drafts(root, pending_only=True)) == 1


def test_job_retry_rejects_changed_target_and_provider_schema_rejects_paths(
    tmp_path: Path,
) -> None:
    from summit_everything.integrations.llm import DraftProposal

    try:
        DraftProposal.model_validate(
            {
                "title": "Not allowed",
                "body": "Proposal",
                "kind": "topic",
                "approval": {"version": 1},
                "path": "/outside/workspace.md",
            }
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("provider schema accepted trust or path fields")
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    first_project = create_project(root, line.id, "项目甲", "project-a")
    second_project = create_project(root, line.id, "项目乙", "project-b")
    item = IntakeService().add_text(root, "事实", filename="x.txt", operation_id="x")
    review = IntakeReviewService(FakeLLM())
    review.create_job(
        root,
        [item.item_id],
        operation_id="same-job",
        line_id=line.id,
        project_id=first_project.id,
    )
    try:
        review.create_job(
            root,
            [item.item_id],
            operation_id="same-job",
            line_id=line.id,
            project_id=second_project.id,
        )
    except ValueError as exc:
        assert "different inputs" in str(exc)
    else:
        raise AssertionError("job intent changed its project on retry")


def test_important_conflict_blocks_confirmation_until_marked_unresolved(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(root, "状态待确认", filename="c.txt", operation_id="c")
    review = IntakeReviewService(FakeLLM(scenario="conflict"))
    job = review.create_job(
        root,
        [item.item_id],
        operation_id="organize-conflict",
        line_id=line.id,
        project_id=project.id,
    )
    draft = review.get_draft(root, job.draft_ids[0])
    try:
        review.confirm_draft(
            root,
            draft.draft_id,
            expected_version=draft.version,
            confirmation_id="yes-conflict",
            operation_id="confirm-conflict",
            conflict_resolutions={},
        )
    except ValueError as exc:
        assert "unresolved" in str(exc).lower()
    else:
        raise AssertionError("unresolved important conflict was confirmed")
    try:
        review.confirm_draft(
            root,
            draft.draft_id,
            expected_version=draft.version,
            confirmation_id="bad-choice",
            operation_id="confirm-bad-choice",
            conflict_resolutions={"status-conflict": "made-up-choice"},
        )
    except ValueError as exc:
        assert "alternatives" in str(exc).lower()
    else:
        raise AssertionError("a conflict choice not shown to the user was accepted")
    result = review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=draft.version,
        confirmation_id="yes-unresolved",
        operation_id="confirm-unresolved",
        conflict_resolutions={draft.important_conflicts[0]["id"]: "unresolved"},
    )
    assert result.state == "succeeded"


def test_bad_file_type_and_changed_retry_are_rejected(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    service = IntakeService()
    try:
        service.add_file(root, b"no", filename="payload.pdf", operation_id="pdf")
    except ValueError as exc:
        assert "TXT" in str(exc)
    else:
        raise AssertionError("unsupported file type was accepted")
    try:
        service.add_file(root, b"\xff", filename="invalid.txt", operation_id="invalid")
    except ValueError as exc:
        assert "UTF-8" in str(exc)
    else:
        raise AssertionError("non-UTF-8 source was accepted")
    service.add_text(root, "first", filename="x.txt", operation_id="retry")
    try:
        service.add_text(root, "different", filename="x.txt", operation_id="retry")
    except IntakeConflict:
        pass
    else:
        raise AssertionError("changed operation retry was accepted")


def test_fake_provider_timeout_is_visible_and_does_not_create_drafts(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(root, "事实", filename="x.txt", operation_id="x")
    review = IntakeReviewService(FakeLLM(scenario="timeout"))
    try:
        review.create_job(
            root,
            [item.item_id],
            operation_id="provider-timeout",
            line_id=line.id,
            project_id=project.id,
        )
    except LLMProviderError:
        pass
    else:
        raise AssertionError("provider timeout was hidden")
    assert review.list_drafts(root) == []


def test_action_suggestions_remain_local_candidates(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(root, "可能需要跟进", filename="todo.md", operation_id="todo")
    review = IntakeReviewService(FakeLLM(scenario="action"))
    job = review.create_job(
        root,
        [item.item_id],
        operation_id="organize-action",
        line_id=line.id,
        project_id=project.id,
    )
    actions = review.list_actions(root)
    assert job.state == "completed"
    assert len(actions) == 1
    assert actions[0].state == "proposed"
    assert not (root / ".summit-everything" / "executions").exists()


def test_authenticated_api_intake_file_job_and_review_flow(tmp_path: Path) -> None:
    token = "m1-acceptance-token"
    provider = FakeLLM()
    app = create_app(
        session_token=token,
        profile_root=tmp_path / "profiles",
        review_service=IntakeReviewService(provider),
    )
    api = TestClient(app)
    api.headers.update({"Authorization": f"Bearer {token}"})
    workspace = tmp_path / "workspace"
    created = api.post(
        "/api/v1/workspaces",
        json={
            "root": str(workspace),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "workspace",
        },
    )
    assert created.status_code == 201, created.text
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    original = b"Synthetic source\r\nsecond line\n"
    item_response = api.post(
        "/api/v1/intake/files",
        data={"operation_id": "source-file"},
        files={"file": ("synthetic.txt", original, "text/plain")},
    )
    assert item_response.status_code == 201, item_response.text
    item = item_response.json()
    assert (workspace / item["original_relative_path"]).read_bytes() == original
    assert len(api.get("/api/v1/intake/items").json()) == 1
    assert provider.calls == 0
    job_response = api.post(
        "/api/v1/intake/jobs",
        json={
            "item_ids": [item["item_id"]],
            "operation_id": "organize",
            "line_id": line["id"],
            "project_id": project["id"],
        },
    )
    assert job_response.status_code == 201, job_response.text
    assert provider.calls == 1
    draft_id = job_response.json()["draft_ids"][0]
    draft = api.get(f"/api/v1/drafts/{draft_id}").json()
    response = api.post(
        f"/api/v1/drafts/{draft_id}/confirmations",
        json={
            "expected_version": draft["version"],
            "confirmation_id": "approved-by-test-user",
            "operation_id": "confirm-test-draft",
            "conflict_resolutions": {},
        },
    )
    assert response.status_code == 200, response.text
    pages = api.get("/api/v1/pages").json()
    assert len(pages) == 1
    assert sum(page["approval_state"] == "confirmed" for page in pages) == 1
