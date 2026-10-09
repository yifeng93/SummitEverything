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
