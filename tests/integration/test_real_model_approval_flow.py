"""End-to-end real-adapter path over a synthetic HTTP boundary only."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import summit_everything.api.app as app_module
import summit_everything.integrations.embedding as embedding_module
import summit_everything.integrations.llm as llm_module
import summit_everything.integrations.rerank as rerank_module
from summit_everything.integrations.acceptance_plans import AcceptancePlanLedger
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-real-adapter-session"}
SOURCE = "青榆的访客登记须由前台核验姓名并记录来访时间。"


@pytest.mark.parametrize("usage_write_fails", [False, True])
def test_organize_index_and_query_use_confirmed_plans_and_real_adapters(
    tmp_path, monkeypatch, usage_write_fails: bool
):
    calls: list[tuple[str, dict[str, Any]]] = []
    closed_clients: list[bool] = []

    class TrackedClient(httpx.Client):
        def __init__(self) -> None:
            super().__init__(transport=httpx.MockTransport(handler), trust_env=False)

        def close(self) -> None:
            if not self.is_closed:
                closed_clients.append(True)
            super().close()

    def new_client() -> TrackedClient:
        return TrackedClient()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer synthetic-adapter-key"
        payload = json.loads(request.content)
        calls.append((request.url.path, payload))
        if request.url.path.endswith("/embeddings"):
            vectors = [
                {"index": index, "embedding": [1.0] + [0.0] * 1023}
                for index, _text in enumerate(payload["input"])
            ]
            return httpx.Response(
                200,
                json={
                    "model": "qwen3.7-text-embedding",
                    "data": vectors,
                    "usage": {"total_tokens": 12},
                },
                headers={"x-request-id": f"synthetic-{len(calls):02d}"},
            )
        if request.url.path.endswith("/text-rerank"):
            documents = payload["input"]["documents"]
            return httpx.Response(
                200,
                json={
                    "output": {
                        "results": [
                            {"index": index, "relevance_score": 0.9 - index / 100}
                            for index in range(len(documents))
                        ]
                    },
                    "usage": {"prompt_tokens": 12, "total_tokens": 12},
                },
                headers={"x-request-id": f"synthetic-{len(calls):02d}"},
            )
        if request.url.path.endswith("/chat/completions"):
            system = payload["messages"][0]["content"]
            if "Faithfully reorganize" in system:
                content = json.dumps(
                    {
                        "proposals": [
                            {
                                "title": "访客登记办法",
                                "kind": "topic",
                                "body": (
                                    "## 访客登记\n\n"
                                    "青榆的访客登记须由前台核验姓名并记录来访时间。\n"
                                ),
                                "input_indexes": [0],
                                "important_conflicts": [],
                                "action_suggestions": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            else:
                content = json.dumps(
                    {
                        "text": "访客登记由前台核验姓名并记录来访时间。",
                        "source_statements": ["青榆的访客登记须由前台核验姓名并记录来访时间。"],
                        "inferences": [],
                        "advice": [],
                        "missing_information": [],
                    },
                    ensure_ascii=False,
                )
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": 14,
                        "completion_tokens": 20,
                        "total_tokens": 34,
                        "completion_tokens_details": {"reasoning_tokens": 2},
                    },
                },
                headers={"x-request-id": f"synthetic-{len(calls):02d}"},
            )
        raise AssertionError(f"unexpected synthetic model request: {request.url}")

    monkeypatch.setattr(
        ModelRuntime,
        "_credential",
        lambda _self, _provider, _account_id: "synthetic-adapter-key",
    )
    monkeypatch.setattr(embedding_module, "create_http_client", new_client)
    monkeypatch.setattr(llm_module, "create_http_client", new_client)
    monkeypatch.setattr(rerank_module, "create_http_client", new_client)
    if usage_write_fails:

        def fail_record_usage(_ledger: AcceptancePlanLedger, _plan_id: Any, _usage: Any) -> None:
            raise RuntimeError("synthetic usage ledger failure")

        monkeypatch.setattr(AcceptancePlanLedger, "record_usage", fail_record_usage)

    app = app_module.create_app(
        session_token="synthetic-real-adapter-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app, base_url="http://127.0.0.1:5173")
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "合成验收库",
            "operation_id": "open-workspace",
        },
    )
    assert opened.status_code == 201, opened.text
    settings = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "mode": "real",
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
                "reasoning_effort": "low",
                "max_output_tokens": 2048,
            },
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "enabled": True,
            },
            "rerank": {
                "provider": "dashscope",
                "model": "qwen3.7-text-rerank",
                "enabled": True,
            },
        },
    )
    assert settings.status_code == 200, settings.text

    line = client.post(
        "/api/v1/lines",
        headers=HEADERS,
        json={"name": "合成线", "operation_id": "line"},
    )
    assert line.status_code == 201, line.text
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={
            "line_id": line.json()["id"],
            "name": "青榆",
            "operation_id": "project",
        },
    )
    assert project.status_code == 201, project.text
    intake = client.post(
        "/api/v1/intake/items",
        headers=HEADERS,
        json={"text": SOURCE, "filename": "synthetic.txt", "operation_id": "intake"},
    )
    assert intake.status_code == 201, intake.text

    organize_scope = {
        "item_ids": [intake.json()["item_id"]],
        "operation_id": "organize-once",
        "line_id": line.json()["id"],
        "project_id": project.json()["id"],
        "reprocess": False,
    }
    organize_plan_response = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.organize", "scope": organize_scope},
    )
    assert organize_plan_response.status_code == 201, organize_plan_response.text
    organize_plan = organize_plan_response.json()
    organize_confirm = client.post(
        f"/api/v1/acceptance-plans/{organize_plan['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": organize_plan["plan"]["scope_sha256"],
            "scope": organize_plan["scope"],
        },
    )
    assert organize_confirm.status_code == 200, organize_confirm.text
    if usage_write_fails:
        with pytest.raises(RuntimeError, match="synthetic usage ledger failure"):
            client.post(
                "/api/v1/intake/jobs",
                headers=HEADERS,
                json={
                    **organize_scope,
                    "acceptance_plan_id": organize_plan["plan"]["plan_id"],
                },
            )
        assert len(closed_clients) == 1
        return

    job = client.post(
        "/api/v1/intake/jobs",
        headers=HEADERS,
        json={**organize_scope, "acceptance_plan_id": organize_plan["plan"]["plan_id"]},
    )
    assert job.status_code == 201, job.text
    assert job.json()["draft_ids"]
    assert calls[0][0].endswith("/chat/completions")
    assert calls[0][1]["thinking"] == {"type": "disabled"}
    organize_state = client.get(
        f"/api/v1/acceptance-plans/{organize_plan['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert organize_state["provider_usage"] == [
        {
            "provider": "deepseek",
            "request_id": "synthetic-01",
            "usage_reported": True,
            "input_tokens": 14,
            "output_tokens": 20,
            "total_tokens": 34,
        }
    ]

    draft_id = job.json()["draft_ids"][0]
    confirmed_draft = client.post(
        f"/api/v1/drafts/{draft_id}/confirmations",
        headers=HEADERS,
        json={
            "expected_version": 1,
            "confirmation_id": "synthetic-draft-confirmation",
            "operation_id": "confirm-synthetic-draft",
        },
    )
    assert confirmed_draft.status_code == 200, confirmed_draft.text

    embedding_fingerprint = settings.json()["embedding_fingerprint"]
    local_index = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": embedding_fingerprint},
    )
    assert local_index.status_code == 200, local_index.text
    index_plan_response = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={
            "operation": "model.index",
            "scope": {
                "mode": local_index.json()["mode"],
                "fingerprint": local_index.json()["fingerprint"],
                "page_ids": local_index.json()["page_ids"],
                "page_versions": local_index.json()["page_versions"],
            },
        },
    )
    assert index_plan_response.status_code == 201, index_plan_response.text
    index_preview = index_plan_response.json()
    index_confirm = client.post(
        f"/api/v1/acceptance-plans/{index_preview['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": index_preview["plan"]["scope_sha256"],
            "scope": index_preview["scope"],
        },
    )
    assert index_confirm.status_code == 200, index_confirm.text
    index_execute = client.post(
        "/api/v1/index/jobs",
        headers=HEADERS,
        json={
            **local_index.json(),
            "acceptance_plan_id": index_preview["plan"]["plan_id"],
        },
    )
    assert index_execute.status_code == 200, index_execute.text
    assert index_execute.json()["indexed_chunks"] >= 1
    index_state = client.get(
        f"/api/v1/acceptance-plans/{index_preview['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert index_state["provider_usage"][0]["provider"] == "qwen3.7-text-embedding"
    assert index_state["provider_usage"][0]["input_tokens"] is None
    assert index_state["provider_usage"][0]["total_tokens"] == 12
    assert len([path for path, _ in calls if path.endswith("/embeddings")]) == 1
    assert calls[1][0].endswith("/embeddings")

    request_id = "47f12779-9448-48b4-979a-e39d276b4e03"
    query_scope = {
        "request_id": request_id,
        "question": "青榆访客登记办法是什么",
        "fingerprint": embedding_fingerprint,
        "purpose": "current",
        "answer_mode": "fact",
    }
    query_preview_response = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.query", "scope": query_scope},
    )
    assert query_preview_response.status_code == 201, query_preview_response.text
    query_preview = query_preview_response.json()
    query_confirm = client.post(
        f"/api/v1/acceptance-plans/{query_preview['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": query_preview["plan"]["scope_sha256"],
            "scope": query_preview["scope"],
        },
    )
    assert query_confirm.status_code == 200, query_confirm.text
    query_result = client.post(
        "/api/v1/queries",
        headers=HEADERS,
        json={
            **query_scope,
            "acceptance_plan_id": query_preview["plan"]["plan_id"],
        },
    )
    assert query_result.status_code == 200, query_result.text
    assert "访客登记由前台核验姓名并记录来访时间" in query_result.text
    query_state = client.get(
        f"/api/v1/acceptance-plans/{query_preview['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert [item["provider"] for item in query_state["provider_usage"]] == [
        "qwen3.7-text-embedding",
        "qwen3.7-text-rerank",
        "deepseek",
    ]
    assert all(
        item["request_id"].startswith("synthetic-") for item in query_state["provider_usage"]
    )

    model_calls = [item for item in calls if item[0].endswith("/chat/completions")]
    assert len(model_calls) == 2
    assert model_calls[0][1]["thinking"] == {"type": "disabled"}
    assert model_calls[1][1]["thinking"] == {"type": "enabled"}
    assert model_calls[1][1]["reasoning_effort"] == "low"
    assert model_calls[1][1]["max_tokens"] == 2048
    assert len([path for path, _ in calls if path.endswith("/embeddings")]) == 2
    assert len([path for path, _ in calls if path.endswith("/text-rerank")]) == 1
    assert len(closed_clients) == 5
