"""Portable action evidence. Callers hold workspace identity lock for every write."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError

from summit_everything.workspace.manifest import WorkspaceError
from summit_everything.workspace.transactions import atomic_delete, atomic_write

if TYPE_CHECKING:
    from summit_everything.intake.actions import Action


def receipt_root(root: Path) -> Path:
    return root / ".summit-everything" / "action_receipts"


def read_receipts(root: Path) -> dict[UUID, Action]:
    from summit_everything.intake.actions import Action, payload_hash, validate_payload

    result: dict[UUID, Action] = {}
    for path in sorted(receipt_root(root).glob("**/*.json")):
        try:
            document = json.loads(path.read_bytes())
            values = (
                document["items"].values()
                if document.get("schema") == "action-receipt-month-v1"
                else [document]
            )
            for value in values:
                item = Action.model_validate(value)
                validate_payload(item.kind, item.payload)
                if item.payload_sha256 != payload_hash(item.kind, item.payload):
                    raise ValueError("Invalid payload fingerprint")
                if item.state != "proposed" and (not item.confirmation_id or not item.confirmed_at):
                    raise ValueError("Missing independent confirmation")
                previous = result.get(item.action_id)
                if previous and previous != item:
                    raise ValueError("Conflicting action receipts")
                result[item.action_id] = item
        except (ValueError, OSError, ValidationError, KeyError, TypeError, AttributeError):
            raise WorkspaceError("动作凭据损坏或存在冲突，请核实后继续。", 409) from None
    return result


def save_receipt(root: Path, action: Action) -> None:
    path = receipt_root(root) / "active" / f"{action.action_id}.json"
    atomic_write(path, action.model_dump_json(indent=2).encode())


def archive_completed(root: Path, now: datetime) -> None:
    months: dict[str, dict[str, object]] = {}
    completed: list[Action] = []
    for item in read_receipts(root).values():
        if (
            item.state not in {"succeeded", "failed"}
            or not item.finished_at
            or item.finished_at.strftime("%Y-%m") >= now.strftime("%Y-%m")
        ):
            continue
        month = item.finished_at.strftime("%Y-%m")
        months.setdefault(month, {})[str(item.action_id)] = item.model_dump(mode="json")
        completed.append(item)
    # Summary replacement precedes active deletion. Interrupted duplicate copies are equal.
    for month, items in months.items():
        target = receipt_root(root) / "completed" / month / "summary.json"
        atomic_write(
            target,
            json.dumps(
                {"schema": "action-receipt-month-v1", "month": month, "items": items},
                ensure_ascii=False,
            ).encode(),
        )
    for item in completed:
        active = receipt_root(root) / "active" / f"{item.action_id}.json"
        if active.exists():
            atomic_delete(active)
