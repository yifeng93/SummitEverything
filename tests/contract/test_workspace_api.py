from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app

TOKEN = "test-session-token"


def client() -> TestClient:
    return TestClient(create_app(session_token=TOKEN))


def open_new_workspace(api: TestClient, root: Path) -> dict[str, object]:
    response = api.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "root": str(root),
            "mode": "create",
            "name": "模拟工作库",
            "operation_id": "create-demo",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_legacy_workspace_is_not_silently_initialized(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "_vault").mkdir()
    (root / "existing.md").write_text("preserve me", encoding="utf-8")

    response = client().post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"root": str(root), "mode": "create", "name": "Demo", "operation_id": "op-1"},
    )

    assert response.status_code == 409
    assert not (root / ".summit-everything" / "manifest.json").exists()
    assert (root / "existing.md").read_text(encoding="utf-8") == "preserve me"


def test_workspace_creation_retry_reuses_the_same_identity(tmp_path: Path) -> None:
    api = client()
    root = tmp_path / "new"
    payload = {
        "root": str(root),
        "mode": "create",
        "name": "Retry-safe workspace",
        "operation_id": "workspace-create-intent",
    }

    first = api.post(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {TOKEN}"}, json=payload
    )
    retry = api.post(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {TOKEN}"}, json=payload
    )

    assert first.status_code == retry.status_code == 201
    assert retry.json()["workspace_id"] == first.json()["workspace_id"]
    different_payload = {**payload, "name": "Different name"}
    conflict = api.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=different_payload,
    )
    assert conflict.status_code == 409


def test_workspace_mutations_require_session_token(tmp_path: Path) -> None:
    response = client().post(
        "/api/v1/workspaces",
        json={
            "root": str(tmp_path / "new"),
            "mode": "create",
            "name": "Demo",
            "operation_id": "op-1",
        },
    )
    assert response.status_code == 401
    assert not (tmp_path / "new").exists()


def test_request_validation_uses_the_stable_error_envelope() -> None:
    response = client().post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"root": "/tmp/demo", "mode": "unexpected", "operation_id": "op-1"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert isinstance(response.json()["error"]["request_id"], str)


def test_line_and_project_names_change_without_changing_ids(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "线甲", "operation_id": "line-create"})
    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    renamed = api.patch(
        f"/api/v1/lines/{line_id}", json={"name": "线乙", "operation_id": "line-rename"}
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["id"] == line_id
    assert renamed.json()["name"] == "线乙"
    conflict = api.patch(
        f"/api/v1/lines/{line_id}",
        json={"name": "另一个名称", "operation_id": "line-rename"},
    )
    assert conflict.status_code == 409

    project = api.post(
        "/api/v1/projects",
        json={"line_id": line_id, "name": "项目甲", "operation_id": "project-create"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    project_rename = api.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "项目乙", "operation_id": "project-rename"},
    )
    assert project_rename.status_code == 200
    assert project_rename.json()["id"] == project_id


def test_repeated_creation_intent_returns_the_same_organization_id(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")

    first = api.post("/api/v1/lines", json={"name": "唯一线", "operation_id": "same-line-op"})
    retry = api.post("/api/v1/lines", json={"name": "唯一线", "operation_id": "same-line-op"})

    assert first.status_code == retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]
    assert len(api.get("/api/v1/lines").json()) == 1


def test_nonempty_line_and_project_deletion_is_rejected(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "线甲", "operation_id": "line-create"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "项目甲", "operation_id": "project-create"},
    ).json()
    project_dir = tmp_path / "new" / project["directory"]
    (project_dir / "page.md").write_text("retained content", encoding="utf-8")

    assert (
        api.delete(
            f"/api/v1/lines/{line['id']}", params={"operation_id": "line-delete"}
        ).status_code
        == 409
    )
    assert (
        api.delete(
            f"/api/v1/projects/{project['id']}", params={"operation_id": "project-delete"}
        ).status_code
        == 409
    )


