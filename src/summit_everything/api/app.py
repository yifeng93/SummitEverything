"""FastAPI application factory for the local-only service."""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from threading import Event, Lock
from typing import Annotated, Any, Literal, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4, uuid5

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from summit_everything.api.routes.actions import register_actions
from summit_everything.domain.content import RetrievalPurpose, StorageArea, retrieval_eligibility
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
from summit_everything.intake.actions import ActionService
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeConflict, IntakeService
from summit_everything.integrations.embedding import ModelStudioEmbedding
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.feishu.provider import (
    CalendarPage,
    CredentialStore,
    FeishuConfig,
    FeishuError,
    FeishuProvider,
    MaterialPage,
    MemoryCredentialStore,
    VaultCredentialStore,
)
from summit_everything.integrations.feishu.service import (
    AuthorizationStart,
    FeishuAuthCoordinator,
    FeishuService,
    FeishuStatus,
    ImportRequest,
    ImportResult,
    callback_boundary,
)
from summit_everything.integrations.feishu.tasks import FeishuTasks
from summit_everything.integrations.llm import DeepSeekLLM, FakeLLM, LLMProviderError
from summit_everything.integrations.provider_smoke import (
    SMOKE_LIMITS,
    SmokeLimitReached,
    reserve_smoke_call,
    smoke_counts,
)
from summit_everything.integrations.rerank import ModelStudioReranker
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import (
    CredentialVault,
    MacOSKeychainBackend,
    ProviderSettingsPatch,
    SecretBackend,
    SettingsError,
    SettingsStore,
    SettingsSummary,
    UnavailableSecretBackend,
    embedding_fingerprint,
    provider_settings_payload,
)
from summit_everything.local.answer_context import (
    AnswerContext,
    AnswerContextStore,
    AnswerRole,
    ContextConflict,
    MemoryCandidate,
    RoleInput,
    UserMemory,
)
from summit_everything.local.conversations import (
    ACTIVE_QUERIES,
    ConversationDetail,
    ConversationNotFound,
    ConversationPage,
    ConversationStore,
    QueryConflict,
    QueryStart,
)
from summit_everything.retrieval.query import AnswerProvider, QueryCancelled, QueryService
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
    load_manifest,
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
    question: str = Field(min_length=1, max_length=8000)
    fingerprint: str = Field(min_length=1)
    purpose: Literal["current", "history"] = "current"
    answer_mode: Literal["fact", "comparison", "plan"] = "fact"
    role_id: UUID | None = None
    request_id: UUID | None = None
    conversation_id: UUID | None = None


class MemoryCandidateRequest(RequestModel):
    message_id: UUID
    text: str = Field(min_length=1, max_length=4000)
    user_expression: Literal[True]


class MemoryConfirmationRequest(RequestModel):
    confirmation_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)


class MemoryPatchRequest(RequestModel):
    text: str = Field(min_length=1, max_length=4000)


