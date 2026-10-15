"""F1 — a 200 response whose content is unusable is a typed provider failure.

QA-only harness (fixed SHA 19078de). Every HTTP interaction uses httpx
MockTransport; no real provider, key or socket is contacted.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from summit_everything.integrations.embedding import (
    EmbeddingProviderError,
    ModelStudioEmbedding,
)
from summit_everything.integrations.http_boundary import ProviderError
from summit_everything.integrations.rerank import ModelStudioReranker, RerankProviderError
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

from qa_common import (
    HEADERS,
    KEY,
    PLAIN_SENTINEL,
    SENTINEL,
    app_client,
    mock_client,
    open_workspace,
    seed_page,
)

EMBED_MODEL = "qwen3.7-text-embedding"


def embedding_adapter(response: httpx.Response) -> ModelStudioEmbedding:
    return ModelStudioEmbedding(KEY, client=mock_client(lambda _request: response))


def rerank_adapter(response: httpx.Response) -> ModelStudioReranker:
    return ModelStudioReranker(KEY, client=mock_client(lambda _request: response))


# --------------------------------------------------------------------------
# F1.a — typed error from the adapter, for every "200 but unusable" shape
# --------------------------------------------------------------------------

EMBEDDING_UNUSABLE = {
    "data-missing": {"model": EMBED_MODEL},
    "data-empty-list": {"model": EMBED_MODEL, "data": []},
    "data-wrong-type": {"model": EMBED_MODEL, "data": "wrong"},
    "model-mismatch": {"model": "other-model", "data": [{"index": 0, "embedding": [0.0] * 1024}]},
    "vector-wrong-dim": {
        "model": EMBED_MODEL,
        "data": [{"index": 0, "embedding": [0.1, 0.2]}],
    },
    "vector-non-numeric": {
        "model": EMBED_MODEL,
        "data": [{"index": 0, "embedding": ["x"] * 1024}],
    },
    "index-out-of-range": {
        "model": EMBED_MODEL,
        "data": [{"index": 5, "embedding": [0.1] * 1024}],
    },
    "vector-omitted": {"model": EMBED_MODEL, "data": []},
}


@pytest.mark.parametrize("label", sorted(EMBEDDING_UNUSABLE))
def test_f1_embedding_unusable_200_is_typed(label: str) -> None:
    body = EMBEDDING_UNUSABLE[label]
    adapter = embedding_adapter(httpx.Response(200, json=body))
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本一"])
    error = caught.value
    assert isinstance(error, ProviderError)
    assert isinstance(error, ValueError)
    assert error.reason == "schema", (label, error.reason)
    assert error.details() == {}, (label, error.details())
    assert "无法解析" in str(error)


NON_FINITE_BODY = (
    '{"model": "'
    + EMBED_MODEL
    + '", "data": [{"index": 0, "embedding": ['
    + ", ".join(["1e400"] * 1024)
    + "]}]}"
).encode()


def test_f1_embedding_non_finite_vector_is_typed() -> None:
    """``1e400`` parses to +inf, which must be rejected as unusable content."""
    adapter = embedding_adapter(httpx.Response(200, content=NON_FINITE_BODY))
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本一"])
    assert caught.value.reason == "schema"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json at all"),
        httpx.Response(200, content=b""),
        httpx.Response(200, content=b"<html>upstream proxy</html>"),
        httpx.Response(200, content=b"\xff\xfe\x00binary"),
    ],
    ids=["text", "empty", "html", "binary"],
)
def test_f1_embedding_non_json_200_is_typed(response: httpx.Response) -> None:
    adapter = embedding_adapter(response)
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本一"])
    assert caught.value.reason == "schema"
    assert KEY not in str(caught.value)


def test_f1_embedding_unusable_200_never_leaks_the_injected_sentinel() -> None:
    """A credential-shaped string smuggled into a 200 body stays out of the error."""
    adapter = embedding_adapter(
        httpx.Response(200, json={"model": EMBED_MODEL, "data": [], "echo": SENTINEL})
    )
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本一"])
    assert SENTINEL not in str(caught.value)
    assert SENTINEL not in repr(caught.value.details())


RERANK_UNUSABLE = {
    "output-missing": {},
    "results-missing": {"output": {}},
    "results-wrong-type": {"output": {"results": "nope"}},
    "results-wrong-length": {"output": {"results": [{"index": 0, "relevance_score": 0.5}]}},
    "score-non-numeric": {
        "output": {"results": [{"index": 0, "relevance_score": "x"}, {"index": 1, "relevance_score": 0.4}]}
    },
    "score-out-of-range": {
        "output": {
            "results": [
                {"index": 0, "relevance_score": 0.1},
                {"index": 1, "relevance_score": 7.0},
            ]
        }
    },
    "index-duplicated": {
        "output": {
            "results": [
                {"index": 0, "relevance_score": 0.1},
                {"index": 0, "relevance_score": 0.2},
            ]
        }
    },
}


@pytest.mark.parametrize("label", sorted(RERANK_UNUSABLE))
def test_f1_rerank_unusable_200_is_typed(label: str) -> None:
    adapter = rerank_adapter(httpx.Response(200, json=RERANK_UNUSABLE[label]))
    with pytest.raises(RerankProviderError) as caught:
        adapter.rank("合成问题", ["候选一", "候选二"])
    error = caught.value
    assert isinstance(error, ProviderError)
    assert error.reason == "schema", (label, error.reason)
    assert error.details() == {}
    assert "无法解析" in str(error)


@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, content=b"nope"), httpx.Response(200, content=b"")],
    ids=["text", "empty"],
)
def test_f1_rerank_non_json_200_is_typed(response: httpx.Response) -> None:
    adapter = rerank_adapter(response)
    with pytest.raises(RerankProviderError) as caught:
        adapter.rank("合成问题", ["候选一", "候选二"])
    assert caught.value.reason == "schema"


# --------------------------------------------------------------------------
# F1.b — the reverse boundary: local parameter checks stay a bare ValueError
# --------------------------------------------------------------------------


def _never_called(_request: httpx.Request) -> httpx.Response:  # pragma: no cover
    raise AssertionError("local validation must run before any HTTP call")


def test_f1_embedding_local_checks_stay_plain_value_error_and_skip_http() -> None:
    adapter = ModelStudioEmbedding(KEY, client=mock_client(_never_called))
    cases = {
        "empty-batch": lambda: adapter.embed_many([]),
        "batch-too-large": lambda: adapter.embed_many([f"文本{index}" for index in range(21)]),
        "blank-text": lambda: adapter.embed_many(["   "]),
        "blank-newline": lambda: adapter.embed_many(["\n\t"]),
        "text-too-large": lambda: adapter.embed_many(["甲" * 20_000]),
    }
    for label, call in cases.items():
        with pytest.raises(ValueError) as caught:
            call()
        assert not isinstance(caught.value, ProviderError), label
        assert type(caught.value) is ValueError, (label, type(caught.value))


def test_f1_rerank_local_checks_stay_plain_value_error_and_skip_http() -> None:
    adapter = ModelStudioReranker(KEY, client=mock_client(_never_called))
    cases = {
        "empty-candidates": lambda: adapter.rank("问题", []),
        "too-many-candidates": lambda: adapter.rank("问题", ["候选"] * 101),
        "blank-query": lambda: adapter.rank("   ", ["候选"]),
        "blank-candidate": lambda: adapter.rank("问题", ["   "]),
        "request-too-large": lambda: adapter.rank("问题", ["乙" * 20_000] * 100),
    }
    for label, call in cases.items():
        with pytest.raises(ValueError) as caught:
            call()
        assert not isinstance(caught.value, ProviderError), label
        assert type(caught.value) is ValueError, (label, type(caught.value))


# --------------------------------------------------------------------------
# F1.c — through the API: 502 + error.code=provider_error
# --------------------------------------------------------------------------


def _real_embedding_query_service(profile: Path, response: httpx.Response) -> QueryService:
    return QueryService(
        IndexStore(profile / "index.sqlite3"),
        embedding=embedding_adapter(response),
    )


def _index_plan(client: TestClient) -> dict[str, object]:
    plan = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": "qa-f1-fingerprint"},
    )
    assert plan.status_code == 200, plan.text
    return plan.json()


def test_f1_api_index_jobs_unusable_200_is_502_provider_error(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    service = _real_embedding_query_service(
        profile, httpx.Response(200, json={"model": EMBED_MODEL, "data": []})
    )
    client = app_client(tmp_path, query_service=service)
    open_workspace(client, tmp_path / "workspace")
    seed_page(client)
    plan = _index_plan(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=plan)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error", error
    assert "向量服务" in error["message"]
    # The client envelope renders the sanitized structured category, never the
    # free-form exception text: a 200 with unusable content is a provider fault.
    assert "返回内容不符合应用要求的字段" in error["message"]
    assert KEY not in response.text
    assert SENTINEL not in response.text


@pytest.mark.parametrize(
    "reserved",
    [
        {"model": EMBED_MODEL, "data": [], "echo": SENTINEL},
        {"model": EMBED_MODEL, "data": []},
    ],
    ids=["with-sentinel", "plain"],
)
def test_f1_api_index_jobs_502_message_is_readable_and_clean(
    tmp_path: Path, reserved: dict[str, object]
) -> None:
    profile = tmp_path / "profile"
    service = _real_embedding_query_service(profile, httpx.Response(200, json=reserved))
    client = app_client(tmp_path, query_service=service)
    open_workspace(client, tmp_path / "workspace")
    seed_page(client)
    plan = _index_plan(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=plan)
    assert response.status_code == 502, response.text
    message = response.json()["error"]["message"]
    assert message and message.strip() and len(message) <= 300, message
    assert SENTINEL not in response.text
    assert PLAIN_SENTINEL not in response.text


def test_f1_api_local_validation_still_422_not_provider_fault(tmp_path: Path) -> None:
    """A bad request body must be 422 validation_error, never 502 provider_error."""
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    response = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "not-a-mode", "fingerprint": "x"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_f1_rerank_typed_error_reaches_the_query_surface(tmp_path: Path) -> None:
    """A rerank schema failure reaches the user as a typed reason.

    The error object is produced by the real adapter against a MockTransport
    200-with-unusable-content response, then surfaced through the real SSE query
    endpoint. Retrieval qualification is bypassed deliberately so that the
    assertion is about error propagation, not about search recall.
    """
    from uuid import uuid4

    with pytest.raises(RerankProviderError) as caught:
        rerank_adapter(httpx.Response(200, json={"output": {}})).rank("问题", ["候选"])
    genuine = caught.value
    assert genuine.reason == "schema"

    class RerankFailingService:
        def __init__(self) -> None:
            self.closed = False

        def query(self, *args: object, **kwargs: object) -> object:
            raise genuine

        def close(self) -> None:
            self.closed = True

    client = app_client(tmp_path, query_service=RerankFailingService())
    open_workspace(client, tmp_path / "workspace")
    stream = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={
            "request_id": str(uuid4()),
            "question": "基线知识是什么？",
            "fingerprint": "fake-v1",
            "purpose": "current",
        },
    )
    assert stream.status_code == 200, stream.text
    assert "排序服务不可用：返回内容不符合应用要求的字段。" in stream.text, stream.text
    assert "查询未能完成，请稍后重试。" not in stream.text
