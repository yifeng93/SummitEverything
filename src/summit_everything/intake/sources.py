"""Raw source preservation and visible local intake queue."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid5

from summit_everything.domain.models import Draft, IntakeItem, SourceDetail, SourceRecord
from summit_everything.workspace.archives import (
    archive_completed_transactions,
    read_active_or_archived,
)
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.state import (
    archive_intake,
    attempt_is_live,
)
from summit_everything.workspace.state import (
    get_job as read_job,
)
from summit_everything.workspace.state import (
    list_items as read_shared_items,
)
from summit_everything.workspace.transactions import atomic_write, workspace_lock


class IntakeConflict(ValueError):
    """An intake retry does not match its original user intent."""


def safe_source_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^\w.() -]+", "_", basename, flags=re.UNICODE).strip(" .")
    if not cleaned or Path(cleaned).suffix.lower() not in {".txt", ".md"}:
        raise WorkspaceError("Only TXT and Markdown files can be added to intake")
    return cleaned


def _operation_path(root: Path, operation_id: str) -> Path:
    key = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    return root / ".summit-everything" / "transactions" / f"intake-{key}.json"


class SourceStore:
    def capture(
        self,
        root: Path,
        raw: bytes,
        filename: str,
        operation_id: str,
        *,
        external_identity: dict[str, str] | None = None,
        origin_kind: Literal["quick_note", "file", "feishu_material", "unknown"] = "unknown",
    ) -> IntakeItem:
        root = root.resolve()
        filename = safe_source_filename(filename)
        if not operation_id.strip():
            raise WorkspaceError("Intake operation ID is required")
        digest = hashlib.sha256(raw).hexdigest()
        if not raw:
            raise WorkspaceError("The selected source file is empty")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("Only UTF-8 text sources can be added") from exc
        self.recover(root)
        archive_completed_transactions(root)
        journal_path = _operation_path(root, operation_id)
        with workspace_lock(root):
            prior = read_active_or_archived(root, journal_path, "transactions", journal_path.name)
            if prior is not None:
                intent = self._read_intent_value(prior)
                if intent.get("request_hash") != self._request_hash(
                    raw,
                    filename,
                    external_identity,
                    origin_kind=intent.get("origin_kind", "unknown"),
                ):
                    raise IntakeConflict("operation_id was already used for different intake")
                if journal_path.exists():
                    item = self._resume(root, journal_path, intent)
                    archive_completed_transactions(root, locked=True)
                    return item
                items = {item.item_id: item for item in read_shared_items(root, archive=False)}
                prior_item = items.get(UUID(intent["item_id"]))
                if prior_item is not None:
                    return prior_item
                return self._resume(root, journal_path, intent)
            manifest = load_manifest(root)
            created_at = datetime.now(UTC)
            source_id = uuid5(manifest.workspace_id, f"source:{operation_id}")
            item_id = uuid5(manifest.workspace_id, f"intake:{operation_id}")
            month = created_at.strftime("%Y-%m")
            original_path = f"原件/{month}/{source_id}-{filename}"
            intent = {
                "schema": "intake-source-v1",
                "origin_kind": origin_kind,
                "external_identity": external_identity,
                "operation_id": operation_id,
                "request_hash": self._request_hash(
                    raw, filename, external_identity, origin_kind=origin_kind
                ),
                "source_id": str(source_id),
                "item_id": str(item_id),
                "filename": filename,
                "title": Path(filename).stem,
                "original_relative_path": original_path,
                "created_at": created_at.isoformat(),
                "sha256": digest,
                "raw_b64": base64.b64encode(raw).decode("ascii"),
                "state": "running",
            }
            atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
            item = self._resume(root, journal_path, intent)
            archive_completed_transactions(root, locked=True)
            return item

    def list_items(self, root: Path) -> list[IntakeItem]:
        root = root.resolve()
        self.recover(root)
        archive_completed_transactions(root)
        items_root = root / ".summit-everything" / "intake" / "items"
        with workspace_lock(root):
            # Re-read under the writer lock: an unlocked snapshot could carry an
            # older attempt into this derived-state write and erase a reprocess.
            items = read_shared_items(root, archive=False)
            for index, item in enumerate(items):
                path = items_root / f"{item.item_id}.json"
                state = self.derived_state(root, item)
                if item.state != state and path.exists():
                    item = item.model_copy(
                        update={
                            "state": state,
                            "revision": item.revision + 1,
                            "finished_at": datetime.now(UTC)
                            if state in {"completed", "failed", "cancelled"}
                            else None,
                        }
                    )
                    atomic_write(path, item.model_dump_json(indent=2).encode())
                    items[index] = item
        return sorted(items, key=lambda item: (item.created_at, str(item.item_id)))

    def refresh_items(self, root: Path, item_ids: list[UUID] | None = None) -> None:
        root = root.resolve()
        items_root = root / ".summit-everything" / "intake" / "items"
        selected_ids = {str(item_id) for item_id in item_ids} if item_ids is not None else None
        with workspace_lock(root):
            items = read_shared_items(root, archive=False)
            for item in items:
                if selected_ids is not None and str(item.item_id) not in selected_ids:
                    continue
                path = items_root / f"{item.item_id}.json"
                if not path.exists():
                    continue
                state = self.derived_state(root, item)
                if item.state != state:
                    updated = item.model_copy(
                        update={
                            "state": state,
                            "revision": item.revision + 1,
                            "finished_at": datetime.now(UTC)
                            if state in {"completed", "failed", "cancelled"}
                            else None,
                        }
                    )
                    atomic_write(path, updated.model_dump_json(indent=2).encode())
        archive_intake(root)

    def derived_state(self, root: Path, item: IntakeItem) -> str:
        if item.latest_job_id is None:
            return item.state
        latest = read_job(root, item.latest_job_id)
        if latest is None:
            raise WorkspaceError("An intake item refers to a missing job", 409)
        if latest.state in {"running", "provider_calling"}:
            return "processing" if attempt_is_live(root, latest.attempt_id) else "unknown"
        if latest.state == "unknown":
            return "unknown"
        if latest.state == "failed":
            return "failed"
        if latest.state == "cancelled":
            return "cancelled"
        drafts_root = root / ".summit-everything" / "drafts"
        for draft_id in latest.draft_ids:
            draft_path = drafts_root / f"{draft_id}.json"
            try:
                draft = Draft.model_validate_json(draft_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise WorkspaceError("An intake job refers to an invalid draft") from exc
            if draft.state == "pending":
                return "reviewing"
        return "completed"

    def get_source(self, root: Path, source_id: UUID) -> SourceDetail:
        root = root.resolve()
        source_root = root / ".summit-everything" / "sources"
        if source_root.exists():
            for index_path in source_root.glob("*.json"):
                try:
                    records = json.loads(index_path.read_text(encoding="utf-8"))
                    record_data = next(
                        (row for row in records if row.get("source_id") == str(source_id)), None
                    )
                    if record_data is None:
                        continue
                    record = SourceRecord.model_validate(record_data)
                    source_path = (root / record.original_relative_path).resolve()
                    if not source_path.is_relative_to(root) or not source_path.is_file():
                        raise WorkspaceError(
                            "The original source is missing or outside the workspace"
                        )
                    raw = source_path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != record.sha256:
                        raise WorkspaceError("The original source no longer matches its saved hash")
                    return SourceDetail(source=record, text=raw.decode("utf-8"))
                except (OSError, UnicodeDecodeError, ValueError) as exc:
                    if isinstance(exc, WorkspaceError):
                        raise
                    raise WorkspaceError("Source record is invalid") from exc
        raise WorkspaceError("Source record was not found", 404)

    def recover(self, root: Path) -> None:
        archive_completed_transactions(root)
        journal_root = root / ".summit-everything" / "transactions"
        if not journal_root.exists():
            return
        with workspace_lock(root):
            for path in sorted(journal_root.glob("intake-*.json")):
                intent = self._read_intent(path)
                if intent.get("state") != "succeeded":
                    self._resume(root, path, intent)
            archive_completed_transactions(root, locked=True)

    def _request_hash(
        self,
        raw: bytes,
        filename: str,
        external_identity: dict[str, str] | None = None,
        *,
        origin_kind: Literal["quick_note", "file", "feishu_material", "unknown"] = "unknown",
    ) -> str:
        fields: dict[str, Any] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "filename": filename,
            **({"external_identity": external_identity} if external_identity else {}),
        }
        if origin_kind != "unknown":
            fields["origin_kind"] = origin_kind
        payload = json.dumps(
            fields,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _read_intent(self, path: Path) -> dict[str, Any]:
        try:
            intent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntakeConflict("Intake transaction journal is invalid") from exc
        if (
            not isinstance(intent, dict)
            or intent.get("schema") != "intake-source-v1"
            or not isinstance(intent.get("source_id"), str)
            or not isinstance(intent.get("item_id"), str)
            or intent.get("state") not in {"running", "succeeded"}
        ):
            raise IntakeConflict("Intake transaction journal is invalid")
        return intent

    def _read_intent_value(self, intent: dict[str, Any]) -> dict[str, Any]:
        if (
            intent.get("schema") != "intake-source-v1"
            or not isinstance(intent.get("source_id"), str)
            or not isinstance(intent.get("item_id"), str)
            or intent.get("state") not in {"running", "succeeded"}
        ):
            raise IntakeConflict("Intake transaction journal is invalid")
        return intent

    def _resume(self, root: Path, journal_path: Path, intent: dict[str, Any]) -> IntakeItem:
        try:
            source_id = UUID(intent["source_id"])
            item_id = UUID(intent["item_id"])
            original_path = Path(intent["original_relative_path"])
            if (
                original_path.is_absolute()
                or original_path.parts[0] != "原件"
                or ".." in original_path.parts
            ):
                raise ValueError("unsafe source path")
            raw_b64 = intent.get("raw_b64")
            original = (
                base64.b64decode(raw_b64, validate=True) if isinstance(raw_b64, str) else None
            )
            if original is None and intent.get("state") != "succeeded":
                raise ValueError("source bytes are missing")
            if original is not None and hashlib.sha256(original).hexdigest() != intent["sha256"]:
                raise ValueError("source bytes do not match their digest")
            created_at = datetime.fromisoformat(intent["created_at"])
            month = created_at.strftime("%Y-%m")
        except (KeyError, TypeError, ValueError) as exc:
            raise IntakeConflict("Intake transaction journal is invalid") from exc
        original_file = root / original_path
        if not original_file.resolve().is_relative_to(root):
            raise IntakeConflict("Original source path escapes the workspace")
        if original is not None:
            if (
                original_file.exists()
                and hashlib.sha256(original_file.read_bytes()).hexdigest() != intent["sha256"]
            ):
                raise IntakeConflict("An existing original conflicts with the intake source hash")
            if not original_file.exists():
                atomic_write(original_file, original)
        source_record = SourceRecord(
            source_id=source_id,
            original_relative_path=original_path.as_posix(),
            filename=intent["filename"],
            sha256=intent["sha256"],
            created_at=created_at,
            external_identity=intent.get("external_identity"),
            origin_kind=intent.get("origin_kind", "unknown"),
        )
        source_index = root / ".summit-everything" / "sources" / f"{month}.json"
        existing_records: list[dict[str, Any]] = []
        if source_index.exists():
            try:
                existing_records = json.loads(source_index.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntakeConflict("Source index is invalid") from exc
        prior = next(
            (record for record in existing_records if record.get("source_id") == str(source_id)),
            None,
        )
        if prior is not None and prior.get("sha256") != source_record.sha256:
            raise IntakeConflict("Source ID already refers to different original bytes")
        if prior is None:
            existing_records.append(source_record.model_dump(mode="json"))
            atomic_write(
                source_index, json.dumps(existing_records, ensure_ascii=False, indent=2).encode()
            )
        item = IntakeItem(
            item_id=item_id,
            source_id=source_id,
            title=intent["title"],
            filename=intent["filename"],
            original_relative_path=original_path.as_posix(),
            created_at=created_at,
            origin_kind=intent.get("origin_kind", "unknown"),
        )
        item_path = root / ".summit-everything" / "intake" / "items" / f"{item_id}.json"
        if item_path.exists():
            existing_item = IntakeItem.model_validate_json(item_path.read_text(encoding="utf-8"))
            if existing_item.source_id != source_id:
                raise IntakeConflict("Intake item ID already refers to another source")
            item = existing_item
        else:
            atomic_write(item_path, item.model_dump_json(indent=2).encode())
        intent["state"] = "succeeded"
        intent.setdefault("finished_at", datetime.now(UTC).isoformat())
        intent.pop("raw_b64", None)
        atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
        return item


class IntakeService:
    def __init__(self, source_store: SourceStore | None = None) -> None:
        self.source_store = source_store or SourceStore()

    def add_text(
        self,
        root: Path,
        text: str,
        *,
        filename: str,
        operation_id: str,
        origin_kind: Literal["quick_note", "file", "feishu_material", "unknown"] = "unknown",
    ) -> IntakeItem:
        return self.source_store.capture(
            root, text.encode("utf-8"), filename, operation_id, origin_kind=origin_kind
        )

    def add_file(
        self,
        root: Path,
        raw: bytes,
        *,
        filename: str,
        operation_id: str,
        origin_kind: Literal["quick_note", "file", "feishu_material", "unknown"] = "unknown",
    ) -> IntakeItem:
        return self.source_store.capture(
            root, raw, filename, operation_id, origin_kind=origin_kind
        )

    def list_items(self, root: Path) -> list[IntakeItem]:
        return self.source_store.list_items(root)

    def get_source(self, root: Path, source_id: UUID) -> SourceDetail:
        return self.source_store.get_source(root, source_id)
