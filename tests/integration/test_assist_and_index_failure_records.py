"""Assist and index failures leave a searchable, sanitized local cause.

The packaged app has no request log and its stderr is discarded, so the profile
diagnostics file (and the query record) are the only surfaces that survive. Both
used to record nothing useful: the assist path replaced every failure with one
sentence, and the index path logged a type name to a handler-less logger.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.intake.review import IntakeReviewService
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import LLMProviderError
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "synthetic-record-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
TYPED = LLMProviderError(
    "模型服务返回错误：InsufficientBalance — Insufficient Balance",
    provider_code="InsufficientBalance",
    provider_message="Insufficient Balance",
    request_id="request-5",
    reason="provider",
)


class FailingProvider:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def organize(self, inputs: object) -> list[object]:  # noqa: ANN001
        raise self.error


def open_workspace(client: TestClient, root: Path) -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={"root": str(root), "mode": "create", "name": "模拟库", "operation_id": "ws"},
    )
    assert opened.status_code == 201, opened.text


def diagnostics_text(profile_root: Path) -> str:
    files = list(profile_root.rglob("diagnostics.log"))
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def diagnostics_events(profile_root: Path) -> list[dict[str, object]]:
    text = diagnostics_text(profile_root).strip()
    return [json.loads(line) for line in text.splitlines() if line]


def assist_client(tmp_path: Path, error: BaseException) -> TestClient:
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            review_service=IntakeReviewService(FailingProvider(error)),
            secret_backend=MemorySecretBackend(),
        )
    )


def test_typed_assist_failure_reports_and_records_the_reason(tmp_path: Path) -> None:
    client = assist_client(tmp_path, TYPED)
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "assistant_unavailable"
    assert "InsufficientBalance" in error["message"]
    assert "已保存内容未更改。" in error["message"]

    events = diagnostics_events(tmp_path / "profile")
    assert events[-1]["event"] == "assistant_failed"
    assert events[-1]["state"] == "failed"
    assert str(events[-1]["reason"]).startswith("模型服务返回错误：InsufficientBalance")


def test_unknown_assist_failure_keeps_the_safe_sentence_and_the_type_only(tmp_path: Path) -> None:
    sentinel = "credential-sentinel-assist"
    client = assist_client(tmp_path, RuntimeError(f"{sentinel} /private/profile"))
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    error = response.json()["error"]
    assert error["code"] == "assistant_unavailable"
    assert sentinel not in response.text
    assert "/private/profile" not in response.text
    assert "AI 辅助暂时不可用" in error["message"]

    text = diagnostics_text(tmp_path / "profile")
    assert sentinel not in text
    assert "/private/profile" not in text
    events = [json.loads(line) for line in text.strip().splitlines() if line]
    assert events[-1]["event"] == "assistant_failed"
    assert events[-1]["reason"] == "RuntimeError"


def test_failed_incremental_index_records_a_searchable_reason(tmp_path: Path) -> None:
    class FailingEmbedding(FakeEmbedding):
        fail = False

        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            if self.fail:
                raise RuntimeError("synthetic-private-probe embedding interruption")
            return super().embed(text, fingerprint=fingerprint)

    profile = tmp_path / "profile"
    embedding = FailingEmbedding()
    service = QueryService(IndexStore(profile / "index.sqlite3"), embedding=embedding)
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=service,
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "合成线", "operation_id": "line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    metadata = {
        "id": str(uuid4()),
        "title": "基线知识",
        "role": "knowledge",
        "kind": "topic",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    baseline = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": metadata,
            "body": "稳定内容琥珀四二。",
            "confirmation_id": "base-confirmation",
            "operation_id": "base-write",
        },
    )
    assert baseline.status_code == 201, baseline.text
    plan = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": "fake-failure-v1"},
    ).json()
    assert client.post("/api/v1/index/jobs", headers=HEADERS, json=plan).status_code == 200

    embedding.fail = True
    failed = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "中断知识"},
            "body": "新内容不应从旧索引引用独特词海蓝八六。",
            "confirmation_id": "new-confirmation",
            "operation_id": "new-write",
        },
    )
    assert failed.status_code == 201, failed.text
    assert failed.json()["index_update"] == "update_failed"

    events = diagnostics_events(profile)
    assert events[-1]["event"] == "index_update_failed"
    assert events[-1]["state"] == "failed"
    # Only the exception type is recorded: the sentinel text never reaches a file.
    assert events[-1]["reason"] == "RuntimeError"
    assert "synthetic-private-probe" not in diagnostics_text(profile)
