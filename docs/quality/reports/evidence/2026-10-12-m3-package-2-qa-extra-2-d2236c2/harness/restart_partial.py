from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
APP_SOURCE = BASE_DIR / "harness" / "app_factory.py"
APP_COPY = BASE_DIR / "harness" / "stream_recovery_app.py"
APP_COPY.write_text(
    APP_SOURCE.read_text(encoding="utf-8")
    .replace('PROFILE_A = BASE / "profiles-A"', 'PROFILE_A = BASE / "profiles-R"')
    .replace('PROFILE_B = BASE / "profiles-B"', 'PROFILE_B = BASE / "profiles-S"'),
    encoding="utf-8",
)
for path in (BASE_DIR / "profiles-R", BASE_DIR / "profiles-S"):
    shutil.rmtree(path, ignore_errors=True)

port = 18796
api = f"http://127.0.0.1:{port}/api/v1"
token = os.environ["QA_M3_SESSION_TOKEN"]
headers = {"Authorization": f"Bearer {token}"}
env = os.environ.copy()
env.update(
    {
        "QA_M3_BASE": str(BASE_DIR),
        "QA_M3_SESSION_TOKEN": token,
        "QA_M3_WORKSPACE": str(BASE_DIR / "workspace-A"),
        "PYTHONPATH": os.pathsep.join(
            [str(BASE_DIR / "harness"), str(ROOT / "src"), env.get("PYTHONPATH", "")]
        ),
    }
)
log = (BASE_DIR / "raw-logs" / "partial-recovery-uvicorn.log").open("w", encoding="utf-8")
command = [sys.executable, "-m", "uvicorn", "stream_recovery_app:app", "--host", "127.0.0.1", "--port", str(port)]


def start() -> subprocess.Popen:
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"uvicorn exited early: {process.returncode}")
        try:
            httpx.get(api + "/workspaces/current", headers=headers, timeout=0.5)
            return process
        except httpx.HTTPError:
            time.sleep(0.1)
    raise TimeoutError("uvicorn readiness timeout")


process = start()
try:
    with httpx.Client(headers=headers, timeout=20) as client:
        opened = client.post(
            api + "/workspaces",
            json={
                "root": str(BASE_DIR / "workspace-A"),
                "mode": "open",
                "operation_id": "qa-partial-recovery-open-r2",
            },
        )
        assert opened.status_code == 201, (opened.status_code, opened.text)
        fingerprint = client.get(api + "/settings").json()["embedding_fingerprint"]
        request_id = str(uuid.uuid4())
        payload = {
            "request_id": request_id,
            "question": "青岚计划的预算上限是多少？",
            "fingerprint": fingerprint,
            "purpose": "current",
        }
        seen: list[dict] = []
        partial_chars = 0
        with client.stream("POST", api + "/queries", json=payload) as response:
            assert response.status_code == 200, (response.status_code, response.read().decode())
            conversation_id = response.headers["x-conversation-id"]
            for line in response.iter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    seen.append(event)
                    if event["type"] == "delta":
                        partial_chars += len(event.get("data", {}).get("text", ""))
                        if partial_chars:
                            os.kill(process.pid, signal.SIGKILL)
                            process.wait(timeout=5)
                            break
        assert partial_chars > 0, {"events": [e["type"] for e in seen], "partial_chars": partial_chars}
        assert not any(e["type"] in {"completed", "error"} for e in seen)

    process = start()
    with httpx.Client(headers=headers, timeout=20) as client:
        opened = client.post(
            api + "/workspaces",
            json={
                "root": str(BASE_DIR / "workspace-A"),
                "mode": "open",
                "operation_id": "qa-partial-recovery-reopen-r2",
            },
        )
        assert opened.status_code == 201, (opened.status_code, opened.text)
        detail = client.get(api + f"/conversations/{conversation_id}").json()
        message = next(row for row in detail["messages"] if row["request_id"] == request_id)
        assert message["state"] == "interrupted", message
        assert message["answer"] and len(message["answer"]) == partial_chars, message
        assert not any(e["type"] in {"completed", "error"} for e in message["events"])
        replay = client.post(api + "/queries", json=payload)
        assert replay.status_code == 200, (replay.status_code, replay.text)
        events = [
            json.loads(line[6:])
            for line in replay.text.splitlines()
            if line.startswith("data: ")
        ]
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1)), events
        assert len(events) == len(message["events"]), (len(events), len(message["events"]))
        assert not any(e["type"] in {"completed", "error"} for e in events)
        detail_after = client.get(api + f"/conversations/{conversation_id}").json()
        after = next(row for row in detail_after["messages"] if row["request_id"] == request_id)
        assert after["state"] == "interrupted" and after["answer"] == message["answer"]
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "partial_answer_chars": partial_chars,
                    "first_connection_events": [e["type"] for e in seen],
                    "replay_event_types": [e["type"] for e in events],
                    "state_after_restart_and_replay": after["state"],
                },
                ensure_ascii=False,
            )
        )
finally:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    log.close()
