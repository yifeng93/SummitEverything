"""Explicit source-to-draft workflow; only user-confirmed drafts reach PageWriter."""

from __future__ import annotations

import fcntl
import hashlib
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4, uuid5

from summit_everything.domain.models import (
    ActionCandidate,
    Draft,
    IntakeJob,
    MutationResult,
)
from summit_everything.intake.sources import SourceStore
from summit_everything.integrations.llm import DraftProposal, FakeLLM, LLMProviderError
from summit_everything.workspace.archives import (
    archive_completed_transactions,
)
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.reader import read_page
from summit_everything.workspace.state import (
    AttemptLease,
    archive_intake,
    attempt_is_live,
    preserve_undated_item,
)
from summit_everything.workspace.state import (
    get_job as read_job,
)
from summit_everything.workspace.state import (
    list_items as read_items,
)
from summit_everything.workspace.transactions import atomic_write, workspace_lock
from summit_everything.workspace.writer import PageWriter, WorkspaceWriteConflict


class OrganizeProvider(Protocol):
    def organize(self, inputs: list[tuple[UUID, UUID, str]]) -> list[DraftProposal]: ...


def _state_root(root: Path) -> Path:
    return root / ".summit-everything"


def _conflict_outcome_body(draft: Draft, resolutions: dict[str, str]) -> str:
    if not draft.important_conflicts:
        return draft.body

    def plain_text(value: str) -> str:
        return " ".join(value.replace("`", "'").split())

    lines = ["## 冲突处理结果"]
    for conflict in draft.important_conflicts:
        question = plain_text(str(conflict["question"]))
        choice = resolutions[str(conflict["id"])]
        if choice == "unresolved":
            alternatives = "；".join(plain_text(str(value)) for value in conflict["alternatives"])
            lines.append(f"- {question}：暂时未决，尚未作为确定事实；可选依据：{alternatives}。")
        else:
            lines.append(f"- {question}：用户选择采用：{plain_text(choice)}。")
    return f"{draft.body.rstrip()}\n\n" + "\n".join(lines) + "\n"


