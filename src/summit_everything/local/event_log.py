"""Small rotating diagnostics stored only in the current local profile."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock

_lock = Lock()
_loggers: dict[Path, logging.Logger] = {}
_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_EVENTS = {
    "intake_saved",
    "intake_job",
    "draft_confirmed",
    "index_update_failed",
    "assistant_failed",
}
_MAX_BYTES = 256 * 1024
_BACKUPS = 3
_REASON_MAX = 200
_REASON_FORBIDDEN = "sk-"
_STATES = {
    "pending",
    "running",
    "provider_calling",
    "completed",
    "failed",
    "cancelled",
    "unknown",
    "reviewing",
    "succeeded",
}


class _JsonLine(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(record.event, sort_keys=True, separators=(",", ":"))  # type: ignore[attr-defined]


def _logger(profile: Path) -> logging.Logger:
    directory = profile.resolve()
    with _lock:
        existing = _loggers.get(directory)
        if existing is not None:
            return existing
        directory.mkdir(parents=True, exist_ok=True)
        logger = logging.Logger(f"summit.profile-events.{len(_loggers)}", logging.INFO)
        logger.propagate = False
        handler = RotatingFileHandler(
            directory / "diagnostics.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUPS,
            encoding="utf-8",
        )
        handler.setFormatter(_JsonLine())
        logger.addHandler(handler)
        _loggers[directory] = logger
        return logger


def _validated_reason(value: str) -> str:
    """A bounded, single-line, credential-free failure reason.

    Callers pass an already-sanitized sentence; this is the last line of defence
    so a diagnostic file can never gain a raw credential or a multi-line dump.
    """
    if not 1 <= len(value) <= _REASON_MAX:
        raise ValueError("invalid diagnostic reason")
    if any(ord(character) < 32 for character in value):
        raise ValueError("invalid diagnostic reason")
    if _REASON_FORBIDDEN in value:
        raise ValueError("invalid diagnostic reason")
    return value


def profile_event(
    profile: Path,
    event: str,
    *,
    record_id: str | None = None,
    state: str | None = None,
    count: int | None = None,
    reason: str | None = None,
) -> None:
    """Write allowlisted status metadata and an optional sanitized reason.

    Free-form provider or exception text is never accepted: reasons are bounded,
    single-line and rejected outright if they still look like a credential.
    """
    if event not in _EVENTS:
        raise ValueError("unsupported profile event")
    payload: dict[str, str | int] = {
        "at": datetime.now(UTC).isoformat(),
        "event": event,
    }
    if record_id is not None:
        if not _ID.fullmatch(record_id):
            raise ValueError("invalid diagnostic record ID")
        payload["record_id"] = record_id
    if state is not None:
        if state not in _STATES:
            raise ValueError("invalid diagnostic state")
        payload["state"] = state
    if count is not None:
        if count < 0:
            raise ValueError("invalid diagnostic count")
        payload["count"] = count
    if reason is not None:
        payload["reason"] = _validated_reason(reason)
    logger = _logger(profile)
    record = logging.LogRecord(logger.name, logging.INFO, "", 0, "", (), None)
    record.event = payload
    logger.handle(record)
