from __future__ import annotations

import json
from pathlib import Path

import pytest

from summit_everything.local import event_log


def test_profile_event_log_is_allowlisted_local_and_rotates(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / "profile"
    monkeypatch.setattr(event_log, "_MAX_BYTES", 300)

    for index in range(30):
        event_log.profile_event(
            profile,
            "intake_job",
            record_id=f"job_{index}",
            state="unknown" if index == 29 else "completed",
            count=index,
        )

    files = list(profile.glob("diagnostics.log*"))
    assert 1 < len(files) <= event_log._BACKUPS + 1
    records = [json.loads(line) for path in files for line in path.read_text().splitlines()]
    assert records
    assert any(record["state"] == "unknown" for record in records)
    assert all(
        set(record).issubset({"at", "event", "record_id", "state", "count", "reason"})
        for record in records
    )
    assert str(tmp_path) not in "".join(path.read_text() for path in files)


def test_profile_event_log_rejects_unbounded_payload_fields(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        event_log.profile_event(tmp_path / "profile", "intake_job", prompt="private source")  # type: ignore[call-arg]


def read_events(profile: Path) -> list[dict[str, object]]:
    lines = (profile / "diagnostics.log").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_a_sanitized_failure_reason_is_recorded(tmp_path: Path) -> None:
    reason = "模型服务返回错误：InsufficientBalance — Insufficient Balance"
    event_log.profile_event(tmp_path, "assistant_failed", state="failed", reason=reason)
    events = read_events(tmp_path)
    assert events[-1]["event"] == "assistant_failed"
    assert events[-1]["state"] == "failed"
    assert events[-1]["reason"] == reason


@pytest.mark.parametrize(
    "reason",
    [
        "line one\nline two",
        "leaked sk-abcdefghijklmnop",
        "x" * 201,
        "",
    ],
)
def test_unsafe_failure_reasons_are_rejected(tmp_path: Path, reason: str) -> None:
    with pytest.raises(ValueError):
        event_log.profile_event(tmp_path, "index_update_failed", state="failed", reason=reason)


def test_the_reason_is_optional(tmp_path: Path) -> None:
    event_log.profile_event(tmp_path, "intake_saved", record_id="record-1", state="pending")
    assert "reason" not in read_events(tmp_path)[-1]
