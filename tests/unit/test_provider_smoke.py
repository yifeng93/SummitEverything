from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from summit_everything.integrations.provider_smoke import (
    SmokeLimitReached,
    reserve_smoke_call,
    smoke_counts,
)


def test_smoke_ledger_allows_each_authorized_synthetic_operation_once(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    assert smoke_counts(profile) == {
        "deepseek_chat": 0,
        "model_studio_embedding": 0,
        "model_studio_rerank": 0,
    }
    assert reserve_smoke_call(profile, "deepseek_chat") == 1
    with pytest.raises(SmokeLimitReached):
        reserve_smoke_call(profile, "deepseek_chat")
    assert reserve_smoke_call(profile, "model_studio_embedding") == 1
    assert reserve_smoke_call(profile, "model_studio_rerank") == 1
    assert smoke_counts(profile)["deepseek_chat"] == 1


def test_smoke_ledger_serializes_concurrent_attempts(tmp_path: Path) -> None:
    profile = tmp_path / "profile"

    def attempt() -> str:
        try:
            reserve_smoke_call(profile, "model_studio_embedding")
            return "reserved"
        except SmokeLimitReached:
            return "limited"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(8)))
    assert outcomes.count("reserved") == 1
    assert outcomes.count("limited") == 7
    assert smoke_counts(profile)["model_studio_embedding"] == 1


def test_corrupt_smoke_ledger_fails_closed(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "provider-smoke.json").write_text('{"schema":1,"counts":{}}')
    with pytest.raises(RuntimeError):
        reserve_smoke_call(profile, "deepseek_chat")
