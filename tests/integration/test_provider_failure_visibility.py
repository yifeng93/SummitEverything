"""A failed query tells the user why, without echoing secrets or paths.

The WebUI renders the SSE ``error`` message verbatim, so the specific cause must
travel in ``message``. Free-form exception text stays out of the client response
(it can carry credentials or local paths) and only reaches the local log.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import EmbeddingProviderError, FakeEmbedding
from summit_everything.integrations.llm import DeepSeekLLM, LLMProviderError
from summit_everything.integrations.settings import MacOSKeychainBackend, MemorySecretBackend
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "synthetic-visibility-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class SyntheticKeychain(MacOSKeychainBackend):
    """In-memory stand-in for the macOS keychain; touches no real credential."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get(self, namespace: str, key: str) -> str | None:
        return self.values.get((namespace, key))

    def set(self, namespace: str, key: str, value: str) -> None:
        self.values[(namespace, key)] = value

    def delete(self, namespace: str, key: str) -> None:
        self.values.pop((namespace, key), None)


def open_workspace(client: TestClient, root) -> None:  # noqa: ANN001 - test helper
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(root),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-visibility-test",
        },
    )
    assert opened.status_code == 201, opened.text
    current = client.get("/api/v1/workspaces/current", headers=HEADERS).json()
    settings = client.get("/api/v1/settings", headers=HEADERS).json()
    index = QueryService(
        IndexStore(Path(current["local_profile_dir"]) / "index.sqlite3"),
        embedding=FakeEmbedding(),
    )
    index.rebuild(Path(root), fingerprint=settings["embedding_fingerprint"])


def ask(client: TestClient) -> str:
    response = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={
            "request_id": str(uuid4()),
            "question": "合成问题",
            "fingerprint": client.get("/api/v1/settings", headers=HEADERS).json()[
                "embedding_fingerprint"
            ],
            "purpose": "current",
        },
    )
    assert response.status_code == 200
    return response.text


