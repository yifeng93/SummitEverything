"""Packaged-runtime check for the D repair1/repair2 first-use progress store.

Runs the *bundled* backend out of the built internal candidate (no GUI, no
credentials, no network) and verifies the half of the P1 fix that the WKWebView
depends on: the progress record is durable across a real backend process
restart, lives inside the isolated profile directory, and rejects anything that
is not the whitelisted non-secret shape.

It deliberately starts the packaged backend binary directly (the same way
``scripts/smoke_packaged_app.py`` does) and never launches the .app GUI, which
must go through LaunchServices.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = "synthetic-packaged-repair2-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  :: {detail}" if detail else ""))


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def call(base: str, path: str, *, method: str = "GET", body: object | None = None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, headers=HEADERS, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=3)
        return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except ValueError:
            return error.code, {"raw": raw.decode(errors="replace")}


def start_backend(backend: Path, resources: Path, profile: Path, home: Path, port: int):
    environment = {
        "PATH": "",
        "HOME": str(home),
        "TMPDIR": str(home),
        "SUMMIT_PROFILE_ROOT": str(profile),
        "SUMMIT_API_PORT": str(port),
        "SUMMIT_WEB_PORT": str(port),
        "SUMMIT_RUN_ID": "synthetic-packaged-repair2",
        "SUMMIT_SESSION_TOKEN": TOKEN,
        "SUMMIT_BUILD_INFO": str(resources / "build-info.json"),
        "SUMMIT_WEB_DIST": str(resources / "web"),
    }
    process = subprocess.Popen(
        [str(backend)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(160):
        if process.poll() is not None:
            raise RuntimeError(f"packaged backend exited early: {process.returncode}")
        try:
            status, payload = call(base, "/api/v1/health")
            if status == 200:
                return process, base, payload
        except (OSError, TimeoutError):
            pass
        time.sleep(0.25)
    raise AssertionError("packaged backend readiness timed out")


def stop_backend(process: subprocess.Popen[bytes]) -> None:
    if process.stdin is not None:
        process.stdin.close()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def open_workspace(base: str, root: Path, operation: str, *, mode: str = "create") -> tuple[int, dict]:
    return call(
        base,
        "/api/v1/workspaces",
        method="POST",
        body={"root": str(root), "mode": mode, "name": "合成库", "operation_id": operation},
    )


def main() -> int:
    app = Path(os.environ["SUMMIT_APP"]).resolve()
    resources = app / "Contents" / "Resources"
    backend = resources / "backend" / "summit-backend" / "summit-backend"
    identity = json.loads((resources / "build-info.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="summit-packaged-repair2-") as temporary:
        root = Path(temporary)
        home = root / "home"
        profile = root / "profile"
        workspace = root / "workspace"
        for directory in (home, profile):
            directory.mkdir(parents=True, exist_ok=True)

        port = free_port()
        process, base, health = start_backend(backend, resources, profile, home, port)
        try:
            check(
                "P1 packaged identity matches the embedded manifest",
                all(
                    health.get(key) == identity[key]
                    for key in ("source_sha", "dirty", "build_id", "frontend_sha256", "dependencies_sha256")
                ),
                f"source_sha={health.get('source_sha')} dirty={health.get('dirty')} build_id={health.get('build_id')}",
            )
            check(
                "P2 packaged frontend bundle ships the new progress endpoint",
                any(
                    b"first-use/progress" in asset.read_bytes()
                    for asset in (resources / "web" / "assets").glob("*.js")
                ),
            )
            check("P3 static WebUI entry point is served", _status(base, "/") == 200)
            check("P4 unauthenticated progress read is rejected", _unauth(base))

            status, opened = open_workspace(base, workspace, "packaged-open-1")
            check("P5 packaged backend opens an isolated workspace", status == 201, f"status={status}")
            profile_dir = Path(str(opened["local_profile_dir"]))
            check(
                "P6 workspace profile dir is inside the isolated profile root",
                profile_dir.resolve().is_relative_to(profile.resolve()),
                str(profile_dir),
            )

            status, absent = call(base, "/api/v1/first-use/progress")
            check(
                "P7 no record yet is reported as absent, not as a default",
                status == 404 and absent.get("error", {}).get("code") == "first_use_progress_absent",
                f"status={status}",
            )

            status, _ = call(
                base, "/api/v1/first-use/progress", method="PUT",
                body={"step": 5, "completed": True, "open": False},
            )
            check("P8 completed progress is accepted", status == 200, f"status={status}")

            store = profile_dir / "first-use-progress.json"
            raw = store.read_text() if store.exists() else ""
            check(
                "P9 store file lives in the workspace profile dir with exactly the three keys",
                store.exists() and sorted(json.loads(raw)) == ["completed", "open", "step"],
                str(store),
            )

            status, _ = call(
                base, "/api/v1/first-use/progress", method="PUT",
                body={"step": 3.0, "completed": False, "open": True},
            )
            check("P10 integral float step is rejected (D-4)", status == 422, f"status={status}")

            status, _ = call(
                base, "/api/v1/first-use/progress", method="PUT",
                body={"step": 3, "completed": False, "open": True, "secret": "sk-packaged-DEADBEEF"},
            )
            check("P11 secret-shaped field is rejected", status == 422, f"status={status}")
            check(
                "P12 the rejected secret never reached the disk",
                b"DEADBEEF" not in store.read_bytes(),
            )
            status, unchanged = call(base, "/api/v1/first-use/progress")
            check(
                "P13 rejected writes left the durable record untouched",
                status == 200 and unchanged == {"step": 5, "completed": True, "open": False},
                str(unchanged),
            )
        finally:
            stop_backend(process)

        # Real process restart over the same profile root.
        port2 = free_port()
        process2, base2, _ = start_backend(backend, resources, profile, home, port2)
        try:
            status, reopened = open_workspace(base2, workspace, "packaged-open-2", mode="open")
            check(
                "P14 the same workspace reopens with the same profile dir after restart",
                status == 201 and Path(str(reopened["local_profile_dir"])).resolve() == profile_dir.resolve(),
                f"status={status}",
            )
            status, durable = call(base2, "/api/v1/first-use/progress")
            check(
                "P15 ***P1 CORE*** completed progress survives a real packaged backend restart",
                status == 200 and durable == {"step": 5, "completed": True, "open": False},
                f"status={status} record={durable}",
            )
        finally:
            stop_backend(process2)

    failed = [name for name, ok, _ in checks if not ok]
    print("=" * 78)
    print(f"PACKAGED REPAIR2 HARNESS TOTAL: {len(checks)} checks, {len(checks) - len(failed)} passed, {len(failed)} failed")
    for name in failed:
        print(f"  FAILED: {name}")
    print(f"EXIT={1 if failed else 0}")
    return 1 if failed else 0


def _unauth(base: str) -> bool:
    try:
        urllib.request.urlopen(urllib.request.Request(base + "/api/v1/first-use/progress"), timeout=3)
    except urllib.error.HTTPError as error:
        return error.code == 401
    except OSError:
        return False
    return False


def _status(base: str, path: str) -> int:
    try:
        return urllib.request.urlopen(base + path, timeout=3).status
    except urllib.error.HTTPError as error:
        return error.code


if __name__ == "__main__":
    sys.exit(main())
