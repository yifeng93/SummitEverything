from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Event, Thread
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import ValidationError

from summit_everything.api.app import create_app
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeConflict, IntakeService
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.reader import list_pages
from summit_everything.workspace.writer import PageWriter


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


def test_source_with_pending_draft_is_not_pending_or_reorganized_again(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    item = intake.add_text(root, "单份来源。", filename="source.txt", operation_id="source")
    review = IntakeReviewService(FakeLLM())

    first_job = review.create_job(
        root,
        [item.item_id],
        operation_id="first-organize",
        line_id=line.id,
        project_id=project.id,
    )

    assert intake.list_items(root)[0].state == "reviewing"
    assert intake.list_items(root)[0].latest_job_id == first_job.job_id
    try:
        review.create_job(
            root,
            [item.item_id],
            operation_id="second-organize",
            line_id=line.id,
            project_id=project.id,
        )
    except ValueError as exc:
        assert "in progress" in str(exc).lower() or "review" in str(exc).lower()
    else:
        raise AssertionError("a source with an unreviewed draft created duplicate drafts")
    assert review.get_job(root, first_job.job_id).draft_ids == first_job.draft_ids
    assert len(review.list_drafts(root)) == 1

    draft = review.get_draft(root, first_job.draft_ids[0])
    review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=draft.version,
        confirmation_id="confirm-source",
        operation_id="write-source",
        conflict_resolutions={},
    )
    assert intake.list_items(root)[0].state == "completed"
    try:
        review.create_job(
            root,
            [item.item_id],
            operation_id="third-organize",
            line_id=line.id,
            project_id=project.id,
        )
    except ValueError as exc:
        assert "reprocess" in str(exc).lower() or "already" in str(exc).lower()
    else:
        raise AssertionError("a completed source was silently organized again")

    repeated = review.create_job(
        root,
        [item.item_id],
        operation_id="intentional-reprocess",
        line_id=line.id,
        project_id=project.id,
        reprocess=True,
    )
    assert repeated.state == "completed"
    assert intake.list_items(root)[0].state == "reviewing"
    assert intake.list_items(root)[0].latest_job_id == repeated.job_id


