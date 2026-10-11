from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.domain.content import RetrievalPurpose
from summit_everything.domain.models import Answer
from summit_everything.local.conversations import ConversationStore, QueryStart
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "conversation-local-test-token"


def _open(api: TestClient, root: Path, *, op: str) -> dict[str, object]:
    mode = "open" if root.exists() else "create"
    response = api.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": mode, "name": op, "operation_id": op},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _events(response: object) -> list[dict[str, object]]:
    text = response.text
    return [
        json.loads(block.removeprefix("data: ").strip())
        for block in text.split("\n\n")
        if block.startswith("data: ")
    ]


def test_first_query_without_conversation_id_creates_and_reopens_server_conversation(
    tmp_path: Path,
) -> None:
    class CountingQuery(QueryService):
        calls = 0

        def query(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
            self.calls += 1
            return super().query(*args, **kwargs)  # type: ignore[arg-type]

    profile = tmp_path / "profile"
    service = CountingQuery(IndexStore(profile / "index.sqlite3"))
    api = TestClient(create_app(session_token=TOKEN, profile_root=profile, query_service=service))
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    workspace = tmp_path / "workspace"
    _open(api, workspace, op="create-ws")
    request_id = str(uuid4())
    payload = {
        "request_id": request_id,
        "question": "当前索引尚未就绪时会怎样？",
        "fingerprint": "fake-conversation-v1",
        "purpose": "current",
    }
    assert "conversation_id" not in payload

    first = api.post("/api/v1/queries", json=payload)
    first_events = _events(first)
    assert first.status_code == 200
    assert first_events[0]["type"] == "status"
    assert first_events[-1]["type"] == "completed"
    assert [event["seq"] for event in first_events] == list(range(1, len(first_events) + 1))
    assert service.calls == 1

    listed = api.get("/api/v1/conversations?limit=1")
    assert listed.status_code == 200
    conversation_id = listed.json()["items"][0]["conversation_id"]
    assert first.headers["x-conversation-id"] == conversation_id
    detail = api.post(f"/api/v1/conversations/{conversation_id}/reopen")
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["request_id"] == request_id
    assert detail.json()["messages"][0]["state"] == "completed"
    assert not list(workspace.rglob("conversations.sqlite3"))

    replay = api.post("/api/v1/queries", json=payload)
    assert _events(replay) == first_events
    assert service.calls == 1
    conflicting_retry = api.post(
        "/api/v1/queries", json={**payload, "question": "改了内容但重复 ID"}
    )
    assert conflicting_retry.status_code == 409

    second_profile = tmp_path / "second-profile"
    second_api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=second_profile,
            query_service=QueryService(IndexStore(second_profile / "index.sqlite3")),
        )
    )
    second_api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(second_api, workspace, op="same-workspace-second-profile")
    assert second_api.get("/api/v1/conversations").json()["items"] == []
    second_api.close()

    api.close()
    reopened_api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=QueryService(IndexStore(profile / "index.sqlite3")),
        )
    )
    reopened_api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(reopened_api, workspace, op="reopen-same-workspace")
    persisted = reopened_api.get(f"/api/v1/conversations/{conversation_id}")
    assert persisted.status_code == 200
    assert persisted.json()["messages"][0]["question"] == payload["question"]
    assert reopened_api.delete(f"/api/v1/conversations/{conversation_id}").status_code == 204
    assert reopened_api.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
    reopened_api.close()


def test_same_request_id_is_scoped_to_workspace_and_cancel_cannot_cross_workspace(
    tmp_path: Path,
) -> None:
    api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            query_service=QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3")),
        )
    )
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    request_id = str(uuid4())
    first_workspace = _open(api, tmp_path / "workspace-a", op="a")
    a = api.post(
        "/api/v1/queries",
        json={"request_id": request_id, "question": "A", "fingerprint": "fake"},
    )
    assert a.status_code == 200
    first_conversation = a.headers["x-conversation-id"]

    second_workspace = _open(api, tmp_path / "workspace-b", op="b")
    b = api.post(
        "/api/v1/queries",
        json={"request_id": request_id, "question": "B", "fingerprint": "fake"},
    )
    assert b.status_code == 200
    assert b.headers["x-conversation-id"] != first_conversation
    # A cancellation in the currently selected workspace cannot address A's history.
    assert api.delete(f"/api/v1/queries/{request_id}").status_code == 404
    _open(api, tmp_path / "workspace-a", op="switch-back-a")
    assert (
        api.get(f"/api/v1/conversations/{first_conversation}").json()["messages"][0]["question"]
        == "A"
    )
    assert first_workspace["workspace_id"] != second_workspace["workspace_id"]
    api.close()


