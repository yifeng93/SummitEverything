"""The origin guard must fail closed with the designed envelope.

An unusable settings/credential store used to escape the guard as a bare
``500``: the guard is a middleware, so it sits outside the application's
exception handlers and an unhandled ``SettingsError`` never reached the
handler that renders the documented JSON error. Independent QA found the
consequence: once a profile was corrupt, every request answered
``Internal Server Error`` with no code, no message and no request id, and the
``PATCH`` that would have repaired the profile failed the same way.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "synthetic-origin-guard-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def client(profile_root: Path) -> TestClient:
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile_root,
            secret_backend=MemorySecretBackend(),
        )
    )


def open_workspace(client: TestClient, root: Path) -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={
            "root": str(root),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-origin-guard-test",
        },
    )
    assert opened.status_code == 201


def corrupt_settings(api: TestClient, document: object) -> Path:
    """Write the corrupt document where the guard will read it.

    The profile directory only appears once something writes to it, so the path
    comes from the workspace context the API reports rather than from a guess.
    """
    current = api.get("/api/v1/workspaces/current", headers=HEADERS)
    assert current.status_code == 200
    profile_dir = Path(current.json()["local_profile_dir"])
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "provider-settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_a_corrupt_profile_answers_with_the_designed_envelope(tmp_path):
    profile_root = tmp_path / "profile"
    api = client(profile_root)
    open_workspace(api, tmp_path / "workspace")
    corrupt_settings(api, {"embedding": "not-an-object"})

    for method, path in (
        ("GET", "/api/v1/settings"),
        ("GET", "/api/v1/workspaces/current"),
        ("PATCH", "/api/v1/settings"),
    ):
        payload = {} if method == "PATCH" else None
        response = api.request(method, path, headers=HEADERS, json=payload)
        assert response.status_code == 503, (method, path, response.status_code)
        assert response.headers["content-type"].startswith("application/json")
        error = response.json()["error"]
        assert error["code"] == "settings_unavailable"
        assert error["message"]
        assert error["request_id"]


def test_the_guard_and_the_handler_render_the_same_shape(tmp_path):
    """A route-level SettingsError keeps the same envelope the guard now emits."""
    profile_root = tmp_path / "profile"
    api = client(profile_root)
    open_workspace(api, tmp_path / "workspace")

    guarded = api.get("/api/v1/settings", headers=HEADERS)
    assert guarded.status_code == 200

    route_level = api.request(
        "DELETE",
        "/api/v1/credentials/deepseek",
        headers=HEADERS,
        json={"account_id": "not-the-configured-account"},
    )
    assert route_level.status_code == 422
    route_error = route_level.json()["error"]
    assert route_error["code"] == "validation_error"

    corrupt_settings(api, {"rerank": {"base_url": 5}})
    blocked = api.get("/api/v1/settings", headers=HEADERS)
    guard_error = blocked.json()["error"]
    assert set(guard_error) == set(route_error)
    assert blocked.status_code == 503


def test_a_healthy_profile_still_uses_its_own_callback_origin(tmp_path):
    """The guard keeps working: the stored callback origin stays allowed."""
    profile_root = tmp_path / "profile"
    api = client(profile_root)
    open_workspace(api, tmp_path / "workspace")
    callback = "http://127.0.0.1:18793/api/v1/integrations/feishu/callback"
    saved = api.patch(
        "/api/v1/settings",
        headers=HEADERS,
        json={"feishu": {"app_id": "", "redirect_uri": callback}},
    )
    assert saved.status_code == 200

    allowed = api.get("/api/v1/settings", headers={**HEADERS, "Origin": "http://127.0.0.1:18793"})
    assert allowed.status_code == 200
    forbidden = api.get("/api/v1/settings", headers={**HEADERS, "Origin": "http://evil.invalid"})
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden_origin"
