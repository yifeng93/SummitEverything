"""Strict proposal schema and a local deterministic provider for isolated tests."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImportantConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    alternatives: list[str] = Field(min_length=2)


class ActionSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["todo", "progress_change"]
    description: str = Field(min_length=1)
    related_project_id: UUID | None = None


class DraftProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    kind: Literal["object", "case", "topic", "decision"] = "topic"
    body: str = Field(min_length=1)
    important_conflicts: list[ImportantConflict] = Field(default_factory=list)
    action_suggestions: list[ActionSuggestion] = Field(default_factory=list)


class LLMProviderError(RuntimeError):
    """The provider failed or returned data outside its declared schema."""


class FakeLLM:
    """Deterministic provider used by development and acceptance scenarios."""

    def __init__(self, *, scenario: str = "valid") -> None:
        self.scenario = scenario
        self.calls = 0

    def organize(self, inputs: list[tuple[UUID, UUID, str]]) -> list[DraftProposal]:
        self.calls += 1
        if self.scenario == "timeout":
            raise LLMProviderError("simulated provider timeout")
        if self.scenario == "malformed":
            raise LLMProviderError("simulated malformed provider response")
        proposals: list[DraftProposal] = []
        for index, (_item_id, _source_id, text) in enumerate(inputs):
            conflict = []
            if self.scenario == "conflict" and index == 0:
                conflict = [
                    ImportantConflict(
                        id="status-conflict",
                        question="状态是否已确认？",
                        alternatives=["已确认", "仍待确认"],
                    )
                ]
            proposals.append(
                DraftProposal(
                    title=f"模拟整理稿 {index + 1}",
                    kind="topic",
                    body=f"## 来源摘要\n\n{text.strip()}\n",
                    important_conflicts=conflict,
                    action_suggestions=(
                        [
                            ActionSuggestion(
                                kind="todo",
                                description="仅供用户决定是否另行创建任务",
                            )
                        ]
                        if self.scenario == "action" and index == 0
                        else []
                    ),
                )
            )
        return proposals
