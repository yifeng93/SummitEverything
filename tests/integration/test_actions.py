"""Synthetic action intents exercise actual API, locks and durable receipts."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app

PREFIX = "/api/v1/actions"
TASKS = "/api/v1/integrations/feishu/tasks"


def client(tmp_path: Path, *, root: Path | None = None, provider=None) -> TestClient:
    app = create_app(
        session_token=str(uuid4()), profile_root=tmp_path / "profile", feishu_provider=provider
    )
    c = TestClient(
        app,
        base_url="http://127.0.0.1:5173",
        headers={"Authorization": "Bearer " + app.state.session_token},
    )
    target = root or tmp_path / "workspace"
    assert (
        c.post(
            "/api/v1/workspaces",
            json={
                "root": str(target),
                "mode": "open" if target.exists() else "create",
                "name": "模拟",
                "operation_id": str(uuid4()),
            },
        ).status_code
        == 201
    )
    url = c.post("/api/v1/integrations/feishu/authorizations", json={}).json()["authorization_url"]
    assert c.get(url).status_code == 200
    return c


def proposal(c: TestClient, *, action_id=None, kind="feishu_task_create", payload=None, **extra):
    request = {
        "action_id": action_id or str(uuid4()),
        "kind": kind,
        "payload": payload or {"summary": "模拟任务", "due": None},
        **extra,
    }
    response = c.post(PREFIX, json=request)
    assert response.status_code == 201, response.text
    return response.json()


def confirm(c, action):
    result = c.post(
        PREFIX + "/" + action["action_id"] + "/confirmations",
        json={"payload_sha256": action["payload_sha256"], "confirmation_id": str(uuid4())},
    )
    assert result.status_code == 200, result.text
    return result.json()


def execute(c, action, **override):
    return c.post(
        PREFIX + "/" + action["action_id"] + "/executions",
        json={
            "payload_sha256": action["payload_sha256"],
            "confirmation_id": action.get("confirmation_id") or "fabricated",
            **override,
        },
    )


def test_independent_confirmation_replay_and_identical_titles(tmp_path):
    c = client(tmp_path)
    first = proposal(c)
    assert first["state"] == "proposed"
    assert execute(c, first).status_code == 409
    assert c.get(TASKS).json()["items"] == []
    approved = confirm(c, first)
    result = execute(c, approved)
    assert result.status_code == 200 and result.json()["state"] == "succeeded"
    assert execute(c, approved).json() == result.json()
    assert (
        c.post(
            PREFIX,
            json={
                "action_id": first["action_id"],
                "kind": first["kind"],
                "payload": {"summary": "改变", "due": None},
            },
        ).status_code
        == 409
    )
    execute(c, confirm(c, proposal(c)))
    tasks = c.get(TASKS).json()["items"]
    assert len(tasks) == 2 and tasks[0]["summary"] == tasks[1]["summary"]
    assert tasks[0]["guid"] != tasks[1]["guid"]


def test_edit_invalidates_confirmation_and_rejects_stale_hash(tmp_path):
    c = client(tmp_path)
    approved = confirm(c, proposal(c))
    edited = c.patch(
        PREFIX + "/" + approved["action_id"],
        json={
            "expected_payload_sha256": approved["payload_sha256"],
            "payload": {"summary": "改后", "due": None},
        },
    )
    assert edited.status_code == 200
    assert edited.json()["state"] == "proposed" and edited.json()["confirmation_id"] is None
    assert execute(c, approved).status_code == 409
    assert execute(c, edited.json()).status_code == 409
    assert execute(c, confirm(c, edited.json())).json()["state"] == "succeeded"
    assert (
        c.patch(
            PREFIX + "/" + approved["action_id"],
            json={
                "expected_payload_sha256": edited.json()["payload_sha256"],
                "payload": approved["payload"],
            },
        ).status_code
        == 409
    )


def test_task_selected_fields_date_and_completed_idempotently(tmp_path):
    c = client(tmp_path)
    created = execute(
        c,
        confirm(
            c,
            proposal(
                c,
                payload={
                    "summary": "日期",
                    "description": "保留",
                    "due": {"value": "2026-10-12", "is_all_day": True, "timezone": "Asia/Shanghai"},
                },
            ),
        ),
    ).json()
    assert created["state"] == "succeeded"
    guid = created["provider_result"]["task"]["guid"]
    updated = execute(
        c,
        confirm(
            c,
            proposal(
                c,
                kind="feishu_task_update",
                payload={
                    "task_guid": guid,
                    "task": {
                        "due": {
                            "value": "2026-10-13T09:00:00+08:00",
                            "is_all_day": False,
                            "timezone": "Asia/Shanghai",
                        }
                    },
                    "update_fields": ["due"],
                },
            ),
        ),
    ).json()
    task = updated["provider_result"]["task"]
    assert task["summary"] == "日期" and task["description"] == "保留"
    assert task["due"] == {"timestamp": 1791853200000, "is_all_day": False}
    for _ in range(2):
        result = execute(
            c, confirm(c, proposal(c, kind="feishu_task_complete", payload={"task_guid": guid}))
        )
        assert result.status_code == 200 and result.json()["state"] == "succeeded"
    assert c.get(TASKS + "/" + guid).json()["completed_at"] > 0


def test_task_validation_does_not_invent_dates(tmp_path):
    c = client(tmp_path)
    invalid = [
        {"summary": "没有日期语义"},
        {"summary": " ", "due": None},
        {
            "summary": "日期",
            "due": {"value": "2026-10-12", "is_all_day": False, "timezone": "Asia/Shanghai"},
        },
        {
            "summary": "日期",
            "due": {
                "value": "2026-10-12T09:00:00",
                "is_all_day": False,
                "timezone": "Asia/Shanghai",
            },
        },
        {
            "summary": "日期",
            "due": {"value": "2026-10-12", "is_all_day": True, "timezone": "Invalid"},
        },
        {"summary": "日期", "due": None, "approval": {"confirmation_id": "model"}},
    ]
    for payload in invalid:
        assert (
            c.post(
                PREFIX,
                json={"action_id": str(uuid4()), "kind": "feishu_task_create", "payload": payload},
            ).status_code
            == 422
        )
    assert c.get(TASKS).json()["items"] == []


def test_unknown_timeout_lookup_and_no_evidence_never_reposts(tmp_path):
    from summit_everything.integrations.feishu.fake import FakeFeishu

    class LostResponse(FakeFeishu):
        def task_create(self, credentials, body):
            super().task_create(credentials, body)
            raise TimeoutError("synthetic-secret must not escape")

    remote = tmp_path / "simulated-remote"
    c = client(tmp_path, provider=LostResponse(remote))
    action = confirm(c, proposal(c))
    unknown = execute(c, action).json()
    assert unknown["state"] == "unknown"
    assert "synthetic-secret" not in str(unknown)
    assert len(c.get(TASKS).json()["items"]) == 1
    assert execute(c, action).json() == unknown
    assert c.get(PREFIX + "/" + action["action_id"]).json()["state"] == "unknown"
    recovered = c.post(PREFIX + "/" + action["action_id"] + "/reconciliations", json={})
    assert recovered.status_code == 200 and recovered.json()["state"] == "succeeded"
    assert recovered.json()["evidence"][-1]["kind"] == "provider_lookup"
    assert len(c.get(TASKS).json()["items"]) == 1

    class NoResponse(FakeFeishu):
        def task_create(self, credentials, body):
            raise TimeoutError()

    c2 = client(tmp_path / "second", provider=NoResponse(tmp_path / "empty-remote"))
    absent = confirm(c2, proposal(c2))
    assert execute(c2, absent).json()["state"] == "unknown"
    assert (
        c2.post(PREFIX + "/" + absent["action_id"] + "/reconciliations", json={}).json()["state"]
        == "unknown"
    )
    explicit = c2.post(
        PREFIX + "/" + absent["action_id"] + "/outcomes",
        json={
            "payload_sha256": absent["payload_sha256"],
            "confirmation_id": "outcome-user",
            "state": "failed",
            "evidence": "用户在飞书确认未创建。",
        },
    )
    assert explicit.status_code == 200 and explicit.json()["state"] == "failed"
    assert explicit.json()["evidence"][-1]["kind"] == "user_outcome"
    assert execute(c2, absent).json()["state"] == "failed"
    assert c2.get(TASKS).json()["items"] == []


def test_concurrent_running_is_durable_before_provider_call(tmp_path):
    import json
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from summit_everything.integrations.feishu.fake import FakeFeishu

    entered, release = Event(), Event()
    root = tmp_path / "workspace"

    class Slow(FakeFeishu):
        def task_create(self, credentials, body):
            receipts = list((root / ".summit-everything/action_receipts/active").glob("*.json"))
            persisted = json.loads(receipts[0].read_bytes())
            assert (
                persisted["state"] == "running"
                and persisted["confirmation_id"]
                and persisted["payload_sha256"]
            )
            entered.set()
            assert release.wait(5)
            return super().task_create(credentials, body)

    c = client(tmp_path, provider=Slow(tmp_path / "simulated-remote"))
    action = confirm(c, proposal(c))
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(execute, c, action)
        assert entered.wait(5)
        try:
            second = execute(c, action)
            assert second.status_code == 200 and second.json()["state"] == "running"
        finally:
            release.set()
        assert future.result().json()["state"] == "succeeded"
    assert len(c.get(TASKS).json()["items"]) == 1


def test_process_exit_restarts_unknown_remote_survives_and_archive_lookup(tmp_path):
    import json
    import subprocess
    import sys
    from datetime import UTC, datetime

    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.workspace.action_receipts import archive_completed
    from summit_everything.workspace.transactions import workspace_lock

    root, remote = tmp_path / "workspace", tmp_path / "simulated-remote"
    c = client(tmp_path, provider=FakeFeishu(remote))
    action = confirm(c, proposal(c))
    script = """