def test_page_reader_returns_only_validated_knowledge_pages(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    page_id = "00000000-0000-4000-8000-000000000123"
    page_path = tmp_path / "new" / project["directory"] / "示例.md"
    page_path.write_text(
        "---\n"
        f"id: {page_id}\ntitle: 模拟事实\nrole: knowledge\nkind: object\n"
        f"line_id: {line['id']}\nproject_id: {project['id']}\n"
        "extra_business_field: preserved\n---\n这是隔离测试正文。\n",
        encoding="utf-8",
    )

    response = api.get("/api/v1/pages")

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["page_id"] == page_id
    assert response.json()[0]["approval_state"] == "pending"
    assert response.json()[0]["metadata"]["extra_business_field"] == "preserved"


def test_page_reader_rejects_duplicate_ids_path_escape_and_wrong_project(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "线甲", "operation_id": "line-create"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "项目甲", "operation_id": "project-create"},
    ).json()
    workspace = tmp_path / "new"
    pages_dir = workspace / project["directory"]
    bad_page = pages_dir / "bad.md"
    bad_page.write_text(
        "---\nid: 00000000-0000-4000-8000-000000000001\ntitle: Bad\nrole: knowledge\n"
        "kind: object\nline_id: 00000000-0000-4000-8000-000000000099\n"
        f"project_id: {project['id']}\n---\ncontent\n",
        encoding="utf-8",
    )

    assert api.get("/api/v1/pages").status_code == 422
    bad_page.unlink()
    outside = tmp_path / "escape.md"
    outside.write_text("---\nid: nope\n---\n", encoding="utf-8")
    manifest_path = workspace / ".summit-everything" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projects"][0]["directory"] = "../../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert api.get("/api/v1/projects").status_code == 422
    assert outside.exists()


def test_page_reader_rejects_duplicate_page_ids(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "项目", "operation_id": "project"},
    ).json()
    page_id = "00000000-0000-4000-8000-000000000077"
    for filename in ("first.md", "second.md"):
        (tmp_path / "new" / project["directory"] / filename).write_text(
            "---\n"
            f"id: {page_id}\ntitle: {filename}\nrole: knowledge\nkind: object\n"
            f"line_id: {line['id']}\nproject_id: {project['id']}\n---\ntext\n",
            encoding="utf-8",
        )

    response = api.get("/api/v1/pages")

    assert response.status_code == 422
    assert "duplicate page IDs" in response.json()["error"]["message"]


def test_page_reader_rejects_markdown_symlink_outside_workspace(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "路径线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "路径项目", "operation_id": "project"},
    ).json()
    outside = tmp_path / "outside.md"
    outside.write_text(
        "---\n"
        "id: 00000000-0000-4000-8000-000000000999\ntitle: 外部页面\n"
        "role: knowledge\nkind: object\n"
        f"line_id: {line['id']}\nproject_id: {project['id']}\n---\nprivate canary\n",
        encoding="utf-8",
    )
    (tmp_path / "new" / project["directory"] / "linked.md").symlink_to(outside)

    response = api.get("/api/v1/pages")

    assert response.status_code == 422
    assert "symlink" in response.json()["error"]["message"]


def test_malformed_frontmatter_is_a_validation_error_not_a_server_crash(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "格式线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "格式项目", "operation_id": "project"},
    ).json()
    malformed = tmp_path / "new" / project["directory"] / "malformed.md"
    malformed.write_text(
        "---\nid: 00000000-0000-4000-8000-000000000876\ntitle: malformed\n"
        "role: [knowledge]\nkind: object\n"
        f"line_id: {line['id']}\nproject_id: {project['id']}\n---\nbody\n",
        encoding="utf-8",
    )

    response = api.get("/api/v1/pages")

    assert response.status_code == 422


