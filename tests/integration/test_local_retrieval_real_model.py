from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from integration.test_qualified_retrieval import approve_page, create_test_workspace

import summit_everything.integrations.llm as llm_module
from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import FakeEmbedding, LocalBgeEmbedding
from summit_everything.integrations.rerank import LocalSemanticReranker
from summit_everything.integrations.runtime import ModelRuntime
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.local.retrieval_model import LocalRetrievalModelStore
from summit_everything.retrieval.chunking import TextChunk
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project


def _model_path() -> Path:
    configured = os.environ.get("SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR")
    if not configured:
        pytest.skip("set SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR to run pinned local model probes")
    path = Path(configured)
    if not path.is_dir():
        pytest.skip("pinned local retrieval model is not present")
    return path


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_args, **_kwargs):
        raise AssertionError("local retrieval attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "create_connection", reject)


def test_pinned_local_model_retrieves_synonyms_inside_query_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    model = LocalBgeEmbedding(_model_path())
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    expected_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="青岚计划预算与排期",
        body="青岚计划可用预算上限为 19 万元；预计于 11 月启动。",
    )
    other_line = create_line(root, "其他模拟线", "other-line")
    other_project = create_project(root, other_line.id, "朱雀项目", "other-project")
    other_id, _ = approve_page(
        root,
        str(other_line.id),
        str(other_project.id),
        title="朱雀项目预算与排期",
        body="朱雀项目可用预算上限为 12 万元；预计于 12 月启动。",
    )
    fingerprint = "local-bge-real-query-probe"
    service = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        model,
        LocalSemanticReranker(model),
    )
    result = service.rebuild(root, fingerprint=fingerprint)
    assert result.indexed_pages == 2

    for question, quote in (
        ("青岚计划可动用的资金额度是多少？", "19 万元"),
        ("青岚计划在什么时候动工？", "预计于 11 月启动"),
        ("青岚计划预算 1000 元够不够？", "19 万元"),
    ):
        answer = service.query(root, question, fingerprint=fingerprint, limit=5)
        assert any(item.page_id == expected_id for item in answer.citations), question
        assert all(item.page_id == expected_id for item in answer.citations), question
        assert quote in " ".join(item.excerpt for item in answer.citations), question
    assert other_id != expected_id

    unrelated = service.query(
        root, "火星深海探测器使用哪种推进剂？", fingerprint=fingerprint, limit=5
    )
    assert unrelated.citations == []


def test_actual_tokenizer_windows_reach_tail_and_retain_exact_source_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _block_network(monkeypatch)
    model = LocalBgeEmbedding(_model_path())
    source = (
        "办理说明：访客设备要逐件登记、现场核验并在离场时归还。" * 230
        + "原文例子：访客𰻞字（合成）：费用 1800 元，项目A-01。"
        + "尾部事实：访客证章必须在西侧服务台领取，编号 Z-17。"
    )
    encoding = model._tokenizer.encode(source, add_special_tokens=False)
    assert len(encoding.ids) >= 1311
    windows = model._token_windows(source)
    exact_quote = "访客𰻞字（合成）：费用 1800 元，项目A-01。"
    tail_fact = "尾部事实：访客证章必须在西侧服务台领取，编号 Z-17。"
    assert all(text in source for text, _weight in windows)
    assert any(exact_quote in text for text, _weight in windows)
    assert tail_fact in windows[-1][0]
    assert len(windows) > len(encoding.ids) // model.window_tokens

    chunk = TextChunk(uuid4(), "a" * 64, "source", "办理", source)
    index_windows = model.split_for_index([chunk])
    assert all(item.text in source for item in index_windows)
    assert any(exact_quote in item.text for item in index_windows)
    assert tail_fact in index_windows[-1].text


def test_query_service_retrieves_and_cites_a_fact_from_the_long_text_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    model = LocalBgeEmbedding(_model_path())
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="访客办理总说明",
        body=(
            "办理提示：访客设备须逐件登记，服务人员应核验签字并在办理结束后回收。" * 240
            + "尾部规则：临时通行卡必须归还到西侧锁柜，柜号为 Z-17。"
        ),
    )
    fingerprint = "local-bge-real-long-tail-query-probe"
    service = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        model,
        LocalSemanticReranker(model),
    )
    plan = service.plan(root, fingerprint=fingerprint, mode="initial")
    assert plan.estimated_cost == 0
    assert service.execute_plan(root, plan).indexed_pages == 1

    answer = service.query(root, "临时通行卡应还到哪里？", fingerprint=fingerprint, limit=5)

    assert any(item.page_id == page_id for item in answer.citations)
    assert any("西侧锁柜" in item.excerpt and "Z-17" in item.excerpt for item in answer.citations)