import os, sys
from pathlib import Path
from uuid import UUID
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import MemoryCredentialStore, FeishuConfig
from summit_everything.integrations.feishu.service import FeishuService
from summit_everything.integrations.feishu.tasks import FeishuTasks
from summit_everything.intake.actions import ActionService, ActionConfirmation
class Interrupted(FakeFeishu):
    def task_create(self, credentials, body):
        super().task_create(credentials, body)
        os._exit(23)
provider = Interrupted(Path(sys.argv[2]))
credentials = MemoryCredentialStore()
credentials.put(provider.exchange('fake-ok', 'unused'))
session = FeishuService(provider, credentials, FeishuConfig(), 'child')
actions = ActionService(FeishuTasks(session), 'child')
actions.execute(
    Path(sys.argv[1]), UUID(sys.argv[3]),
    ActionConfirmation(payload_sha256=sys.argv[4], confirmation_id=sys.argv[5]),
)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(root),
            str(remote),
            action["action_id"],
            action["payload_sha256"],
            action["confirmation_id"],
        ],
        check=False,
    )
    assert result.returncode == 23
    restarted = client(tmp_path, root=root, provider=FakeFeishu(remote))
    unknown = restarted.get(PREFIX + "/" + action["action_id"]).json()
    assert unknown["state"] == "unknown"
    assert len(restarted.get(TASKS).json()["items"]) == 1
    assert execute(restarted, action).json()["state"] == "unknown"
    resolved = restarted.post(
        PREFIX + "/" + action["action_id"] + "/reconciliations", json={}
    ).json()
    assert resolved["state"] == "succeeded"
    with workspace_lock(root):
        archive_completed(root, datetime(2027, 1, 1, tzinfo=UTC))
    assert list((root / ".summit-everything/action_receipts/completed").glob("*/*.json"))
    restarted2 = client(tmp_path, root=root, provider=FakeFeishu(remote))
    assert execute(restarted2, action).json() == resolved
    assert len(restarted2.get(TASKS).json()["items"]) == 1
    assert "simulated_remote_tasks.json" not in {path.name for path in root.rglob("*")}
    for path in (root / ".summit-everything/action_receipts/completed").glob("*/*.json"):
        assert (
            json.loads(path.read_bytes())["items"][action["action_id"]]["confirmation_id"]
            == action["confirmation_id"]
        )


