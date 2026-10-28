"""Smoke a relocated internal bundle backend without development tools or credentials."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

_LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(base: str, path: str, *, headers: dict[str, str] | None = None) -> object:
    try:
        return _LOOPBACK_OPENER.open(
            urllib.request.Request(base + path, headers=headers or {}), timeout=1
        )
    except urllib.error.HTTPError as error:
        return error


def api(
    base: str,
    token: str,
    path: str,
    *,
    payload: object | None = None,
    method: str | None = None,
) -> object:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request_value = urllib.request.Request(
        base + path, data=data, headers=headers, method=method or ("POST" if data else "GET")
    )
    with _LOOPBACK_OPENER.open(request_value, timeout=10) as response:
        body = response.read()
        if response.headers.get_content_type() == "text/event-stream":
            return [
                json.loads(line[6:])
                for line in body.decode("utf-8").splitlines()
                if line.startswith("data: ")
            ]
        return json.loads(body) if body else None


def wait_ready(process: subprocess.Popen[bytes], base: str) -> None:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"backend exited early: {process.returncode}")
        try:
            response = request(base, "/api/v1/health")
            if response.status == 200:
                return
        except (OSError, TimeoutError):
            time.sleep(0.25)
    raise AssertionError("packaged backend readiness timed out")


def start_backend(backend: Path, environment: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(backend)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
    )


def index_and_query(base: str, token: str, workspace_root: Path, *, create: bool) -> None:
    if create:
        api(
            base,
            token,
            "/api/v1/workspaces",
            payload={
                "root": str(workspace_root),
                "mode": "create",
                "name": "LanceDB 合成验收",
                "operation_id": "synthetic-workspace-create",
            },
        )
        line = api(
            base,
            token,
            "/api/v1/lines",
            payload={"name": "合成主线", "operation_id": "synthetic-line"},
        )
        project = api(
            base,
            token,
            "/api/v1/projects",
            payload={
                "line_id": line["id"],
                "name": "合成项目",
                "operation_id": "synthetic-project",
            },
        )
        page = api(
            base,
            token,
            "/api/v1/pages",
            payload={
                "metadata": {
                    "id": str(uuid4()),
                    "title": "云杉大厦消防验收",
                    "role": "knowledge",
                    "kind": "topic",
                    "line_id": line["id"],
                    "project_id": project["id"],
                },
                "body": "云杉大厦消防验收结论为合格，疏散通道保持畅通。",
                "confirmation_id": "synthetic-confirmation",
                "operation_id": "synthetic-page-confirm",
            },
        )
        assert page["changed_paths"]
    else:
        opened = api(
            base,
            token,
            "/api/v1/workspaces",
            payload={
                "root": str(workspace_root),
                "mode": "open",
                "operation_id": "synthetic-workspace-open",
            },
        )
        assert Path(opened["root"]).resolve() == workspace_root.resolve(), (
            opened["root"],
            str(workspace_root),
        )

    status = api(base, token, "/api/v1/index/status")
    if create:
        assert status["state"] == "not_ready"
        plan = api(
            base,
            token,
            "/api/v1/index/plans",
            payload={"mode": "initial", "fingerprint": "summit-fake-embedding-v1"},
        )
        result = api(base, token, "/api/v1/index/jobs", payload=plan)
        assert result["indexed_pages"] == 1 and result["indexed_chunks"] > 0
    else:
        assert status["state"] == "ready" and status["chunks"] > 0

    events = api(
        base,
        token,
        "/api/v1/queries",
        payload={
            "request_id": str(uuid4()),
            "question": "云杉大厦消防验收结论是什么？",
            "fingerprint": "summit-fake-embedding-v1",
            "purpose": "current",
            "answer_mode": "fact",
        },
    )
    terminal = next((event for event in events if event["type"] == "completed"), None)
    if terminal is None:
        raise AssertionError(f"synthetic query did not complete: {events!r}")
    if not terminal["data"].get("citations"):
        raise AssertionError("synthetic query did not return a qualified citation")


def main() -> int:
    app = Path(os.environ["SUMMIT_APP"]).resolve()
    with tempfile.TemporaryDirectory(prefix="summit-app-relocation-") as temporary:
        root = Path(temporary)
        copied = root / app.name
        shutil.copytree(app, copied)
        contents = copied / "Contents"
        resources = contents / "Resources"
        identity = json.loads((resources / "build-info.json").read_text(encoding="utf-8"))
        port = int(os.environ.get("SUMMIT_SMOKE_PORT", "18793"))
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError("smoke port is occupied before the test") from exc

        token = "synthetic-internal-smoke-token"
        environment = {
            "PATH": "",
            "HOME": str(root),
            "TMPDIR": str(root),
            "SUMMIT_PROFILE_ROOT": str(root / "profile"),
            "SUMMIT_API_PORT": str(port),
            "SUMMIT_WEB_PORT": str(port),
            "SUMMIT_RUN_ID": "synthetic-run",
            "SUMMIT_SESSION_TOKEN": token,
            "SUMMIT_BUILD_INFO": str(resources / "build-info.json"),
            "SUMMIT_WEB_DIST": str(resources / "web"),
        }
        backend = resources / "backend" / "summit-backend" / "summit-backend"
        process = start_backend(backend, environment)
        base = f"http://127.0.0.1:{port}"
        try:
            wait_ready(process, base)
            health = json.loads(request(base, "/api/v1/health").read())
            expected = {
                "run_id": "synthetic-run",
                "source_sha": identity["source_sha"],
                "dirty": identity["dirty"],
                "build_id": identity["build_id"],
                "app_version": identity["app_version"],
                "frontend_sha256": identity["frontend_sha256"],
                "dependencies_sha256": identity["dependencies_sha256"],
            }
            if any(health.get(key) != value for key, value in expected.items()):
                raise AssertionError("health identity differs from the embedded manifest")
            if request(base, "/").status != 200:
                raise AssertionError("packaged WebUI did not serve its entry point")
            if request(base, "/api/v1/workspaces/current").status != 401:
                raise AssertionError("unauthenticated workspace read was accepted")
            unauthorized_write = urllib.request.Request(
                base + "/api/v1/workspaces",
                data=b'{"root":"/tmp/x","mode":"create","name":"x"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                _LOOPBACK_OPENER.open(unauthorized_write, timeout=1)
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise AssertionError("unauthorized workspace write was not rejected") from error
            else:
                raise AssertionError("unauthorized workspace write was accepted")

            workspace_root = root / "synthetic-workspace"
            index_and_query(base, token, workspace_root, create=True)

            second = subprocess.Popen(
                [str(backend)],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={
                    **environment,
                    "SUMMIT_RUN_ID": "conflict-run",
                    "SUMMIT_PROFILE_ROOT": str(root / "second-profile"),
                },
            )
            try:
                second.wait(timeout=8)
                if second.returncode == 0:
                    raise AssertionError("second server unexpectedly bound an occupied port")
                if request(base, "/api/v1/health").status != 200:
                    raise AssertionError("port conflict affected the owning server")
            finally:
                if second.poll() is None:
                    if second.stdin is not None:
                        second.stdin.close()
                    second.wait(timeout=8)

            if process.stdin is not None:
                process.stdin.close()
            process.wait(timeout=10)
            if process.returncode == 0:
                raise AssertionError("parent pipe EOF did not terminate the backend")
            for _ in range(20):
                try:
                    request(base, "/api/v1/health")
                except OSError:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("backend kept listening after parent pipe EOF")
            process = start_backend(backend, environment)
            wait_ready(process, base)
            index_and_query(base, token, workspace_root, create=False)
            if process.stdin is not None:
                process.stdin.close()
            process.wait(timeout=10)
            if process.returncode == 0:
                raise AssertionError("restarted backend did not honor parent-pipe cleanup")
            print(
                "PASS: onedir backend starts with empty PATH; identity, static UI, "
                "unauthorized reads/writes, port conflicts, synthetic create/confirm/index/query, "
                "LanceDB restart persistence, and parent-pipe cleanup verified"
            )
            return 0
        finally:
            if process.poll() is None:
                if process.stdin is not None:
                    process.stdin.close()
                process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
