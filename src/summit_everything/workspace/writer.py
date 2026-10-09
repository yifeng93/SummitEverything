"""Idempotent workspace mutations and explicit knowledge confirmation."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import UUID

import yaml

from summit_everything.domain.content import (
    RetrievalPurpose,
    StorageArea,
    content_sha256,
    retrieval_eligibility,
)
from summit_everything.domain.models import MutationResult, WorkspaceManifest
from summit_everything.workspace.manifest import (
    WorkspaceError,
    _safe_directory,
    load_manifest,
)
from summit_everything.workspace.reader import _expected_location, _split_markdown, list_pages
from summit_everything.workspace.transactions import (
    atomic_delete,
    atomic_write,
    workspace_lock,
)

_INLINE_LINK = re.compile(r"(?P<opening>!?\[[^\]]*\]\()(?P<target>[^\s)]+)(?P<tail>[^)]*\))")
_INLINE_CODE = re.compile(r"(`+)(.+?)\1")


def _rewrite_local_links(body: str, *, source_path: str, old_target: str, new_target: str) -> str:
    def rewrite_segment(segment: str) -> str:
        def replace(match: re.Match[str]) -> str:
            target = match.group("target")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
                return match.group(0)
            resolved = os.path.normpath(
                os.path.join(os.path.dirname(source_path), unquote(parsed.path))
            )
            if resolved != old_target:
                return match.group(0)
            relative_target = os.path.relpath(new_target, start=os.path.dirname(source_path) or ".")
            updated = relative_target
            if parsed.query:
                updated += f"?{parsed.query}"
            if parsed.fragment:
                updated += f"#{parsed.fragment}"
            return f"{match.group('opening')}{updated}{match.group('tail')}"

        return _INLINE_LINK.sub(replace, segment)

    result: list[str] = []
    fence: tuple[str, int] | None = None
    for line in body.splitlines(keepends=True):
        trimmed = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", trimmed)
        if fence is not None:
            result.append(line)
            if fence_match and fence_match.group(1)[0] == fence[0]:
                if len(fence_match.group(1)) >= fence[1]:
                    fence = None
            continue
        if fence_match:
            fence = (fence_match.group(1)[0], len(fence_match.group(1)))
            result.append(line)
            continue
        cursor = 0
        for code_span in _INLINE_CODE.finditer(line):
            result.append(rewrite_segment(line[cursor : code_span.start()]))
            result.append(code_span.group(0))
            cursor = code_span.end()
        result.append(rewrite_segment(line[cursor:]))
    return "".join(result)


class WorkspaceWriteConflict(ValueError):
    """A mutation cannot safely be replayed against the current workspace."""


def _operation_path(root: Path, operation_id: str) -> Path:
    key = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    return root / ".summit-everything" / "transactions" / f"mutation-{key}.json"


def _safe_target(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or relative.parts[0] in {".summit-everything", "原件"}
    ):
        raise WorkspaceWriteConflict("Mutation path is reserved or escapes the workspace")
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise WorkspaceWriteConflict("Mutation path escapes the workspace")
    return target


def _read_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _result(intent: dict[str, Any]) -> MutationResult:
    return MutationResult(
        operation_id=intent["operation_id"],
        changed_paths=[change["path"] for change in intent["changes"]],
        page_versions=intent.get("page_versions", {}),
    )


def _read_intent(path: Path) -> dict[str, Any]:
    try:
        intent = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkspaceWriteConflict("Workspace transaction journal is invalid") from exc
    if (
        not isinstance(intent, dict)
        or intent.get("schema") != "workspace-mutation-v1"
        or not isinstance(intent.get("operation_id"), str)
        or intent.get("state") not in {"running", "succeeded"}
        or not isinstance(intent.get("intent_hash"), str)
        or not isinstance(intent.get("changes"), list)
        or not isinstance(intent.get("page_versions"), dict)
        or not isinstance(intent.get("applied_paths"), list)
    ):
        raise WorkspaceWriteConflict("Workspace transaction journal is invalid")
    for change in intent["changes"]:
        if (
            not isinstance(change, dict)
            or not isinstance(change.get("path"), str)
            or (
                change.get("expected_hash") is not None
                and not isinstance(change.get("expected_hash"), str)
            )
            or (
                change.get("target_hash") is not None
                and not isinstance(change.get("target_hash"), str)
            )
        ):
            raise WorkspaceWriteConflict("Workspace transaction journal is invalid")
    return intent


class WorkspaceWriter:
    """Persist one or more files using a durable, forward-recoverable journal."""

    def lookup(self, root: Path, operation_id: str, intent_hash: str) -> MutationResult | None:
        root = root.resolve()
        with workspace_lock(root):
            journal_path = _operation_path(root, operation_id)
            if not journal_path.exists():
                return None
            intent = _read_intent(journal_path)
            self._check_intent(intent, operation_id, intent_hash)
            if intent.get("state") != "succeeded":
                intent = self._resume(root, journal_path, intent)
            return _result(intent)

    def apply(
        self,
        operation_id: str,
        root: Path,
        expected_versions: dict[str, str | None],
        changes: dict[str, bytes | None],
        *,
        page_versions: dict[str, str] | None = None,
        intent_payload_hash: str | None = None,
    ) -> MutationResult:
        root = root.resolve()
        self.recover(root)
        if not operation_id.strip() or set(expected_versions) != set(changes) or not changes:
            raise WorkspaceWriteConflict("A mutation needs an ID and matching expected versions")
        normalized: list[dict[str, Any]] = []
        for relative_path in sorted(changes):
            target = _safe_target(root, relative_path)
            data = changes[relative_path]
            if data is not None and not isinstance(data, bytes):
                raise WorkspaceWriteConflict("Workspace changes must contain bytes or deletion")
            normalized.append(
                {
                    "path": relative_path,
                    "expected_hash": expected_versions[relative_path],
                    "target_hash": hashlib.sha256(data).hexdigest() if data is not None else None,
                    "content_b64": base64.b64encode(data).decode("ascii")
                    if data is not None
                    else None,
                }
            )
        payload_hash = (
            intent_payload_hash
            or hashlib.sha256(
                json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        )
        journal_path = _operation_path(root, operation_id)
        with workspace_lock(root):
            if journal_path.exists():
                intent = _read_intent(journal_path)
                self._check_intent(intent, operation_id, payload_hash)
                if intent.get("state") == "succeeded":
                    return _result(intent)
                return _result(self._resume(root, journal_path, intent))
            for change in normalized:
                target = _safe_target(root, change["path"])
                if _read_digest(target) != change["expected_hash"]:
                    raise WorkspaceWriteConflict("Workspace content changed since it was read")
            intent = {
                "schema": "workspace-mutation-v1",
                "operation_id": operation_id,
                "intent_hash": payload_hash,
                "state": "running",
                "changes": normalized,
                "page_versions": page_versions or {},
                "applied_paths": [],
            }
            atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
            return _result(self._resume(root, journal_path, intent))

    def recover(self, root: Path) -> None:
        root = root.resolve()
        journal_root = root / ".summit-everything" / "transactions"
        if not journal_root.exists():
            return
        with workspace_lock(root):
            for journal_path in sorted(journal_root.glob("mutation-*.json")):
                intent = _read_intent(journal_path)
                if (
                    intent.get("schema") == "workspace-mutation-v1"
                    and intent.get("state") != "succeeded"
                ):
                    self._resume(root, journal_path, intent)

    def _check_intent(self, intent: dict[str, Any], operation_id: str, payload_hash: str) -> None:
        if (
            intent.get("schema") != "workspace-mutation-v1"
            or intent.get("operation_id") != operation_id
        ):
            raise WorkspaceWriteConflict("Workspace mutation journal is invalid")
        if intent.get("intent_hash") != payload_hash:
            raise WorkspaceWriteConflict("operation_id was already used for a different payload")

    def _resume(self, root: Path, journal_path: Path, intent: dict[str, Any]) -> dict[str, Any]:
        for change in intent["changes"]:
            target = _safe_target(root, change["path"])
            current_hash = _read_digest(target)
            if current_hash == change["target_hash"]:
                continue
            if current_hash != change["expected_hash"]:
                raise WorkspaceWriteConflict(
                    "Workspace changed while an interrupted operation was pending"
                )
            if change["target_hash"] is None:
                atomic_delete(target)
            else:
                content_b64 = change.get("content_b64")
                if not isinstance(content_b64, str):
                    raise WorkspaceWriteConflict("Workspace mutation journal content is corrupt")
                content = base64.b64decode(content_b64, validate=True)
                if hashlib.sha256(content).hexdigest() != change["target_hash"]:
                    raise WorkspaceWriteConflict("Workspace mutation journal content is corrupt")
                atomic_write(target, content)
            intent["applied_paths"].append(change["path"])
            atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
        intent["state"] = "succeeded"
        for change in intent["changes"]:
            change.pop("content_b64", None)
        atomic_write(journal_path, json.dumps(intent, sort_keys=True).encode("utf-8"))
        return intent

    def move_page(
        self,
        root: Path,
        page_id: UUID,
        destination_relative_path: str,
        *,
        operation_id: str,
        structure_confirmation_id: str | None = None,
    ) -> MutationResult:
        root = root.resolve()
        semantic_hash = hashlib.sha256(
            json.dumps(
                {
                    "page_id": str(page_id),
                    "destination": destination_relative_path,
                    "structure_confirmation_id": structure_confirmation_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        prior = self.lookup(root, operation_id, semantic_hash)
        if prior is not None:
            return prior
        pages = list_pages(root)
        page = next((item for item in pages if item.page_id == page_id), None)
        if page is None:
            raise WorkspaceError("Page not found", 404)
        if page.approval_state != "confirmed" or page.validity != "current":
            raise WorkspaceWriteConflict("Only a currently confirmed page can be moved")
        metadata = page.metadata
        project_id = metadata.get("project_id")
        if not isinstance(project_id, str):
            raise WorkspaceWriteConflict("Unbound journal pages cannot be moved into a project")
        manifest = load_manifest(root)
        project = next((item for item in manifest.projects if str(item.id) == project_id), None)
        if project is None:
            raise WorkspaceError("Page project no longer exists", 409)
        destination = _safe_target(root, destination_relative_path)
        destination_project = next(
            (
                item
                for item in manifest.projects
                if destination.resolve().is_relative_to(_safe_directory(root, item.directory))
            ),
            None,
        )
        if destination_project is None:
            raise WorkspaceWriteConflict("Page destination must be inside a registered project")
        cross_project = destination_project.id != project.id
        if cross_project and not (structure_confirmation_id or "").strip():
            raise WorkspaceWriteConflict("Cross-project move needs confirmation")
        if (
            cross_project
            and metadata.get("kind") == "project_overview"
            and page_id != destination_project.overview_id
        ):
            raise WorkspaceWriteConflict(
                "A project overview cannot become another project's overview"
            )
        if destination.suffix.lower() != ".md":
            raise WorkspaceWriteConflict("Page destination must be a Markdown file")
        if destination_relative_path == page.relative_path:
            raise WorkspaceWriteConflict("Page is already at the requested location")
        if destination.exists():
            raise WorkspaceWriteConflict("A page already occupies the requested path")

        changes: dict[str, bytes | None] = {page.relative_path: None}
        expected_versions: dict[str, str | None] = {page.relative_path: page.raw_sha256}
        page_versions: dict[str, str] = {}
        for candidate in pages:
            source_path = root / candidate.relative_path
            raw = source_path.read_bytes()
            candidate_metadata, body = _split_markdown(raw)
            moved_page = candidate.page_id == page.page_id
            if moved_page and cross_project:
                candidate_metadata["line_id"] = str(destination_project.line_id)
                candidate_metadata["project_id"] = str(destination_project.id)
            link_base = (
                destination_relative_path
                if candidate.page_id == page.page_id
                else candidate.relative_path
            )
            updated_body = _rewrite_local_links(
                body,
                source_path=link_base,
                old_target=page.relative_path,
                new_target=destination_relative_path,
            )
            ownership_changed = moved_page and cross_project
            if moved_page or updated_body != body:
                if (
                    updated_body != body or ownership_changed
                ) and candidate.approval_state == "confirmed":
                    proof = candidate_metadata.get("approval")
                    if isinstance(proof, dict):
                        proof["content_sha256"] = content_sha256(candidate_metadata, updated_body)
                        if ownership_changed:
                            proof["confirmation_id"] = structure_confirmation_id
                            proof["confirmed_at"] = datetime.now(UTC).isoformat()
                serialized = yaml.safe_dump(
                    candidate_metadata,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
                rendered = f"---\n{serialized}---\n{updated_body}".encode()
                target_rel = (
                    destination_relative_path
                    if candidate.page_id == page.page_id
                    else candidate.relative_path
                )
                changes[target_rel] = rendered
                expected_versions[target_rel] = (
                    None if target_rel == destination_relative_path else candidate.raw_sha256
                )
                page_versions[str(candidate.page_id)] = content_sha256(
                    candidate_metadata, updated_body
                )
        return self.apply(
            operation_id,
            root,
            expected_versions,
            changes,
            page_versions=page_versions,
            intent_payload_hash=semantic_hash,
        )


class PageWriter:
    """Turn an explicitly confirmed full page into the approved current version."""

    def __init__(self, writer: WorkspaceWriter | None = None) -> None:
        self.writer = writer or WorkspaceWriter()

    def confirm(
        self,
        root: Path,
        *,
        metadata: dict[str, Any],
        body: str,
        confirmation_id: str,
        operation_id: str,
        expected_base_sha256: str | None = None,
    ) -> MutationResult:
        root = root.resolve()
        if not confirmation_id.strip():
            raise WorkspaceError("User confirmation ID is required")
        clean_metadata = {key: value for key, value in metadata.items() if key != "approval"}
        clean_body = body.replace("\r\n", "\n").replace("\r", "\n")
        try:
            page_id = UUID(str(clean_metadata.get("id")))
            base_content_hash = content_sha256(clean_metadata, clean_body)
        except (TypeError, ValueError) as exc:
            raise WorkspaceError("Page identity or content metadata is invalid") from exc
        intent_hash = hashlib.sha256(
            json.dumps(
                {
                    "page_id": str(page_id),
                    "content_sha256": base_content_hash,
                    "confirmation_id": confirmation_id,
                    "expected_base_sha256": expected_base_sha256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        prior = self.writer.lookup(root, operation_id, intent_hash)
        if prior is not None:
            return prior
        manifest = load_manifest(root)
        if clean_metadata.get("role") != "knowledge":
            raise WorkspaceError("Only knowledge pages can be explicitly confirmed")
        if _expected_location(manifest, clean_metadata) != StorageArea.FORMAL.value:
            raise WorkspaceError("Page is not in formal storage")
        current_pages = list_pages(root)
        current = next((page for page in current_pages if page.page_id == page_id), None)
        if current is not None:
            if expected_base_sha256 is None or current.content_sha256 != expected_base_sha256:
                raise WorkspaceWriteConflict("Page changed since it was reviewed")
            if any(
                clean_metadata.get(key) != current.metadata.get(key)
                for key in ("line_id", "project_id")
            ):
                raise WorkspaceWriteConflict("Page ownership changes need structure confirmation")
            relative_path = current.relative_path
            expected_file_hash: str | None = current.raw_sha256
        else:
            if expected_base_sha256 is not None:
                raise WorkspaceWriteConflict("The reviewed page no longer exists")
            relative_path = self._new_page_path(root, manifest, clean_metadata, page_id)
            expected_file_hash = None
        approval = {
            "version": 1,
            "content_sha256": base_content_hash,
            "confirmed_at": datetime.now(UTC).isoformat(),
            "confirmation_id": confirmation_id,
        }
        approved_metadata = {**clean_metadata, "approval": approval}
        eligibility = retrieval_eligibility(
            approved_metadata,
            clean_body,
            area=StorageArea.FORMAL,
            purpose=(
                RetrievalPurpose.HISTORY
                if approved_metadata.get("validity") == "superseded"
                else RetrievalPurpose.CURRENT
            ),
        )
        if not eligibility.eligible:
            raise WorkspaceError(f"Page cannot be confirmed: {eligibility.reason}")
        serialized = yaml.safe_dump(
            approved_metadata,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        content = f"---\n{serialized}---\n{clean_body}".encode()
        result = self.writer.apply(
            operation_id,
            root,
            {relative_path: expected_file_hash},
            {relative_path: content},
            page_versions={str(page_id): base_content_hash},
            intent_payload_hash=intent_hash,
        )
        return result

    def _new_page_path(
        self,
        root: Path,
        manifest: WorkspaceManifest,
        metadata: dict[str, Any],
        page_id: UUID,
    ) -> str:
        kind = metadata["kind"]
        project_value = metadata.get("project_id")
        if kind in {"log", "thought"} and project_value is None:
            directory = root / ("工作日志" if kind == "log" else "工作思考")
        else:
            project = next(
                (item for item in manifest.projects if str(item.id) == str(project_value)), None
            )
            if project is None:
                raise WorkspaceError("Target project does not exist", 404)
            directory = _safe_directory(root, project.directory)
        title = str(metadata["title"]).strip()
        slug = re.sub(r"[^\w-]+", "-", title, flags=re.UNICODE).strip("-") or "page"
        target = directory / f"{slug}.md"
        if target.exists():
            target = directory / f"{slug}-{str(page_id)[:8]}.md"
        if target.exists():
            raise WorkspaceWriteConflict("A page already occupies the generated path")
        return target.relative_to(root).as_posix()
