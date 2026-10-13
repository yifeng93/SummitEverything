import fcntl
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

from summit_everything.integrations.acceptance_plans import (
    AcceptancePlanLedger,
    PlanConflict,
    ProviderUsage,
)


def test_plan_requires_explicit_confirmation_and_reserves_once(tmp_path: Path) -> None:
    ledger = AcceptancePlanLedger(tmp_path)
    plan = ledger.create(
        operation="model.query",
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        scope={"page_ids": ["page-a"], "versions": {"page-a": "c" * 64}},
        request_limit=3,
    )

    with pytest.raises(PlanConflict, match="fresh explicit confirmation"):
        ledger.begin_execution(
            plan.plan_id,
            workspace_id="workspace-a",
            profile_id="profile-a",
            config_sha256="a" * 64,
            scope_sha256="b" * 64,
            run_id=uuid4(),
        )

    confirmed = ledger.confirm(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
    )
    assert confirmed.state == "confirmed"
    ledger.begin_execution(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        run_id=uuid4(),
    )
    reserved = ledger.reserve_request(
        plan.plan_id, workspace_id="workspace-a", profile_id="profile-a"
    )
    assert reserved.requests_reserved == 1
    assert ledger.get(plan.plan_id).requests_reserved == 1


def test_plan_confirmation_fails_closed_on_binding_change(tmp_path: Path) -> None:
    ledger = AcceptancePlanLedger(tmp_path)
    plan = ledger.create(
        operation="feishu.calendar.read",
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        scope={"start": "2026-10-13", "end": "2026-10-14", "timezone": "Asia/Shanghai"},
        request_limit=2,
    )
    with pytest.raises(PlanConflict, match="changed"):
        ledger.confirm(
            plan.plan_id,
            workspace_id="workspace-a",
            profile_id="profile-a",
            config_sha256="d" * 64,
            scope_sha256="b" * 64,
        )
    ledger.confirm(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
    )
    ledger.begin_execution(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        run_id=uuid4(),
    )
    with pytest.raises(PlanConflict, match="fresh explicit confirmation"):
        ledger.begin_execution(
            plan.plan_id,
            workspace_id="workspace-a",
            profile_id="profile-a",
            config_sha256="a" * 64,
            scope_sha256="b" * 64,
            run_id=uuid4(),
        )


def test_concurrent_reservation_obeys_finite_request_budget(tmp_path: Path) -> None:
    ledger = AcceptancePlanLedger(tmp_path)
    plan = ledger.create(
        operation="model.index",
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        scope={"page_ids": ["page-a"]},
        request_limit=1,
    )
    ledger.confirm(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
    )
    ledger.begin_execution(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        run_id=uuid4(),
    )

    def reserve() -> bool:
        try:
            ledger.reserve_request(plan.plan_id, workspace_id="workspace-a", profile_id="profile-a")
            return True
        except PlanConflict:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: reserve(), range(8)))
    assert sum(results) == 1
    assert ledger.get(plan.plan_id).requests_reserved == 1


def test_ledger_never_persists_scope_text_and_corruption_fails_closed(tmp_path: Path) -> None:
    ledger = AcceptancePlanLedger(tmp_path)
    plan = ledger.create(
        operation="model.query",
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        scope={"question": "SYNTHETIC PRIVATE QUERY", "body": "SYNTHETIC PRIVATE PAGE"},
        request_limit=3,
    )
    raw = (tmp_path / "acceptance-plans.json").read_text()
    assert "SYNTHETIC PRIVATE" not in raw
    assert plan.scope_sha256 == "b" * 64
    (tmp_path / "acceptance-plans.json").write_text("not-json")
    with pytest.raises(RuntimeError, match="unavailable"):
        ledger.get(plan.plan_id)
    with (tmp_path / "acceptance-plans.lock").open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_provider_usage_records_only_reported_counts_and_bounded_request_ids(
    tmp_path: Path,
) -> None:
    ledger = AcceptancePlanLedger(tmp_path)
    plan = ledger.create(
        operation="model.query",
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        scope={"question": "SYNTHETIC PRIVATE QUERY"},
        request_limit=3,
    )
    ledger.confirm(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
    )
    ledger.begin_execution(
        plan.plan_id,
        workspace_id="workspace-a",
        profile_id="profile-a",
        config_sha256="a" * 64,
        scope_sha256="b" * 64,
        run_id=uuid4(),
    )
    ledger.reserve_requests(
        plan.plan_id, workspace_id="workspace-a", profile_id="profile-a", count=3
    )
    ledger.record_usage(
        plan.plan_id,
        [
            ProviderUsage(
                provider="qwen3.7-text-embedding",
                request_id="synthetic-request-1",
                usage_reported=True,
                total_tokens=17,
            ),
            ProviderUsage(
                provider="deepseek",
                request_id=None,
                usage_reported=False,
            ),
        ],
    )
    raw = (tmp_path / "acceptance-plans.json").read_text()
    assert "SYNTHETIC PRIVATE QUERY" not in raw
    assert "synthetic-request-1" in raw
    assert "prompt" not in raw and "secret" not in raw
    restored = ledger.get(plan.plan_id).provider_usage
    assert restored[0].total_tokens == 17
    assert restored[0].input_tokens is None
    assert restored[1].usage_reported is False
    assert restored[1].total_tokens is None
    with pytest.raises(PlanConflict, match="request bound"):
        ledger.record_usage(
            plan.plan_id,
            [
                ProviderUsage(
                    provider="deepseek",
                    request_id="synthetic-extra",
                    usage_reported=False,
                ),
                ProviderUsage(
                    provider="deepseek",
                    request_id="synthetic-extra-2",
                    usage_reported=False,
                ),
            ],
        )
