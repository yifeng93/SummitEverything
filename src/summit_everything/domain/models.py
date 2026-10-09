"""Shared API and workspace value objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpenModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class LineRecord(OpenModel):
    id: UUID
    name: str = Field(min_length=1)
    directory: str


class ProjectRecord(OpenModel):
    id: UUID
    line_id: UUID
    name: str = Field(min_length=1)
    directory: str
    overview_id: UUID
    archived: bool = False


class WorkspaceManifest(OpenModel):
    version: Literal[1] = 1
    workspace_id: UUID
    name: str
    created_at: datetime
    lines: list[LineRecord] = Field(default_factory=list)
    projects: list[ProjectRecord] = Field(default_factory=list)


class WorkspaceContext(BaseModel):
    workspace_id: UUID
    root: str
    local_profile_dir: str
    name: str
    read_only: bool = False


class PageSnapshot(BaseModel):
    page_id: UUID
    relative_path: str
    metadata: dict[str, Any]
    body: str
    content_sha256: str
    storage_area: Literal["formal", "source", "draft", "system"]
    approval_state: Literal["confirmed", "pending", "invalid"]
    validity: str = "current"
    raw_sha256: str = Field(exclude=True)


class MutationResult(BaseModel):
    operation_id: str
    state: Literal["succeeded"] = "succeeded"
    changed_paths: list[str]
    page_versions: dict[str, str] = Field(default_factory=dict)
    saved_locally: bool = True


class SourceRecord(OpenModel):
    source_id: UUID
    role: Literal["source"] = "source"
    original_relative_path: str
    filename: str
    sha256: str
    created_at: datetime


class SourceDetail(BaseModel):
    source: SourceRecord
    text: str


class IntakeItem(OpenModel):
    item_id: UUID
    source_id: UUID
    title: str
    filename: str
    original_relative_path: str
    created_at: datetime
    state: Literal["pending", "processing", "completed", "cancelled"] = "pending"


class Draft(OpenModel):
    draft_id: UUID
    input_ids: list[UUID]
    target_page_id: UUID | None = None
    metadata: dict[str, Any]
    body: str
    expected_base_sha256: str | None = None
    important_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    action_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    conflict_resolutions: dict[str, str] = Field(default_factory=dict)
    source_ids: list[UUID]
    state: Literal["pending", "confirmed", "cancelled"] = "pending"
    created_at: datetime
    version: int = 1


class IntakeJob(OpenModel):
    job_id: UUID
    item_ids: list[UUID]
    request_hash: str
    state: Literal["running", "completed", "failed", "cancelled"]
    draft_ids: list[UUID] = Field(default_factory=list)
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime


class ActionCandidate(OpenModel):
    action_id: UUID
    kind: Literal["todo", "progress_change"]
    description: str
    related_project_id: UUID | None = None
    state: Literal["proposed"] = "proposed"
    source_draft_id: UUID
    created_at: datetime


class Citation(BaseModel):
    page_id: UUID
    content_sha256: str
    chunk_id: str
    heading: str
    excerpt: str
    validity: Literal["current", "superseded", "invalid"] = "current"


class Answer(BaseModel):
    answer_id: UUID
    question: str
    text: str
    citations: list[Citation] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    purpose: Literal["current", "history"] = "current"
    index_status: Literal["ready", "empty", "not_ready"]


class IndexPlan(BaseModel):
    plan_id: UUID
    workspace_id: UUID
    mode: Literal["initial", "incremental", "full", "model_change"]
    fingerprint: str
    page_ids: list[UUID]
    page_versions: dict[str, str] = Field(default_factory=dict)
    estimated_tokens: int
    estimated_cost: float = 0


class IndexResult(BaseModel):
    indexed_pages: int
    indexed_chunks: int
    embedded_chunks: int
    reused_chunks: int
    active_fingerprint: str
    saved_locally: bool = True
