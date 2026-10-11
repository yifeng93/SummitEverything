"""Cross-run one-shot ledger for the user's narrowly authorized synthetic calls."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import cast

from summit_everything.workspace.transactions import atomic_write

SMOKE_LIMITS = {"deepseek_chat": 1, "model_studio_embedding": 1, "model_studio_rerank": 1}


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
        counts = smoke_counts(profile)
        if counts[operation] >= SMOKE_LIMITS[operation]:
            raise SmokeLimitReached("this authorized synthetic call has already been used")
        counts[operation] += 1
        atomic_write(
            profile / "provider-smoke.json",
            json.dumps({"schema": 1, "counts": counts}, sort_keys=True).encode(),
        )
        return counts[operation]
