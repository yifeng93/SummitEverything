"""Typed provider failures carry a sanitized, bounded reason (all synthetic).

These tests exist because four real first-use failures (a bad key, a denied
model, a malformed key and a schema mismatch) were all invisible: the provider's
own ``code``/``message`` was discarded and the caller saw an opaque 500.
"""

from __future__ import annotations

import httpx
import pytest

from summit_everything.integrations.embedding import EmbeddingProviderError, ModelStudioEmbedding
from summit_everything.integrations.http_boundary import (
    ProviderError,
    bounded_json_post,
    provider_error_fields,
    reject_business_error,
    sanitize_provider_text,
)
from summit_everything.integrations.rerank import ModelStudioReranker, RerankProviderError

KEY = "sk-synthetic-provider-key-0001"


def mock_client(handler) -> httpx.Client:  # noqa: ANN001 - test helper
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_provider_error_fields_reads_both_envelope_shapes():
    openai = {
        "error": {
            "message": "Invalid API-key provided.",
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }
    assert provider_error_fields(openai) == (
        "invalid_api_key",
        "Invalid API-key provided.",
        None,
    )
    dashscope = {
        "code": "InvalidApiKey",
        "message": "Invalid API-key provided.",
        "request_id": "dashscope-request-1",
    }
    assert provider_error_fields(dashscope) == (
        "InvalidApiKey",
        "Invalid API-key provided.",
        "dashscope-request-1",
    )


def test_sanitize_masks_keys_collapses_lines_and_bounds_length():
    masked = sanitize_provider_text(f"line1\nline2 {KEY} trailing")
    assert masked is not None
    assert "\n" not in masked
    assert KEY not in masked
    assert "sk-***" in masked
    bounded = sanitize_provider_text("x" * 1000)
    assert bounded is not None and len(bounded) == 300


def test_reject_business_error_carries_sanitized_provider_details():
    with pytest.raises(ProviderError) as caught:
        reject_business_error({"error": {"code": "invalid_api_key", "message": f"bad {KEY}"}})
    error = caught.value
    assert isinstance(error, ValueError)
    assert error.provider_code == "invalid_api_key"
    assert KEY not in (error.provider_message or "")
    assert error.details()["code"] == "invalid_api_key"
    assert "invalid_api_key" in error.describe()


def test_non_success_status_keeps_the_provider_reason_under_one_read():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "message": "Model access denied",
                "id": "request-42",
                "type": "access_denied",
                "code": "access_denied",
            },
        )

    with pytest.raises(ProviderError) as caught:
        bounded_json_post(
            mock_client(handler),
            "https://example.invalid/embeddings",
            headers={"Authorization": f"Bearer {KEY}"},
            payload={"input": ["x"]},
            max_response_bytes=4096,
        )
    error = caught.value
    assert error.provider_message == "Model access denied"
    assert error.request_id == "request-42"
    assert "HTTP 403" in str(error)


def test_expired_deadline_is_typed_with_a_controlled_reason():
    def handler(_request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must not leave the client")

    with pytest.raises(ProviderError) as caught:
        bounded_json_post(
            mock_client(handler),
            "https://example.invalid/embeddings",
            headers={},
            payload={"input": ["x"]},
            max_response_bytes=4096,
            deadline_seconds=-1.0,
        )
    assert caught.value.reason == "deadline"


def test_embedding_provider_failure_is_typed_and_hides_the_key():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "error": {
                    "code": "invalid_api_key",
                    "message": "Invalid API-key provided.",
                    "type": "invalid_request_error",
                }
            },
        )

    adapter = ModelStudioEmbedding(KEY, client=mock_client(handler))
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本"])
    error = caught.value
    assert isinstance(error, ValueError)
    assert error.provider_code == "invalid_api_key"
    assert error.reason == "provider"
    assert "invalid_api_key" in str(error)
    assert KEY not in str(error)
    assert error.details() == {
        "code": "invalid_api_key",
        "message": "Invalid API-key provided.",
    }


def test_rerank_provider_failure_is_typed():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"code": "access_denied", "message": "Model access denied"},
        )

    adapter = ModelStudioReranker(KEY, client=mock_client(handler))
    with pytest.raises(RerankProviderError) as caught:
        adapter.rank("问题", ["候选一", "候选二"])
    assert caught.value.provider_code == "access_denied"
    assert caught.value.reason == "provider"


def test_transport_failure_is_typed_with_a_controlled_reason():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("synthetic transport failure")

    adapter = ModelStudioEmbedding(KEY, client=mock_client(handler))
    with pytest.raises(EmbeddingProviderError) as caught:
        adapter.embed_many(["合成文本"])
    assert caught.value.reason == "transport"
    assert caught.value.details() == {}


def test_local_parameter_validation_stays_a_plain_value_error():
    adapter = ModelStudioEmbedding(KEY, client=mock_client(lambda _r: httpx.Response(200, json={})))
    with pytest.raises(ValueError) as caught:
        adapter.embed_many([])
    assert not isinstance(caught.value, ProviderError)
