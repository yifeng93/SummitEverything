"""QA harness (item 9): residual boundary behaviour of the rewritten clean_reason.

These pin the *observed* contract so the residual risks are reproducible evidence
rather than prose. Every assertion here documents measured behaviour at f40bc39.
"""

from __future__ import annotations

import json

import pytest

from summit_everything.integrations.http_boundary import sanitize_provider_text
from summit_everything.local import event_log
from summit_everything.local.event_log import clean_reason

RAW_KEY = "sk-abcdefghijklmnop"


# --------------------------------------------- whitespace / line-separator set


@pytest.mark.parametrize(
    "character",
    ["\n", "\r", "\t", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f", "\x85", "\xa0", "\u1680",
     "\u2000", "\u2003", "\u2028", "\u2029", "\u3000"],  # type: ignore[arg-type]
)
def test_all_unicode_line_separators_are_collapsed(character: str) -> None:
    """No separator that a reader would treat as a line break survives."""
    assert clean_reason(f"a{character}b").count(character) == 0
    assert "\n" not in clean_reason(f"a{character}b")


# ------------------------------------------------- RESIDUAL: raw control chars


@pytest.mark.parametrize("character", ["\x00", "\x01", "\x07", "\x08", "\x0e", "\x1b", "\x7f"])
def test_residual_non_whitespace_control_characters_survive(character: str) -> None:
    """RESIDUAL (low): the old rule rejected every ``ord < 32`` character.

    The new rule only folds characters that ``str.split()`` treats as whitespace,
    so NUL, BEL, ESC/ANSI and DEL now survive into the reason. This is a
    defence-in-depth reduction, not a credential leak: ``json.dumps`` still emits
    a single valid JSON line. Measured, not assumed.
    """
    cleaned = clean_reason(f"before{character}after")
    assert character in cleaned, f"{character!r} was stripped (behaviour changed)"


def test_residual_ansi_escape_reaches_the_file(tmp_path) -> None:
    """The concrete consequence: a terminal escape sequence lands in the log."""
    event_log.profile_event(
        tmp_path, "assistant_failed", state="failed", reason="\x1b[31mred\x1b[0m"
    )
    line = (tmp_path / "diagnostics.log").read_text(encoding="utf-8").strip()
    assert len(line.splitlines()) == 1
    payload = json.loads(line)
    assert "\x1b" in payload["reason"]
    assert "\x1b" not in line, "json.dumps must escape the raw ESC byte"


# ------------------------------------------- masking strength vs the boundary


@pytest.mark.parametrize(
    "value",
    [
        RAW_KEY,
        f"leaked {RAW_KEY} now",
        f"a\n{RAW_KEY}\nb",
        f"{RAW_KEY}{RAW_KEY}",
        "sk-abcdefgh",
        "sk-abcdefghijklmnopqrstuvwxyz0123456789",
    ],
)
def test_masking_is_at_least_as_strong_as_the_http_boundary(value: str) -> None:
    """The log rule must never be weaker than the primary sanitizer."""
    logged = clean_reason(value)
    boundary = sanitize_provider_text(value) or ""
    assert logged == boundary[:200], (logged, boundary)


def test_masking_is_idempotent() -> None:
    for value in [RAW_KEY, f"leaked {RAW_KEY}", "sk-***", "\x1b[31m" + RAW_KEY]:
        once = clean_reason(value)
        assert clean_reason(once) == once


@pytest.mark.parametrize(
    ("value", "note"),
    [
        ("SK-ABCDEFGHIJKLMNOP", "uppercase prefix: same case-sensitivity as the boundary"),
        ("sk-abc", "shorter than the 8-char shape: never a real key"),
        ("sk-abcdefg", "7 chars: below the shared {8,} threshold"),
        ("sk-abcdefg\u200bijklmnop", "zero-width space splits the shape (boundary does too)"),
        ("sk-abcdefg\u202eijklmnop", "RTL override splits the shape (boundary does too)"),
    ],
)
def test_residual_shapes_that_are_not_masked_match_the_boundary(value: str, note: str) -> None:
    """RESIDUAL (informational): identical to ``_SECRET_LIKE`` in http_boundary.

    Nothing here is introduced or worsened by f40bc39: the same regex already
    guards the primary sanitizer. Recorded so the shared gap is not mistaken for
    a new one.
    """
    assert clean_reason(value) == (sanitize_provider_text(value) or "")
    assert "***" not in clean_reason(value) or note.startswith("upper")


# --------------------------------------------------------- extreme inputs


def test_very_long_inputs_are_truncated_without_error() -> None:
    assert len(clean_reason("z" * 5_000_000)) == 200
    assert len(clean_reason("日" * 200_000)) == 200
    assert len(clean_reason("\U0001f600" * 200_000)) == 200


def test_length_ceiling_is_code_points_not_bytes() -> None:
    """A 200-astral-char reason is ~800 UTF-8 bytes; the ceiling is characters."""
    cleaned = clean_reason("\U0001f600" * 300)
    assert len(cleaned) == 200
    assert len(cleaned.encode("utf-8")) == 800


def test_a_lone_surrogate_is_written_without_raising(tmp_path) -> None:
    """Unreachable from a real provider, but must not crash the log writer."""
    event_log.profile_event(
        tmp_path, "assistant_failed", state="failed", reason="a\ud800b"
    )
    text = (tmp_path / "diagnostics.log").read_text(encoding="utf-8").strip()
    assert json.loads(text)["reason"] == "a\ud800b"


def test_limit_zero_yields_empty_but_is_unreachable_from_profile_event(tmp_path) -> None:
    """``limit`` is only reachable via the default 200 through ``profile_event``."""
    assert clean_reason("hello", limit=0) == ""
    import inspect

    assert inspect.signature(event_log.profile_event).parameters["reason"].default is None
    event_log.profile_event(tmp_path, "assistant_failed", state="failed", reason="hello")
    assert json.loads((tmp_path / "diagnostics.log").read_text(encoding="utf-8"))["reason"] == (
        "hello"
    )


# ------------------------------- RESIDUAL: logging-layer swallow (not new here)


def test_residual_logging_handler_swallows_a_broken_stream(tmp_path, capsys) -> None:
    """RESIDUAL (bounded): ``logging.Handler.handleError`` eats the write error.

    The D1 fix guarantees no *validation* failure drops an event. A broken
    handler stream is different: ``RotatingFileHandler.emit`` catches everything
    and reports through ``handleError``, so ``profile_event`` returns normally and
    ``record_diagnostic`` never reaches its ``except OSError``. This behaviour is
    unchanged by f40bc39 (it lives in the stdlib) but it bounds the "never
    silently dropped" claim and must not be read as fixed.
    """
    profile = tmp_path / "profile"
    event_log.profile_event(profile, "assistant_failed", state="failed", reason="first")
    log = profile / "diagnostics.log"
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1

    event_log._logger(profile).handlers[0].stream.close()
    event_log.profile_event(profile, "assistant_failed", state="failed", reason="second")

    assert len(log.read_text(encoding="utf-8").splitlines()) == 1, "second event DID land"
    assert "Logging error" in capsys.readouterr().err
