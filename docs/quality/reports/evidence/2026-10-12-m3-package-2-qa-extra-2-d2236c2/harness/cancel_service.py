from __future__ import annotations

import json
import os
import uuid

import httpx

API = "http://127.0.0.1:18373/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
events: list[dict] = []
request_id = str(uuid.uuid4())
cancel_status: int | None = None
with httpx.Client(headers=HEADERS, timeout=20) as client:
    fingerprint = client.get(API + "/settings").json()["embedding_fingerprint"]
    opened = client.post(
        API + "/workspaces",
        json={
            "root": os.environ["QA_M3_WORKSPACE"],
            "mode": "open",
            "operation_id": f"qa-live-cancel-open-{uuid.uuid4()}",
        },
    )
    assert opened.status_code == 201, (opened.status_code, opened.text)
    payload = {
        "request_id": request_id,
        "question": "青岚计划的预算上限是多少？",
        "fingerprint": fingerprint,
        "purpose": "current",
    }
    with client.stream("POST", API + "/queries", json=payload) as response:
        assert response.status_code == 200, (response.status_code, response.read().decode())
        conversation_id = response.headers["x-conversation-id"]
        pending: list[str] = []
        for line in response.iter_lines():
            if line:
                pending.append(line)
                continue
            raw = next((row[6:] for row in pending if row.startswith("data: ")), None)
            if raw:
                event = json.loads(raw)
                events.append(event)
                if event["type"] == "status" and cancel_status is None:
                    cancel_status = client.delete(API + f"/queries/{request_id}").status_code
            pending.clear()
    history = client.get(API + f"/conversations/{conversation_id}")
    assert history.status_code == 200
    message = next(row for row in history.json()["messages"] if row["request_id"] == request_id)
    assert cancel_status == 202, cancel_status
    assert [event["type"] for event in events][-1] == "error", events
    assert events[-1]["data"]["code"] == "cancelled", events
    assert sum(event["type"] in {"completed", "error"} for event in events) == 1
    assert message["state"] == "cancelled" and not message["answer"], message
    print(
        json.dumps(
            {
                "status": "PASS",
                "cancel_http": cancel_status,
                "event_types": [event["type"] for event in events],
                "event_seq": [event["seq"] for event in events],
                "history_state": message["state"],
                "answer_chars": len(message["answer"]),
            },
            ensure_ascii=False,
        )
    )
