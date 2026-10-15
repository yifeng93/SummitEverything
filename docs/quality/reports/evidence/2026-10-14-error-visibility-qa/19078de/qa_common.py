"""Shared helpers for the independent QA harness on fixed SHA 19078de.

QA-only file. It lives under ``.local/qa`` and is never committed; it does not
import private internals beyond the public seams the product already exposes.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MacOSKeychainBackend, MemorySecretBackend

TOKEN = "qa-19078de-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
KEY = "sk-synthetic-qa-19078de-key-0001"
SENTINEL = "sk-QA-SENTINEL-9f3c2b1a"
PLAIN_SENTINEL = "qa-private-probe-4d5e6f"


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


def mock_client(handler) -> httpx.Client:  # noqa: ANN001 - test helper
    """An httpx client whose only transport is a synthetic in-process handler."""
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        trust_env=False,
        follow_redirects=False,
    )


def app_client(tmp_path: Path, **kwargs: object) -> TestClient:
    backend = kwargs.pop("secret_backend", None) or MemorySecretBackend()
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=backend,
            **kwargs,  # type: ignore[arg-type]
        )
    )


def open_workspace(client: TestClient, root: Path) -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={"root": str(root), "mode": "create", "name": "QA 模拟库", "operation_id": "qa-ws"},
    )
    assert opened.status_code == 201, opened.text


def seed_page(client: TestClient, *, body: str = "稳定内容琥珀四二。", title: str = "基线知识"):
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA 线", "operation_id": "qa-line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "QA 项目", "operation_id": "qa-project"},
    ).json()
    metadata = {
        "id": str(uuid4()),
        "title": title,
        "role": "knowledge",
        "kind": "topic",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    created = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": metadata,
            "body": body,
            "confirmation_id": "qa-confirmation",
            "operation_id": f"qa-write-{uuid4()}",
        },
    )
    assert created.status_code == 201, created.text
    return metadata, line, project


def configure_real(client: TestClient, *, llm: bool = False) -> None:
    body: dict[str, object] = {"mode": "real"}
    if llm:
        body["llm"] = {"provider": "deepseek", "model": "deepseek-flash", "enabled": True}
    else:
        body["embedding"] = {
            "provider": "dashscope",
            "model": "qwen3.7-text-embedding",
            "enabled": True,
        }
        body["rerank"] = {"provider": "dashscope", "model": "qwen3.7-text-rerank", "enabled": True}
    response = client.patch("/api/v1/settings", headers=HEADERS, json=body)
    assert response.status_code == 200, response.text


def store_credential(client: TestClient, provider: str, secret: str = KEY) -> None:
    response = client.put(
        f"/api/v1/credentials/{provider}",
        headers=HEADERS,
        json={"account_id": "default", "secret": secret},
    )
    assert response.status_code == 200, response.text


def diagnostics_text(profile_root: Path) -> str:
    files = sorted(profile_root.rglob("diagnostics.log"))
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def diagnostics_events(profile_root: Path) -> list[dict[str, object]]:
    text = diagnostics_text(profile_root).strip()
    return [json.loads(line) for line in text.splitlines() if line]
