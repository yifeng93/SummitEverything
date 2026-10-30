"""Explicitly prepared, machine-local retrieval model files.

The model source and every byte are pinned in code. Reading status is local-only;
the only method that opens an HTTP connection is ``start_prepare`` after an
explicit authenticated API action.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import httpx

from summit_everything.integrations.embedding import LocalBgeEmbedding

MODEL_REPOSITORY = "Qdrant/bge-small-zh-v1.5"
MODEL_REVISION = "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_DIMENSIONS = 512
MODEL_TOKEN_LIMIT = 512
MODEL_DOWNLOAD_SIZE = 95_330_972
MODEL_FILES: dict[str, tuple[int, str]] = {
    "config.json": (
        739,
        "9088751d39abbf86ec3d19ffca92ad62ad19075f7e59712e6c71217fa125d1d3",
    ),
    "model_optimized.onnx": (
        94_781_076,
        "1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38",
    ),
    "special_tokens_map.json": (
        125,
        "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
    ),
    "tokenizer.json": (
        439_125,
        "48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26",
    ),
    "tokenizer_config.json": (
        367,
        "e6f3b96db926a37d4039995fbf5ad17de158dfb8f6343d607e4dbaad18d75f5a",
    ),
    "vocab.txt": (
        109_540,
        "45bbac6b341c319adc98a532532882e91a9cefc0329aa57bac9ae761c27b291c",
    ),
}

_ALLOWED_REDIRECT_SUFFIXES = (".huggingface.co", ".hf.co")
_INITIAL_HOST = "huggingface.co"
_REDIRECT_LIMIT = 4
_CHUNK_BYTES = 256 * 1024
_PREPARE_TIMEOUT_SECONDS = 30 * 60
_FILE_TIMEOUT_SECONDS = 10 * 60


class LocalModelError(RuntimeError):
    """A safe model preparation or local-file validation error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def _safe_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _verified_model_dir(path: Path) -> bool:
    if not path.is_dir() or path.is_symlink():
        return False
    for name, (expected_size, expected_hash) in MODEL_FILES.items():
        candidate = path / name
        try:
            if not _safe_file(candidate) or candidate.stat().st_size != expected_size:
                return False
            if _sha256(candidate) != expected_hash:
                return False
        except OSError:
            return False
    return True


def _redirect_host_allowed(url: str) -> bool:
    parts = urlsplit(url)
    hostname = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and not parts.username
        and not parts.password
        and not parts.port
        and (hostname == _INITIAL_HOST or hostname.endswith(_ALLOWED_REDIRECT_SUFFIXES))
    )


def _download_file(
    url: str,
    destination: Path,
    *,
    expected_size: int,
    progress: Callable[[int], None],
    deadline_monotonic: float,
) -> None:
    current = url
    headers = {"Accept-Encoding": "identity", "User-Agent": "SummitEverything/1"}
    with httpx.Client(
        trust_env=True, timeout=httpx.Timeout(60.0), follow_redirects=False
    ) as client:
        for redirect_count in range(_REDIRECT_LIMIT + 1):
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                raise LocalModelError("model_download_timeout")
            if not _redirect_host_allowed(current):
                raise LocalModelError("model_source_rejected")
            timeout = httpx.Timeout(
                connect=min(10.0, remaining),
                read=min(60.0, remaining),
                write=min(10.0, remaining),
                pool=min(10.0, remaining),
            )
            with client.stream("GET", current, headers=headers, timeout=timeout) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or redirect_count >= _REDIRECT_LIMIT:
                        raise LocalModelError("model_download_failed")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise LocalModelError("model_download_failed")
                content_length = response.headers.get("content-length")
                if content_length is not None and content_length != str(expected_size):
                    raise LocalModelError("model_download_failed")
                written = 0
                with destination.open("xb") as handle:
                    for block in response.iter_bytes(_CHUNK_BYTES):
                        if time.monotonic() >= deadline_monotonic:
                            raise LocalModelError("model_download_timeout")
                        if not block:
                            continue
                        written += len(block)
                        if written > expected_size:
                            raise LocalModelError("model_download_failed")
                        handle.write(block)
                        progress(len(block))
                    handle.flush()
                    os.fsync(handle.fileno())
                if written != expected_size:
                    raise LocalModelError("model_download_failed")
                return
    raise LocalModelError("model_download_failed")