class JournalRequest(RequestModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    line_id: UUID | None = None
    project_id: UUID | None = None
    confirmation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class ProjectOverviewConfirmation(RequestModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    confirmation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    expected_content_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")


class JournalAssistRequest(RequestModel):
    text: str = Field(min_length=1)


class JournalAssistResponse(BaseModel):
    title: str
    body: str


class CredentialRequest(RequestModel):
    account_id: str = Field(min_length=1, max_length=200)
    secret: SecretStr = Field(min_length=1, max_length=20_000, repr=False)


class CredentialAccountRequest(RequestModel):
    account_id: str = Field(min_length=1, max_length=200)


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


class CallbackAccessLogFilter(logging.Filter):
    """Remove OAuth callback query parameters from Uvicorn access logs."""

    _callback_paths = {"/callback", "/api/v1/integrations/feishu/callback"}

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3:
            path = args[2]
            if isinstance(path, str) and path.partition("?")[0] in self._callback_paths:
                record.args = (*args[:2], path.partition("?")[0] + "?[redacted]", *args[3:])
        return True


def create_app(
    *,
    session_token: str | None = None,
    profile_root: Path | None = None,
    review_service: IntakeReviewService | None = None,
    query_service: QueryService | None = None,
    feishu_provider: FeishuProvider | None = None,
    credential_store: CredentialStore | None = None,
    secret_backend: SecretBackend | None = None,
    feishu_config: FeishuConfig | None = None,
) -> FastAPI:
    app = FastAPI(title="SummitEverything Local API", version="1.0.0")
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, CallbackAccessLogFilter) for item in access_logger.filters):
        access_logger.addFilter(CallbackAccessLogFilter())
    app.add_middleware(LoopbackOnly)
    app.state.session_token = session_token or secrets.token_urlsafe(32)
    app.state.profile_root = profile_root or Path(
        os.environ.get(
            "SUMMIT_PROFILE_ROOT",
            str(Path.home() / "Library/Application Support/SummitEverything"),
        )
    )
    if secret_backend is None:
        try:
            secret_backend = MacOSKeychainBackend()
        except SettingsError:
            secret_backend = UnavailableSecretBackend()
    app.state.secret_backend = secret_backend
    app.state.workspace = None
    intake_service = IntakeService()
    review = review_service or IntakeReviewService(FakeLLM())
    app.state.intake_service = intake_service
    app.state.review_service = review
    cancellations: dict[tuple[str, str, str], Event] = {}
    cancellation_requests: set[tuple[str, str, str]] = set()
    config = feishu_config or FeishuConfig()
    feishu_services: dict[tuple[str, ...], FeishuService] = {}
    auth_coordinators: dict[tuple[str, str], FeishuAuthCoordinator] = {}
    action_services: dict[int, ActionService] = {}
    feishu_services_lock = Lock()
    feishu = FeishuService(
        feishu_provider
        or FakeFeishu(
            Path(tempfile.gettempdir())
            / "summit-simulated-feishu-remote"
            / hashlib.sha256(str(app.state.profile_root).encode()).hexdigest()
        ),
        credential_store or MemoryCredentialStore(),
        config,
        app.state.session_token,
    )
    app.state.feishu_service = feishu

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        origin = request.headers.get("origin")
        workspace = cast(WorkspaceContext | None, app.state.workspace)
        allowed_origins = config.allowed_origins
        if workspace is not None:
            settings = SettingsStore(
                Path(workspace.local_profile_dir) / "provider-settings.json"
            ).read()
            callback = settings.feishu.redirect_uri or config.redirect_uri
            parts = urlsplit(callback)
            callback_origin = f"{parts.scheme}://{parts.netloc}"
            allowed_origins = tuple(dict.fromkeys((*allowed_origins, callback_origin)))
        if origin is not None and origin not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {"code": "forbidden_origin", "message": "只允许配置的本机页面访问。"}
                },
            )
        response = await call_next(request)
        if request.url.path in {"/api/v1/integrations/feishu/callback", "/callback"}:
            response.headers["Cache-Control"] = "no-store"
            if origin is not None:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
        return response

    @app.exception_handler(FeishuError)
    async def feishu_error_handler(request: Request, exc: FeishuError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(IntakeConflict)
    async def intake_conflict_handler(request: Request, exc: IntakeConflict) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "intent_conflict",
                    "message": str(exc),
                    "request_id": request.state.request_id,
                }
            },
        )

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

    def settings_store(workspace: WorkspaceContext) -> SettingsStore:
        return SettingsStore(Path(workspace.local_profile_dir) / "provider-settings.json")

    def feishu_for(workspace: WorkspaceContext) -> FeishuService:
        settings = settings_store(workspace).read()
        app_id = settings.feishu.app_id or config.app_id
        redirect_uri = settings.feishu.redirect_uri or config.redirect_uri
        parts = urlsplit(redirect_uri)
        callback_origin = f"{parts.scheme}://{parts.netloc}"
        real = settings.mode == "real" and bool(settings.feishu.app_id)
        workspace_config = FeishuConfig(
            mode="real" if real else "fake",
            app_id=app_id,
            redirect_uri=redirect_uri,
            allowed_origins=tuple(dict.fromkeys((*config.allowed_origins, callback_origin))),
            state_ttl_seconds=config.state_ttl_seconds,
            identity=settings.feishu.identity,
            calendar_id=settings.feishu.calendar_id,
            material_content=settings.feishu.material_content,
            scope_materials=("minutes:minutes.search:read" if real else config.scope_materials),
            scope_calendar=("calendar:calendar.event:read" if real else config.scope_calendar),
            scope_material_body=(
                "minutes:minutes.transcript:export" if real else config.scope_material_body
            ),
            scope_material_artifacts=(
                "minutes:minutes.artifacts:read" if real else config.scope_material_artifacts
            ),
        )
        profile = str(Path(workspace.local_profile_dir).resolve())
        # Every execution-affecting field participates in the key, so a settings
        # change never keeps serving the previous identity/calendar/body mode.
        key = (
            profile,
            app_id,
            redirect_uri,
            workspace_config.mode,
            workspace_config.identity,
            workspace_config.calendar_id,
            workspace_config.material_content,
        )
        with feishu_services_lock:
            service = feishu_services.get(key)
            if service is None:
                if feishu_provider is not None:
                    provider: FeishuProvider = feishu_provider
                elif real:
                    # One credential slot system: the app secret is read from the
                    # same vault slot the settings UI writes, and user tokens are
                    # stored next to it under the same profile namespace.
                    store = credential_store or VaultCredentialStore(
                        credential_vault(workspace), app_id
                    )
                    provider = FeishuHttpProvider(workspace_config, store.get_app)
                else:
                    provider = FakeFeishu(
                        Path(tempfile.gettempdir())
                        / "summit-simulated-feishu-remote"
                        / hashlib.sha256(profile.encode()).hexdigest()
                    )
                if credential_store is not None:
                    store = credential_store
                elif real:
                    store = VaultCredentialStore(credential_vault(workspace), app_id)
                else:
                    store = MemoryCredentialStore()
                # One authorization coordinator per credential identity, shared
                # by every service instance so a configuration change cannot
                # fork refresh single-flight or the authorization generation.
                coordinator = auth_coordinators.setdefault(
                    (profile, app_id), FeishuAuthCoordinator()
                )
                service = FeishuService(
                    provider,
                    store,
                    workspace_config,
                    app.state.session_token,
                    coordinator=coordinator,
                )
                feishu_services[key] = service
                # Retire superseded services for the same profile/app so their
                # HTTP clients are released once idle, while any operation still
                # holding the old service keeps its configuration snapshot.
                for stale_key, stale in list(feishu_services.items()):
                    if stale_key == key or stale_key[:2] != key[:2]:
                        continue
                    del feishu_services[stale_key]
                    action_services.pop(id(stale), None)
                    retire = getattr(stale.provider, "retire", None)
                    if callable(retire):
                        retire()
        app.state.feishu_service = service
        return service

    def require_feishu_data(workspace: WorkspaceContext) -> None:
        """Stage B keeps real Feishu business reads server-disabled by default."""
        settings = settings_store(workspace).read()
        if settings.mode != "real":
            return
        if not settings.feishu.app_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_not_configured",
                    "message": "请先在本机设置中填写飞书 App ID 与密钥。",
                },
            )
        if not settings.feishu.real_data_enabled:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "stage_c_authorization_required",
                    "message": "真实飞书数据读取需要逐项授权后才会启用。",
                },
            )

    def actions_for(workspace: WorkspaceContext) -> ActionService:
        service = feishu_for(workspace)
        with feishu_services_lock:
            actions = action_services.get(id(service))
            if actions is None:
                actions = ActionService(
                    FeishuTasks(service),
                    app.state.session_token,
                    write_gate=lambda _kind: service.require_task_write(),
                )
                action_services[id(service)] = actions
        app.state.action_service = actions
        return actions

    def credential_vault(workspace: WorkspaceContext) -> CredentialVault:
        backend = app.state.secret_backend
        namespace = (
            "com.summiteverything.credentials."
            + hashlib.sha256(str(Path(workspace.local_profile_dir).resolve()).encode()).hexdigest()
        )
        return CredentialVault(namespace, backend)

    def validate_credential_account(
        workspace: WorkspaceContext, provider: str, account_id: str
    ) -> None:
        settings = settings_store(workspace).read()
        expected = {
            "feishu_app": settings.feishu.app_id or "default",
            "feishu_user": settings.feishu.app_id or "default",
            "deepseek": settings.llm.account_id,
            "dashscope": settings.model_studio_account_id,
        }.get(provider)
        if expected is None or account_id != expected:
            raise SettingsError("validation_error")

    register_actions(app, actions_for, authenticated, active_workspace, require_feishu_data)

    @app.exception_handler(SettingsError)
    async def settings_error_handler(request: Request, exc: SettingsError) -> JSONResponse:
        status = 422 if exc.code == "validation_error" else 503
        message = "设置或凭据无法使用，请检查本机配置和钥匙串状态。"
        if exc.code == "validation_error":
            message = "设置字段或凭据无效。"
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": exc.code,
                    "message": message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def payload_validation_error(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "validation_error", "message": "请填写有效的动作字段和日期。"}
            },
        )

    def runtime_for(workspace: WorkspaceContext) -> ModelRuntime:
        return ModelRuntime(settings_store(workspace).read(), credential_vault(workspace))

    def ensure_remote_calls_allowed(
        workspace: WorkspaceContext, providers: tuple[str, ...]
    ) -> None:
        settings = settings_store(workspace).read()
        if settings.mode != "real":
            return
        selected: dict[str, Any] = {
            "llm": settings.llm,
            "embedding": settings.embedding,
            "rerank": settings.rerank,
        }
        if any(selected[name].provider != "fake" and selected[name].enabled for name in providers):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_disabled",
                    "message": "真实业务调用当前关闭；仅允许单次合成连接检查。",
                },
            )

    def review_for(workspace: WorkspaceContext) -> IntakeReviewService:
        if review_service is not None:
            return review_service
        ensure_remote_calls_allowed(workspace, ("llm",))
        return IntakeReviewService(runtime_for(workspace).llm())

    def fingerprint_is_current(workspace: WorkspaceContext, fingerprint: str) -> bool:
        settings = settings_store(workspace).read()
        if settings.mode == "fake" and settings.embedding.provider == "fake":
            return True
        return fingerprint == embedding_fingerprint(settings.embedding, mode=settings.mode)

    def query_for(workspace: WorkspaceContext, *, remote: bool = False) -> QueryService:
        if query_service is not None:
            return query_service
        if remote:
            ensure_remote_calls_allowed(workspace, ("embedding", "rerank", "llm"))
        providers = runtime_for(workspace) if remote else None
        return QueryService(
            IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3"),
            embedding=providers.embedding() if providers else None,
            reranker=providers.reranker() if providers else None,
            answer_provider=(cast(AnswerProvider, providers.llm()) if providers else None),
        )

    def conversations_for(workspace: WorkspaceContext) -> ConversationStore:
        return ConversationStore(Path(workspace.local_profile_dir) / "conversations.sqlite3")

    def answer_context_for(workspace: WorkspaceContext) -> AnswerContextStore:
        return AnswerContextStore(Path(workspace.local_profile_dir) / "answer_context.sqlite3")

    def query_cancellation_key(
        workspace: WorkspaceContext, request_id: UUID
    ) -> tuple[str, str, str]:
        return (
            str(Path(workspace.local_profile_dir).resolve()),
            str(workspace.workspace_id),
            str(request_id),
        )

    def current_citation_availability(
        workspace: WorkspaceContext, citation: Any, purpose: str
    ) -> str:
        try:
            page = read_page(Path(workspace.root), citation.page_id)
        except WorkspaceError:
            return "unavailable"
        eligibility = retrieval_eligibility(
            page.metadata,
            page.body,
            area=StorageArea(page.storage_area),
            purpose=RetrievalPurpose(purpose),
        )
        if not eligibility.eligible:
            return "unavailable"
        return "available" if page.content_sha256 == citation.content_sha256 else "updated"

    @app.get("/api/v1/settings", dependencies=[Depends(authenticated)])
    def get_settings(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> SettingsSummary:
        settings = settings_store(workspace).read()
        return provider_settings_payload(settings, credential_vault(workspace))

    @app.patch("/api/v1/settings", dependencies=[Depends(authenticated)])
    def patch_settings(
        payload: ProviderSettingsPatch,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> SettingsSummary:
        try:
            settings = settings_store(workspace).update(payload.model_dump(exclude_unset=True))
        except ValidationError as exc:
            raise SettingsError("validation_error") from exc
        if payload.feishu is not None:
            feishu_for(workspace)
        return provider_settings_payload(settings, credential_vault(workspace))

    @app.put("/api/v1/credentials/{provider}", dependencies=[Depends(authenticated)])
    def put_credential(
        provider: str,
        payload: CredentialRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        validate_credential_account(workspace, provider, payload.account_id)
        credential_vault(workspace).put(
            provider, payload.secret.get_secret_value(), account_id=payload.account_id
        )
        return {"provider": provider, "configured": True}

    @app.delete("/api/v1/credentials/{provider}", dependencies=[Depends(authenticated)])
    def delete_credential(
        provider: str,
        payload: CredentialAccountRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        validate_credential_account(workspace, provider, payload.account_id)
        credential_vault(workspace).delete(provider, account_id=payload.account_id)
        return Response(status_code=204)

    @app.get("/api/v1/provider-smoke", dependencies=[Depends(authenticated)])
    def provider_smoke_status(
        _workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        counts = smoke_counts(Path(app.state.profile_root))
        return {
            "counts": counts,
            "limits": SMOKE_LIMITS,
            "remaining": {key: SMOKE_LIMITS[key] - counts[key] for key in SMOKE_LIMITS},
        }

    def require_smoke_provider(workspace: WorkspaceContext, operation: str) -> ModelRuntime:
        settings = settings_store(workspace).read()
        requirement = {
            "deepseek_chat": settings.mode == "real"
            and settings.llm.provider == "deepseek"
            and settings.llm.enabled,
            "model_studio_embedding": settings.mode == "real"
            and settings.embedding.provider == "dashscope"
            and settings.embedding.enabled,
            "model_studio_rerank": settings.mode == "real"
            and settings.rerank.provider == "dashscope"
            and settings.rerank.enabled,
        }.get(operation, False)
        if not requirement:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_not_configured",
                    "message": "请先保存并配置对应 provider。",
                },
            )
        return runtime_for(workspace)

    def reserve_smoke(operation: str) -> int:
        try:
            return reserve_smoke_call(Path(app.state.profile_root), operation)
        except SmokeLimitReached:
            raise HTTPException(
                status_code=409,
                detail={"code": "smoke_limit_reached", "message": "此合成连接检查次数已用完。"},
            ) from None
        except RuntimeError:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "smoke_ledger_unavailable",
                    "message": "本地调用记录不可用；已停止请求。",
                },
            ) from None

    @app.post("/api/v1/provider-smoke/deepseek-chat", dependencies=[Depends(authenticated)])
    def smoke_deepseek_chat(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        runtime = require_smoke_provider(workspace, "deepseek_chat")
        provider = runtime.llm(max_tokens=64)
        if not isinstance(provider, DeepSeekLLM):
            raise HTTPException(status_code=409, detail="所选 provider 不支持此检查。")
        try:
            attempt = reserve_smoke("deepseek_chat")
            provider.answer(
                "请仅复述合成短语。",
                [{"heading": "合成标题", "excerpt": "合成短语：连接正常。"}],
            )
            return {"state": "succeeded", "operation": "deepseek_chat", "attempt": attempt}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_smoke_failed",
                    "message": "请求已计入一次尝试；结果未知，不会自动重发。",
                },
            ) from None
        finally:
            provider.close()

    @app.post(
        "/api/v1/provider-smoke/model-studio-embedding", dependencies=[Depends(authenticated)]
    )
    def smoke_model_studio_embedding(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        runtime = require_smoke_provider(workspace, "model_studio_embedding")
        provider = runtime.embedding()
        if not isinstance(provider, ModelStudioEmbedding):
            raise HTTPException(status_code=409, detail="所选 provider 不支持此检查。")
        try:
            attempt = reserve_smoke("model_studio_embedding")
            provider.embed_many(["synthetic connection check"], fingerprint=None)
            return {
                "state": "succeeded",
                "operation": "model_studio_embedding",
                "attempt": attempt,
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_smoke_failed",
                    "message": "请求已计入一次尝试；结果未知，不会自动重发。",
                },
            ) from None
        finally:
            provider.close()

    @app.post("/api/v1/provider-smoke/model-studio-rerank", dependencies=[Depends(authenticated)])
    def smoke_model_studio_rerank(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        runtime = require_smoke_provider(workspace, "model_studio_rerank")
        provider = runtime.reranker()
        if not isinstance(provider, ModelStudioReranker):
            raise HTTPException(status_code=409, detail="所选 provider 不支持此检查。")
        try:
            attempt = reserve_smoke("model_studio_rerank")
            provider.rank(
                "synthetic connection query",
                ["synthetic candidate alpha", "synthetic candidate beta"],
            )
            return {
                "state": "succeeded",
                "operation": "model_studio_rerank",
                "attempt": attempt,
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_smoke_failed",
                    "message": "请求已计入一次尝试；结果未知，不会自动重发。",
                },
            ) from None
        finally:
            provider.close()

    def index_after_approval(
        workspace: WorkspaceContext, mutation: MutationResult
    ) -> MutationResult:
        settings = settings_store(workspace).read()
        service = query_for(workspace)
        fingerprint = service.store.active_fingerprint(workspace.workspace_id)
        if fingerprint is None:
            return mutation.model_copy(update={"index_update": "not_enabled"})
        if settings.mode == "real" and settings.embedding.provider != "fake":
            return mutation.model_copy(update={"index_update": "manual_required"})
        try:
            root = Path(workspace.root)
            plan = service.plan(root, fingerprint=fingerprint, mode="incremental")
            service.execute_plan(root, plan)
        except Exception as exc:
            logging.getLogger(__name__).error(
                "Incremental index update failed for workspace %s (%s)",
                workspace.workspace_id,
                type(exc).__name__,
            )
            return mutation.model_copy(update={"index_update": "update_failed"})
        return mutation.model_copy(update={"index_update": "updated"})

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
        feishu_for(context)
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
        return index_after_approval(
            workspace,
            PageWriter().confirm(
                Path(workspace.root),
                metadata=payload.metadata,
                body=payload.body,
                confirmation_id=payload.confirmation_id,
                operation_id=payload.operation_id,
            ),
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
        return index_after_approval(
            workspace,
            PageWriter().confirm(
                Path(workspace.root),
                metadata=payload.metadata,
                body=payload.body,
                confirmation_id=payload.confirmation_id,
                operation_id=payload.operation_id,
                expected_base_sha256=payload.expected_base_sha256,
            ),
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

    @app.post("/api/v1/journal/assist", dependencies=[Depends(authenticated)])
    def journal_assist(
        payload: JournalAssistRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> JournalAssistResponse:
        try:
            proposals = review_for(workspace).provider.organize([(uuid4(), uuid4(), payload.text)])
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=502, detail="AI 辅助暂时不可用；已保存内容未更改。"
            ) from exc
        if not proposals:
            raise HTTPException(status_code=502, detail="AI 辅助没有返回建议；已保存内容未更改。")
        return JournalAssistResponse(title=proposals[0].title, body=proposals[0].body)

    @app.post("/api/v1/journal/{kind}", status_code=201, dependencies=[Depends(authenticated)])
    def journal_create(
        kind: Literal["log", "thought"],
        payload: JournalRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        manifest = load_manifest(Path(workspace.root))
        metadata: dict[str, Any] = {
            "id": str(uuid5(manifest.workspace_id, f"journal:{kind}:{payload.operation_id}")),
            "title": payload.title,
            "role": "knowledge",
            "kind": kind,
        }
        if payload.line_id is not None:
            metadata["line_id"] = str(payload.line_id)
        if payload.project_id is not None:
            metadata["project_id"] = str(payload.project_id)
        return index_after_approval(
            workspace,
            PageWriter().confirm(
                Path(workspace.root),
                metadata=metadata,
                body=payload.body,
                confirmation_id=payload.confirmation_id,
                operation_id=payload.operation_id,
            ),
        )

    @app.post(
        "/api/v1/projects/{project_id}/overview/confirmations",
        status_code=201,
        dependencies=[Depends(authenticated)],
    )
    def project_overview_confirm(
        project_id: UUID,
        payload: ProjectOverviewConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MutationResult:
        manifest = load_manifest(Path(workspace.root))
        project = next((item for item in manifest.projects if item.id == project_id), None)
        if project is None:
            raise WorkspaceError("Project not found", 404)
        existing_page = next(
            (
                page
                for page in list_pages(Path(workspace.root))
                if page.page_id == project.overview_id
            ),
            None,
        )
        metadata = dict(existing_page.metadata) if existing_page is not None else {}
        metadata.update(
            {
                "id": str(project.overview_id),
                "title": payload.title,
                "role": "knowledge",
                "kind": "project_overview",
                "line_id": str(project.line_id),
                "project_id": str(project.id),
            }
        )
        return index_after_approval(
            workspace,
            PageWriter().confirm(
                Path(workspace.root),
                metadata=metadata,
                body=payload.body,
                confirmation_id=payload.confirmation_id,
                operation_id=payload.operation_id,
                expected_base_sha256=payload.expected_content_sha256,
            ),
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
        return review_for(workspace).create_job(
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
        return index_after_approval(
            workspace,
            review.confirm_draft(
                Path(workspace.root),
                draft_id,
                expected_version=payload.expected_version,
                confirmation_id=payload.confirmation_id,
                operation_id=payload.operation_id,
                conflict_resolutions=payload.conflict_resolutions,
            ),
        )

    @app.get("/api/v1/actions", dependencies=[Depends(authenticated)])
    def action_candidates(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: UUID | None = None,
        limit: int | None = Query(default=None, ge=1, le=100),
    ) -> list[ActionCandidate] | dict[str, Any]:
        rows = review.list_actions(Path(workspace.root))
        if limit is None and cursor is None:
            return rows
        rows = sorted(rows, key=lambda row: str(row.action_id))
        if cursor:
            rows = [row for row in rows if str(row.action_id) > str(cursor)]
        size = limit or 20
        return {
            "items": rows[:size],
            "next_cursor": str(rows[size - 1].action_id) if len(rows) > size else None,
        }

    @app.post("/api/v1/index/plans", dependencies=[Depends(authenticated)])
    def index_plan(
        payload: IndexPlanRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IndexPlan:
        if query_service is None and not fingerprint_is_current(workspace, payload.fingerprint):
            raise HTTPException(status_code=409, detail="Provider 设置已变化，请重新生成索引计划。")
        return query_for(workspace).plan(
            Path(workspace.root), fingerprint=payload.fingerprint, mode=payload.mode
        )

    @app.post("/api/v1/index/jobs", dependencies=[Depends(authenticated)])
    def index_execute(
        payload: IndexPlan,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IndexResult:
        ensure_remote_calls_allowed(workspace, ("embedding",))
        if query_service is None and not fingerprint_is_current(workspace, payload.fingerprint):
            raise HTTPException(status_code=409, detail="Provider 设置已变化，请重新生成索引计划。")
        service = query_for(workspace, remote=True)
        try:
            return service.execute_plan(Path(workspace.root), payload)
        finally:
            if query_service is None:
                service.close()

    @app.get("/api/v1/index/status", dependencies=[Depends(authenticated)])
    def index_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, int | str | None]:
        return query_for(workspace).status(Path(workspace.root))

    @app.get("/api/v1/conversations", dependencies=[Depends(authenticated)])
    def conversation_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> ConversationPage:
        try:
            return conversations_for(workspace).list(
                workspace.workspace_id, cursor=cursor, limit=limit
            )
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_cursor", "message": "历史分页位置无效。"},
            ) from None

    @app.get("/api/v1/conversations/{conversation_id}", dependencies=[Depends(authenticated)])
    def conversation_get(
        conversation_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> ConversationDetail:
        store = conversations_for(workspace)
        detail = store.get(workspace.workspace_id, conversation_id)
        if detail is None:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这段问答历史。"}
            )
        messages = []
        for message in detail.messages:
            citations = [
                citation.model_copy(
                    update={
                        "availability": current_citation_availability(
                            workspace, citation, message.purpose
                        )
                    }
                )
                for citation in message.citations
            ]
            messages.append(message.model_copy(update={"citations": citations}))
        return detail.model_copy(update={"messages": messages})

    @app.post(
        "/api/v1/conversations/{conversation_id}/reopen",
        dependencies=[Depends(authenticated)],
    )
    def conversation_reopen(
        conversation_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> ConversationDetail:
        detail = conversation_get(conversation_id, workspace)
        return detail

    @app.delete(
        "/api/v1/conversations/{conversation_id}",
        status_code=204,
        dependencies=[Depends(authenticated)],
    )
    def conversation_delete(
        conversation_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        store = conversations_for(workspace)
        running = store.running_requests(workspace.workspace_id, conversation_id)
        for request_id in running:
            cancellation = cancellations.get(query_cancellation_key(workspace, request_id))
            if cancellation is not None:
                cancellation.set()
        if not store.delete(workspace.workspace_id, conversation_id):
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这段问答历史。"}
            )
        return Response(status_code=204)

    @app.get("/api/v1/roles", dependencies=[Depends(authenticated)])
    def roles_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[AnswerRole]:
        return answer_context_for(workspace).list_roles(workspace.workspace_id)

    @app.post("/api/v1/roles", status_code=201, dependencies=[Depends(authenticated)])
    def roles_create(
        payload: RoleInput,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> AnswerRole:
        return answer_context_for(workspace).save_role(workspace.workspace_id, payload)

    @app.patch("/api/v1/roles/{role_id}", dependencies=[Depends(authenticated)])
    def roles_update(
        role_id: UUID,
        payload: RoleInput,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> AnswerRole:
        store = answer_context_for(workspace)
        if store.role(workspace.workspace_id, role_id) is None:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这个问答角色。"}
            )
        return store.save_role(workspace.workspace_id, payload, role_id)

    @app.delete("/api/v1/roles/{role_id}", status_code=204, dependencies=[Depends(authenticated)])
    def roles_delete(
        role_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        if not answer_context_for(workspace).delete_role(workspace.workspace_id, role_id):
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这个问答角色。"}
            )
        return Response(status_code=204)

    @app.get("/api/v1/memory/candidates", dependencies=[Depends(authenticated)])
    def memory_candidates(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[MemoryCandidate]:
        return answer_context_for(workspace).candidates(workspace.workspace_id)

    @app.post("/api/v1/memory/candidates", status_code=201, dependencies=[Depends(authenticated)])
    def memory_candidate_create(
        payload: MemoryCandidateRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> MemoryCandidate:
        source = conversations_for(workspace).user_message(
            workspace.workspace_id, payload.message_id
        )
        text = payload.text.strip()
        if source is None or text not in source:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "只能从本人历史问题中的原文提取记忆。",
                },
            )
        provenance_markers = (
            "原文",
            "原件",
            "来源",
            "材料",
            "资料",
            "引用",
            "转述",
            "摘录",
            "粘贴",
            "转发",
            "以下内容",
            "这段内容",
            "文档写",
            "页面写",
            "邮件写",
            "记录写",
            "according to",
            "source says",
            "quoted",
            "excerpt",
            "forwarded",
            "paste",
            "“",
            "”",
            '"',
            "‘",
            "’",
            "'",
            "「",
            "」",
            "『",
            "』",
            ">",
        )
        if any(marker.casefold() in text.casefold() for marker in provenance_markers):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "这段内容看起来是引用或材料描述，不能作为本人记忆候选。",
                },
            )
        explicit_expression = any(
            marker in text
            for marker in (
                "我希望",
                "我偏好",
                "我喜欢",
                "我不喜欢",
                "我需要",
                "我负责",
                "我通常",
                "我习惯",
                "我的工作",
                "我的目标",
                "我的偏好",
                "我是",
                "我计划",
            )
        )
        if not explicit_expression:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": (
                        "请只选择你本人明确表达的偏好、习惯或事实；引用和粘贴材料不能作为记忆。"
                    ),
                },
            )
        return answer_context_for(workspace).create_candidate(
            workspace.workspace_id, payload.message_id, text
        )

    @app.post(
        "/api/v1/memory/candidates/{candidate_id}/confirmations",
        dependencies=[Depends(authenticated)],
    )
    def memory_candidate_confirm(
        candidate_id: UUID,
        payload: MemoryConfirmationRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> UserMemory:
        try:
            return answer_context_for(workspace).confirm_candidate(
                workspace.workspace_id,
                candidate_id,
                confirmation_id=payload.confirmation_id,
                text=payload.text.strip(),
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": str(exc)}
            ) from exc
        except ContextConflict as exc:
            raise HTTPException(
                status_code=409, detail={"code": "intent_conflict", "message": str(exc)}
            ) from exc

    @app.get("/api/v1/memory", dependencies=[Depends(authenticated)])
    def memory_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[UserMemory]:
        return answer_context_for(workspace).memories(workspace.workspace_id)

    @app.patch("/api/v1/memory/{memory_id}", dependencies=[Depends(authenticated)])
    def memory_update(
        memory_id: UUID,
        payload: MemoryPatchRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> UserMemory:
        updated = answer_context_for(workspace).update_memory(
            workspace.workspace_id, memory_id, payload.text.strip()
        )
        if updated is None:
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这条已确认记忆。"}
            )
        return updated

    @app.delete(
        "/api/v1/memory/{memory_id}", status_code=204, dependencies=[Depends(authenticated)]
    )
    def memory_delete(
        memory_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        if not answer_context_for(workspace).delete_memory(workspace.workspace_id, memory_id):
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": "找不到这条已确认记忆。"}
            )
        return Response(status_code=204)

    @app.post("/api/v1/queries", dependencies=[Depends(authenticated)])
    def query_stream(
        request: Request,
        payload: QueryRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> StreamingResponse:
        ensure_remote_calls_allowed(workspace, ("embedding", "rerank", "llm"))
        request_id = str(payload.request_id or uuid4())
        stable_request_id = UUID(request_id)
        store = conversations_for(workspace)
        answer_store = answer_context_for(workspace)
        replay_existing = store.has_request(workspace.workspace_id, stable_request_id)
        context = AnswerContext(answer_mode=payload.answer_mode)
        context_version = "replay-existing-request"
        if not replay_existing:
            selected_role = None
            if payload.role_id is not None:
                selected_role = answer_store.role(workspace.workspace_id, payload.role_id)
                if selected_role is None:
                    raise HTTPException(
                        status_code=404,
                        detail={"code": "not_found", "message": "找不到这个问答角色。"},
                    )
                if len(selected_role.instructions.encode("utf-8")) > selected_role.context_budget:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "context_budget_exceeded",
                            "message": "角色说明超过设定预算；请编辑角色内容后重试。",
                        },
                    )
            try:
                memories = answer_store.active_memory_text(workspace.workspace_id)
            except ContextConflict as exc:
                raise HTTPException(
                    status_code=422, detail={"code": "context_budget_exceeded", "message": str(exc)}
                ) from exc
            previous_questions = store.previous_user_questions(
                workspace.workspace_id, payload.conversation_id, excluding=stable_request_id
            )
            context = AnswerContext(
                answer_mode=payload.answer_mode,
                role_name=selected_role.name if selected_role else "",
                role_instructions=selected_role.instructions if selected_role else "",
                user_memories=memories,
                previous_user_questions=previous_questions,
            )
            context_version = hashlib.sha256(
                json.dumps(
                    context.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
        active_query_key = (
            str(Path(workspace.local_profile_dir).resolve() / "conversations.sqlite3"),
            str(workspace.workspace_id),
            request_id,
        )
        registered_before_begin = active_query_key not in ACTIVE_QUERIES
        if registered_before_begin:
            # Close the small window between committing `running` and registering the
            # in-process attempt, during which a concurrent history read could recover it.
            ACTIVE_QUERIES.add(active_query_key)
        try:
            created, conversation_id = store.begin(
                workspace.workspace_id,
                QueryStart(
                    request_id=stable_request_id,
                    conversation_id=payload.conversation_id,
                    question=payload.question,
                    fingerprint=payload.fingerprint,
                    purpose=payload.purpose,
                    answer_mode=payload.answer_mode,
                    role_id=payload.role_id,
                    context_version=context_version,
                ),
            )
        except QueryConflict as exc:
            if registered_before_begin:
                ACTIVE_QUERIES.discard(active_query_key)
            raise HTTPException(
                status_code=409, detail={"code": "intent_conflict", "message": str(exc)}
            ) from exc
        except ConversationNotFound as exc:
            if registered_before_begin:
                ACTIVE_QUERIES.discard(active_query_key)
            raise HTTPException(
                status_code=404, detail={"code": "not_found", "message": str(exc)}
            ) from exc
        replay = store.replay(workspace.workspace_id, stable_request_id)
        cancel_key = query_cancellation_key(workspace, stable_request_id)
        if created and cancel_key in cancellations:
            store.finish(workspace.workspace_id, stable_request_id, "interrupted")
            if registered_before_begin:
                ACTIVE_QUERIES.discard(active_query_key)
            raise HTTPException(
                status_code=409,
                detail={"code": "intent_conflict", "message": "查询标识已在使用"},
            )
        if created:
            ACTIVE_QUERIES.add(active_query_key)
        elif registered_before_begin:
            ACTIVE_QUERIES.discard(active_query_key)
        cancelled = Event()
        if created:
            cancellations[cancel_key] = cancelled

        def event(seq: int, event_type: str, data: Any) -> str:
            value = {
                "request_id": request_id,
                "seq": seq,
                "type": event_type,
                "data": data,
            }
            return f"data: {json.dumps(value, ensure_ascii=False)}\n\n"

        async def generate() -> AsyncIterator[str]:
            operation = None
            query_task: asyncio.Task[Any] | None = None
            client_disconnected = False
            try:
                if not created:
                    if replay is not None:
                        for saved_event in replay[1]:
                            yield event(
                                saved_event.seq,
                                saved_event.type,
                                saved_event.data,
                            )
                    return
                operation = query_for(workspace, remote=True) if query_service is None else None
                initial = store.append_event(
                    workspace.workspace_id,
                    stable_request_id,
                    "status",
                    {"state": "retrieving", "conversation_id": str(conversation_id)},
                )
                yield event(initial.seq, initial.type, initial.data)
                if query_service is None and not fingerprint_is_current(
                    workspace, payload.fingerprint
                ):
                    raise ValueError("provider settings changed; refresh the index settings")
                query_task = asyncio.create_task(
                    asyncio.to_thread(
                        (operation or query_for(workspace)).query,
                        Path(workspace.root),
                        payload.question,
                        fingerprint=payload.fingerprint,
                        purpose=RetrievalPurpose(payload.purpose),
                        answer_mode=payload.answer_mode,
                        context=context,
                        cancelled=cancelled,
                    )
                )
                while not query_task.done():
                    if await request.is_disconnected():
                        client_disconnected = True
                        cancelled.set()
                    await asyncio.sleep(0.05)
                answer = await query_task
                if client_disconnected or await request.is_disconnected():
                    cancelled.set()
                    store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                    return
                if cancelled.is_set():
                    terminal = store.terminate(
                        workspace.workspace_id,
                        stable_request_id,
                        "error",
                        {"code": "cancelled", "message": "查询已取消"},
                        "cancelled",
                        error="查询已取消",
                    )
                    if terminal is not None:
                        yield event(terminal.seq, terminal.type, terminal.data)
                    return
                for citation in answer.citations:
                    if await request.is_disconnected():
                        store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                        return
                    citation_event = store.append_event(
                        workspace.workspace_id,
                        stable_request_id,
                        "citation",
                        citation.model_dump(mode="json"),
                    )
                    yield event(citation_event.seq, citation_event.type, citation_event.data)
                for offset in range(0, len(answer.text), 120):
                    if cancelled.is_set() or await request.is_disconnected():
                        cancelled.set()
                        if await request.is_disconnected():
                            store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                            return
                        terminal = store.terminate(
                            workspace.workspace_id,
                            stable_request_id,
                            "error",
                            {"code": "cancelled", "message": "查询已取消"},
                            "cancelled",
                            error="查询已取消",
                        )
                        if terminal is not None:
                            yield event(terminal.seq, terminal.type, terminal.data)
                        return
                    delta = store.append_event(
                        workspace.workspace_id,
                        stable_request_id,
                        "delta",
                        {"text": answer.text[offset : offset + 120]},
                    )
                    yield event(delta.seq, delta.type, delta.data)
                if cancelled.is_set() or await request.is_disconnected():
                    if await request.is_disconnected():
                        store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                        return
                    terminal = store.terminate(
                        workspace.workspace_id,
                        stable_request_id,
                        "error",
                        {"code": "cancelled", "message": "查询已取消"},
                        "cancelled",
                        error="查询已取消",
                    )
                    if terminal is not None:
                        yield event(terminal.seq, terminal.type, terminal.data)
                    return
                terminal = store.terminate(
                    workspace.workspace_id,
                    stable_request_id,
                    "completed",
                    answer.model_dump(mode="json"),
                    "completed",
                )
                if terminal is not None:
                    yield event(terminal.seq, terminal.type, terminal.data)
            except QueryCancelled:
                if client_disconnected:
                    store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                    return
                terminal = store.terminate(
                    workspace.workspace_id,
                    stable_request_id,
                    "error",
                    {"code": "cancelled", "message": "查询已取消"},
                    "cancelled",
                    error="查询已取消",
                )
                if terminal is not None:
                    yield event(terminal.seq, terminal.type, terminal.data)
            except asyncio.CancelledError:
                cancelled.set()
                if cancel_key in cancellation_requests:
                    store.terminate(
                        workspace.workspace_id,
                        stable_request_id,
                        "error",
                        {"code": "cancelled", "message": "查询已取消"},
                        "cancelled",
                        error="查询已取消",
                    )
                else:
                    store.finish(workspace.workspace_id, stable_request_id, "interrupted")
                raise
            except Exception as exc:
                terminal = store.terminate(
                    workspace.workspace_id,
                    stable_request_id,
                    "error",
                    {"code": "query_error", "message": str(exc)},
                    "error",
                    error=str(exc),
                )
                if terminal is not None:
                    yield event(terminal.seq, terminal.type, terminal.data)
            finally:
                cancellations.pop(cancel_key, None)
                cancellation_requests.discard(cancel_key)
                ACTIVE_QUERIES.discard(active_query_key)
                if operation is not None:
                    if query_task is None or query_task.done():
                        operation.close()
                    else:
                        query_task.add_done_callback(lambda _task: operation.close())

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Conversation-ID": str(conversation_id),
            },
        )

    @app.delete(
        "/api/v1/queries/{request_id}", status_code=202, dependencies=[Depends(authenticated)]
    )
    def query_cancel(request_id: UUID) -> dict[str, str]:
        workspace = active_workspace()
        cancellation = cancellations.get(query_cancellation_key(workspace, request_id))
        if cancellation is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "查询已结束或不存在"},
            )
        cancellation.set()
        cancellation_requests.add(query_cancellation_key(workspace, request_id))
        return {
            "request_id": str(request_id),
            "state": "cancellation_requested",
            "message": "已发出的模型请求仍可能完成并计费；不会启动后续阶段或自动重发。",
        }

    prefix = "/api/v1/integrations/feishu"

    @app.get(prefix + "/status", dependencies=[Depends(authenticated)])
    def feishu_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> FeishuStatus:
        return feishu_for(workspace).status()

    @app.post(prefix + "/authorizations", dependencies=[Depends(authenticated)])
    def feishu_authorize(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> AuthorizationStart:
        return feishu_for(workspace).authorize()

    @app.delete(prefix + "/authorizations", status_code=204, dependencies=[Depends(authenticated)])
    def feishu_logout(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        feishu_for(workspace).logout()
        return Response(status_code=204)

    @app.get(prefix + "/callback")
    @app.get("/callback")
    def feishu_callback(
        request: Request,
        state: str,
        code: str | None = None,
        error: str | None = None,
    ) -> FeishuStatus:
        workspace = cast(WorkspaceContext | None, app.state.workspace)
        service = feishu_for(workspace) if workspace is not None else feishu
        return service.callback(state, code, error, callback_boundary(str(request.url)))

    @app.get(prefix + "/materials", dependencies=[Depends(authenticated)])
    def feishu_materials(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        query: str = "",
        visibility: Literal["owner", "shared"] | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> MaterialPage:
        if not 1 <= limit <= 30 or len(query) > 500 or (cursor and len(cursor) > 500):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "材料筛选无效。"}
            )
        require_feishu_data(workspace)
        return feishu_for(workspace).materials(query, visibility, cursor, limit)

    @app.post(prefix + "/imports", dependencies=[Depends(authenticated)])
    def feishu_imports(
        payload: ImportRequest, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> ImportResult:
        require_feishu_data(workspace)
        try:
            return feishu_for(workspace).imports(Path(workspace.root), payload)
        except ValueError as exc:
            if isinstance(exc, IntakeConflict):
                raise
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "材料选择无效。"}
            ) from None

    @app.get(prefix + "/calendar", dependencies=[Depends(authenticated)])
    def feishu_calendar(
        start: datetime,
        end: datetime,
        timezone: str,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = 20,
    ) -> CalendarPage:
        if not 1 <= limit <= 30 or (cursor and len(cursor) > 500):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "日历分页无效。"}
            )
        require_feishu_data(workspace)
        try:
            return feishu_for(workspace).calendar(start, end, timezone, cursor, limit)
        except ValueError:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "请选择有效的起止时间和时区。"}
            ) from None

    return app


app = create_app(
    session_token=os.environ.get("SUMMIT_SESSION_TOKEN"),
    feishu_config=FeishuConfig(
        redirect_uri=os.environ.get(
            "SUMMIT_FEISHU_REDIRECT_URI",
            f"http://127.0.0.1:{os.environ.get('SUMMIT_WEB_PORT', '5173')}"
            "/api/v1/integrations/feishu/callback",
        ),
        allowed_origins=(
            f"http://127.0.0.1:{os.environ.get('SUMMIT_WEB_PORT', '5173')}",
            f"http://127.0.0.1:{os.environ.get('SUMMIT_API_PORT', '8793')}",
        ),
    ),
)
