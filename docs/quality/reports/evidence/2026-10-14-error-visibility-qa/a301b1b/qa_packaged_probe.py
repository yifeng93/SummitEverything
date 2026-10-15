"""Independent QA probe: does the archived candidate really contain this fix?

Starts the packaged backend from a copied bundle, loopback only, with the
keychain disabled (``SUMMIT_OFFLINE_GUARD_ACTIVE=1``) so no credential is ever
written to the real macOS keychain. The only credential value submitted has an
invalid shape, so it is rejected before any store is touched.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = "qa-packaged-probe-token"


def request(base: str, path: str, *, method: str = "GET", body: object | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        return urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        return error


def main() -> int:
    app = Path(os.environ["SUMMIT_APP"]).resolve()
    port = int(os.environ.get("QA_PROBE_PORT", "18794"))
    results: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory(prefix="qa-packaged-probe-") as temporary:
        root = Path(temporary)
        copied = root / app.name
        shutil.copytree(app, copied, symlinks=True)
        resources = copied / "Contents" / "Resources"
        identity = json.loads((resources / "build-info.json").read_text(encoding="utf-8"))
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:  # pragma: no cover
                raise RuntimeError("probe port occupied") from exc

        backend = resources / "backend" / "summit-backend" / "summit-backend"
        process = subprocess.Popen(
            [str(backend)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                "PATH": "",
                "HOME": str(root),
                "TMPDIR": str(root),
                "SUMMIT_PROFILE_ROOT": str(root / "profile"),
                "SUMMIT_API_PORT": str(port),
                "SUMMIT_WEB_PORT": str(port),
                "SUMMIT_RUN_ID": "qa-probe-run",
                "SUMMIT_SESSION_TOKEN": TOKEN,
                "SUMMIT_BUILD_INFO": str(resources / "build-info.json"),
                "SUMMIT_WEB_DIST": str(resources / "web"),
                "SUMMIT_OFFLINE_GUARD_ACTIVE": "1",
            },
        )
        base = f"http://127.0.0.1:{port}"
        try:
            health = None
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
            assert health is not None, "backend readiness timed out"
            results.append(
                (
                    "health.source_sha",
                    health.get("source_sha") == identity["source_sha"],
                    str(health.get("source_sha")),
                )
            )
            opened = request(
                base,
                "/api/v1/workspaces",
                method="POST",
                body={
                    "root": str(root / "workspace"),
                    "mode": "create",
                    "name": "QA 包内探测库",
                    "operation_id": "qa-probe-open",
                },
            )
            results.append(("workspace.create", opened.status == 201, str(opened.status)))

            blob = "sk-" + "a" * 120 + "\n" + "b" * 130
            rejected = request(
                base,
                "/api/v1/credentials/deepseek",
                method="PUT",
                body={"account_id": "default", "secret": blob},
            )
            payload = json.loads(rejected.read())
            results.append(
                (
                    "credential.shape_invalid",
                    rejected.status == 422
                    and payload["error"]["code"] == "credential_shape_invalid",
                    f"{rejected.status} {payload['error']['code']}",
                )
            )
            results.append(
                (
                    "credential.no_echo",
                    blob not in json.dumps(payload),
                    "value absent from the rejection body",
                )
            )

            shaped = "sk-" + "z" * 20
            accepted = request(
                base,
                "/api/v1/credentials/deepseek",
                method="PUT",
                body={"account_id": "default", "secret": shaped},
            )
            accepted_payload = json.loads(accepted.read())
            # The shape gate passed it; the disabled store then fails closed.
            results.append(
                (
                    "credential.valid_shape_passes_the_gate",
                    accepted.status == 503
                    and accepted_payload["error"]["code"] == "credential_store_unavailable",
                    f"{accepted.status} {accepted_payload['error']['code']}",
                )
            )
            results.append(
                (
                    "credential.valid_no_echo",
                    shaped not in json.dumps(accepted_payload),
                    "value absent from the store-error body",
                )
            )
        finally:
            if process.stdin is not None:
                process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                process.kill()

    ok = True
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
