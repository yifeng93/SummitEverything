"""Item 4 — provider failures must surface with their own code/message/request id.

Real adapters, real API routes, synthetic HTTP boundary only
(``httpx.MockTransport`` through the module's ``create_http_client`` seam).
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import summit_everything.integrations.embedding as embedding_module
import summit_everything.integrations.llm as llm_module
import summit_everything.integrations.rerank as rerank_module
from summit_everything.api.app import create_app
from summit_everything.integrations.runtime import ModelRuntime

from qa_helpers import (
    HEADERS,
    SENTINEL_KEY,
    SyntheticKeychain,
    configure_real_mode,
    json_response,
    open_workspace,
)

OPENAI_401 = {"error": {"message": "Invalid API-key provided.", "code": "invalid_api_key"}}
DASHSCOPE_403 = {
    "code": "Model.AccessDenied",
    "message": "Model access denied.",
    "request_id": "req-403-synthetic",
}


def _install_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path})
        return handler(request)

    def factory() -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(wrapped), trust_env=False)

    monkeypatch.setattr(embedding_module, "create_http_client", factory)
    monkeypatch.setattr(llm_module, "create_http_client", factory)
    monkeypatch.setattr(rerank_module, "create_http_client", factory)
    monkeypatch.setattr(
        ModelRuntime, "_credential", lambda _self, _provider, _account_id: SENTINEL_KEY
    )
    return seen


def _client(tmp_path, *, keychain: bool = True) -> TestClient:
    return TestClient(
        create_app(
            session_token="qa-independent-session",
            profile_root=tmp_path / "profile",
            secret_backend=SyntheticKeychain() if keychain else None,
        )
    )


def _workspace_with_one_page(client: TestClient, tmp_path) -> None:
    open_workspace(client, tmp_path / "workspace")
    configure_real_mode(client)
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA 线", "operation_id": "qa-line"}
    )
    assert line.status_code == 201, line.text
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line.json()["id"], "name": "QA 项目", "operation_id": "qa-project"},
    )
    assert project.status_code == 201, project.text
    page = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {
                "id": "22222222-2222-2222-2222-222222222222",
                "title": "QA 合成页",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line.json()["id"],
                "project_id": project.json()["id"],
            },
            "body": "合成事实：青榆的访客登记须由前台核验姓名。",
            "confirmation_id": "qa-confirm-page",
            "operation_id": "qa-page",
        },
    )
    assert page.status_code == 201, page.text


def _ready_index_request(client: TestClient) -> dict[str, Any]:
    """A confirmed real-mode index plan ready to execute (no provider call yet)."""
    fingerprint = client.get("/api/v1/settings", headers=HEADERS).json()["embedding_fingerprint"]
    plan = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": fingerprint},
    )
    assert plan.status_code == 200, plan.text
    plan_body = plan.json()
    assert plan_body["page_ids"], plan_body
    scope = {
        "mode": plan_body["mode"],
        "fingerprint": plan_body["fingerprint"],
        "page_ids": plan_body["page_ids"],
        "page_versions": plan_body["page_versions"],
    }
    preview = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.index", "scope": scope},
    )
    assert preview.status_code == 201, preview.text
    preview_body = preview.json()
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{preview_body['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": preview_body["plan"]["scope_sha256"],
            "scope": preview_body["scope"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    return {**plan_body, "acceptance_plan_id": preview_body["plan"]["plan_id"]}


def test_embedding_401_keeps_provider_code_and_message(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    key_body = {
        "error": {
            "message": f"Invalid API-key provided. key={SENTINEL_KEY}",
            "code": "invalid_api_key",
        }
    }
    _install_transport(monkeypatch, lambda request: json_response(key_body, status=401))
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)

    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error", error
    assert "invalid_api_key" in error["message"], error
    assert "Invalid API-key provided." in error["message"], error
    assert error["provider"]["code"] == "invalid_api_key"
    assert "Invalid API-key provided." in error["provider"]["message"]
    assert error["request_id"]

    # The injected credential never appears in the response or any log record.
    assert SENTINEL_KEY not in response.text
    assert "sk-***" in response.text
    assert SENTINEL_KEY not in caplog.text


def test_embedding_403_with_request_id_on_the_body(tmp_path, monkeypatch):
    _install_transport(monkeypatch, lambda request: json_response(DASHSCOPE_403, status=403))
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)

    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error", error
    assert "Model.AccessDenied" in error["message"]
    assert "Model access denied." in error["message"]
    assert error["provider"]["code"] == "Model.AccessDenied"
    assert error["provider"]["message"] == "Model access denied."
    assert error["provider"]["request_id"] == "req-403-synthetic"


def test_embedding_200_with_dashscope_error_envelope_is_rejected(tmp_path, monkeypatch):
    """Some providers report the failure with HTTP 200 and a non-zero code."""
    _install_transport(monkeypatch, lambda request: json_response(DASHSCOPE_403, status=200))
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)

    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error", error
    assert error["provider"]["code"] == "Model.AccessDenied"
    assert error["provider"]["request_id"] == "req-403-synthetic"


def test_embedding_200_with_openai_error_envelope_is_rejected(tmp_path, monkeypatch):
    _install_transport(monkeypatch, lambda request: json_response(OPENAI_401, status=200))
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error"
    assert error["provider"]["code"] == "invalid_api_key"


def _rerank_client(tmp_path, monkeypatch, body: object, status: int = 200) -> TestClient:
    _install_transport(monkeypatch, lambda request: json_response(body, status=status))
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    return client


def test_rerank_smoke_surfaces_provider_detail(tmp_path, monkeypatch):
    client = _rerank_client(tmp_path, monkeypatch, DASHSCOPE_403, status=403)
    response = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert "Model.AccessDenied" in error["message"]
    assert "Model access denied." in error["message"]
    assert "req-403-synthetic" in error["message"]
    # Documented deviation from the literal item-4 shape: the smoke route wraps
    # the failure, so the envelope carries no structured ``provider`` object.
    assert error["code"] == "provider_smoke_failed", error
    assert "provider" not in error, error


def test_rerank_smoke_never_echoes_the_credential(tmp_path, monkeypatch):
    body = {
        "code": "invalid_api_key",
        "message": f"Invalid API-key provided: {SENTINEL_KEY}",
        "request_id": "req-rerank-9",
    }
    client = _rerank_client(tmp_path, monkeypatch, body, status=401)
    response = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=HEADERS)
    assert response.status_code == 502, response.text
    assert SENTINEL_KEY not in response.text
    assert "sk-***" in response.text


def test_deepseek_smoke_surfaces_provider_detail(tmp_path, monkeypatch):
    client = _rerank_client(tmp_path, monkeypatch, OPENAI_401, status=401)
    response = client.post("/api/v1/provider-smoke/deepseek-chat", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert "invalid_api_key" in error["message"]
    assert "Invalid API-key provided." in error["message"]
    assert error["code"] == "provider_smoke_failed"


def test_rerank_failure_inside_a_real_query_reaches_the_client(tmp_path, monkeypatch):
    """The real rerank user path is the query stream, not the smoke check."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/embeddings"):
            payload = json.loads(request.content)
            return json_response(
                {
                    "model": "qwen3.7-text-embedding",
                    "data": [
                        {"index": index, "embedding": [1.0] + [0.0] * 1023}
                        for index in range(len(payload["input"]))
                    ],
                    "usage": {"total_tokens": 5},
                }
            )
        if path.endswith("/text-rerank"):
            return json_response(DASHSCOPE_403, status=403)
        raise AssertionError(f"unexpected request {path}")

    _install_transport(monkeypatch, handler)
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    index_payload = _ready_index_request(client)
    indexed = client.post("/api/v1/index/jobs", headers=HEADERS, json=index_payload)
    assert indexed.status_code == 200, indexed.text

    fingerprint = index_payload["fingerprint"]
    request_id = str(uuid4())
    scope = {
        "question": "青榆 访客登记",
        "fingerprint": fingerprint,
        "purpose": "current",
        "answer_mode": "fact",
        "role_id": None,
        "request_id": request_id,
        "conversation_id": None,
    }
    preview = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.query", "scope": scope},
    )
    assert preview.status_code == 201, preview.text
    preview_body = preview.json()
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{preview_body['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": preview_body["plan"]["scope_sha256"],
            "scope": preview_body["scope"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text

    streamed = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={**scope, "acceptance_plan_id": preview_body["plan"]["plan_id"]},
    )
    assert streamed.status_code == 200, streamed.text
    assert any(path.endswith("/text-rerank") for path in calls), calls
    assert "Model.AccessDenied" in streamed.text, streamed.text
    assert "Model access denied." in streamed.text, streamed.text
    assert "req-403-synthetic" in streamed.text, streamed.text


def test_non_2xx_drops_the_transport_request_id_header(tmp_path, monkeypatch):
    """Finding: the ``x-request-id`` response header is read only on 2xx bodies."""

    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(OPENAI_401, status=401, headers={"x-request-id": "hdr-401-abc"})

    _install_transport(monkeypatch, handler)
    client = _client(tmp_path)
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["provider"]["code"] == "invalid_api_key"
    # The provider sent a request id only in the header; it is lost on error.
    assert "request_id" not in error["provider"], error
    assert "hdr-401-abc" not in response.text


def test_rerank_provider_error_handler_shape_is_correct_but_unreachable(tmp_path, monkeypatch):
    """The registered 502 handler works; no product route can currently reach it.

    ``/api/v1/provider-smoke/model-studio-rerank`` catches the error, and the only
    business use of the reranker is inside the SSE query stream. The route below
    is added by this harness only, to exercise the product's own handler.
    """
    from summit_everything.integrations.rerank import RerankProviderError

    _install_transport(monkeypatch, lambda request: json_response(DASHSCOPE_403, status=403))
    app = create_app(
        session_token="qa-independent-session",
        profile_root=tmp_path / "profile",
        secret_backend=SyntheticKeychain(),
    )

    @app.get("/qa-only/rerank-boom")
    def boom() -> None:  # pragma: no cover - harness route
        raise RerankProviderError(
            "排序服务返回错误：Model.AccessDenied — Model access denied.",
            provider_code="Model.AccessDenied",
            provider_message="Model access denied.",
            request_id="req-403-synthetic",
            reason="provider",
        )

    client = TestClient(app)
    response = client.get("/qa-only/rerank-boom")
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_error"
    assert error["provider"]["request_id"] == "req-403-synthetic"
    assert "Model.AccessDenied" in error["message"]
