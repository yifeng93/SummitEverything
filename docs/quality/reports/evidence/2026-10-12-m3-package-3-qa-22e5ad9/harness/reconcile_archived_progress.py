from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.workspace.archives import archive_completed_transactions
from summit_everything.workspace.transactions import atomic_write

TOKEN = "synthetic-progress-token"
with TemporaryDirectory(prefix="m3-p3-progress-archive-") as temp:
    base = Path(temp)
    root = base / "workspace"
    app = create_app(session_token=TOKEN, profile_root=base / "profile", feishu_provider=FakeFeishu(base / "remote"))
    c = TestClient(app, base_url="http://127.0.0.1:5173", headers={"Authorization": f"Bearer {TOKEN}"}, raise_server_exceptions=False)
    opened = c.post("/api/v1/workspaces", json={"root": str(root), "mode": "create", "name": "QA synthetic", "operation_id": str(uuid4())})
    assert opened.status_code == 201, opened.text
    line = c.post("/api/v1/lines", json={"name": "line", "operation_id": str(uuid4())}).json()
    project = c.post("/api/v1/projects", json={"name": "project", "line_id": line["id"], "operation_id": str(uuid4())}).json()
    proposal = c.post("/api/v1/actions", json={"action_id": str(uuid4()), "kind": "project_progress", "payload": {"project_id": project["id"], "expected_version": 0, "progress": "synthetic complete"}}).json()
    confirmed = c.post(f"/api/v1/actions/{proposal['action_id']}/confirmations", json={"payload_sha256": proposal["payload_sha256"], "confirmation_id": str(uuid4())}).json()
    executed = c.post(f"/api/v1/actions/{proposal['action_id']}/executions", json={"payload_sha256": confirmed["payload_sha256"], "confirmation_id": confirmed["confirmation_id"]})
    assert executed.status_code == 200 and executed.json()["state"] == "succeeded", executed.text
    before_version = c.get("/api/v1/projects").json()[0]["progress_version"]
    receipt_path = root / ".summit-everything" / "action_receipts" / "active" / f"{proposal['action_id']}.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["state"] = "unknown"
    receipt["finished_at"] = None
    atomic_write(receipt_path, json.dumps(receipt).encode())
    archived_count = archive_completed_transactions(root, datetime.now(UTC) + timedelta(days=62))
    active_transaction_files = list((root / ".summit-everything" / "transactions").glob("[0-9a-f]" * 64 + ".json"))
    summary_paths = list((root / ".summit-everything" / "archives" / "transactions").glob("*/summary.json"))
    summary_values = [json.loads(p.read_text()) for p in summary_paths]
    proof_records = [entry["value"] for summary in summary_values for entry in summary.get("items", {}).values() if entry.get("value", {}).get("operation_id", "").startswith("progress:")]
    found_write_proof = bool(proof_records) and all(value.get("state") == "succeeded" and value.get("relative_path") == ".summit-everything/manifest.json" for value in proof_records)
    reconciled = c.post(f"/api/v1/actions/{proposal['action_id']}/reconciliations", json={})
    final_version = c.get("/api/v1/projects").json()[0]["progress_version"]
    result = {"action_receipt_state_before_reconcile": receipt["state"], "archived_transaction_receipts": archived_count, "active_sha_transaction_receipts": len(active_transaction_files), "transaction_month_summary_count": len(summary_paths), "archive_contains_progress_proof": found_write_proof, "summary_paths": [str(p) for p in summary_paths], "summary_months": [value.get("month") for value in summary_values], "progress_proof_records": proof_records, "reconcile_http": reconciled.status_code, "reconcile_state": reconciled.json().get("state"), "progress_version_before_reconcile": before_version, "progress_version_after_reconcile": final_version}
    print(json.dumps(result, indent=2))
    assert len(active_transaction_files) == 0 and found_write_proof
    assert reconciled.status_code == 200 and reconciled.json()["state"] == "succeeded"
    assert before_version == 1 and final_version == 1
    c.close()
