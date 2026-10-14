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
# Same shape the HTTP boundary masks: a credential that is still readable. An
# already-masked ``sk-***`` does not match and must be accepted as-is.
_CREDENTIAL_SHAPE = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_MASKED_CREDENTIAL = "sk-***"
FALLBACK_REASON = "unrecorded"
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


def clean_reason(value: object, *, limit: int = _REASON_MAX) -> str:
    """Mask, flatten and truncate a failure reason; never reject readable text.

    Cleaning replaces the old "reject anything suspicious" rule, which silently
    dropped whole events: an already-masked ``sk-***`` contains the literal
    ``sk-`` and a provider message can exceed the limit, so both used to lose the
    ``assistant_failed`` / ``index_update_failed`` event entirely. Only a
    non-string or an empty result is refused, and callers then fall back to a
    minimal safe value so the event itself still lands.
    """
    if not isinstance(value, str):
        return ""
    collapsed = " ".join(value.split())
    if not collapsed:
        return ""
    return _CREDENTIAL_SHAPE.sub(_MASKED_CREDENTIAL, collapsed)[:limit]


def profile_event(
    profile: Path,
    event: str,
    *,
    record_id: str | None = None,
    state: str | None = None,
    count: int | None = None,
    reason: str | None = None,
) -> None:
    """Write allowlisted status metadata and an optional cleaned reason.

    A reason is masked, flattened and truncated rather than rejected, so an event
    is never lost to an over-long message or an already-masked credential. Only a
    non-string or empty reason raises; callers fall back to a safe value.
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
        cleaned = clean_reason(reason)
        if not cleaned:
            raise ValueError("invalid diagnostic reason")
        payload["reason"] = cleaned
    logger = _logger(profile)
    record = logging.LogRecord(logger.name, logging.INFO, "", 0, "", (), None)
    record.event = payload
    logger.handle(record)
