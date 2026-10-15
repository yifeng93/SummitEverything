from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread, current_thread
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from summit_everything.api.app import create_app
from summit_everything.domain.models import IntakeItem, IntakeJob
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
    assert source_record["origin_kind"] == item.origin_kind == "unknown"
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


def test_completed_item_archive_reprocesses_as_a_linked_attempt(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    item = intake.add_text(root, "可再次整理的来源。", filename="again.txt", operation_id="again")
    review = IntakeReviewService(FakeLLM())
    first = review.create_job(
        root, [item.item_id], operation_id="first-attempt", line_id=line.id, project_id=project.id
    )
    first_draft = review.get_draft(root, first.draft_ids[0])
    review.confirm_draft(
        root,
        first_draft.draft_id,
        expected_version=first_draft.version,
        confirmation_id="first-confirmation",
        operation_id="first-write",
        conflict_resolutions={},
    )
    items_root = root / ".summit-everything" / "intake" / "items"
    assert not (items_root / f"{item.item_id}.json").exists()
    current = intake.list_items(root)[0]
    assert current.state == "completed"
    first_archive = (
        root
        / ".summit-everything"
        / "archives"
        / "intake-items"
        / current.finished_at.strftime("%Y-%m")
        / "summary.json"
    )
    assert first_archive.exists()

    second = review.create_job(
        root,
        [item.item_id],
        operation_id="second-attempt",
        line_id=line.id,
        project_id=project.id,
        reprocess=True,
    )
    active = IntakeItem.model_validate_json((items_root / f"{item.item_id}.json").read_bytes())
    assert second.state == "completed"
    assert active.attempt_no == 1
    assert active.previous_attempt_sha256
    assert intake.list_items(root)[0].state == "reviewing"
    assert review.get_job(root, first.job_id).state == "completed"

    second_draft = review.get_draft(root, second.draft_ids[0])
    review.confirm_draft(
        root,
        second_draft.draft_id,
        expected_version=second_draft.version,
        confirmation_id="second-confirmation",
        operation_id="second-write",
        conflict_resolutions={},
    )
    assert not (items_root / f"{item.item_id}.json").exists()
    assert intake.list_items(root)[0].state == "completed"
    summary = json.loads(first_archive.read_text(encoding="utf-8"))
    assert set(summary["items"]) == {f"{item.item_id}@0", f"{item.item_id}@1"}


def test_legacy_undated_completed_item_is_preserved_before_first_reprocess(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(
        root, "legacy source", filename="legacy.txt", operation_id="legacy-item"
    )
    review = IntakeReviewService(FakeLLM())
    first = review.create_job(
        root, [item.item_id], operation_id="legacy-job-a", line_id=line.id, project_id=project.id
    )
    assert first.state == "completed"
    draft = review.get_draft(root, first.draft_ids[0])
    review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=draft.version,
        confirmation_id="legacy-confirm",
        operation_id="legacy-write",
        conflict_resolutions={},
    )

    item_path = root / ".summit-everything" / "intake" / "items" / f"{item.item_id}.json"
    summaries = list(
        (root / ".summit-everything" / "archives" / "intake-items").glob("*/summary.json")
    )
    legacy = None
    for summary_path in summaries:
        document = json.loads(summary_path.read_text(encoding="utf-8"))
        entry = document["items"].pop(f"{item.item_id}@0", None)
        if entry is not None:
            legacy = entry["value"]
            if document["items"]:
                summary_path.write_text(json.dumps(document), encoding="utf-8")
            else:
                summary_path.unlink()
            break
    assert legacy is not None
    legacy.pop("finished_at", None)
    legacy["finished_at"] = None
    item_path.parent.mkdir(parents=True, exist_ok=True)
    item_path.write_text(json.dumps(legacy), encoding="utf-8")
    legacy_hash = hashlib.sha256(
        json.dumps(legacy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    item_path.write_text(json.dumps(legacy), encoding="utf-8")

    second = review.create_job(
        root,
        [item.item_id],
        operation_id="legacy-job-b",
        line_id=line.id,
        project_id=project.id,
        reprocess=True,
    )
    bucket = json.loads(
        (
            root / ".summit-everything" / "archives" / "intake-items" / "undated" / "summary.json"
        ).read_text(encoding="utf-8")
    )
    current = IntakeService().list_items(root)[0]
    assert second.state == "completed"
    assert bucket["items"][f"{item.item_id}@0"]["value"] == legacy
    assert current.attempt_no == 1
    assert current.previous_attempt_sha256 == legacy_hash
    assert review.get_job(root, first.job_id).job_id == first.job_id


def test_completed_intake_bulk_monthly_file_counts_keep_originals_and_drafts(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    review = IntakeReviewService(FakeLLM())
    items = []
    for index in range(8):
        item = intake.add_text(
            root,
            f"source body {index}",
            filename=f"source-{index}.txt",
            operation_id=f"bulk-source-{index}",
        )
        items.append(item)
        job = review.create_job(
            root,
            [item.item_id],
            operation_id=f"bulk-job-{index}",
            line_id=line.id,
            project_id=project.id,
        )
        draft = review.get_draft(root, job.draft_ids[0])
        review.confirm_draft(
            root,
            draft.draft_id,
            expected_version=draft.version,
            confirmation_id=f"bulk-confirm-{index}",
            operation_id=f"bulk-write-{index}",
            conflict_resolutions={},
        )

    state = root / ".summit-everything"
    assert list((state / "intake" / "items").glob("*.json")) == []
    assert list((state / "intake" / "jobs").glob("*.json")) == []
    archives = state / "archives"
    month = items[0].created_at.strftime("%Y-%m")
    item_summary = json.loads(
        (archives / "intake-items" / month / "summary.json").read_text(encoding="utf-8")
    )
    job_summary = json.loads(
        (archives / "intake-jobs" / month / "summary.json").read_text(encoding="utf-8")
    )
    transaction_summary = json.loads(
        (archives / "transactions" / month / "summary.json").read_text(encoding="utf-8")
    )
    assert len(item_summary["items"]) == 8
    assert len(job_summary["items"]) == 8
    assert len(transaction_summary["items"]) >= 16
    assert len(list((root / "原件" / month).glob("*.txt"))) == 8
    draft_paths = list((state / "drafts").glob("*.json"))
    assert len(draft_paths) == 8
    assert all(json.loads(path.read_text(encoding="utf-8"))["body"] for path in draft_paths)
    assert len(list((state / "intake" / "checkpoints").glob("*.json"))) == 0


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


def test_refresh_rechecks_item_under_lock_before_writing_derived_state(
    tmp_path: Path, monkeypatch
) -> None:
    from summit_everything.intake import sources as sources_module

    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(
        root, "race source", filename="race.txt", operation_id="race-source"
    )
    first = IntakeReviewService(FakeLLM()).create_job(
        root, [item.item_id], operation_id="race-job-a", line_id=line.id, project_id=project.id
    )
    assert first.state == "completed"
    item_path = root / ".summit-everything" / "intake" / "items" / f"{item.item_id}.json"
    first_review = IntakeReviewService(FakeLLM())
    draft = first_review.get_draft(root, first.draft_ids[0])
    first_review.confirm_draft(
        root,
        draft.draft_id,
        expected_version=draft.version,
        confirmation_id="race-confirm-a",
        operation_id="race-write-a",
        conflict_resolutions={},
    )
    stale = IntakeService().list_items(root)[0].model_dump(mode="json")
    archive_root = root / ".summit-everything" / "archives" / "intake-items"
    for summary_path in archive_root.glob("*/summary.json"):
        document = json.loads(summary_path.read_text(encoding="utf-8"))
        if document["items"].pop(f"{item.item_id}@0", None) is not None:
            if document["items"]:
                summary_path.write_text(json.dumps(document), encoding="utf-8")
            else:
                summary_path.unlink()
            break
    stale.update({"state": "failed", "finished_at": None})
    item_path.parent.mkdir(parents=True, exist_ok=True)
    item_path.write_text(json.dumps(stale), encoding="utf-8")

    snapshotted = Event()
    continue_refresh = Event()
    original_read = sources_module.read_shared_items

    def paused_read(path: Path, *, archive: bool = True):  # type: ignore[no-untyped-def]
        values = original_read(path, archive=archive)
        if current_thread().name == "stale-refresh":
            snapshotted.set()
            assert continue_refresh.wait(timeout=5)
        return values

    monkeypatch.setattr(sources_module, "read_shared_items", paused_read)
    refresh = Thread(
        name="stale-refresh", target=lambda: sources_module.SourceStore().refresh_items(root)
    )
    refresh.start()
    assert snapshotted.wait(timeout=5)

    provider_started = Event()
    release_provider = Event()

    class BlockingProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            provider_started.set()
            assert release_provider.wait(timeout=5)
            return super().organize(inputs)

    review = IntakeReviewService(BlockingProvider())
    job_errors: list[BaseException] = []

    def reprocess() -> None:
        try:
            review.create_job(
                root,
                [item.item_id],
                operation_id="race-job-b",
                line_id=line.id,
                project_id=project.id,
                reprocess=True,
            )
        except BaseException as exc:
            job_errors.append(exc)

    worker = Thread(target=reprocess)
    worker.start()
    # With the lock-safe implementation this waits behind refresh; the old
    # unlocked snapshot allowed the new attempt to enter its provider here.
    entered_before_refresh = provider_started.wait(timeout=0.1)
    continue_refresh.set()
    if not entered_before_refresh:
        assert provider_started.wait(timeout=5), repr(job_errors)
    release_provider.set()
    refresh.join(timeout=5)
    worker.join(timeout=5)
    assert not refresh.is_alive() and not worker.is_alive()
    assert not job_errors
    current = IntakeService().list_items(root)[0]
    assert current.attempt_no == 1
    assert current.latest_job_id != first.job_id


def test_same_host_profile_reads_live_attempt_without_marking_unknown(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(
        root, "并行 profile 的来源。", filename="shared.txt", operation_id="shared"
    )
    started = Event()
    release = Event()

    class BlockingProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            started.set()
            assert release.wait(timeout=5)
            return super().organize(inputs)

    provider = BlockingProvider()
    first_profile = IntakeReviewService(provider)
    second_profile = IntakeReviewService(provider)
    result: list[object] = []
    worker = Thread(
        target=lambda: result.append(
            first_profile.create_job(
                root,
                [item.item_id],
                operation_id="shared-job",
                line_id=line.id,
                project_id=project.id,
            )
        )
    )
    worker.start()
    assert started.wait(timeout=5)
    job_id = next(
        UUID(path.stem) for path in (root / ".summit-everything/intake/jobs").glob("*.json")
    )
    in_progress = second_profile.get_job(root, job_id)
    assert in_progress.state == "provider_calling"
    assert IntakeService().list_items(root)[0].state == "processing"
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert provider.calls == 1
    assert not isinstance(result[0], BaseException)


def test_cancelled_job_rejects_late_provider_result(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(
        root, "取消后不得覆盖。", filename="cancel.txt", operation_id="cancel"
    )
    started = Event()
    release = Event()

    class BlockingProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            started.set()
            assert release.wait(timeout=5)
            return super().organize(inputs)

    provider = BlockingProvider()
    review = IntakeReviewService(provider)
    errors: list[BaseException] = []

    def organize() -> None:
        try:
            review.create_job(
                root,
                [item.item_id],
                operation_id="cancel-job",
                line_id=line.id,
                project_id=project.id,
            )
        except BaseException as exc:
            errors.append(exc)

    worker = Thread(target=organize)
    worker.start()
    assert started.wait(timeout=5)
    job_id = next(
        UUID(path.stem) for path in (root / ".summit-everything/intake/jobs").glob("*.json")
    )
    assert review.cancel_job(root, job_id).state == "cancelled"
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert not errors
    assert provider.calls == 1
    assert review.get_job(root, job_id).state == "cancelled"
    assert review.list_drafts(root) == []
    assert IntakeService().list_items(root)[0].state == "cancelled"


def test_provider_checkpoint_recovers_local_draft_without_second_call(
    tmp_path: Path, monkeypatch
) -> None:
    import summit_everything.intake.review as review_module

    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    intake = IntakeService()
    first = intake.add_text(
        root, "checkpoint 原文甲。", filename="checkpoint-a.txt", operation_id="checkpoint-a"
    )
    second = intake.add_text(
        root, "checkpoint 原文乙。", filename="checkpoint-b.txt", operation_id="checkpoint-b"
    )
    provider = FakeLLM()
    review = IntakeReviewService(provider)
    original_write = review_module.atomic_write
    draft_writes = 0

    def fail_first_draft(path: Path, content: bytes) -> None:
        nonlocal draft_writes
        if "/drafts/" in str(path):
            draft_writes += 1
            if draft_writes == 2:
                raise OSError("simulated local draft interruption")
        original_write(path, content)

    monkeypatch.setattr(review_module, "atomic_write", fail_first_draft)
    try:
        review.create_job(
            root,
            [first.item_id, second.item_id],
            operation_id="checkpoint-job",
            line_id=line.id,
            project_id=project.id,
        )
    except OSError:
        pass
    else:
        raise AssertionError("the local interruption was not injected")
    monkeypatch.setattr(review_module, "atomic_write", original_write)
    assert review.list_drafts(root, pending_only=True) == []

    job_id = next(
        UUID(path.stem) for path in (root / ".summit-everything/intake/jobs").glob("*.json")
    )
    recovered = review.get_job(root, job_id)
    assert recovered.state == "completed"
    assert provider.calls == 1
    assert len(review.list_drafts(root, pending_only=True)) == 2
    assert list_pages(root) == []


def test_dead_provider_attempt_becomes_unknown_and_is_never_resent(tmp_path: Path) -> None:
    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    item = IntakeService().add_text(
        root, "结果未知来源。", filename="unknown.txt", operation_id="unknown"
    )

    class ProcessExitProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            self.calls += 1
            raise SystemExit("simulated worker exit")

    provider = ProcessExitProvider()
    review = IntakeReviewService(provider)
    errors: list[BaseException] = []

    def organize() -> None:
        try:
            review.create_job(
                root,
                [item.item_id],
                operation_id="lost-job",
                line_id=line.id,
                project_id=project.id,
            )
        except BaseException as exc:
            errors.append(exc)

    worker = Thread(target=organize)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert isinstance(errors[0], SystemExit)
    job_id = next(
        UUID(path.stem) for path in (root / ".summit-everything/intake/jobs").glob("*.json")
    )

    first_read = review.get_job(root, job_id)
    second_read = review.get_job(root, job_id)
    assert first_read.state == second_read.state == "unknown"
    assert provider.calls == 1
    assert IntakeService().list_items(root)[0].state == "unknown"
    assert review.list_drafts(root) == []


def test_intake_list_recovers_dead_attempt_status_without_resending_provider(
    tmp_path: Path,
) -> None:
    token = "dead-attempt-api-token"

    provider = FakeLLM()
    review = IntakeReviewService(provider)
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
                "name": "本地状态恢复",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    item = api.post(
        "/api/v1/intake/items",
        json={"text": "原文", "filename": "source.txt", "operation_id": "source"},
    ).json()
    job_id, attempt_id = uuid4(), uuid4()
    job = IntakeJob(
        job_id=job_id,
        item_ids=[UUID(item["item_id"])],
        line_id=UUID(line["id"]),
        project_id=UUID(project["id"]),
        request_hash="a" * 64,
        state="provider_calling",
        created_at=datetime.now(UTC),
        attempt_id=str(attempt_id),
        revision=1,
    )
    job_root = root / ".summit-everything" / "intake" / "jobs"
    job_root.mkdir(parents=True, exist_ok=True)
    (job_root / f"{job_id}.json").write_text(job.model_dump_json())
    item_path = root / ".summit-everything" / "intake" / "items" / f"{item['item_id']}.json"
    stale_item = IntakeItem.model_validate_json(item_path.read_bytes()).model_copy(
        update={"state": "processing", "latest_job_id": job_id}
    )
    item_path.write_text(stale_item.model_dump_json())

    rows = api.get("/api/v1/intake/items").json()
    assert rows[0]["state"] == "unknown"
    job = api.get(f"/api/v1/jobs/{rows[0]['latest_job_id']}").json()
    assert job["state"] == "unknown"
    assert api.get("/api/v1/drafts").json() == []
    assert provider.calls == 0


def test_running_idempotent_job_returns_accepted_with_location(tmp_path: Path) -> None:
    token = "running-job-api-token"
    provider_started = Event()
    release = Event()

    class BlockingProvider(FakeLLM):
        def organize(self, inputs):  # type: ignore[no-untyped-def]
            provider_started.set()
            assert release.wait(timeout=5)
            return super().organize(inputs)

    api = TestClient(
        create_app(
            session_token=token,
            profile_root=tmp_path / "profiles",
            review_service=IntakeReviewService(BlockingProvider()),
        )
    )
    api.headers.update({"Authorization": f"Bearer {token}"})
    root = tmp_path / "workspace"
    assert (
        api.post(
            "/api/v1/workspaces",
            json={"root": str(root), "mode": "create", "name": "并发收件", "operation_id": "open"},
        ).status_code
        == 201
    )
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    item = api.post(
        "/api/v1/intake/items",
        json={"text": "原文", "filename": "source.txt", "operation_id": "source"},
    ).json()
    request = {
        "item_ids": [item["item_id"]],
        "line_id": line["id"],
        "project_id": project["id"],
        "operation_id": "same-operation",
    }
    first_result: list[Any] = []
    first_error: list[BaseException] = []

    def submit_first() -> None:
        try:
            first_result.append(api.post("/api/v1/intake/jobs", json=request))
        except BaseException as exc:
            first_error.append(exc)

    worker = Thread(target=submit_first)
    worker.start()
    assert provider_started.wait(timeout=5)
    duplicate = api.post("/api/v1/intake/jobs", json=request)
    release.set()
    worker.join(timeout=5)
    assert not worker.is_alive() and not first_error
    assert duplicate.status_code == 202
    assert duplicate.headers["Location"] == f"/api/v1/jobs/{duplicate.json()['job_id']}"
    assert first_result[0].status_code == 201


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
    assert item["origin_kind"] == "file"
    assert (workspace / item["original_relative_path"]).read_bytes() == original
    source_record = api.get(f"/api/v1/sources/{item['source_id']}").json()["source"]
    assert source_record["origin_kind"] == "file"
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


def test_job_start_directory_failure_releases_attempt_lease_without_gc(
    tmp_path: Path, monkeypatch
) -> None:
    import pytest

    root = make_workspace(tmp_path / "workspace")
    line = create_line(root, "模拟主线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    provider = FakeLLM()
    item = IntakeService().add_text(
        root, "保留原件。", filename="source.txt", operation_id="source"
    )
    jobs_root = root / ".summit-everything" / "intake" / "jobs"
    assert not jobs_root.exists()
    real_mkdir = Path.mkdir

    def fail_job_directory(path, *args, **kwargs):
        if path == jobs_root:
            raise OSError("synthetic jobs directory failure")
        return real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_job_directory)
    with pytest.raises(OSError, match="synthetic jobs directory failure") as raised:
        IntakeReviewService(provider).create_job(
            root,
            [item.item_id],
            operation_id="job-directory-failure",
            line_id=line.id,
            project_id=project.id,
        )

    # The held traceback retains create_job locals, so cleanup must be explicit.
    assert raised.value is not None
    lease_root = root / ".summit-everything" / "attempt-leases"
    assert list(lease_root.glob("*.lock")) == []
    assert IntakeService().list_items(root)[0].state == "pending"
    assert not jobs_root.exists()
    assert provider.calls == 0


def test_text_intake_route_records_quick_note_without_client_selected_kind(tmp_path: Path) -> None:
    token = "m1-quick-note-token"
    app = create_app(session_token=token, profile_root=tmp_path / "profiles")
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
    response = api.post(
        "/api/v1/intake/items",
        json={"text": "一句合成记录", "filename": "arbitrary.txt", "operation_id": "note"},
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["origin_kind"] == "quick_note"
    source = api.get(f"/api/v1/sources/{item['source_id']}").json()["source"]
    assert source["origin_kind"] == "quick_note"
    assert (workspace / item["original_relative_path"]).read_bytes() == "一句合成记录".encode()


def test_legacy_intake_replay_stays_unknown_when_route_now_tags_it(
    tmp_path: Path,
) -> None:
    root = make_workspace(tmp_path / "workspace")
    service = IntakeService()
    original = b"legacy receipt bytes"
    legacy = service.add_file(root, original, filename="same.txt", operation_id="legacy-op")

    replay = service.source_store.capture(
        root, original, "same.txt", "legacy-op", origin_kind="file"
    )

    assert replay.item_id == legacy.item_id
    assert replay.origin_kind == "unknown"
    source = json.loads(
        (
            root
            / ".summit-everything"
            / "sources"
            / f"{legacy.created_at.strftime('%Y-%m')}.json"
        ).read_text(encoding="utf-8")
    )[0]
    assert source["origin_kind"] == "unknown"