def test_typed_provider_failure_reaches_the_user_message(tmp_path):
    class FailingQuery:
        def query(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise EmbeddingProviderError(
                "向量服务返回错误：invalid_api_key — Invalid API-key provided.",
                provider_code="invalid_api_key",
                provider_message="Invalid API-key provided.",
                request_id="request-77",
                reason="provider",
            )

    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
            query_service=FailingQuery(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    text = ask(client)
    assert "invalid_api_key" in text
    assert "Invalid API-key provided." in text
    assert "request-77" in text

    # The query record must keep the same specific reason, not a generic one.
    stored = list((tmp_path / "profile").rglob("conversations.sqlite3"))
    assert len(stored) == 1, stored
    with sqlite3.connect(f"file:{stored[0]}?mode=ro", uri=True) as connection:
        errors = [
            row[0]
            for row in connection.execute("select error from queries order by created_at desc")
        ]
    assert errors and "invalid_api_key" in errors[0]
    assert "查询未能完成，请稍后重试。" not in errors[0]


def test_unknown_exception_keeps_the_generic_message_and_hides_text(tmp_path):
    sentinel = "credential-sentinel-visibility"

    class FailingQuery:
        def query(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise RuntimeError(f"{sentinel} /private/profile")

    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
            query_service=FailingQuery(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    text = ask(client)
    assert sentinel not in text
    assert "/private/profile" not in text
    assert "查询未能完成，请稍后重试。" in text

    # The client keeps the safe sentence, but the local record must still say what
    # broke: in a packaged app that record is the only surface that survives
    # (Python logging has no handler and its stderr is discarded).
    stored = list((tmp_path / "profile").rglob("conversations.sqlite3"))
    assert len(stored) == 1, stored
    with sqlite3.connect(f"file:{stored[0]}?mode=ro", uri=True) as connection:
        errors = [
            row[0]
            for row in connection.execute("select error from queries order by created_at desc")
        ]
    assert errors and "RuntimeError" in errors[0]
    assert sentinel in errors[0]


@pytest.mark.parametrize(
    ("provider", "secret", "expected_status"),
    [
        ("deepseek", "sk-synthetic-key-0000000000", 200),
        # Real Model Studio keys carry JWT-style dot separators; they must pass
        # the shape gate even though the old alphabet rejected them.
        ("deepseek", "sk-abcdefghijklmnop.qrstuvwx", 200),
        (
            "deepseek",
            "sk-" + "a" * 16 + "." + "b" * 16 + "." + "c" * 16 + "." + "d" * 16,
            200,
        ),
        ("deepseek", "sk-abcdefghijklmnop+/=", 200),
        ("deepseek", "sk-abcdefghijklmnop\u200b", 422),
        ("deepseek", 'sk-abcdefghij"klmnop', 422),
        ("deepseek", "synthetic-key", 422),
        ("deepseek", "sk-short", 422),
        ("deepseek", "sk-synthetic\nkey-0000000000", 422),
        ("deepseek", "sk-synthetic key-0000000000", 422),
        ("deepseek", "sk-" + "a" * 600, 422),
        ("feishu_app", "synthetic-app-secret-value-01", 200),
        ("feishu_app", "synthetic app secret", 422),
        ("feishu_app", "short", 422),
    ],
)
def test_credential_shape_is_checked_before_the_keychain_write(
    tmp_path, provider, secret, expected_status
):
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    response = client.put(
        f"/api/v1/credentials/{provider}",
        headers=HEADERS,
        json={"account_id": "default", "secret": secret},
    )
    assert response.status_code == expected_status, response.text
    assert secret not in response.text
    if expected_status == 422:
        assert response.json()["error"]["code"] == "credential_shape_invalid"
        assert response.json()["error"]["message"]


def _store_credential(client: TestClient, provider: str) -> None:
    response = client.put(
        f"/api/v1/credentials/{provider}",
        headers=HEADERS,
        json={"account_id": "default", "secret": "sk-synthetic-provider-key-0001"},
    )
    assert response.status_code == 200, response.text


def _configure_real(client: TestClient, *, llm: bool) -> None:
    payload: dict[str, object] = {"mode": "real"}
    if llm:
        payload["llm"] = {
            "provider": "deepseek",
            "model": "deepseek-flash",
            "enabled": True,
        }
    saved = client.patch("/api/v1/settings", headers=HEADERS, json=payload)
    assert saved.status_code == 200, saved.text


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/provider-smoke/model-studio-embedding",
        "/api/v1/provider-smoke/model-studio-rerank",
    ],
)
def test_legacy_retrieval_smokes_are_rejected_without_provider_calls(tmp_path, endpoint):
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=SyntheticKeychain(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    response = client.post(endpoint, headers=HEADERS)
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "legacy_provider_migration_required"


def test_deepseek_smoke_failure_is_502_with_provider_details(tmp_path, monkeypatch):
    def failing_answer(self, question, passages, context=None):  # noqa: ANN001, ANN002, ANN003
        raise LLMProviderError(
            "模型服务返回错误：InsufficientBalance — Insufficient Balance",
            provider_code="InsufficientBalance",
            provider_message="Insufficient Balance",
            request_id="request-100",
            reason="provider",
        )

    monkeypatch.setattr(DeepSeekLLM, "answer", failing_answer)
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=SyntheticKeychain(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    _configure_real(client, llm=True)
    _store_credential(client, "deepseek")

    response = client.post("/api/v1/provider-smoke/deepseek-chat", headers=HEADERS)
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "provider_smoke_failed"
    assert error["provider"]["code"] == "InsufficientBalance"
    assert error["provider"]["request_id"] == "request-100"


def test_llm_provider_error_handler_is_502_and_keeps_details():
    """Provider-side failures are uniformly 502, with the provider's own words."""
    app = create_app(session_token="synthetic-status-token", secret_backend=MemorySecretBackend())
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
    request.state.request_id = "status-check"
    error = LLMProviderError(
        "模型服务返回错误：invalid_api_key — Invalid API-key provided.",
        provider_code="invalid_api_key",
        provider_message="Invalid API-key provided.",
        request_id="request-101",
        reason="provider",
    )
    handler = app.exception_handlers[LLMProviderError]
    response = asyncio.run(handler(request, error))
    assert response.status_code == 502
    body = json.loads(response.body)
    assert body["error"]["code"] == "provider_error"
    assert body["error"]["provider"]["code"] == "invalid_api_key"
