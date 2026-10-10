from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.domain.content import RetrievalPurpose
from summit_everything.domain.models import Answer
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "m1-lifecycle-token"


def test_failed_automatic_incremental_index_is_visible_and_stale_chunks_are_rejected(
    tmp_path: Path,
) -> None:
    class FailingEmbedding(FakeEmbedding):
        fail = False

        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            if self.fail:
                raise RuntimeError("synthetic Fake embedding interruption")
            return super().embed(text, fingerprint=fingerprint)

    profile = tmp_path / "profiles"
    embedding = FailingEmbedding()
    service = QueryService(IndexStore(profile / "index.sqlite3"), embedding=embedding)
    api = TestClient(create_app(session_token=TOKEN, profile_root=profile, query_service=service))
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    root = tmp_path / "workspace"
    opened = api.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": "create", "name": "索引中断模拟", "operation_id": "ws"},
    )
    assert opened.status_code == 201, opened.text
    line = api.post("/api/v1/lines", json={"name": "合成线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    baseline = api.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": str(uuid4()),
                "title": "基线知识",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "稳定内容琥珀四二。",
            "confirmation_id": "base-confirmation",
            "operation_id": "base-write",
        },
    )
    assert baseline.status_code == 201
    assert baseline.json()["index_update"] == "not_enabled"
    initial = api.post(
        "/api/v1/index/plans", json={"mode": "initial", "fingerprint": "fake-failure-v1"}
    ).json()
    assert api.post("/api/v1/index/jobs", json=initial).status_code == 200

    embedding.fail = True
    new_page = api.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": str(uuid4()),
                "title": "中断知识",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "新内容不应从旧索引引用独特词海蓝八六。",
            "confirmation_id": "new-confirmation",
            "operation_id": "new-write",
        },
    )
    assert new_page.status_code == 201
    assert new_page.json()["index_update"] == "update_failed"
    status = api.get("/api/v1/index/status").json()
    assert status["state"] == "stale" and status["stale_pages"] == 1

    events_response = api.post(
        "/api/v1/queries",
        json={"question": "海蓝八六是什么", "fingerprint": "fake-failure-v1", "purpose": "current"},
    )
    events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in events_response.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert not any(event["type"] == "citation" for event in events)


def test_api_index_query_and_stale_citation_lifecycle(tmp_path: Path) -> None:
    api = TestClient(create_app(session_token=TOKEN, profile_root=tmp_path / "profiles"))
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    root = tmp_path / "workspace"
    response = api.post(
        "/api/v1/workspaces",
        json={
            "root": str(root),
            "mode": "create",
            "name": "隔离验收库",
            "operation_id": "create",
        },
    )
    assert response.status_code == 201, response.text
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    page_id = str(uuid4())
    page = api.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": page_id,
                "title": "模拟地点",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "银杏项目的会议地点是北馆。",
            "confirmation_id": "approve-v1",
            "operation_id": "page-v1",
        },
    )
    assert page.status_code == 201, page.text
    fingerprint = "fake-embedding-v1"
    plan = api.post("/api/v1/index/plans", json={"mode": "initial", "fingerprint": fingerprint})
    assert plan.status_code == 200, plan.text
    built = api.post("/api/v1/index/jobs", json=plan.json())
    assert built.status_code == 200, built.text
    assert built.json()["indexed_pages"] == 1

    answer = api.post(
        "/api/v1/queries",
        json={"question": "银杏项目会议地点", "fingerprint": fingerprint, "purpose": "current"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.headers["content-type"].startswith("text/event-stream")
    events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in answer.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert [event["type"] for event in events][0] == "status"
    assert [event["type"] for event in events][-1] == "completed"
    assert sum(event["type"] in {"completed", "error"} for event in events) == 1
    citation = next(event["data"] for event in events if event["type"] == "citation")
    assert citation["page_id"] == page_id

    current_page = api.get(f"/api/v1/pages/{page_id}").json()
    update = api.post(
        f"/api/v1/pages/{page_id}/confirmations",
        json={
            "metadata": current_page["metadata"],
            "body": "银杏项目的会议地点已改为西馆。",
            "confirmation_id": "approve-v2",
            "operation_id": "page-v2",
            "expected_base_sha256": current_page["content_sha256"],
        },
    )
    assert update.status_code == 200, update.text
    assert update.json()["index_update"] == "updated"
    assert api.get("/api/v1/index/status").json()["state"] == "ready"
    fresh = api.post(
        "/api/v1/queries",
        json={"question": "银杏项目会议地点", "fingerprint": fingerprint, "purpose": "current"},
    )
    fresh_events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in fresh.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert any(event["type"] == "citation" for event in fresh_events)
    assert "西馆" in fresh.text
    assert "北馆" not in fresh.text


def test_query_cancel_emits_terminal_error_without_completed_answer(tmp_path: Path) -> None:
    started = Event()
    release = Event()

    class BlockingQuery(QueryService):
        def query(self, root, question, *, fingerprint, purpose=RetrievalPurpose.CURRENT, limit=5):
            started.set()
            assert release.wait(3)
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="这段回答在取消后不应标为完成。",
                purpose=purpose.value,
                index_status="ready",
            )

    query_service = BlockingQuery(IndexStore(tmp_path / "profile" / "index.sqlite3"))
    app = create_app(
        session_token=TOKEN,
        profile_root=tmp_path / "profiles",
        query_service=query_service,
    )
    api = TestClient(app)
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    root = tmp_path / "workspace"
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(root),
                "mode": "create",
                "name": "隔离取消库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    request_id = str(uuid4())

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            api.post,
            "/api/v1/queries",
            json={
                "question": "模拟问题",
                "fingerprint": "fake-v1",
                "request_id": request_id,
            },
        )
        assert started.wait(1)
        cancelled = api.delete(f"/api/v1/queries/{request_id}")
        assert cancelled.status_code == 202
        release.set()
        response = pending.result(timeout=3)

    events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in response.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert events[-1]["type"] == "error"
    assert events[-1]["data"]["code"] == "cancelled"
    assert not any(event["type"] == "completed" for event in events)


