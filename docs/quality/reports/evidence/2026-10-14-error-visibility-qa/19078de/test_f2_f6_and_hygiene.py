"""F2–F6 and hygiene checks for fixed SHA 19078de.

QA-only harness. All provider interactions use httpx MockTransport with synthetic
credentials; no network, no real key, no real keychain.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from summit_everything.integrations.embedding import EmbeddingProviderError, FakeEmbedding
from summit_everything.integrations.http_boundary import (
    ProviderError,
    bounded_json_post,
    sanitize_provider_text,
)
from summit_everything.integrations.llm import (
    DeepSeekLLM,
    GroundedAnswer,
    LLMProviderError,
)
from summit_everything.integrations.rerank import RerankProviderError
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.intake.review import IntakeReviewService
from summit_everything.local.event_log import profile_event
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

import summit_everything.integrations.embedding as embedding_module
import summit_everything.integrations.llm as llm_module
import summit_everything.integrations.rerank as rerank_module
from qa_common import (
    HEADERS,
    KEY,
    PLAIN_SENTINEL,
    SENTINEL,
    app_client,
    configure_real,
    diagnostics_events,
    diagnostics_text,
    SyntheticKeychain,
    mock_client,
    open_workspace,
    seed_page,
    store_credential,
)

PROVIDER_BODY = {
    "error": {"code": "invalid_api_key", "message": "Invalid API-key provided."},
    "request_id": "body-request-7",
}


# ==========================================================================
# F2 — /api/v1/journal/assist keeps the reason, and records it locally
# ==========================================================================


class FailingProvider:
    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0

    def organize(self, inputs: object) -> list[object]:  # noqa: ANN001
        self.calls += 1
        raise self.error


def assist_client(tmp_path: Path, error: BaseException) -> TestClient:
    return app_client(tmp_path, review_service=IntakeReviewService(FailingProvider(error)))


def test_f2_typed_assist_failure_shows_the_reason_and_records_it(tmp_path: Path) -> None:
    typed = LLMProviderError(
        "模型服务返回错误：InsufficientBalance — Insufficient Balance",
        provider_code="InsufficientBalance",
        provider_message="Insufficient Balance",
        request_id="request-5",
        reason="provider",
    )
    client = assist_client(tmp_path, typed)
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "assistant_unavailable", error
    assert "InsufficientBalance" in error["message"], error
    assert "request-5" in error["message"], error
    assert "已保存内容未更改。" in error["message"]

    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "assistant_failed", events
    assert events[-1]["state"] == "failed"
    assert "InsufficientBalance" in str(events[-1]["reason"])


@pytest.mark.parametrize(
    "error",
    [
        LLMProviderError("模型服务连接失败", reason="transport"),
        LLMProviderError("模型服务请求超时", reason="deadline"),
        EmbeddingProviderError("向量服务返回了无法解析的响应", reason="schema"),
        ProviderError("provider returned an unsuccessful response (HTTP 429)", reason="provider"),
    ],
    ids=["llm-transport", "llm-deadline", "embedding-schema", "bare-provider"],
)
def test_f2_every_typed_provider_failure_keeps_a_coded_reason(
    tmp_path: Path, error: BaseException
) -> None:
    client = assist_client(tmp_path, error)
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    body = response.json()["error"]
    assert body["code"] == "assistant_unavailable"
    assert body["message"].strip() != ""
    assert "AI 辅助暂时不可用" not in body["message"], body
    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "assistant_failed"


def test_f2_unknown_assist_failure_stays_safe_but_records_the_type(tmp_path: Path) -> None:
    client = assist_client(tmp_path, RuntimeError(f"{PLAIN_SENTINEL} /private/qa/profile"))
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "assistant_unavailable"
    assert "AI 辅助暂时不可用" in error["message"]
    assert PLAIN_SENTINEL not in response.text
    assert "/private/qa/profile" not in response.text

    text = diagnostics_text(tmp_path / "profile")
    assert PLAIN_SENTINEL not in text
    assert "/private/qa/profile" not in text
    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "assistant_failed"
    assert events[-1]["reason"] == "RuntimeError"


# ==========================================================================
# F3 — provider-smoke failures carry error.provider{code,message,request_id}
# ==========================================================================


def _patch_clients(monkeypatch: pytest.MonkeyPatch, handler) -> list[httpx.Request]:  # noqa: ANN001
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    for module in (embedding_module, rerank_module, llm_module):
        monkeypatch.setattr(
            module, "create_http_client", lambda h=wrapped: mock_client(h), raising=True
        )
    return seen


def _smoke_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, handler) -> TestClient:  # noqa: ANN001
    _patch_clients(monkeypatch, handler)
    client = app_client(tmp_path, secret_backend=SyntheticKeychain())
    open_workspace(client, tmp_path / "workspace")
    configure_real(client)
    store_credential(client, "dashscope")
    return client


def test_f3_embedding_smoke_failure_carries_structured_provider_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _smoke_client(
        tmp_path,
        monkeypatch,
        lambda _r: httpx.Response(400, json=PROVIDER_BODY, headers={"x-request-id": "hdr-1"}),
    )
    response = client.post("/api/v1/provider-smoke/model-studio-embedding", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_smoke_failed", error
    assert error["provider"] == {
        "code": "invalid_api_key",
        "message": "Invalid API-key provided.",
        "request_id": "body-request-7",
    }, error
    assert KEY not in response.text


def test_f3_rerank_smoke_failure_carries_structured_provider_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rerank smoke response lacked a structured provider object before."""
    client = _smoke_client(
        tmp_path,
        monkeypatch,
        lambda _r: httpx.Response(403, json=PROVIDER_BODY, headers={"x-request-id": "hdr-1"}),
    )
    response = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_smoke_failed", error
    assert error["provider"] == {
        "code": "invalid_api_key",
        "message": "Invalid API-key provided.",
        "request_id": "body-request-7",
    }, error


