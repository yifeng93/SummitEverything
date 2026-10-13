from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.provider import FeishuConfig

base = Path(os.environ["QA_M3_BASE"])
token = os.environ["QA_M3_SESSION_TOKEN"]
app = create_app(session_token=token, profile_root=base / "profiles-r2-A", feishu_config=FeishuConfig(allowed_origins=("http://127.0.0.1:15573",)))
with TestClient(app) as client:
    headers = {"Authorization": f"Bearer {token}"}
    opened = client.post("/api/v1/workspaces", headers=headers, json={"root": str(base / "workspace-A"), "mode": "create", "name": "QA extra2 synthetic workspace", "operation_id": "qa-extra2-create-workspace"})
    assert opened.status_code in {200, 201}, (opened.status_code, opened.text)
    line = client.post("/api/v1/lines", headers=headers, json={"name": "QA青岚朱雀合成线", "operation_id": "qa-extra2-line"})
    assert line.status_code == 201, (line.status_code, line.text)
    project = client.post("/api/v1/projects", headers=headers, json={"line_id": line.json()["id"], "name": "QA青岚朱雀对照项目", "operation_id": "qa-extra2-project"})
    assert project.status_code == 201, (project.status_code, project.text)
    print(json.dumps({"workspace": opened.status_code, "line": line.json(), "project": project.json()}, ensure_ascii=False))
