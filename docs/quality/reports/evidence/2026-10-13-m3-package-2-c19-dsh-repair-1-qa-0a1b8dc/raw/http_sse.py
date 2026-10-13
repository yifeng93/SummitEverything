import json
from urllib.request import Request, urlopen
from uuid import uuid4

base = "http://127.0.0.1:18874"
token = "qa-c19-repair-1-local-only"
fingerprint = "summit-fake-embedding-v1"

def request(path, payload=None, method=None):
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = Request(base + path, data=data, method=method or ("POST" if data is not None else "GET"),
                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urlopen(req, timeout=15) as response:
        raw = response.read().decode()
        content_type = response.headers.get("Content-Type", "")
        body = raw if content_type.startswith("text/event-stream") else json.loads(raw) if raw else {}
        return response.status, body, {k.lower(): v for k, v in response.headers.items()}

def query(question, mode="fact"):
    status, body, headers = request("/api/v1/queries", {
        "request_id": str(uuid4()), "question": question,
        "fingerprint": fingerprint, "answer_mode": mode
    })
    assert status == 200 and isinstance(body, str), (status, body)
    assert headers.get("content-type", "").startswith("text/event-stream"), headers
    events = [json.loads(block.removeprefix("data: ").strip()) for block in body.split("\n\n") if block.startswith("data: ")]
    assert events and events[0]["type"] == "status" and events[-1]["type"] == "completed", events
    citations = [event["data"] for event in events if event["type"] == "citation"]
    final = events[-1]["data"]
    return events, citations, final, headers

results = {}
events, citations, final, headers = query("白萤会展的年度访客信息登记办法是什么？")
assert citations and any("核验身份" in c.get("excerpt", "") for c in citations), (citations, final)
conversation_id = headers["x-conversation-id"]
results["complete"] = {"citations": len(citations), "missing": final["missing_information"], "conversation": conversation_id}
status, history, _ = request(f"/api/v1/conversations/{conversation_id}/reopen", {}, method="POST")
assert status == 200 and history["messages"][0]["citations"], history
results["history_reopen"] = {"status": status, "messages": len(history["messages"]), "citations": len(history["messages"][0]["citations"])}

_, citations, final, _ = query("比较白萤会展的年度访客信息登记与汀屿计划的排期", "comparison")
assert citations and any("汀屿计划" in x and "缺少" in x for x in final["missing_information"]), (citations, final)
results["partial"] = {"citations": len(citations), "missing": final["missing_information"]}

_, citations, final, _ = query("彩色牙刷的存储规则是什么？")
assert not citations and any("彩色牙刷" in x and "缺少" in x for x in final["missing_information"]), (citations, final)
results["zero"] = {"citations": len(citations), "missing": final["missing_information"]}

_, citations, final, _ = query("白萤近似的访客信息登记怎么办？")
assert not citations and any("白萤近似" in x and "缺少" in x for x in final["missing_information"]), (citations, final)
results["information_negative"] = {"citations": len(citations), "missing": final["missing_information"]}

_, citations, final, _ = query("比较云岬营地预算与汀屿计划的排期", "comparison")
assert len(citations) == 5 and any("汀屿计划" in x and "缺少" in x for x in final["missing_information"]) and any("上限" in x for x in final["missing_information"]), (citations, final)
results["mixed_cap_and_true_absence"] = {"citations": len(citations), "missing": final["missing_information"]}

_, citations, final, _ = query("云岬营地预算是多少？")
assert len(citations) == 5 and any("上限" in x for x in final["missing_information"]) and not any("缺少" in x for x in final["missing_information"]), (citations, final)
results["pure_cap"] = {"citations": len(citations), "missing": final["missing_information"]}

print(json.dumps({"api": "loopback", "sse": "PASS", "results": results, "providers": "Fake only"}, ensure_ascii=False))
