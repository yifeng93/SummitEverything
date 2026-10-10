"""Independent regressions for the fixed M2 original candidate.

These assertions state product expectations and intentionally fail on the original SHA.
They exercise actual API, PageWriter, Fake Feishu, index and retrieval behavior.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.domain.content import RetrievalPurpose
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import UserCredentials
from summit_everything.integrations.feishu.tasks import FeishuTask
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.writer import PageWriter


def make_workspace(tmp_path: Path, provider=None) -> tuple[TestClient, Path, str]:
    token = "qa-synthetic-token"
    api = TestClient(
        create_app(
            session_token=token,
            profile_root=tmp_path / "profile",
            feishu_provider=provider,
        )
    )
    api.headers.update({"Authorization": f"Bearer {token}"})
    root = tmp_path / "workspace"
    created = api.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": "create", "name": "合成QA库", "operation_id": "ws"},
    )
    assert created.status_code == 201, created.text
    return api, root, created.json()["workspace_id"]


def add_project(api: TestClient) -> dict[str, str]:
    line = api.post("/api/v1/lines", json={"name": "合成线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    return {"line": line["id"], "project": project["id"], "overview": project["overview_id"]}


def test_a01_overview_title_update_preserves_validity_and_metadata(tmp_path: Path) -> None:
    api, root, workspace_id = make_workspace(tmp_path)
    ids = add_project(api)
    metadata = {
        "id": ids["overview"],
        "title": "旧概览标题",
        "role": "knowledge",
        "kind": "project_overview",
        "line_id": ids["line"],
        "project_id": ids["project"],
        "validity": "superseded",
        "tags": ["qa", "保留"],
        "source_refs": ["synthetic:fixture-1"],
        "custom_qa_field": {"preserve": True},
    }
    original_body = "独特事实：蓝色火车从合成站出发。"
    PageWriter().confirm(
        root,
        metadata=metadata,
        body=original_body,
        confirmation_id="initial-overview",
        operation_id="initial-overview-write",
    )
    index = QueryService(IndexStore(tmp_path / "profile" / workspace_id / "index.sqlite3"))
    index.rebuild(root, fingerprint="fake-qa-v1")
    before = api.get(f"/api/v1/pages/{ids['overview']}").json()
    response = api.post(
        f"/api/v1/projects/{ids['project']}/overview/confirmations",
        json={
            "title": "仅改标题",
            "body": original_body,
            "confirmation_id": "title-only-confirmation",
            "operation_id": "title-only-operation",
            "expected_content_sha256": before["content_sha256"],
        },
    )
    assert response.status_code == 201, response.text
    after = api.get(f"/api/v1/pages/{ids['overview']}").json()
    metadata_preserved = (
        after["metadata"].get("validity") == "superseded"
        and after["metadata"].get("tags") == ["qa", "保留"]
        and after["metadata"].get("source_refs") == ["synthetic:fixture-1"]
        and after["metadata"].get("custom_qa_field") == {"preserve": True}
    )
    # Simulate the index refresh that would occur after an accepted page edit.
    incremental = index.plan(root, fingerprint="fake-qa-v1", mode="incremental")
    index.execute_plan(root, incremental)
    answer = index.query(
        root,
        "独特词鲸蓝九七是什么",
        fingerprint="fake-qa-v1",
        purpose=RetrievalPurpose.CURRENT,
    )
    citation_ids = {str(c.page_id) for c in answer.citations}
    overview_cited = str(ids["overview"]) in citation_ids
    assert metadata_preserved and str(ids["overview"]) not in citation_ids, (
        f"metadata_preserved={metadata_preserved}; overview_cited={overview_cited}; "
        f"citations={len(answer.citations)}"
    )


def test_a02_same_guid_uncompleted_task_is_not_successful_completion(tmp_path: Path) -> None:
    class NoopPatch(FakeFeishu):
        ignore_patch = False

        def task_patch(self, credentials, guid, body, token):
            if self.ignore_patch:
                return super().task_get(credentials, guid)
            return super().task_patch(credentials, guid, body, token)

    provider = NoopPatch(tmp_path / "fake-remote")
    api, _root, _workspace_id = make_workspace(tmp_path, provider)
    authorization = api.post("/api/v1/integrations/feishu/authorizations", json={}).json()
    assert api.get(authorization["authorization_url"]).status_code == 200
    create_response = api.post(
        "/api/v1/actions",
        json={
            "action_id": str(uuid4()),
            "kind": "feishu_task_create",
            "payload": {"summary": "合成待办", "due": None},
        },
    )
    assert create_response.status_code == 201, create_response.text
    create = create_response.json()
    confirmed = api.post(
        f"/api/v1/actions/{create['action_id']}/confirmations",
        json={"payload_sha256": create["payload_sha256"], "confirmation_id": "confirm-create"},
    ).json()
    created = api.post(
        f"/api/v1/actions/{create['action_id']}/executions",
        json={
            "payload_sha256": confirmed["payload_sha256"],
            "confirmation_id": confirmed["confirmation_id"],
        },
    ).json()
    guid = created["provider_result"]["task"]["guid"]
    provider.ignore_patch = True
    complete = api.post(
        "/api/v1/actions",
        json={
            "action_id": str(uuid4()),
            "kind": "feishu_task_complete",
            "payload": {"task_guid": guid},
        },
    ).json()
    confirmed = api.post(
        f"/api/v1/actions/{complete['action_id']}/confirmations",
        json={"payload_sha256": complete["payload_sha256"], "confirmation_id": "confirm-complete"},
    ).json()
    result = api.post(
        f"/api/v1/actions/{complete['action_id']}/executions",
        json={
            "payload_sha256": confirmed["payload_sha256"],
            "confirmation_id": confirmed["confirmation_id"],
        },
    ).json()
    assert result["state"] == "succeeded"
    actual = provider.task_get(
        UserCredentials(
            access_token="synthetic",
            refresh_token="synthetic",
            expires_at=9999999999,
            scopes=["task:task:write"],
        ),
        guid,
    )
    assert actual.completed_at != 0
    assert result["state"] == "succeeded"


def test_a03_unrelated_task_does_not_reconcile_unknown_create_as_success(tmp_path: Path) -> None:
    class TimeoutWithUnrelatedEvidence(FakeFeishu):
        unrelated: FeishuTask | None = None
        lose_next_create = False

        def task_create(self, credentials, body):
            result = super().task_create(credentials, body)
            if self.lose_next_create:
                raise TimeoutError("synthetic timeout after accepted write")
            return result

        def task_result(self, credentials, token):
            return self.unrelated

    provider = TimeoutWithUnrelatedEvidence(tmp_path / "fake-remote")
    unrelated = FakeFeishu.task_create(
        provider,
        UserCredentials(
            access_token="synthetic",
            refresh_token="synthetic",
            expires_at=9999999999,
            scopes=["task:task:write"],
        ),
        {
            "summary": "无关任务",
            "description": "其它动作",
            "due": None,
            "client_token": "unrelated",
        },
    )
    provider.unrelated = unrelated
    api, _root, _workspace_id = make_workspace(tmp_path, provider)
    authorization = api.post("/api/v1/integrations/feishu/authorizations", json={}).json()
    assert api.get(authorization["authorization_url"]).status_code == 200
    action_response = api.post(
        "/api/v1/actions",
        json={
            "action_id": str(uuid4()),
            "kind": "feishu_task_create",
            "payload": {"summary": "本动作新任务", "due": None},
        },
    )
    assert action_response.status_code == 201, action_response.text
    action = action_response.json()
    confirmed = api.post(
        f"/api/v1/actions/{action['action_id']}/confirmations",
        json={"payload_sha256": action["payload_sha256"], "confirmation_id": "confirm-unknown"},
    ).json()
    provider.lose_next_create = True
    pending = api.post(
        f"/api/v1/actions/{action['action_id']}/executions",
        json={
            "payload_sha256": confirmed["payload_sha256"],
            "confirmation_id": confirmed["confirmation_id"],
        },
    ).json()
    assert pending["state"] == "unknown"
    reconciled = api.post(f"/api/v1/actions/{action['action_id']}/reconciliations", json={}).json()
    assert reconciled["state"] == "unknown"


def test_a04_approved_journal_is_incrementally_indexed_without_manual_job(tmp_path: Path) -> None:
    api, root, workspace_id = make_workspace(tmp_path)
    ids = add_project(api)
    service = QueryService(IndexStore(tmp_path / "profile" / workspace_id / "index.sqlite3"))
    PageWriter().confirm(
        root,
        metadata={
            "id": "c0caa4b6-a099-433e-b3a5-8b48266de207",
            "title": "基线页",
            "role": "knowledge",
            "kind": "topic",
            "line_id": ids["line"],
            "project_id": ids["project"],
        },
        body="基线合成知识。",
        confirmation_id="base-confirmation",
        operation_id="base-operation",
    )
    service.rebuild(root, fingerprint="fake-qa-v1")
    before = service.store.status(UUID(workspace_id))
    saved = api.post(
        "/api/v1/journal/log",
        json={
            "title": "自动索引独特事实",
            "body": "蓝色玻璃鲸的代号是独特词鲸蓝九七。",
            "confirmation_id": "journal-confirmation",
            "operation_id": "journal-operation",
        },
    )
    assert saved.status_code == 201, saved.text
    after = service.store.status(UUID(workspace_id))
    assert after["pages"] == before["pages"] + 1
    answer = service.query(
        root, "代号是什么", fingerprint="fake-qa-v1", purpose=RetrievalPurpose.CURRENT
    )
    assert any("鲸蓝九七" in citation.snippet for citation in answer.citations)
