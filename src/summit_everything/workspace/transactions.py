"""Small, recoverable local file transactions for the active workspace."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class IntentConflict(ValueError):
    pass


@contextmanager
def workspace_lock(root: Path) -> Iterator[None]:
    lock_path = root / ".summit-everything" / "workspace.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as temp:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_delete(path: Path) -> None:
    path.unlink()
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def digest(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def write_intent(
    root: Path, operation_id: str, path: Path, expected: str | None, content: bytes
) -> str:
    """Apply one idempotent file replacement, with intent and result receipts."""
    safe_id = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    journal = root / ".summit-everything" / "transactions" / f"{safe_id}.json"
    request_hash = hashlib.sha256(content).hexdigest()
    current = path.read_bytes() if path.exists() else None
    if journal.exists():
        prior = json.loads(journal.read_text(encoding="utf-8"))
        if prior["request_hash"] != request_hash:
            raise IntentConflict("operation_id was already used for a different payload")
        if prior["state"] == "succeeded":
            result_hash = prior.get("result_hash")
            if isinstance(result_hash, str):
                return result_hash
            raise IntentConflict("completed operation is missing its result hash")
        if digest(current) not in {expected, request_hash}:
            raise IntentConflict("workspace changed while an interrupted operation was pending")
    elif digest(current) != expected:
        raise IntentConflict("workspace content changed since it was read")
    intent = {
        "operation_id": operation_id,
        "request_hash": request_hash,
        "relative_path": path.relative_to(root).as_posix(),
        "expected_hash": expected,
        "state": "running",
    }
    atomic_write(journal, json.dumps(intent, sort_keys=True).encode("utf-8"))
    if digest(current) != request_hash:
        atomic_write(path, content)
    result_hash = hashlib.sha256(content).hexdigest()
    intent.update(state="succeeded", result_hash=result_hash)
    atomic_write(journal, json.dumps(intent, sort_keys=True).encode("utf-8"))
    return result_hash
