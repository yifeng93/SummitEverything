"""FastAPI application factory for the local-only service."""

import json
import os
import secrets
from collections.abc import Iterator
from pathlib import Path
from threading import Event
from typing import Annotated, Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from summit_everything.domain.content import RetrievalPurpose
from summit_everything.domain.models import (
    ActionCandidate,
    Draft,
    IndexPlan,
    IndexResult,
    IntakeItem,
    IntakeJob,
    LineRecord,
    MutationResult,
    PageSnapshot,
    ProjectRecord,
    SourceDetail,
    WorkspaceContext,
)
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.llm import FakeLLM, LLMProviderError
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    WorkspaceError,
    create_line,
    create_project,
    create_workspace,
    delete_line,
    delete_project,
    list_lines,
    list_projects,
    open_workspace,
    update_line,
    update_project,
)
from summit_everything.workspace.reader import list_pages, read_page
from summit_everything.workspace.writer import (
    PageWriter,
    WorkspaceWriteConflict,
    WorkspaceWriter,
)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspaceRequest(RequestModel):
    root: str
    mode: str = Field(pattern="^(create|open)$")
    name: str | None = None
    operation_id: str = Field(min_length=1)


class LineCreate(RequestModel):
    name: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class LinePatch(RequestModel):
    name: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class ProjectCreate(RequestModel):
    line_id: UUID
    name: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class ProjectPatch(RequestModel):
    name: str | None = Field(default=None, min_length=1)
    archived: bool | None = None
    operation_id: str = Field(min_length=1)


class PageCreate(RequestModel):
    metadata: dict[str, Any]
    body: str
    confirmation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class PageConfirmation(PageCreate):
    expected_base_sha256: str = Field(pattern="^[0-9a-f]{64}$")


class PageMove(RequestModel):
    destination_relative_path: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    structure_confirmation_id: str | None = None


class IntakeTextRequest(RequestModel):
    text: str = Field(min_length=1)
    filename: str = Field(default="paste.txt", min_length=1)
    operation_id: str = Field(min_length=1)


class IntakeJobRequest(RequestModel):
    item_ids: list[UUID] = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    line_id: UUID
    project_id: UUID
    reprocess: bool = False


class DraftPatchRequest(RequestModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    target_page_id: UUID | None = None
    expected_base_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")


class DraftConfirmationRequest(RequestModel):
    expected_version: int = Field(ge=1)
    confirmation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    conflict_resolutions: dict[str, str] = Field(default_factory=dict)


class IndexPlanRequest(RequestModel):
    mode: str = Field(pattern="^(initial|incremental|full|model_change)$")
    fingerprint: str = Field(min_length=1)


class QueryRequest(RequestModel):
    question: str = Field(min_length=1)
    fingerprint: str = Field(min_length=1)
    purpose: Literal["current", "history"] = "current"
    request_id: UUID | None = None


class JournalRequest(RequestModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    line_id: UUID | None = None
    project_id: UUID | None = None
    confirmation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class LoopbackOnly(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = secrets.token_hex(8)
        host = request.client.host if request.client else ""
        if host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "forbidden", "message": "Local connections only"}},
            )
        return await call_next(request)


