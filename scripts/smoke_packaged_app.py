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


def request(base: str, path: str, *, headers: dict[str, str] | None = None) -> object:
    try:
        return urllib.request.urlopen(
            urllib.request.Request(base + path, headers=headers or {}), timeout=1
        )
    except urllib.error.HTTPError as error:
        return error


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
        process = subprocess.Popen(
            [str(backend)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            health: dict[str, object] | None = None
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError(f"backend exited early: {process.returncode}")
                try:
                    response = request(base, "/api/v1/health")
                    if response.status == 200:
                        health = json.loads(response.read())
                        break
                except (OSError, TimeoutError):
                    time.sleep(0.25)
            if health is None:
                raise AssertionError("packaged backend readiness timed out")
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
                urllib.request.urlopen(unauthorized_write, timeout=1)
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise AssertionError("unauthorized workspace write was not rejected") from error
            else:
                raise AssertionError("unauthorized workspace write was accepted")

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
            print(
                "PASS: onedir backend starts with empty PATH; identity, static UI, "
                "unauthorized reads/writes, port conflicts, and parent-pipe cleanup verified"
            )
            return 0
        finally:
            if process.poll() is None:
                if process.stdin is not None:
                    process.stdin.close()
                process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
