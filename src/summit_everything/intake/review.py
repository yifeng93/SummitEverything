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
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.transactions import atomic_write
from summit_everything.workspace.writer import PageWriter, WorkspaceWriteConflict


def _state_root(root: Path) -> Path:
    return root / ".summit-everything"


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
    ) -> IntakeJob:
        root = root.resolve()
        if not operation_id.strip() or not item_ids or len(set(item_ids)) != len(item_ids):
            raise WorkspaceError("Choose one or more distinct intake items")
        manifest = load_manifest(root)
        project = next((record for record in manifest.projects if record.id == project_id), None)
        if project is None or project.line_id != line_id or project.archived:
            raise WorkspaceError("Choose an active project in the selected line")
        job_id = uuid5(manifest.workspace_id, f"intake-job:{operation_id}")
        request_hash = hashlib.sha256(
            json.dumps(
                {
                    "item_ids": [str(item_id) for item_id in item_ids],
                    "line_id": str(line_id),
                    "project_id": str(project_id),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        jobs_root = _state_root(root) / "intake" / "jobs"
        job_path = jobs_root / f"{job_id}.json"
        if job_path.exists():
            prior = IntakeJob.model_validate_json(job_path.read_text(encoding="utf-8"))
            if prior.request_hash != request_hash:
                raise WorkspaceWriteConflict("Job operation ID was reused for different inputs")
            return prior
        items = self._load_items(root)
        selected = [items.get(item_id) for item_id in item_ids]
        if any(item is None or item.state != "pending" for item in selected):
            raise WorkspaceError("Every selected intake item must be pending")
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
        try:
            proposals = self.provider.organize(inputs)
            if len(proposals) != len(inputs):
                raise LLMProviderError("Provider returned an unexpected proposal count")
            drafts: list[Draft] = []
            actions: list[ActionCandidate] = []
            for index, (proposal, (item_id, source_id, _text)) in enumerate(
                zip(proposals, inputs, strict=True)
            ):
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
                    input_ids=[item_id],
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
                    source_ids=[source_id],
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
            return completed
        except Exception as exc:
            failed = job.model_copy(update={"state": "failed", "error": str(exc)[:500]})
            atomic_write(job_path, failed.model_dump_json(indent=2).encode())
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
        self, root: Path, draft_id: UUID, *, expected_version: int, title: str, body: str
    ) -> Draft:
        root = root.resolve()
        path = _state_root(root) / "drafts" / f"{draft_id}.json"
        with _draft_lock(root, draft_id):
            draft = self.get_draft(root, draft_id)
            if draft.state != "pending" or draft.version != expected_version:
                raise WorkspaceWriteConflict("Draft changed since it was reviewed")
            edited = draft.model_copy(
                update={
                    "metadata": {**draft.metadata, "title": title},
                    "body": body,
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
            result = self.page_writer.confirm(
                root,
                metadata=page_metadata,
                body=draft.body,
                confirmation_id=confirmation_id,
                operation_id=operation_id,
            )
            confirmed = draft.model_copy(
                update={"state": "confirmed", "conflict_resolutions": conflict_resolutions}
            )
            atomic_write(path, confirmed.model_dump_json(indent=2).encode())
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
