"""Item 5 — a failed question must be diagnosable locally and safe on the wire."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import EmbeddingProviderError
from summit_everything.integrations.settings import MemorySecretBackend

from qa_helpers import HEADERS, SENTINEL_KEY, conversations_db, open_workspace


def _client(tmp_path: Any, service: Any) -> TestClient:
    return TestClient(
        create_app(
            session_token="qa-independent-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
            query_service=service,
        )
    )


def _ask(client: TestClient) -> str:
    response = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={
            "request_id": "44444444-4444-4444-4444-444444444444",
            "question": "合成问题",
            "fingerprint": "fake-v1",
            "purpose": "current",
        },
    )
    assert response.status_code == 200, response.text
    return response.text


def _errors(tmp_path: Any) -> list[str]:
    with sqlite3.connect(f"file:{conversations_db(tmp_path)}?mode=ro", uri=True) as connection:
        return [
            row[0]
            for row in connection.execute("select error from queries order by created_at desc")
        ]


def test_typed_failure_is_specific_on_the_wire_and_in_the_record(tmp_path):
    class FailingQuery:
        def query(self, *args: Any, **kwargs: Any) -> None:
            raise EmbeddingProviderError(
                f"向量服务返回错误：invalid_api_key — Invalid API-key provided. {SENTINEL_KEY}",
                provider_code="invalid_api_key",
                provider_message=f"Invalid API-key provided. {SENTINEL_KEY}",
                request_id="request-77",
                reason="provider",
            )

    client = _client(tmp_path, FailingQuery())
    open_workspace(client, tmp_path / "workspace")
    text = _ask(client)

    assert "invalid_api_key" in text
    assert "Invalid API-key provided." in text
    assert "request-77" in text
    assert SENTINEL_KEY not in text
    assert "sk-***" in text

    stored = _errors(tmp_path)
    assert stored and "EmbeddingProviderError" in stored[0]
    assert "invalid_api_key" in stored[0]
    assert SENTINEL_KEY not in stored[0]
    assert "sk-***" in stored[0]
    assert "查询未能完成，请稍后重试。" not in stored[0]
    assert "\n" not in stored[0]


def test_unknown_failure_keeps_the_safe_text_but_still_records_the_cause(tmp_path):
    class FailingQuery:
        def query(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(f"sentinel {SENTINEL_KEY} /private/qa-profile")

    client = _client(tmp_path, FailingQuery())
    open_workspace(client, tmp_path / "workspace")
    text = _ask(client)

    assert "查询未能完成，请稍后重试。" in text
    assert "sentinel" not in text
    assert "/private/qa-profile" not in text
    assert SENTINEL_KEY not in text
    assert "RuntimeError" not in text

    stored = _errors(tmp_path)
    assert stored and "RuntimeError" in stored[0], stored
    assert "sentinel" in stored[0], stored
    assert "/private/qa-profile" in stored[0], stored
    assert SENTINEL_KEY not in stored[0], stored
    assert "sk-***" in stored[0], stored
    assert "\n" not in stored[0]
    assert len(stored[0]) <= 300


def test_error_event_carries_the_same_reason_as_the_client_message(tmp_path):
    class FailingQuery:
        def query(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("boom")

    client = _client(tmp_path, FailingQuery())
    open_workspace(client, tmp_path / "workspace")
    text = _ask(client)
    payloads = [
        json.loads(line.removeprefix("data: "))
        for line in text.splitlines()
        if line.startswith("data: ")
    ]
    error_events = [item for item in payloads if item["type"] == "error"]
    assert error_events, payloads
    data = error_events[-1]["data"]
    assert data["code"] == "query_error"
    assert data["message"] == "查询未能完成，请稍后重试。"
    assert data["detail"] == data["message"]
    assert "boom" not in text


def test_provider_error_event_keeps_the_masked_provider_reason(tmp_path):
    class FailingQuery:
        def query(self, *args: Any, **kwargs: Any) -> None:
            raise EmbeddingProviderError(
                "向量服务返回错误：Model.AccessDenied — Model access denied.",
                provider_code="Model.AccessDenied",
                provider_message="Model access denied.",
                request_id="req-abc",
                reason="provider",
            )

    client = _client(tmp_path, FailingQuery())
    open_workspace(client, tmp_path / "workspace")
    text = _ask(client)
    payloads = [
        json.loads(line.removeprefix("data: "))
        for line in text.splitlines()
        if line.startswith("data: ")
    ]
    data = [item for item in payloads if item["type"] == "error"][-1]["data"]
    assert "Model.AccessDenied" in data["message"]
    assert "req-abc" in data["message"]
    assert "查询未能完成，请稍后重试。" not in data["message"]


@pytest.mark.parametrize("exception_type", ["timeout", "transport"])
def test_unclassified_typed_failures_fall_back_to_a_fixed_reason(tmp_path, exception_type):
    class FailingQuery:
        def query(self, *args: Any, **kwargs: Any) -> None:
            raise EmbeddingProviderError("embedding provider timed out", reason=exception_type)

    client = _client(tmp_path, FailingQuery())
    open_workspace(client, tmp_path / "workspace")
    text = _ask(client)
    assert "向量服务" in text
    assert "sk-" not in text
    stored = _errors(tmp_path)
    assert stored and "EmbeddingProviderError" in stored[0]
