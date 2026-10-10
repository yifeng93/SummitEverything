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
from summit_everything.intake.actions import ActionService
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeConflict, IntakeService
from summit_everything.integrations.embedding import ModelStudioEmbedding
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import (
    CalendarPage,
    CredentialStore,
    FeishuConfig,
    FeishuError,
    FeishuProvider,
    MaterialPage,
    MemoryCredentialStore,
)
from summit_everything.integrations.feishu.service import (
    AuthorizationStart,
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
    cancellations: dict[str, Event] = {}
    config = feishu_config or FeishuConfig()
    feishu_services: dict[tuple[str, str, str], FeishuService] = {}
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
        workspace_config = FeishuConfig(
            app_id=app_id,
            redirect_uri=redirect_uri,
            allowed_origins=tuple(dict.fromkeys((*config.allowed_origins, callback_origin))),
            state_ttl_seconds=config.state_ttl_seconds,
        )
        profile = str(Path(workspace.local_profile_dir).resolve())
        key = (profile, app_id, redirect_uri)
        with feishu_services_lock:
            service = feishu_services.get(key)
            if service is None:
                provider = feishu_provider or FakeFeishu(
                    Path(tempfile.gettempdir())
                    / "summit-simulated-feishu-remote"
                    / hashlib.sha256(profile.encode()).hexdigest()
                )
                store = credential_store or MemoryCredentialStore()
                service = FeishuService(provider, store, workspace_config, app.state.session_token)
                feishu_services[key] = service
        app.state.feishu_service = service
        return service

    def actions_for(workspace: WorkspaceContext) -> ActionService:
        service = feishu_for(workspace)
        with feishu_services_lock:
            actions = action_services.get(id(service))
            if actions is None:
                actions = ActionService(FeishuTasks(service), app.state.session_token)
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
            "deepseek": settings.llm.account_id,
            "dashscope": settings.model_studio_account_id,
        }.get(provider)
        if expected is None or account_id != expected:
            raise SettingsError("validation_error")

    register_actions(app, actions_for, authenticated, active_workspace)

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
            answer_provider=(
                cast(AnswerProvider, providers.llm())
                if providers
                and settings_store(workspace).read().mode == "real"
                and settings_store(workspace).read().llm.provider != "fake"
                else None
            ),
        )

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
        return query_for(workspace, remote=True).execute_plan(Path(workspace.root), payload)

    @app.get("/api/v1/index/status", dependencies=[Depends(authenticated)])
    def index_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, int | str | None]:
        return query_for(workspace).status(Path(workspace.root))

    @app.post("/api/v1/queries", dependencies=[Depends(authenticated)])
    def query_stream(
        request: Request,
        payload: QueryRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> StreamingResponse:
        ensure_remote_calls_allowed(workspace, ("embedding", "rerank", "llm"))
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

        async def generate() -> AsyncIterator[str]:
            seq = 0
            try:
                seq += 1
                yield event(seq, "status", {"state": "retrieving"})
                if query_service is None and not fingerprint_is_current(
                    workspace, payload.fingerprint
                ):
                    raise ValueError("provider settings changed; refresh the index settings")
                query_task = asyncio.create_task(
                    asyncio.to_thread(
                        query_for(workspace, remote=True).query,
                        Path(workspace.root),
                        payload.question,
                        fingerprint=payload.fingerprint,
                        purpose=RetrievalPurpose(payload.purpose),
                        cancelled=cancelled,
                    )
                )
                while not query_task.done():
                    if await request.is_disconnected():
                        cancelled.set()
                    await asyncio.sleep(0.05)
                answer = await query_task
                if await request.is_disconnected():
                    cancelled.set()
                    return
                if cancelled.is_set():
                    seq += 1
                    yield event(seq, "error", {"code": "cancelled", "message": "查询已取消"})
                    return
                for citation in answer.citations:
                    seq += 1
                    yield event(seq, "citation", citation.model_dump(mode="json"))
                for offset in range(0, len(answer.text), 120):
                    if cancelled.is_set() or await request.is_disconnected():
                        cancelled.set()
                        if await request.is_disconnected():
                            return
                        seq += 1
                        yield event(seq, "error", {"code": "cancelled", "message": "查询已取消"})
                        return
                    seq += 1
                    yield event(seq, "delta", {"text": answer.text[offset : offset + 120]})
                seq += 1
                yield event(seq, "completed", answer.model_dump(mode="json"))
            except QueryCancelled:
                seq += 1
                yield event(seq, "error", {"code": "cancelled", "message": "查询已取消"})
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
        return feishu_for(workspace).materials(query, visibility, cursor, limit)

    @app.post(prefix + "/imports", dependencies=[Depends(authenticated)])
    def feishu_imports(
        payload: ImportRequest, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> ImportResult:
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