def test_external_edit_can_be_reconfirmed_from_current_page_snapshot(tmp_path: Path) -> None:
    token = "m1-reconfirm-token"
    store = IndexStore(tmp_path / "profile" / "index.sqlite3")
    query_service = QueryService(store)
    app = create_app(
        session_token=token,
        profile_root=tmp_path / "profiles",
        query_service=query_service,
    )
    api = TestClient(app)
    api.headers.update({"Authorization": f"Bearer {token}"})
    root = tmp_path / "workspace"
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(root),
                "mode": "create",
                "name": "重新确认模拟库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    page_id = "00000000-0000-4000-8000-000000000902"
    metadata = {
        "id": page_id,
        "title": "模拟事实",
        "role": "knowledge",
        "kind": "topic",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    assert (
        api.post(
            "/api/v1/pages",
            json={
                "metadata": metadata,
                "body": "蓝松项目预算是 123 元。",
                "confirmation_id": "approve-v1",
                "operation_id": "page-v1",
            },
        ).status_code
        == 201
    )
    fingerprint = "fake-reconfirm-v1"
    plan = api.post(
        "/api/v1/index/plans", json={"mode": "initial", "fingerprint": fingerprint}
    ).json()
    assert api.post("/api/v1/index/jobs", json=plan).status_code == 200
    snapshot = api.get(f"/api/v1/pages/{page_id}").json()
    path = root / snapshot["relative_path"]
    path.write_text(path.read_text(encoding="utf-8").replace("123 元", "999 元"), encoding="utf-8")

    changed = api.get(f"/api/v1/pages/{page_id}").json()
    stale = api.post(
        "/api/v1/queries",
        json={"question": "蓝松项目预算", "fingerprint": fingerprint, "purpose": "current"},
    )
    stale_events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in stale.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert changed["approval_state"] == "invalid"
    assert not any(event["type"] == "citation" for event in stale_events)

    confirmation = api.post(
        f"/api/v1/pages/{page_id}/confirmations",
        json={
            "metadata": changed["metadata"],
            "body": changed["body"] + "\n已按外部合同复核。",
            "expected_base_sha256": changed["content_sha256"],
            "confirmation_id": "approve-current-v2",
            "operation_id": "page-v2",
        },
    )
    assert confirmation.status_code == 200, confirmation.text
    assert confirmation.json()["index_update"] == "updated"
    assert api.get(f"/api/v1/pages/{page_id}").json()["approval_state"] == "confirmed"
    current = api.post(
        "/api/v1/queries",
        json={"question": "蓝松项目预算", "fingerprint": fingerprint, "purpose": "current"},
    )
    current_events = [
        json.loads(block.removeprefix("data: ").strip())
        for block in current.text.split("\n\n")
        if block.startswith("data: ")
    ]
    assert any(event["type"] == "citation" for event in current_events)
    assert "999 元" in current.text
    assert "123 元" not in current.text
