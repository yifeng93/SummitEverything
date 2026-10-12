"""Recoverable monthly summaries for completed workspace receipts.

The active file and monthly summaries are the only sources of truth. Reads scan
summaries instead of relying on a separately maintained index.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from summit_everything.workspace.manifest import WorkspaceError
from summit_everything.workspace.transactions import atomic_delete, atomic_write

_MONTH = re.compile(r"^\d{4}-\d{2}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _summary_path(root: Path, namespace: str, month: str) -> Path:
    if month == "undated":
        return root / ".summit-everything" / "archives" / namespace / month / "summary.json"
    if not _MONTH.fullmatch(month):
        raise WorkspaceError("Archive month is invalid", 409)
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise WorkspaceError("Archive month is invalid", 409) from None
    return root / ".summit-everything" / "archives" / namespace / month / "summary.json"


def _read_summary(path: Path, namespace: str) -> dict[str, dict[str, Any]]:
    try:
        document = json.loads(path.read_bytes())
        if (
            not isinstance(document, dict)
            or document.get("schema") != "workspace-month-v1"
            or document.get("namespace") != namespace
            or not isinstance(document.get("month"), str)
            or (document["month"] != "undated" and not _MONTH.fullmatch(document["month"]))
            or document["month"] != path.parent.name
            or not isinstance(document.get("items"), dict)
        ):
            raise ValueError("invalid archive schema")
        if document["month"] != "undated":
            datetime.strptime(document["month"], "%Y-%m")
        items: dict[str, dict[str, Any]] = {}
        for name, entry in document["items"].items():
            if (
                not isinstance(name, str)
                or not isinstance(entry, dict)
                or not isinstance(entry.get("value"), dict)
                or entry.get("sha256") != hashlib.sha256(_canonical(entry["value"])).hexdigest()
            ):
                raise ValueError("invalid archive entry")
            finished_at = entry["value"].get("finished_at")
            if document["month"] == "undated" and finished_at is not None:
                raise ValueError("dated record stored in undated bucket")
            if document["month"] != "undated" and not isinstance(finished_at, str):
                raise ValueError("undated record stored in a dated bucket")
            if finished_at is not None:
                finished = datetime.fromisoformat(str(finished_at).replace("Z", "+00:00"))
                if finished.strftime("%Y-%m") != document["month"]:
                    raise ValueError("record is stored in the wrong finish month")
            items[name] = entry
        return items
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise WorkspaceError("归档摘要损坏，请核实后继续。", 409) from exc


def find_archived(root: Path, namespace: str, name: str) -> dict[str, Any] | None:
    """Find an archived receipt by its stable active filename; reject ambiguity."""
    archive_root = root / ".summit-everything" / "archives" / namespace
    if not archive_root.exists():
        return None
    _validate_archive_files(archive_root)
    found: dict[str, Any] | None = None
    for path in sorted(archive_root.glob("*/summary.json")):
        items = _read_summary(path, namespace)
        entry = items.get(name)
        if entry is None:
            continue
        value = entry["value"]
        if found is not None and found != value:
            raise WorkspaceError("归档中存在冲突回执，请核实后继续。", 409)
        found = value
    return found


def archived_records(root: Path, namespace: str) -> dict[str, dict[str, Any]]:
    """Return the union of monthly records, accepting only identical duplicates."""
    archive_root = root / ".summit-everything" / "archives" / namespace
    records: dict[str, dict[str, Any]] = {}
    if not archive_root.exists():
        return records
    _validate_archive_files(archive_root)
    for path in sorted(archive_root.glob("*/summary.json")):
        for name, entry in _read_summary(path, namespace).items():
            value = entry["value"]
            if name in records and records[name] != value:
                raise WorkspaceError("归档中存在冲突回执，请核实后继续。", 409)
            records[name] = value
    return records


def _validate_archive_files(archive_root: Path) -> None:
    for path in archive_root.rglob("*"):
        if path.is_file() and (path.name != "summary.json" or path.parent.parent != archive_root):
            raise WorkspaceError("归档目录存在冲突副本，请核实后继续。", 409)


def read_active_or_archived(
    root: Path, active_path: Path, namespace: str, name: str
) -> dict[str, Any] | None:
    """Read an active receipt or its monthly copy; exact crash duplicates are safe."""
    active: dict[str, Any] | None = None
    if active_path.exists():
        try:
            active = json.loads(active_path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkspaceError("业务回执损坏，请核实后继续。", 409) from exc
        if not isinstance(active, dict):
            raise WorkspaceError("业务回执损坏，请核实后继续。", 409)
    archived = find_archived(root, namespace, name)
    if active is not None and archived is not None and active != archived:
        raise WorkspaceError("活动回执与归档副本冲突，请核实后继续。", 409)
    return active if active is not None else archived


def archive_one(
    root: Path,
    active_path: Path,
    namespace: str,
    name: str,
    value: dict[str, Any],
    month: str,
) -> None:
    """Write a monthly summary first, then remove the completed active receipt."""
    finished_at = value.get("finished_at")
    if month == "undated":
        if finished_at is not None:
            raise WorkspaceError("带完成时间的回执不能进入 undated 桶。", 409)
    else:
        if not isinstance(finished_at, str):
            raise WorkspaceError("没有完成时间的回执不能分配月份。", 409)
        try:
            record_month = datetime.fromisoformat(finished_at.replace("Z", "+00:00")).strftime(
                "%Y-%m"
            )
        except ValueError as exc:
            raise WorkspaceError("业务回执损坏，请核实后继续。", 409) from exc
        if record_month != month:
            raise WorkspaceError("归档月份与回执完成时间不一致。", 409)
    existing_records = archived_records(root, namespace)
    if name in existing_records and existing_records[name] != value:
        raise WorkspaceError("归档中存在冲突回执，请核实后继续。", 409)
    target = _summary_path(root, namespace, month)
    items: dict[str, dict[str, Any]] = {}
    if target.exists():
        items = _read_summary(target, namespace)
    entry = {"sha256": hashlib.sha256(_canonical(value)).hexdigest(), "value": value}
    prior = items.get(name)
    if prior is not None and prior != entry:
        raise WorkspaceError("活动回执与归档副本冲突，请核实后继续。", 409)
    items[name] = entry
    atomic_write(
        target,
        _canonical(
            {
                "schema": "workspace-month-v1",
                "namespace": namespace,
                "month": month,
                "items": items,
            }
        ),
    )
    if active_path.exists():
        active = read_active_or_archived(root, active_path, namespace, name)
        if active != value:
            raise WorkspaceError("活动回执在归档时发生变化，请重试。", 409)
        atomic_delete(active_path)


def archive_completed_json(
    root: Path,
    active_path: Path,
    *,
    namespace: str,
    name: str,
    now: datetime,
    terminal_states: set[str],
) -> bool:
    """Archive one timestamped terminal JSON record into its finish month.

    Legacy receipts without ``finished_at`` remain active and readable; the
    archive process never invents a completion month for them. Future-dated
    records remain active until their finish month.
    """
    if not active_path.exists():
        return False
    try:
        value = json.loads(active_path.read_bytes())
        if not isinstance(value, dict):
            raise ValueError("not a JSON object")
        finished_at = value.get("finished_at")
        state = value.get("state")
        if not isinstance(finished_at, str) or state not in terminal_states:
            return False
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        month = finished.strftime("%Y-%m")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise WorkspaceError("业务回执损坏，请核实后继续。", 409) from exc
    if month > now.strftime("%Y-%m"):
        return False
    archive_one(root, active_path, namespace, name, value, month)
    return True


def archive_completed_transactions(
    root: Path, now: datetime | None = None, *, locked: bool = False
) -> int:
    """Compress timestamped completed transaction families; unknown/running stay active."""
    from contextlib import nullcontext

    from summit_everything.workspace.transactions import workspace_lock

    current = now or datetime.now(UTC)
    transaction_root = root / ".summit-everything" / "transactions"
    if not transaction_root.exists():
        return 0
    archived = 0
    families = (
        "intake-*.json",
        "mutation-*.json",
        "feishu-import-*.json",
        "[0-9a-f]" * 64 + ".json",
    )
    guard = nullcontext() if locked else workspace_lock(root)
    with guard:
        paths = sorted({path for pattern in families for path in transaction_root.glob(pattern)})
        for path in paths:
            try:
                value = json.loads(path.read_bytes())
                if not isinstance(value, dict):
                    continue
                if path.name.startswith("intake-"):
                    valid = value.get("schema") == "intake-source-v1"
                    terminal = {"succeeded"}
                elif path.name.startswith("mutation-"):
                    valid = value.get("schema") == "workspace-mutation-v1"
                    terminal = {"succeeded"}
                elif path.name.startswith("feishu-import-"):
                    valid = isinstance(value.get("request_hash"), str) and "result" in value
                    terminal = {"completed"}
                else:
                    valid = (
                        isinstance(value.get("operation_id"), str)
                        and isinstance(value.get("request_hash"), str)
                        and isinstance(value.get("relative_path"), str)
                    )
                    terminal = {"succeeded"}
                if not valid:
                    continue
                if archive_completed_json(
                    root,
                    path,
                    namespace="transactions",
                    name=path.name,
                    now=current,
                    terminal_states=terminal,
                ):
                    archived += 1
            except WorkspaceError:
                raise
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise WorkspaceError("业务回执损坏，请核实后继续。", 409) from None
    return archived
