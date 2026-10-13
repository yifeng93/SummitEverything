from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from summit_everything.workspace.archives import (
    archive_completed_json,
    archive_one,
    find_archived,
    read_active_or_archived,
)
from summit_everything.workspace.manifest import WorkspaceError
from summit_everything.workspace.state import AttemptLease, attempt_is_live


def test_finished_receipt_is_found_after_summary_then_active_delete(tmp_path: Path) -> None:
    active = tmp_path / ".summit-everything" / "transactions" / "mutation-x.json"
    active.parent.mkdir(parents=True)
    value = {"state": "succeeded", "finished_at": "2026-09-30T23:00:00+00:00", "result": "old"}
    active.write_text(json.dumps(value), encoding="utf-8")

    assert archive_completed_json(
        tmp_path,
        active,
        namespace="transactions",
        name=active.name,
        now=datetime(2026, 10, 12, tzinfo=UTC),
        terminal_states={"succeeded"},
    )

    assert not active.exists()
    assert find_archived(tmp_path, "transactions", active.name) == value
    assert read_active_or_archived(tmp_path, active, "transactions", active.name) == value


def test_legacy_undated_and_current_month_receipts_remain_active(tmp_path: Path) -> None:
    active = tmp_path / ".summit-everything" / "transactions" / "legacy.json"
    active.parent.mkdir(parents=True)
    active.write_text('{"state":"succeeded"}', encoding="utf-8")

    assert not archive_completed_json(
        tmp_path,
        active,
        namespace="transactions",
        name=active.name,
        now=datetime(2026, 10, 12, tzinfo=UTC),
        terminal_states={"succeeded"},
    )
    assert active.exists()


def test_corrupt_summary_blocks_lookup_without_overwrite(tmp_path: Path) -> None:
    summary = (
        tmp_path / ".summit-everything" / "archives" / "transactions" / "2026-09" / "summary.json"
    )
    summary.parent.mkdir(parents=True)
    summary.write_text('{"schema":"wrong"}', encoding="utf-8")
    active = tmp_path / ".summit-everything" / "transactions" / "same.json"
    active.parent.mkdir(parents=True)
    value = {"state": "succeeded", "finished_at": "2026-09-01T00:00:00+00:00"}
    active.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(WorkspaceError, match="归档摘要损坏"):
        archive_completed_json(
            tmp_path,
            active,
            namespace="transactions",
            name=active.name,
            now=datetime(2026, 10, 12, tzinfo=UTC),
            terminal_states={"succeeded"},
        )
    assert json.loads(active.read_text(encoding="utf-8")) == value


def test_conflicting_active_and_archived_copy_blocks_read(tmp_path: Path) -> None:
    from summit_everything.workspace.archives import archive_one

    active = tmp_path / ".summit-everything" / "transactions" / "same.json"
    value = {"state": "succeeded", "finished_at": "2026-09-01T00:00:00+00:00"}
    archive_one(tmp_path, active, "transactions", active.name, value, "2026-09")
    conflicting = {**value, "result": "changed"}
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps(conflicting), encoding="utf-8")

    with pytest.raises(WorkspaceError, match="冲突"):
        read_active_or_archived(tmp_path, active, "transactions", active.name)


def test_undated_archive_preserves_legacy_record_without_inventing_finish_month(
    tmp_path: Path,
) -> None:
    value = {"item_id": "legacy", "attempt_no": 0, "state": "completed"}
    active = tmp_path / ".summit-everything" / "intake" / "items" / "legacy.json"
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps(value), encoding="utf-8")

    archive_one(tmp_path, active, "intake-items", "legacy@0", value, "undated")

    bucket = (
        tmp_path / ".summit-everything" / "archives" / "intake-items" / "undated" / "summary.json"
    )
    assert not active.exists()
    assert json.loads(bucket.read_text(encoding="utf-8"))["month"] == "undated"
    assert find_archived(tmp_path, "intake-items", "legacy@0") == value


def test_dated_record_cannot_be_written_to_undated_bucket(tmp_path: Path) -> None:
    from summit_everything.workspace.archives import WorkspaceError as ArchiveError

    with pytest.raises(ArchiveError, match="undated"):
        archive_one(
            tmp_path,
            tmp_path / "missing.json",
            "transactions",
            "missing.json",
            {"state": "succeeded", "finished_at": "2026-09-01T00:00:00+00:00"},
            "undated",
        )


def test_dated_summary_rejects_record_without_finish_month(tmp_path: Path) -> None:
    from summit_everything.workspace.archives import find_archived

    summary = (
        tmp_path / ".summit-everything" / "archives" / "transactions" / "2026-09" / "summary.json"
    )
    summary.parent.mkdir(parents=True)
    value = {"state": "succeeded"}

    def canonical(data: object) -> bytes:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )

    summary.write_bytes(
        canonical(
            {
                "schema": "workspace-month-v1",
                "namespace": "transactions",
                "month": "2026-09",
                "items": {
                    "legacy.json": {
                        "sha256": hashlib.sha256(canonical(value)).hexdigest(),
                        "value": value,
                    }
                },
            }
        )
    )

    with pytest.raises(WorkspaceError, match="摘要损坏"):
        find_archived(tmp_path, "transactions", "legacy.json")


def test_attempt_lease_rejects_path_like_untrusted_ids(tmp_path: Path) -> None:
    outside = tmp_path / "outside.lock"
    with pytest.raises(ValueError, match="UUID"):
        AttemptLease(tmp_path / "workspace", f"../../{outside}")
    assert not outside.exists()
    assert not attempt_is_live(tmp_path / "workspace", f"../../{outside}")
