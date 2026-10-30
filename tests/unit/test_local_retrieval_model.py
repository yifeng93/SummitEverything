from __future__ import annotations

import time
from pathlib import Path

from summit_everything.local.retrieval_model import LocalModelError, LocalRetrievalModelStore


def test_model_status_is_read_only_and_reports_missing_model(tmp_path: Path) -> None:
    store = LocalRetrievalModelStore(tmp_path / "profile" / "retrieval-models")

    status = store.status()

    assert status["state"] == "not_prepared"
    assert not store.root.exists()
    assert status["model"] == "BAAI/bge-small-zh-v1.5"
    assert status["download_size_bytes"] > 90_000_000


def test_explicit_prepare_failure_is_visible_and_retryable(tmp_path: Path) -> None:
    def fail_download(*_args, **_kwargs):
        raise LocalModelError("model_download_failed")

    store = LocalRetrievalModelStore(
        tmp_path / "profile" / "retrieval-models", downloader=fail_download
    )

    first = store.start_prepare()
    assert first["state"] == "preparing"
    failed = store.wait_for_prepare()
    assert failed["state"] == "failed"
    assert failed["error_code"] == "model_download_failed"

    second = store.start_prepare()
    assert second["state"] == "preparing"
    retried = store.wait_for_prepare()
    assert retried["state"] == "failed"
    assert retried["error_code"] == "model_download_failed"


def test_injected_model_directory_cannot_be_downloaded_or_replaced(tmp_path: Path) -> None:
    store = LocalRetrievalModelStore(
        tmp_path / "profile" / "retrieval-models",
        model_directory=tmp_path / "test-model",
    )

    try:
        store.start_prepare()
    except LocalModelError as exc:
        assert exc.code == "model_directory_read_only"
    else:
        raise AssertionError("injected model directories must be read-only")


def test_prepare_deadline_fails_cleanly_and_retry_starts_from_empty_stage(tmp_path: Path) -> None:
    calls = 0

    def slow_download(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        time.sleep(0.08)

    store = LocalRetrievalModelStore(
        tmp_path / "profile" / "retrieval-models",
        downloader=slow_download,
        prepare_timeout_seconds=0.05,
        file_timeout_seconds=1,
    )

    store.start_prepare()
    first = store.wait_for_prepare(timeout=1)

    assert first["state"] == "failed"
    assert first["error_code"] == "model_prepare_timeout"
    assert not list(store.revision_dir.parent.glob(".partial-*"))

    store.start_prepare()
    second = store.wait_for_prepare(timeout=1)
    assert second["state"] == "failed"
    assert second["error_code"] == "model_prepare_timeout"
    assert calls == 2
    assert not list(store.revision_dir.parent.glob(".partial-*"))
