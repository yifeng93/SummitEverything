"""Non-secret first-use wizard progress, stored in the active local profile.

The wizard used to keep its step only in browser ``localStorage``. The packaged
application runs the WebUI in a WKWebView with non-persistent storage, so that
copy disappeared on every restart and the user was pushed back into step 2 after
already having finished the first-use configuration.

This store is the durable single source of truth. It is deliberately narrow:

* the document holds only ``step`` / ``completed`` / ``open`` — no credential,
  path or free-form field can be written or read back;
* the file lives inside the workspace's own local profile directory, so two
  workspaces (or two profiles) can never observe each other's progress;
* writes replace the file atomically under an exclusive lock, so a crash or two
  concurrent writers can never leave a truncated document behind.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, field_validator

FirstUseStep = Literal[2, 3, 4, 5]


class FirstUseProgressError(RuntimeError):
    """The stored progress cannot be read or written."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FirstUseProgress(BaseModel):
    """Exactly the three non-secret fields the wizard is allowed to persist.

    ``extra="forbid"`` plus strict booleans keep the wire contract honest: a
    caller that tries to smuggle in a credential, a path or a raw JSON blob is
    rejected instead of having it silently stored on disk.

    ``step`` is a real integer or nothing. ``Literal`` alone would let Pydantic's
    lax mode normalise an integral JSON float (``3.0``) into ``3``, so an
    out-of-contract payload would look accepted; the validator below closes that
    (independent QA finding D-4).
    """

    model_config = ConfigDict(extra="forbid")

    step: FirstUseStep
    completed: StrictBool
    open: StrictBool

    @field_validator("step", mode="before")
    @classmethod
    def integer_step(cls, value: object) -> object:
        # ``bool`` is an ``int`` subclass, so it is excluded explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("step must be an integer")
        return value


class FirstUseProgressStore:
    """Atomic reader/writer for one profile+workspace progress document."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> FirstUseProgress | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_bytes())
        except (OSError, ValueError) as exc:
            raise FirstUseProgressError("progress_unavailable") from exc
        try:
            return FirstUseProgress.model_validate(raw)
        except ValueError as exc:
            # A corrupted or hand-edited document fails closed rather than
            # being quietly reinterpreted as "no progress yet".
            raise FirstUseProgressError("progress_unavailable") from exc

    def write(self, progress: FirstUseProgress) -> FirstUseProgress:
        payload = progress.model_dump(mode="json")
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a+b") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    self._replace(payload)
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise FirstUseProgressError("progress_unavailable") from exc
        return progress

    def _replace(self, payload: dict[str, object]) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".first-use-progress-", dir=self.path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(json.dumps(payload, ensure_ascii=False, indent=2).encode())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
