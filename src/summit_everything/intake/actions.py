"""Independent action confirmation and a durable, non-retrying execution claim."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, Field

from summit_everything.integrations.feishu.provider import FeishuError
from summit_everything.integrations.feishu.tasks import (
    FeishuTasks,
    StrictModel,
    TaskComplete,
    TaskCreate,
    TaskUpdate,
)
from summit_everything.workspace.action_receipts import (
    archive_completed,
    read_receipts,
    save_receipt,
)
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.transactions import workspace_lock
from summit_everything.workspace.writer import ProjectProgressWriter, WorkspaceWriteConflict

ActionKind = Literal[
    "feishu_task_create", "feishu_task_update", "feishu_task_complete", "project_progress"
]


class ProgressPayload(StrictModel):
    project_id: UUID
    expected_version: int = Field(ge=0)
    progress: str = Field(min_length=1, max_length=2000)


class ActionProposal(StrictModel):
    action_id: UUID
    kind: ActionKind
    payload: dict[str, Any]
    candidate_id: UUID | None = None


class ActionEdit(StrictModel):
    expected_payload_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    payload: dict[str, Any]


class ActionConfirmation(StrictModel):
    payload_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    confirmation_id: str = Field(min_length=1, max_length=200)


class UserOutcome(ActionConfirmation):
    state: Literal["succeeded", "failed"]
    evidence: str = Field(min_length=1, max_length=2000)


class Action(StrictModel):
    action_id: UUID
    kind: ActionKind
    payload: dict[str, Any]
    payload_sha256: str
    confirmation_id: str | None = None
    state: Literal["proposed", "confirmed", "running", "succeeded", "failed", "unknown"] = (
        "proposed"
    )
    candidate_id: UUID | None = None
    source_draft_id: UUID | None = None
    source_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    confirmed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempt_session: str | None = None
    provider_result: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ActionPage(StrictModel):
    items: list[Action]
    next_cursor: str | None = None


def payload_hash(kind: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            {"kind": kind, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def validate_payload(kind: str, payload: dict[str, Any]) -> None:
    models: dict[str, type[BaseModel]] = {
        "feishu_task_create": TaskCreate,
        "feishu_task_update": TaskUpdate,
        "feishu_task_complete": TaskComplete,
        "project_progress": ProgressPayload,
    }
    models[kind].model_validate(payload)


class ActionService:
    def __init__(self, tasks: FeishuTasks, session: str) -> None:
        self.tasks = tasks
        self.session = session

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.tasks.session.clock(), UTC)

    def _all(self, root: Path) -> dict[UUID, Action]:
        load_manifest(root)
        actions = read_receipts(root)
        for item in actions.values():
            if item.state == "running" and item.attempt_session != self.session:
                item.state = "unknown"
                item.evidence.append({"kind": "interrupted", "at": self.now().isoformat()})
                save_receipt(root, item)
        archive_completed(root, self.now())
        return actions

    def _get(self, root: Path, action_id: UUID) -> Action:
        action = self._all(root).get(action_id)
        if action is None:
            raise WorkspaceError("动作不存在。", 404)
        return action

    def get(self, root: Path, action_id: UUID) -> Action:
        with workspace_lock(root):
            return self._get(root, action_id)

    def list(self, root: Path, cursor: str | None, limit: int) -> ActionPage:
        with workspace_lock(root):
            rows = sorted(self._all(root).values(), key=lambda item: str(item.action_id))
        if cursor is not None:
            try:
                UUID(cursor)
            except ValueError:
                raise FeishuError("invalid_cursor") from None
            rows = [row for row in rows if str(row.action_id) > cursor]
        return ActionPage(
            items=rows[:limit],
            next_cursor=str(rows[limit - 1].action_id) if len(rows) > limit else None,
        )

    def propose(self, root: Path, request: ActionProposal) -> Action:
        validate_payload(request.kind, request.payload)
        fingerprint = payload_hash(request.kind, request.payload)
        with workspace_lock(root):
            prior = self._all(root).get(request.action_id)
            if prior:
                if (
                    prior.payload_sha256 != fingerprint
                    or prior.candidate_id != request.candidate_id
                ):
                    raise WorkspaceWriteConflict("同一动作已用于另一组内容。")
                return prior
            action = Action(
                **request.model_dump(), payload_sha256=fingerprint, created_at=self.now()
            )
            if request.candidate_id is not None:
                from summit_everything.intake.review import IntakeReviewService
                from summit_everything.integrations.llm import FakeLLM

                candidates = IntakeReviewService(FakeLLM()).list_actions(root)
                candidate = next(
                    (value for value in candidates if value.action_id == request.candidate_id), None
                )
                if candidate is None:
                    raise WorkspaceError("建议不存在。", 404)
                if (candidate.kind == "todo") != request.kind.startswith("feishu_task_"):
                    raise WorkspaceWriteConflict("建议类型与动作不一致。")
                action.source_draft_id = candidate.source_draft_id
                source_ids = getattr(candidate, "source_ids", [])
                draft_path = (
                    root / ".summit-everything/drafts" / f"{candidate.source_draft_id}.json"
                )
                if draft_path.exists():
                    from summit_everything.domain.models import Draft

                    source_ids = Draft.model_validate_json(draft_path.read_bytes()).source_ids
                action.source_ids = [UUID(str(value)) for value in source_ids]
            save_receipt(root, action)
            return action

    def edit(self, root: Path, action_id: UUID, request: ActionEdit) -> Action:
        with workspace_lock(root):
            item = self._get(root, action_id)
            self._hash(item, request.expected_payload_sha256)
            if item.state not in {"proposed", "confirmed"}:
                raise WorkspaceWriteConflict("已执行或结果未知的动作不能修改。")
            validate_payload(item.kind, request.payload)
            item.payload = request.payload
            item.payload_sha256 = payload_hash(item.kind, request.payload)
            item.state = "proposed"
            item.confirmation_id = None
            item.confirmed_at = None
            save_receipt(root, item)
            return item

    def _hash(self, item: Action, expected: str) -> None:
        if item.payload_sha256 != expected:
            raise WorkspaceWriteConflict("动作内容已变化，请重新核对并确认。")

    def confirm(self, root: Path, action_id: UUID, request: ActionConfirmation) -> Action:
        with workspace_lock(root):
            item = self._get(root, action_id)
            self._hash(item, request.payload_sha256)
            if item.state != "proposed":
                if item.confirmation_id == request.confirmation_id:
                    return item
                raise WorkspaceWriteConflict("动作已有独立确认或执行结果。")
            item.state = "confirmed"
            item.confirmation_id = request.confirmation_id
            item.confirmed_at = self.now()
            save_receipt(root, item)
            return item

    def token(self, root: Path, item: Action) -> str:
        return str(uuid5(load_manifest(root).workspace_id, "action:" + str(item.action_id)))

    def execute(self, root: Path, action_id: UUID, request: ActionConfirmation) -> Action:
        with workspace_lock(root):
            item = self._get(root, action_id)
            self._hash(item, request.payload_sha256)
            if item.confirmation_id != request.confirmation_id or item.state == "proposed":
                raise WorkspaceWriteConflict("请先独立确认最终动作内容。")
            if item.state != "confirmed":
                return item
            if item.kind != "project_progress":
                self.tasks.session._user("task:task:write")
            item.state = "running"
            item.attempt_session = self.session
            item.started_at = self.now()
            save_receipt(root, item)
        try:
            if item.kind == "project_progress":
                payload = ProgressPayload.model_validate(item.payload)
                item.provider_result = ProjectProgressWriter().apply(
                    root,
                    project_id=payload.project_id,
                    expected_version=payload.expected_version,
                    progress=payload.progress,
                    operation_id="progress:" + self.token(root, item),
                    confirmation_id=item.confirmation_id or "",
                )
            else:
                task = self.tasks.execute(item.kind, item.payload, self.token(root, item))
                item.provider_result = {"task": task.model_dump(mode="json")}
            item.state = "succeeded"
            item.finished_at = self.now()
        except (WorkspaceWriteConflict, WorkspaceError):
            item.state = "failed"
            item.finished_at = self.now()
            item.provider_result = {
                "error_code": "version_conflict",
                "message": "项目进度已变化或项目不可用，请重新查看。",
            }
        except FeishuError as exc:
            item.state = (
                "failed"
                if exc.code in {"not_authorized", "token_expired", "missing_scope", "not_found"}
                else "unknown"
            )
            item.provider_result = {
                "error_code": exc.code,
                "message": "动作未得到明确成功结果，请核实。",
            }
            if item.state == "failed":
                item.finished_at = self.now()
        with workspace_lock(root):
            save_receipt(root, item)
        return item

    def reconcile(self, root: Path, action_id: UUID) -> Action:
        item = self.get(root, action_id)
        if item.state != "unknown":
            return item
        task = None
        if item.kind != "project_progress":
            task = self.tasks.lookup(self.token(root, item))
        with workspace_lock(root):
            item = self._get(root, action_id)
            if item.state != "unknown":
                return item
            item.evidence.append(
                {
                    "kind": "provider_lookup",
                    "at": self.now().isoformat(),
                    "found": task is not None,
                    "task": task.model_dump(mode="json") if task else None,
                }
            )
            if task is not None:
                item.state = "succeeded"
                item.finished_at = self.now()
                item.provider_result = {"task": task.model_dump(mode="json")}
            save_receipt(root, item)
            return item

    def outcome(self, root: Path, action_id: UUID, request: UserOutcome) -> Action:
        with workspace_lock(root):
            item = self._get(root, action_id)
            self._hash(item, request.payload_sha256)
            if item.state != "unknown":
                raise WorkspaceWriteConflict("只有未知结果需要人工核实。")
            item.evidence.append(
                {
                    "kind": "user_outcome",
                    "state": request.state,
                    "text": request.evidence,
                    "confirmation_id": request.confirmation_id,
                    "at": self.now().isoformat(),
                }
            )
            item.state = request.state
            item.finished_at = self.now()
            save_receipt(root, item)
            return item