def test_failed_source_is_visible_and_retry_requires_explicit_reprocess(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    item = intake.add_text(root, "可重试来源。", filename="retry.txt", operation_id="retry-source")
    failing_review = IntakeReviewService(FakeLLM(scenario="timeout"))

    try:
        failing_review.create_job(
            root,
            [item.item_id],
            operation_id="failed-job",
            line_id=line.id,
            project_id=project.id,
        )
    except LLMProviderError:
        pass
    else:
        raise AssertionError("the configured provider failure was hidden")

    assert intake.list_items(root)[0].state == "failed"
    retry_review = IntakeReviewService(FakeLLM())
    try:
        retry_review.create_job(
            root,
            [item.item_id],
            operation_id="retry-without-confirmation",
            line_id=line.id,
            project_id=project.id,
        )
    except ValueError as exc:
        assert "reprocess" in str(exc).lower()
    else:
        raise AssertionError("a failed source was retried without an explicit reprocess choice")

    retried = retry_review.create_job(
        root,
        [item.item_id],
        operation_id="explicit-retry",
        line_id=line.id,
        project_id=project.id,
        reprocess=True,
    )
    assert retried.state == "completed"
    assert intake.list_items(root)[0].state == "reviewing"


def test_in_progress_source_cannot_start_a_second_job(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    item = intake.add_text(
        root, "正在整理的来源。", filename="active.txt", operation_id="active-source"
    )
    started = Event()
    release = Event()

    class BlockingProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            started.set()
            assert release.wait(timeout=5)
            return super().organize(inputs)

    review = IntakeReviewService(BlockingProvider())
    errors: list[BaseException] = []

    def organize_first() -> None:
        try:
            review.create_job(
                root,
                [item.item_id],
                operation_id="active-job",
                line_id=line.id,
                project_id=project.id,
            )
        except BaseException as exc:
            errors.append(exc)

    worker = Thread(target=organize_first)
    worker.start()
    assert started.wait(timeout=5)
    assert intake.list_items(root)[0].state == "processing"
    try:
        review.create_job(
            root,
            [item.item_id],
            operation_id="duplicate-active-job",
            line_id=line.id,
            project_id=project.id,
        )
    except ValueError as exc:
        assert "active" in str(exc).lower()
    else:
        raise AssertionError("an in-progress source accepted another organization job")
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert not errors
    assert intake.list_items(root)[0].state == "reviewing"


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
    confirmed_page = list_pages(root)[0]
    assert "## 冲突处理结果" in confirmed_page.body
    assert "状态是否已确认？" in confirmed_page.body
    assert "暂时未决" in confirmed_page.body

    selected_item = IntakeService().add_text(
        root, "另一条状态材料。", filename="selected.txt", operation_id="selected-source"
    )
    selected_review = IntakeReviewService(FakeLLM(scenario="conflict"))
    selected_job = selected_review.create_job(
        root,
        [selected_item.item_id],
        operation_id="organize-selected-conflict",
        line_id=line.id,
        project_id=project.id,
    )
    selected_draft = selected_review.get_draft(root, selected_job.draft_ids[0])
    selected_review.confirm_draft(
        root,
        selected_draft.draft_id,
        expected_version=selected_draft.version,
        confirmation_id="choose-confirmed",
        operation_id="write-confirmed-choice",
        conflict_resolutions={"status-conflict": "已确认"},
    )
    selected_page = next(
        page for page in list_pages(root) if page.page_id == selected_draft.draft_id
    )
    assert "用户选择采用：已确认" in selected_page.body


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


def test_review_can_update_an_authoritative_page_with_its_current_version(tmp_path: Path) -> None:
    from uuid import uuid4

    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    metadata = {
        "id": str(uuid4()),
        "title": "已确认事实",
        "role": "knowledge",
        "kind": "topic",
        "line_id": str(line.id),
        "project_id": str(project.id),
    }
    first = PageWriter().confirm(
        root,
        metadata=metadata,
        body="会议地点是旧馆。",
        confirmation_id="confirm-old",
        operation_id="write-old",
    )
    item = IntakeService().add_text(
        root, "会议地点已更新为新馆。", filename="update.txt", operation_id="update"
    )
    review = IntakeReviewService(FakeLLM())
    job = review.create_job(
        root,
        [item.item_id],
        operation_id="organize-update",
        line_id=line.id,
        project_id=project.id,
    )
    draft = review.get_draft(root, job.draft_ids[0])
    page = next(page for page in list_pages(root) if page.page_id == UUID(metadata["id"]))
    edited = review.edit_draft(
        root,
        draft.draft_id,
        expected_version=draft.version,
        title=draft.metadata["title"],
        body="会议地点已更新为新馆。",
        target_page_id=page.page_id,
        expected_base_sha256=page.content_sha256,
    )
    result = review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=edited.version,
        confirmation_id="confirm-update",
        operation_id="write-update",
        conflict_resolutions={},
    )
    pages = list_pages(root)
    updated = next(page for page in pages if page.page_id == UUID(metadata["id"]))
    assert result.page_versions[str(metadata["id"])] != first.page_versions[str(metadata["id"])]
    assert updated.body == "会议地点已更新为新馆。"
    assert len([page for page in pages if page.page_id == UUID(metadata["id"])]) == 1


def test_stale_review_target_can_be_rebased_only_after_explicit_conflict(tmp_path: Path) -> None:
    token = "stale-review-token"
    review = IntakeReviewService(FakeLLM())
    api = TestClient(
        create_app(
            session_token=token,
            profile_root=tmp_path / "profiles",
            review_service=review,
        )
    )
    api.headers.update({"Authorization": f"Bearer {token}"})
    root = tmp_path / "workspace"
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(root),
                "mode": "create",
                "name": "冲突模拟库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    page_id = "00000000-0000-4000-8000-000000000901"
    created = api.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": page_id,
                "title": "权威事实",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "合同金额是 123 元。",
            "confirmation_id": "confirm-original",
            "operation_id": "create-original",
        },
    )
    assert created.status_code == 201, created.text
    original = api.get(f"/api/v1/pages/{page_id}").json()
    item = api.post(
        "/api/v1/intake/items",
        json={"text": "合同金额更新为 456 元。", "filename": "update.txt", "operation_id": "input"},
    ).json()
    job = api.post(
        "/api/v1/intake/jobs",
        json={
            "item_ids": [item["item_id"]],
            "line_id": line["id"],
            "project_id": project["id"],
            "operation_id": "organize",
        },
    ).json()
    draft_id = job["draft_ids"][0]
    draft = api.get(f"/api/v1/drafts/{draft_id}").json()
    assert (
        api.patch(
            f"/api/v1/drafts/{draft_id}",
            json={
                "expected_version": draft["version"],
                "title": draft["metadata"]["title"],
                "body": "合同金额更新为 456 元。",
                "target_page_id": page_id,
                "expected_base_sha256": original["content_sha256"],
            },
        ).status_code
        == 200
    )
    page_path = root / original["relative_path"]
    external_text = page_path.read_text(encoding="utf-8").replace("123 元", "999 元")
    page_path.write_text(external_text, encoding="utf-8")
    current = api.get(f"/api/v1/pages/{page_id}").json()

    stale_edit = api.patch(
        f"/api/v1/drafts/{draft_id}",
        json={
            "expected_version": draft["version"] + 1,
            "title": "审核后的权威事实",
            "body": "合同金额更新为 456 元。",
            "target_page_id": page_id,
            "expected_base_sha256": original["content_sha256"],
        },
    )

    assert stale_edit.status_code == 409
    assert "页面已变化" in stale_edit.json()["error"]["message"]
    assert "999 元" in page_path.read_text(encoding="utf-8")
    assert api.get(f"/api/v1/drafts/{draft_id}").json()["state"] == "pending"

    rebased = api.patch(
        f"/api/v1/drafts/{draft_id}",
        json={
            "expected_version": draft["version"] + 1,
            "title": "审核后的权威事实",
            "body": "合同金额更新为 456 元。",
            "target_page_id": page_id,
            "expected_base_sha256": current["content_sha256"],
        },
    )
    assert rebased.status_code == 200, rebased.text
    confirmed = api.post(
        f"/api/v1/drafts/{draft_id}/confirmations",
        json={
            "expected_version": rebased.json()["version"],
            "confirmation_id": "confirm-after-rebase",
            "operation_id": "confirm-after-rebase",
            "conflict_resolutions": {},
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    final_page = api.get(f"/api/v1/pages/{page_id}").json()
    assert final_page["approval_state"] == "confirmed"
    assert final_page["body"] == "合同金额更新为 456 元。"


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
    assert item["state"] == "pending"
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
    assert api.get("/api/v1/intake/items").json()[0]["state"] == "reviewing"
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
    assert api.get("/api/v1/intake/items").json()[0]["state"] == "completed"
    duplicate = api.post(
        "/api/v1/intake/jobs",
        json={
            "item_ids": [item["item_id"]],
            "operation_id": "organize-again",
            "line_id": line["id"],
            "project_id": project["id"],
        },
    )
    assert duplicate.status_code == 422
    assert provider.calls == 1
    explicit_reprocess = api.post(
        "/api/v1/intake/jobs",
        json={
            "item_ids": [item["item_id"]],
            "operation_id": "explicit-reprocess",
            "line_id": line["id"],
            "project_id": project["id"],
            "reprocess": True,
        },
    )
    assert explicit_reprocess.status_code == 201, explicit_reprocess.text
    assert provider.calls == 2
    assert api.get("/api/v1/intake/items").json()[0]["state"] == "reviewing"
    pages = api.get("/api/v1/pages").json()
    assert len(pages) == 1
    assert sum(page["approval_state"] == "confirmed" for page in pages) == 1


def test_one_selected_project_can_receive_multiple_drafts_from_one_source(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    selected_project = create_project(root, line.id, "用户选定项目", "selected-project")
    other_project = create_project(root, line.id, "相似名称的其他项目", "other-project")
    intake = IntakeService()
    item = intake.add_text(
        root,
        "## 预算\n\n预算上限为 100 元。\n\n## 时间\n\n计划在周五完成。\n",
        filename="multi-topic.md",
        operation_id="multi-topic-source",
    )
    review = IntakeReviewService(FakeLLM())

    job = review.create_job(
        root,
        [item.item_id],
        operation_id="multi-topic-job",
        line_id=line.id,
        project_id=selected_project.id,
    )
    drafts = review.list_drafts(root, pending_only=True)

    assert job.state == "completed"
    assert len(job.draft_ids) == 2
    assert intake.list_items(root)[0].state == "reviewing"
    assert len(drafts) == 2
    assert all(draft.input_ids == [item.item_id] for draft in drafts)
    assert all(draft.source_ids == [item.source_id] for draft in drafts)
    assert all(draft.metadata["project_id"] == str(selected_project.id) for draft in drafts)
    assert all(draft.metadata["project_id"] != str(other_project.id) for draft in drafts)
    assert {draft.metadata["title"] for draft in drafts} == {"预算", "时间"}
    accepted = review.confirm_draft(
        root,
        drafts[0].draft_id,
        expected_version=1,
        confirmation_id="accept-one-topic",
        operation_id="accept-one-topic",
        conflict_resolutions={},
    )
    assert accepted.state == "succeeded"
    assert len(review.list_drafts(root, pending_only=True)) == 1
    assert intake.list_items(root)[0].state == "reviewing"
    remaining = review.list_drafts(root, pending_only=True)[0]
    review.confirm_draft(
        root,
        remaining.draft_id,
        expected_version=remaining.version,
        confirmation_id="confirm-second-topic",
        operation_id="confirm-second-topic",
        conflict_resolutions={},
    )
    assert intake.list_items(root)[0].state == "completed"
    assert not review.list_actions(root)
