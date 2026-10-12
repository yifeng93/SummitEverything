from __future__ import annotations

import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.intake import actions as action_module
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.workspace.state import attempt_is_live

TOKEN = "synthetic-qa-token"

with TemporaryDirectory(prefix="m3-p3-action-lease-") as temp:
    base = Path(temp)
    root = base / "workspace"
    provider = FakeFeishu(base / "fake-feishu-remote")
    app = create_app(session_token=TOKEN, profile_root=base / "profile", feishu_provider=provider)
    client = TestClient(app, base_url="http://127.0.0.1:5173", headers={"Authorization": f"Bearer {TOKEN}"}, raise_server_exceptions=False)
    opened = client.post("/api/v1/workspaces", json={"root": str(root), "mode": "create", "name": "QA synthetic", "operation_id": str(uuid4())})
    assert opened.status_code == 201, opened.text
    authorization = client.post("/api/v1/integrations/feishu/authorizations", json={})
    assert authorization.status_code == 200
    assert client.get(authorization.json()["authorization_url"]).status_code == 200
    proposed = client.post("/api/v1/actions", json={"action_id": str(uuid4()), "kind": "feishu_task_create", "payload": {"summary": "Synthetic task", "due": None}})
    assert proposed.status_code == 201, proposed.text
    action = proposed.json()
    confirmed = client.post(f"/api/v1/actions/{action['action_id']}/confirmations", json={"payload_sha256": action["payload_sha256"], "confirmation_id": str(uuid4())})
    assert confirmed.status_code == 200, confirmed.text
    action = confirmed.json()

    real_save = action_module.save_receipt
    def fail_first_running_receipt(workspace: Path, current) -> None:
        if current.state == "running":
            raise OSError("synthetic running-receipt write failure")
        real_save(workspace, current)
    action_module.save_receipt = fail_first_running_receipt
    first_status = client.post(f"/api/v1/actions/{action['action_id']}/executions", json={"payload_sha256": action["payload_sha256"], "confirmation_id": action["confirmation_id"]})
    action_module.save_receipt = real_save

    lease_dir = root / ".summit-everything" / "attempt-leases"
    lease_paths = sorted(lease_dir.glob("*.lock"))
    live = [attempt_is_live(root, path.stem) for path in lease_paths]
    receipt_path = root / ".summit-everything" / "action_receipts" / "active" / f"{action['action_id']}.json"
    persisted = json.loads(receipt_path.read_text())
    remote_path = provider.simulated_remote_root / "simulated_remote_tasks.json"
    remote_after_failure = json.loads(remote_path.read_text()) if remote_path.exists() else {"tasks": {}}

    gc.collect()
    live_after_gc = [attempt_is_live(root, path.stem) for path in lease_paths]
    retry = client.post(f"/api/v1/actions/{action['action_id']}/executions", json={"payload_sha256": action["payload_sha256"], "confirmation_id": action["confirmation_id"]})
    remote_after_retry = json.loads(remote_path.read_text()) if remote_path.exists() else {"tasks": {}}
    result = {
        "first_http_status": first_status.status_code,
        "state_after_failed_running_receipt": persisted["state"],
        "lease_files_left_after_failure": len(lease_paths),
        "lease_file_names": [path.name for path in lease_paths],
        "lease_live_checks": live,
        "lease_live_checks_after_gc": live_after_gc,
        "remote_tasks_after_failure": len(remote_after_failure.get("tasks", {})),
        "retry_http_status": retry.status_code,
        "retry_state": retry.json().get("state") if retry.headers.get("content-type", "").startswith("application/json") else None,
        "remote_tasks_after_retry": len(remote_after_retry.get("tasks", {})),
    }
    print(json.dumps(result, indent=2))
    assert first_status.status_code == 500
    assert persisted["state"] == "confirmed"
    assert len(lease_paths) == 1 and live == [True] and live_after_gc == [False]
    assert len(remote_after_failure.get("tasks", {})) == 0
    assert retry.status_code == 200 and retry.json()["state"] == "succeeded"
    assert len(remote_after_retry.get("tasks", {})) == 1
    client.close()
