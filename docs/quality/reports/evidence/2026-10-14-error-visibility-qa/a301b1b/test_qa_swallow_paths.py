"""Item 10 — other paths that still swallow a provider or exception reason.

Each ``test_finding_*`` asserts the *observed* behaviour of a301b1b so the
defect is reproducible from a green test run; the comment above the assertion
states what the finding is.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.runtime import ModelRuntime

import summit_everything.integrations.embedding as embedding_module
import summit_everything.integrations.llm as llm_module
import summit_everything.integrations.rerank as rerank_module

from qa_helpers import HEADERS, SENTINEL_KEY, SyntheticKeychain, configure_real_mode, json_response, open_workspace
from test_qa_provider_errors import (
    DASHSCOPE_403,
    OPENAI_401,
    _client,
    _install_transport,
    _ready_index_request,
    _workspace_with_one_page,
)


def test_finding_content_level_embedding_failure_is_a_bare_500(tmp_path, monkeypatch):
    """A 200 answer whose data is missing/duplicated still raises a bare ValueError.

    The typed ``EmbeddingProviderError`` handler covers provider-reported errors,
    but the content-validation branches still raise plain ``ValueError``, which no
    handler maps: the client gets an anonymous 500 and the reason is lost.
    """
    _install_transport(
        monkeypatch,
        lambda request: json_response({"model": "qwen3.7-text-embedding", "data": []}),
    )
    client = TestClient(
        create_app(
            session_token="qa-independent-session",
            profile_root=tmp_path / "profile",
            secret_backend=SyntheticKeychain(),
        ),
        raise_server_exceptions=False,
    )
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 500, response.status_code
    assert "provider_error" not in response.text


def test_finding_non_json_200_embedding_body_is_a_bare_500(tmp_path, monkeypatch):
    """A non-JSON 200 body also degrades to an anonymous 500."""
    _install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, content=b"<html>gateway</html>", headers={"content-type": "text/html"}
        ),
    )
    client = TestClient(
        create_app(
            session_token="qa-independent-session",
            profile_root=tmp_path / "profile",
            secret_backend=SyntheticKeychain(),
        ),
        raise_server_exceptions=False,
    )
    _workspace_with_one_page(client, tmp_path)
    payload = _ready_index_request(client)
    response = client.post("/api/v1/index/jobs", headers=HEADERS, json=payload)
    assert response.status_code == 500, response.status_code


def test_finding_journal_assist_swallows_the_provider_reason(tmp_path, monkeypatch):
    """``/api/v1/journal/assist`` replaces any LLMProviderError with a fixed sentence."""
    _install_transport(monkeypatch, lambda request: json_response(OPENAI_401, status=401))
    client = _client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    configure_real_mode(client)

    text = "合成日志正文。"
    preview = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.journal_assist", "scope": {"text": text}},
    )
    assert preview.status_code == 201, preview.text
    body = preview.json()
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{body['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": body["plan"]["scope_sha256"], "scope": body["scope"]},
    )
    assert confirmed.status_code == 200, confirmed.text

    response = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": text, "acceptance_plan_id": body["plan"]["plan_id"]},
    )
    assert response.status_code == 502, response.text
    # Finding: the typed provider code/message never reaches the client here,
    # unlike the query stream and the provider-smoke routes.
    assert "invalid_api_key" not in response.text, response.text
    assert "Invalid API-key provided." not in response.text, response.text


def test_finding_index_after_approval_hides_the_failure_reason(tmp_path, monkeypatch):
    """A local index update failure is reported as ``update_failed`` with no cause."""
    from summit_everything.retrieval.query import QueryService

    client = _client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA 线", "operation_id": "qa-line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "QA 项目", "operation_id": "qa-project"},
    ).json()

    # Give the workspace an active fingerprint, then make the local plan fail.
    fingerprint = client.get("/api/v1/settings", headers=HEADERS).json()["embedding_fingerprint"]
    plan = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": fingerprint},
    ).json()
    built = client.post("/api/v1/index/jobs", headers=HEADERS, json=plan)
    assert built.status_code == 200, built.text

    def boom(self: Any, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("sentinel local index failure /private/path")

    monkeypatch.setattr(QueryService, "plan", boom)
    response = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {
                "id": "55555555-5555-5555-5555-555555555555",
                "title": "QA 页",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "合成正文。",
            "confirmation_id": "qa-confirm-2",
            "operation_id": "qa-page-2",
        },
    )
    assert response.status_code == 201, response.text
    # Finding: the mutation still succeeds, but the index failure is a bare marker.
    assert response.json()["index_update"] == "update_failed", response.json()
    assert "sentinel" not in response.text


def test_finding_worker_job_records_the_raw_exception_text(tmp_path, monkeypatch):
    """The intake job record keeps ``str(exc)`` unmasked on the local disk."""
    _install_transport(
        monkeypatch,
        lambda request: json_response(
            {
                "error": {
                    "message": f"Invalid API-key provided. key={SENTINEL_KEY}",
                    "code": "invalid_api_key",
                }
            },
            status=401,
        ),
    )
    client = _client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    configure_real_mode(client)
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA 线", "operation_id": "qa-line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "QA 项目", "operation_id": "qa-project"},
    ).json()
    intake = client.post(
        "/api/v1/intake/items",
        headers=HEADERS,
        json={"text": "合成材料正文。", "filename": "qa.txt", "operation_id": "qa-intake"},
    )
    assert intake.status_code == 201, intake.text

    scope = {
        "item_ids": [intake.json()["item_id"]],
        "operation_id": "qa-organize",
        "line_id": line["id"],
        "project_id": project["id"],
        "reprocess": False,
    }
    preview = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.organize", "scope": scope},
    ).json()
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{preview['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": preview["plan"]["scope_sha256"], "scope": preview["scope"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    job = client.post(
        "/api/v1/intake/jobs",
        headers=HEADERS,
        json={**scope, "acceptance_plan_id": preview["plan"]["plan_id"]},
    )
    assert job.status_code == 503, job.text
    error = job.json()["error"]
    # The API response is sanitized and typed ...
    assert error["code"] == "provider_error"
    assert "invalid_api_key" in error["message"]
    assert SENTINEL_KEY not in job.text
    assert "sk-***" in job.text
    # ... but the local job record keeps the raw exception text (masked only by
    # luck of the adapter message, not by this writer).
    summaries = [
        path
        for path in (tmp_path / "workspace").rglob("summary.json")
        if path.parent.parent.name == "intake-jobs"
    ]
    assert summaries, "no archived intake-job summary was written"
    records = json.loads(summaries[0].read_text(encoding="utf-8"))["items"]
    failed = [entry["value"] for entry in records.values() if entry["value"]["state"] == "failed"]
    assert failed, records
    recorded = failed[0]
    assert SENTINEL_KEY not in recorded["error"], recorded["error"]
    assert "sk-***" in recorded["error"], recorded["error"]
    assert "模型服务返回错误" in recorded["error"]

    # Positive control: the organize path *is* diagnosable through the API.
    fetched = client.get(f"/api/v1/jobs/{recorded['job_id']}", headers=HEADERS)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["state"] == "failed"
    assert "invalid_api_key" in fetched.json()["error"]
