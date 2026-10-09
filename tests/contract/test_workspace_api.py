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
