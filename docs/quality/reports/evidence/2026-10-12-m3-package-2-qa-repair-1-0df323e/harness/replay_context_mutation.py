from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:18793/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
CAPTURE = BASE / "harness" / "deepseek-payloads.jsonl"


def events(response: httpx.Response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def capture_count() -> int:
    return len(CAPTURE.read_text(encoding="utf-8").splitlines()) if CAPTURE.exists() else 0


with httpx.Client(headers=HEADERS, timeout=30) as client:
    fingerprint = client.get(API + "/settings").json()["embedding_fingerprint"]
    role = client.post(
        API + "/roles",
        json={"name": "QA Replay Mutation", "instructions": "初始短句风格。", "context_budget": 200},
    ).json()
    source_text = "我偏好在回放验收中把事实和建议分开。"
    source_response = client.post(
        API + "/queries",
        json={
            "request_id": str(uuid.uuid4()),
            "question": source_text,
            "fingerprint": fingerprint,
            "answer_mode": "fact",
            "purpose": "current",
        },
    )
    source_events = events(source_response)
    source_request = source_events[0]["request_id"]
    conversation_id = source_events[0]["data"]["conversation_id"]
    candidate = client.post(
        API + "/memory/candidates",
        json={"message_id": source_request, "text": source_text, "user_expression": True},
    ).json()
    memory = client.post(
        API + f"/memory/candidates/{candidate['candidate_id']}/confirmations",
        json={"confirmation_id": "qa-replay-context-confirm-v1", "text": source_text},
    ).json()

    request = {
        "request_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "question": "青岚计划目前的预算上限是多少？",
        "fingerprint": fingerprint,
        "answer_mode": "fact",
        "purpose": "current",
        "role_id": role["role_id"],
    }
    initial_count = capture_count()
    initial = client.post(API + "/queries", json=request)
    initial_events = events(initial)
    after_initial = capture_count()
    client.patch(
        API + f"/roles/{role['role_id']}",
        json={"name": role["name"], "instructions": "编辑后的表达风格；仍不能改证据权限。", "context_budget": 200},
    )
    client.patch(
        API + f"/memory/{memory['memory_id']}",
        json={"text": "我偏好编辑后也把事实和建议分开。"},
    )
    replay = client.post(API + "/queries", json=request)
    replay_events = events(replay)
    after_replay = capture_count()
    conflict = client.post(API + "/queries", json={**request, "answer_mode": "comparison"})
    deleted_memory = client.delete(API + f"/memory/{memory['memory_id']}")
    deleted_role = client.delete(API + f"/roles/{role['role_id']}")
    result = {
        "case": "C14-same-request-replay-after-role-and-memory-edit",
        "source_http": source_response.status_code,
        "initial_http": initial.status_code,
        "replay_http": replay.status_code,
        "same_events": initial_events == replay_events,
        "same_event_types": [event["type"] for event in initial_events] == [event["type"] for event in replay_events],
        "provider_calls_before_initial": initial_count,
        "provider_calls_after_initial": after_initial,
        "provider_calls_after_replay": after_replay,
        "different_mode_conflict_http": conflict.status_code,
        "delete_http": {"memory": deleted_memory.status_code, "role": deleted_role.status_code},
        "status": "PASS"
        if source_response.status_code == 200
        and initial.status_code == 200
        and replay.status_code == 200
        and initial_events == replay_events
        and after_initial == initial_count + 1
        and after_replay == after_initial
        and conflict.status_code == 409
        and deleted_memory.status_code == 204
        and deleted_role.status_code == 204
        else "FAIL",
    }
output = BASE / "harness" / "replay-context-results.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
