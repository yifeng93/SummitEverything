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
    ("reason", "expected"),
    [
        ("line one\nline two", "line one line two"),
        # An already-masked credential contains the literal "sk-" and must be
        # accepted: rejecting it used to drop the whole event.
        (
            "Authentication Fails, Your api key: sk-*** is invalid",
            "Authentication Fails, Your api key: sk-*** is invalid",
        ),
        ("leaked sk-abcdefghijklmnop now", "leaked sk-*** now"),
        ("y" * 258, "y" * 200),
        # Control bytes are dropped instead of carried into the file; the rule
        # this replaces refused them outright, which lost the event.
        ("escape \x1b[31mred\x1b[0m and \x07bell", "escape [31mred [0m and bell"),
        ("nul\x00byte", "nul byte"),
        ("delete\x7fchar", "delete char"),
    ],
)
def test_reasons_are_cleaned_rather_than_dropped(
    tmp_path: Path, reason: str, expected: str
) -> None:
    event_log.profile_event(tmp_path, "index_update_failed", state="failed", reason=reason)
    events = read_events(tmp_path)
    assert events[-1]["event"] == "index_update_failed"
    assert events[-1]["reason"] == expected
    assert len(str(events[-1]["reason"])) <= 200


def test_an_empty_or_non_string_reason_is_still_refused(tmp_path: Path) -> None:
    for reason in ("", "   ", 5):
        with pytest.raises(ValueError):
            event_log.profile_event(
                tmp_path,
                "index_update_failed",
                state="failed",
                reason=reason,  # type: ignore[arg-type]
            )


def test_an_absent_reason_is_allowed(tmp_path: Path) -> None:
    # ``None`` means "no reason", which is an allowed optional field; a non-string
    # value is refused so the payload keeps its declared type.
    event_log.profile_event(tmp_path, "assistant_failed", state="failed")
    assert "reason" not in read_events(tmp_path)[-1]


def test_an_unmasked_credential_never_reaches_the_file(tmp_path: Path) -> None:
    secret = "sk-abcdefghijklmnop"
    event_log.profile_event(
        tmp_path,
        "assistant_failed",
        state="failed",
        reason=f"Authentication Fails, Your api key: {secret} is invalid",
    )
    text = (tmp_path / "diagnostics.log").read_text(encoding="utf-8")
    assert secret not in text
    assert "sk-***" in text


def test_the_reason_is_optional(tmp_path: Path) -> None:
    event_log.profile_event(tmp_path, "intake_saved", record_id="record-1", state="pending")
    assert "reason" not in read_events(tmp_path)[-1]
