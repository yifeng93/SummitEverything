"""FastAPI application factory for the local-only service."""

import os
import secrets
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from summit_everything.domain.models import (
    LineRecord,
    PageSnapshot,
    ProjectRecord,
    WorkspaceContext,
)
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


def create_app(*, session_token: str | None = None, profile_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="SummitEverything Local API", version="1.0.0")
    app.add_middleware(LoopbackOnly)
    app.state.session_token = session_token or secrets.token_urlsafe(32)
    app.state.profile_root = (
        profile_root or Path.home() / "Library/Application Support/SummitEverything"
    )
    app.state.workspace = None

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
        return {"service": "ready", "workspace_open": workspace is not None, "version": "1.0.0"}

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

    @app.get("/api/v1/pages/{page_id}", dependencies=[Depends(authenticated)])
    def page_get(
        page_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> PageSnapshot:
        return read_page(Path(workspace.root), page_id)

    return app


app = create_app(session_token=os.environ.get("SUMMIT_SESSION_TOKEN"))
