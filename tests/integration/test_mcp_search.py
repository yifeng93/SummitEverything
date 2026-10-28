from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.domain.models import WorkspaceContext
from summit_everything.retrieval.chunking import TextChunk
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.reader import read_page
from summit_everything.workspace.writer import PageWriter


def _api(tmp_path: Path, token: str = "search-token") -> tuple[TestClient, Path, WorkspaceContext]:
    root = tmp_path / "workspace"
    context = create_workspace(root, "MCP 搜索合成库", tmp_path / "profiles", "workspace")
    app = create_app(session_token=token, profile_root=tmp_path / "profiles")
    client = TestClient(app)
    response = client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"root": str(root), "mode": "open", "operation_id": "open"},
    )
    assert response.status_code == 201
    context = WorkspaceContext.model_validate(response.json())
    return client, root, context


def test_agent_search_requires_new_index_and_requests_explicit_legacy_rebuild(
    tmp_path: Path,
) -> None:
    client, _root, context = _api(tmp_path)
    headers = {
        "Authorization": "Bearer search-token",
        "X-Summit-Workspace-Id": str(context.workspace_id),
    }
    response = client.get("/api/v1/agent/search", params={"q": "消防验收"}, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "index_not_ready"

    db_path = Path(context.local_profile_dir) / "index.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("DROP TABLE active_generations")
        db.execute(
            "CREATE TABLE active_generations ("
            "workspace_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO active_generations(workspace_id, fingerprint) VALUES (?, ?)",
            (str(context.workspace_id), "legacy-vector-json"),
        )
    legacy = client.get("/api/v1/agent/search", params={"q": "消防验收"}, headers=headers)
    assert legacy.status_code == 409
    assert legacy.json()["error"]["code"] == "index_rebuild_required"


def test_agent_bm25_search_rechecks_current_page_hash_and_eligibility(tmp_path: Path) -> None:
    client, root, context = _api(tmp_path)
    token_headers = {"Authorization": "Bearer search-token"}
    line = create_line(root, "主线", "line")
    project = create_project(root, line.id, "项目", "project")
    current_id = uuid4()
    current_meta = {
        "id": str(current_id),
        "role": "knowledge",
        "kind": "topic",
        "validity": "current",
        "title": "当前消防验收",
        "line_id": str(line.id),
        "project_id": str(project.id),
    }
    PageWriter().confirm(
        root,
        metadata=current_meta,
        body="云杉大厦消防验收记录，当前疏散通道复核。",
        confirmation_id="user-confirmed-current",
        operation_id="confirmed-page",
    )
    current_page = read_page(root, current_id)
    old_id = uuid4()
    old_meta = {
        **current_meta,
        "id": str(old_id),
        "validity": "superseded",
        "title": "历史消防验收",
    }
    PageWriter().confirm(
        root,
        metadata=old_meta,
        body="云杉大厦消防验收历史版本。",
        confirmation_id="user-confirmed-old",
        operation_id="old-page",
    )
    old_page = read_page(root, old_id)
    pending_id = uuid4()
    pending_page_path = root / project.directory / "unconfirmed.md"
    pending_page_path.write_text(
        "---\n"
        f"id: {pending_id}\nrole: knowledge\nkind: topic\nvalidity: current\n"
        "title: 未确认消防验收\n"
        f"line_id: {line.id}\nproject_id: {project.id}\n"
        "---\n云杉大厦消防验收尚未确认。\n",
        encoding="utf-8",
    )
    pending_page = read_page(root, pending_id)
    store = IndexStore(Path(context.local_profile_dir) / "index.sqlite3")
    chunks = []
    for page in (current_page, old_page, pending_page):
        chunks.append(
            (
                TextChunk(
                    page_id=page.page_id,
                    content_sha256=page.content_sha256,
                    chunk_id=f"chunk-{page.page_id}",
                    heading="消防验收",
                    text=page.body,
                ),
                [1.0, 0.0],
            )
        )
    store.replace_generation(
        context.workspace_id,
        "synthetic-bm25",
        chunks,
        expected_generation=None,
        vector_dimension=2,
    )
    workspace_headers = {
        **token_headers,
        "X-Summit-Workspace-Id": str(context.workspace_id),
    }
    response = client.get(
        "/api/v1/agent/search",
        params={"q": "云杉大厦消防验收"},
        headers=workspace_headers,
    )
    assert response.status_code == 200, response.text
    hits = response.json()
    assert [hit["page_id"] for hit in hits] == [str(current_id)]
    assert "bm25_score" in hits[0]

    file_path = root / current_page.relative_path
    raw = file_path.read_text(encoding="utf-8")
    file_path.write_text(raw.replace("当前疏散通道", "外部修改的通道"), encoding="utf-8")
    stale_search = client.get(
        "/api/v1/agent/search",
        params={"q": "云杉大厦消防验收"},
        headers=workspace_headers,
    )
    assert stale_search.status_code == 200 and stale_search.json() == []
    stale_read = client.get(
        f"/api/v1/agent/pages/{current_id}",
        params={"expected_content_sha256": current_page.content_sha256},
        headers=workspace_headers,
    )
    assert stale_read.status_code == 409
