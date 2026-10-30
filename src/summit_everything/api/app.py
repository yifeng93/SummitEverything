"""FastAPI application factory for the local-only service."""

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
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
from starlette.staticfiles import StaticFiles

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
    PageDirectoryEntry,
    PageSnapshot,
    ProjectRecord,
    SourceDetail,
    WorkspaceContext,
)
from summit_everything.intake.actions import ActionService
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeConflict, IntakeService
from summit_everything.integrations.acceptance_plans import (
    AcceptancePlan,
    AcceptancePlanLedger,
    PlanConflict,
    ProviderUsage,
    plan_conflict_message,
)
from summit_everything.integrations.credential_generations import CredentialGenerationStore
from summit_everything.integrations.embedding import EmbeddingProviderError
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
from summit_everything.integrations.first_use_defaults import (
    FirstUseDefaults,
    load_first_use_defaults,
)
from summit_everything.integrations.http_boundary import (
    REASON_TEXT,
    ProviderError,
    describe_failure,
    sanitize_provider_text,
)
from summit_everything.integrations.llm import DeepSeekLLM, LLMProviderError
from summit_everything.integrations.provider_smoke import (
    SMOKE_LIMITS,
    SmokeLimitReached,
    record_smoke_result,
    reserve_smoke_call,
    smoke_counts,
    smoke_result,
)
from summit_everything.integrations.rerank import RerankProviderError
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import (
    CredentialVault,
    LocalModelStatus,
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
from summit_everything.local.event_log import FALLBACK_REASON, profile_event
from summit_everything.local.first_use_progress import (
    FirstUseProgress,
    FirstUseProgressError,
    FirstUseProgressStore,
)
from summit_everything.local.retrieval_model import LocalModelError, LocalRetrievalModelStore
from summit_everything.release import (
    fingerprint_web_dist,
    load_build_identity,
    verify_dependency_manifest,
)
from summit_everything.retrieval.chunking import chunk_markdown
from summit_everything.retrieval.query import (
    AnswerProvider,
    IndexPlanStale,
    QueryCancelled,
    QueryService,
)
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

_SOURCE_ATTRIBUTION = re.compile(
    r"(?:原文|原件|材料|资料|文档|文件|页面|邮件|记录|通知|对方|他人|朋友|团队|同事|source|document|email|message|team)"
    r"[^\n。！？]{0,24}(?:写(?:着|道|到)?|提到|记载|表示|称|说|指出|显示|内容(?:是|为)|如下|[:：])",
    re.IGNORECASE,
)
_FORWARDED_CONTENT = re.compile(
    r"(?:我)?(?:转发|粘贴|复制|转述|摘录|引用)(?:过|的)?(?:这段|该)?"
    r"(?:内容|文字|信息|原文)?(?:是|为|如下|[:：])",
    re.IGNORECASE,
)
_SOURCE_ATTRIBUTION_PREFIX = re.compile(
    _SOURCE_ATTRIBUTION.pattern + r"[\s\"“‘「『]*$", re.IGNORECASE
)
_FORWARDED_CONTENT_PREFIX = re.compile(
    _FORWARDED_CONTENT.pattern + r"[\s\"“‘「『]*$", re.IGNORECASE
)
_QUOTE_PAIRS = (("“", "”"), ("‘", "’"), ("「", "」"), ("『", "』"), ('"', '"'), ("'", "'"))
_FIRST_PERSON_EXPRESSION = re.compile(
    r"^\s*(?:我(?:希望|偏好|喜欢|不喜欢|需要|负责|通常|习惯|是|计划)|我的(?:工作|目标|偏好))"
)


def _contains_quoted_first_person(text: str) -> bool:
    for opening, closing in _QUOTE_PAIRS:
        start = text.find(opening)
        while start >= 0:
            end = text.find(closing, start + len(opening))
            if end < 0:
                break
            if _FIRST_PERSON_EXPRESSION.match(text[start + len(opening) : end].strip()):
                return True
            start = text.find(opening, end + len(closing))
    return False


def _is_attributed_source_text(source: str, candidate: str) -> bool:
    """Reject candidate spans framed as external source text in the real user message."""
    if _SOURCE_ATTRIBUTION.search(candidate) or _FORWARDED_CONTENT.search(candidate):
        return True
    if _contains_quoted_first_person(candidate) and not _FIRST_PERSON_EXPRESSION.match(
        candidate.strip()
    ):
        return True
    if any(line.lstrip().startswith(">") for line in candidate.splitlines()):
        return True

    start = source.find(candidate)
    while start >= 0:
        end = start + len(candidate)
        prefix = source[max(0, start - 80) : start]
        if _SOURCE_ATTRIBUTION_PREFIX.search(prefix) or _FORWARDED_CONTENT_PREFIX.search(prefix):
            return True
        line_start = source.rfind("\n", 0, start) + 1
        if source[line_start:start].lstrip().startswith(">"):
            return True
        for opening, closing in _QUOTE_PAIRS:
            quote_start = source.rfind(opening, 0, start)
            quote_end = source.find(closing, end)
            if quote_start < 0 or quote_end < end:
                continue
            quoted_expression = source[quote_start + len(opening) : quote_end].strip()
            if _FIRST_PERSON_EXPRESSION.match(quoted_expression):
                return True
            attribution = source[max(0, quote_start - 80) : quote_start]
            if _SOURCE_ATTRIBUTION_PREFIX.search(attribution) or _FORWARDED_CONTENT_PREFIX.search(
                attribution
            ):
                return True
        start = source.find(candidate, start + 1)
    return False


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
    acceptance_plan_id: UUID | None = None


class DraftPatchRequest(RequestModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    target_page_id: UUID | None = None
    expected_base_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")


class AgentDraftCreateRequest(RequestModel):
    operation_id: str = Field(min_length=1)
    item_ids: list[UUID] = Field(min_length=1)
    line_id: UUID
    project_id: UUID
    title: str = Field(min_length=1)
    kind: Literal["object", "case", "topic", "decision", "log", "thought"]
    body: str = Field(min_length=1)
    target_page_id: UUID | None = None
    expected_base_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")


class AgentImportRequest(RequestModel):
    text: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


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
    acceptance_plan_id: UUID | None = None


class AcceptancePlanRequest(RequestModel):
    operation: Literal[
        "feishu.materials.read",
        "feishu.materials.import",
        "feishu.calendar.read",
        "feishu.tasks.read",
        "feishu.task.read",
        "model.index",
        "model.query",
        "model.organize",
        "model.journal_assist",
    ]
    scope: dict[str, Any]


class AcceptancePlanConfirmRequest(RequestModel):
    scope_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    scope: dict[str, Any] | None = None


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
    text: str = Field(min_length=1, max_length=100_000)
    acceptance_plan_id: UUID | None = None


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


_LOGGER = logging.getLogger("summit_everything.api")


def error_envelope(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    extra: dict[str, object] | None = None,
) -> JSONResponse:
    """The one error body shape: ``{"error": {code, message, request_id, ...}}``.

    Shared by the exception handlers and the origin guard. Handlers that can run
    before the request-id middleware allocate an id here so the envelope always
    carries a correlation id.
    """
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = secrets.token_hex(8)
        request.state.request_id = request_id
    body: dict[str, object] = {"code": code, "message": message, "request_id": request_id}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status_code, content={"error": body})


def settings_error_response(request: Request, exc: SettingsError) -> JSONResponse:
    """The single shape for an unusable settings/credential store."""
    if exc.code == "validation_error":
        message = "设置字段或凭据无效。"
        return error_envelope(request, status_code=422, code=exc.code, message=message)
    message = "设置或凭据无法使用，请检查本机配置和钥匙串状态。"
    return error_envelope(request, status_code=503, code=exc.code, message=message)


def query_failure_message(exc: BaseException) -> str:
    """A single-line, bounded, credential-free reason for a failed query.

    Only typed, structured failures are described in detail. An unknown
    exception keeps the generic sentence: arbitrary exception text can carry
    credentials or local paths, and the release tests pin that it is never
    echoed to a client. The sanitized cause still reaches the local log.
    """
    if isinstance(exc, EmbeddingProviderError):
        return sanitize_provider_text(describe_failure("向量服务", exc)) or "向量服务不可用。"
    if isinstance(exc, RerankProviderError):
        return sanitize_provider_text(describe_failure("排序服务", exc)) or "排序服务不可用。"
    if isinstance(exc, (ProviderError, LLMProviderError)):
        return sanitize_provider_text(describe_failure("模型服务", exc)) or "模型服务不可用。"
    return "查询未能完成，请稍后重试。"


# Provider keys are single-line printable ASCII tokens. The original class only
# accepted ``[A-Za-z0-9_-]``, which rejected real Model Studio keys that carry
# JWT-style dot separators (for example ``sk-...<dot>...<dot>...``). Keep the
# guard against pasted multi-line blobs and invisible characters, but do not
# narrow the alphabet beyond what the provider formats actually use.
_API_KEY_SHAPE = re.compile(r"sk-[\x21-\x7e]{16,}")
_API_KEY_FORBIDDEN = frozenset("\"'`“”‘’")
_CREDENTIAL_MAX_LENGTH = 512


def safe_failure_reason(exc: BaseException, *, service: str = "provider") -> str:
    """A searchable cause that never carries free-form exception text.

    Typed provider failures render their sanitized structured fields; anything
    else is reduced to the exception type name, because arbitrary exception text
    can carry credentials, local paths or user content, and the release tests
    pin that it never reaches a log or a client.
    """
    if isinstance(exc, (ProviderError, LLMProviderError)):
        if exc.details():
            return describe_failure(service, exc)
        return f"{service}不可用：{REASON_TEXT.get(exc.reason or '', '原因未说明')}。"
    return type(exc).__name__


def assistant_failure(exc: BaseException, *, suffix: str) -> HTTPException:
    """The assist failure envelope: a typed reason, or a safe generic sentence.

    Free-form exception text never reaches the client; a typed provider failure
    renders its sanitized provider fields so the user learns what actually
    failed (the assist path used to answer every failure identically).
    """
    if isinstance(exc, (ProviderError, LLMProviderError)):
        reason = sanitize_provider_text(describe_failure("模型服务", exc))
        if reason:
            return HTTPException(
                status_code=502,
                detail={"code": "assistant_unavailable", "message": f"{reason} {suffix}"},
            )
    return HTTPException(
        status_code=502,
        detail={"code": "assistant_unavailable", "message": f"AI 辅助暂时不可用；{suffix}"},
    )


def record_diagnostic(profile: Path, event: str, *, state: str, reason: object) -> None:
    """Record a profile diagnostic without silently dropping the event.

    The event log cleans the reason (mask, one line, truncate); when cleaning
    still refuses it the minimal safe value is used instead, so an over-long or
    already-masked reason can never cost us the whole record. Only a disk failure
    (OSError) can still stop it.
    """
    candidates = [reason if isinstance(reason, str) else "", FALLBACK_REASON]
    for candidate in candidates:
        try:
            profile_event(profile, event, state=state, reason=candidate)
            return
        except ValueError:
            continue
        except OSError:
            return


def record_assistant_failure(workspace: object, exc: BaseException) -> None:
    """Keep a sanitized, bounded reason in the profile diagnostics log."""
    record_diagnostic(
        Path(workspace.local_profile_dir),  # type: ignore[attr-defined]
        "assistant_failed",
        state="failed",
        reason=safe_failure_reason(exc, service="模型服务"),
    )


def smoke_failure_message(exc: BaseException, *, service: str) -> str:
    """The one-shot warning, prefixed with the reason when it is a typed failure.

    The smoke checks are where the first real failures appeared, so the provider
    reason belongs in the message the WebUI shows; unknown exception text stays
    out of it.
    """
    warning = "请求已计入一次尝试；结果未知，不会自动重发。"
    if isinstance(exc, (ProviderError, LLMProviderError)):
        detail = sanitize_provider_text(describe_failure(service, exc))
        if detail:
            return f"{detail} {warning}"
    return warning


def validate_credential_shape(provider: str, secret: str) -> None:
    """Reject a value that cannot be the credential it claims to be.

    A pasted multi-line blob or a stray table row used to be stored silently and
    only failed later as an opaque provider error. Shape is checked before the
    keychain write; the submitted value is never echoed back.
    """
    if provider in {"deepseek", "dashscope"}:
        if (
            len(secret) > _CREDENTIAL_MAX_LENGTH
            or not _API_KEY_SHAPE.fullmatch(secret)
            or any(character in _API_KEY_FORBIDDEN for character in secret)
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "credential_shape_invalid",
                    "message": (
                        "这不像一把 API key：请确认它以 sk- 开头，且不含空格、换行或引号。"
                    ),
                },
            )
        return
    if provider == "feishu_app":
        if not 8 <= len(secret) <= _CREDENTIAL_MAX_LENGTH or any(
            character.isspace() or ord(character) < 32 for character in secret
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "credential_shape_invalid",
                    "message": "飞书应用密钥不能包含空白或控制字符，长度需在 8 到 512 之间。",
                },
            )


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
    first_use_defaults: FirstUseDefaults | None = None,
    settings_store_factory: Callable[[Path, FirstUseDefaults | None], SettingsStore] | None = None,
) -> FastAPI:
    app = FastAPI(title="SummitEverything Local API", version="1.0.0")
    app.state.acceptance_run_id = uuid4()
    # Non-secret setup values (App ID, callback, base URLs) may be injected by an
    # explicit environment path or by the packaged bundle resource; the runtime
    # reads no repository file. A rejected source fails closed at startup.
    app.state.first_use_defaults = (
        first_use_defaults if first_use_defaults is not None else load_first_use_defaults()
    )
    # Pure-Python dependency injection supports isolated tests that need a
    # synthetic settings store. Runtime callers always get the production
    # SettingsStore; this factory is not selected from HTTP, config or env.
    store_factory = settings_store_factory or (
        lambda path, defaults: SettingsStore(path, defaults=defaults)
    )
    app.state.settings_store_factory = store_factory

    def make_settings_store(path: Path) -> SettingsStore:
        return store_factory(path, app.state.first_use_defaults)

    build_info_path = os.environ.get("SUMMIT_BUILD_INFO")
    build_identity = load_build_identity(build_info_path)
    web_dist = os.environ.get("SUMMIT_WEB_DIST")
    if build_info_path is not None:
        verify_dependency_manifest(build_info_path, build_identity["dependencies_sha256"])
    if web_dist is not None and not (
        Path(web_dist).is_dir() and (Path(web_dist) / "index.html").is_file()
    ):
        raise ValueError("Built WebUI directory is unavailable")
    if web_dist is not None and fingerprint_web_dist(web_dist) != build_identity["frontend_sha256"]:
        raise ValueError("Built WebUI frontend identity does not match build manifest")
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
    if secret_backend is None and os.environ.get("SUMMIT_OFFLINE_GUARD_ACTIVE") == "1":
        secret_backend = UnavailableSecretBackend()
    if secret_backend is None:
        try:
            secret_backend = MacOSKeychainBackend()
        except SettingsError:
            secret_backend = UnavailableSecretBackend()
    app.state.secret_backend = secret_backend
    app.state.local_model_stores = {}
    app.state.local_model_stores_lock = Lock()
    app.state.workspace = None
    intake_service = IntakeService()
    review = review_service or IntakeReviewService()
    app.state.intake_service = intake_service
    app.state.review_service = review
    cancellations: dict[tuple[str, str, str], Event] = {}
    cancellation_requests: set[tuple[str, str, str]] = set()
    config = feishu_config or FeishuConfig()
    feishu_services: dict[tuple[str, ...], FeishuService] = {}
    auth_coordinators: dict[tuple[str, str], FeishuAuthCoordinator] = {}
    action_services: dict[int, ActionService] = {}
    feishu_services_lock = Lock()
    feishu = (
        FeishuService(
            feishu_provider,
            credential_store or MemoryCredentialStore(),
            config,
            app.state.session_token,
        )
        if feishu_provider is not None
        else None
    )
    app.state.feishu_service = feishu

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        origin = request.headers.get("origin")
        workspace = cast(WorkspaceContext | None, app.state.workspace)
        allowed_origins = config.allowed_origins
        if workspace is not None:
            try:
                settings = make_settings_store(
                    Path(workspace.local_profile_dir) / "provider-settings.json"
                ).read()
            except SettingsError as exc:
                # A corrupt profile must fail closed with the designed envelope.
                # This middleware sits outside the application's exception
                # handlers, so an unhandled SettingsError here would escape as a
                # bare 500 and the client could not even tell what happened.
                return settings_error_response(request, exc)
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

    def agent_workspace(
        expected_workspace_id: Annotated[UUID, Header(alias="X-Summit-Workspace-Id")],
    ) -> WorkspaceContext:
        workspace = active_workspace()
        if workspace.workspace_id != expected_workspace_id:
            raise HTTPException(
                status_code=409,
                detail={"code": "workspace_changed", "message": "当前工作库已变化，请重新连接。"},
            )
        return workspace

    def settings_store(workspace: WorkspaceContext) -> SettingsStore:
        return make_settings_store(Path(workspace.local_profile_dir) / "provider-settings.json")

    def local_models_for(workspace: WorkspaceContext) -> LocalRetrievalModelStore:
        profile = Path(workspace.local_profile_dir).resolve()
        key = str(profile)
        with app.state.local_model_stores_lock:
            stores = cast(dict[str, LocalRetrievalModelStore], app.state.local_model_stores)
            if key not in stores:
                stores[key] = LocalRetrievalModelStore(profile / "retrieval-models")
            return stores[key]

    def first_use_progress_store(workspace: WorkspaceContext) -> FirstUseProgressStore:
        # Living inside the workspace's own local profile directory is what
        # isolates the record per profile and per workspace.
        return FirstUseProgressStore(Path(workspace.local_profile_dir) / "first-use-progress.json")

    def acceptance_ledger(workspace: WorkspaceContext) -> AcceptancePlanLedger:
        return AcceptancePlanLedger(Path(workspace.local_profile_dir))

    def credential_generations(workspace: WorkspaceContext) -> CredentialGenerationStore:
        return CredentialGenerationStore(Path(workspace.local_profile_dir))

    def persist_provider_usage(
        workspace: WorkspaceContext, plan_id: UUID, providers: tuple[Any, ...]
    ) -> None:
        usage = [
            ProviderUsage.model_validate(record)
            for provider in providers
            for record in getattr(provider, "usage_records", [])
        ]
        if usage:
            acceptance_ledger(workspace).record_usage(plan_id, usage)

    def profile_binding(workspace: WorkspaceContext) -> str:
        resolved = str(Path(workspace.local_profile_dir).resolve())
        return hashlib.sha256(resolved.encode()).hexdigest()

    def legacy_settings_binding(workspace: WorkspaceContext) -> str:
        settings = settings_store(workspace).read()
        encoded = json.dumps(
            settings.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def settings_binding(workspace: WorkspaceContext) -> str:
        return credential_bound_settings_binding(
            legacy_settings_binding(workspace),
            credential_generations(workspace).get("deepseek"),
        )

    def credential_bound_settings_binding(settings_digest: str, generation: int) -> str:
        return json_binding(
            {
                "settings": settings_digest,
                "deepseek_credential_generation": generation,
            }
        )

    def model_call_status(workspace: WorkspaceContext) -> dict[str, object]:
        try:
            generation = credential_generations(workspace).get("deepseek")
            settings_digest = legacy_settings_binding(workspace)
            current_binding = credential_bound_settings_binding(settings_digest, generation)
        except Exception:
            return {"state": "unreadable", "has_success": False}
        compatible_bindings = {current_binding}
        # Existing acceptance plans predate credential generations. They can
        # be adopted only before this app has observed a DeepSeek key change.
        if generation == 0:
            compatible_bindings.add(settings_digest)
        profile_id = profile_binding(workspace)
        ledger_unreadable = False
        try:
            plan_items = [
                plan
                for plan in acceptance_ledger(workspace).list_plans()
                if plan.operation in {"model.organize", "model.query", "model.journal_assist"}
                and plan.workspace_id == str(workspace.workspace_id)
                and plan.profile_id == profile_id
                and plan.config_sha256 in compatible_bindings
            ]
        except RuntimeError:
            plan_items = []
            ledger_unreadable = True
        successful = [
            plan
            for plan in plan_items
            if plan.state == "succeeded"
            and any(item.provider == "deepseek" for item in plan.provider_usage)
        ]
        attempts = [
            plan
            for plan in plan_items
            if plan.requests_reserved > 0 and plan.state in {"succeeded", "failed", "unknown"}
        ]
        latest_attempt = max(
            attempts, key=lambda plan: plan.finished_at or plan.created_at, default=None
        )
        latest_success = max(
            successful, key=lambda plan: plan.finished_at or plan.created_at, default=None
        )
        latest_state = "none"
        latest_attempt_at = (
            latest_attempt.finished_at.isoformat()
            if latest_attempt is not None and latest_attempt.finished_at is not None
            else None
        )
        latest_success_at = (
            latest_success.finished_at.isoformat()
            if latest_success is not None and latest_success.finished_at is not None
            else None
        )
        if latest_attempt is not None:
            latest_state = (
                latest_attempt.state
                if latest_attempt.state in {"failed", "unknown"}
                else "succeeded"
                if any(item.provider == "deepseek" for item in latest_attempt.provider_usage)
                else "unknown"
            )
        try:
            smoke = smoke_result(Path(app.state.profile_root), "deepseek_chat")
        except RuntimeError:
            smoke = None
            ledger_unreadable = True
        if (
            smoke
            and smoke.get("workspace_id") == str(workspace.workspace_id)
            and smoke.get("profile_id") == profile_id
            and smoke.get("config_sha256") in compatible_bindings
        ):
            smoke_at = smoke.get("finished_at")
            if not latest_attempt_at or (smoke_at and smoke_at > latest_attempt_at):
                latest_state = smoke.get("state", "unknown")
                latest_attempt_at = smoke_at
            if smoke.get("state") == "succeeded" and (
                not latest_success_at or (smoke_at and smoke_at > latest_success_at)
            ):
                latest_success_at = smoke_at
        if latest_state == "none" and latest_success_at:
            latest_state = "succeeded"
        if latest_state == "none" and ledger_unreadable:
            latest_state = "unreadable"
        return {
            "state": latest_state,
            "has_success": latest_success_at is not None,
            "last_attempt_at": latest_attempt_at,
            "last_success_at": latest_success_at,
        }

    def operation_config_binding(workspace: WorkspaceContext, operation: str) -> str:
        if operation.startswith("feishu."):
            return json_binding(
                {
                    "settings": legacy_settings_binding(workspace),
                    "authorization_generation": feishu_auth_generation(workspace),
                }
            )
        return settings_binding(workspace)

    def feishu_auth_generation(workspace: WorkspaceContext) -> int:
        # This reads only the in-process coordinator counter; it does not inspect
        # credentials or contact the provider. Logout/new OAuth changes the value.
        return feishu_for(workspace).auth.version()

    def json_binding(value: object) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    def normalize_feishu_scope(operation: str, values: dict[str, Any]) -> dict[str, Any]:
        defaults: dict[str, dict[str, Any]] = {
            "feishu.materials.read": {"query": "", "visibility": None, "cursor": None, "limit": 20},
            "feishu.materials.import": {"material_ids": [], "operation_id": None},
            "feishu.calendar.read": {
                "start": None,
                "end": None,
                "timezone": None,
                "cursor": None,
                "limit": 20,
            },
            "feishu.tasks.read": {"cursor": None, "limit": 20},
            "feishu.task.read": {"task_guid": ""},
        }
        expected = defaults.get(operation)
        if expected is None or set(values) - set(expected):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "授权范围字段无效。"}
            )
        result = {**expected, **values}
        if operation == "feishu.materials.read":
            if (
                not isinstance(result["query"], str)
                or len(result["query"]) > 500
                or result["visibility"] not in {None, "owner", "shared"}
                or result["cursor"] is not None
                and (not isinstance(result["cursor"], str) or len(result["cursor"]) > 500)
                or type(result["limit"]) is not int
                or not 1 <= result["limit"] <= 30
            ):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "材料授权范围无效。"}
                )
        elif operation == "feishu.calendar.read":
            try:
                start = datetime.fromisoformat(str(result["start"]))
                end = datetime.fromisoformat(str(result["end"]))
                if (
                    start.tzinfo is None
                    or end.tzinfo is None
                    or not isinstance(result["timezone"], str)
                ):
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "日历授权范围无效。"}
                ) from None
            result["start"] = start.isoformat()
            result["end"] = end.isoformat()
            if result["cursor"] is not None and (
                not isinstance(result["cursor"], str) or len(result["cursor"]) > 500
            ):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "日历授权范围无效。"}
                )
            if type(result["limit"]) is not int or not 1 <= result["limit"] <= 30:
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "日历授权范围无效。"}
                )
        elif operation == "feishu.tasks.read":
            if result["cursor"] is not None and (
                not isinstance(result["cursor"], str) or len(result["cursor"]) > 500
            ):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "任务授权范围无效。"}
                )
            if type(result["limit"]) is not int or not 1 <= result["limit"] <= 100:
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "任务授权范围无效。"}
                )
        elif operation == "feishu.materials.import":
            material_ids = result["material_ids"]
            if (
                not isinstance(material_ids, list)
                or not 1 <= len(material_ids) <= 20
                or len(set(material_ids)) != len(material_ids)
                or any(
                    not isinstance(value, str) or not value or len(value) > 500
                    for value in material_ids
                )
                or not isinstance(result["operation_id"], str)
                or not result["operation_id"]
                or len(result["operation_id"]) > 200
            ):
                raise HTTPException(
                    422,
                    detail={
                        "code": "validation_error",
                        "message": "材料导入范围无效；最多选择 20 份材料。",
                    },
                )
        elif operation == "feishu.task.read":
            if (
                not isinstance(result["task_guid"], str)
                or not result["task_guid"]
                or len(result["task_guid"]) > 200
            ):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "任务授权范围无效。"}
                )
        else:
            ids = result["material_ids"]
            if (
                not isinstance(ids, list)
                or not 1 <= len(ids) <= 30
                or any(not isinstance(item, str) or not item or len(item) > 200 for item in ids)
                or len(set(ids)) != len(ids)
                or not isinstance(result["operation_id"], str)
                or not result["operation_id"]
                or len(result["operation_id"]) > 200
            ):
                raise HTTPException(
                    422, detail={"code": "validation_error", "message": "材料选择授权范围无效。"}
                )
        return result

    def normalize_index_scope(
        workspace: WorkspaceContext, values: dict[str, Any]
    ) -> dict[str, Any]:
        if set(values) != {"mode", "fingerprint", "page_ids", "page_versions"}:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "索引授权范围字段无效。"}
            )
        mode, fingerprint = values["mode"], values["fingerprint"]
        if (
            mode not in {"initial", "incremental", "full", "model_change"}
            or not isinstance(fingerprint, str)
            or not isinstance(values["page_ids"], list)
            or not isinstance(values["page_versions"], dict)
        ):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "索引授权范围无效。"}
            )
        try:
            current = query_for(workspace).plan(
                Path(workspace.root), fingerprint=fingerprint, mode=mode
            )
        except (ValueError, WorkspaceError):
            raise HTTPException(
                409,
                detail={"code": "acceptance_plan_stale", "message": "索引计划已变化，请重新预览。"},
            ) from None
        page_ids = sorted(str(item) for item in current.page_ids)
        page_versions = {key: current.page_versions[key] for key in sorted(current.page_versions)}
        if sorted(values["page_ids"]) != page_ids or values["page_versions"] != page_versions:
            raise HTTPException(
                409,
                detail={
                    "code": "acceptance_plan_stale",
                    "message": "合格页面或版本已变化，请重新预览。",
                },
            )
        return {
            "mode": mode,
            "fingerprint": fingerprint,
            "page_ids": page_ids,
            "page_versions": page_versions,
        }

    def index_embedding_call_bound(workspace: WorkspaceContext, scope: dict[str, Any]) -> int:
        chunks = 0
        for page_id in scope["page_ids"]:
            page = read_page(Path(workspace.root), UUID(page_id))
            expected = scope["page_versions"].get(page_id)
            if page.content_sha256 != expected:
                raise HTTPException(
                    409,
                    detail={
                        "code": "acceptance_plan_stale",
                        "message": "合格页面已变化，请重新预览。",
                    },
                )
            chunks += len(chunk_markdown(page.page_id, page.content_sha256, page.body))
        # Qwen embedding accepts up to 20 texts per provider operation.
        return max(1, (chunks + 19) // 20)

    def normalize_organize_scope(
        workspace: WorkspaceContext, values: dict[str, Any]
    ) -> dict[str, Any]:
        allowed = {"item_ids", "operation_id", "line_id", "project_id", "reprocess"}
        if set(values) != allowed:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "整理范围字段无效。"}
            )
        try:
            item_ids = [UUID(value) for value in values["item_ids"]]
            line_id = UUID(values["line_id"])
            project_id = UUID(values["project_id"])
            operation_id = str(values["operation_id"])
            reprocess = bool(values["reprocess"])
            inputs = review.preview_inputs(
                Path(workspace.root),
                item_ids,
                line_id=line_id,
                project_id=project_id,
                reprocess=reprocess,
            )
        except (ValueError, TypeError, WorkspaceError) as exc:
            raise HTTPException(
                409,
                detail={
                    "code": "acceptance_plan_stale",
                    "message": "所选来源或目标已变化，请重新预览。",
                },
            ) from exc
        return {
            "item_ids": [str(item_id) for item_id in item_ids],
            "operation_id": operation_id,
            "line_id": str(line_id),
            "project_id": str(project_id),
            "reprocess": reprocess,
            "max_output_tokens": settings_store(workspace).read().llm.max_output_tokens,
            # Returned only to the local preview caller; the ledger persists the digest, never text.
            "outgoing_inputs": [
                {"item_id": str(item_id), "source_id": str(source_id), "text": text}
                for item_id, source_id, text in inputs
            ],
        }

    def normalize_journal_assist_scope(
        workspace: WorkspaceContext, values: dict[str, Any]
    ) -> dict[str, Any]:
        if set(values) - {"text", "max_output_tokens"}:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "日志辅助范围字段无效。"}
            )
        text = values.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 100_000:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "请提供有效的日志正文。"}
            )
        max_output_tokens = settings_store(workspace).read().llm.max_output_tokens
        supplied_budget = values.get("max_output_tokens", max_output_tokens)
        if type(supplied_budget) is not int or supplied_budget != max_output_tokens:
            raise HTTPException(
                409,
                detail={
                    "code": "acceptance_plan_stale",
                    "message": "模型输出预算已变化，请重新预览。",
                },
            )
        return {"text": text, "max_output_tokens": max_output_tokens}

    def normalize_query_scope(
        workspace: WorkspaceContext, values: dict[str, Any]
    ) -> dict[str, Any]:
        allowed = {
            "question",
            "fingerprint",
            "purpose",
            "answer_mode",
            "role_id",
            "request_id",
            "conversation_id",
        }
        if set(values) - allowed or "request_id" not in values or "question" not in values:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "问答授权范围字段无效。"}
            )
        try:
            query = QueryRequest.model_validate(values)
        except ValueError:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "问答授权范围无效。"}
            ) from None
        if query.request_id is None:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "问答计划需要固定请求标识。"}
            )
        store = conversations_for(workspace)
        answer_store = answer_context_for(workspace)
        selected_role = None
        if query.role_id is not None:
            selected_role = answer_store.role(workspace.workspace_id, query.role_id)
            if selected_role is None:
                raise HTTPException(
                    404, detail={"code": "not_found", "message": "找不到这个问答角色。"}
                )
            if len(selected_role.instructions.encode("utf-8")) > selected_role.context_budget:
                raise HTTPException(
                    422,
                    detail={
                        "code": "context_budget_exceeded",
                        "message": "角色说明超过设定预算；请编辑角色内容后重试。",
                    },
                )
        try:
            memories = answer_store.active_memory_text(workspace.workspace_id)
        except ContextConflict as exc:
            raise HTTPException(
                422, detail={"code": "context_budget_exceeded", "message": str(exc)}
            ) from None
        previous_questions = store.previous_user_questions(
            workspace.workspace_id, query.conversation_id, excluding=query.request_id
        )
        context = AnswerContext(
            answer_mode=query.answer_mode,
            role_name=selected_role.name if selected_role else "",
            role_instructions=selected_role.instructions if selected_role else "",
            user_memories=memories,
            previous_user_questions=previous_questions,
        )
        purpose = RetrievalPurpose(query.purpose)
        # Authorization scope comes from the canonical content eligibility
        # rule, not from an optionally injected query executor. The latter may
        # be a narrow adapter (for example, one that only exposes query()).
        pages = QueryService._eligible_pages(list_pages(Path(workspace.root)), purpose=purpose)
        versions = {
            str(page.page_id): page.content_sha256
            for page in sorted(pages, key=lambda item: str(item.page_id))
        }
        settings = settings_store(workspace).read()
        return {
            "request_id": str(query.request_id),
            "conversation_id": str(query.conversation_id) if query.conversation_id else None,
            "question": query.question,
            "purpose": query.purpose,
            "answer_mode": query.answer_mode,
            "role_id": str(query.role_id) if query.role_id else None,
            "context": context.model_dump(mode="json"),
            "source_versions": versions,
            "fingerprint": query.fingerprint,
            "max_output_tokens": settings.llm.max_output_tokens,
            "reasoning_effort": settings.llm.reasoning_effort,
        }

    def start_feishu_plan(
        workspace: WorkspaceContext,
        operation: str,
        scope: dict[str, Any],
        plan_id: UUID | None,
        request_count: int = 1,
    ) -> UUID | None:
        settings = settings_store(workspace).read()
        if settings.mode != "real":
            return None
        if not settings.feishu.app_id:
            raise HTTPException(
                status_code=409,
                detail={"code": "provider_not_configured", "message": "请先配置飞书 App ID。"},
            )
        if plan_id is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "acceptance_plan_required",
                    "message": "真实飞书读取需先预览并确认本次范围。",
                },
            )
        scope_sha256 = json_binding(
            {
                "operation": operation,
                "scope": scope,
                "authorization_generation": feishu_auth_generation(workspace),
            }
        )
        ledger = acceptance_ledger(workspace)
        try:
            prior = ledger.get(plan_id)
            if prior.operation != operation or request_count > prior.request_limit:
                raise PlanConflict("operation does not match its approved request bound")
            ledger.begin_execution(
                plan_id,
                workspace_id=str(workspace.workspace_id),
                profile_id=profile_binding(workspace),
                config_sha256=operation_config_binding(workspace, operation),
                scope_sha256=scope_sha256,
                run_id=app.state.acceptance_run_id,
            )
            for _ in range(request_count):
                ledger.reserve_request(
                    plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                )
            return plan_id
        except PlanConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "acceptance_plan_conflict", "message": plan_conflict_message(exc)},
            ) from None

    def finish_feishu_plan(workspace: WorkspaceContext, plan_id: UUID | None, state: str) -> None:
        if plan_id is None:
            return
        ledger = acceptance_ledger(workspace)
        try:
            ledger.finish(plan_id, state=cast(Any, state))
        except PlanConflict:
            logging.getLogger(__name__).error("Acceptance plan state could not be finalized")

    def feishu_for(workspace: WorkspaceContext) -> FeishuService:
        settings = settings_store(workspace).read()
        app_id = settings.feishu.app_id or config.app_id
        redirect_uri = settings.feishu.redirect_uri or config.redirect_uri
        parts = urlsplit(redirect_uri)
        callback_origin = f"{parts.scheme}://{parts.netloc}"
        # A missing app ID/secret is a real configuration gap, not a reason to
        # select the simulated Feishu provider in a normal app session.
        real = settings.mode == "real"
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
                    raise SettingsError("provider_not_allowed")
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

    def feishu_calendar_ready_for(workspace: WorkspaceContext) -> bool:
        settings = settings_store(workspace).read()
        if settings.mode != "real" or not (settings.feishu.app_id or config.app_id):
            return False
        return feishu_for(workspace).status().calendar_ready

    def require_feishu_data(
        workspace: WorkspaceContext,
        operation: str,
        scope: dict[str, Any],
        plan_id: UUID | None,
        request_count: int = 1,
    ) -> UUID | None:
        return start_feishu_plan(workspace, operation, scope, plan_id, request_count)

    def require_calendar_provider_config(workspace: WorkspaceContext) -> None:
        current = settings_store(workspace).read()
        # A missing app_id is a real setup gap, not permission to read a
        # synthetic calendar through an adapter selected for tests.
        if current.mode == "real" and not current.feishu.app_id:
            raise HTTPException(
                409,
                detail={"code": "provider_not_configured", "message": "请先完成飞书应用配置。"},
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

    register_actions(
        app,
        actions_for,
        authenticated,
        active_workspace,
        require_feishu_data,
        finish_feishu_plan,
    )

    @app.exception_handler(SettingsError)
    async def settings_error_handler(request: Request, exc: SettingsError) -> JSONResponse:
        return settings_error_response(request, exc)

    @app.exception_handler(FirstUseProgressError)
    async def first_use_progress_error_handler(
        request: Request, exc: FirstUseProgressError
    ) -> JSONResponse:
        # A store that cannot be read or written must be visible; the wizard
        # must never be told "saved" when the durable write did not land.
        return error_envelope(
            request,
            status_code=503,
            code=exc.code,
            message="首次配置进度无法读写，请检查本机 profile 后重试。",
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
        return ModelRuntime(
            settings_store(workspace).read(),
            credential_vault(workspace),
            local_models_for(workspace),
        )

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
        labels = {
            "llm": "整理与问答模型",
            "embedding": "知识索引向量化",
            "rerank": "检索结果排序",
        }
        missing: list[str] = []
        for name in providers:
            config = selected[name]
            if name in {"embedding", "rerank"} and config.provider == "dashscope":
                missing.append(f"{labels[name]}已停用旧云端配置，请切换到本地模型")
                continue
            if name in {"embedding", "rerank"} and config.provider == "local":
                if local_models_for(workspace).status()["state"] != "ready":
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "local_model_not_ready",
                            "message": "请先在设置中准备本地检索模型，再建立索引或提问。",
                        },
                    )
                continue
            if config.provider == "fake":
                missing.append(f"{labels[name]}未选择真实模型")
                continue
            if not config.enabled:
                missing.append(f"{labels[name]}未启用")
                continue
            if not config.model:
                missing.append(f"{labels[name]}未选择模型")
        if missing:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_disabled",
                    "message": "所需 AI 服务尚未配置完成："
                    + "；".join(missing)
                    + "。请到设置完成配置后重新查看本次预览；不会自动改用模拟结果或自动重发。",
                },
            )

    def review_for(workspace: WorkspaceContext) -> IntakeReviewService:
        if review_service is not None:
            return review_service
        ensure_remote_calls_allowed(workspace, ("llm",))
        return IntakeReviewService(runtime_for(workspace).llm())

    def fingerprint_is_current(workspace: WorkspaceContext, fingerprint: str) -> bool:
        settings = settings_store(workspace).read()
        if settings.mode == "fake":
            return True
        return fingerprint == embedding_fingerprint(settings.embedding, mode=settings.mode)

    def query_for(
        workspace: WorkspaceContext,
        *,
        remote: bool = False,
        provider_guard: Any = None,
        required_providers: tuple[str, ...] = ("embedding", "rerank", "llm"),
        local_costs: bool = False,
    ) -> QueryService:
        if query_service is not None:
            return query_service
        if remote:
            ensure_remote_calls_allowed(workspace, required_providers)
        settings = settings_store(workspace).read()
        # Fake providers are allowed only through explicit test settings
        # injection. Production real-mode metadata/preview requests must not
        # instantiate them implicitly.
        providers = runtime_for(workspace) if remote or settings.mode == "fake" else None
        return QueryService(
            IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3"),
            embedding=providers.embedding()
            if providers and "embedding" in required_providers
            else None,
            reranker=providers.reranker() if providers and "rerank" in required_providers else None,
            answer_provider=(
                cast(AnswerProvider, providers.llm())
                if providers and "llm" in required_providers
                else None
            ),
            provider_guard=provider_guard,
            local_costs=local_costs,
            # Production API services never synthesize test adapters when a
            # metadata/preview path does not need a provider. Generation and
            # query calls must receive the configured runtime adapters above.
            require_explicit_providers=True,
        )

    def require_query_index_ready(workspace: WorkspaceContext, fingerprint: str) -> None:
        """Reject a real query before reserving calls when no matching index exists."""
        settings = settings_store(workspace).read()
        expected = embedding_fingerprint(settings.embedding, mode=settings.mode)
        active = IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3").active_fingerprint(
            workspace.workspace_id
        )
        if active is None or active != expected or fingerprint != expected:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "index_not_ready",
                    "message": (
                        "当前本机索引尚未按已选向量模型准备完成。请前往审批建立或更新索引后再提问；"
                        "本次问题已保留，尚未预留或发送模型请求。"
                    ),
                },
            )

    def require_local_retrieval_ready(workspace: WorkspaceContext) -> None:
        if query_service is not None:
            return
        settings = settings_store(workspace).read()
        if settings.mode == "fake":
            return
        if settings.embedding.provider == "dashscope" or settings.rerank.provider == "dashscope":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "legacy_provider_migration_required",
                    "message": (
                        "旧版云端检索配置已停用，请在设置中切换为本地检索模型并重新建立索引。"
                    ),
                },
            )
        if settings.embedding.provider != "local" or settings.rerank.provider != "local":
            raise HTTPException(
                status_code=409,
                detail={"code": "local_provider_required", "message": "请先选择本地检索模型。"},
            )
        if local_models_for(workspace).status()["state"] != "ready":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "local_model_not_ready",
                    "message": "本地检索模型尚未准备完成；请在设置中下载并校验模型文件。",
                },
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
        return citation_availability_of_page(page, citation, purpose)

    def citation_availability_of_page(page: Any, citation: Any, purpose: str) -> str:
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
        return provider_settings_payload(
            settings,
            credential_vault(workspace),
            local_model_status=local_models_for(workspace).status(),
            legacy_provider_migration_required=settings.legacy_provider_migration_required,
            feishu_calendar_ready=feishu_calendar_ready_for(workspace),
            model_call_status=model_call_status(workspace),
        )

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
        return provider_settings_payload(
            settings,
            credential_vault(workspace),
            local_model_status=local_models_for(workspace).status(),
            legacy_provider_migration_required=settings.legacy_provider_migration_required,
            feishu_calendar_ready=feishu_calendar_ready_for(workspace),
            model_call_status=model_call_status(workspace),
        )

    @app.get(
        "/api/v1/retrieval-model/status",
        response_model=LocalModelStatus,
        dependencies=[Depends(authenticated)],
    )
    def retrieval_model_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        return local_models_for(workspace).status()

    @app.post(
        "/api/v1/retrieval-model/prepare",
        response_model=LocalModelStatus,
        dependencies=[Depends(authenticated)],
    )
    def retrieval_model_prepare(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        try:
            return local_models_for(workspace).start_prepare()
        except LocalModelError as exc:
            status_code = 409 if exc.code == "model_directory_read_only" else 503
            raise HTTPException(
                status_code=status_code,
                detail={
                    "code": exc.code,
                    "message": "无法准备本地检索模型，请检查本机存储后重试。",
                },
            ) from None

    @app.get("/api/v1/first-use/progress", dependencies=[Depends(authenticated)])
    def get_first_use_progress(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> FirstUseProgress:
        progress = first_use_progress_store(workspace).read()
        if progress is None:
            # "No record yet" is a real answer, not a default: the UI must be
            # able to tell a brand-new workspace from one whose wizard the user
            # explicitly closed.
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "first_use_progress_absent",
                    "message": "本机还没有保存首次配置进度。",
                },
            )
        return progress

    @app.put("/api/v1/first-use/progress", dependencies=[Depends(authenticated)])
    def put_first_use_progress(
        payload: FirstUseProgress,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> FirstUseProgress:
        # Only step / completed / open reach this point; extra or secret-shaped
        # fields are rejected by the model before any write is attempted.
        return first_use_progress_store(workspace).write(payload)

    @app.put("/api/v1/credentials/{provider}", dependencies=[Depends(authenticated)])
    def put_credential(
        provider: str,
        payload: CredentialRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        validate_credential_account(workspace, provider, payload.account_id)
        secret = payload.secret.get_secret_value()
        validate_credential_shape(provider, secret)
        vault = credential_vault(workspace)
        if provider == "deepseek":
            # Fail before creating the local generation record when Keychain is
            # unavailable. Keep the generation bump before the real mutation so
            # a failed write cannot leave stale success evidence reusable.
            vault.has(provider, account_id=payload.account_id)
            credential_generations(workspace).bump(provider)
        vault.put(provider, secret, account_id=payload.account_id)
        return {"provider": provider, "configured": True}

    @app.delete("/api/v1/credentials/{provider}", dependencies=[Depends(authenticated)])
    def delete_credential(
        provider: str,
        payload: CredentialAccountRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Response:
        validate_credential_account(workspace, provider, payload.account_id)
        vault = credential_vault(workspace)
        if provider == "deepseek":
            vault.has(provider, account_id=payload.account_id)
            credential_generations(workspace).bump(provider)
        vault.delete(provider, account_id=payload.account_id)
        return Response(status_code=204)

    @app.post("/api/v1/acceptance-plans", status_code=201, dependencies=[Depends(authenticated)])
    def acceptance_plan_create(
        payload: AcceptancePlanRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        settings = settings_store(workspace).read()
        if payload.operation == "model.index":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "local_index_plan_required",
                    "message": "本地索引无需外部调用授权，请使用索引预览计划。",
                },
            )
        if settings.mode != "real":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_not_configured",
                    "message": "请先配置 Real 模式，再预览外部调用范围。",
                },
            )
        if payload.operation.startswith("feishu.") and not settings.feishu.app_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "provider_not_configured",
                    "message": "请先配置飞书 App ID，再预览飞书操作范围。",
                },
            )
        if payload.operation == "model.query":
            ensure_remote_calls_allowed(workspace, ("llm",))
            require_local_retrieval_ready(workspace)
        elif payload.operation == "model.organize":
            ensure_remote_calls_allowed(workspace, ("llm",))
        elif payload.operation == "model.journal_assist":
            ensure_remote_calls_allowed(workspace, ("llm",))
        if payload.operation == "model.query":
            scope = normalize_query_scope(workspace, payload.scope)
            require_query_index_ready(workspace, str(scope["fingerprint"]))
            request_limit = 1  # local embedding/ranking; DeepSeek answer only
        elif payload.operation == "model.organize":
            scope = normalize_organize_scope(workspace, payload.scope)
            request_limit = 1
        elif payload.operation == "model.journal_assist":
            scope = normalize_journal_assist_scope(workspace, payload.scope)
            request_limit = 1
        else:
            scope = normalize_feishu_scope(payload.operation, payload.scope)
            request_limit = (
                3 * len(scope["material_ids"]) + 2
                if payload.operation == "feishu.materials.import"
                else 2
            )
        if request_limit > 100:
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_error", "message": "本次授权范围超过上限。"},
            )
        scope_binding: dict[str, object] = {"operation": payload.operation, "scope": scope}
        if payload.operation.startswith("feishu."):
            scope_binding["authorization_generation"] = feishu_auth_generation(workspace)
        scope_sha256 = json_binding(scope_binding)
        try:
            plan = acceptance_ledger(workspace).create(
                operation=payload.operation,
                workspace_id=str(workspace.workspace_id),
                profile_id=profile_binding(workspace),
                config_sha256=operation_config_binding(workspace, payload.operation),
                scope_sha256=scope_sha256,
                scope=scope,
                request_limit=max(1, request_limit),
            )
        except RuntimeError:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "acceptance_plan_ledger_unavailable",
                    "message": "本机授权账本已满或不可用。",
                },
            ) from None
        return {"plan": plan, "scope": scope}

    @app.post(
        "/api/v1/acceptance-plans/{plan_id}/confirm",
        dependencies=[Depends(authenticated)],
    )
    def acceptance_plan_confirm(
        plan_id: UUID,
        payload: AcceptancePlanConfirmRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> AcceptancePlan:
        try:
            current = acceptance_ledger(workspace).get(plan_id)
            if payload.scope is None:
                if current.operation.startswith("model."):
                    raise PlanConflict("model plan confirmation needs its displayed scope")
                scope = None
            elif current.operation == "model.index":
                scope = normalize_index_scope(workspace, payload.scope)
            elif current.operation == "model.query":
                query_intent = {
                    key: payload.scope[key]
                    for key in (
                        "question",
                        "fingerprint",
                        "purpose",
                        "answer_mode",
                        "role_id",
                        "request_id",
                        "conversation_id",
                    )
                    if key in payload.scope
                }
                scope = normalize_query_scope(workspace, query_intent)
            elif current.operation == "model.organize":
                organize_intent = {
                    key: payload.scope[key]
                    for key in ("item_ids", "operation_id", "line_id", "project_id", "reprocess")
                    if key in payload.scope
                }
                scope = normalize_organize_scope(workspace, organize_intent)
            elif current.operation == "model.journal_assist":
                scope = normalize_journal_assist_scope(workspace, payload.scope or {})
            else:
                scope = normalize_feishu_scope(current.operation, payload.scope)
            expected_sha = payload.scope_sha256
            if scope is not None:
                binding: dict[str, object] = {"operation": current.operation, "scope": scope}
                if current.operation.startswith("feishu."):
                    binding["authorization_generation"] = feishu_auth_generation(workspace)
                expected_sha = json_binding(binding)
                if expected_sha != payload.scope_sha256:
                    raise PlanConflict("preview scope changed before confirmation")
            return acceptance_ledger(workspace).confirm(
                plan_id,
                workspace_id=str(workspace.workspace_id),
                profile_id=profile_binding(workspace),
                config_sha256=operation_config_binding(workspace, current.operation),
                scope_sha256=expected_sha,
            )
        except PlanConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "acceptance_plan_conflict", "message": plan_conflict_message(exc)},
            ) from None

    @app.get("/api/v1/acceptance-plans/{plan_id}", dependencies=[Depends(authenticated)])
    def acceptance_plan_get(
        plan_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> AcceptancePlan:
        try:
            plan = acceptance_ledger(workspace).get(plan_id)
        except PlanConflict as exc:
            raise HTTPException(
                status_code=404,
                detail={"code": "acceptance_plan_not_found", "message": plan_conflict_message(exc)},
            ) from None
        if plan.workspace_id != str(workspace.workspace_id) or plan.profile_id != profile_binding(
            workspace
        ):
            raise HTTPException(
                status_code=404,
                detail={"code": "acceptance_plan_not_found", "message": "找不到本次计划。"},
            )
        # A process interruption after request reservation is observable as unknown;
        # the plan remains consumed and has no resume or resend endpoint.
        if plan.state == "executing" and plan.execution_run_id != app.state.acceptance_run_id:
            # This timestamp records when this process observed the interrupted run,
            # not when the provider operation finished. Keep the ledger unchanged.
            return AcceptancePlan.model_validate(
                {
                    **plan.model_dump(),
                    "state": "unknown",
                    "finished_at": datetime.now(UTC),
                }
            )
        return plan

    @app.delete("/api/v1/acceptance-plans/{plan_id}", dependencies=[Depends(authenticated)])
    def acceptance_plan_cancel(
        plan_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> AcceptancePlan:
        try:
            return acceptance_ledger(workspace).cancel(
                plan_id,
                workspace_id=str(workspace.workspace_id),
                profile_id=profile_binding(workspace),
            )
        except PlanConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "acceptance_plan_conflict", "message": plan_conflict_message(exc)},
            ) from None

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
        if operation in {"model_studio_embedding", "model_studio_rerank"}:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "legacy_provider_migration_required",
                    "message": "云端检索连接测试已停用，请切换到本地检索模型。",
                },
            )
        settings = settings_store(workspace).read()
        requirement = {
            "deepseek_chat": settings.mode == "real"
            and settings.llm.provider == "deepseek"
            and settings.llm.enabled,
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

    def persist_smoke_result(
        workspace: WorkspaceContext,
        operation: str,
        state: Literal["succeeded", "failed", "unknown"],
        config_sha256: str,
    ) -> None:
        try:
            record_smoke_result(
                Path(app.state.profile_root),
                operation,
                workspace_id=str(workspace.workspace_id),
                profile_id=profile_binding(workspace),
                config_sha256=config_sha256,
                state=state,
            )
        except Exception:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "smoke_ledger_unavailable",
                    "message": "本地调用记录不可用；无法确认本次检查状态。",
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
        call_binding = settings_binding(workspace)
        attempt: int | None = None
        try:
            attempt = reserve_smoke("deepseek_chat")
            provider.answer(
                "请仅复述合成短语。",
                [{"heading": "合成标题", "excerpt": "合成短语：连接正常。"}],
            )
            persist_smoke_result(workspace, "deepseek_chat", "succeeded", call_binding)
            return {"state": "succeeded", "operation": "deepseek_chat", "attempt": attempt}
        except HTTPException:
            raise
        except Exception as exc:
            if attempt is not None:
                try:
                    persist_smoke_result(workspace, "deepseek_chat", "unknown", call_binding)
                except HTTPException:
                    pass
            detail: dict[str, object] = {
                "code": "provider_smoke_failed",
                "message": smoke_failure_message(exc, service="模型服务"),
            }
            if isinstance(exc, (ProviderError, LLMProviderError)) and exc.details():
                detail["provider"] = exc.details()
            raise HTTPException(status_code=502, detail=detail) from None
        finally:
            provider.close()

    @app.post(
        "/api/v1/provider-smoke/model-studio-embedding", dependencies=[Depends(authenticated)]
    )
    def smoke_model_studio_embedding(
        _workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "legacy_provider_migration_required",
                "message": "云端检索连接测试已停用，请切换到本地检索模型。",
            },
        )

    @app.post("/api/v1/provider-smoke/model-studio-rerank", dependencies=[Depends(authenticated)])
    def smoke_model_studio_rerank(
        _workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, object]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "legacy_provider_migration_required",
                "message": "云端检索连接测试已停用，请切换到本地检索模型。",
            },
        )

    def index_after_approval(
        workspace: WorkspaceContext, mutation: MutationResult
    ) -> MutationResult:
        try:
            settings = settings_store(workspace).read()
            store = (
                query_service.store
                if query_service is not None
                else IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3")
            )
            fingerprint = store.active_fingerprint(workspace.workspace_id)
            if fingerprint is None:
                return mutation.model_copy(update={"index_update": "not_enabled"})
            expected_fingerprint = embedding_fingerprint(settings.embedding, mode=settings.mode)
            if query_service is None and fingerprint != expected_fingerprint:
                # Never append vectors from a newly selected model to a generation
                # created by another model. Keep the old generation intact until
                # the user explicitly previews and confirms model_change.
                return mutation.model_copy(update={"index_update": "manual_required"})
            if settings.mode == "real" and settings.embedding.provider == "dashscope":
                return mutation.model_copy(update={"index_update": "manual_required"})
            service = query_for(
                workspace,
                remote=settings.mode == "real" and settings.embedding.provider == "local",
                required_providers=("embedding",),
            )
            root = Path(workspace.root)
            plan = service.plan(root, fingerprint=fingerprint, mode="incremental")
            service.execute_plan(root, plan)
        except Exception as exc:
            reason = safe_failure_reason(exc, service="索引服务")
            logging.getLogger(__name__).error(
                "Incremental index update failed for workspace %s (%s)",
                workspace.workspace_id,
                reason,
            )
            record_diagnostic(
                Path(workspace.local_profile_dir),
                "index_update_failed",
                state="failed",
                reason=reason,
            )
            return mutation.model_copy(update={"index_update": "update_failed"})
        return mutation.model_copy(update={"index_update": "updated"})

    @app.exception_handler(WorkspaceError)
    async def workspace_error_handler(_request: Request, exc: WorkspaceError) -> JSONResponse:
        safe_messages = {
            "这条主线下仍有项目，请先移动项目，再删除空主线。",
            "这条主线目录仍有内容，请先移动内容，再删除空主线。",
            "这个项目仍有内容，无法删除；如需收起，请归档项目。",
            "Workspace contains duplicate page IDs",
            "Markdown page symlink is not allowed",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "workspace_error",
                    "message": exc.args[0]
                    if exc.args and exc.args[0] in safe_messages
                    else "工作库请求未能完成。",
                    "request_id": _request.state.request_id,
                }
            },
        )

    @app.exception_handler(WorkspaceWriteConflict)
    async def conflict_error_handler(request: Request, exc: WorkspaceWriteConflict) -> JSONResponse:
        message = (
            "页面已变化，请重新查看后确认。"
            if exc.args
            and exc.args[0]
            in {
                "Page changed since it was reviewed",
                "Draft changed since it was reviewed",
                "目标页面已变化，请检查当前版本后再继续审核。",
            }
            else "工作库内容已发生变化，请刷新后重试。"
        )
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "version_conflict",
                    "message": message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.exception_handler(LLMProviderError)
    async def provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        return error_envelope(
            request,
            status_code=502,
            code="provider_error",
            message=sanitize_provider_text(describe_failure("模型服务", exc))
            or "模型服务暂时不可用，请检查本地设置后重试。",
            extra={"provider": exc.details()} if exc.details() else None,
        )

    @app.exception_handler(ProviderError)
    async def typed_provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
        """Typed provider failures keep the provider's own explanation.

        Only the structured, sanitized fields are rendered: free-form exception
        text is never echoed, because it can carry credentials or local paths.
        """
        return error_envelope(
            request,
            status_code=502,
            code="provider_error",
            message=sanitize_provider_text(describe_failure("模型服务", exc))
            or "模型服务返回错误。",
            extra={"provider": exc.details()} if exc.details() else None,
        )

    @app.exception_handler(EmbeddingProviderError)
    async def embedding_provider_error_handler(
        request: Request, exc: EmbeddingProviderError
    ) -> JSONResponse:
        return error_envelope(
            request,
            status_code=502,
            code="provider_error",
            message=sanitize_provider_text(describe_failure("向量服务", exc))
            or "向量服务返回错误。",
            extra={"provider": exc.details()} if exc.details() else None,
        )

    @app.exception_handler(RerankProviderError)
    async def rerank_provider_error_handler(
        request: Request, exc: RerankProviderError
    ) -> JSONResponse:
        return error_envelope(
            request,
            status_code=502,
            code="provider_error",
            message=sanitize_provider_text(describe_failure("排序服务", exc))
            or "排序服务返回错误。",
            extra={"provider": exc.details()} if exc.details() else None,
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
            "source_sha": build_identity["source_sha"],
            "dirty": build_identity["dirty"],
            "build_id": build_identity["build_id"],
            "app_version": build_identity["app_version"],
            "frontend_sha256": build_identity["frontend_sha256"],
            "dependencies_sha256": build_identity["dependencies_sha256"],
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

    @app.get("/api/v1/agent/workspace", dependencies=[Depends(authenticated)])
    def agent_workspace_info(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> WorkspaceContext:
        return workspace

    @app.get("/api/v1/agent/workspace/bound", dependencies=[Depends(authenticated)])
    def agent_workspace_bound(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> WorkspaceContext:
        return workspace

    @app.get("/api/v1/agent/lines", dependencies=[Depends(authenticated)])
    def agent_lines(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> list[LineRecord]:
        return list_lines(Path(workspace.root))

    @app.get("/api/v1/agent/projects", dependencies=[Depends(authenticated)])
    def agent_projects(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> list[ProjectRecord]:
        return list_projects(Path(workspace.root))

    @app.get("/api/v1/agent/index", dependencies=[Depends(authenticated)])
    def agent_index_status(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> dict[str, int | str | None]:
        return query_for(workspace).status(Path(workspace.root))

    @app.get("/api/v1/agent/pages", dependencies=[Depends(authenticated)])
    def agent_pages(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> list[dict[str, Any]]:
        result = []
        for page in list_pages(Path(workspace.root)):
            if page.storage_area != "formal" or page.approval_state != "confirmed":
                continue
            eligible = retrieval_eligibility(
                page.metadata,
                page.body,
                area=StorageArea.FORMAL,
                purpose=RetrievalPurpose.CURRENT,
                expected_content_sha256=page.content_sha256,
            )
            if eligible.eligible:
                result.append(
                    {
                        "page_id": page.page_id,
                        "title": page.metadata.get("title", ""),
                        "content_sha256": page.content_sha256,
                    }
                )
        return result

    @app.get("/api/v1/agent/search", dependencies=[Depends(authenticated)])
    def agent_search(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
        q: str = Query(min_length=1, max_length=1000),
        limit: int = Query(default=10, ge=1, le=30),
    ) -> list[dict[str, Any]]:
        store = IndexStore(Path(workspace.local_profile_dir) / "index.sqlite3")
        generation, rows = store.search_bm25(workspace.workspace_id, q, limit=min(120, limit * 4))
        if generation is None:
            legacy = store.has_legacy_index(workspace.workspace_id)
            raise HTTPException(
                409,
                detail={
                    "code": "index_rebuild_required" if legacy else "index_not_ready",
                    "message": "旧索引需要显式重建后才能搜索。" if legacy else "本机索引尚未建立。",
                },
            )
        hits: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            page_id = UUID(str(row["page_id"]))
            expected_sha = str(row["content_sha256"])
            key = (str(page_id), expected_sha)
            if key in seen:
                continue
            seen.add(key)
            try:
                page = read_page(Path(workspace.root), page_id)
            except WorkspaceError:
                continue
            eligible = retrieval_eligibility(
                page.metadata,
                page.body,
                area=StorageArea(page.storage_area),
                purpose=RetrievalPurpose.CURRENT,
                expected_content_sha256=expected_sha,
            )
            if not eligible.eligible:
                continue
            hits.append(
                {
                    "page_id": page_id,
                    "content_sha256": expected_sha,
                    "title": page.metadata.get("title", ""),
                    "heading": str(row["heading"]),
                    "excerpt": str(row["text"]),
                    "bm25_score": float(row["bm25_score"]),
                }
            )
            if len(hits) >= limit:
                break
        return hits

    @app.get("/api/v1/agent/pages/{page_id}", dependencies=[Depends(authenticated)])
    def agent_page_get(
        page_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
        expected_content_sha256: str,
    ) -> dict[str, Any]:
        page = read_page(Path(workspace.root), page_id)
        if page.content_sha256 != expected_content_sha256:
            raise HTTPException(
                409, detail={"code": "stale_page", "message": "页面内容已更新，请重新读取。"}
            )
        eligible = retrieval_eligibility(
            page.metadata,
            page.body,
            area=StorageArea.FORMAL,
            purpose=RetrievalPurpose.CURRENT,
            expected_content_sha256=expected_content_sha256,
        )
        if not eligible.eligible:
            raise HTTPException(
                404, detail={"code": "not_retrievable", "message": "页面未确认或已失效。"}
            )
        return {
            "page_id": page.page_id,
            "title": page.metadata.get("title", ""),
            "content_sha256": page.content_sha256,
            "body": page.body,
        }

    @app.get("/api/v1/agent/intake", dependencies=[Depends(authenticated)])
    def agent_intake_list(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> list[IntakeItem]:
        return intake_service.list_items(Path(workspace.root))

    @app.get("/api/v1/agent/sources/{source_id}", dependencies=[Depends(authenticated)])
    def agent_source_get(
        source_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> dict[str, Any]:
        detail = intake_service.get_source(Path(workspace.root), source_id)
        return {
            "source": detail.source,
            "text": detail.text,
            "trust_state": "unconfirmed_source_not_knowledge",
        }

    @app.get("/api/v1/agent/drafts", dependencies=[Depends(authenticated)])
    def agent_draft_list(
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> list[Draft]:
        return review.list_drafts(Path(workspace.root), pending_only=True)

    @app.get("/api/v1/agent/drafts/{draft_id}", dependencies=[Depends(authenticated)])
    def agent_draft_get(
        draft_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> Draft:
        return review.get_draft(Path(workspace.root), draft_id)

    @app.patch("/api/v1/agent/drafts/{draft_id}", dependencies=[Depends(authenticated)])
    def agent_draft_edit(
        draft_id: UUID,
        payload: DraftPatchRequest,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
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

    @app.post("/api/v1/agent/import", status_code=201, dependencies=[Depends(authenticated)])
    def agent_import(
        payload: AgentImportRequest,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> IntakeItem:
        return intake_service.add_text(
            Path(workspace.root),
            payload.text,
            filename=payload.filename,
            operation_id=payload.operation_id,
            origin_kind="quick_note",
        )

    @app.post("/api/v1/agent/drafts", status_code=201, dependencies=[Depends(authenticated)])
    def agent_draft_create(
        payload: AgentDraftCreateRequest,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
    ) -> Draft:
        try:
            return review.create_agent_draft(
                Path(workspace.root),
                operation_id=payload.operation_id,
                item_ids=payload.item_ids,
                line_id=payload.line_id,
                project_id=payload.project_id,
                title=payload.title,
                kind=payload.kind,
                body=payload.body,
                target_page_id=payload.target_page_id,
                expected_base_sha256=payload.expected_base_sha256,
                workspace_id=workspace.workspace_id,
            )
        except WorkspaceError as exc:
            raise HTTPException(
                409, detail={"code": "draft_conflict", "message": str(exc)}
            ) from None

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

    @app.get(
        "/api/v1/pages/directory",
        dependencies=[Depends(authenticated)],
        response_model_exclude_none=True,
    )
    def page_directory(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[PageDirectoryEntry]:
        return [
            PageDirectoryEntry(
                page_id=page.page_id,
                relative_path=page.relative_path,
                metadata=page.metadata,
                content_sha256=page.content_sha256,
                storage_area=page.storage_area,
                approval_state=page.approval_state,
                validity=page.validity,
                # Project rows need the overview's short next-step summary. Other
                # page bodies remain strictly on-demand.
                body=page.body if page.metadata.get("kind") == "project_overview" else None,
            )
            for page in list_pages(Path(workspace.root))
        ]

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
        if settings_store(workspace).read().mode == "real":
            ensure_remote_calls_allowed(workspace, ("llm",))
            if payload.acceptance_plan_id is None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "acceptance_plan_required",
                        "message": "发送日志正文前请预览并确认本次 AI 辅助范围。",
                    },
                )
            try:
                scope = normalize_journal_assist_scope(workspace, {"text": payload.text})
                scope_sha = json_binding({"operation": "model.journal_assist", "scope": scope})
                ledger = acceptance_ledger(workspace)
                approved = ledger.get(payload.acceptance_plan_id)
                if approved.operation != "model.journal_assist":
                    raise PlanConflict("acceptance plan operation does not match")
                ledger.begin_execution(
                    payload.acceptance_plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                    config_sha256=settings_binding(workspace),
                    scope_sha256=scope_sha,
                    run_id=app.state.acceptance_run_id,
                )
            except PlanConflict as exc:
                raise HTTPException(
                    409,
                    detail={
                        "code": "acceptance_plan_conflict",
                        "message": plan_conflict_message(exc),
                    },
                ) from None

            reserved = False
            provider_review: IntakeReviewService | None = None
            try:
                # Use the configured runtime directly. Test-only injected review services
                # cannot turn a real-mode action into a Fake or bypass its credential gate.
                provider_review = IntakeReviewService(runtime_for(workspace).llm())
                if provider_review.provider is None:
                    raise LLMProviderError("provider_not_configured")
                current_scope = normalize_journal_assist_scope(workspace, {"text": payload.text})
                if (
                    settings_binding(workspace) != approved.config_sha256
                    or json_binding({"operation": "model.journal_assist", "scope": current_scope})
                    != approved.scope_sha256
                ):
                    raise PlanConflict("journal text or provider settings changed")
                ledger.reserve_request(
                    payload.acceptance_plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                )
                reserved = True
                proposals = provider_review.provider.organize([(uuid4(), uuid4(), payload.text)])
                if not proposals:
                    raise LLMProviderError("provider returned no journal-assist proposal")
                ledger.finish(payload.acceptance_plan_id, state="succeeded")
                return JournalAssistResponse(title=proposals[0].title, body=proposals[0].body)
            except PlanConflict as exc:
                if ledger.get(payload.acceptance_plan_id).state == "executing":
                    ledger.finish(
                        payload.acceptance_plan_id, state="unknown" if reserved else "failed"
                    )
                raise HTTPException(
                    409,
                    detail={
                        "code": "acceptance_plan_conflict",
                        "message": plan_conflict_message(exc),
                    },
                ) from None
            except (ProviderError, LLMProviderError) as exc:
                if ledger.get(payload.acceptance_plan_id).state == "executing":
                    ledger.finish(
                        payload.acceptance_plan_id, state="unknown" if reserved else "failed"
                    )
                record_assistant_failure(workspace, exc)
                raise assistant_failure(exc, suffix="记录仍留在编辑区，未保存。") from exc
            except Exception as exc:
                if ledger.get(payload.acceptance_plan_id).state == "executing":
                    ledger.finish(
                        payload.acceptance_plan_id, state="unknown" if reserved else "failed"
                    )
                record_assistant_failure(workspace, exc)
                raise assistant_failure(exc, suffix="记录仍留在编辑区，未保存。") from exc
            finally:
                try:
                    if provider_review is not None:
                        persist_provider_usage(
                            workspace,
                            payload.acceptance_plan_id,
                            (provider_review.provider,),
                        )
                finally:
                    if provider_review is not None:
                        close_provider = getattr(provider_review.provider, "close", None)
                        if callable(close_provider):
                            close_provider()
        try:
            provider = review_for(workspace).provider
            if provider is None:
                raise LLMProviderError("provider_not_configured")
            proposals = provider.organize([(uuid4(), uuid4(), payload.text)])
        except Exception as exc:
            # Every failure answers with a safe sentence and leaves a searchable
            # local cause; a typed provider failure also names the reason.
            record_assistant_failure(workspace, exc)
            raise assistant_failure(exc, suffix="已保存内容未更改。") from exc
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
        item = intake_service.add_text(
            Path(workspace.root),
            payload.text,
            filename=payload.filename,
            operation_id=payload.operation_id,
            origin_kind="quick_note",
        )
        profile_event(
            Path(workspace.local_profile_dir),
            "intake_saved",
            record_id=str(item.item_id),
            state=item.state,
        )
        return item

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
        item = intake_service.add_file(
            Path(workspace.root),
            raw,
            filename=file.filename or "source.txt",
            operation_id=operation_id,
            origin_kind="file",
        )
        profile_event(
            Path(workspace.local_profile_dir),
            "intake_saved",
            record_id=str(item.item_id),
            state=item.state,
        )
        return item

    @app.get("/api/v1/intake/items", dependencies=[Depends(authenticated)])
    def intake_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> list[IntakeItem]:
        root = Path(workspace.root)
        items = intake_service.list_items(root)
        # Listing and crash-recovery replay are local reads only. Do not create
        # a real provider just to inspect an existing job checkpoint.
        active_review = review
        for item in items:
            if item.latest_job_id is not None and item.state in {"processing", "unknown"}:
                # This only checks the local lease and replays a durable local
                # checkpoint; it never retries the external model call.
                active_review.get_job(root, item.latest_job_id)
        return intake_service.list_items(root)

    @app.get("/api/v1/sources/{source_id}", dependencies=[Depends(authenticated)])
    def source_get(
        source_id: UUID,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> SourceDetail:
        return intake_service.get_source(Path(workspace.root), source_id)

    @app.post(
        "/api/v1/intake/jobs",
        status_code=201,
        responses={
            202: {"model": IntakeJob, "description": "Existing provider attempt is still running"}
        },
        dependencies=[Depends(authenticated)],
    )
    def intake_job_create(
        payload: IntakeJobRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        response: Response,
    ) -> IntakeJob:
        replay = review.replay_job(
            Path(workspace.root),
            item_ids=payload.item_ids,
            operation_id=payload.operation_id,
            line_id=payload.line_id,
            project_id=payload.project_id,
            reprocess=payload.reprocess,
        )
        if replay is not None:
            job = replay
        elif settings_store(workspace).read().mode == "real" and review_service is None:
            ensure_remote_calls_allowed(workspace, ("llm",))
            if payload.acceptance_plan_id is None:
                raise HTTPException(
                    409,
                    detail={
                        "code": "acceptance_plan_required",
                        "message": "真实整理前请预览并确认所选材料。",
                    },
                )
            organize_plan_id = payload.acceptance_plan_id
            intent = {
                "item_ids": [str(item_id) for item_id in payload.item_ids],
                "operation_id": payload.operation_id,
                "line_id": str(payload.line_id),
                "project_id": str(payload.project_id),
                "reprocess": payload.reprocess,
            }
            current_scope = normalize_organize_scope(workspace, intent)
            scope_sha = json_binding({"operation": "model.organize", "scope": current_scope})
            ledger = acceptance_ledger(workspace)
            try:
                approved = ledger.get(payload.acceptance_plan_id)
                if approved.operation != "model.organize":
                    raise PlanConflict("acceptance plan operation does not match")
                ledger.begin_execution(
                    payload.acceptance_plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                    config_sha256=settings_binding(workspace),
                    scope_sha256=scope_sha,
                    run_id=app.state.acceptance_run_id,
                )
            except PlanConflict as exc:
                raise HTTPException(
                    409,
                    detail={
                        "code": "acceptance_plan_conflict",
                        "message": plan_conflict_message(exc),
                    },
                ) from None
            reserved = False

            def guard_organize_call(actual_inputs: list[tuple[UUID, UUID, str]]) -> None:
                nonlocal reserved
                actual_scope = {
                    **intent,
                    "max_output_tokens": settings_store(workspace).read().llm.max_output_tokens,
                    "outgoing_inputs": [
                        {"item_id": str(item_id), "source_id": str(source_id), "text": text}
                        for item_id, source_id, text in actual_inputs
                    ],
                }
                if (
                    settings_binding(workspace) != approved.config_sha256
                    or json_binding({"operation": "model.organize", "scope": actual_scope})
                    != approved.scope_sha256
                ):
                    raise PlanConflict("approved source or provider settings changed")
                ledger.reserve_request(
                    organize_plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                )
                reserved = True

            operation_review: IntakeReviewService | None = None
            try:
                operation_review = review_for(workspace)
                job = operation_review.create_job(
                    Path(workspace.root),
                    payload.item_ids,
                    operation_id=payload.operation_id,
                    line_id=payload.line_id,
                    project_id=payload.project_id,
                    reprocess=payload.reprocess,
                    before_provider_call=guard_organize_call,
                )
                finish_feishu_plan(workspace, payload.acceptance_plan_id, "succeeded")
            except Exception:
                finish_feishu_plan(
                    workspace, payload.acceptance_plan_id, "unknown" if reserved else "failed"
                )
                raise
            finally:
                try:
                    if operation_review is not None:
                        persist_provider_usage(
                            workspace,
                            organize_plan_id,
                            (operation_review.provider,),
                        )
                finally:
                    close_provider = (
                        getattr(operation_review.provider, "close", None)
                        if operation_review is not None
                        else None
                    )
                    if callable(close_provider):
                        close_provider()
        elif settings_store(workspace).read().mode == "real" and review_service is not None:
            # Injected providers are an offline test seam, never a user-facing bypass.
            raise HTTPException(
                409,
                detail={
                    "code": "acceptance_plan_required",
                    "message": "真实整理必须使用服务端授权计划。",
                },
            )
        else:
            job = review.create_job(
                Path(workspace.root),
                payload.item_ids,
                operation_id=payload.operation_id,
                line_id=payload.line_id,
                project_id=payload.project_id,
                reprocess=payload.reprocess,
            )
        if job.state in {"running", "provider_calling"}:
            response.status_code = 202
            response.headers["Location"] = f"/api/v1/jobs/{job.job_id}"
        profile_event(
            Path(workspace.local_profile_dir),
            "intake_job",
            record_id=str(job.job_id),
            state=job.state,
            count=len(job.draft_ids),
        )
        return job

    @app.get("/api/v1/jobs/{job_id}", dependencies=[Depends(authenticated)])
    def intake_job_get(
        job_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> IntakeJob:
        job = review.get_job(Path(workspace.root), job_id)
        profile_event(
            Path(workspace.local_profile_dir),
            "intake_job",
            record_id=str(job.job_id),
            state=job.state,
        )
        return job

    @app.delete("/api/v1/jobs/{job_id}", dependencies=[Depends(authenticated)])
    def intake_job_cancel(
        job_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> IntakeJob:
        job = review.cancel_job(Path(workspace.root), job_id)
        profile_event(
            Path(workspace.local_profile_dir),
            "intake_job",
            record_id=str(job.job_id),
            state=job.state,
        )
        return job

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
        result = index_after_approval(
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
        profile_event(
            Path(workspace.local_profile_dir),
            "draft_confirmed",
            record_id=str(draft_id),
            state=result.state,
        )
        return result

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
        require_local_retrieval_ready(workspace)
        if query_service is None and not fingerprint_is_current(workspace, payload.fingerprint):
            raise HTTPException(status_code=409, detail="Provider 设置已变化，请重新生成索引计划。")
        return query_for(
            workspace,
            local_costs=settings_store(workspace).read().embedding.provider == "local",
        ).plan(Path(workspace.root), fingerprint=payload.fingerprint, mode=payload.mode)

    @app.post("/api/v1/index/jobs", dependencies=[Depends(authenticated)])
    def index_execute(
        payload: IndexPlan,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> IndexResult:
        require_local_retrieval_ready(workspace)
        ensure_remote_calls_allowed(workspace, ("embedding",))
        if query_service is None and not fingerprint_is_current(workspace, payload.fingerprint):
            raise HTTPException(status_code=409, detail="Provider 设置已变化，请重新生成索引计划。")
        plan_id: UUID | None = None
        expected_config_sha256 = settings_binding(workspace)
        expected_scope: dict[str, Any] | None = None
        if (
            query_service is None
            and settings_store(workspace).read().mode == "real"
            and settings_store(workspace).read().embedding.provider == "dashscope"
        ):
            if payload.acceptance_plan_id is None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "acceptance_plan_required",
                        "message": "真实索引需先预览并确认本次页面与版本。",
                    },
                )
            scope = normalize_index_scope(
                workspace,
                {
                    "mode": payload.mode,
                    "fingerprint": payload.fingerprint,
                    "page_ids": [str(item) for item in payload.page_ids],
                    "page_versions": payload.page_versions,
                },
            )
            expected_scope = scope
            request_count = index_embedding_call_bound(workspace, scope)
            scope_sha256 = json_binding({"operation": "model.index", "scope": scope})
            ledger = acceptance_ledger(workspace)
            try:
                prior = ledger.get(payload.acceptance_plan_id)
                if prior.operation != "model.index":
                    raise PlanConflict("acceptance plan operation does not match")
                plan_id = payload.acceptance_plan_id
                ledger.begin_execution(
                    plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                    config_sha256=settings_binding(workspace),
                    scope_sha256=scope_sha256,
                    run_id=app.state.acceptance_run_id,
                )
                ledger.reserve_requests(
                    plan_id,
                    workspace_id=str(workspace.workspace_id),
                    profile_id=profile_binding(workspace),
                    count=request_count,
                )
            except PlanConflict as exc:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "acceptance_plan_conflict",
                        "message": plan_conflict_message(exc),
                    },
                ) from None

        def index_provider_guard() -> None:
            if settings_binding(workspace) != expected_config_sha256:
                raise IndexPlanStale("Provider settings changed after confirmation")
            if expected_scope is not None:
                payload_scope = {
                    "mode": payload.mode,
                    "fingerprint": payload.fingerprint,
                    "page_ids": [str(item) for item in payload.page_ids],
                    "page_versions": payload.page_versions,
                }
                if normalize_index_scope(workspace, payload_scope) != expected_scope:
                    raise IndexPlanStale("Workspace pages changed after confirmation")

        service: QueryService | None = None
        try:
            service = query_for(
                workspace,
                remote=True,
                provider_guard=index_provider_guard if plan_id else None,
                required_providers=("embedding",),
            )
            result = service.execute_plan(Path(workspace.root), payload)
            if plan_id is not None:
                finish_feishu_plan(workspace, plan_id, "succeeded")
            return result
        except Exception:
            if plan_id is not None:
                finish_feishu_plan(workspace, plan_id, "unknown")
            raise
        finally:
            if query_service is None and service is not None:
                try:
                    if plan_id is not None:
                        persist_provider_usage(workspace, plan_id, (service.embedding,))
                finally:
                    service.close()

    @app.get("/api/v1/index/status", dependencies=[Depends(authenticated)])
    def index_status(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> dict[str, int | str | None]:
        status = query_for(workspace).status(Path(workspace.root))
        fingerprint = status.get("fingerprint")
        settings = settings_store(workspace).read()
        if (
            query_service is None
            and fingerprint is not None
            and fingerprint != embedding_fingerprint(settings.embedding, mode=settings.mode)
        ):
            # The generation may still be internally consistent with its old
            # page hashes, but it cannot serve a query for the selected model.
            status["state"] = "stale"
            status["stale_pages"] = status.get("current_pages", 0)
            status["reason"] = "embedding_model_changed"
        # 完整指纹是内部标识，不进界面；概览只需要「仿真 / 真实」这一层。
        status["vector"] = (
            "unknown"
            if fingerprint is None
            else "simulated"
            if str(fingerprint).startswith("summit-fake")
            else "real"
        )
        return status

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
        # 每检查一条引用都重扫整棵页面目录会随引用数线性变慢；
        # 一段会话只扫一次，之后按 page_id 查表。
        page_index: dict[Any, Any] | None = None
        messages = []
        for message in detail.messages:
            citations = []
            for citation in message.citations:
                if page_index is None:
                    page_index = {page.page_id: page for page in list_pages(Path(workspace.root))}
                page = page_index.get(citation.page_id)
                availability = (
                    "unavailable"
                    if page is None
                    else citation_availability_of_page(page, citation, message.purpose)
                )
                citations.append(citation.model_copy(update={"availability": availability}))
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
        if _is_attributed_source_text(source, text):
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
        request_id = str(payload.request_id or uuid4())
        stable_request_id = UUID(request_id)
        store = conversations_for(workspace)
        replay_existing = store.has_request(workspace.workspace_id, stable_request_id)
        context = AnswerContext(answer_mode=payload.answer_mode)
        context_version = "replay-existing-request"
        query_plan_id: UUID | None = None
        query_scope: dict[str, Any] | None = None
        query_scope_sha256: str | None = None
        query_config_sha256: str | None = None
        if not replay_existing:
            query_scope = normalize_query_scope(
                workspace,
                {
                    "question": payload.question,
                    "fingerprint": payload.fingerprint,
                    "purpose": payload.purpose,
                    "answer_mode": payload.answer_mode,
                    "role_id": str(payload.role_id) if payload.role_id else None,
                    "request_id": request_id,
                    "conversation_id": str(payload.conversation_id)
                    if payload.conversation_id
                    else None,
                },
            )
            context = AnswerContext.model_validate(query_scope["context"])
            ensure_remote_calls_allowed(workspace, ("llm",))
            if settings_store(workspace).read().mode == "real":
                require_local_retrieval_ready(workspace)
                require_query_index_ready(workspace, str(query_scope["fingerprint"]))
            context_version = hashlib.sha256(
                json.dumps(
                    context.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            if query_service is None and settings_store(workspace).read().mode == "real":
                if payload.acceptance_plan_id is None:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "acceptance_plan_required",
                            "message": "真实问答需先预览并确认发送范围。",
                        },
                    )
                scope_sha256 = json_binding({"operation": "model.query", "scope": query_scope})
                query_scope_sha256 = scope_sha256
                query_config_sha256 = settings_binding(workspace)
                ledger = acceptance_ledger(workspace)
                try:
                    prior = ledger.get(payload.acceptance_plan_id)
                    if prior.operation != "model.query":
                        raise PlanConflict("acceptance plan operation does not match")
                    ledger.begin_execution(
                        payload.acceptance_plan_id,
                        workspace_id=str(workspace.workspace_id),
                        profile_id=profile_binding(workspace),
                        config_sha256=settings_binding(workspace),
                        scope_sha256=scope_sha256,
                        run_id=app.state.acceptance_run_id,
                    )
                    ledger.reserve_requests(
                        payload.acceptance_plan_id,
                        workspace_id=str(workspace.workspace_id),
                        profile_id=profile_binding(workspace),
                        count=prior.request_limit,
                    )
                    query_plan_id = payload.acceptance_plan_id
                except PlanConflict as exc:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "acceptance_plan_conflict",
                            "message": plan_conflict_message(exc),
                        },
                    ) from None
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

        def query_provider_guard() -> None:
            if (
                query_config_sha256 is not None
                and settings_binding(workspace) != query_config_sha256
            ):
                raise ValueError("Provider configuration changed after confirmation")
            if query_scope_sha256 is not None:
                current_scope = normalize_query_scope(
                    workspace,
                    {
                        "question": payload.question,
                        "fingerprint": payload.fingerprint,
                        "purpose": payload.purpose,
                        "answer_mode": payload.answer_mode,
                        "role_id": str(payload.role_id) if payload.role_id else None,
                        "request_id": request_id,
                        "conversation_id": str(payload.conversation_id)
                        if payload.conversation_id
                        else None,
                    },
                )
                if (
                    json_binding({"operation": "model.query", "scope": current_scope})
                    != query_scope_sha256
                ):
                    raise ValueError(
                        "Question context or source versions changed after confirmation"
                    )

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
            query_plan_state = "unknown"
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
                operation = (
                    query_for(
                        workspace,
                        remote=True,
                        provider_guard=query_provider_guard if query_plan_id else None,
                    )
                    if query_service is None
                    else None
                )
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
                query_plan_state = "succeeded"
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
                # The WebUI shows the SSE message verbatim, so it keeps the safe
                # sentence for untyped exceptions. The query record is a different
                # surface: it must stay diagnosable, because in a packaged app
                # Python logging has no handler and its stderr is discarded, which
                # leaves this record as the only survival surface. It therefore
                # always carries the sanitized, single-line, bounded cause.
                reason = query_failure_message(exc)
                # The local record is the surface that survives packaging, so it
                # keeps the sanitized <type>: <message>; the client response and
                # the service log stay on the controlled text only.
                diagnostic = sanitize_provider_text(f"{type(exc).__name__}: {exc}") or reason
                _LOGGER.warning(
                    "query failed request_id=%s error=%s cause=%s logged=%s",
                    stable_request_id,
                    type(exc).__name__,
                    reason,
                    safe_failure_reason(exc, service="模型服务"),
                )
                terminal = store.terminate(
                    workspace.workspace_id,
                    stable_request_id,
                    "error",
                    {"code": "query_error", "message": reason, "detail": reason},
                    "error",
                    error=diagnostic,
                )
                if terminal is not None:
                    yield event(terminal.seq, terminal.type, terminal.data)
            finally:
                if query_plan_id is not None:
                    finish_feishu_plan(workspace, query_plan_id, query_plan_state)
                cancellations.pop(cancel_key, None)
                cancellation_requests.discard(cancel_key)
                ACTIVE_QUERIES.discard(active_query_key)

                def settle_query(task: asyncio.Task[Any]) -> None:
                    try:
                        task.exception()
                    except asyncio.CancelledError:
                        pass
                    if operation is not None:
                        try:
                            if query_plan_id is not None:
                                persist_provider_usage(
                                    workspace,
                                    query_plan_id,
                                    (
                                        operation.embedding,
                                        operation.reranker,
                                        operation.answer_provider,
                                    ),
                                )
                        finally:
                            operation.close()

                if query_task is None:
                    if operation is not None:
                        operation.close()
                elif query_task.done():
                    settle_query(query_task)
                else:
                    query_task.add_done_callback(settle_query)

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
        if service is None:
            raise HTTPException(
                409,
                detail={
                    "code": "provider_not_configured",
                    "message": "请先打开工作库并完成飞书配置。",
                },
            )
        return service.callback(state, code, error, callback_boundary(str(request.url)))

    @app.get(prefix + "/materials", dependencies=[Depends(authenticated)])
    def feishu_materials(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        query: str = "",
        visibility: Literal["owner", "shared"] | None = None,
        cursor: str | None = None,
        limit: int = 20,
        plan_id: UUID | None = None,
    ) -> MaterialPage:
        if not 1 <= limit <= 30 or len(query) > 500 or (cursor and len(cursor) > 500):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "材料筛选无效。"}
            )
        scope = normalize_feishu_scope(
            "feishu.materials.read",
            {"query": query, "visibility": visibility, "cursor": cursor, "limit": limit},
        )
        plan = require_feishu_data(workspace, "feishu.materials.read", scope, plan_id, 2)
        try:
            result = feishu_for(workspace).materials(query, visibility, cursor, limit)
        except Exception:
            finish_feishu_plan(workspace, plan, "unknown")
            raise
        finish_feishu_plan(workspace, plan, "succeeded")
        return result

    @app.post(prefix + "/imports", dependencies=[Depends(authenticated)])
    def feishu_imports(
        payload: ImportRequest,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        plan_id: UUID | None = None,
    ) -> ImportResult:
        scope = normalize_feishu_scope(
            "feishu.materials.import",
            {"material_ids": payload.material_ids, "operation_id": payload.operation_id},
        )
        plan = require_feishu_data(
            workspace, "feishu.materials.import", scope, plan_id, 3 * len(payload.material_ids) + 2
        )
        try:
            result = feishu_for(workspace).imports(Path(workspace.root), payload)
        except ValueError as exc:
            finish_feishu_plan(workspace, plan, "failed")
            if isinstance(exc, IntakeConflict):
                raise
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "材料选择无效。"}
            ) from None
        except Exception:
            finish_feishu_plan(workspace, plan, "unknown")
            raise
        finish_feishu_plan(workspace, plan, "succeeded")
        return result

    @app.get(prefix + "/calendar", dependencies=[Depends(authenticated)])
    def feishu_calendar(
        start: datetime,
        end: datetime,
        timezone: str,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = 20,
    ) -> CalendarPage:
        require_calendar_provider_config(workspace)
        if not 1 <= limit <= 30 or (cursor and len(cursor) > 500):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "日历分页无效。"}
            )
        normalize_feishu_scope(
            "feishu.calendar.read",
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "timezone": timezone,
                "cursor": cursor,
                "limit": limit,
            },
        )
        try:
            return feishu_for(workspace).calendar(start, end, timezone, cursor, limit)
        except ValueError:
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "请选择有效的起止时间和时区。"}
            ) from None

    @app.get("/api/v1/agent/calendar", dependencies=[Depends(authenticated)])
    def agent_calendar(
        start: datetime,
        end: datetime,
        timezone: str,
        workspace: Annotated[WorkspaceContext, Depends(agent_workspace)],
        cursor: str | None = None,
        limit: int = 20,
    ) -> CalendarPage:
        require_calendar_provider_config(workspace)
        if not 1 <= limit <= 30 or (cursor and len(cursor) > 500):
            raise HTTPException(
                422, detail={"code": "validation_error", "message": "日历分页无效。"}
            )
        normalize_feishu_scope(
            "feishu.calendar.read",
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "timezone": timezone,
                "cursor": cursor,
                "limit": limit,
            },
        )
        try:
            return feishu_for(workspace).calendar(start, end, timezone, cursor, limit)
        except ValueError:
            raise HTTPException(
                422,
                detail={"code": "validation_error", "message": "请选择有效的起止时间和时区。"},
            ) from None

    if web_dist is not None:
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="webui")
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
