"""Non-secret first-use wizard progress store (frontend milestone D repair1).

The store must be the durable replacement for the browser-only progress that the
production WKWebView discards on restart. These tests pin the properties the
repair depends on: profile/workspace isolation, a strict field whitelist, atomic
replacement, and a read that never observes a half-written file.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from summit_everything.local.first_use_progress import (
    FirstUseProgress,
    FirstUseProgressError,
    FirstUseProgressStore,
)


def store(tmp_path: Path, *parts: str) -> FirstUseProgressStore:
    return FirstUseProgressStore(tmp_path.joinpath(*parts) / "first-use-progress.json")


def test_absent_record_is_none_not_an_error(tmp_path: Path) -> None:
    assert store(tmp_path, "profile-a", "workspace-a").read() is None


def test_round_trip_survives_a_new_store_instance(tmp_path: Path) -> None:
    progress = FirstUseProgress(step=3, completed=False, open=True)
    store(tmp_path, "profile-a", "workspace-a").write(progress)

    # A fresh store instance is what a restarted backend builds.
    assert store(tmp_path, "profile-a", "workspace-a").read() == progress


def test_profiles_and_workspaces_are_isolated(tmp_path: Path) -> None:
    store(tmp_path, "profile-a", "workspace-a").write(
        FirstUseProgress(step=3, completed=False, open=True)
    )
    store(tmp_path, "profile-b", "workspace-a").write(
        FirstUseProgress(step=4, completed=False, open=True)
    )
    store(tmp_path, "profile-a", "workspace-b").write(
        FirstUseProgress(step=5, completed=True, open=False)
    )

    assert store(tmp_path, "profile-a", "workspace-a").read() == FirstUseProgress(
        step=3, completed=False, open=True
    )
    assert store(tmp_path, "profile-b", "workspace-a").read() == FirstUseProgress(
        step=4, completed=False, open=True
    )
    assert store(tmp_path, "profile-a", "workspace-b").read() == FirstUseProgress(
        step=5, completed=True, open=False
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"step": 1, "completed": False, "open": True},
        {"step": 6, "completed": False, "open": True},
        {"step": "3", "completed": False, "open": True},
        {"step": 3, "completed": "yes", "open": True},
        {"step": 3, "completed": False},
    ],
)
def test_rejects_values_outside_the_whitelisted_shape(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        FirstUseProgress.model_validate(payload)


@pytest.mark.parametrize(
    "extra",
    [
        {"secret": "sk-synthetic-00000000"},
        {"api_key": "sk-synthetic-00000000"},
        {"path": "/Users/synthetic/profile"},
        {"step_extra": 1},
    ],
)
def test_rejects_extra_and_secret_shaped_fields(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        FirstUseProgress.model_validate({"step": 3, "completed": False, "open": True, **extra})


def test_stored_document_contains_only_the_three_whitelisted_keys(tmp_path: Path) -> None:
    path = tmp_path / "profile-a" / "workspace-a" / "first-use-progress.json"
    FirstUseProgressStore(path).write(FirstUseProgress(step=4, completed=False, open=True))

    assert json.loads(path.read_text()) == {"step": 4, "completed": False, "open": True}


def test_corrupted_document_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "profile-a" / "workspace-a" / "first-use-progress.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json")

    with pytest.raises(FirstUseProgressError):
        FirstUseProgressStore(path).read()


def test_corrupted_document_with_unknown_field_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "profile-a" / "workspace-a" / "first-use-progress.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"step": 3, "completed": False, "open": True, "secret": "x"}))

    with pytest.raises(FirstUseProgressError):
        FirstUseProgressStore(path).read()


def test_rewriting_leaves_no_partial_or_temporary_documents(tmp_path: Path) -> None:
    directory = tmp_path / "profile-a" / "workspace-a"
    document = FirstUseProgressStore(directory / "first-use-progress.json")

    document.write(FirstUseProgress(step=2, completed=False, open=True))
    document.write(FirstUseProgress(step=3, completed=False, open=True))

    # Only the live document and its lock file may survive; a crashed or
    # non-atomic write would leave a ``.first-use-progress-*`` turd behind.
    assert sorted(item.name for item in directory.iterdir()) == [
        "first-use-progress.json",
        "first-use-progress.json.lock",
    ]


def test_concurrent_writers_never_lose_or_corrupt_the_document(tmp_path: Path) -> None:
    path = tmp_path / "profile-a" / "workspace-a" / "first-use-progress.json"
    document = FirstUseProgressStore(path)
    errors: list[BaseException] = []
    barrier = threading.Barrier(6)

    def writer(step: int) -> None:
        try:
            barrier.wait()
            for _ in range(10):
                document.write(FirstUseProgress(step=step, completed=False, open=True))  # type: ignore[arg-type]
        except BaseException as exc:  # noqa: BLE001 - recorded and re-raised below
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(step,)) for step in (2, 3, 4, 5, 2, 3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    # The document is a valid, complete record from the whitelist — never a
    # truncated mixture of two writers.
    read_back = document.read()
    assert read_back is not None
    assert read_back.step in {2, 3, 4, 5}
    assert json.loads(path.read_text()) == read_back.model_dump(mode="json")


def test_reader_observes_whole_documents_while_writing(tmp_path: Path) -> None:
    path = tmp_path / "profile-a" / "workspace-a" / "first-use-progress.json"
    document = FirstUseProgressStore(path)
    document.write(FirstUseProgress(step=2, completed=False, open=True))
    observed: list[int] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            record = document.read()
            assert record is not None
            observed.append(record.step)

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        for step in (3, 4, 5, 2, 3, 4):
            document.write(FirstUseProgress(step=step, completed=False, open=True))  # type: ignore[arg-type]
    finally:
        stop.set()
        thread.join()

    assert observed and set(observed) <= {2, 3, 4, 5}
