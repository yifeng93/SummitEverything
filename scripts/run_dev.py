"""Run the local API and WebUI together for development and M1 replay."""

from __future__ import annotations

import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8793/api/v1/health"
WEB_URL = "http://127.0.0.1:5173"


def main() -> int:
    web_modules = ROOT / "web" / "node_modules"
    if not web_modules.is_dir():
        print("Web dependencies missing. Run: cd web && npm ci", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("SUMMIT_SESSION_TOKEN", secrets.token_urlsafe(32))
    children: list[subprocess.Popen[bytes]] = []

    def stop_children(*_: object) -> None:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()

    signal.signal(signal.SIGINT, stop_children)
    signal.signal(signal.SIGTERM, stop_children)

    try:
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "summit_everything.api.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8793",
                ],
                cwd=ROOT,
                env=env,
            )
        )
        children.append(
            subprocess.Popen(["npm", "run", "dev"], cwd=ROOT / "web", env=env)
        )

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                return next(child.returncode or 1 for child in children if child.poll() is not None)
            try:
                with urlopen(API_URL, timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(0.2)
        else:
            print("Local API did not become ready within 30 seconds.", file=sys.stderr)
            return 1

        print(f"Local API: {API_URL}")
        print(f"WebUI: {WEB_URL}")
        print("Press Ctrl+C to stop both services.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        return next(child.returncode or 0 for child in children if child.poll() is not None)
    finally:
        stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