class LocalRetrievalModelStore:
    """Owns a revisioned model directory outside the workspace and Git tree."""

    def __init__(
        self,
        root: Path,
        *,
        model_directory: Path | None = None,
        downloader: Callable[..., None] = _download_file,
        prepare_timeout_seconds: float = _PREPARE_TIMEOUT_SECONDS,
        file_timeout_seconds: float = _FILE_TIMEOUT_SECONDS,
    ) -> None:
        self.root = root.resolve()
        self.model_directory = model_directory.resolve() if model_directory else None
        self.revision_dir = self.root / "bge-small-zh-v1.5" / MODEL_REVISION
        self._downloader = downloader
        self._prepare_timeout_seconds = prepare_timeout_seconds
        self._file_timeout_seconds = file_timeout_seconds
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._embedding: LocalBgeEmbedding | None = None
        self._progress: dict[str, Any] = {}
        self._model_factory: Callable[[Path], LocalBgeEmbedding] | None = None
        self._verification_signature: tuple[tuple[str, int, int, int], ...] | None = None
        self._verification_result = False

    def _target(self) -> Path:
        return self.model_directory or self.revision_dir

    def _verified_target(self) -> bool:
        target = self._target()
        try:
            signature = tuple(
                (
                    name,
                    (target / name).stat().st_size,
                    (target / name).stat().st_mtime_ns,
                    (target / name).stat().st_ino,
                )
                for name in sorted(MODEL_FILES)
                if _safe_file(target / name)
            )
        except OSError:
            signature = ()
        if len(signature) != len(MODEL_FILES):
            return False
        with self._lock:
            if signature == self._verification_signature:
                return self._verification_result
        verified = _verified_model_dir(target)
        with self._lock:
            self._verification_signature = signature
            self._verification_result = verified
        return verified

    def status(self) -> dict[str, object]:
        """Read local status without importing FastEmbed or accessing network.

        Complete files are SHA-256 checked on first observation and again if their
        size, mtime, or inode changes; unchanged verified files use the cached result.
        """
        with self._lock:
            progress = dict(self._progress)
        target = self._target()
        files_present = all(
            _safe_file(target / name) and (target / name).stat().st_size == expected_size
            for name, (expected_size, _digest) in MODEL_FILES.items()
            if (target / name).exists()
        )
        complete_files = all((target / name).exists() for name in MODEL_FILES)
        if complete_files and files_present and self._verified_target():
            state = "ready"
        elif progress.get("state") == "preparing":
            state = "preparing"
        elif progress.get("state") == "failed":
            state = "failed"
        elif any((target / name).exists() for name in MODEL_FILES):
            state = "incomplete"
        else:
            state = "not_prepared"
        return {
            "model": MODEL_NAME,
            "revision": MODEL_REVISION,
            "dimensions": MODEL_DIMENSIONS,
            "token_limit": MODEL_TOKEN_LIMIT,
            "download_size_bytes": MODEL_DOWNLOAD_SIZE,
            "state": state,
            "downloaded_bytes": progress.get("downloaded_bytes", 0),
            "progress_percent": progress.get("progress_percent", 0),
            "error_code": progress.get("error_code") if state in {"failed", "incomplete"} else None,
        }

    def verify_model_directory(self) -> Path:
        target = self._target()
        if not self._verified_target():
            raise LocalModelError("local_model_not_ready")
        return target

    def start_prepare(self) -> dict[str, object]:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self.status()
            current = self.status()
            if current["state"] == "ready" and _verified_model_dir(self._target()):
                return current
            if self.model_directory is not None:
                raise LocalModelError("model_directory_read_only")
            self._progress = {
                "state": "preparing",
                "downloaded_bytes": 0,
                "progress_percent": 0,
                "error_code": None,
                "job_id": str(uuid4()),
            }
            self._thread = threading.Thread(
                target=self._prepare, name="local-model-prepare", daemon=True
            )
            self._thread.start()
            return self.status()

    def _write_marker(self, path: Path) -> None:
        marker = {
            "repository": MODEL_REPOSITORY,
            "revision": MODEL_REVISION,
            "files": {
                name: {"size": size, "sha256": digest}
                for name, (size, digest) in MODEL_FILES.items()
            },
        }
        (path / ".summit-model.json").write_text(
            json.dumps(marker, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )

    def _prepare(self) -> None:
        deadline = time.monotonic() + self._prepare_timeout_seconds
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.revision_dir.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.root / ".bge-small-zh-v1.5.lock"
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                import fcntl

                while True:
                    if time.monotonic() >= deadline:
                        raise LocalModelError("model_prepare_timeout")
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        time.sleep(min(0.1, deadline - time.monotonic()))
                self._prepare_locked(deadline)
            finally:
                os.close(descriptor)
        except LocalModelError as exc:
            self._finish_error(exc.code)
        except httpx.TimeoutException:
            self._finish_error("model_download_timeout")
        except Exception:
            self._finish_error("model_download_failed")

    def _prepare_locked(self, prepare_deadline: float) -> None:
        if _verified_model_dir(self.revision_dir):
            with self._lock:
                self._progress.update(
                    state="ready", downloaded_bytes=MODEL_DOWNLOAD_SIZE, progress_percent=100
                )
            return

        stage = self.revision_dir.parent / f".partial-{uuid4()}"
        stage.mkdir(mode=0o700)
        try:
            downloaded = 0

            def on_progress(amount: int) -> None:
                nonlocal downloaded
                downloaded += amount
                with self._lock:
                    self._progress.update(
                        downloaded_bytes=downloaded,
                        progress_percent=min(99, downloaded * 100 // MODEL_DOWNLOAD_SIZE),
                    )

            for filename, (expected_size, expected_hash) in MODEL_FILES.items():
                now = time.monotonic()
                if now >= prepare_deadline:
                    raise LocalModelError("model_prepare_timeout")
                url = (
                    f"https://{_INITIAL_HOST}/{MODEL_REPOSITORY}/resolve/"
                    f"{MODEL_REVISION}/{filename}"
                )
                path = stage / filename
                file_deadline = min(prepare_deadline, now + self._file_timeout_seconds)
                self._downloader(
                    url,
                    path,
                    expected_size=expected_size,
                    progress=on_progress,
                    deadline_monotonic=file_deadline,
                )
                if time.monotonic() >= prepare_deadline:
                    raise LocalModelError("model_prepare_timeout")
                if time.monotonic() >= file_deadline:
                    raise LocalModelError("model_download_timeout")
                if _sha256(path) != expected_hash:
                    raise LocalModelError("model_download_hash_mismatch")
            self._write_marker(stage)
            if not _verified_model_dir(stage):
                raise LocalModelError("model_download_hash_mismatch")
            backup: Path | None = None
            if self.revision_dir.exists():
                backup = self.revision_dir.parent / f".incomplete-{uuid4()}"
                os.replace(self.revision_dir, backup)
            try:
                os.replace(stage, self.revision_dir)
            except Exception:
                if backup is not None and backup.exists() and not self.revision_dir.exists():
                    os.replace(backup, self.revision_dir)
                raise
            with self._lock:
                self._progress.update(
                    state="ready", downloaded_bytes=MODEL_DOWNLOAD_SIZE, progress_percent=100
                )
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    def _finish_error(self, code: str) -> None:
        with self._lock:
            self._progress.update(state="failed", error_code=code)

    def wait_for_prepare(self, timeout: float = 30.0) -> dict[str, object]:
        """Test/support hook; production UI polls status instead of blocking."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.status()

    def embedding(
        self, *, model_factory: Callable[[Path], LocalBgeEmbedding] | None = None
    ) -> LocalBgeEmbedding:
        with self._lock:
            if self._embedding is not None:
                return self._embedding
            factory = model_factory or self._model_factory
        directory = self.verify_model_directory()
        if factory is None:
            provider = LocalBgeEmbedding(directory)
        else:
            provider = factory(directory)
        with self._lock:
            if self._embedding is None:
                self._embedding = provider
            return self._embedding

    def set_model_factory_for_tests(self, factory: Callable[[Path], LocalBgeEmbedding]) -> None:
        self._model_factory = factory
