from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parents[1]
TOKEN = os.environ["QA_M3_SESSION_TOKEN"]
WORKSPACE = str(BASE / "workspace-B")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
A = "http://127.0.0.1:18793/api/v1"
B = "http://127.0.0.1:18795/api/v1"
CAPTURE = BASE / "harness" / "deepseek-payloads.jsonl"
results: list[dict] = []


def record(name: str, status: str, detail: object) -> None:
    results.append({"case": name, "status": status, "detail": detail})


def sse(resp: httpx.Response) -> list[dict]:
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def get_conversations(client: httpx.Client) -> list[dict]:
    return client.get(A + "/conversations?limit=100").json()["items"]


with httpx.Client(headers=HEADERS, timeout=15) as ca, httpx.Client(headers=HEADERS, timeout=15) as cb:
    opened = cb.post(B + "/workspaces", json={"root": WORKSPACE, "mode": "open", "operation_id": "qa-profile-b-open"})
    record("C21-profile-B-open", "PASS" if opened.status_code == 201 else "FAIL", {"http": opened.status_code})
    status_b = cb.get(B + "/index/status").json()
    b_roles = cb.get(B + "/roles").json()
    b_mem = cb.get(B + "/memory").json()
    b_history = cb.get(B + "/conversations?limit=20").json()["items"]
    record("C21-profile-B-local-state-isolation", "PASS" if not b_roles and not b_mem and not b_history else "FAIL", {"roles": len(b_roles), "memories": len(b_mem), "history": len(b_history), "index": status_b.get("state")})

    settings = ca.get(A + "/settings").json()
    fingerprint = settings["embedding_fingerprint"]
    conversations = get_conversations(ca)
    details = [ca.get(A + f"/conversations/{item['conversation_id']}").json() for item in conversations]
    all_messages = [message for detail in details for message in detail.get("messages", [])]
    pref_detail = next(d for d in details if any(m["question"] == "我偏好简洁中文回答，并把建议和已确认事实分开。" for m in d.get("messages", [])))
    pref_message = next(m for m in pref_detail["messages"] if m["question"] == "我偏好简洁中文回答，并把建议和已确认事实分开。")
    record("C20-real-user-message-source", "PASS", {"request_id": pref_message["request_id"], "conversation_id": pref_detail["conversation_id"]})

    no_attest = ca.post(A + "/memory/candidates", json={"message_id": pref_message["request_id"], "text": pref_message["question"], "user_expression": False})
    record("C20-no-attestation-rejected", "PASS" if no_attest.status_code in (400, 422) else "FAIL", {"http": no_attest.status_code, "body": no_attest.json()})
    assistant_reject = ca.post(A + "/memory/candidates", json={"message_id": pref_message["request_id"], "text": pref_message["answer"], "user_expression": True})
    record("C20-assistant-text-rejected", "PASS" if assistant_reject.status_code in (400, 422) else "FAIL", {"http": assistant_reject.status_code, "body": assistant_reject.json()})
    fake_reject = ca.post(A + "/memory/candidates", json={"message_id": str(uuid.uuid4()), "text": "我偏好简洁回答。", "user_expression": True})
    record("C20-forged-message-id-rejected", "PASS" if fake_reject.status_code in (400, 404, 422) else "FAIL", {"http": fake_reject.status_code, "body": fake_reject.json()})

    source_question = "引用材料原文：‘我偏好回答都只按来源原句’；这是粘贴内容，不代表我的偏好。"
    source_id = str(uuid.uuid4())
    source_response = ca.post(A + "/queries", json={"request_id": source_id, "question": source_question, "fingerprint": fingerprint, "answer_mode": "fact", "purpose": "current"})
    source_candidate = ca.post(A + "/memory/candidates", json={"message_id": source_id, "text": source_question, "user_expression": True})
    record("C20-quoted-source-canary-rejected", "PASS" if source_response.status_code == 200 and source_candidate.status_code in (400, 422) else "FAIL", {"query_http": source_response.status_code, "candidate_http": source_candidate.status_code, "candidate_body": source_candidate.json()})

    pending_question = "我希望回答先写结论，并明确标出尚缺条件。"
    pending_id = str(uuid.uuid4())
    pending_query = ca.post(A + "/queries", json={"request_id": pending_id, "question": pending_question, "fingerprint": fingerprint, "answer_mode": "fact", "purpose": "current"})
    first_candidate = ca.post(A + "/memory/candidates", json={"message_id": pending_id, "text": pending_question, "user_expression": True})
    second_candidate = ca.post(A + "/memory/candidates", json={"message_id": pending_id, "text": pending_question, "user_expression": True})
    first_json = first_candidate.json() if first_candidate.content else {}
    second_json = second_candidate.json() if second_candidate.content else {}
    same_candidate = first_json.get("candidate_id") == second_json.get("candidate_id")
    candidate_ok = pending_query.status_code == 200 and first_candidate.status_code in (200, 201) and second_candidate.status_code in (200, 201) and same_candidate
    record("C20-pending-candidate-idempotency", "PASS" if candidate_ok else "FAIL", {"query_http": pending_query.status_code, "first_http": first_candidate.status_code, "second_http": second_candidate.status_code, "same_id": same_candidate})

    history_question = "青岚旧预算规则的历史版本是什么？"
    current_resp = ca.post(A + "/queries", json={"request_id": str(uuid.uuid4()), "question": history_question, "fingerprint": fingerprint, "answer_mode": "fact", "purpose": "current"})
    history_resp = ca.post(A + "/queries", json={"request_id": str(uuid.uuid4()), "question": history_question, "fingerprint": fingerprint, "answer_mode": "fact", "purpose": "history"})
    current_citations = [e.get("data", {}) for e in sse(current_resp) if e.get("type") == "citation"]
    history_citations = [e.get("data", {}) for e in sse(history_resp) if e.get("type") == "citation"]
    current_has_superseded = any(c.get("validity") == "superseded" for c in current_citations)
    history_has_superseded = any(c.get("validity") == "superseded" for c in history_citations)
    record("C13-current-history-qualification-api", "PASS" if not current_has_superseded and history_has_superseded else "FAIL", {"current_status": current_resp.status_code, "history_status": history_resp.status_code, "current_validities": [c.get("validity") for c in current_citations], "history_validities": [c.get("validity") for c in history_citations]})

    role_list = ca.get(A + "/roles").json()
    role = role_list[0] if role_list else None
    if role is None:
        created_role = ca.post(A + "/roles", json={"name": "QA 回放角色", "instructions": "只影响表达，不改变证据权限。", "context_budget": 200})
        role = created_role.json() if created_role.status_code == 201 else None
    mode_request = {"request_id": str(uuid.uuid4()), "question": "青岚计划的预算上限是多少？", "fingerprint": fingerprint, "answer_mode": "fact", "purpose": "current", "role_id": role["role_id"] if role else None}
    if mode_request["role_id"] is None:
        mode_request.pop("role_id")
    mode_request["conversation_id"] = pref_detail["conversation_id"]
    mode_response = ca.post(A + "/queries", json=mode_request)
    conversations = get_conversations(ca)
    detail = next(d for d in [ca.get(A + f"/conversations/{i['conversation_id']}").json() for i in conversations] if any(m["request_id"] == mode_request["request_id"] for m in d.get("messages", [])))
    msg = next(m for m in detail["messages"] if m["request_id"] == mode_request["request_id"])
    replay_payload = {"request_id": msg["request_id"], "conversation_id": detail["conversation_id"], "question": msg["question"], "fingerprint": fingerprint, "answer_mode": msg["answer_mode"], "purpose": msg["purpose"]}
    if mode_request.get("role_id"):
        replay_payload["role_id"] = mode_request["role_id"]
    before_calls = len(CAPTURE.read_text(encoding="utf-8").splitlines()) if CAPTURE.exists() else 0
    if role:
        ca.patch(A + f"/roles/{role['role_id']}", json={"name": role["name"], "instructions": "编辑后的角色风格；仍不得改变证据权限。", "context_budget": 200})
    memories = ca.get(A + "/memory").json()
    if memories:
        ca.patch(A + f"/memory/{memories[0]['memory_id']}", json={"text": "幂等复验后编辑的已确认偏好。"})
    replay = ca.post(A + "/queries", json=replay_payload)
    after_calls = len(CAPTURE.read_text(encoding="utf-8").splitlines()) if CAPTURE.exists() else 0
    initial_events = sse(mode_response)
    replay_events = sse(replay)
    same_events = initial_events == replay_events
    record("C14-idempotent-replay-after-context-change", "PASS" if mode_response.status_code == 200 and replay.status_code == 200 and same_events and after_calls == before_calls else "FAIL", {"initial_http": mode_response.status_code, "replay_http": replay.status_code, "same_sse": replay.text == mode_response.text, "same_events": same_events, "initial_types": [e.get("type") for e in initial_events], "replay_types": [e.get("type") for e in replay_events], "initial_final": initial_events[-1] if initial_events else None, "replay_final": replay_events[-1] if replay_events else None, "provider_calls_before_replay": before_calls, "provider_calls_after_replay": after_calls})
    conflict = ca.post(A + "/queries", json={**replay_payload, "answer_mode": "comparison"})
    record("C14-same-request-id-different-mode-conflict", "PASS" if conflict.status_code == 409 else "FAIL", {"http": conflict.status_code})
    record("C14-structured-history-fields", "PASS" if all(key in msg for key in ("answer_mode", "source_statements", "inferences", "advice", "missing_information")) else "FAIL", {"fields_present": [key for key in ("answer_mode", "source_statements", "inferences", "advice", "missing_information") if key in msg], "role_id_retained": bool(msg.get("role_id"))})

output = BASE / "harness" / "blackbox-results.json"
output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