def test_project_progress_separate_from_knowledge_and_version_conflict(tmp_path):
    c = client(tmp_path)
    line = c.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = c.post(
        "/api/v1/projects",
        json={"name": "模拟项目", "line_id": line["id"], "operation_id": "project"},
    ).json()
    action = proposal(
        c,
        kind="project_progress",
        payload={"project_id": project["id"], "expected_version": 0, "progress": "已完成准备"},
    )
    page = c.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": str(uuid4()),
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
                "title": "知识",
            },
            "body": "模拟事实",
            "confirmation_id": "knowledge-approval",
            "operation_id": "page",
        },
    )
    assert page.status_code == 201
    assert c.get("/api/v1/projects").json()[0].get("progress", "") == ""
    assert execute(c, action, confirmation_id="knowledge-approval").status_code == 409
    result = execute(c, confirm(c, action))
    assert result.status_code == 200 and result.json()["state"] == "succeeded"
    current = c.get("/api/v1/projects").json()[0]
    assert current["progress"] == "已完成准备" and current["progress_version"] == 1
    assert execute(c, result.json()).json() == result.json()
    stale = confirm(
        c,
        proposal(
            c,
            kind="project_progress",
            payload={"project_id": project["id"], "expected_version": 0, "progress": "过时"},
        ),
    )
    assert execute(c, stale).json()["state"] == "failed"
    assert c.get("/api/v1/projects").json()[0]["progress"] == "已完成准备"
    assert c.get(TASKS).json()["items"] == []


