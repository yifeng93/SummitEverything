"""Read-only probe of the packaged backend inside the archive candidate.

QA-only harness. Starts the bundled backend with an isolated HOME/profile and
``SUMMIT_OFFLINE_GUARD_ACTIVE=1``, then checks that the *shipped* bytes carry
this round's fixes. It never sends a valid-shape credential, so no keychain
write is ever attempted; all traffic is loopback only.
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

APP = Path(
    "/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/"
    "internal-19078de/SummitEverything Internal.app"
)
EXPECTED_SHA = "19078dedb62655c4090051ee5e2159068ef5f607"
TOKEN = "qa-probe-session-token"
# Strings that only exist after this round's fix.
REQUIRED_STRINGS = [
    "向量服务返回了无法解析的响应",
    "排序服务返回了无法解析的响应",
    "index_update_failed",
    "assistant_failed",
    "assistant_unavailable",
    "answer text must not be blank",
    "credential_shape_invalid",
]


def call(base: str, path: str, *, method: str = "GET", body: dict | None = None, auth: bool = True):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=3)
        return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except ValueError:
            return error.code, raw.decode("utf-8", "replace")


def scan_zlib_streams(blob: bytes, targets: list[str]) -> dict[str, bool]:
    """Find strings inside a PyInstaller bundle's zlib-compressed modules.

    The app modules live compressed inside the onedir executable, so a raw byte
    search always misses. Every zlib stream in the file is decompressed and
    searched; this is read-only and never executes the bundle.
    """
    import zlib

    found = {text: False for text in targets}
    encoded = {text: text.encode() for text in targets}
    offset = 0
    while True:
        offset = blob.find(b"\x78\x9c", offset)
        if offset < 0:
            break
        try:
            chunk = zlib.decompressobj().decompress(blob[offset : offset + 2_000_000], 8_000_000)
        except Exception:  # noqa: BLE001 - a false header just skips the offset
            offset += 2
            continue
        for text in targets:
            if not found[text] and encoded[text] in chunk:
                found[text] = True
        offset += 2
    return found


def main() -> int:
    resources = APP / "Contents" / "Resources"
    backend = resources / "backend" / "summit-backend" / "summit-backend"
    identity = json.loads((resources / "build-info.json").read_text(encoding="utf-8"))
    print(f"build-info: source_sha={identity['source_sha']} dirty={identity['dirty']}")

    # Static check inside the compressed bundle: the shipped bytes contain the
    # product strings introduced by this round.
    presence = scan_zlib_streams(backend.read_bytes(), REQUIRED_STRINGS)
    present = sum(1 for value in presence.values() if value)
    print(f"shipped-string check: {present}/{len(REQUIRED_STRINGS)} present")
    missing = [text for text, value in presence.items() if not value]
    if missing:
        print(f"MISSING strings in shipped backend: {missing}")
        return 1

    port = 18794
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError("probe port occupied") from exc

    with tempfile.TemporaryDirectory(prefix="qa-probe-") as temporary:
        root = Path(temporary)
        env = {
            "PATH": "",
            "HOME": str(root),
            "TMPDIR": str(root),
            "SUMMIT_PROFILE_ROOT": str(root / "profile"),
            "SUMMIT_API_PORT": str(port),
            "SUMMIT_WEB_PORT": str(port),
            "SUMMIT_RUN_ID": "qa-readonly-probe",
            "SUMMIT_SESSION_TOKEN": TOKEN,
            "SUMMIT_BUILD_INFO": str(resources / "build-info.json"),
            "SUMMIT_WEB_DIST": str(resources / "web"),
            "SUMMIT_OFFLINE_GUARD_ACTIVE": "1",
        }
        process = subprocess.Popen(
            [str(backend)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        base = f"http://127.0.0.1:{port}"
        failures: list[str] = []
        try:
            health = None
            for _ in range(160):
                if process.poll() is not None:
                    raise RuntimeError(f"backend exited early: {process.returncode}")
                try:
                    status, payload = call(base, "/api/v1/health", auth=False)
                    if status == 200:
                        health = payload
                        break
                except (OSError, TimeoutError):
                    time.sleep(0.25)
            if health is None:
                raise RuntimeError("packaged backend readiness timed out")
            print(f"health: {json.dumps(health, ensure_ascii=False, sort_keys=True)}")
            if health.get("source_sha") != EXPECTED_SHA:
                failures.append(f"health source_sha={health.get('source_sha')!r}")
            if health.get("dirty") is not False:
                failures.append(f"health dirty={health.get('dirty')!r}")

            status, _ = call(base, "/api/v1/workspaces/current", auth=False)
            print(f"unauthorized read -> {status}")
            if status != 401:
                failures.append(f"unauthenticated read was {status}, expected 401")

            status, payload = call(
                base,
                "/api/v1/workspaces",
                method="POST",
                body={
                    "root": str(root / "workspace"),
                    "mode": "create",
                    "name": "QA 只读探测",
                    "operation_id": "qa-probe-open",
                },
            )
            print(f"create workspace -> {status}")
            if status != 201:
                failures.append(f"workspace create was {status}: {payload}")

            # Bad credential shape must be refused before any keychain write.
            status, payload = call(
                base,
                "/api/v1/credentials/deepseek",
                method="PUT",
                body={"account_id": "default", "secret": "not-a-key-shape"},
            )
            print(f"bad credential shape -> {status} {json.dumps(payload, ensure_ascii=False)}")
            if status != 422 or payload.get("error", {}).get("code") != "credential_shape_invalid":
                failures.append(f"credential shape probe returned {status}: {payload}")

            # An over-long credential-shaped value is still refused before any
            # keychain write, and must never be echoed back. Only invalid shapes
            # are sent: a valid shape would attempt a real macOS keychain write,
            # which this QA pass must not do.
            shaped = "sk-qa-probe-" + "a" * 600
            status, payload = call(
                base,
                "/api/v1/credentials/deepseek",
                method="PUT",
                body={"account_id": "default", "secret": shaped},
            )
            text = json.dumps(payload, ensure_ascii=False)
            print(f"over-long credential -> {status} (value redacted={shaped not in text})")
            if status != 422 or shaped in text:
                failures.append(f"over-long credential probe returned {status}: {payload[:200]}")
        finally:
            if process.poll() is None:
                if process.stdin is not None:
                    process.stdin.close()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("PASS: packaged backend carries this round's fixes and rejects bad credential shapes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
