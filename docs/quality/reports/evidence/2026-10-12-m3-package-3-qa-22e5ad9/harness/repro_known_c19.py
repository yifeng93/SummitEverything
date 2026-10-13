from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import FakeLLM
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.writer import PageWriter

with TemporaryDirectory(prefix="m3-p3-known-c19-") as temp:
    base = Path(temp)
    root, profile = base / "workspace", base / "profile"
    create_workspace(root, "QA synthetic workspace", profile, "create")
    line = create_line(root, "Synthetic line", "line")
    project = create_project(root, line.id, "Synthetic project", "project")
    contents = [
        ("专项储备上限", "专项储备上限为 3.6 万元。"),
        ("朱雀项目设备预算", "朱雀项目设备预算上限为 12 万元。"),
        ("年度采购排期", "年度采购计划于 11 月开始。"),
        ("库存周转说明", "已确认备货数量为 40 件。"),
        ("客服交接", "客服交接由两人轮值。"),
        ("文档归档规则", "已批准材料按月份存档。"),
    ]
    writer = PageWriter()
    for index, (title, body) in enumerate(contents):
        writer.confirm(
            root,
            metadata={"id": str(uuid4()), "title": title, "role": "knowledge", "kind": "topic", "line_id": str(line.id), "project_id": str(project.id)},
            body=body,
            confirmation_id=f"confirm-{index}",
            operation_id=f"write-{index}",
        )
    fake = FakeLLM()
    query = QueryService(IndexStore(profile / "index.sqlite3"), FakeEmbedding(), answer_provider=fake)
    query.rebuild(root, fingerprint="fake-v1")
    app = create_app(session_token="synthetic-c19-token", profile_root=profile, query_service=query)
    client = TestClient(app, raise_server_exceptions=False, headers={"Authorization": "Bearer synthetic-c19-token"})
    opened = client.post("/api/v1/workspaces", json={"root": str(root), "mode": "open", "operation_id": "open"})
    assert opened.status_code == 201, opened.text
    before_calls = fake.calls
    response = client.post("/api/v1/queries", json={"request_id": str(uuid4()), "question": "比较风铃工程与霜塔项目的彩色牙刷储存规则。", "fingerprint": "fake-v1", "answer_mode": "comparison", "purpose": "current"})
    events = [json.loads(part[6:]) for part in response.text.split("\n\n") if part.startswith("data: ")]
    final = next((event["data"] for event in reversed(events) if event["type"] == "completed"), {})
    result = {"http": response.status_code, "answer_mode": final.get("answer_mode"), "citations": final.get("citations", []), "source_statements": final.get("source_statements", []), "missing_information": final.get("missing_information", []), "provider_calls_before": before_calls, "provider_calls_after": fake.calls, "final": final}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    client.close()