def create_app(
    *,
    session_token: str | None = None,
    profile_root: Path | None = None,
    review_service: IntakeReviewService | None = None,
    query_service: QueryService | None = None,
) -> FastAPI:
    app = FastAPI(title="SummitEverything Local API", version="1.0.0")
    app.add_middleware(LoopbackOnly)
    app.state.session_token = session_token or secrets.token_urlsafe(32)
    app.state.profile_root = profile_root or Path(
        os.environ.get(
            "SUMMIT_PROFILE_ROOT",
            str(Path.home() / "Library/Application Support/SummitEverything"),
        )
    )
    app.state.workspace = None
    intake_service = IntakeService()
    review = review_service or IntakeReviewService(FakeLLM())
    app.state.intake_service = intake_service
    app.state.review_service = review
    cancellations: dict[str, Event] = {}

    def authenticated(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {app.state.session_token}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthenticated", "message": "Session token required"},
            )

    def active_workspace() -> WorkspaceContext:
        workspace = cast(WorkspaceContext | None, app.state.workspace)
        if workspace is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "workspace_not_open", "message": "Open a workspace first"},
            )
        return workspace

    def query_for(workspace: WorkspaceContext) -> QueryService:
        if query_service is not None:
            return query_service
        return QueryService(IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3"))

    @app.exception_handler(WorkspaceError)
    async def workspace_error_handler(_request: Request, exc: WorkspaceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "workspace_error",
                    "message": str(exc),
                    "request_id": _request.state.request_id,
                }
            },
        )

    @app.exception_handler(WorkspaceWriteConflict)
    async def conflict_error_handler(request: Request, exc: WorkspaceWriteConflict) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "version_conflict",
                    "message": str(exc),
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(LLMProviderError)
    async def provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "provider_error",
                    "message": str(exc),
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "request_error", "message": str(exc.detail)}
        )
        detail = {**detail, "request_id": _request.state.request_id}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request contains invalid fields",
                    "request_id": _request.state.request_id,
                }
            },
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, str | bool]:
        workspace = app.state.workspace
        return {
            "service": "ready",
            "workspace_open": workspace is not None,
            "version": "1.0.0",
            "run_id": os.environ.get("SUMMIT_RUN_ID", "unmanaged"),
        }

    @app.post("/api/v1/workspaces", status_code=201, dependencies=[Depends(authenticated)])
    def workspace_open(payload: WorkspaceRequest) -> WorkspaceContext:
        root = Path(payload.root)
        if payload.mode == "create":
            if not payload.name or not payload.name.strip():
                raise HTTPException(
                    status_code=422,
                    detail={"code": "validation_error", "message": "Workspace name is required"},
                )
            context = create_workspace(
                root, payload.name, app.state.profile_root, payload.operation_id
            )
        else:
            context = open_workspace(root, app.state.profile_root)
        app.state.workspace = context
        return context

    @app.get("/api/v1/workspaces/current", dependencies=[Depends(authenticated)])
    def workspace_current(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> WorkspaceContext:
        return workspace

    @app.get("/api/v1/lines", dependencies=[Depends(authenticated)])
    def lines(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[LineRecord]:
        return list_lines(Path(workspace.root))

    @app.post("/api/v1/lines", status_code=201, dependencies=[Depends(authenticated)])
    def line_create(
        payload: LineCreate, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> LineRecord:
        return create_line(Path(workspace.root), payload.name, payload.operation_id)

    @app.patch("/api/v1/lines/{line_id}", dependencies=[Depends(authenticated)])
    def line_patch(
        line_id: UUID,
        payload: LinePatch,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> LineRecord:
        return update_line(Path(workspace.root), line_id, payload.name, payload.operation_id)

    @app.delete("/api/v1/lines/{line_id}", status_code=204, dependencies=[Depends(authenticated)])
    def line_delete(
        line_id: UUID,
        operation_id: str,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        delete_line(Path(workspace.root), line_id, operation_id)
        return Response(status_code=204)

    @app.get("/api/v1/projects", dependencies=[Depends(authenticated)])
    def projects(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[ProjectRecord]:
        return list_projects(Path(workspace.root))

    @app.post("/api/v1/projects", status_code=201, dependencies=[Depends(authenticated)])
    def project_create(
        payload: ProjectCreate, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> ProjectRecord:
        return create_project(
            Path(workspace.root), payload.line_id, payload.name, payload.operation_id
        )

    @app.patch("/api/v1/projects/{project_id}", dependencies=[Depends(authenticated)])
    def project_patch(
        project_id: UUID,
        payload: ProjectPatch,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> ProjectRecord:
        return update_project(
            Path(workspace.root),
            project_id,
            name=payload.name,
            archived=payload.archived,
            operation_id=payload.operation_id,
        )

    @app.delete(
        "/api/v1/projects/{project_id}", status_code=204, dependencies=[Depends(authenticated)]
    )
    def project_delete(
        project_id: UUID,
        operation_id: str,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        delete_project(Path(workspace.root), project_id, operation_id)
        return Response(status_code=204)

    @app.get("/api/v1/pages", dependencies=[Depends(authenticated)])
    def pages(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[PageSnapshot]:
        return list_pages(Path(workspace.root))

    @app.post("/api/v1/pages", status_code=201, dependencies=[Depends(authenticated)])
    def page_create(
        payload: PageCreate,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        return PageWriter().confirm(
            Path(workspace.root),
            metadata=payload.metadata,
            body=payload.body,
            confirmation_id=payload.confirmation_id,
            operation_id=payload.operation_id,
        )

    @app.get("/api/v1/pages/{page_id}", dependencies=[Depends(authenticated)])
    def page_get(
        page_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        expected_content_sha256: str | None = None,
    ) -> PageSnapshot:
        page = read_page(Path(workspace.root), page_id)
        if expected_content_sha256 is not None and page.content_sha256 != expected_content_sha256:
            raise WorkspaceWriteConflict("Page content has changed since this citation was created")
        return page

    @app.post("/api/v1/pages/{page_id}/confirmations", dependencies=[Depends(authenticated)])
    def page_confirmation(
        page_id: UUID,
        payload: PageConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        if str(payload.metadata.get("id")) != str(page_id):
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_error", "message": "Page ID does not match the route"},
            )
        return PageWriter().confirm(
            Path(workspace.root),
            metadata=payload.metadata,
            body=payload.body,
            confirmation_id=payload.confirmation_id,
            operation_id=payload.operation_id,
            expected_base_sha256=payload.expected_base_sha256,
        )

    @app.post("/api/v1/pages/{page_id}/moves", dependencies=[Depends(authenticated)])
    def page_move(
        page_id: UUID,
        payload: PageMove,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        return WorkspaceWriter().move_page(
            Path(workspace.root),
            page_id,
            payload.destination_relative_path,
            operation_id=payload.operation_id,
            structure_confirmation_id=payload.structure_confirmation_id,
        )

    @app.post("/api/v1/journal/{kind}", status_code=201, dependencies=[Depends(authenticated)])
    def journal_create(
        kind: Literal["log", "thought"],
        payload: JournalRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        metadata: dict[str, Any] = {
            "id": str(UUID(bytes=secrets.token_bytes(16), version=4)),
            "title": payload.title,
            "role": "knowledge",
            "kind": kind,
        }
        if payload.line_id is not None:
            metadata["line_id"] = str(payload.line_id)
        if payload.project_id is not None:
            metadata["project_id"] = str(payload.project_id)
        return PageWriter().confirm(
            Path(workspace.root),
            metadata=metadata,
            body=payload.body,
            confirmation_id=payload.confirmation_id,
            operation_id=payload.operation_id,
        )

    @app.post("/api/v1/intake/items", status_code=201, dependencies=[Depends(authenticated)])
    def intake_text(
        payload: IntakeTextRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IntakeItem:
        return intake_service.add_text(
            Path(workspace.root),
            payload.text,
            filename=payload.filename,
            operation_id=payload.operation_id,
        )

    @app.post("/api/v1/intake/files", status_code=201, dependencies=[Depends(authenticated)])
    async def intake_file(
        operation_id: Annotated[str, Form(min_length=1)],
        file: Annotated[UploadFile, File()],
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IntakeItem:
        raw = await file.read(20 * 1024 * 1024 + 1)
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail={"code": "file_too_large", "message": "File must be 20 MB or smaller"},
            )
        return intake_service.add_file(
            Path(workspace.root),
            raw,
            filename=file.filename or "source.txt",
            operation_id=operation_id,
        )

    @app.get("/api/v1/intake/items", dependencies=[Depends(authenticated)])
    def intake_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[IntakeItem]:
        return intake_service.list_items(Path(workspace.root))

    @app.get("/api/v1/sources/{source_id}", dependencies=[Depends(authenticated)])
    def source_get(
        source_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> SourceDetail:
        return intake_service.get_source(Path(workspace.root), source_id)

    @app.post("/api/v1/intake/jobs", status_code=201, dependencies=[Depends(authenticated)])
    def intake_job_create(
        payload: IntakeJobRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IntakeJob:
        return review.create_job(
            Path(workspace.root),
            payload.item_ids,
            operation_id=payload.operation_id,
            line_id=payload.line_id,
            project_id=payload.project_id,
            reprocess=payload.reprocess,
        )

    @app.get("/api/v1/jobs/{job_id}", dependencies=[Depends(authenticated)])
    def intake_job_get(
        job_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> IntakeJob:
        return review.get_job(Path(workspace.root), job_id)

    @app.delete("/api/v1/jobs/{job_id}", dependencies=[Depends(authenticated)])
    def intake_job_cancel(
        job_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> IntakeJob:
        return review.cancel_job(Path(workspace.root), job_id)

    @app.get("/api/v1/drafts", dependencies=[Depends(authenticated)])
    def drafts(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[Draft]:
        return review.list_drafts(Path(workspace.root))

    @app.get("/api/v1/drafts/{draft_id}", dependencies=[Depends(authenticated)])
    def draft_get(
        draft_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Draft:
        return review.get_draft(Path(workspace.root), draft_id)

    @app.patch("/api/v1/drafts/{draft_id}", dependencies=[Depends(authenticated)])
    def draft_patch(
        draft_id: UUID,
        payload: DraftPatchRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Draft:
        return review.edit_draft(
            Path(workspace.root),
            draft_id,
            expected_version=payload.expected_version,
            title=payload.title,
            body=payload.body,
            target_page_id=payload.target_page_id,
            expected_base_sha256=payload.expected_base_sha256,
        )

    @app.post("/api/v1/drafts/{draft_id}/confirmations", dependencies=[Depends(authenticated)])
    def draft_confirmation(
        draft_id: UUID,
        payload: DraftConfirmationRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        return review.confirm_draft(
            Path(workspace.root),
            draft_id,
            expected_version=payload.expected_version,
            confirmation_id=payload.confirmation_id,
            operation_id=payload.operation_id,
            conflict_resolutions=payload.conflict_resolutions,
        )

    @app.get("/api/v1/actions", dependencies=[Depends(authenticated)])
    def action_candidates(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[ActionCandidate]:
        return review.list_actions(Path(workspace.root))

    @app.post("/api/v1/index/plans", dependencies=[Depends(authenticated)])
    def index_plan(
        payload: IndexPlanRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IndexPlan:
        return query_for(workspace).plan(
            Path(workspace.root), fingerprint=payload.fingerprint, mode=payload.mode
        )

    @app.post("/api/v1/index/jobs", dependencies=[Depends(authenticated)])
    def index_execute(
        payload: IndexPlan,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IndexResult:
        return query_for(workspace).execute_plan(Path(workspace.root), payload)

    @app.get("/api/v1/index/status", dependencies=[Depends(authenticated)])
    def index_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, int | str | None]:
        store = IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3")
        return store.status(workspace.workspace_id)

    @app.post("/api/v1/queries", dependencies=[Depends(authenticated)])
    def query_stream(
        payload: QueryRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> StreamingResponse:
        request_id = str(payload.request_id or uuid4())
        if request_id in cancellations:
            raise HTTPException(
                status_code=409,
                detail={"code": "intent_conflict", "message": "查询标识已在使用"},
            )
        cancelled = Event()
        cancellations[request_id] = cancelled

        def event(seq: int, event_type: str, data: Any) -> str:
            value = {
                "request_id": request_id,
                "seq": seq,
                "type": event_type,
                "data": data,
            }
            return f"data: {json.dumps(value, ensure_ascii=False)}\n\n"

        def generate() -> Iterator[str]:
            seq = 0
            try:
                seq += 1
                yield event(seq, "status", {"state": "retrieving"})
                answer = query_for(workspace).query(
                    Path(workspace.root),
                    payload.question,
                    fingerprint=payload.fingerprint,
                    purpose=RetrievalPurpose(payload.purpose),
                )
                if cancelled.is_set():
                    seq += 1
                    yield event(seq, "error", {"code": "cancelled", "message": "查询已取消"})
                    return
                for citation in answer.citations:
                    seq += 1
                    yield event(seq, "citation", citation.model_dump(mode="json"))
                for offset in range(0, len(answer.text), 120):
                    if cancelled.is_set():
                        seq += 1
                        yield event(seq, "error", {"code": "cancelled", "message": "查询已取消"})
                        return
                    seq += 1
                    yield event(seq, "delta", {"text": answer.text[offset : offset + 120]})
                seq += 1
                yield event(seq, "completed", answer.model_dump(mode="json"))
            except Exception as exc:
                seq += 1
                yield event(seq, "error", {"code": "query_error", "message": str(exc)})
            finally:
                cancellations.pop(request_id, None)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.delete(
        "/api/v1/queries/{request_id}", status_code=202, dependencies=[Depends(authenticated)]
    )
    def query_cancel(request_id: UUID) -> dict[str, str]:
        cancellation = cancellations.get(str(request_id))
        if cancellation is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "查询已结束或不存在"},
            )
        cancellation.set()
        return {"request_id": str(request_id), "state": "cancellation_requested"}

    return app


app = create_app(session_token=os.environ.get("SUMMIT_SESSION_TOKEN"))
