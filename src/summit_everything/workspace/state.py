"""Read and archive the shared intake state without an auxiliary index."""

from __future__ import annotations

import fcntl
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from summit_everything.domain.models import IntakeItem, IntakeJob
from summit_everything.workspace.archives import (
    archive_completed_json,
    archive_one,
    archived_records,
)
from summit_everything.workspace.manifest import WorkspaceError
from summit_everything.workspace.transactions import atomic_delete, workspace_lock


class AttemptLease:
    """Same-host advisory liveness for one provider attempt, independent of profile."""

    def __init__(self, root: Path, attempt_id: str) -> None:
        try:
            safe_id = str(UUID(attempt_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("attempt ID must be a UUID") from exc
        self.path = root / ".summit-everything" / "attempt-leases" / f"{safe_id}.lock"
        self.file: Any = None

    def acquire(self, *, blocking: bool = True) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            fcntl.flock(self.file.fileno(), flags)
            return True
        except BlockingIOError:
            self.file.close()
            self.file = None
            return False

    def __enter__(self) -> AttemptLease:
        if self.file is None:
            self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.file is not None:
            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()
            self.file = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def attempt_is_live(root: Path, attempt_id: str | None) -> bool:
    """Check a live worker without creating a lease or consulting profile IDs."""
    if not attempt_id:
        return False
    try:
        safe_id = str(UUID(attempt_id))
    except (ValueError, TypeError, AttributeError):
        return False
    path = root / ".summit-everything" / "attempt-leases" / f"{safe_id}.lock"
    if not path.exists():
        return False
    try:
        with path.open("rb") as lease:
            try:
                fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(lease.fileno(), fcntl.LOCK_UN)
            return False
    except OSError:
        return False


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def item_archive_name(item_id: UUID, attempt_no: int) -> str:
    return f"{item_id}@{attempt_no}"


def preserve_undated_item(root: Path, item: IntakeItem) -> None:
    """Preserve a legacy terminal attempt before a new operation replaces it."""
    if item.finished_at is not None or item.state not in {"completed", "failed", "cancelled"}:
        return
    value = item.model_dump(mode="json")
    active = root / ".summit-everything" / "intake" / "items" / f"{item.item_id}.json"
    archive_one(
        root,
        active,
        "intake-items",
        item_archive_name(item.item_id, item.attempt_no),
        value,
        "undated",
    )


def archive_intake(root: Path, now: datetime | None = None) -> int:
    """Compress terminal item/job records; drafts and original bytes stay in place."""
    current = now or datetime.now(UTC)
    state_root = root / ".summit-everything" / "intake"
    archived = 0
    with workspace_lock(root):
        item_root = state_root / "items"
        if item_root.exists():
            for path in sorted(item_root.glob("*.json")):
                try:
                    item = IntakeItem.model_validate_json(path.read_bytes())
                except (OSError, ValueError) as exc:
                    raise WorkspaceError("收件项损坏，请核实后继续。", 409) from exc
                if item.state not in {"completed", "failed", "cancelled"}:
                    continue
                if not item.finished_at:
                    continue
                archived += archive_completed_json(
                    root,
                    path,
                    namespace="intake-items",
                    name=item_archive_name(item.item_id, item.attempt_no),
                    now=current,
                    terminal_states={item.state},
                )
        job_root = state_root / "jobs"
        if job_root.exists():
            for path in sorted(job_root.glob("*.json")):
                try:
                    job = IntakeJob.model_validate_json(path.read_bytes())
                except (OSError, ValueError) as exc:
                    raise WorkspaceError("整理任务损坏，请核实后继续。", 409) from exc
                if job.state not in {"completed", "failed", "cancelled"} or not job.finished_at:
                    continue
                archived += archive_completed_json(
                    root,
                    path,
                    namespace="intake-jobs",
                    name=str(job.job_id),
                    now=current,
                    terminal_states={job.state},
                )
                if job.state == "completed":
                    checkpoint = state_root / "checkpoints" / f"{job.job_id}.json"
                    if checkpoint.exists():
                        atomic_delete(checkpoint)
        for name, value in archived_records(root, "intake-jobs").items():
            if value.get("state") == "completed":
                checkpoint = state_root / "checkpoints" / f"{name}.json"
                if checkpoint.exists():
                    atomic_delete(checkpoint)
    return archived


def list_items(root: Path, *, archive: bool = True) -> list[IntakeItem]:
    """Read active items plus immutable completion attempts, blocking broken chains."""
    if archive:
        archive_intake(root)
    item_root = root / ".summit-everything" / "intake" / "items"
    active: dict[UUID, IntakeItem] = {}
    if item_root.exists():
        for path in sorted(item_root.glob("*.json")):
            try:
                item = IntakeItem.model_validate_json(path.read_bytes())
            except (OSError, ValueError) as exc:
                raise WorkspaceError("收件项损坏，请核实后继续。", 409) from exc
            if item.item_id in active:
                raise WorkspaceError("收件项存在重复 ID。", 409)
            active[item.item_id] = item
    archived = archived_records(root, "intake-items")
    grouped: dict[UUID, dict[int, dict[str, Any]]] = {}
    for name, value in archived.items():
        try:
            item_id_text, attempt_text = name.rsplit("@", 1)
            item_id, attempt_no = UUID(item_id_text), int(attempt_text)
            item = IntakeItem.model_validate(value)
            if item.item_id != item_id or item.attempt_no != attempt_no:
                raise ValueError("archive identity mismatch")
            grouped.setdefault(item_id, {})[attempt_no] = value
        except (ValueError, TypeError) as exc:
            raise WorkspaceError("收件归档损坏或冲突。", 409) from exc
    result: list[IntakeItem] = []
    for item_id in set(grouped) | set(active):
        versions = grouped.get(item_id, {})
        ordered = sorted(versions)
        if ordered and ordered != list(range(ordered[0], ordered[-1] + 1)):
            raise WorkspaceError("收件归档版本链不完整。", 409)
        for prior_no, next_no in zip(ordered, ordered[1:], strict=False):
            prior = versions[prior_no]
            current_value = versions[next_no]
            if (
                current_value.get("previous_attempt_sha256")
                != hashlib.sha256(_canonical(prior)).hexdigest()
            ):
                raise WorkspaceError("收件归档版本链冲突。", 409)
        current_item = active.get(item_id)
        if current_item is not None:
            previous = versions.get(current_item.attempt_no)
            if previous is not None:
                if previous != current_item.model_dump(mode="json"):
                    raise WorkspaceError("活动收件项与归档版本冲突。", 409)
                # Exact duplicate is the expected summary-first crash window.
            elif versions:
                latest_no = max(versions)
                if current_item.attempt_no != latest_no + 1:
                    raise WorkspaceError("活动收件项与归档版本链不连续。", 409)
                if (
                    current_item.previous_attempt_sha256
                    != hashlib.sha256(_canonical(versions[latest_no])).hexdigest()
                ):
                    raise WorkspaceError("活动收件项与归档版本链冲突。", 409)
            result.append(current_item)
        elif versions:
            result.append(IntakeItem.model_validate(versions[max(versions)]))
    return sorted(result, key=lambda item: (item.created_at, str(item.item_id)))


def get_job(root: Path, job_id: UUID) -> IntakeJob | None:
    path = root / ".summit-everything" / "intake" / "jobs" / f"{job_id}.json"
    active: dict[str, Any] | None = None
    if path.exists():
        try:
            active = json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise WorkspaceError("整理任务损坏，请核实后继续。", 409) from exc
    prior = archived_records(root, "intake-jobs").get(str(job_id))
    if active is not None and prior is not None and active != prior:
        raise WorkspaceError("活动整理任务与归档副本冲突。", 409)
    value = active if active is not None else prior
    return IntakeJob.model_validate(value) if value is not None else None


def job_attempt_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()