def test_f3_header_only_request_id_is_still_reported_for_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = lambda _r: httpx.Response(  # noqa: E731
        500, json={"error": {"code": "internal_error", "message": "boom"}}, headers={"x-request-id": "hdr-9"}
    )
    client = _smoke_client(tmp_path, monkeypatch, handler)
    embedding = client.post("/api/v1/provider-smoke/model-studio-embedding", headers=HEADERS)
    rerank = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=HEADERS)
    for response in (embedding, rerank):
        assert response.status_code == 502, response.text
        assert response.json()["error"]["provider"]["request_id"] == "hdr-9", response.text


def test_f3_deepseek_smoke_failure_keeps_llm_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        llm_module,
        "create_http_client",
        lambda: mock_client(
            lambda _r: httpx.Response(
                402,
                json={
                    "error": {"code": "InsufficientBalance", "message": "Insufficient Balance"},
                    "request_id": "llm-req-3",
                },
            )
        ),
    )
    client = app_client(tmp_path, secret_backend=SyntheticKeychain())
    open_workspace(client, tmp_path / "workspace")
    configure_real(client, llm=True)
    store_credential(client, "deepseek")
    response = client.post("/api/v1/provider-smoke/deepseek-chat", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["provider"]["code"] == "InsufficientBalance"
    assert error["provider"]["request_id"] == "llm-req-3"


# ==========================================================================
# F4 — request-id handling on non-2xx, body-first, and 2xx non-regression
# ==========================================================================


def _post(handler) -> object:  # noqa: ANN001
    try:
        return bounded_json_post(
            mock_client(handler),
            "https://example.invalid/qa",
            headers={},
            payload={"input": ["x"]},
            max_response_bytes=4096,
        )
    except ProviderError as exc:
        return exc


def test_f4_non_2xx_header_request_id_is_adopted() -> None:
    error = _post(
        lambda _r: httpx.Response(
            500, headers={"x-request-id": "header-request-9"}, json={"code": "e", "message": "m"}
        )
    )
    assert isinstance(error, ProviderError)
    assert error.request_id == "header-request-9"
    assert error.details() == {"code": "e", "message": "m", "request_id": "header-request-9"}


def test_f4_body_request_id_wins_over_header() -> None:
    error = _post(
        lambda _r: httpx.Response(
            403,
            headers={"x-request-id": "header-request-9"},
            json={"code": "access_denied", "message": "denied", "request_id": "body-request-1"},
        )
    )
    assert isinstance(error, ProviderError)
    assert error.request_id == "body-request-1"


def test_f4_non_2xx_without_any_request_id_is_none() -> None:
    error = _post(lambda _r: httpx.Response(500, json={"code": "e", "message": "m"}))
    assert isinstance(error, ProviderError)
    assert error.request_id is None


@pytest.mark.parametrize(
    "header",
    ["bad id!", "x" * 201, "", "with space"],
    ids=["punct", "too-long", "empty", "space"],
)
def test_f4_unshaped_header_is_rejected(header: str) -> None:
    error = _post(lambda _r: httpx.Response(500, headers={"x-request-id": header}, json={}))
    assert isinstance(error, ProviderError)
    assert error.request_id is None


def test_f4_success_path_still_reads_the_header_id() -> None:
    wire = _post(
        lambda _r: httpx.Response(
            200, headers={"x-request-id": "ok-request-1"}, json={"data": [{"index": 0}]}
        )
    )
    assert isinstance(wire, dict)
    assert wire.request_id == "ok-request-1"


def test_f4_alternate_header_names_and_body_id_field() -> None:
    for name in ("request-id", "x-dashscope-request-id"):
        error = _post(lambda _r, n=name: httpx.Response(429, headers={n: "alt-1"}, json={}))
        assert isinstance(error, ProviderError)
        assert error.request_id == "alt-1", name
    error = _post(lambda _r: httpx.Response(500, json={"id": "top-level-id"}))
    assert isinstance(error, ProviderError)
    assert error.request_id == "top-level-id"


def test_f4_request_id_reaches_the_api_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _smoke_client(
        tmp_path,
        monkeypatch,
        lambda _r: httpx.Response(
            429,
            headers={"x-request-id": "transport-42"},
            json={"error": {"code": "throttled", "message": "slow down"}},
        ),
    )
    response = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=HEADERS)
    assert response.status_code == 502, response.text
    assert response.json()["error"]["provider"]["request_id"] == "transport-42"


