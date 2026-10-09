"""Explicit source-to-draft workflow; only user-confirmed drafts reach PageWriter."""

from __future__ import annotations

import fcntl
import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5

from summit_everything.domain.models import (
    ActionCandidate,
    Draft,
    IntakeItem,
    IntakeJob,
    MutationResult,
)
from summit_everything.intake.sources import SourceStore
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.reader import read_page
from summit_everything.workspace.transactions import atomic_write, workspace_lock
from summit_everything.workspace.writer import PageWriter, WorkspaceWriteConflict


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
        self, provider: FakeLLM | None = None, page_writer: PageWriter | None = None
    ) -> None:
        self.provider = provider or FakeLLM()
        self.page_writer = page_writer or PageWriter()

    def create_job(
        self,
        root: Path,
        item_ids: list[UUID],
        *,
        operation_id: str,
        line_id: UUID,
        project_id: UUID,
        reprocess: bool = False,
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
        jobs_root = _state_root(root) / "intake" / "jobs"
        job_path = jobs_root / f"{job_id}.json"
        with workspace_lock(root):
            if job_path.exists():
                prior = IntakeJob.model_validate_json(job_path.read_text(encoding="utf-8"))
                if prior.request_hash != request_hash:
                    raise WorkspaceWriteConflict("Job operation ID was reused for different inputs")
                return prior
            items = self._load_items(root)
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
                if state != "pending" and not reprocess:
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
            job = IntakeJob(
                job_id=job_id,
                item_ids=item_ids,
                request_hash=request_hash,
                state="running",
                created_at=datetime.now(UTC),
            )
            jobs_root.mkdir(parents=True, exist_ok=True)
            atomic_write(job_path, job.model_dump_json(indent=2).encode())
            for item in selected:
                assert item is not None
                item_path = _state_root(root) / "intake" / "items" / f"{item.item_id}.json"
                updated = item.model_copy(update={"state": "processing", "latest_job_id": job_id})
                atomic_write(item_path, updated.model_dump_json(indent=2).encode())
        try:
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
            drafts: list[Draft] = []
            actions: list[ActionCandidate] = []
            for index, proposal in enumerate(proposals):
                proposal_inputs = [inputs[source_index] for source_index in proposal.input_indexes]
                draft_id = uuid5(job_id, f"draft:{index}")
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
                    input_ids=[item_id for item_id, _source_id, _text in proposal_inputs],
                    metadata=metadata,
                    body=proposal.body,
                    important_conflicts=[
                        conflict.model_dump(mode="json")
                        for conflict in proposal.important_conflicts
                    ],
                    action_suggestions=[
                        suggestion.model_dump(mode="json")
                        for suggestion in proposal.action_suggestions
                    ],
                    source_ids=list(
                        dict.fromkeys(source_id for _item_id, source_id, _text in proposal_inputs)
                    ),
                    created_at=datetime.now(UTC),
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
                        created_at=datetime.now(UTC),
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
                }
            )
            atomic_write(job_path, completed.model_dump_json(indent=2).encode())
            SourceStore().refresh_items(root, item_ids)
            return completed
        except Exception as exc:
            failed = job.model_copy(update={"state": "failed", "error": str(exc)[:500]})
            atomic_write(job_path, failed.model_dump_json(indent=2).encode())
            SourceStore().refresh_items(root, item_ids)
            raise

    def get_job(self, root: Path, job_id: UUID) -> IntakeJob:
        path = _state_root(root) / "intake" / "jobs" / f"{job_id}.json"
        try:
            return IntakeJob.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkspaceError("Intake job was not found", 404) from exc

    def cancel_job(self, root: Path, job_id: UUID) -> IntakeJob:
        path = _state_root(root) / "intake" / "jobs" / f"{job_id}.json"
        try:
            job = IntakeJob.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkspaceError("Intake job was not found", 404) from exc
        if job.state == "running":
            job = job.model_copy(update={"state": "cancelled"})
            atomic_write(path, job.model_dump_json(indent=2).encode())
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
        if pending_only:
            drafts = [draft for draft in drafts if draft.state == "pending"]
        return sorted(drafts, key=lambda draft: (draft.created_at, str(draft.draft_id)))

    def get_draft(self, root: Path, draft_id: UUID) -> Draft:
        path = _state_root(root) / "drafts" / f"{draft_id}.json"
        try:
            return Draft.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkspaceError("Draft was not found", 404) from exc

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

    def _load_items(self, root: Path) -> dict[UUID, IntakeItem]:
        item_root = _state_root(root) / "intake" / "items"
        if not item_root.exists():
            return {}
        items = [
            IntakeItem.model_validate_json(path.read_text(encoding="utf-8"))
            for path in item_root.glob("*.json")
        ]
        return {item.item_id: item for item in items}

    def _source_identity(self, root: Path, source_id: UUID) -> tuple[UUID, str]:
        source_root = _state_root(root) / "sources"
        if source_root.exists():
            for index_path in source_root.glob("*.json"):
                records = json.loads(index_path.read_text(encoding="utf-8"))
                for record in records:
                    if record.get("source_id") == str(source_id):
                        return UUID(record["source_id"]), str(record["sha256"])
        raise WorkspaceError("Source record was not found")
