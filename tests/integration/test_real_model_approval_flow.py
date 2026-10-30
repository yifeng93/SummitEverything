"""End-to-end real-adapter path over a synthetic HTTP boundary only."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import summit_everything.api.app as app_module
import summit_everything.integrations.llm as llm_module
from summit_everything.integrations.acceptance_plans import AcceptancePlanLedger
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.local.retrieval_model import LocalRetrievalModelStore

HEADERS = {"Authorization": "Bearer synthetic-real-adapter-session"}
SOURCE = "青榆的访客登记须由前台核验姓名并记录来访时间。"


@pytest.mark.parametrize("usage_write_fails", [False, True])
def test_organize_index_and_query_use_confirmed_plans_and_real_adapters(
    tmp_path, monkeypatch, usage_write_fails: bool
):
    model_directory_value = os.environ.get("SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR", "")
    model_directory = Path(model_directory_value) if model_directory_value else None
    if not usage_write_fails and (model_directory is None or not model_directory.is_dir()):
        pytest.skip("set SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR to run the local-model approval flow")
    if not usage_write_fails:

        def reject_network(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("local retrieval attempted a network connection")

        monkeypatch.setattr(socket.socket, "connect", reject_network)
        monkeypatch.setattr(socket, "create_connection", reject_network)
    calls: list[tuple[str, dict[str, Any]]] = []
    closed_clients: list[bool] = []
    fail_next_chat = [False]

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
        if request.url.path.endswith("/chat/completions"):
            if fail_next_chat[0]:
                fail_next_chat[0] = False
                raise httpx.ReadTimeout("synthetic provider timeout")
            system = payload["messages"][0]["content"]
            if "Faithfully reorganize" in system:
                content = json.dumps(
                    {
                        "proposals": [
                            {
                                "title": "访客登记办法",
                                # The model may follow the old wording; the draft
                                # must still land as a valid page kind.
                                "kind": "fact",
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
    monkeypatch.setattr(llm_module, "create_http_client", new_client)
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
    if not usage_write_fails:
        workspace_id = opened.json()["workspace_id"]
        profile = (tmp_path / "profile" / workspace_id).resolve()
        assert model_directory is not None
        app.state.local_model_stores[str(profile)] = LocalRetrievalModelStore(
            profile / "retrieval-models", model_directory=model_directory
        )
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
            "embedding": {"provider": "local", "model": "BAAI/bge-small-zh-v1.5", "enabled": True},
            "rerank": {"provider": "local", "model": "BAAI/bge-small-zh-v1.5", "enabled": True},
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
    # Preview and confirmation planning are local-only. Until the user confirms,
    # the source remains without drafts and no adapter transport is invoked.
    assert calls == []
    assert client.get("/api/v1/drafts", headers=HEADERS).json() == []
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
    draft = client.get(f"/api/v1/drafts/{job.json()['draft_ids'][0]}", headers=HEADERS)
    assert draft.status_code == 200, draft.text
    assert draft.json()["metadata"]["kind"] == "topic"
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
    index_execute = client.post(
        "/api/v1/index/jobs",
        headers=HEADERS,
        json=local_index.json(),
    )
    assert index_execute.status_code == 200, index_execute.text
    assert index_execute.json()["indexed_chunks"] >= 1
    assert local_index.json()["estimated_cost"] == 0

    # Same-model local content changes are indexed incrementally without a paid plan.
    late_page = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {
                "id": "00000000-0000-4000-8000-000000000113",
                "title": "访客登记补充说明",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line.json()["id"],
                "project_id": project.json()["id"],
            },
            "body": "仅用于部分陈旧同指纹索引验证。",
            "confirmation_id": "confirm-late-page",
            "operation_id": "late-page",
        },
    )
    assert late_page.status_code == 201, late_page.text
    assert late_page.json()["index_update"] == "updated"
    partial_status = client.get("/api/v1/index/status", headers=HEADERS).json()
    assert partial_status["state"] == "ready"
    assert partial_status.get("reason") != "embedding_model_changed"

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
    stream_events = [
        json.loads(line.removeprefix("data: "))
        for line in query_result.text.splitlines()
        if line.startswith("data: {")
    ]
    citation_events = [item["data"] for item in stream_events if item["type"] == "citation"]
    assert citation_events
    citation_page = client.get(f"/api/v1/pages/{citation_events[0]['page_id']}", headers=HEADERS)
    assert citation_page.status_code == 200, citation_page.text
    assert citation_page.json()["content_sha256"] == citation_events[0]["content_sha256"]
    query_state = client.get(
        f"/api/v1/acceptance-plans/{query_preview['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert [item["provider"] for item in query_state["provider_usage"]] == ["deepseek"]
    assert all(
        item["request_id"].startswith("synthetic-") for item in query_state["provider_usage"]
    )

    model_calls = [item for item in calls if item[0].endswith("/chat/completions")]
    assert len(model_calls) == 2
    assert model_calls[0][1]["thinking"] == {"type": "disabled"}
    assert model_calls[1][1]["thinking"] == {"type": "enabled"}
    assert model_calls[1][1]["reasoning_effort"] == "low"
    assert model_calls[1][1]["max_tokens"] == 2048
    assert len(closed_clients) == 2

    journal_text = "合成日志：周三完成访客流程演练，遗留事项待确认。"
    before_journal = len(calls)
    unapproved = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": journal_text})
    assert unapproved.status_code == 409
    assert unapproved.json()["error"]["code"] == "acceptance_plan_required"
    assert len(calls) == before_journal

    journal_preview_response = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.journal_assist", "scope": {"text": journal_text}},
    )
    assert journal_preview_response.status_code == 201, journal_preview_response.text
    journal_preview = journal_preview_response.json()
    assert journal_preview["scope"]["text"] == journal_text
    assert journal_preview["scope"]["max_output_tokens"] == 2048
    journal_confirm = client.post(
        f"/api/v1/acceptance-plans/{journal_preview['plan']['plan_id']}/confirm",
        headers=HEADERS,
        json={
            "scope_sha256": journal_preview["plan"]["scope_sha256"],
            "scope": journal_preview["scope"],
        },
    )
    assert journal_confirm.status_code == 200, journal_confirm.text

    changed_text = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={
            "text": journal_text + " 越界附加内容。",
            "acceptance_plan_id": journal_preview["plan"]["plan_id"],
        },
    )
    assert changed_text.status_code == 409
    assert len(calls) == before_journal

    journal_response = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": journal_text, "acceptance_plan_id": journal_preview["plan"]["plan_id"]},
    )
    assert journal_response.status_code == 200, journal_response.text
    assert journal_response.json()["title"] == "访客登记办法"
    assert journal_response.json()["body"]
    journal_state = client.get(
        f"/api/v1/acceptance-plans/{journal_preview['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert journal_state["state"] == "succeeded"
    assert journal_state["requests_reserved"] == 1
    assert journal_state["provider_usage"][0]["request_id"].startswith("synthetic-")
    assert len(calls) == before_journal + 1
    journal_wire = calls[-1][1]
    assert journal_wire["max_tokens"] == 2048
    assert journal_wire["thinking"] == {"type": "disabled"}

    repeated = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": journal_text, "acceptance_plan_id": journal_preview["plan"]["plan_id"]},
    )
    assert repeated.status_code == 409
    assert len(calls) == before_journal + 1
    assert len(closed_clients) == 3

    def confirmed_journal_plan(text: str) -> dict[str, Any]:
        preview_response = client.post(
            "/api/v1/acceptance-plans",
            headers=HEADERS,
            json={"operation": "model.journal_assist", "scope": {"text": text}},
        )
        assert preview_response.status_code == 201, preview_response.text
        preview = preview_response.json()
        confirm_response = client.post(
            f"/api/v1/acceptance-plans/{preview['plan']['plan_id']}/confirm",
            headers=HEADERS,
            json={"scope_sha256": preview["plan"]["scope_sha256"], "scope": preview["scope"]},
        )
        assert confirm_response.status_code == 200, confirm_response.text
        return preview

    # Cancellation and a changed provider configuration both stop before the MockHTTP boundary.
    cancelled = confirmed_journal_plan("取消用合成日志正文")
    cancelled_delete = client.delete(
        f"/api/v1/acceptance-plans/{cancelled['plan']['plan_id']}", headers=HEADERS
    )
    assert cancelled_delete.status_code == 200
    assert cancelled_delete.json()["state"] == "cancelled"
    cancelled_execute = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": "取消用合成日志正文", "acceptance_plan_id": cancelled["plan"]["plan_id"]},
    )
    assert cancelled_execute.status_code == 409
    assert len(calls) == before_journal + 1
    changed_config_plan = confirmed_journal_plan("配置变化用合成日志正文")
    changed_config = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
                "reasoning_effort": "high",
                "max_output_tokens": 2048,
            }
        },
    )
    assert changed_config.status_code == 200, changed_config.text
    config_rejected = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={
            "text": "配置变化用合成日志正文",
            "acceptance_plan_id": changed_config_plan["plan"]["plan_id"],
        },
    )
    assert config_rejected.status_code == 409
    assert len(calls) == before_journal + 1
    restored_config = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
                "reasoning_effort": "low",
                "max_output_tokens": 2048,
            }
        },
    )
    assert restored_config.status_code == 200

    # A transport timeout consumes its reservation, closes the runtime client, and cannot replay.
    timeout_plan = confirmed_journal_plan("超时用合成日志正文")
    fail_next_chat[0] = True
    timeout_result = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": "超时用合成日志正文", "acceptance_plan_id": timeout_plan["plan"]["plan_id"]},
    )
    assert timeout_result.status_code == 502
    assert len(calls) == before_journal + 2
    timeout_state = client.get(
        f"/api/v1/acceptance-plans/{timeout_plan['plan']['plan_id']}", headers=HEADERS
    ).json()
    assert timeout_state["state"] == "unknown"
    assert timeout_state["requests_reserved"] == 1
    closed_after_timeout = len(closed_clients)
    timeout_replay = client.post(
        "/api/v1/journal/assist",
        headers=HEADERS,
        json={"text": "超时用合成日志正文", "acceptance_plan_id": timeout_plan["plan"]["plan_id"]},
    )
    assert timeout_replay.status_code == 409
    assert len(calls) == before_journal + 2
    assert len(closed_clients) == closed_after_timeout

    # Even a failed usage-ledger write must not leak the provider client.
    usage_failure_plan = confirmed_journal_plan("账本写入故障用合成日志正文")

    def fail_journal_usage(_ledger: AcceptancePlanLedger, _plan_id: Any, _usage: Any) -> None:
        raise RuntimeError("synthetic journal usage ledger failure")

    monkeypatch.setattr(AcceptancePlanLedger, "record_usage", fail_journal_usage)
    closed_before_usage_failure = len(closed_clients)
    with pytest.raises(RuntimeError, match="synthetic journal usage ledger failure"):
        client.post(
            "/api/v1/journal/assist",
            headers=HEADERS,
            json={
                "text": "账本写入故障用合成日志正文",
                "acceptance_plan_id": usage_failure_plan["plan"]["plan_id"],
            },
        )
    assert len(closed_clients) == closed_before_usage_failure + 1
