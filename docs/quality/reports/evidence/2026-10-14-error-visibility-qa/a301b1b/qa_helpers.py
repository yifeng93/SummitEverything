"""Shared harness helpers for the independent QA of SHA a301b1b.

No real provider, no real keychain, no external socket: every network-facing
check uses ``httpx.MockTransport`` and every credential store is in memory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MacOSKeychainBackend, MemorySecretBackend

TOKEN = "qa-independent-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

#: Sentinel credential shape. Never a real key; long enough to match the
#: boundary's ``sk-[A-Za-z0-9_-]{8,}`` masking pattern.
SENTINEL_KEY = "sk-abcdefghijklmnop"

DASH_SCOPE_BASE = "https://dashscope.aliyuncs.com"
MODEL_STUDIO_BASE = "<injected workspace endpoint>"


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


def mock_client(handler: Any) -> httpx.Client:
    """A client whose transport is a synthetic external boundary."""
    return httpx.Client(transport=httpx.MockTransport(handler))


def json_response(payload: object, *, status: int = 200, headers: dict[str, str] | None = None):
    return httpx.Response(
        status,
        content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json", **(headers or {})},
    )


def open_workspace(client: TestClient, root: Path, *, name: str = "QA 模拟库") -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(root),
            "mode": "create",
            "name": name,
            "operation_id": f"qa-open-{root.name}-{uuid4()}",
        },
    )
    assert opened.status_code == 201, opened.text


def configure_real_mode(client: TestClient, *, base_url: str = MODEL_STUDIO_BASE) -> None:
    """Real mode with all three providers enabled and pointing at a synthetic host."""
    configured = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "mode": "real",
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "enabled": True,
                "base_url": base_url + "/compatible-mode/v1",
            },
            "rerank": {
                "provider": "dashscope",
                "model": "qwen3.7-text-rerank",
                "enabled": True,
                "base_url": base_url + "/api/v1",
            },
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
                "max_output_tokens": 2048,
            },
        },
    )
    assert configured.status_code == 200, configured.text


def store_sentinel_credentials(client: TestClient) -> None:
    for provider in ("dashscope", "deepseek"):
        stored = client.put(
            f"/api/v1/credentials/{provider}",
            headers=HEADERS,
            json={"account_id": "default", "secret": SENTINEL_KEY},
        )
        assert stored.status_code == 200, stored.text


def new_client(tmp_path: Path, *, query_service: Any = None, **kwargs: Any) -> TestClient:
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=kwargs.pop("secret_backend", MemorySecretBackend()),
            query_service=query_service,
            **kwargs,
        )
    )


def conversations_db(tmp_path: Path) -> Path:
    stored = list((tmp_path / "profile").rglob("conversations.sqlite3"))
    assert len(stored) == 1, stored
    return stored[0]


def deepseek_wire(content: str, *, finish_reason: str = "stop") -> dict[str, object]:
    """A DeepSeek-shaped chat completion envelope carrying ``content``."""
    return {
        "id": "chatcmpl-qa-1",
        "object": "chat.completion",
        "model": "deepseek-flash",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
