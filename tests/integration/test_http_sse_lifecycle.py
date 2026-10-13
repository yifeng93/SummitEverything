from __future__ import annotations

import asyncio
import gc
import json
import socket
import threading
import time
from pathlib import Path
from queue import Queue
from uuid import uuid4

import httpx
import uvicorn

from summit_everything.api.app import create_app
from summit_everything.integrations.llm import GroundedAnswer as ProviderAnswer
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore


class BlockingFakeAnswerProvider:
    """A synthetic provider that pauses only the final answer call."""

    def __init__(self) -> None:
        self.started: Queue[threading.Event] = Queue()

    def answer(self, question, passages, context) -> ProviderAnswer:  # type: ignore[no-untyped-def]
        release = threading.Event()
        self.started.put(release)
        if not release.wait(5):
            raise AssertionError("test provider was not released")
        return ProviderAnswer(text="基于合成资料的回答。")


class CaptureLoopExceptions:
    def __init__(self, app, errors: Queue[str]) -> None:  # type: ignore[no-untyped-def]
        self.app = app
        self.errors = errors

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        asyncio.get_running_loop().set_exception_handler(
            lambda _loop, context: self.errors.put(str(context.get("message", "loop error")))
        )
        await self.app(scope, receive, send)


def _first_event(lines) -> dict[str, object]:  # type: ignore[no-untyped-def]
    for line in lines:
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("SSE stream ended before its first event")


def test_live_http_sse_cancel_disconnect_and_reopen(tmp_path: Path) -> None:
    token = "synthetic-http-session-token"
    provider = BlockingFakeAnswerProvider()
    profile = tmp_path / "profile"
    query = QueryService(IndexStore(profile / "index.sqlite3"), answer_provider=provider)
    app = create_app(session_token=token, profile_root=profile, query_service=query)
    loop_errors: Queue[str] = Queue()
    app.add_middleware(CaptureLoopExceptions, errors=loop_errors)
    server_socket = socket.socket()
    server_socket.bind(("127.0.0.1", 0))
    port = server_socket.getsockname()[1]
    server_socket.close()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical", access_log=False)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if server.started:
                break
            time.sleep(0.01)
        assert server.started, "local HTTP test server did not become ready"
        with httpx.Client(base_url=base, headers=headers, timeout=5) as client:
            opened = client.post(
                "/api/v1/workspaces",
                json={
                    "root": str(tmp_path / "workspace"),
                    "mode": "create",
                    "name": "HTTP SSE 隔离库",
                    "operation_id": "http-sse-workspace",
                },
            )
            assert opened.status_code == 201, opened.text
            line = client.post(
                "/api/v1/lines", json={"name": "合成主线", "operation_id": "line"}
            ).json()
            project = client.post(
                "/api/v1/projects",
                json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
            ).json()
            page = client.post(
                "/api/v1/pages",
                json={
                    "metadata": {
                        "id": str(uuid4()),
                        "title": "橡果预算",
                        "role": "knowledge",
                        "kind": "topic",
                        "line_id": line["id"],
                        "project_id": project["id"],
                    },
                    "body": "橡果计划预算为 120 元。",
                    "confirmation_id": "approve-http-sse",
                    "operation_id": "page-http-sse",
                },
            )
            assert page.status_code == 201, page.text
            plan = client.post(
                "/api/v1/index/plans",
                json={"mode": "initial", "fingerprint": "summit-fake-embedding-v1"},
            )
            assert plan.status_code == 200, plan.text
            indexed = client.post("/api/v1/index/jobs", json=plan.json())
            assert indexed.status_code == 200, indexed.text
            assert indexed.json()["indexed_pages"] == 1

            cancel_id = str(uuid4())
            with client.stream(
                "POST",
                "/api/v1/queries",
                json={
                    "request_id": cancel_id,
                    "question": "橡果计划预算是多少？",
                    "fingerprint": "summit-fake-embedding-v1",
                    "purpose": "current",
                },
            ) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                lines = response.iter_lines()
                first = _first_event(lines)
                assert first["type"] == "status"
                release = provider.started.get(timeout=3)
                cancelled = client.delete(f"/api/v1/queries/{cancel_id}")
                assert cancelled.status_code == 202, cancelled.text
                release.set()
                rest = [line for line in lines if line.startswith("data: ")]
                terminal = [json.loads(line.removeprefix("data: ")) for line in rest]
                assert terminal[-1]["data"]["code"] == "cancelled"
                conversation_id = response.headers["x-conversation-id"]

            reopened = client.post(f"/api/v1/conversations/{conversation_id}/reopen", json={})
            assert reopened.status_code == 200
            assert reopened.json()["messages"][-1]["state"] == "cancelled"

            disconnect_id = str(uuid4())
            with client.stream(
                "POST",
                "/api/v1/queries",
                json={
                    "request_id": disconnect_id,
                    "question": "橡果计划预算是多少？",
                    "fingerprint": "summit-fake-embedding-v1",
                    "purpose": "current",
                },
            ) as response:
                assert response.status_code == 200
                lines = response.iter_lines()
                first = _first_event(lines)
                assert first["type"] == "status"
                release = provider.started.get(timeout=3)
                conversation_id = response.headers["x-conversation-id"]
                response.close()
            time.sleep(0.1)
            release.set()
            for _ in range(100):
                detail = client.get(f"/api/v1/conversations/{conversation_id}")
                if (
                    detail.status_code == 200
                    and detail.json()["messages"][-1]["state"] == "interrupted"
                ):
                    break
                time.sleep(0.02)
            assert detail.status_code == 200
            assert detail.json()["messages"][-1]["state"] == "interrupted"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive(), "local HTTP test server did not stop"
        gc.collect()
    assert loop_errors.empty(), list(loop_errors.queue)
