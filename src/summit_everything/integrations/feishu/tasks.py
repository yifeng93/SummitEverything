"""Task v2 values and mapping; no HTTP or second authorization stack."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from summit_everything.integrations.feishu.provider import FeishuError, UserCredentials
from summit_everything.integrations.feishu.service import FeishuService


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskDate(StrictModel):
    value: str
    is_all_day: bool = Field(strict=True)
    timezone: str

    @model_validator(mode="after")
    def valid_date(self) -> TaskDate:
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError("请选择有效的时区。") from None
        if self.is_all_day:
            from datetime import date

            date.fromisoformat(self.value)
        else:
            parsed = datetime.fromisoformat(self.value)
            if parsed.tzinfo is None or parsed.utcoffset() != parsed.astimezone(zone).utcoffset():
                raise ValueError("日期时间须带与所选时区一致的偏移量。")
        return self

    def provider_value(self) -> dict[str, Any]:
        """Map Fake wire values; all-day midnight is only a simulation convention.

        The exact all-day date extraction rule was unavailable in official docs.
        Keep the original date and IANA zone in the intent; a real adapter must
        verify the rule before using this conversion. Configuration is Fake only.
        """
        if self.is_all_day:
            from datetime import date

            value = datetime.combine(
                date.fromisoformat(self.value), time(), ZoneInfo(self.timezone)
            )
        else:
            value = datetime.fromisoformat(self.value)
        return {"timestamp": str(int(value.timestamp() * 1000)), "is_all_day": self.is_all_day}


class TaskCreate(StrictModel):
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    due: TaskDate | None  # required explicit no-date choice

    @field_validator("summary")
    @classmethod
    def title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请填写任务标题。")
        return value


class TaskChanges(StrictModel):
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    due: TaskDate | None = None


class TaskUpdate(StrictModel):
    task_guid: str = Field(min_length=1, max_length=200)
    task: TaskChanges
    update_fields: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def selected_only(self) -> TaskUpdate:
        if set(self.update_fields) != self.task.model_fields_set or len(
            set(self.update_fields)
        ) != len(self.update_fields):
            raise ValueError("请只填写明确选择的修改字段。")
        if "summary" in self.update_fields and (
            self.task.summary is None or not self.task.summary.strip()
        ):
            raise ValueError("请填写任务标题。")
        if "description" in self.update_fields and self.task.description is None:
            raise ValueError("清空描述请使用空文本。")
        return self


class TaskComplete(StrictModel):
    task_guid: str = Field(min_length=1, max_length=200)


class ProviderDue(StrictModel):
    timestamp: int = Field(ge=0)
    is_all_day: bool


class FeishuTask(StrictModel):
    guid: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = ""
    due: ProviderDue | None = None
    completed_at: int = Field(default=0, ge=0)


class TaskExecutionEvidence(StrictModel):
    client_token: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern="^feishu_task_(create|update|complete)$")
    target_guid: str | None = Field(default=None, min_length=1, max_length=200)
    task: FeishuTask


class TaskPage(StrictModel):
    items: list[FeishuTask]
    next_cursor: str | None = None


class FeishuTasks:
    def __init__(self, session: FeishuService) -> None:
        self.session = session

    def _reader(self) -> UserCredentials:
        credentials = self.session.credentials.get()
        scope = (
            "task:task:write"
            if credentials and "task:task:write" in credentials.scopes
            else "task:task:read"
        )
        return self.session._user(scope)

    def list(self, cursor: str | None, limit: int) -> TaskPage:
        user = self._reader()
        result = self.session._call(lambda: self.session.provider.tasks(user, cursor, limit))
        if not isinstance(result, TaskPage) or len(result.items) > limit:
            raise FeishuError("malformed_response")
        return result

    def get(self, guid: str) -> FeishuTask:
        user = self._reader()
        return self._task(
            self.session._call(lambda: self.session.provider.task_get(user, guid)), guid
        )

    def _task(self, result: FeishuTask, expected_guid: str | None = None) -> FeishuTask:
        if not isinstance(result, FeishuTask) or (
            expected_guid is not None and result.guid != expected_guid
        ):
            raise FeishuError("malformed_response")
        return result

    @staticmethod
    def _matches_due(expected: TaskDate | None, actual: ProviderDue | None) -> bool:
        if expected is None:
            return actual is None
        wire_due = expected.provider_value()
        return actual is not None and (
            actual.timestamp == int(wire_due["timestamp"])
            and actual.is_all_day == wire_due["is_all_day"]
        )

    def _validate_result(
        self, kind: str, payload: dict[str, Any], result: FeishuTask
    ) -> FeishuTask:
        if kind == "feishu_task_create":
            create_request = TaskCreate.model_validate(payload)
            matches = (
                result.summary == create_request.summary
                and result.description == create_request.description
                and self._matches_due(create_request.due, result.due)
            )
        elif kind == "feishu_task_update":
            update_request = TaskUpdate.model_validate(payload)
            changes = update_request.task
            matches = result.guid == update_request.task_guid
            if "summary" in update_request.update_fields:
                matches = matches and result.summary == changes.summary
            if "description" in update_request.update_fields:
                matches = matches and result.description == changes.description
            if "due" in update_request.update_fields:
                matches = matches and self._matches_due(changes.due, result.due)
        elif kind == "feishu_task_complete":
            complete_request = TaskComplete.model_validate(payload)
            matches = result.guid == complete_request.task_guid and result.completed_at > 0
        else:
            raise FeishuError("malformed_response")
        if not matches:
            raise FeishuError("malformed_response")
        return result

    def execute(self, kind: str, payload: dict[str, Any], token: str) -> FeishuTask:
        user = self.session._user("task:task:write")
        if kind == "feishu_task_create":
            data = TaskCreate.model_validate(payload)
            body = data.model_dump(exclude={"due"})
            if data.due is not None:
                body["due"] = data.due.provider_value()
            body["client_token"] = token
            result = self._task(
                self.session._call(lambda: self.session.provider.task_create(user, body))
            )
            return self._validate_result(kind, payload, result)
        if kind == "feishu_task_complete":
            current = self.get(payload["task_guid"])
            if current.completed_at:
                return current
            body = {
                "task": {"completed_at": str(int(self.session.clock() * 1000))},
                "update_fields": ["completed_at"],
            }
        else:
            change = TaskUpdate.model_validate(payload)
            values = change.task.model_dump(exclude_unset=True)
            if change.task.due is not None:
                values["due"] = change.task.due.provider_value()
            body = {"task": values, "update_fields": change.update_fields}
        result = self._task(
            self.session._call(
                lambda: self.session.provider.task_patch(user, payload["task_guid"], body, token)
            ),
            payload["task_guid"],
        )
        return self._validate_result(kind, payload, result)

    def lookup(self, token: str) -> TaskExecutionEvidence | None:
        user = self._reader()
        value = self.session._call(lambda: self.session.provider.task_result(user, token))
        if value is None:
            return None
        try:
            evidence = TaskExecutionEvidence.model_validate(value)
        except ValueError:
            return None
        return evidence

    def verify_lookup(
        self, kind: str, payload: dict[str, Any], token: str, evidence: TaskExecutionEvidence
    ) -> bool:
        if evidence.client_token != token or evidence.kind != kind:
            return False
        if kind == "feishu_task_create":
            if evidence.target_guid is not None:
                return False
        elif evidence.target_guid != payload.get("task_guid"):
            return False
        try:
            self._validate_result(kind, payload, evidence.task)
        except (FeishuError, ValueError):
            return False
        return True