# ==========================================================================
# F5 — incremental index failure leaves a searchable diagnostics event
# ==========================================================================


class ToggleEmbedding(FakeEmbedding):
    fail = False

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        if self.fail:
            raise RuntimeError(f"{PLAIN_SENTINEL} embedding interruption /private/qa")
        return super().embed(text, fingerprint=fingerprint)


def _index_once(client: TestClient, fingerprint: str) -> None:
    plan = client.post(
        "/api/v1/index/plans", headers=HEADERS, json={"mode": "initial", "fingerprint": fingerprint}
    ).json()
    assert client.post("/api/v1/index/jobs", headers=HEADERS, json=plan).status_code == 200


def test_f5_index_failure_is_recorded_and_keeps_the_field_semantics(tmp_path: Path) -> None:
    embedding = ToggleEmbedding()
    service = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), embedding=embedding)
    client = app_client(tmp_path, query_service=service)
    open_workspace(client, tmp_path / "workspace")
    metadata, _line, _project = seed_page(client)
    _index_once(client, "qa-f5-fingerprint")

    embedding.fail = True
    failed = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "中断知识"},
            "body": "新内容不应从旧索引引用独特词海蓝八六。",
            "confirmation_id": "qa-next-confirmation",
            "operation_id": "qa-next-write",
        },
    )
    assert failed.status_code == 201, failed.text
    assert failed.json()["index_update"] == "update_failed"

    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "index_update_failed", events
    assert events[-1]["state"] == "failed"
    assert events[-1]["reason"] == "RuntimeError"

    text = diagnostics_text(tmp_path / "profile")
    assert PLAIN_SENTINEL not in text
    assert "/private/qa" not in text

    # A successful update keeps the other value of the same field.
    embedding.fail = False
    ok = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "恢复知识"},
            "body": "恢复后写入的另一段独特词青竹三七。",
            "confirmation_id": "qa-ok-confirmation",
            "operation_id": "qa-ok-write",
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["index_update"] == "updated"


