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
_EVENTS = {"intake_saved", "intake_job", "draft_confirmed"}
_MAX_BYTES = 256 * 1024
_BACKUPS = 3
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


def profile_event(
    profile: Path,
    event: str,
    *,
    record_id: str | None = None,
    state: str | None = None,
    count: int | None = None,
) -> None:
    """Write allowlisted status metadata; never accept messages or source text."""
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
    logger = _logger(profile)
    record = logging.LogRecord(logger.name, logging.INFO, "", 0, "", (), None)
    record.event = payload
    logger.handle(record)
