"""Cross-run one-shot ledger for the user's narrowly authorized synthetic calls."""

from __future__ import annotations

import fcntl
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict, cast

from summit_everything.workspace.transactions import atomic_write

SMOKE_LIMITS = {"deepseek_chat": 1, "model_studio_embedding": 1, "model_studio_rerank": 1}


class SmokeLedger(TypedDict):
    counts: dict[str, int]
    results: dict[str, dict[str, str]]


class SmokeLimitReached(RuntimeError):
    pass


def smoke_counts(profile: Path) -> dict[str, int]:
    path = profile / "provider-smoke.json"
    if not path.exists():
        return dict.fromkeys(SMOKE_LIMITS, 0)
    try:
        value = json.loads(path.read_bytes())
        counts = value["counts"]
        if (
            value.get("schema") != 1
            or set(counts) != set(SMOKE_LIMITS)
            or any(type(counts[name]) is not int or counts[name] < 0 for name in SMOKE_LIMITS)
        ):
            raise ValueError
        results = value.get("results", {})
        if not isinstance(results, dict):
            raise ValueError
        return cast(dict[str, int], counts)
    except (OSError, ValueError, TypeError, KeyError):
        raise RuntimeError("provider smoke ledger is unavailable") from None


def reserve_smoke_call(profile: Path, operation: str) -> int:
    if operation not in SMOKE_LIMITS:
        raise ValueError("unknown provider smoke operation")
    profile.mkdir(parents=True, exist_ok=True)
    lock_path = profile / "provider-smoke.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = _read_smoke(profile)
        counts = current["counts"]
        if counts[operation] >= SMOKE_LIMITS[operation]:
            raise SmokeLimitReached("this authorized synthetic call has already been used")
        counts[operation] += 1
        current["counts"] = counts
        _write_smoke(profile, current)
        return counts[operation]


def record_smoke_result(
    profile: Path,
    operation: str,
    *,
    workspace_id: str,
    profile_id: str,
    config_sha256: str,
    state: Literal["succeeded", "failed", "unknown"],
) -> None:
    """Persist only the outcome and non-secret configuration identity."""
    if operation not in SMOKE_LIMITS or len(config_sha256) != 64:
        raise ValueError("invalid smoke result binding")
    profile.mkdir(parents=True, exist_ok=True)
    with (profile / "provider-smoke.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = _read_smoke(profile)
        current["results"][operation] = {
            "workspace_id": workspace_id,
            "profile_id": profile_id,
            "config_sha256": config_sha256,
            "state": state,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        _write_smoke(profile, current)


def smoke_result(profile: Path, operation: str) -> dict[str, str] | None:
    return _read_smoke(profile)["results"].get(operation)


def _read_smoke(profile: Path) -> SmokeLedger:
    path = profile / "provider-smoke.json"
    if not path.exists():
        return {"counts": dict.fromkeys(SMOKE_LIMITS, 0), "results": {}}
    try:
        value = json.loads(path.read_bytes())
        counts = value["counts"]
        results = value.get("results", {})
        if (
            value.get("schema") != 1
            or set(counts) != set(SMOKE_LIMITS)
            or any(type(counts[name]) is not int or counts[name] < 0 for name in SMOKE_LIMITS)
            or not isinstance(results, dict)
            or any(
                key not in SMOKE_LIMITS or not isinstance(item, dict)
                for key, item in results.items()
            )
        ):
            raise ValueError
        expected_fields = {"workspace_id", "profile_id", "config_sha256", "state", "finished_at"}
        for item in results.values():
            if (
                set(item) != expected_fields
                or not all(isinstance(field, str) for field in item.values())
                or item["state"] not in {"succeeded", "failed", "unknown"}
                or len(item["config_sha256"]) != 64
            ):
                raise ValueError
        return cast(SmokeLedger, {"counts": counts, "results": results})
    except (OSError, ValueError, TypeError, KeyError):
        raise RuntimeError("provider smoke ledger is unavailable") from None


def _write_smoke(profile: Path, value: SmokeLedger) -> None:
    atomic_write(
        profile / "provider-smoke.json",
        json.dumps({"schema": 1, **value}, sort_keys=True, separators=(",", ":")).encode(),
    )
