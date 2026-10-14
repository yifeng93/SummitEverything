"""Run the local API and WebUI together for development and M1 replay."""

from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from summit_everything.integrations.first_use_defaults import (
    DEFAULTS_ENV_VAR as FIRST_USE_DEFAULTS_ENV_VAR,
    REPO_DEFAULTS_RELATIVE_PATH,
)

ROOT = Path(__file__).resolve().parents[1]


def first_use_defaults_environment(env: dict[str, str]) -> dict[str, str]:
    """Point the dev API at the Git-ignored local defaults file when it exists.

    The runtime never reads the repository file implicitly, so the development
    preview opts in explicitly here. An already configured environment variable
    wins, and a missing file changes nothing.
    """
    configured = dict(env)
    path = ROOT / REPO_DEFAULTS_RELATIVE_PATH
    if path.is_file():
        configured.setdefault(FIRST_USE_DEFAULTS_ENV_VAR, str(path))
    return configured


def main() -> int:
    web_modules = ROOT / "web" / "node_modules"
    if not web_modules.is_dir():
        print("Web dependencies missing. Run: cd web && npm ci", file=sys.stderr)
        return 2

    env = first_use_defaults_environment(os.environ)
    api_port = int(env.get("SUMMIT_API_PORT", "8793"))
    web_port = int(env.get("SUMMIT_WEB_PORT", "5173"))
    run_id = env.setdefault("SUMMIT_RUN_ID", secrets.token_hex(16))
    env.setdefault("SUMMIT_API_TARGET", f"http://127.0.0.1:{api_port}")
    env.setdefault("SUMMIT_SESSION_TOKEN", secrets.token_urlsafe(32))
    api_url = f"http://127.0.0.1:{api_port}/api/v1/health"
    web_url = f"http://127.0.0.1:{web_port}/"
    children: list[subprocess.Popen[bytes]] = []
    interrupted = False

    def stop_children(*_: object) -> None:
        nonlocal interrupted
        interrupted = True
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
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
                    str(api_port),
                ],
                cwd=ROOT,
                env=env,
                start_new_session=True,
            )
        )
        children.append(
            subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=ROOT / "web",
                env=env,
                start_new_session=True,
            )
        )

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if interrupted:
                return 0
            if any(child.poll() is not None for child in children):
                return next(child.returncode or 1 for child in children if child.poll() is not None)
            try:
                with urlopen(api_url, timeout=1) as response:
                    health = json.loads(response.read())
                with urlopen(web_url, timeout=1) as response:
                    web_ready = response.status == 200
                if (
                    health.get("service") == "ready"
                    and health.get("run_id") == run_id
                    and web_ready
                ):
                    break
            except (OSError, URLError):
                time.sleep(0.2)
        else:
            print("Local API did not become ready within 30 seconds.", file=sys.stderr)
            return 1

        print(f"Local API: {api_url}")
        print(f"WebUI: {web_url}")
        print("Press Ctrl+C to stop both services.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        if interrupted:
            return 0
        return next(child.returncode or 0 for child in children if child.poll() is not None)
    finally:
        stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
