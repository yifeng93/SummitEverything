"""Small local ledger for explicit, one-shot real-operation approvals."""

from __future__ import annotations

import fcntl
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from summit_everything.workspace.transactions import atomic_write

PlanState = Literal[
    "preview", "confirmed", "executing", "succeeded", "failed", "unknown", "cancelled"
]


class PlanConflict(RuntimeError):
    """A plan is stale, already used, or outside its confirmed scope."""


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["deepseek", "qwen3.7-text-embedding", "qwen3.7-text-rerank"]
    request_id: str | None = Field(default=None, max_length=200)
    usage_reported: bool
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AcceptancePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    operation: str
    workspace_id: str
    profile_id: str
    config_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    scope_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    request_limit: int = Field(ge=1, le=100)
    requests_reserved: int = Field(default=0, ge=0, le=100)
    state: PlanState = "preview"
    execution_run_id: UUID | None = None
    provider_usage: list[ProviderUsage] = Field(default_factory=list, max_length=100)
    created_at: datetime
    expires_at: datetime
    finished_at: datetime | None = None

    @field_validator("created_at", "expires_at", "finished_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_state_shape(self) -> AcceptancePlan:
        if self.expires_at <= self.created_at:
            raise ValueError("plan expiration must follow creation")
        if self.state == "executing" and self.execution_run_id is None:
            raise ValueError("executing plans require a run identifier")
        if self.state in {"succeeded", "failed", "unknown", "cancelled"}:
            if self.finished_at is None:
                raise ValueError("terminal plans require a finish time")
        elif self.finished_at is not None:
            raise ValueError("active plans cannot have a finish time")
        return self


class AcceptancePlanLedger:
    """Atomically persists only IDs, hashes, state, and bounded counters."""

    schema_version = 1
    max_plans = 256
    lifetime = timedelta(minutes=10)

    def __init__(self, profile: Path) -> None:
        self.path = profile / "acceptance-plans.json"
        self.lock_path = profile / "acceptance-plans.lock"

    def create(
        self,
        *,
        operation: str,
        workspace_id: str,
        profile_id: str,
        config_sha256: str,
        scope_sha256: str,
        scope: dict[str, object],
        request_limit: int,
    ) -> AcceptancePlan:
        # scope is accepted only so callers cannot accidentally skip digesting it;
        # raw questions, page text, task queries, and other payloads are never saved.
        del scope
        now = datetime.now(UTC)
        plan = AcceptancePlan(
            plan_id=uuid4(),
            operation=operation,
            workspace_id=workspace_id,
            profile_id=profile_id,
            config_sha256=config_sha256,
            scope_sha256=scope_sha256,
            request_limit=request_limit,
            created_at=now,
            expires_at=now + self.lifetime,
        )
        with self._locked() as records:
            active = [
                item
                for item in records.values()
                if item.state in {"preview", "confirmed", "executing"} and item.expires_at > now
            ]
            if len(active) >= 32 or len(records) >= self.max_plans:
                raise RuntimeError("acceptance plan ledger is full")
            records[str(plan.plan_id)] = plan
        return plan

    def get(self, plan_id: UUID) -> AcceptancePlan:
        with self._locked(read_only=True) as records:
            plan = records.get(str(plan_id))
            if plan is None:
                raise PlanConflict("acceptance plan was not found")
            if plan.expires_at <= datetime.now(UTC) and plan.state in {
                "preview",
                "confirmed",
            }:
                raise PlanConflict("acceptance plan expired")
            return plan

    def confirm(
        self,
        plan_id: UUID,
        *,
        workspace_id: str,
        profile_id: str,
        config_sha256: str,
        scope_sha256: str,
    ) -> AcceptancePlan:
        with self._locked() as records:
            plan = self._bound(
                records,
                plan_id,
                workspace_id=workspace_id,
                profile_id=profile_id,
                config_sha256=config_sha256,
                scope_sha256=scope_sha256,
            )
            if plan.state != "preview":
                raise PlanConflict("only an unused preview can be confirmed")
            plan = plan.model_copy(update={"state": "confirmed"})
            records[str(plan_id)] = plan
            return plan

    def begin_execution(
        self,
        plan_id: UUID,
        *,
        workspace_id: str,
        profile_id: str,
        config_sha256: str,
        scope_sha256: str,
        run_id: UUID,
    ) -> AcceptancePlan:
        with self._locked() as records:
            plan = self._bound(
                records,
                plan_id,
                workspace_id=workspace_id,
                profile_id=profile_id,
                config_sha256=config_sha256,
                scope_sha256=scope_sha256,
            )
            if plan.state != "confirmed":
                raise PlanConflict("plan requires a fresh explicit confirmation")
            plan = plan.model_copy(update={"state": "executing", "execution_run_id": run_id})
            records[str(plan_id)] = plan
            return plan

    def reserve_request(
        self, plan_id: UUID, *, workspace_id: str, profile_id: str
    ) -> AcceptancePlan:
        return self.reserve_requests(
            plan_id, workspace_id=workspace_id, profile_id=profile_id, count=1
        )

    def reserve_requests(
        self, plan_id: UUID, *, workspace_id: str, profile_id: str, count: int
    ) -> AcceptancePlan:
        if count < 1:
            raise ValueError("request reservation must be positive")
        with self._locked() as records:
            plan = records.get(str(plan_id))
            if plan is None:
                raise PlanConflict("acceptance plan was not found")
            if plan.workspace_id != workspace_id or plan.profile_id != profile_id:
                raise PlanConflict("acceptance plan belongs to a different workspace or profile")
            if plan.state != "executing":
                raise PlanConflict("plan requires explicit confirmation and execution")
            if plan.expires_at <= datetime.now(UTC):
                raise PlanConflict("acceptance plan expired; reserved requests remain consumed")
            if plan.requests_reserved + count > plan.request_limit:
                raise PlanConflict("confirmed provider request limit has been reached")
            plan = plan.model_copy(update={"requests_reserved": plan.requests_reserved + count})
            records[str(plan_id)] = plan
            return plan

    def record_usage(self, plan_id: UUID, usage: list[ProviderUsage]) -> AcceptancePlan:
        if not usage:
            return self.get(plan_id)
        with self._locked() as records:
            plan = records.get(str(plan_id))
            if plan is None:
                raise PlanConflict("acceptance plan was not found")
            if plan.state not in {"executing", "succeeded", "unknown"}:
                raise PlanConflict("provider usage does not belong to an executing plan")
            updated = [*plan.provider_usage, *usage]
            if len(updated) > min(plan.request_limit, 100):
                raise PlanConflict("provider usage exceeds the confirmed request bound")
            plan = plan.model_copy(update={"provider_usage": updated})
            records[str(plan_id)] = plan
            return plan

    def finish(
        self, plan_id: UUID, *, state: Literal["succeeded", "failed", "unknown"]
    ) -> AcceptancePlan:
        with self._locked() as records:
            plan = records.get(str(plan_id))
            if plan is None or plan.state != "executing":
                raise PlanConflict("plan is not executing")
            plan = plan.model_copy(
                update={
                    "state": state,
                    "finished_at": datetime.now(UTC),
                }
            )
            records[str(plan_id)] = plan
            return plan

    def cancel(self, plan_id: UUID, *, workspace_id: str, profile_id: str) -> AcceptancePlan:
        with self._locked() as records:
            plan = records.get(str(plan_id))
            if plan is None or plan.workspace_id != workspace_id or plan.profile_id != profile_id:
                raise PlanConflict("acceptance plan was not found")
            if plan.state not in {"preview", "confirmed"}:
                raise PlanConflict("an executing or completed plan cannot be cancelled")
            plan = plan.model_copy(update={"state": "cancelled", "finished_at": datetime.now(UTC)})
            records[str(plan_id)] = plan
            return plan

    def _bound(
        self,
        records: dict[str, AcceptancePlan],
        plan_id: UUID,
        *,
        workspace_id: str,
        profile_id: str,
        config_sha256: str,
        scope_sha256: str,
    ) -> AcceptancePlan:
        plan = records.get(str(plan_id))
        if plan is None:
            raise PlanConflict("acceptance plan was not found")
        if plan.expires_at <= datetime.now(UTC):
            raise PlanConflict("acceptance plan expired")
        if (
            plan.workspace_id != workspace_id
            or plan.profile_id != profile_id
            or plan.config_sha256 != config_sha256
            or plan.scope_sha256 != scope_sha256
        ):
            raise PlanConflict("workspace, profile, configuration, or scope changed")
        return plan

    def _read(self) -> dict[str, AcceptancePlan]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_bytes())
            if value.get("schema") != self.schema_version or not isinstance(
                value.get("plans"), dict
            ):
                raise ValueError
            plans = {
                key: AcceptancePlan.model_validate(item) for key, item in value["plans"].items()
            }
            if len(plans) > self.max_plans or any(
                key != str(plan.plan_id)
                or plan.requests_reserved > plan.request_limit
                or len(plan.provider_usage) > plan.requests_reserved
                for key, plan in plans.items()
            ):
                raise ValueError
            return plans
        except (OSError, ValueError, TypeError, AttributeError):
            raise RuntimeError("acceptance plan ledger is unavailable") from None

    def _write(self, records: dict[str, AcceptancePlan]) -> None:
        payload = {
            "schema": self.schema_version,
            "plans": {
                key: item.model_dump(mode="json", exclude_none=True)
                for key, item in records.items()
            },
        }
        atomic_write(
            self.path,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        )

    class _Lock:
        def __init__(self, ledger: AcceptancePlanLedger, read_only: bool) -> None:
            self.ledger = ledger
            self.read_only = read_only
            self.stream: BinaryIO | None = None
            self.records: dict[str, AcceptancePlan] = {}

        def __enter__(self) -> dict[str, AcceptancePlan]:
            self.ledger.path.parent.mkdir(parents=True, exist_ok=True)
            self.stream = self.ledger.lock_path.open("a+b")
            try:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX)
                self.records = self.ledger._read()
                return self.records
            except BaseException:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                self.stream.close()
                self.stream = None
                raise

        def __exit__(self, *_exc: object) -> None:
            try:
                if not self.read_only:
                    self.ledger._write(self.records)
            finally:
                if self.stream is not None:
                    fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                    self.stream.close()

    def _locked(self, *, read_only: bool = False) -> AcceptancePlanLedger._Lock:
        return self._Lock(self, read_only)
