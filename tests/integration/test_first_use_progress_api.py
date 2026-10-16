"""First-use wizard progress API (frontend milestone D repair1).

Durable, profile+workspace scoped, non-secret progress over a typed contract.
The browser can no longer be the only copy: the production WKWebView uses
non-persistent storage, so a restart used to lose "first use completed" and show
the workspace gate plus wizard step 2 again.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-session"}


def build(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            session_token="synthetic-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )


def open_workspace(
    client: TestClient, root: Path, name: str, operation: str, *, mode: str = "create"
) -> dict[str, object]:
    response = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={"root": str(root), "mode": mode, "name": name, "operation_id": operation},
    )
    assert response.status_code == 201
    return response.json()


def test_absent_progress_is_reported_as_absent_not_as_a_default(tmp_path: Path) -> None:
    client = build(tmp_path)
    open_workspace(client, tmp_path / "workspace", "模拟库", "open-progress-absent")

    response = client.get("/api/v1/first-use/progress", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "first_use_progress_absent"


def test_progress_round_trips_and_survives_a_restarted_app(tmp_path: Path) -> None:
    client = build(tmp_path)
    open_workspace(client, tmp_path / "workspace", "模拟库", "open-progress-write")

    written = client.put(
        "/api/v1/first-use/progress",
        headers=HEADERS,
        json={"step": 4, "completed": False, "open": True},
    )
    assert written.status_code == 200
    assert written.json() == {"step": 4, "completed": False, "open": True}
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).json() == {
        "step": 4,
        "completed": False,
        "open": True,
    }

    # A brand-new app object over the same profile root is what a process
    # restart looks like; the progress must come back from disk.
    restarted = build(tmp_path)
    open_workspace(
        restarted, tmp_path / "workspace", "模拟库", "reopen-progress-restart", mode="open"
    )
    assert restarted.get("/api/v1/first-use/progress", headers=HEADERS).json() == {
        "step": 4,
        "completed": False,
        "open": True,
    }


def test_completed_progress_is_durable(tmp_path: Path) -> None:
    client = build(tmp_path)
    open_workspace(client, tmp_path / "workspace", "模拟库", "open-progress-complete")

    client.put(
        "/api/v1/first-use/progress",
        headers=HEADERS,
        json={"step": 5, "completed": True, "open": False},
    )

    assert client.get("/api/v1/first-use/progress", headers=HEADERS).json() == {
        "step": 5,
        "completed": True,
        "open": False,
    }


def test_progress_is_isolated_between_workspaces_and_profiles(tmp_path: Path) -> None:
    client = build(tmp_path)
    first = open_workspace(client, tmp_path / "workspace-a", "甲库", "open-progress-a")
    client.put(
        "/api/v1/first-use/progress",
        headers=HEADERS,
        json={"step": 3, "completed": False, "open": True},
    )

    second = open_workspace(client, tmp_path / "workspace-b", "乙库", "open-progress-b")
    assert first["local_profile_dir"] != second["local_profile_dir"]
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).status_code == 404

    open_workspace(client, tmp_path / "workspace-a", "甲库", "reopen-progress-a", mode="open")
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).json() == {
        "step": 3,
        "completed": False,
        "open": True,
    }

    # A second profile root (another machine profile) must not see the record.
    other_profile = TestClient(
        create_app(
            session_token="synthetic-session",
            profile_root=tmp_path / "other-profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(
        other_profile, tmp_path / "workspace-a", "甲库", "open-progress-other", mode="open"
    )
    assert other_profile.get("/api/v1/first-use/progress", headers=HEADERS).status_code == 404


def test_rejects_illegal_steps_and_unknown_or_secret_fields(tmp_path: Path) -> None:
    client = build(tmp_path)
    open_workspace(client, tmp_path / "workspace", "模拟库", "open-progress-invalid")

    for payload in (
        {"step": 1, "completed": False, "open": True},
        {"step": 6, "completed": False, "open": True},
        # QA D-4：整数值 JSON 浮点曾被 Literal 归一化接受，现在必须 422。
        {"step": 3.0, "completed": False, "open": True},
        {"step": 4.5, "completed": False, "open": True},
        {"step": True, "completed": False, "open": True},
        {"step": 3, "completed": False, "open": True, "secret": "sk-synthetic-00000000"},
        {"step": 3, "completed": False, "open": True, "api_key": "sk-synthetic-00000000"},
    ):
        response = client.put("/api/v1/first-use/progress", headers=HEADERS, json=payload)
        assert response.status_code == 422, payload
        assert "synthetic" not in response.text

    # A rejected payload is never stored.
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).status_code == 404


def test_requires_a_session_token_and_an_open_workspace(tmp_path: Path) -> None:
    client = build(tmp_path)
    assert client.get("/api/v1/first-use/progress").status_code == 401
    assert (
        client.put(
            "/api/v1/first-use/progress",
            headers=HEADERS,
            json={"step": 2, "completed": False, "open": True},
        ).status_code
        == 409
    )
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).status_code == 409


def test_an_unwritable_store_fails_visibly_instead_of_pretending_to_save(tmp_path: Path) -> None:
    client = build(tmp_path)
    opened = open_workspace(client, tmp_path / "workspace", "模拟库", "open-progress-failure")
    # Occupy the store path with a directory: the atomic replace can never land.
    Path(str(opened["local_profile_dir"]), "first-use-progress.json").mkdir(parents=True)

    written = client.put(
        "/api/v1/first-use/progress",
        headers=HEADERS,
        json={"step": 3, "completed": False, "open": True},
    )
    assert written.status_code == 503
    assert written.json()["error"]["code"] == "progress_unavailable"
    assert client.get("/api/v1/first-use/progress", headers=HEADERS).status_code == 503
