from __future__ import annotations

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

source = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
root.mkdir(parents=True, exist_ok=True)
copy = root / "tampered.app"
shutil.copytree(source, copy)
resources = copy / "Contents" / "Resources"
web = resources / "web"
with (web / "index.html").open("ab") as file:
    file.write(b"\n<!-- synthetic tamper evidence -->\n")
backend = resources / "backend" / "summit-backend" / "summit-backend"
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
env = {
    "PATH": "",
    "HOME": str(root),
    "TMPDIR": str(root),
    "SUMMIT_PROFILE_ROOT": str(root / "profile"),
    "SUMMIT_API_PORT": str(port),
    "SUMMIT_WEB_PORT": str(port),
    "SUMMIT_RUN_ID": "qa-tamper-run",
    "SUMMIT_SESSION_TOKEN": "qa-synthetic-token-never-log",
    "SUMMIT_BUILD_INFO": str(resources / "build-info.json"),
    "SUMMIT_WEB_DIST": str(web),
}
process = subprocess.Popen(
    [str(backend)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, env=env,
)
try:
    deadline = time.monotonic() + 8
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if process.poll() is None:
        raise SystemExit("FAIL: tampered packaged backend stayed running")
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=0.3)
    except (OSError, urllib.error.URLError):
        pass
    else:
        raise SystemExit("FAIL: tampered backend exposed health/readiness")
    if process.returncode == 0:
        raise SystemExit("FAIL: tampered packaged backend exited successfully")
    print(f"PASS: packaged backend failed closed (exit={process.returncode}); no readiness listener; empty PATH")
finally:
    if process.poll() is None:
        if process.stdin is not None:
            process.stdin.close()
        process.wait(timeout=5)