@contextmanager
def _draft_lock(root: Path, draft_id: UUID) -> Iterator[None]:
    lock_path = _state_root(root) / "transactions" / f"draft-{draft_id}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class IntakeReviewService:
    def __init__(
        self, provider: OrganizeProvider | None = None, page_writer: PageWriter | None = None
    ) -> None:
        self.provider = provider or FakeLLM()
        self.page_writer = page_writer or PageWriter()

    def preview_inputs(
        self,
        root: Path,
        item_ids: list[UUID],
        *,
        line_id: UUID,
        project_id: UUID,
        reprocess: bool = False,
    ) -> list[tuple[UUID, UUID, str]]:
        """Read the exact UTF-8 bodies that organize() would send, without mutation."""
        root = root.resolve()
        if not item_ids or len(set(item_ids)) != len(item_ids):
            raise WorkspaceError("Choose one or more distinct intake items")
        manifest = load_manifest(root)
        project = next((record for record in manifest.projects if record.id == project_id), None)
        if project is None or project.line_id != line_id or project.archived:
            raise WorkspaceError("Choose an active project in the selected line")
        with workspace_lock(root):
            items = {item.item_id: item for item in read_items(root, archive=False)}
            selected = [items.get(item_id) for item_id in item_ids]
            if any(item is None for item in selected):
                raise WorkspaceError("Every selected intake item must exist")
            result: list[tuple[UUID, UUID, str]] = []
            source_store = SourceStore()
            for item in selected:
                assert item is not None
                state = source_store.derived_state(root, item)
                if state in {"processing", "reviewing"}:
                    raise WorkspaceError(
                        "This source already has an active job or drafts awaiting review"
                    )
                if (state != "pending" or item.latest_job_id is not None) and not reprocess:
                    raise WorkspaceError(
                        "This source was already processed; explicitly choose reprocess"
                    )
                source_path = (root / item.original_relative_path).resolve()
                if not source_path.is_relative_to(root) or not source_path.is_file():
                    raise WorkspaceError("An intake original is missing or outside the workspace")
                source_bytes = source_path.read_bytes()
                source_id, source_digest = self._source_identity(root, item.source_id)
                if (
                    source_id != item.source_id
                    or hashlib.sha256(source_bytes).hexdigest() != source_digest
                ):
                    raise WorkspaceError("An intake original no longer matches its source record")
                try:
                    text = source_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WorkspaceError("Only UTF-8 text sources can be organized") from exc
                result.append((item.item_id, item.source_id, text))
            return result

    def replay_job(
        self,
        root: Path,
        *,
        item_ids: list[UUID],
        operation_id: str,
        line_id: UUID,
        project_id: UUID,
        reprocess: bool = False,
    ) -> IntakeJob | None:
        manifest = load_manifest(root)
        job_id = uuid5(manifest.workspace_id, f"intake-job:{operation_id}")
        existing = read_job(root, job_id)
        if existing is None:
            return None
        request: dict[str, object] = {
            "item_ids": [str(item_id) for item_id in item_ids],
            "line_id": str(line_id),
            "project_id": str(project_id),
        }
        if reprocess:
            request["reprocess"] = True
        request_hash = hashlib.sha256(
            json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if existing.request_hash != request_hash:
            raise WorkspaceWriteConflict("Job operation ID was reused for different inputs")
        return existing

    def create_job(
        self,
        root: Path,
        item_ids: list[UUID],
        *,
        operation_id: str,
        line_id: UUID,
        project_id: UUID,
        reprocess: bool = False,
        before_provider_call: Callable[[list[tuple[UUID, UUID, str]]], None] | None = None,
    ) -> IntakeJob:
        root = root.resolve()
        if not operation_id.strip() or not item_ids or len(set(item_ids)) != len(item_ids):
            raise WorkspaceError("Choose one or more distinct intake items")
        manifest = load_manifest(root)
        project = next((record for record in manifest.projects if record.id == project_id), None)
        if project is None or project.line_id != line_id or project.archived:
            raise WorkspaceError("Choose an active project in the selected line")
        job_id = uuid5(manifest.workspace_id, f"intake-job:{operation_id}")
        request: dict[str, object] = {
            "item_ids": [str(item_id) for item_id in item_ids],
            "line_id": str(line_id),
            "project_id": str(project_id),
        }
        if reprocess:
            request["reprocess"] = True
        request_hash = hashlib.sha256(
            json.dumps(
                request,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        existing = read_job(root, job_id)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise WorkspaceWriteConflict("Job operation ID was reused for different inputs")
            return existing
        jobs_root = _state_root(root) / "intake" / "jobs"
        job_path = jobs_root / f"{job_id}.json"
        archive_intake(root)
        archive_completed_transactions(root)
        with workspace_lock(root):
            prior = read_job(root, job_id)
            if prior is not None:
                if prior.request_hash != request_hash:
                    raise WorkspaceWriteConflict("Job operation ID was reused for different inputs")
                return prior
            items = {item.item_id: item for item in read_items(root, archive=False)}
            selected = [items.get(item_id) for item_id in item_ids]
            if any(item is None for item in selected):
                raise WorkspaceError("Every selected intake item must exist")
            source_store = SourceStore()
            for item in selected:
                assert item is not None
                state = source_store.derived_state(root, item)
                if state in {"processing", "reviewing"}:
                    raise WorkspaceError(
                        "This source already has an active job or drafts awaiting review"
                    )
                if (state != "pending" or item.latest_job_id is not None) and not reprocess:
                    raise WorkspaceError(
                        "This source was already processed; explicitly choose reprocess "
                        "to organize it again"
                    )
            inputs: list[tuple[UUID, UUID, str]] = []
            for item in selected:
                assert item is not None
                source_path = (root / item.original_relative_path).resolve()
                if not source_path.is_relative_to(root) or not source_path.is_file():
                    raise WorkspaceError("An intake original is missing or outside the workspace")
                source_bytes = source_path.read_bytes()
                source_id, source_digest = self._source_identity(root, item.source_id)
                if (
                    source_id != item.source_id
                    or hashlib.sha256(source_bytes).hexdigest() != source_digest
                ):
                    raise WorkspaceError("An intake original no longer matches its source record")
                try:
                    text = source_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WorkspaceError("Only UTF-8 text sources can be organized") from exc
                inputs.append((item.item_id, item.source_id, text))
            attempt_id = str(uuid4())
            job = IntakeJob(
                job_id=job_id,
                item_ids=item_ids,
                line_id=line_id,
                project_id=project_id,
                request_hash=request_hash,
                state="running",
                attempt_id=attempt_id,
                created_at=datetime.now(UTC),
            )
            lease = AttemptLease(root, attempt_id)
            if not lease.acquire(blocking=False):
                raise WorkspaceError("A job attempt with this identity is already active", 409)
            try:
                jobs_root.mkdir(parents=True, exist_ok=True)
                atomic_write(job_path, job.model_dump_json(indent=2).encode())
                for item in selected:
                    assert item is not None
                    item_path = _state_root(root) / "intake" / "items" / f"{item.item_id}.json"
                    attempt_no = item.attempt_no
                    parent_hash = item.previous_attempt_sha256
                    if item.latest_job_id is not None or item.state != "pending":
                        if item.finished_at is None and item.state in {
                            "completed",
                            "failed",
                            "cancelled",
                        }:
                            preserve_undated_item(root, item)
                        parent_hash = hashlib.sha256(
                            json.dumps(
                                item.model_dump(mode="json"),
                                sort_keys=True,
                                separators=(",", ":"),
                                ensure_ascii=False,
                            ).encode()
                        ).hexdigest()
                        attempt_no += 1
                    updated = item.model_copy(
                        update={
                            "state": "processing",
                            "latest_job_id": job_id,
                            "attempt_no": attempt_no,
                            "revision": item.revision + 1,
                            "previous_attempt_sha256": parent_hash,
                            "finished_at": None,
                        }
                    )
                    atomic_write(item_path, updated.model_dump_json(indent=2).encode())
            except BaseException:
                lease.__exit__(None, None, None)
                raise
        return self._run_attempt(
            root, job, inputs, line_id, project_id, lease, before_provider_call
        )

    def _run_attempt(
        self,
        root: Path,
        job: IntakeJob,
        inputs: list[tuple[UUID, UUID, str]],
        line_id: UUID,
        project_id: UUID,
        lease: AttemptLease,
        before_provider_call: Callable[[list[tuple[UUID, UUID, str]]], None] | None = None,
    ) -> IntakeJob:
        assert job.attempt_id is not None
        checkpoint_path = _state_root(root) / "intake" / "checkpoints" / f"{job.job_id}.json"
        checkpoint_written = False
        with lease:
            with workspace_lock(root):
                current = read_job(root, job.job_id)
                if (
                    current is None
                    or current.state not in {"running", "provider_calling"}
                    or current.attempt_id != job.attempt_id
                    or current.revision != job.revision
                ):
                    return current or job
                calling = current.model_copy(
                    update={"state": "provider_calling", "revision": current.revision + 1}
                )
                atomic_write(
                    _state_root(root) / "intake" / "jobs" / f"{job.job_id}.json",
                    calling.model_dump_json(indent=2).encode(),
                )
            try:
                if before_provider_call is not None:
                    before_provider_call(inputs)
                proposals = self.provider.organize(inputs)
                covered_inputs: set[int] = set()
                for proposal in proposals:
                    if not proposal.input_indexes or len(set(proposal.input_indexes)) != len(
                        proposal.input_indexes
                    ):
                        raise LLMProviderError("Every proposal must identify its source inputs")
                    if any(index < 0 or index >= len(inputs) for index in proposal.input_indexes):
                        raise LLMProviderError("Provider returned an unknown source input")
                    covered_inputs.update(proposal.input_indexes)
                if covered_inputs != set(range(len(inputs))):
                    raise LLMProviderError("Every selected input must appear in a proposal")
                checkpoint = {
                    "schema": "intake-provider-checkpoint-v1",
                    "job_id": str(job.job_id),
                    "attempt_id": job.attempt_id,
                    "request_hash": job.request_hash,
                    "input_hashes": {
                        str(item_id): hashlib.sha256(text.encode("utf-8")).hexdigest()
                        for item_id, _source_id, text in inputs
                    },
                    "proposals": [proposal.model_dump(mode="json") for proposal in proposals],
                }
                payload_bytes = json.dumps(
                    checkpoint, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
                checkpoint_hash = hashlib.sha256(payload_bytes).hexdigest()
                checkpoint_document = {**checkpoint, "checkpoint_sha256": checkpoint_hash}
                checkpoint_bytes = json.dumps(
                    checkpoint_document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
                with workspace_lock(root):
                    current = read_job(root, job.job_id)
                    if (
                        current is None
                        or current.state != "provider_calling"
                        or current.attempt_id != job.attempt_id
                        or current.revision != job.revision + 1
                    ):
                        return current or job
                    atomic_write(checkpoint_path, checkpoint_bytes)
                    checkpoint_written = True
                    completed = self._apply_checkpoint(
                        root,
                        current,
                        checkpoint,
                        checkpoint_hash,
                        line_id,
                        project_id,
                        inputs,
                    )
                SourceStore().refresh_items(root, job.item_ids)
                archive_intake(root)
                archive_completed_transactions(root)
                return completed
            except Exception as exc:
                if checkpoint_written:
                    raise
                with workspace_lock(root):
                    current = read_job(root, job.job_id)
                    if (
                        current is not None
                        and current.state == "provider_calling"
                        and current.attempt_id == job.attempt_id
                    ):
                        failed = current.model_copy(
                            update={
                                "state": "failed",
                                "error": str(exc)[:500],
                                "finished_at": datetime.now(UTC),
                                "revision": current.revision + 1,
                            }
                        )
                        atomic_write(
                            _state_root(root) / "intake" / "jobs" / f"{job.job_id}.json",
                            failed.model_dump_json(indent=2).encode(),
                        )
                SourceStore().refresh_items(root, job.item_ids)
                archive_intake(root)
                raise

    def _apply_checkpoint(
        self,
        root: Path,
        job: IntakeJob,
        checkpoint: dict[str, Any],
        checkpoint_hash: str,
        line_id: UUID,
        project_id: UUID,
        inputs: list[tuple[UUID, UUID, str]],
    ) -> IntakeJob:
        proposals = [DraftProposal.model_validate(row) for row in checkpoint["proposals"]]
        drafts: list[Draft] = []
        actions: list[ActionCandidate] = []
        for index, proposal in enumerate(proposals):
            proposal_inputs = [inputs[source_index] for source_index in proposal.input_indexes]
            draft_id = uuid5(job.job_id, f"draft:{index}")
            metadata = {
                "id": str(draft_id),
                "title": proposal.title,
                "role": "knowledge",
                "kind": proposal.kind,
                "line_id": str(line_id),
                "project_id": str(project_id),
            }
            draft = Draft(
                draft_id=draft_id,
                job_id=job.job_id,
                input_ids=[item_id for item_id, _source_id, _text in proposal_inputs],
                metadata=metadata,
                body=proposal.body,
                important_conflicts=[
                    conflict.model_dump(mode="json") for conflict in proposal.important_conflicts
                ],
                action_suggestions=[
                    suggestion.model_dump(mode="json") for suggestion in proposal.action_suggestions
                ],
                source_ids=list(
                    dict.fromkeys(source_id for _item_id, source_id, _text in proposal_inputs)
                ),
                created_at=job.created_at,
            )
            draft_path = _state_root(root) / "drafts" / f"{draft_id}.json"
            atomic_write(draft_path, draft.model_dump_json(indent=2).encode())
            drafts.append(draft)
            for action_index, suggestion in enumerate(proposal.action_suggestions):
                action = ActionCandidate(
                    action_id=uuid5(draft_id, f"action:{action_index}"),
                    kind=suggestion.kind,
                    description=suggestion.description,
                    related_project_id=suggestion.related_project_id,
                    source_draft_id=draft_id,
                    created_at=job.created_at,
                )
                atomic_write(
                    _state_root(root) / "actions" / f"{action.action_id}.json",
                    action.model_dump_json(indent=2).encode(),
                )
                actions.append(action)
        completed = job.model_copy(
            update={
                "state": "completed",
                "draft_ids": [draft.draft_id for draft in drafts],
                "action_candidates": [action.model_dump(mode="json") for action in actions],
                "finished_at": datetime.now(UTC),
                "checkpoint_sha256": checkpoint_hash,
                "revision": job.revision + 1,
            }
        )
        atomic_write(
            _state_root(root) / "intake" / "jobs" / f"{job.job_id}.json",
            completed.model_dump_json(indent=2).encode(),
        )
        return completed

    def get_job(self, root: Path, job_id: UUID) -> IntakeJob:
        root = root.resolve()
        job = read_job(root, job_id)
        if job is None:
            raise WorkspaceError("Intake job was not found", 404)
        if job.state not in {"running", "provider_calling"} or attempt_is_live(
            root, job.attempt_id
        ):
            return job
        path = _state_root(root) / "intake" / "checkpoints" / f"{job_id}.json"
        checkpoint: dict[str, Any] | None = None
        checkpoint_hash: str | None = None
        if path.exists():
            try:
                document = json.loads(path.read_bytes())
                checkpoint_hash = document.pop("checkpoint_sha256")
                candidate_hash = hashlib.sha256(
                    json.dumps(
                        document,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode()
                ).hexdigest()
                if (
                    document.get("schema") == "intake-provider-checkpoint-v1"
                    and document.get("job_id") == str(job_id)
                    and document.get("attempt_id") == job.attempt_id
                    and document.get("request_hash") == job.request_hash
                    and checkpoint_hash == candidate_hash
                ):
                    checkpoint = document
            except (OSError, ValueError, TypeError, KeyError):
                checkpoint = None
        inputs = (
            self._job_inputs(root, job, checkpoint.get("input_hashes", {}))
            if checkpoint is not None
            else None
        )
        with workspace_lock(root):
            current = read_job(root, job_id)
            if current is None or current.state not in {"running", "provider_calling"}:
                return current or job
            if current.attempt_id != job.attempt_id or current.revision != job.revision:
                return current
            if checkpoint is not None and checkpoint_hash is not None:
                if (
                    inputs is not None
                    and current.line_id is not None
                    and current.project_id is not None
                ):
                    completed = self._apply_checkpoint(
                        root,
                        current,
                        checkpoint,
                        checkpoint_hash,
                        current.line_id,
                        current.project_id,
                        inputs,
                    )
                    recovered = True
                else:
                    completed = None
                    recovered = False
            else:
                completed = None
                recovered = False
            if not recovered:
                unknown = current.model_copy(
                    update={
                        "state": "unknown",
                        "error": "模型请求状态未知；不会自动重新发送。请明确选择重新整理。",
                        "revision": current.revision + 1,
                    }
                )
                atomic_write(
                    _state_root(root) / "intake" / "jobs" / f"{job_id}.json",
                    unknown.model_dump_json(indent=2).encode(),
                )
                result = unknown
            else:
                assert completed is not None
                result = completed
        SourceStore().refresh_items(root, job.item_ids)
        archive_intake(root)
        archive_completed_transactions(root)
        return result

    def _job_inputs(
        self, root: Path, job: IntakeJob, expected_hashes: dict[str, Any]
    ) -> list[tuple[UUID, UUID, str]] | None:
        items = {item.item_id: item for item in read_items(root)}
        inputs: list[tuple[UUID, UUID, str]] = []
        for item_id in job.item_ids:
            item = items.get(item_id)
            if item is None:
                return None
            path = (root / item.original_relative_path).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                return None
            raw = path.read_bytes()
            source_id, digest = self._source_identity(root, item.source_id)
            if source_id != item.source_id or hashlib.sha256(raw).hexdigest() != digest:
                return None
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                return None
            if expected_hashes.get(str(item_id)) != hashlib.sha256(text.encode()).hexdigest():
                return None
            inputs.append((item.item_id, item.source_id, text))
        return inputs

    def cancel_job(self, root: Path, job_id: UUID) -> IntakeJob:
        root = root.resolve()
        path = _state_root(root) / "intake" / "jobs" / f"{job_id}.json"
        with workspace_lock(root):
            job = read_job(root, job_id)
            if job is None:
                raise WorkspaceError("Intake job was not found", 404)
            if job.state in {"running", "provider_calling"}:
                job = job.model_copy(
                    update={
                        "state": "cancelled",
                        "finished_at": datetime.now(UTC),
                        "revision": job.revision + 1,
                    }
                )
                atomic_write(path, job.model_dump_json(indent=2).encode())
        SourceStore().refresh_items(root, job.item_ids)
        archive_intake(root)
        return job

    def list_actions(self, root: Path) -> list[ActionCandidate]:
        action_root = _state_root(root) / "actions"
        if not action_root.exists():
            return []
        actions = [
            ActionCandidate.model_validate_json(path.read_text(encoding="utf-8"))
            for path in action_root.glob("*.json")
        ]
        return sorted(actions, key=lambda action: (action.created_at, str(action.action_id)))

    def list_drafts(self, root: Path, *, pending_only: bool = False) -> list[Draft]:
        draft_root = _state_root(root) / "drafts"
        if not draft_root.exists():
            return []
        drafts = [
            Draft.model_validate_json(path.read_text(encoding="utf-8"))
            for path in draft_root.glob("*.json")
        ]
        drafts = [
            draft
            for draft in drafts
            if draft.job_id is None
            or (job := read_job(root, draft.job_id)) is not None
            and job.state == "completed"
        ]
        if pending_only:
            drafts = [draft for draft in drafts if draft.state == "pending"]
        return sorted(drafts, key=lambda draft: (draft.created_at, str(draft.draft_id)))

    def get_draft(self, root: Path, draft_id: UUID) -> Draft:
        path = _state_root(root) / "drafts" / f"{draft_id}.json"
        try:
            draft = Draft.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkspaceError("Draft was not found", 404) from exc
        if draft.job_id is not None:
            job = read_job(root, draft.job_id)
            if job is None or job.state != "completed":
                raise WorkspaceError("Draft is not ready for review", 404)
        return draft

    def edit_draft(
        self,
        root: Path,
        draft_id: UUID,
        *,
        expected_version: int,
        title: str,
        body: str,
        target_page_id: UUID | None = None,
        expected_base_sha256: str | None = None,
    ) -> Draft:
        root = root.resolve()
        path = _state_root(root) / "drafts" / f"{draft_id}.json"
        with _draft_lock(root, draft_id):
            draft = self.get_draft(root, draft_id)
            if draft.state != "pending" or draft.version != expected_version:
                raise WorkspaceWriteConflict("Draft changed since it was reviewed")
            metadata = {**draft.metadata, "title": title}
            if target_page_id is None:
                if expected_base_sha256 is not None:
                    raise WorkspaceError("A base version requires a target page")
                metadata["id"] = str(draft.draft_id)
            else:
                target = read_page(root, target_page_id)
                if target.storage_area != "formal" or target.approval_state == "pending":
                    raise WorkspaceError("Only confirmed knowledge pages can be updated")
                if target.content_sha256 != expected_base_sha256:
                    raise WorkspaceWriteConflict("目标页面已变化，请检查当前版本后再继续审核。")
                if any(
                    metadata.get(key) != target.metadata.get(key)
                    for key in ("line_id", "project_id")
                ):
                    raise WorkspaceError("A draft can only update a page in its selected project")
                metadata["id"] = str(target.page_id)
            edited = draft.model_copy(
                update={
                    "metadata": metadata,
                    "body": body,
                    "target_page_id": target_page_id,
                    "expected_base_sha256": expected_base_sha256,
                    "version": draft.version + 1,
                }
            )
            atomic_write(path, edited.model_dump_json(indent=2).encode())
            return edited

    def confirm_draft(
        self,
        root: Path,
        draft_id: UUID,
        *,
        expected_version: int,
        confirmation_id: str,
        operation_id: str,
        conflict_resolutions: dict[str, str],
    ) -> MutationResult:
        root = root.resolve()
        path = _state_root(root) / "drafts" / f"{draft_id}.json"
        with _draft_lock(root, draft_id):
            draft = self.get_draft(root, draft_id)
            if draft.state != "pending" or draft.version != expected_version:
                raise WorkspaceWriteConflict("Draft changed since it was reviewed")
            required = {conflict["id"] for conflict in draft.important_conflicts}
            if set(conflict_resolutions) != required:
                raise WorkspaceError("Resolve each important conflict or mark it unresolved")
            conflicts_by_id = {conflict["id"]: conflict for conflict in draft.important_conflicts}
            if any(
                value != "unresolved" and value not in conflicts_by_id[conflict_id]["alternatives"]
                for conflict_id, value in conflict_resolutions.items()
            ):
                raise WorkspaceError("Choose one of the alternatives shown for each conflict")
            page_metadata = {
                key: value for key, value in draft.metadata.items() if key != "approval"
            }
            if conflict_resolutions:
                page_metadata["conflict_resolutions"] = conflict_resolutions
            final_body = _conflict_outcome_body(draft, conflict_resolutions)
            result = self.page_writer.confirm(
                root,
                metadata=page_metadata,
                body=final_body,
                confirmation_id=confirmation_id,
                operation_id=operation_id,
                expected_base_sha256=draft.expected_base_sha256,
            )
            confirmed = draft.model_copy(
                update={
                    "state": "confirmed",
                    "body": final_body,
                    "conflict_resolutions": conflict_resolutions,
                }
            )
            atomic_write(path, confirmed.model_dump_json(indent=2).encode())
            SourceStore().refresh_items(root, draft.input_ids)
            return result

    def _source_identity(self, root: Path, source_id: UUID) -> tuple[UUID, str]:
        source_root = _state_root(root) / "sources"
        if source_root.exists():
            for index_path in source_root.glob("*.json"):
                records = json.loads(index_path.read_text(encoding="utf-8"))
                for record in records:
                    if record.get("source_id") == str(source_id):
                        return UUID(record["source_id"]), str(record["sha256"])
        raise WorkspaceError("Source record was not found")