def test_page_confirmation_route_writes_only_after_explicit_confirmation(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "确认线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "确认项目", "operation_id": "project"},
    ).json()
    metadata = {
        "id": "00000000-0000-4000-8000-000000000234",
        "title": "待确认事实",
        "role": "knowledge",
        "kind": "object",
        "line_id": line["id"],
        "project_id": project["id"],
        "approval": {"confirmed": True},
    }
    payload = {
        "metadata": metadata,
        "body": "这是一份隔离模拟稿。\n",
        "confirmation_id": "operator-explicitly-confirmed",
        "operation_id": "confirm-page",
    }

    result = api.post("/api/v1/pages", json=payload)

    assert result.status_code == 201, result.text
    snapshot = api.get(f"/api/v1/pages/{metadata['id']}").json()
    assert snapshot["approval_state"] == "confirmed"
    assert snapshot["metadata"]["approval"]["confirmation_id"] == payload["confirmation_id"]
    assert snapshot["metadata"]["approval"]["version"] == 1
    assert "raw_sha256" not in snapshot


def test_page_confirmation_refuses_stale_review_base(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "确认线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "确认项目", "operation_id": "project"},
    ).json()
    metadata = {
        "id": "00000000-0000-4000-8000-000000000235",
        "title": "待确认事实",
        "role": "knowledge",
        "kind": "object",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    created = api.post(
        "/api/v1/pages",
        json={
            "metadata": metadata,
            "body": "第一稿。\n",
            "confirmation_id": "first-confirmation",
            "operation_id": "page-create",
        },
    )
    assert created.status_code == 201, created.text
    snapshot = api.get(f"/api/v1/pages/{metadata['id']}").json()
    page_path = tmp_path / "new" / snapshot["relative_path"]
    page_path.write_text(
        page_path.read_text(encoding="utf-8").replace("第一稿", "外部编辑"), encoding="utf-8"
    )
    assert api.get(f"/api/v1/pages/{metadata['id']}").json()["approval_state"] == "invalid"

    response = api.post(
        f"/api/v1/pages/{metadata['id']}/confirmations",
        json={
            "metadata": metadata,
            "body": "覆盖稿。\n",
            "expected_base_sha256": snapshot["content_sha256"],
            "confirmation_id": "second-confirmation",
            "operation_id": "page-update",
        },
    )

    assert response.status_code == 409
    assert "外部编辑" in page_path.read_text(encoding="utf-8")


def test_page_move_route_keeps_same_project_references_valid(tmp_path: Path) -> None:
    api = client()
    api.headers.update({"Authorization": f"Bearer {TOKEN}"})
    open_new_workspace(api, tmp_path / "new")
    line = api.post("/api/v1/lines", json={"name": "移动线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "移动项目", "operation_id": "project"},
    ).json()
    target_metadata = {
        "id": "00000000-0000-4000-8000-000000000441",
        "title": "目标页",
        "role": "knowledge",
        "kind": "object",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    source = api.post(
        "/api/v1/pages",
        json={
            "metadata": target_metadata,
            "body": "可移动事实。\n",
            "confirmation_id": "target-confirmation",
            "operation_id": "create-target",
        },
    )
    assert source.status_code == 201
    link_metadata = {
        **target_metadata,
        "id": "00000000-0000-4000-8000-000000000442",
        "title": "引用页",
    }
    api.post(
        "/api/v1/pages",
        json={
            "metadata": link_metadata,
            "body": "链接 [目标](目标页.md)。\n",
            "confirmation_id": "link-confirmation",
            "operation_id": "create-link",
        },
    )
    destination = f"{project['directory']}/历史/目标页.md"

    moved = api.post(
        f"/api/v1/pages/{target_metadata['id']}/moves",
        json={"destination_relative_path": destination, "operation_id": "move-page"},
    )

    assert moved.status_code == 200, moved.text
    assert api.get(f"/api/v1/pages/{target_metadata['id']}").json()["relative_path"] == destination
    link_snapshot = api.get(f"/api/v1/pages/{link_metadata['id']}").json()
    assert "[目标](历史/目标页.md)" in link_snapshot["body"]
    assert link_snapshot["approval_state"] == "confirmed"