def test_f5_typed_index_failure_records_the_sanitized_provider_reason(tmp_path: Path) -> None:
    class TypedFailingEmbedding(FakeEmbedding):
        fail = False

        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            if not self.fail:
                return super().embed(text, fingerprint=fingerprint)
            raise EmbeddingProviderError(
                "向量服务返回错误：invalid_api_key — Invalid API-key provided.",
                provider_code="invalid_api_key",
                provider_message="Invalid API-key provided.",
                request_id="req-11",
                reason="provider",
            )

    embedding = TypedFailingEmbedding()
    service = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), embedding=embedding)
    client = app_client(tmp_path, query_service=service)
    open_workspace(client, tmp_path / "workspace")
    metadata, _line, _project = seed_page(client)
    _index_once(client, "qa-f5-typed-fingerprint")
    embedding.fail = True
    response = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "类型化失败"},
            "body": "独特词玄铁九一。",
            "confirmation_id": "qa-typed-confirmation",
            "operation_id": "qa-typed-write",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["index_update"] == "update_failed"
    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "index_update_failed"
    reason = str(events[-1]["reason"])
    assert "invalid_api_key" in reason and "req-11" in reason, reason


# ==========================================================================
# F6 — GroundedAnswer.text must not be blank
# ==========================================================================


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "\u3000\u00a0", " \n \t "], ids=repr)
def test_f6_blank_answer_text_is_rejected(text: str) -> None:
    with pytest.raises(ValidationError):
        GroundedAnswer(text=text)


def test_f6_normal_text_is_stripped_but_kept() -> None:
    answer = GroundedAnswer(text="  有内容的回答。  ")
    assert answer.text == "有内容的回答。"
    assert GroundedAnswer(text="单行").text == "单行"


def test_f6_blank_answer_from_the_provider_is_a_typed_502(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = json.dumps({"text": "   ", "source_statements": []}, ensure_ascii=False)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "model": "deepseek-flash",
            },
        )

    monkeypatch.setattr(llm_module, "create_http_client", lambda: mock_client(handler))
    client = app_client(tmp_path, secret_backend=SyntheticKeychain())
    open_workspace(client, tmp_path / "workspace")
    configure_real(client, llm=True)
    store_credential(client, "deepseek")
    response = client.post("/api/v1/provider-smoke/deepseek-chat", headers=HEADERS)
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "provider_smoke_failed"
    assert "返回内容不符合应用要求的字段" in response.json()["error"]["message"]


def test_f6_nonblank_answer_from_the_provider_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = json.dumps({"text": "  连接正常。  ", "source_statements": []}, ensure_ascii=False)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "model": "deepseek-flash",
            },
        )

    monkeypatch.setattr(llm_module, "create_http_client", lambda: mock_client(handler))
    client = app_client(tmp_path, secret_backend=SyntheticKeychain())
    open_workspace(client, tmp_path / "workspace")
    configure_real(client, llm=True)
    store_credential(client, "deepseek")
    response = client.post("/api/v1/provider-smoke/deepseek-chat", headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "succeeded"


# ==========================================================================
# Item 8 — 502 / 422 consistency and sanitized failure records
# ==========================================================================


def test_hygiene_provider_side_failures_are_uniformly_502() -> None:
    from starlette.requests import Request

    from summit_everything.api.app import create_app

    app = create_app(session_token="qa-status-token", secret_backend=MemorySecretBackend())
    assert set(app.exception_handlers) >= {ProviderError, LLMProviderError}
    assert set(app.exception_handlers) >= {EmbeddingProviderError, RerankProviderError}

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/journal/assist",
            "raw_path": b"/api/v1/journal/assist",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 1),
            "client": ("127.0.0.1", 2),
        }
    )
    request.state.request_id = "qa-check"
    import anyio

    cases = [
        LLMProviderError,
        ProviderError,
        EmbeddingProviderError,
        RerankProviderError,
    ]
    for cls in cases:
        handler = app.exception_handlers[cls]
        exc = cls("synthetic failure", reason="provider")
        response = anyio.run(handler, request, exc)
        assert response.status_code == 502, cls
        assert json.loads(response.body)["error"]["code"] == "provider_error", cls


