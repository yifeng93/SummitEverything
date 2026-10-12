from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from summit_everything.workspace import archives
from summit_everything.workspace.manifest import WorkspaceError


def completed() -> dict[str, object]:
    return {"state": "succeeded", "finished_at": "2026-09-30T23:00:00+00:00", "value": "synthetic"}


with TemporaryDirectory(prefix="m3-p3-archive-matrix-") as temp:
    root = Path(temp) / "workspace"
    active = root / ".summit-everything" / "transactions" / "same.json"
    active.parent.mkdir(parents=True)
    value = completed()

    # Archive is persisted before active deletion; a failed summary write leaves active intact.
    active.write_text(json.dumps(value), encoding="utf-8")
    real_atomic_write = archives.atomic_write
    def fail_summary(path: Path, content: bytes) -> None:
        if path.name == "summary.json":
            raise OSError("synthetic archive summary write failure")
        real_atomic_write(path, content)
    archives.atomic_write = fail_summary
    try:
        archives.archive_completed_json(root, active, namespace="transactions", name=active.name,
                                        now=datetime(2026, 10, 12, tzinfo=UTC), terminal_states={"succeeded"})
        raise AssertionError("summary failure injection did not fail")
    except OSError as exc:
        assert "synthetic" in str(exc)
    finally:
        archives.atomic_write = real_atomic_write
    assert active.exists() and not list((root / ".summit-everything" / "archives").glob("**/summary.json"))
    write_failure_keeps_active = True

    # Simulate crash duplicate: byte-equivalent active and summary copies are readable.
    archives.archive_one(root, active, "transactions", active.name, value, "2026-09")
    duplicate_restored = archives.read_active_or_archived(root, active, "transactions", active.name) == value

    # Invalid month summary and unexpected copied file fail closed; source active stays present.
    invalid_root = root / ".summit-everything" / "archives" / "transactions" / "2026-13"
    invalid_root.mkdir(parents=True)
    (invalid_root / "summary.json").write_text(json.dumps({"schema": "workspace-month-v1", "namespace": "transactions", "month": "2026-13", "items": {}}), encoding="utf-8")
    try:
        archives.find_archived(root, "transactions", "other.json")
        raise AssertionError("invalid month was accepted")
    except WorkspaceError:
        invalid_month_rejected = True
    (invalid_root / "summary.json").unlink()
    invalid_root.rmdir()

    active.write_text(json.dumps(value), encoding="utf-8")
    bad = root / ".summit-everything" / "archives" / "transactions" / "2026-09" / "unrecognized-copy.json"
    bad.write_text("synthetic", encoding="utf-8")
    try:
        archives.archive_completed_json(root, active, namespace="transactions", name=active.name,
                                        now=datetime(2026, 10, 12, tzinfo=UTC), terminal_states={"succeeded"})
        raise AssertionError("unexpected copy was accepted")
    except WorkspaceError:
        unexpected_copy_rejected = True
    assert active.exists()
    print(json.dumps({"summary_write_failure_keeps_active": write_failure_keeps_active,
                      "identical_active_archive_duplicate_readable": duplicate_restored,
                      "invalid_month_rejected": invalid_month_rejected,
                      "unexpected_copy_rejected_and_active_preserved": unexpected_copy_rejected}, indent=2))
    assert write_failure_keeps_active and duplicate_restored and invalid_month_rejected and unexpected_copy_rejected
