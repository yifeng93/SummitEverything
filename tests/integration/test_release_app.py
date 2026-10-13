import asyncio
import hashlib
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from starlette.requests import Request

from summit_everything.api.app import create_app
from summit_everything.integrations.llm import LLMProviderError
from summit_everything.workspace.manifest import WorkspaceError
from summit_everything.workspace.writer import WorkspaceWriteConflict


def digest_tree(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def write_manifest(path, frontend_sha256):
    dependencies = b'{"python_packages":[]}'
    path.with_name("dependencies.json").write_bytes(dependencies)
    path.write_text(
        json.dumps(
            {
                "source_sha": "a" * 40,
                "dirty": False,
                "build_id": "test-build",
                "app_version": "0.1.0",
                "frontend_sha256": frontend_sha256,
                "dependencies_sha256": hashlib.sha256(dependencies).hexdigest(),
            }
        ),
        encoding="utf-8",
    )


def test_release_health_and_static_webui_are_bound_to_build_identity(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<!doctype html><title>Internal UI</title>", encoding="utf-8")
    (web / "asset.js").write_text("window.app = true", encoding="utf-8")
    manifest = tmp_path / "build-info.json"
    frontend_sha256 = digest_tree(web)
    write_manifest(manifest, frontend_sha256)
    monkeypatch.setenv("SUMMIT_BUILD_INFO", str(manifest))
    monkeypatch.setenv("SUMMIT_WEB_DIST", str(web))
    monkeypatch.setenv("SUMMIT_RUN_ID", "test-run")
    client = TestClient(create_app(session_token="secret-test", profile_root=tmp_path / "profile"))

    health = client.get("/api/v1/health").json()
    assert health == {
        "service": "ready",
        "workspace_open": False,
        "version": "1.0.0",
        "run_id": "test-run",
        "source_sha": "a" * 40,
        "dirty": False,
        "build_id": "test-build",
        "app_version": "0.1.0",
        "frontend_sha256": frontend_sha256,
        "dependencies_sha256": hashlib.sha256(b'{"python_packages":[]}').hexdigest(),
    }
    assert client.get("/").status_code == 200
    assert client.get("/asset.js").text == "window.app = true"
    assert client.get("/%2e%2e/build-info.json").status_code == 404


def test_release_refuses_tampered_frontend_resources(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("tampered", encoding="utf-8")
    manifest = tmp_path / "build-info.json"
    write_manifest(manifest, "b" * 64)
    monkeypatch.setenv("SUMMIT_BUILD_INFO", str(manifest))
    monkeypatch.setenv("SUMMIT_WEB_DIST", str(web))
    try:
        create_app(session_token="test", profile_root=tmp_path / "profile")
    except ValueError as exc:
        assert "frontend" in str(exc).lower()
    else:
        raise AssertionError("frontend resources must match the embedded build identity")


def test_release_build_manifest_is_required_when_path_is_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("SUMMIT_BUILD_INFO", str(tmp_path / "missing.json"))
    try:
        create_app(session_token="test", profile_root=tmp_path / "profile")
    except ValueError as exc:
        assert "build manifest" in str(exc).lower()
    else:
        raise AssertionError("missing release manifest must fail closed")


def test_api_exception_messages_do_not_echo_credentials_or_paths(tmp_path):
    app = create_app(session_token="api-redaction-test", profile_root=tmp_path / "profile")
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/test",
            "raw_path": b"/api/v1/test",
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 1),
            "client": ("127.0.0.1", 2),
        }
    )
    request.state.request_id = "test-request"
    sentinel = "credential-sentinel-7e7a"
    exceptions = (
        WorkspaceError(f"{sentinel} /private/profile", 400),
        WorkspaceWriteConflict(f"{sentinel} /private/profile"),
        LLMProviderError(f"{sentinel} /private/profile"),
    )
    for exception in exceptions:
        handler = app.exception_handlers[type(exception)]
        response = asyncio.run(handler(request, exception))
        assert sentinel not in response.body.decode()


def test_sse_query_error_does_not_echo_provider_exception(tmp_path):
    sentinel = "credential-sentinel-c8d1"

    class ExplodingQuery:
        def query(self, *args, **kwargs):
            raise RuntimeError(f"{sentinel} /private/profile")

    token = "synthetic-session-token"
    profile = tmp_path / "profile"
    client = TestClient(
        create_app(session_token=token, profile_root=profile, query_service=ExplodingQuery())
    )
    headers = {"Authorization": f"Bearer {token}"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "合成库",
            "operation_id": "ws",
        },
    )
    assert opened.status_code == 201, opened.text
    response = client.post(
        "/api/v1/queries",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "question": "合成问题",
            "fingerprint": "fake-v1",
            "purpose": "current",
        },
    )
    assert response.status_code == 200
    assert sentinel not in response.text
    assert "查询未能完成，请稍后重试。" in response.text
