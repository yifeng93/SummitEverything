"""Validated Markdown page reads with path-derived storage classification."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID

import yaml

from summit_everything.domain.content import (
    RetrievalPurpose,
    StorageArea,
    content_sha256,
    retrieval_eligibility,
)
from summit_everything.domain.models import PageSnapshot, WorkspaceManifest
from summit_everything.workspace.manifest import WorkspaceError, _safe_directory, load_manifest

StorageName = Literal["formal", "source", "draft", "system"]
ApprovalState = Literal["confirmed", "pending", "invalid"]
KINDS = {"project_overview", "object", "case", "topic", "decision", "log", "thought"}


def _yaml_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_yaml_value(item) for item in value]
    return value


def _split_markdown(raw: bytes) -> tuple[dict[str, Any], str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError("Markdown page must be UTF-8") from exc
    if text.startswith("\ufeff"):
        raise WorkspaceError("Formal Markdown must not start with a BOM")
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        raise WorkspaceError("Markdown page is missing YAML frontmatter")
    lines = text.splitlines(keepends=True)
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
    if end is None:
        raise WorkspaceError("Markdown frontmatter is not closed")
    try:
        metadata = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise WorkspaceError("Markdown frontmatter is invalid YAML") from exc
    if not isinstance(metadata, dict):
        raise WorkspaceError("Markdown frontmatter must be an object")
    return _yaml_value(metadata), "".join(lines[end + 1 :])


def _expected_location(manifest: WorkspaceManifest, metadata: dict[str, Any]) -> StorageName:
    try:
        page_id = UUID(str(metadata.get("id")))
    except (ValueError, TypeError) as exc:
        raise WorkspaceError("Page id must be a UUID") from exc
    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        raise WorkspaceError("Page title is required")
    role = metadata.get("role")
    if role in {"source", "draft", "system"}:
        return cast(StorageName, role)
    if role != "knowledge":
        raise WorkspaceError("Page role must be knowledge, source, draft, or system")
    kind = metadata.get("kind")
    if kind not in KINDS:
        raise WorkspaceError("Page kind is not supported")
    if kind in {"log", "thought"}:
        line_value, project_value = metadata.get("line_id"), metadata.get("project_id")
        if line_value is None and project_value is None:
            return "formal"
        try:
            line_id = UUID(str(line_value))
            project_id = UUID(str(project_value)) if project_value is not None else None
        except (ValueError, TypeError) as exc:
            raise WorkspaceError("Journal page organization IDs must be UUIDs") from exc
        line = next((item for item in manifest.lines if item.id == line_id), None)
        project = next((item for item in manifest.projects if item.id == project_id), None)
        if line is None or (
            project_id is not None and (project is None or project.line_id != line_id)
        ):
            raise WorkspaceError("Journal page organization does not match the registry")
        return "formal"
    try:
        line_id = UUID(str(metadata.get("line_id")))
        project_id = UUID(str(metadata.get("project_id")))
    except (ValueError, TypeError) as exc:
        raise WorkspaceError("Formal page requires valid line_id and project_id") from exc
    line = next((item for item in manifest.lines if item.id == line_id), None)
    project = next((item for item in manifest.projects if item.id == project_id), None)
    if line is None or project is None or project.line_id != line_id:
        raise WorkspaceError("Page line and project ownership do not match the registry")
    if page_id == project.overview_id and kind != "project_overview":
        raise WorkspaceError("Project overview page has an invalid kind")
    return "formal"


def _project_path(
    root: Path, manifest: WorkspaceManifest, path: Path, project_id: UUID | None
) -> bool:
    project = next((item for item in manifest.projects if item.id == project_id), None)
    return project is not None and path.is_relative_to(_safe_directory(root, project.directory))


def _page_paths(root: Path, manifest: WorkspaceManifest) -> list[Path]:
    paths: list[Path] = []
    for project in manifest.projects:
        project_root = _safe_directory(root, project.directory)
        if project_root.exists():
            paths.extend(project_root.rglob("*.md"))
    for directory in ("工作日志", "工作思考"):
        journal_root = root / directory
        if journal_root.exists():
            paths.extend(journal_root.rglob("*.md"))
    return sorted(set(paths))


def _validate_location(
    root: Path, manifest: WorkspaceManifest, path: Path, metadata: dict[str, Any]
) -> StorageName:
    area = _expected_location(manifest, metadata)
    if area != "formal":
        return area
    kind = metadata.get("kind")
    project_value = metadata.get("project_id")
    project_id = UUID(str(project_value)) if project_value is not None else None
    if kind not in {"log", "thought"}:
        if _project_path(root, manifest, path, project_id):
            return area
        raise WorkspaceError("Formal page is outside its registered project directory")
    if project_id is not None:
        if _project_path(root, manifest, path, project_id):
            return area
        raise WorkspaceError("Journal page is outside its registered project directory")
    expected = "工作日志" if kind == "log" else "工作思考"
    relative = path.relative_to(root)
    if relative.parts[0] != expected:
        raise WorkspaceError("Unbound journal page is outside its journal directory")
    return area


def _approval_state(metadata: dict[str, Any], body: str, area: StorageName) -> ApprovalState:
    if "approval" not in metadata:
        return "pending"
    result = retrieval_eligibility(
        metadata,
        body,
        area=StorageArea(area),
        purpose=RetrievalPurpose.CURRENT,
    )
    return "confirmed" if result.eligible else "invalid"


def _snapshot(
    root: Path, path: Path, metadata: dict[str, Any], body: str, area: StorageName
) -> PageSnapshot:
    try:
        page_id = UUID(str(metadata["id"]))
        digest = content_sha256(metadata, body)
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError("Page identity or metadata is invalid") from exc
    return PageSnapshot(
        page_id=page_id,
        relative_path=path.relative_to(root).as_posix(),
        metadata=metadata,
        body=body,
        content_sha256=digest,
        storage_area=area,
        approval_state=_approval_state(metadata, body, area),
        validity=str(metadata.get("validity", "current")),
    )


def list_pages(root: Path) -> list[PageSnapshot]:
    root = root.resolve()
    manifest = load_manifest(root)
    pages: list[PageSnapshot] = []
    seen: set[UUID] = set()
    for path in _page_paths(root, manifest):
        metadata, body = _split_markdown(path.read_bytes())
        area = _validate_location(root, manifest, path, metadata)
        if area != "formal":
            continue
        snapshot = _snapshot(root, path, metadata, body, area)
        if snapshot.page_id in seen:
            raise WorkspaceError("Workspace contains duplicate page IDs")
        seen.add(snapshot.page_id)
        pages.append(snapshot)
    return pages


def read_page(root: Path, page_id: UUID) -> PageSnapshot:
    pages = list_pages(root)
    page = next((item for item in pages if item.page_id == page_id), None)
    if page is None:
        raise WorkspaceError("Page not found", 404)
    return page