def test_hygiene_local_validation_is_422(tmp_path: Path) -> None:
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    bad = client.put(
        "/api/v1/credentials/deepseek",
        headers=HEADERS,
        json={"account_id": "default", "secret": "not-a-key-shape"},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["error"]["code"] == "credential_shape_invalid"
    assert "not-a-key-shape" not in bad.text


def test_hygiene_failure_records_are_sanitized_before_the_write(tmp_path: Path) -> None:
    """A credential-shaped exception text must be masked in the local record."""
    secret_like = "sk-qa-hygiene-abcdefghijklmnop"
    client = assist_client(tmp_path, RuntimeError(f"boom {secret_like} /private/qa"))
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502
    assert secret_like not in response.text
    assert secret_like not in diagnostics_text(tmp_path / "profile")


def test_hygiene_profile_event_rejects_raw_credentials_and_multiline() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        profile = Path(directory)
        with pytest.raises(ValueError):
            profile_event(profile, "assistant_failed", reason="leak sk-abcdefghijklmnop")
        with pytest.raises(ValueError):
            profile_event(profile, "assistant_failed", reason="line one\nline two")
        with pytest.raises(ValueError):
            profile_event(profile, "assistant_failed", reason="")
        with pytest.raises(ValueError):
            profile_event(profile, "assistant_failed", reason="x" * 201)
        profile_event(profile, "assistant_failed", reason="安全原因")
        assert "sk-abcdefghijklmnop" not in (profile / "diagnostics.log").read_text()


def test_hygiene_intake_job_failure_record_is_sanitized(tmp_path: Path) -> None:
    text = sanitize_provider_text(f"boom sk-qa-intake-abcdefghijklmnop {PLAIN_SENTINEL}")
    assert text is not None
    assert "sk-qa-intake-abcdefghijklmnop" not in text
    assert "sk-***" in text
    assert PLAIN_SENTINEL in text  # non-credential text is preserved verbatim


def test_hygiene_query_record_keeps_the_sanitized_cause(tmp_path: Path) -> None:
    class Failing:
        def query(self, *args: object, **kwargs: object) -> object:
            raise EmbeddingProviderError(
                "向量服务返回错误：invalid_api_key — Invalid API-key provided.",
                provider_code="invalid_api_key",
                provider_message="Invalid API-key provided.",
                request_id="req-77",
                reason="provider",
            )

        def close(self) -> None:
            pass

    client = app_client(tmp_path, query_service=Failing())
    open_workspace(client, tmp_path / "workspace")
    stream = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={
            "request_id": str(uuid4()),
            "question": "合成问题",
            "fingerprint": "fake-v1",
            "purpose": "current",
        },
    )
    assert stream.status_code == 200
    assert "invalid_api_key" in stream.text, stream.text
    stored = list((tmp_path / "profile").rglob("conversations.sqlite3"))
    assert len(stored) == 1, stored
    with sqlite3.connect(f"file:{stored[0]}?mode=ro", uri=True) as connection:
        errors = [
            row[0]
            for row in connection.execute("select error from queries order by created_at desc")
        ]
    assert errors and "invalid_api_key" in errors[0]
    assert "查询未能完成，请稍后重试。" not in errors[0]


def test_hygiene_intake_job_failure_record_is_sanitized_end_to_end(tmp_path: Path) -> None:
    """The persisted intake job error keeps a masked, readable cause.

    ``review.py`` used to write ``str(exc)`` verbatim; it now runs the text
    through ``sanitize_provider_text``. The API reads that same field back.
    """
    secret_like = "sk-qa-job-abcdefghijklmnop"
    provider = FailingProvider(LLMProviderError(f"boom {secret_like} /private/qa/job"))
    client = app_client(tmp_path, review_service=IntakeReviewService(provider))
    open_workspace(client, tmp_path / "workspace")
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA 线", "operation_id": "qa-line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "QA 项目", "operation_id": "qa-project"},
    ).json()
    item = client.post(
        "/api/v1/intake/items",
        headers=HEADERS,
        json={"text": "可重试来源。", "filename": "qa.txt", "operation_id": "qa-intake"},
    ).json()
    response = client.post(
        "/api/v1/intake/jobs",
        headers=HEADERS,
        json={
            "item_ids": [item["item_id"]],
            "operation_id": "qa-failing-job",
            "line_id": line["id"],
            "project_id": project["id"],
        },
    )
    assert response.status_code == 502, response.text
    assert secret_like not in response.text

    rows = client.get("/api/v1/intake/items", headers=HEADERS).json()
    job_id = rows[0]["latest_job_id"]
    assert job_id
    job = client.get(f"/api/v1/jobs/{job_id}", headers=HEADERS).json()
    assert job["state"] == "failed", job
    assert secret_like not in json.dumps(job, ensure_ascii=False), job
    assert "sk-***" in (job.get("error") or ""), job
