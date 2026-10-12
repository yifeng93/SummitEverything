from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx

API = "http://127.0.0.1:18793/api/v1"
PROFILE_B_API = "http://127.0.0.1:18795/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
BASE = Path(__file__).resolve().parents[1]
A_ROOT = str(BASE / "workspace-A")
B_ROOT = str(BASE / "workspace-C")


def state(client: httpx.Client) -> dict:
    workspace = client.get(API + "/workspaces/current").json()
    roles = client.get(API + "/roles").json()
    memories = client.get(API + "/memory").json()
    conversations = client.get(API + "/conversations?limit=100").json()["items"]
    questions: list[str] = []
    for item in conversations:
        detail = client.get(API + f"/conversations/{item['conversation_id']}").json()
        questions.extend(message["question"] for message in detail["messages"])
    return {
        "workspace_id": workspace["workspace_id"],
        "local_profile_dir": workspace["local_profile_dir"],
        "role_ids": [role["role_id"] for role in roles],
        "roles": [role["name"] for role in roles],
        "memory_ids": [memory["memory_id"] for memory in memories],
        "history_count": len(conversations),
        "questions": questions,
        "index": client.get(API + "/index/status").json()["state"],
    }


with httpx.Client(headers=HEADERS, timeout=30) as client, httpx.Client(
    headers=HEADERS, timeout=30
) as profile_b:
    profile_b_open = profile_b.post(
        PROFILE_B_API + "/workspaces",
        json={"root": A_ROOT, "mode": "open", "operation_id": "qa-c21-profile-b-same-workspace-r1b"},
    )
    assert profile_b_open.status_code == 201, (profile_b_open.status_code, profile_b_open.text)
    open_b = client.post(
        API + "/workspaces",
        json={"root": B_ROOT, "mode": "open", "operation_id": "qa-c21-workspace-b-open-r1b"},
    )
    before_b = state(client)
    role = client.post(
        API + "/roles",
        json={
            "name": "QA Workspace B role marker r1b",
            "instructions": "短句表达；不改变证据权限。",
            "context_budget": 200,
        },
    ).json()
    question = "我偏好工作库B里的短句回答 marker r1b。"
    fingerprint = client.get(API + "/settings").json()["embedding_fingerprint"]
    query = client.post(
        API + "/queries",
        json={
            "request_id": str(uuid.uuid4()),
            "question": question,
            "fingerprint": fingerprint,
            "answer_mode": "fact",
            "purpose": "current",
        },
    )
    first_event = json.loads(next(line[6:] for line in query.text.splitlines() if line.startswith("data: ")))
    candidate = client.post(
        API + "/memory/candidates",
        json={"message_id": first_event["request_id"], "text": question, "user_expression": True},
    ).json()
    memory = client.post(
        API + f"/memory/candidates/{candidate['candidate_id']}/confirmations",
        json={"confirmation_id": "qa-c21-workspace-memory-r1b", "text": question},
    ).json()
    populated_b = state(client)

    open_a = client.post(
        API + "/workspaces",
        json={"root": A_ROOT, "mode": "open", "operation_id": "qa-c21-workspace-a-open-r1b"},
    )
    workspace_a = state(client)
    return_b = client.post(
        API + "/workspaces",
        json={"root": B_ROOT, "mode": "open", "operation_id": "qa-c21-workspace-b-return-r1b"},
    )
    returned_b = state(client)

    profile_b_roles = profile_b.get(PROFILE_B_API + "/roles").json()
    profile_b_memories = profile_b.get(PROFILE_B_API + "/memory").json()
    profile_b_conversations = profile_b.get(PROFILE_B_API + "/conversations?limit=100").json()["items"]
    profile_b_questions: list[str] = []
    for item in profile_b_conversations:
        detail = profile_b.get(PROFILE_B_API + f"/conversations/{item['conversation_id']}").json()
        profile_b_questions.extend(message["question"] for message in detail["messages"])
    profile_b_path = profile_b.get(PROFILE_B_API + "/workspaces/current").json()["local_profile_dir"]

    workspace_marker_absent = (
        role["role_id"] not in workspace_a["role_ids"]
        and memory["memory_id"] not in workspace_a["memory_ids"]
        and question not in workspace_a["questions"]
    )
    profile_marker_absent = (
        not profile_b_roles
        and not profile_b_memories
        and question not in profile_b_questions
    )
    cleanup_memory = client.delete(API + f"/memory/{memory['memory_id']}").status_code
    cleanup_role = client.delete(API + f"/roles/{role['role_id']}").status_code

result = {
    "case": "C21-same-profile-workspace-switch-isolation",
    "open_http": [open_b.status_code, open_a.status_code, return_b.status_code],
    "workspace_b_before": {
        "workspace_id": before_b["workspace_id"],
        "roles": len(before_b["roles"]),
        "memories": len(before_b["memory_ids"]),
        "history": before_b["history_count"],
        "index": before_b["index"],
    },
    "workspace_a_during": {
        "workspace_id": workspace_a["workspace_id"],
        "role_names": workspace_a["roles"],
        "memory_count": len(workspace_a["memory_ids"]),
        "history_count": workspace_a["history_count"],
        "workspace_b_markers_absent": workspace_marker_absent,
        "index": workspace_a["index"],
        "profile_path": workspace_a["local_profile_dir"],
    },
    "workspace_b_after_return": {
        "workspace_id": returned_b["workspace_id"],
        "role_marker_present": role["role_id"] in returned_b["role_ids"],
        "memory_marker_present": memory["memory_id"] in returned_b["memory_ids"],
        "history_marker_present": question in returned_b["questions"],
        "index": returned_b["index"],
    },
    "profile_b_same_workspace_separate_local_state": {
        "profile_path": profile_b_path,
        "different_local_profile_path": profile_b_path != populated_b["local_profile_dir"],
        "roles": len(profile_b_roles),
        "memories": len(profile_b_memories),
        "history": len(profile_b_conversations),
        "workspace_b_marker_absent": profile_marker_absent,
    },
    "cleanup_http": {"memory": cleanup_memory, "role": cleanup_role},
}
result["status"] = (
    "PASS"
    if all(status == 201 for status in result["open_http"])
    and workspace_marker_absent
    and returned_b["workspace_id"] == populated_b["workspace_id"]
    and role["role_id"] in returned_b["role_ids"]
    and memory["memory_id"] in returned_b["memory_ids"]
    and question in returned_b["questions"]
    and profile_b_path != populated_b["local_profile_dir"]
    and profile_marker_absent
    and cleanup_memory == 204
    and cleanup_role == 204
    else "FAIL"
)
output = BASE / "harness" / "workspace-switch-results.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