def test_cancel_from_other_workspace_does_not_touch_active_query(tmp_path: Path) -> None:
    started = Event()
    release = Event()

    class BlockingQuery(QueryService):
        def query(
            self,
            root,
            question,
            *,
            fingerprint,
            purpose=RetrievalPurpose.CURRENT,
            limit=5,
            cancelled=None,
        ):
            del root, fingerprint, limit
            started.set()
            assert release.wait(3)
            if cancelled is not None and cancelled.is_set():
                from summit_everything.retrieval.query import QueryCancelled

                raise QueryCancelled
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="仍在第一本库中的完整回答。",
                purpose=purpose.value,
                index_status="ready",
            )

    profile = tmp_path / "profile"
    api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=BlockingQuery(IndexStore(profile / "index.sqlite3")),
        )
    )
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(api, tmp_path / "workspace-a", op="a")
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            api.post,
            "/api/v1/queries",
            json={"request_id": request_id, "question": "A", "fingerprint": "fake"},
        )
        assert started.wait(1)
        _open(api, tmp_path / "workspace-b", op="b")
        assert api.delete(f"/api/v1/queries/{request_id}").status_code == 404
        release.set()
        response = pending.result(timeout=3)
    assert _events(response)[-1]["type"] == "completed"
    _open(api, tmp_path / "workspace-a", op="switch-back")
    detail = api.get(f"/api/v1/conversations/{response.headers['x-conversation-id']}").json()
    assert detail["messages"][0]["state"] == "completed"
    api.close()


def test_running_query_recovery_preserves_live_work_and_marks_dead_attempt_interrupted(
    tmp_path: Path,
) -> None:
    store = ConversationStore(tmp_path / "profile" / "conversations.sqlite3")
    workspace_id = uuid4()
    live_request = uuid4()
    created, conversation_id = store.begin(
        workspace_id,
        QueryStart(
            request_id=live_request,
            question="在途",
            fingerprint="fake",
            purpose="current",
        ),
    )
    assert created
    key = (str(store.path.resolve()), str(workspace_id), str(live_request))
    from summit_everything.local.conversations import ACTIVE_QUERIES

    ACTIVE_QUERIES.add(key)
    try:
        store.recover_interrupted(workspace_id)
        assert store.get(workspace_id, conversation_id).messages[0].state == "running"  # type: ignore[union-attr]
    finally:
        ACTIVE_QUERIES.discard(key)

    dead_request = uuid4()
    _, dead_conversation = store.begin(
        workspace_id,
        QueryStart(
            request_id=dead_request,
            question="中断",
            fingerprint="fake",
            purpose="current",
        ),
    )
    store.append_event(
        workspace_id,
        dead_request,
        "status",
        {"state": "retrieving", "conversation_id": str(dead_conversation)},
    )
    store.append_event(workspace_id, dead_request, "delta", {"text": "真实部分"})
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE queries SET owner_pid=? WHERE workspace_id=? AND request_id=?",
            (99_999_999, str(workspace_id), str(dead_request)),
        )
    store.recover_interrupted(workspace_id)
    recovered = store.get(workspace_id, dead_conversation)
    assert recovered is not None
    assert recovered.messages[0].state == "interrupted"
    assert recovered.messages[0].answer == "真实部分"
    assert (
        store.terminate(workspace_id, dead_request, "completed", {"text": "假完整"}, "completed")
        is None
    )


def test_query_cannot_implicitly_reopen_missing_conversation_and_paging_is_bounded(
    tmp_path: Path,
) -> None:
    api = TestClient(create_app(session_token=TOKEN, profile_root=tmp_path / "profile"))
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(api, tmp_path / "workspace", op="create")
    missing = api.post(
        "/api/v1/queries",
        json={
            "conversation_id": str(uuid4()),
            "question": "not found",
            "fingerprint": "fake",
        },
    )
    assert missing.status_code == 404
    assert api.get("/api/v1/conversations?limit=0").status_code == 422
    api.close()


def test_conversation_list_uses_cursor_pages_without_duplicates(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=QueryService(IndexStore(profile / "index.sqlite3")),
        )
    )
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(api, tmp_path / "workspace", op="create")
    first = api.post(
        "/api/v1/queries",
        json={"request_id": str(uuid4()), "question": "先问", "fingerprint": "fake"},
    )
    second = api.post(
        "/api/v1/queries",
        json={"request_id": str(uuid4()), "question": "再问", "fingerprint": "fake"},
    )
    assert first.status_code == second.status_code == 200
    page_one = api.get("/api/v1/conversations?limit=1").json()
    assert len(page_one["items"]) == 1
    assert page_one["next_cursor"]
    page_two = api.get(
        "/api/v1/conversations", params={"limit": 1, "cursor": page_one["next_cursor"]}
    ).json()
    assert len(page_two["items"]) == 1
    assert page_two["next_cursor"] is None
    assert page_one["items"][0]["conversation_id"] != page_two["items"][0]["conversation_id"]
    assert api.get("/api/v1/conversations?cursor=malformed&limit=20").status_code == 422
    api.close()
