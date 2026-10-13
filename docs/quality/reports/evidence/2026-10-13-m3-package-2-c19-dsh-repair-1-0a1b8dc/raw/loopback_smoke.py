from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

repo = Path.cwd()
with tempfile.TemporaryDirectory(prefix="c19-r1-loopback-") as temp:
    root = Path(temp) / "workspace"
    profile = Path(temp) / "profile"
    token = "synthetic-c19-loopback-token"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update({"SUMMIT_PROFILE_ROOT": str(profile), "SUMMIT_SESSION_TOKEN": token})
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "summit_everything.api.app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    def request(path: str, payload: dict | None = None, method: str | None = None) -> tuple[int, dict | str, dict[str, str]]:
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(
            base + path,
            data=data,
            method=method or ("POST" if data is not None else "GET"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=8) as response:
            raw = response.read().decode()
            content_type = response.headers.get("Content-Type", "")
            body = raw if content_type.startswith("text/event-stream") else json.loads(raw) if raw else {}
            return response.status, body, {key.lower(): value for key, value in response.headers.items()}

    def wait_ready() -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"uvicorn exited {process.returncode}: {process.stderr.read()}")
            try:
                request("/api/v1/health")
                return
            except (OSError, URLError):
                time.sleep(0.1)
        raise TimeoutError("loopback API did not become ready")

    try:
        wait_ready()
        status, workspace, _ = request(
            "/api/v1/workspaces",
            {"root": str(root), "mode": "create", "name": "C19 合成回归", "operation_id": "ws"},
        )
        assert status == 201, workspace
        _, line, _ = request("/api/v1/lines", {"name": "合成线", "operation_id": "line"})
        _, project_a, _ = request(
            "/api/v1/projects", {"line_id": line["id"], "name": "白萤会展", "operation_id": "project-a"}
        )
        _, project_b, _ = request(
            "/api/v1/projects", {"line_id": line["id"], "name": "岚桥计划", "operation_id": "project-b"}
        )
        for name, project, body in [
            ("信息登记", project_a, "白萤会展年度访客信息登记须记录访客姓名和到离时间。"),
            ("预算", project_b, "岚桥计划预算上限为六万元。"),
        ]:
            status, _, _ = request(
                "/api/v1/pages",
                {
                    "metadata": {
                        "id": str(uuid4()), "title": name, "role": "knowledge", "kind": "topic",
                        "line_id": line["id"], "project_id": project["id"],
                    },
                    "body": body, "confirmation_id": f"confirm-{name}", "operation_id": f"write-{name}",
                },
            )
            assert status == 201
        _, plan, _ = request("/api/v1/index/plans", {"mode": "initial", "fingerprint": "fake-c19-v1"})
        _, build, _ = request("/api/v1/index/jobs", plan)
        assert build["indexed_pages"] == 2

        def query(question: str, mode: str = "fact") -> tuple[list[dict], str]:
            status, body, headers = request(
                "/api/v1/queries",
                {"request_id": str(uuid4()), "question": question, "fingerprint": "fake-c19-v1", "answer_mode": mode},
            )
            assert status == 200 and isinstance(body, str)
            events = [json.loads(block.removeprefix("data: ").strip()) for block in body.split("\n\n") if block.startswith("data: ")]
            assert headers.get("content-type", "").startswith("text/event-stream")
            assert events[0]["type"] == "status" and events[-1]["type"] == "completed"
            return events, headers["x-conversation-id"]

        complete, conversation_id = query("白萤会展年度访客信息登记")
        assert any(event["type"] == "citation" for event in complete)
        assert not complete[-1]["data"]["missing_information"]
        reopened_status, history, _ = request(
            f"/api/v1/conversations/{conversation_id}/reopen", {}, method="POST"
        )
        assert reopened_status == 200
        assert history["messages"][0]["citations"]

        partial, _ = query("比较白萤会展年度访客信息登记与汀屿计划排期", "comparison")
        partial_data = partial[-1]["data"]
        assert any(event["type"] == "citation" for event in partial)
        assert any("汀屿计划" in item and "缺少" in item for item in partial_data["missing_information"])

        zero, _ = query("为彩色牙刷储存规则提出建议并列出缺失信息")
        zero_data = zero[-1]["data"]
        assert not any(event["type"] == "citation" for event in zero)
        assert zero_data["missing_information"] == ["彩色牙刷：缺少存储或保管规则依据。"]
        print(json.dumps({"loopback": "127.0.0.1", "complete": "PASS", "partial": "PASS", "zero": "PASS", "history_reopen": "PASS", "provider": "Fake", "real_data": "none"}, ensure_ascii=False))
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
