from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.intake import actions as action_module
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.llm import FakeLLM
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.state import attempt_is_live


def action_failure_case(base: Path) -> dict[str, object]:
    token = "synthetic-qa-token"
    root = base / "action-workspace"
    provider = FakeFeishu(base / "fake-feishu-remote")
    app = create_app(session_token=token, profile_root=base / "profile", feishu_provider=provider)
    client = TestClient(
        app,
        base_url="http://127.0.0.1:5173",
        headers={"Authorization": f"Bearer {token}"},
        raise_server_exceptions=False,
    )
    assert client.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": "create", "name": "Synthetic QA", "operation_id": str(uuid4())},
    ).status_code == 201
    auth_url = client.post("/api/v1/integrations/feishu/authorizations", json={}).json()["authorization_url"]
    assert client.get(auth_url).status_code == 200
    proposed = client.post(
        "/api/v1/actions",
        json={"action_id": str(uuid4()), "kind": "feishu_task_create", "payload": {"summary": "Synthetic task", "due": None}},
    )
    assert proposed.status_code == 201, proposed.text
    action = proposed.json()
    confirmed = client.post(
        f"/api/v1/actions/{action['action_id']}/confirmations",
        json={"payload_sha256": action["payload_sha256"], "confirmation_id": str(uuid4())},
    )
    assert confirmed.status_code == 200, confirmed.text
    action = confirmed.json()

    real_save = action_module.save_receipt
    attempt_ids: list[str] = []
    retained_exception = OSError("synthetic first-running-save failure")

    def fail_running_save(workspace: Path, receipt) -> None:
        if receipt.state == "running":
            attempt_ids.append(str(receipt.attempt_id))
            raise retained_exception
        real_save(workspace, receipt)

    action_module.save_receipt = fail_running_save
    try:
        failed = client.post(
            f"/api/v1/actions/{action['action_id']}/executions",
            json={"payload_sha256": action["payload_sha256"], "confirmation_id": action["confirmation_id"]},
        )
    finally:
        action_module.save_receipt = real_save

    assert failed.status_code == 500
    assert retained_exception.__traceback__ is not None
    assert len(attempt_ids) == 1
    attempt_id = attempt_ids[0]
    lease_path = root / ".summit-everything" / "attempt-leases" / f"{attempt_id}.lock"
    receipt_path = root / ".summit-everything" / "action_receipts" / "active" / f"{action['action_id']}.json"
    persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
    remote_path = provider.simulated_remote_root / "simulated_remote_tasks.json"
    remote_after_failure = json.loads(remote_path.read_text(encoding="utf-8")) if remote_path.exists() else {"tasks": {}}

    assert not lease_path.exists(), f"lease remained while exception+traceback alive: {lease_path}"
    assert not attempt_is_live(root, attempt_id)
    assert persisted["state"] == "confirmed"
    assert len(remote_after_failure.get("tasks", {})) == 0

    retry = client.post(
        f"/api/v1/actions/{action['action_id']}/executions",
        json={"payload_sha256": action["payload_sha256"], "confirmation_id": action["confirmation_id"]},
    )
    assert retry.status_code == 200 and retry.json()["state"] == "succeeded", retry.text
    remote_after_retry = json.loads(remote_path.read_text(encoding="utf-8"))
    assert len(remote_after_retry.get("tasks", {})) == 1
    client.close()
    return {
        "case": "action_first_running_receipt_save_failure",
        "http_after_injected_failure": failed.status_code,
        "exception_and_traceback_retained": retained_exception.__traceback__ is not None,
        "lease_file_exists_while_traceback_alive": lease_path.exists(),
        "attempt_is_live_while_traceback_alive": attempt_is_live(root, attempt_id),
        "receipt_state_after_failure": persisted["state"],
        "provider_tasks_after_failure": len(remote_after_failure.get("tasks", {})),
        "same_operation_retry_http": retry.status_code,
        "same_operation_retry_state": retry.json()["state"],
        "provider_tasks_after_retry": len(remote_after_retry.get("tasks", {})),
    }


def job_directory_failure_case(base: Path) -> dict[str, object]:
    root = base / "job-workspace"
    create_workspace(root, "Synthetic QA", base / "job-profile", "qa-create-workspace")
    line = create_line(root, "Synthetic line", "qa-line")
    project = create_project(root, line.id, "Synthetic project", "qa-project")
    item = IntakeService().add_text(root, "Deidentified source text.", filename="source.txt", operation_id="qa-source")
    provider = FakeLLM()
    service = IntakeReviewService(provider)
    jobs_root = root / ".summit-everything" / "intake" / "jobs"
    jobs_root_existed_before_failure = jobs_root.exists()
    real_mkdir = Path.mkdir
    retained_exception = OSError("synthetic jobs directory mkdir failure")

    def fail_jobs_mkdir(path: Path, *args, **kwargs):
        if Path(path).resolve() == jobs_root.resolve():
            raise retained_exception
        return real_mkdir(path, *args, **kwargs)

    Path.mkdir = fail_jobs_mkdir
    try:
        try:
            service.create_job(
                root,
                [item.item_id],
                operation_id="qa-same-intent",
                line_id=line.id,
                project_id=project.id,
            )
            raise AssertionError("injected jobs mkdir failure did not fire")
        except OSError as exc:
            assert exc is retained_exception
    finally:
        Path.mkdir = real_mkdir

    assert retained_exception.__traceback__ is not None
    leases = list((root / ".summit-everything" / "attempt-leases").glob("*.lock"))
    state_after_failure = IntakeService().list_items(root)[0].state
    jobs_root_exists_after_failure = jobs_root.exists()
    job_records_after_failure = list(jobs_root.glob("*.json")) if jobs_root.exists() else []
    assert not leases
    assert state_after_failure == "pending"
    assert not job_records_after_failure
    assert provider.calls == 0

    retried = service.create_job(
        root,
        [item.item_id],
        operation_id="qa-same-intent",
        line_id=line.id,
        project_id=project.id,
    )
    assert retried.state == "completed"
    assert provider.calls == 1
    return {
        "case": "job_jobs_root_mkdir_failure",
        "exception_and_traceback_retained": retained_exception.__traceback__ is not None,
        "lease_files_after_failure": len(leases),
        "item_state_after_failure": state_after_failure,
        "jobs_root_existed_before_failure": jobs_root_existed_before_failure,
        "jobs_root_exists_after_failure": jobs_root_exists_after_failure,
        "job_records_after_failure": len(job_records_after_failure),
        "provider_calls_after_failure": 0,
        "same_intent_retry_state": retried.state,
        "provider_calls_after_retry": provider.calls,
    }


with TemporaryDirectory(prefix="m3-package-3-repair-1-qa-") as temp:
    root = Path(temp)
    results = [action_failure_case(root), job_directory_failure_case(root)]
    print(json.dumps(results, ensure_ascii=False, indent=2))
