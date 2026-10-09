"""Manifest parsing, workspace creation, and organization mutations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from pydantic import ValidationError

from summit_everything.domain.models import (
    LineRecord,
    ProjectRecord,
    WorkspaceContext,
    WorkspaceManifest,
)
from summit_everything.workspace.transactions import (
    IntentConflict,
    atomic_write,
    workspace_lock,
    write_intent,
)


class WorkspaceError(ValueError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _manifest_path(root: Path) -> Path:
    return root / ".summit-everything" / "manifest.json"


def _safe_directory(root: Path, directory: str) -> Path:
    rel = Path(directory)
    if rel.is_absolute() or not directory or any(part in {"..", "."} for part in rel.parts):
        raise WorkspaceError("Workspace directory must be a safe relative path")
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise WorkspaceError("Workspace directory escapes the selected root")
    return candidate


def load_manifest(root: Path) -> WorkspaceManifest:
    path = _manifest_path(root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        manifest = WorkspaceManifest.model_validate(value)
    except FileNotFoundError as exc:
        raise WorkspaceError("This directory is not a SummitEverything workspace", 409) from exc
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise WorkspaceError("Workspace manifest is invalid") from exc
    _validate_registry(root, manifest)
    return manifest


def _validate_registry(root: Path, manifest: WorkspaceManifest) -> None:
    line_ids = [line.id for line in manifest.lines]
    project_ids = [project.id for project in manifest.projects]
    if len(set(line_ids)) != len(line_ids) or len(set(project_ids)) != len(project_ids):
        raise WorkspaceError("Workspace contains duplicate organization IDs")
    if set(line_ids) & set(project_ids):
        raise WorkspaceError("Organization IDs must be globally unique")
    overview_ids = [project.overview_id for project in manifest.projects]
    if len(set(overview_ids)) != len(overview_ids) or set(overview_ids) & (
        set(line_ids) | set(project_ids)
    ):
        raise WorkspaceError("Workspace contains duplicate organization or overview IDs")
    line_directories = [line.directory for line in manifest.lines]
    project_directories = [project.directory for project in manifest.projects]
    if len(set(line_directories)) != len(line_directories) or len(set(project_directories)) != len(
        project_directories
    ):
        raise WorkspaceError("Workspace contains duplicate organization directories")
    for line in manifest.lines:
        _safe_directory(root, line.directory)
    for project in manifest.projects:
        _safe_directory(root, project.directory)
        if project.line_id not in line_ids:
            raise WorkspaceError("Project belongs to a line that does not exist")
        line = next(line for line in manifest.lines if line.id == project.line_id)
        if (
            Path(project.directory).parts[: len(Path(line.directory).parts)]
            != Path(line.directory).parts
        ):
            raise WorkspaceError("Project directory is outside its registered line")
        if project.overview_id in project_ids or project.overview_id in line_ids:
            raise WorkspaceError("Project overview ID conflicts with an organization ID")


def create_workspace(
    root: Path, name: str, profile_root: Path, operation_id: str
) -> WorkspaceContext:
    root = root.expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise WorkspaceError("Selected workspace path is not a directory")
    if not name.strip():
        raise WorkspaceError("Workspace name is required")
    manifest_root = root / ".summit-everything"
    operation_key = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    journal = manifest_root / "transactions" / f"workspace-create-{operation_key}.json"
    request_hash = hashlib.sha256(
        json.dumps(
            {"root": str(root), "name": name.strip()}, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if root.exists() and any(root.iterdir()) and not journal.exists():
        raise WorkspaceError(
            "Selected directory is not empty; existing data was left untouched", 409
        )
    root.mkdir(parents=True, exist_ok=True)
    if journal.exists():
        intent = json.loads(journal.read_text(encoding="utf-8"))
        if intent.get("request_hash") != request_hash:
            raise WorkspaceError("operation_id was already used for a different workspace", 409)
    else:
        manifest_root.mkdir(parents=True, exist_ok=True)
        intent = {
            "operation_id": operation_id,
            "request_hash": request_hash,
            "workspace_id": str(uuid4()),
            "name": name.strip(),
            "created_at": datetime.now(UTC).isoformat(),
            "state": "running",
        }
        atomic_write(journal, json.dumps(intent, sort_keys=True).encode("utf-8"))
    try:
        workspace_id = UUID(intent["workspace_id"])
        manifest = WorkspaceManifest(
            workspace_id=workspace_id,
            name=intent["name"],
            created_at=datetime.fromisoformat(intent["created_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkspaceError("Workspace creation journal is invalid") from exc
    manifest_path = _manifest_path(root)
    if manifest_path.exists():
        existing = load_manifest(root)
        if existing.workspace_id != workspace_id or existing.name != name.strip():
            raise WorkspaceError("Workspace identity conflicts with the creation intent", 409)
    else:
        manifest_root.mkdir(parents=True, exist_ok=True)
        atomic_write(manifest_path, manifest.model_dump_json(indent=2).encode("utf-8"))
    conventions = (
        b"# SummitEverything workspace\n\nSee the workspace contract for page and approval rules.\n"
    )
    conventions_path = root / "conventions.md"
    if conventions_path.exists() and conventions_path.read_bytes() != conventions:
        raise WorkspaceError("Workspace conventions file conflicts with the creation intent", 409)
    if not conventions_path.exists():
        atomic_write(conventions_path, conventions)
    intent.update(state="succeeded")
    atomic_write(journal, json.dumps(intent, sort_keys=True).encode("utf-8"))
    return WorkspaceContext(
        workspace_id=workspace_id,
        root=str(root),
        local_profile_dir=str(profile_root / str(workspace_id)),
        name=manifest.name,
    )


def open_workspace(root: Path, profile_root: Path) -> WorkspaceContext:
    root = root.expanduser().resolve()
    from summit_everything.workspace.writer import WorkspaceWriteConflict, WorkspaceWriter

    try:
        WorkspaceWriter().recover(root)
    except WorkspaceWriteConflict as exc:
        raise WorkspaceError(str(exc), 409) from exc
    manifest = load_manifest(root)
    return WorkspaceContext(
        workspace_id=manifest.workspace_id,
        root=str(root),
        local_profile_dir=str(profile_root / str(manifest.workspace_id)),
        name=manifest.name,
    )


def _slug(name: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", name.strip(), flags=re.UNICODE).strip("-")
    return slug or "new"


def _write_manifest(
    root: Path, operation_id: str, manifest: WorkspaceManifest, expected_hash: str
) -> None:
    path = _manifest_path(root)
    with workspace_lock(root):
        load_manifest(root)
        content = manifest.model_dump_json(indent=2).encode("utf-8")
        try:
            write_intent(root, operation_id, path, expected_hash, content)
        except IntentConflict as exc:
            raise WorkspaceError(str(exc), 409) from exc


def current_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_lines(root: Path) -> list[LineRecord]:
    return load_manifest(root).lines


def create_line(root: Path, name: str, operation_id: str) -> LineRecord:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    if not name.strip():
        raise WorkspaceError("Line name is required")
    line_id = uuid5(manifest.workspace_id, f"line:{operation_id}")
    existing = next((item for item in manifest.lines if item.id == line_id), None)
    if existing is not None:
        if existing.name != name.strip():
            raise WorkspaceError("operation_id was already used for a different line", 409)
        return existing
    if any(line.name.casefold() == name.strip().casefold() for line in manifest.lines):
        raise WorkspaceError("A line with this name already exists", 409)
    directory = _slug(name)
    if any(line.directory == directory for line in manifest.lines):
        directory = f"{directory}-{str(line_id)[:8]}"
    record = LineRecord(id=line_id, name=name.strip(), directory=directory)
    manifest.lines.append(record)
    path = _safe_directory(root, directory)
    if path.exists() and any(path.iterdir()):
        raise WorkspaceError("Line directory already contains unrelated data", 409)
    path.mkdir(parents=True, exist_ok=True)
    _write_manifest(root, operation_id, manifest, expected_hash)
    return record


def update_line(root: Path, line_id: UUID, name: str, operation_id: str) -> LineRecord:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    record = next((item for item in manifest.lines if item.id == line_id), None)
    if record is None:
        raise WorkspaceError("Line not found", 404)
    if not name.strip():
        raise WorkspaceError("Line name is required")
    if any(
        item.id != line_id and item.name.casefold() == name.strip().casefold()
        for item in manifest.lines
    ):
        raise WorkspaceError("A line with this name already exists", 409)
    record.name = name.strip()
    _write_manifest(root, operation_id, manifest, expected_hash)
    return record


def delete_line(root: Path, line_id: UUID, operation_id: str) -> None:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    if any(project.line_id == line_id for project in manifest.projects):
        raise WorkspaceError("A nonempty line must have its projects moved or archived first", 409)
    record = next((item for item in manifest.lines if item.id == line_id), None)
    if record is None:
        raise WorkspaceError("Line not found", 404)
    if any(_safe_directory(root, record.directory).iterdir()):
        raise WorkspaceError("A line containing pages cannot be deleted", 409)
    manifest.lines.remove(record)
    _write_manifest(root, operation_id, manifest, expected_hash)
    _safe_directory(root, record.directory).rmdir()


def list_projects(root: Path) -> list[ProjectRecord]:
    return load_manifest(root).projects


def create_project(root: Path, line_id: UUID, name: str, operation_id: str) -> ProjectRecord:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    if not any(line.id == line_id for line in manifest.lines):
        raise WorkspaceError("Line not found", 404)
    if not name.strip():
        raise WorkspaceError("Project name is required")
    project_id = uuid5(manifest.workspace_id, f"project:{operation_id}")
    existing = next((item for item in manifest.projects if item.id == project_id), None)
    if existing is not None:
        if existing.line_id != line_id or existing.name != name.strip():
            raise WorkspaceError("operation_id was already used for a different project", 409)
        return existing
    if any(
        item.line_id == line_id and item.name.casefold() == name.strip().casefold()
        for item in manifest.projects
    ):
        raise WorkspaceError("A project with this name already exists in the line", 409)
    directory = _slug(name)
    parent = next(line for line in manifest.lines if line.id == line_id)
    path = _safe_directory(root, parent.directory) / directory
    if path.exists():
        directory = f"{directory}-{str(project_id)[:8]}"
        path = _safe_directory(root, parent.directory) / directory
    record = ProjectRecord(
        id=project_id,
        line_id=line_id,
        name=name.strip(),
        directory=f"{parent.directory}/{directory}",
        overview_id=uuid5(manifest.workspace_id, f"project-overview:{operation_id}"),
    )
    manifest.projects.append(record)
    if path.exists() and any(path.iterdir()):
        raise WorkspaceError("Project directory already contains unrelated data", 409)
    path.mkdir(parents=True, exist_ok=True)
    _write_manifest(root, operation_id, manifest, expected_hash)
    return record


def update_project(
    root: Path, project_id: UUID, *, name: str | None, archived: bool | None, operation_id: str
) -> ProjectRecord:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    record = next((item for item in manifest.projects if item.id == project_id), None)
    if record is None:
        raise WorkspaceError("Project not found", 404)
    if name is not None:
        if not name.strip():
            raise WorkspaceError("Project name is required")
        if any(
            item.id != project_id
            and item.line_id == record.line_id
            and item.name.casefold() == name.strip().casefold()
            for item in manifest.projects
        ):
            raise WorkspaceError("A project with this name already exists in the line", 409)
        record.name = name.strip()
    if archived is not None:
        record.archived = archived
    _write_manifest(root, operation_id, manifest, expected_hash)
    return record


def delete_project(root: Path, project_id: UUID, operation_id: str) -> None:
    expected_hash = current_hash(_manifest_path(root))
    manifest = load_manifest(root)
    record = next((item for item in manifest.projects if item.id == project_id), None)
    if record is None:
        raise WorkspaceError("Project not found", 404)
    path = _safe_directory(root, record.directory)
    if any(path.iterdir()):
        raise WorkspaceError("A nonempty project must be archived", 409)
    manifest.projects.remove(record)
    _write_manifest(root, operation_id, manifest, expected_hash)
    path.rmdir()
