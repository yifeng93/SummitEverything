"""Raw source preservation and visible local intake queue."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from summit_everything.domain.models import IntakeItem, SourceRecord
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.transactions import atomic_write, workspace_lock


class IntakeConflict(ValueError):
    """An intake retry does not match its original user intent."""


def _safe_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^\w.() -]+", "_", basename, flags=re.UNICODE).strip(" .")
    if not cleaned or Path(cleaned).suffix.lower() not in {".txt", ".md"}:
        raise WorkspaceError("Only TXT and Markdown files can be added to intake")
    return cleaned


def _operation_path(root: Path, operation_id: str) -> Path:
    key = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    return root / ".summit-everything" / "transactions" / f"intake-{key}.json"


class SourceStore:
    def capture(self, root: Path, raw: bytes, filename: str, operation_id: str) -> IntakeItem:
        root = root.resolve()
        filename = _safe_filename(filename)
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
        journal_path = _operation_path(root, operation_id)
        with workspace_lock(root):
            if journal_path.exists():
                intent = self._read_intent(journal_path)
                if intent.get("request_hash") != self._request_hash(raw, filename):
                    raise IntakeConflict("operation_id was already used for different intake")
                return self._resume(root, journal_path, intent)
            manifest = load_manifest(root)
            created_at = datetime.now(UTC)
            source_id = uuid5(manifest.workspace_id, f"source:{operation_id}")
            item_id = uuid5(manifest.workspace_id, f"intake:{operation_id}")
            month = created_at.strftime("%Y-%m")
            original_path = f"原件/{month}/{source_id}-{filename}"
            intent = {
                "schema": "intake-source-v1",
                "operation_id": operation_id,
                "request_hash": self._request_hash(raw, filename),
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
            return self._resume(root, journal_path, intent)

    def list_items(self, root: Path) -> list[IntakeItem]:
        root = root.resolve()
        self.recover(root)
        items_root = root / ".summit-everything" / "intake" / "items"
        items: list[IntakeItem] = []
        if not items_root.exists():
            return items
        for path in sorted(items_root.glob("*.json")):
            try:
                items.append(IntakeItem.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                raise WorkspaceError("An intake queue item is invalid") from exc
        return sorted(items, key=lambda item: (item.created_at, str(item.item_id)))

    def recover(self, root: Path) -> None:
        journal_root = root / ".summit-everything" / "transactions"
        if not journal_root.exists():
            return
        with workspace_lock(root):
            for path in sorted(journal_root.glob("intake-*.json")):
                intent = self._read_intent(path)
                if intent.get("state") != "succeeded":
                    self._resume(root, path, intent)

    def _request_hash(self, raw: bytes, filename: str) -> str:
        payload = json.dumps(
            {"sha256": hashlib.sha256(raw).hexdigest(), "filename": filename},
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
        intent.pop("raw_b64", None)
        atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
        return item


class IntakeService:
    def __init__(self, source_store: SourceStore | None = None) -> None:
        self.source_store = source_store or SourceStore()

    def add_text(self, root: Path, text: str, *, filename: str, operation_id: str) -> IntakeItem:
        return self.source_store.capture(root, text.encode("utf-8"), filename, operation_id)

    def add_file(self, root: Path, raw: bytes, *, filename: str, operation_id: str) -> IntakeItem:
        return self.source_store.capture(root, raw, filename, operation_id)

    def list_items(self, root: Path) -> list[IntakeItem]:
        return self.source_store.list_items(root)
