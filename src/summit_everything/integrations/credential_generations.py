"""Local, non-secret credential replacement generations for evidence binding."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import BinaryIO

from summit_everything.workspace.transactions import atomic_write


class CredentialGenerationError(RuntimeError):
    """The local credential generation record cannot be trusted or updated."""


class CredentialGenerationStore:
    """Track replacement of credentials without storing credential material."""

    schema_version = 1

    def __init__(self, profile: Path) -> None:
        self.path = profile / "credential-generations.json"
        self.lock_path = profile / "credential-generations.lock"

    def get(self, provider: str) -> int:
        with self._locked(read_only=True) as records:
            return records.get(provider, 0)

    def bump(self, provider: str) -> int:
        with self._locked() as records:
            records[provider] = records.get(provider, 0) + 1
            return records[provider]

    def _read(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_bytes())
            generations = value["generations"]
            if value.get("schema") != self.schema_version or not isinstance(generations, dict):
                raise ValueError
            if any(
                not isinstance(provider, str)
                or not provider
                or type(generation) is not int
                or generation < 0
                for provider, generation in generations.items()
            ):
                raise ValueError
            return generations
        except (OSError, ValueError, TypeError, KeyError):
            raise CredentialGenerationError("credential_generation_unavailable") from None

    def _write(self, records: dict[str, int]) -> None:
        atomic_write(
            self.path,
            json.dumps(
                {"schema": self.schema_version, "generations": records},
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
        )

    class _Lock:
        def __init__(self, store: CredentialGenerationStore, read_only: bool) -> None:
            self.store = store
            self.read_only = read_only
            self.stream: BinaryIO | None = None
            self.records: dict[str, int] = {}

        def __enter__(self) -> dict[str, int]:
            self.store.path.parent.mkdir(parents=True, exist_ok=True)
            self.stream = self.store.lock_path.open("a+b")
            try:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX)
                self.records = self.store._read()
                return self.records
            except BaseException:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                self.stream.close()
                self.stream = None
                raise

        def __exit__(self, *_exc: object) -> None:
            try:
                if not self.read_only:
                    self.store._write(self.records)
            finally:
                if self.stream is not None:
                    fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                    self.stream.close()

    def _locked(self, *, read_only: bool = False) -> _Lock:
        return self._Lock(self, read_only)
