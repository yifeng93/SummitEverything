from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "legacy-index-rebuild-token"


class CountingEmbedding(FakeEmbedding):
    calls = 0

    def embed_many(self, texts: list[str], *, fingerprint: str) -> list[list[float]]:
        self.calls += len(texts)
        return super().embed_many(texts, fingerprint=fingerprint)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_legacy_index_status_query_and_plan_remain_read_only_without_local_model(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "profile" / "index.sqlite3"
    index_path.parent.mkdir(parents=True)
    old_page_id = uuid4()
    old_vector = json.dumps([0.25, 0.5, 0.75])
    with sqlite3.connect(index_path) as connection:
        connection.execute(
            """CREATE TABLE active_generations (
                 workspace_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL
               )"""
        )
        connection.execute(
            """CREATE TABLE chunks (
                 workspace_id TEXT NOT NULL, fingerprint TEXT NOT NULL, page_id TEXT NOT NULL,
                 content_sha256 TEXT NOT NULL, chunk_id TEXT NOT NULL, heading TEXT NOT NULL,
                 text TEXT NOT NULL, vector_json TEXT NOT NULL,
                 PRIMARY KEY (workspace_id, fingerprint, chunk_id))"""
        )
        connection.execute(
            "INSERT INTO active_generations (workspace_id, fingerprint) VALUES (?, ?)",
            ("workspace-pending", "legacy-fake64"),
        )
        connection.execute(
            """INSERT INTO chunks (workspace_id, fingerprint, page_id, content_sha256,
               chunk_id, heading, text, vector_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "workspace-pending",
                "legacy-fake64",
                str(old_page_id),
                "a" * 64,
                "legacy-chunk",
                "旧向量样本",
                "这段旧文本不得被读取或引用。",
                old_vector,
            ),
        )

    embedding = CountingEmbedding()
    store = IndexStore(index_path)
    service = QueryService(store, embedding=embedding)
    api = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=index_path.parent,
            query_service=service,
        )
    )
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    root = tmp_path / "workspace"
    opened = api.post(
        "/api/v1/workspaces",
        json={"root": str(root), "mode": "create", "name": "旧索引重建测试", "operation_id": "ws"},
    )
    assert opened.status_code == 201, opened.text
    workspace_id = opened.json()["workspace_id"]
    with sqlite3.connect(index_path) as connection:
        connection.execute(
            "UPDATE active_generations SET workspace_id = ? WHERE workspace_id = ?",
            (workspace_id, "workspace-pending"),
        )
        connection.execute(
            "UPDATE chunks SET workspace_id = ? WHERE workspace_id = ?",
            (workspace_id, "workspace-pending"),
        )
    # Simulate a profile saved by the older release. New settings writes no
    # longer allow selecting this provider, but existing local files still load.
    workspace = api.get("/api/v1/workspaces/current").json()
    provider_settings = Path(workspace["local_profile_dir"]) / "provider-settings.json"
    provider_settings.parent.mkdir(parents=True, exist_ok=True)
    provider_settings.write_text(
        json.dumps(
            {
                "mode": "real",
                "embedding": {
                    "provider": "dashscope",
                    "model": "qwen3.7-text-embedding",
                    "enabled": True,
                },
            }
        ),
        encoding="utf-8",
    )

    line = api.post("/api/v1/lines", json={"name": "合成线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    page = api.post(
        "/api/v1/pages",
        json={
            "metadata": {
                "id": str(uuid4()),
                "title": "已确认的合成知识",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "本页只作为从已确认 Markdown 重建的合成内容。",
            "confirmation_id": "confirm-page",
            "operation_id": "page",
        },
    )
    assert page.status_code == 201, page.text
    assert page.json()["index_update"] == "not_enabled"
    assert embedding.calls == 0
    fake_mode = api.patch("/api/v1/settings", json={"mode": "fake"})
    assert fake_mode.status_code == 422, fake_mode.text

    before = _sha256(index_path)
    with sqlite3.connect(index_path) as connection:
        columns_before = [
            row[1] for row in connection.execute("PRAGMA table_info(active_generations)")
        ]
        tables_before = sorted(
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        )
        legacy_before = connection.execute(
            "SELECT workspace_id, chunk_id, vector_json FROM chunks"
        ).fetchall()
    assert legacy_before == [(workspace_id, "legacy-chunk", old_vector)]
    status = api.get("/api/v1/index/status")
    assert status.status_code == 200, status.text
    assert status.json()["state"] == "not_ready"
    assert status.json()["reason"] == "legacy_vectors_require_rebuild"
    assert "已确认的 Markdown" in status.json()["message"]

    query = api.post(
        "/api/v1/queries",
        json={"question": "旧向量样本是什么", "fingerprint": "legacy-fake64", "purpose": "current"},
    )
    assert query.status_code == 409, query.text
    assert "当前本机索引尚未按已选向量模型准备完成" in query.text
    assert "这段旧文本不得被读取或引用" not in query.text
    assert embedding.calls == 0

    plan_response = api.post(
        "/api/v1/index/plans",
        json={"mode": "initial", "fingerprint": "summit-fake-embedding-v1"},
    )
    assert plan_response.status_code == 200, plan_response.text
    plan = plan_response.json()
    assert plan["mode"] == "initial"
    assert len(plan["page_ids"]) == 1
    assert embedding.calls == 0
    assert _sha256(index_path) == before
    with sqlite3.connect(index_path) as connection:
        assert [
            row[1] for row in connection.execute("PRAGMA table_info(active_generations)")
        ] == columns_before
        assert (
            sorted(
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            )
            == tables_before
        )
        assert (
            connection.execute("SELECT workspace_id, chunk_id, vector_json FROM chunks").fetchall()
            == legacy_before
        )

    built = api.post("/api/v1/index/jobs", json=plan)
    assert built.status_code == 409, built.text
    assert built.json()["error"]["code"] == "local_model_not_ready"
    assert embedding.calls == 0
    assert api.get("/api/v1/index/status").json()["state"] == "not_ready"
    with sqlite3.connect(index_path) as connection:
        source = connection.execute(
            "SELECT vector_json FROM chunks WHERE workspace_id = ? AND chunk_id = ?",
            (workspace_id, "legacy-chunk"),
        ).fetchone()
        assert source == (old_vector,)
