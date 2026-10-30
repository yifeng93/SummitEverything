from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fake_settings_factory import create_fake_test_app as create_app
from fastapi.testclient import TestClient

from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.settings import EmbeddingSettings, embedding_fingerprint
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.writer import PageWriter


def test_approval_succeeds_when_incremental_local_index_cannot_load_model(tmp_path: Path) -> None:
    token = "offline-local-model-approval-test"
    profile_root = tmp_path / "profiles"
    app = create_app(session_token=token, profile_root=profile_root)
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    root = tmp_path / "workspace"
    workspace = client.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": "create", "name": "模拟库", "operation_id": "workspace"},
    ).json()
    line = client.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = client.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()

    # A valid active index under the chosen local fingerprint makes the next
    # approval take the incremental-update path; embedding is intentionally Fake
    # here so this setup does not prepare or invoke the real local model.
    first_id = uuid4()
    PageWriter().confirm(
        root,
        metadata={
            "id": str(first_id),
            "title": "已确认事实",
            "role": "knowledge",
            "kind": "topic",
            "line_id": line["id"],
            "project_id": project["id"],
        },
        body="隔离模拟的现有事实。",
        confirmation_id="first-confirmation",
        operation_id="first-write",
    )
    local_settings = EmbeddingSettings()
    fingerprint = embedding_fingerprint(local_settings)
    workspace_id = UUID(workspace["workspace_id"])
    QueryService(
        IndexStore(profile_root / str(workspace_id) / "index.sqlite3"), FakeEmbedding()
    ).rebuild(root, fingerprint=fingerprint)

    settings = client.patch(
        "/api/v1/settings",
        json={
            "mode": "real",
            "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": False},
            "embedding": {
                "provider": "local",
                "model": "BAAI/bge-small-zh-v1.5",
                "dimensions": 512,
                "enabled": True,
            },
            "rerank": {
                "provider": "local",
                "model": "BAAI/bge-small-zh-v1.5",
                "dimensions": 512,
                "enabled": True,
            },
        },
    )
    assert settings.status_code == 200, settings.text
    assert settings.json()["local_model"]["state"] == "not_prepared"

    second_id = uuid4()
    confirmation = client.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": str(second_id),
                "title": "新确认事实",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "这项事实必须保存在正式页。",
            "confirmation_id": "second-confirmation",
            "operation_id": "second-write",
        },
    )

    assert confirmation.status_code == 201, confirmation.text
    assert confirmation.json()["saved_locally"] is True
    assert confirmation.json()["index_update"] == "update_failed"
    page = client.get(f"/api/v1/pages/{second_id}")
    assert page.status_code == 200, page.text
    assert page.json()["approval_state"] == "confirmed"
    assert page.json()["body"] == "这项事实必须保存在正式页。"
