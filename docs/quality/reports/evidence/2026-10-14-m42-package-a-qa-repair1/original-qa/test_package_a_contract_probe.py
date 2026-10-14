from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.acceptance_plans import AcceptancePlanLedger
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "synthetic-qa-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _client(
    tmp_path: Path, profile: Path | None = None, *, raise_server_exceptions: bool = True
) -> TestClient:
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile or tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        ),
        base_url="http://127.0.0.1:5173",
        raise_server_exceptions=raise_server_exceptions,
    )


def _open(client: TestClient, tmp_path: Path, mode: str = "create") -> None:
    response = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": mode,
            "name": "QA 合成工作库",
            "operation_id": "qa-open-workspace",
        },
    )
    assert response.status_code == (201 if mode == "create" else 200), response.text


def _configure_real(client: TestClient) -> tuple[str, str, str]:
    response = client.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={
            "mode": "real",
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
                "max_output_tokens": 2048,
            },
        },
    )
    assert response.status_code == 200, response.text
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "QA线", "operation_id": "qa-line"}
    )
    assert line.status_code == 201, line.text
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={
            "line_id": line.json()["id"],
            "name": "QA项目",
            "operation_id": "qa-project",
        },
    )
    assert project.status_code == 201, project.text
    intake = client.post(
        "/api/v1/intake/items",
        headers=HEADERS,
        json={
            "text": "合成来源事实：访客须登记。",
            "filename": "qa-synthetic.txt",
            "operation_id": "qa-intake",
        },
    )
    assert intake.status_code == 201, intake.text
    return line.json()["id"], project.json()["id"], intake.json()["item_id"]


def _organize_scope(line_id: str, project_id: str, item_id: str) -> dict[str, object]:
    return {
        "item_ids": [item_id],
        "operation_id": "qa-organize-once",
        "line_id": line_id,
        "project_id": project_id,
        "reprocess": False,
    }


def _preview(client: TestClient, scope: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={"operation": "model.organize", "scope": scope},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _confirm(client: TestClient, preview: dict[str, object]) -> None:
    plan = preview["plan"]
    response = client.post(
        f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": plan["scope_sha256"], "scope": preview["scope"]},
    )
    assert response.status_code == 200, response.text


def test_cancelled_organize_plan_is_revoked_before_any_provider_call(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _open(client, tmp_path)
    line_id, project_id, item_id = _configure_real(client)
    scope = _organize_scope(line_id, project_id, item_id)
    preview = _preview(client, scope)
    plan_id = preview["plan"]["plan_id"]

    cancelled = client.delete(f"/api/v1/acceptance-plans/{plan_id}", headers=HEADERS)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "cancelled"
    execution = client.post(
        "/api/v1/intake/jobs",
        headers=HEADERS,
        json={**scope, "acceptance_plan_id": plan_id},
    )
    assert execution.status_code == 409, execution.text
    assert client.get(f"/api/v1/acceptance-plans/{plan_id}", headers=HEADERS).json()[
        "requests_reserved"
    ] == 0


def test_changed_model_settings_reject_confirmed_plan_before_reservation(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _open(client, tmp_path)
    line_id, project_id, item_id = _configure_real(client)
    scope = _organize_scope(line_id, project_id, item_id)
    preview = _preview(client, scope)
    _confirm(client, preview)
    plan_id = preview["plan"]["plan_id"]

    changed = client.patch(
        "/api/v1/settings", headers=HEADERS, json={"llm": {"max_output_tokens": 4096}}
    )
    assert changed.status_code == 200, changed.text
    execution = client.post(
        "/api/v1/intake/jobs",
        headers=HEADERS,
        json={**scope, "acceptance_plan_id": plan_id},
    )
    assert execution.status_code == 409, execution.text
    status = client.get(f"/api/v1/acceptance-plans/{plan_id}", headers=HEADERS).json()
    assert status["state"] == "confirmed"
    assert status["requests_reserved"] == 0


def test_reserved_request_survives_application_restart_as_unknown_without_replay(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    workspace = tmp_path / "workspace"
    first = _client(tmp_path, profile)
    _open(first, tmp_path)
    configured = first.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={"mode": "real", "feishu": {"app_id": "cli_qa_synthetic"}},
    )
    assert configured.status_code == 200, configured.text
    preview = first.post(
        "/api/v1/acceptance-plans",
        headers=HEADERS,
        json={
            "operation": "feishu.tasks.read",
            "scope": {"cursor": None, "limit": 20},
        },
    )
    assert preview.status_code == 201, preview.text
    plan = preview.json()["plan"]
    confirmation = first.post(
        f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
        headers=HEADERS,
        json={"scope_sha256": plan["scope_sha256"]},
    )
    assert confirmation.status_code == 200, confirmation.text

    ledger_path = next(profile.rglob("acceptance-plans.json"))
    ledger = AcceptancePlanLedger(ledger_path.parent)
    original_run_id = uuid4()
    ledger.begin_execution(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        config_sha256=plan["config_sha256"],
        scope_sha256=plan["scope_sha256"],
        run_id=original_run_id,
    )
    ledger.reserve_requests(
        UUID(plan["plan_id"]),
        workspace_id=plan["workspace_id"],
        profile_id=plan["profile_id"],
        count=2,
    )

    restarted = _client(tmp_path, profile, raise_server_exceptions=False)
    opened = restarted.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(workspace),
            "mode": "open",
            "name": "QA 合成工作库",
            "operation_id": "qa-open-workspace",
        },
    )
    assert opened.status_code == 201, opened.text
    replay = restarted.get(
        f"/api/v1/integrations/feishu/tasks?limit=20&plan_id={plan['plan_id']}",
        headers=HEADERS,
    )
    assert replay.status_code == 409, replay.text
    assert replay.json()["error"]["code"] == "acceptance_plan_conflict"
    persisted = ledger.get(UUID(plan["plan_id"]))
    assert persisted.requests_reserved == 2

    ledger_bytes_before_status = ledger_path.read_bytes()
    status = restarted.get(f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS)
    repeated_status = restarted.get(
        f"/api/v1/acceptance-plans/{plan['plan_id']}", headers=HEADERS
    )
    assert status.status_code == 200, status.text
    assert repeated_status.status_code == 200, repeated_status.text
    assert status.json()["state"] == "unknown"
    assert status.json()["finished_at"]
    assert repeated_status.json()["state"] == "unknown"
    assert repeated_status.json()["finished_at"]
    assert status.json()["requests_reserved"] == 2
    assert repeated_status.json()["requests_reserved"] == 2
    assert status.json()["execution_run_id"] == str(original_run_id)
    persisted_after_reads = ledger.get(UUID(plan["plan_id"]))
    assert persisted_after_reads.state == "executing"
    assert persisted_after_reads.execution_run_id == original_run_id
    assert persisted_after_reads.requests_reserved == 2
    assert ledger_path.read_bytes() == ledger_bytes_before_status