def test_fake_index_requires_explicit_model_change_before_local_512_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ready local model must expose the fingerprint gate, not mask it as missing."""
    _block_network(monkeypatch)
    model_path = _model_path()
    token = "local-model-change-gate-test"
    profile_root = tmp_path / "profile"
    app = create_app(
        session_token=token,
        profile_root=profile_root,
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "隔离模型切换库",
            "operation_id": "model-change-workspace",
        },
    )
    assert opened.status_code == 201, opened.text
    workspace_id = opened.json()["workspace_id"]
    profile = (profile_root / workspace_id).resolve()
    app.state.local_model_stores[str(profile)] = LocalRetrievalModelStore(
        profile / "retrieval-models", model_directory=model_path
    )

    line = client.post(
        "/api/v1/lines", headers=headers, json={"name": "合成线", "operation_id": "line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    page_id = str(uuid4())
    page = client.post(
        "/api/v1/pages",
        headers=headers,
        json={
            "metadata": {
                "id": page_id,
                "title": "本地模型切换事实",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "切换模型验收使用的合成正文。",
            "confirmation_id": "confirm-model-change-page",
            "operation_id": "write-model-change-page",
        },
    )
    assert page.status_code == 201, page.text

    # Recreate a pre-real-only on-disk profile and its legacy fake index without
    # reopening the removed Fake settings API. Runtime still migrates it to real.
    settings_path = profile / "provider-settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        '{"mode":"fake","llm":{"provider":"fake","enabled":false},'
        '"embedding":{"provider":"fake","enabled":false},'
        '"rerank":{"provider":"fake","enabled":false}}',
        encoding="utf-8",
    )
    migrated = client.get("/api/v1/settings", headers=headers)
    assert migrated.status_code == 200, migrated.text
    assert migrated.json()["mode"] == "real"
    assert migrated.json()["legacy_provider_migration_required"] is True
    old_fingerprint = "summit-fake-embedding-v1"
    legacy_index = QueryService(IndexStore(profile / "index.sqlite3"), embedding=FakeEmbedding())
    legacy_index.rebuild(Path(tmp_path / "workspace"), fingerprint=old_fingerprint)

    local_settings = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "embedding": {"provider": "local", "model": "BAAI/bge-small-zh-v1.5", "enabled": True},
            "rerank": {"provider": "local", "model": "BAAI/bge-small-zh-v1.5", "enabled": True},
        },
    )
    assert local_settings.status_code == 200, local_settings.text
    assert local_settings.json()["local_model"]["state"] == "ready"
    new_fingerprint = local_settings.json()["embedding_fingerprint"]
    assert new_fingerprint != old_fingerprint

    stale_query = client.post(
        "/api/v1/queries",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "question": "模型切换验收内容是什么？",
            "fingerprint": old_fingerprint,
            "purpose": "current",
        },
    )
    assert stale_query.status_code == 409, stale_query.text
    assert stale_query.json()["error"]["code"] != "local_model_not_ready"

    rejected_old_generation = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "model_change", "fingerprint": old_fingerprint},
    )
    assert rejected_old_generation.status_code == 409, rejected_old_generation.text
    assert rejected_old_generation.json()["error"]["code"] != "local_model_not_ready"

    rebuild = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "model_change", "fingerprint": new_fingerprint},
    )
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["estimated_cost"] == 0
    executed = client.post("/api/v1/index/jobs", headers=headers, json=rebuild.json())
    assert executed.status_code == 200, executed.text
    status = client.get("/api/v1/index/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["state"] == "ready"
    assert status.json()["fingerprint"] == new_fingerprint


def test_mock_deepseek_approval_local_index_and_query_sse_closed_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    model_path = _model_path()
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload)
        system = payload["messages"][0]["content"]
        if "Faithfully reorganize" in system:
            content = json.dumps(
                {
                    "proposals": [
                        {
                            "title": "访客登记办法",
                            "kind": "topic",
                            "body": "青榆访客登记由前台核验姓名，并记录来访时间。",
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
                    "text": "青榆访客登记由前台核验姓名，并记录来访时间。",
                    "source_statements": ["青榆访客登记由前台核验姓名，并记录来访时间。"],
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
                "usage": {"prompt_tokens": 10, "completion_tokens": 16, "total_tokens": 26},
            },
            headers={"x-request-id": f"mock-deepseek-{len(calls)}"},
        )

    monkeypatch.setattr(
        ModelRuntime, "_credential", lambda _self, _provider, _account_id: "synthetic-deepseek-key"
    )
    monkeypatch.setattr(
        llm_module,
        "create_http_client",
        lambda **_kwargs: httpx.Client(transport=httpx.MockTransport(handler), trust_env=False),
    )

    token = "local-retrieval-closed-loop-test"
    profile_root = tmp_path / "profile"
    app = create_app(
        session_token=token,
        profile_root=profile_root,
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "隔离闭环库",
            "operation_id": "closed-loop-workspace",
        },
    )
    assert opened.status_code == 201, opened.text
    workspace_id = opened.json()["workspace_id"]
    profile = (profile_root / workspace_id).resolve()
    app.state.local_model_stores[str(profile)] = LocalRetrievalModelStore(
        profile / "retrieval-models", model_directory=model_path
    )
    settings = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
        },
    )
    assert settings.status_code == 200, settings.text

    line = client.post(
        "/api/v1/lines", headers=headers, json={"name": "合成线", "operation_id": "line"}
    )
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"line_id": line.json()["id"], "name": "青榆", "operation_id": "project"},
    )
    source = "青榆访客登记由前台核验姓名，并记录来访时间。"
    imported = client.post(
        "/api/v1/intake/items",
        headers=headers,
        json={"text": source, "filename": "synthetic.txt", "operation_id": "import"},
    )
    assert imported.status_code == 201, imported.text
    organize_scope = {
        "item_ids": [imported.json()["item_id"]],
        "operation_id": "organize-once",
        "line_id": line.json()["id"],
        "project_id": project.json()["id"],
        "reprocess": False,
    }
    organize_preview = client.post(
        "/api/v1/acceptance-plans",
        headers=headers,
        json={"operation": "model.organize", "scope": organize_scope},
    )
    assert organize_preview.status_code == 201, organize_preview.text
    organize = organize_preview.json()
    confirmed = client.post(
        f"/api/v1/acceptance-plans/{organize['plan']['plan_id']}/confirm",
        headers=headers,
        json={"scope_sha256": organize["plan"]["scope_sha256"], "scope": organize["scope"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    job = client.post(
        "/api/v1/intake/jobs",
        headers=headers,
        json={**organize_scope, "acceptance_plan_id": organize["plan"]["plan_id"]},
    )
    assert job.status_code == 201, job.text
    draft_id = job.json()["draft_ids"][0]
    approved = client.post(
        f"/api/v1/drafts/{draft_id}/confirmations",
        headers=headers,
        json={
            "expected_version": 1,
            "confirmation_id": "approve-draft",
            "operation_id": "approve-once",
        },
    )
    assert approved.status_code == 200, approved.text

    fingerprint = settings.json()["embedding_fingerprint"]
    index_plan = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "initial", "fingerprint": fingerprint},
    )
    assert index_plan.status_code == 200, index_plan.text
    assert index_plan.json()["estimated_cost"] == 0
    indexed = client.post("/api/v1/index/jobs", headers=headers, json=index_plan.json())
    assert indexed.status_code == 200, indexed.text

    question = "青榆访客登记怎样办理？"
    request_id = str(uuid4())
    query_scope = {
        "request_id": request_id,
        "question": question,
        "fingerprint": fingerprint,
        "purpose": "current",
        "answer_mode": "fact",
    }
    query_preview = client.post(
        "/api/v1/acceptance-plans",
        headers=headers,
        json={"operation": "model.query", "scope": query_scope},
    )
    assert query_preview.status_code == 201, query_preview.text
    assert query_preview.json()["plan"]["request_limit"] == 1
    query_plan = query_preview.json()
    query_confirm = client.post(
        f"/api/v1/acceptance-plans/{query_plan['plan']['plan_id']}/confirm",
        headers=headers,
        json={"scope_sha256": query_plan["plan"]["scope_sha256"], "scope": query_plan["scope"]},
    )
    assert query_confirm.status_code == 200, query_confirm.text
    answer = client.post(
        "/api/v1/queries",
        headers=headers,
        json={**query_scope, "acceptance_plan_id": query_plan["plan"]["plan_id"]},
    )
    assert answer.status_code == 200, answer.text
    events = [
        json.loads(line.removeprefix("data: "))
        for line in answer.text.splitlines()
        if line.startswith("data: {")
    ]
    citations = [event["data"] for event in events if event["type"] == "citation"]
    assert citations, answer.text
    assert len(calls) == 2