def test_candidate_conversion_keeps_source_and_legacy_array(tmp_path):
    import json
    from datetime import UTC, datetime

    root = tmp_path / "workspace"
    c = client(tmp_path)
    candidate, draft, source = str(uuid4()), str(uuid4()), str(uuid4())
    path = root / ".summit-everything/actions" / (candidate + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy = {
        "action_id": candidate,
        "kind": "todo",
        "description": "模型建议与虚构审批不能执行",
        "source_draft_id": draft,
        "related_project_id": None,
        "state": "proposed",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_ids": [source],
        "approval": {"confirmation_id": "model"},
    }
    path.write_text(json.dumps(legacy))
    assert c.get(PREFIX).json() == [legacy]
    converted = proposal(c, candidate_id=candidate)
    assert converted["candidate_id"] == candidate and converted["source_draft_id"] == draft
    assert converted["source_ids"] == [source] and converted["confirmation_id"] is None
    assert execute(c, converted, confirmation_id="model").status_code == 409
    assert c.get(PREFIX + "?limit=1").json()["items"][0]["action_id"] == candidate
    assert json.loads(path.read_bytes()) == legacy
    assert c.get(TASKS).json()["items"] == []


def test_receipt_hash_corruption_blocks_writes_and_monthly_summary_keeps_unresolved(tmp_path):
    import json
    from datetime import UTC, datetime

    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.workspace.action_receipts import archive_completed
    from summit_everything.workspace.transactions import workspace_lock

    class Timeout(FakeFeishu):
        def task_create(self, credentials, body):
            raise TimeoutError()

    root = tmp_path / "workspace"
    c = client(tmp_path, provider=Timeout(tmp_path / "remote"))
    pending = confirm(c, proposal(c))
    unknown = execute(c, pending).json()
    done = c.post(
        PREFIX + "/" + pending["action_id"] + "/outcomes",
        json={
            "payload_sha256": pending["payload_sha256"],
            "confirmation_id": "explicit-outcome",
            "state": "failed",
            "evidence": "模拟核实未执行",
        },
    ).json()
    unresolved = confirm(c, proposal(c))
    assert execute(c, unresolved).json()["state"] == "unknown"
    with workspace_lock(root):
        archive_completed(root, datetime(2027, 1, 1, tzinfo=UTC))
    summaries = list((root / ".summit-everything/action_receipts/completed").glob("*/summary.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_bytes())
    assert summary["schema"] == "action-receipt-month-v1"
    assert summary["items"][pending["action_id"]] == done
    assert (
        root / ".summit-everything/action_receipts/active" / (unresolved["action_id"] + ".json")
    ).exists()
    active = (
        root / ".summit-everything/action_receipts/active" / (unresolved["action_id"] + ".json")
    )
    data = json.loads(active.read_bytes())
    data["payload"]["summary"] = "tampered"
    active.write_text(json.dumps(data))
    assert c.get(PREFIX + "/" + unresolved["action_id"]).status_code == 409
    assert execute(c, unresolved).status_code == 409
    assert unknown["state"] == "unknown"


def test_task_scopes_paging_errors_and_provider_v2_mapping(tmp_path):
    from summit_everything.integrations.feishu.fake import FakeFeishu

    class Capture(FakeFeishu):
        requests = []

        def task_create(self, credentials, body):
            self.requests.append(body)
            return super().task_create(credentials, body)

        def task_patch(self, credentials, guid, body, token):
            self.requests.append(body)
            return super().task_patch(credentials, guid, body, token)

    provider = Capture(tmp_path / "remote")
    c = client(tmp_path, provider=provider)
    credentials = c.app.state.feishu_service.credentials.get()
    credentials.scopes.remove("task:task:write")
    approved = confirm(c, proposal(c))
    assert execute(c, approved).status_code == 403
    assert c.get(TASKS).json()["items"] == []
    credentials.scopes.append("task:task:write")
    created = execute(c, approved).json()
    assert created["state"] == "succeeded"
    assert provider.requests[0]["client_token"] and "due" not in provider.requests[0]
    assert provider.requests[0]["summary"] == "模拟任务"
    execute(c, confirm(c, proposal(c)))
    page = c.get(TASKS, params={"limit": 1}).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    next_page = c.get(TASKS, params={"limit": 1, "cursor": page["next_cursor"]}).json()
    assert (
        next_page["items"][0]["guid"] != page["items"][0]["guid"]
        and next_page["next_cursor"] is None
    )
    intents = c.get("/api/v1/action-intents?limit=1").json()
    assert len(intents["items"]) == 1 and intents["next_cursor"]
    assert c.get(TASKS + "?cursor=bad").status_code == 422
    assert c.get(TASKS + "/missing").status_code == 404
    credentials.scopes.remove("task:task:read")
    assert c.get(TASKS).status_code == 403
    credentials.scopes.append("task:task:read")
    guid = created["provider_result"]["task"]["guid"]
    complete = execute(
        c, confirm(c, proposal(c, kind="feishu_task_complete", payload={"task_guid": guid}))
    ).json()
    assert complete["state"] == "succeeded"
    assert provider.requests[-1]["update_fields"] == ["completed_at"]
    assert set(provider.requests[-1]["task"]) == {"completed_at"}
    before = len(provider.requests)
    assert (
        execute(
            c, confirm(c, proposal(c, kind="feishu_task_complete", payload={"task_guid": guid}))
        ).json()["state"]
        == "succeeded"
    )
    assert len(provider.requests) == before
    expired = credentials.model_copy(update={"expires_at": 0})
    c.app.state.feishu_service.credentials.put(expired)
    assert c.get(TASKS).status_code == 401


def test_patch_bad_response_is_unknown_and_selected_only_validation(tmp_path):
    from summit_everything.integrations.feishu.fake import FakeFeishu

    class Wrong(FakeFeishu):
        def task_patch(self, credentials, guid, body, token):
            result = super().task_patch(credentials, guid, body, token)
            return result.model_copy(update={"guid": "wrong-provider-id"})

    c = client(tmp_path, provider=Wrong(tmp_path / "remote"))
    created = execute(c, confirm(c, proposal(c))).json()
    guid = created["provider_result"]["task"]["guid"]
    for fields, task in [
        (["summary"], {"description": "不选中"}),
        (["summary", "summary"], {"summary": "改"}),
        (["members"], {"members": []}),
        (["summary"], {"summary": " "}),
    ]:
        assert (
            c.post(
                PREFIX,
                json={
                    "action_id": str(uuid4()),
                    "kind": "feishu_task_update",
                    "payload": {"task_guid": guid, "task": task, "update_fields": fields},
                },
            ).status_code
            == 422
        )
    update = confirm(
        c,
        proposal(
            c,
            kind="feishu_task_update",
            payload={"task_guid": guid, "task": {"summary": "改后"}, "update_fields": ["summary"]},
        ),
    )
    assert execute(c, update).json()["state"] == "unknown"
    assert execute(c, update).json()["state"] == "unknown"
    assert c.get(TASKS + "/" + guid).json()["summary"] == "改后"
