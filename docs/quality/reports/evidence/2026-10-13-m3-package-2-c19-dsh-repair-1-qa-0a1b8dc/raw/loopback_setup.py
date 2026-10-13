import json
from urllib.request import Request, urlopen
from uuid import uuid4

base = "http://127.0.0.1:18874"
token = "qa-c19-repair-1-local-only"
workspace_root = "/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-repair-1-qa/SummitEverything/.local/qa/c19-repair-1/ui-api-workspace"

def request(path, payload=None, method=None):
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = Request(base + path, data=data, method=method or ("POST" if data is not None else "GET"),
                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, raw.decode() if content_type.startswith("text/event-stream") else json.loads(raw) if raw else {}

status, ws = request("/api/v1/workspaces", {"root": workspace_root, "mode": "create", "name": "C19 QA WebUI 合成库", "operation_id": "qa-workspace"})
assert status == 201
_, line = request("/api/v1/lines", {"name": "C19 QA 综合线", "operation_id": "qa-line"})
projects = {}
for name in ("白萤会展", "白萤近似", "汀屿计划", "云岬营地"):
    _, p = request("/api/v1/projects", {"line_id": line["id"], "name": name, "operation_id": f"project-{name}"})
    projects[name] = p

pages = [
    ("白萤会展", "年度访客信息登记", "白萤会展年度访客信息登记须核验身份并登记姓名。"),
    ("白萤近似", "访客登记", "白萤近似访客登记须核验身份并登记姓名。"),
    ("汀屿计划", "访客流程", "汀屿计划访客登记须由前台核验。"),
    *[("云岬营地", f"预算记录{i}", f"云岬营地预算额度第{i}项为{i * 10000 + 30000}元。") for i in range(1, 7)],
]
for project_name, title, body in pages:
    status, _ = request("/api/v1/pages", {
        "metadata": {"id": str(uuid4()), "title": title, "role": "knowledge", "kind": "topic",
                     "line_id": line["id"], "project_id": projects[project_name]["id"]},
        "body": body, "confirmation_id": f"confirm-{title}", "operation_id": f"write-{title}"})
    assert status == 201, (project_name, title, status)
_, plan = request("/api/v1/index/plans", {"mode": "initial", "fingerprint": "qa-c19-v1"})
_, built = request("/api/v1/index/jobs", plan)
assert built["indexed_pages"] == len(pages), built
print(json.dumps({"workspace": ws["name"], "line": line["name"], "projects": list(projects),
                  "pages": len(pages), "indexed_pages": built["indexed_pages"],
                  "workspace_root": workspace_root, "providers": "Fake only"}, ensure_ascii=False))
