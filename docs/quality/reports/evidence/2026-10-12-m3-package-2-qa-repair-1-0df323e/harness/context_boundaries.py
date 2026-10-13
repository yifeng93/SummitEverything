from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:18793/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
CAPTURE = BASE / "harness" / "deepseek-payloads.jsonl"


def capture_count() -> int:
    return len(CAPTURE.read_text(encoding="utf-8").splitlines()) if CAPTURE.exists() else 0


def events(response: httpx.Response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


results: list[dict] = []
with httpx.Client(headers=HEADERS, timeout=30) as client:
    fingerprint = client.get(API + "/settings").json()["embedding_fingerprint"]
    role = client.get(API + "/roles").json()[0]
    long_question = "青岚计划预算上限是多少？" + ("注" * (8000 - len("青岚计划预算上限是多少？")))
    before = capture_count()
    long_result = client.post(
        API + "/queries",
        json={
            "request_id": str(uuid.uuid4()),
            "question": long_question,
            "fingerprint": fingerprint,
            "answer_mode": "fact",
            "purpose": "current",
            "role_id": role["role_id"],
        },
    )
    after = capture_count()
    captured = json.loads(CAPTURE.read_text(encoding="utf-8").splitlines()[-1])["body"] if after > before else {}
    results.append(
        {
            "case": "C20-current-question-not-silently-truncated",
            "status": "PASS"
            if long_result.status_code == 200
            and len(long_question) == 8000
            and captured.get("question") == long_question
            else "FAIL",
            "detail": {
                "http": long_result.status_code,
                "question_chars": len(long_question),
                "captured_chars": len(captured.get("question", "")),
                "question_sha256": hashlib.sha256(long_question.encode()).hexdigest(),
                "captured_sha256": hashlib.sha256(captured.get("question", "").encode()).hexdigest(),
                "provider_calls_before": before,
                "provider_calls_after": after,
            },
        }
    )

    confirmed_memory_ids: list[str] = []
    for index in range(2):
        memory_text = f"我偏好边界测试{index + 1}" + ("x" * 3490)
        query = client.post(
            API + "/queries",
            json={
                "request_id": str(uuid.uuid4()),
                "question": memory_text,
                "fingerprint": fingerprint,
                "answer_mode": "fact",
                "purpose": "current",
                "role_id": role["role_id"],
            },
        )
        conversations = client.get(API + "/conversations?limit=100").json()["items"]
        detail = None
        for item in conversations:
            candidate_detail = client.get(API + f"/conversations/{item['conversation_id']}").json()
            if any(message["question"] == memory_text for message in candidate_detail["messages"]):
                detail = candidate_detail
                break
        if detail is None:
            raise RuntimeError("Synthetic user message was not saved in conversation history")
        actual = next(message for message in detail["messages"] if message["question"] == memory_text)
        candidate = client.post(
            API + "/memory/candidates",
            json={"message_id": str(actual["request_id"]), "text": memory_text, "user_expression": True},
        )
        candidate_id = candidate.json()["candidate_id"]
        confirmation = client.post(
            API + f"/memory/candidates/{candidate_id}/confirmations",
            json={"confirmation_id": f"qa-memory-budget-confirm-{index}", "text": memory_text},
        )
        if query.status_code != 200 or candidate.status_code != 201 or confirmation.status_code != 200:
            results.append(
                {"case": f"C20-budget-memory-setup-{index + 1}", "status": "FAIL", "detail": {"query": query.status_code, "candidate": candidate.status_code, "confirmation": confirmation.status_code}}
            )
        else:
            confirmed_memory_ids.append(confirmation.json()["memory_id"])

    memory_bytes = sum(len(item["text"].encode()) for item in client.get(API + "/memory").json())
    before = capture_count()
    overflow = client.post(
        API + "/queries",
        json={
            "request_id": str(uuid.uuid4()),
            "question": "青岚计划预算上限是多少？",
            "fingerprint": fingerprint,
            "answer_mode": "fact",
            "purpose": "current",
            "role_id": role["role_id"],
        },
    )
    after = capture_count()
    results.append(
        {
            "case": "C20-active-memory-budget-explicit-rejection",
            "status": "PASS" if memory_bytes > 6000 and overflow.status_code == 422 and after == before else "FAIL",
            "detail": {"active_memory_bytes": memory_bytes, "http": overflow.status_code, "provider_calls_before": before, "provider_calls_after": after, "body": overflow.json()},
        }
    )
    deleted = [client.delete(API + f"/memory/{memory_id}").status_code for memory_id in confirmed_memory_ids]
    remaining = client.get(API + "/memory").json()
    results.append({"case": "C20-memory-budget-fixture-cleanup", "status": "PASS" if all(status == 204 for status in deleted) and not remaining else "FAIL", "detail": {"delete_http": deleted, "remaining": len(remaining)}})

out = BASE / "harness" / "context-boundary-results.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
