from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import UnavailableSecretBackend

ROOT = Path(__file__).resolve().parents[3]
GOOD_TOKEN = "synthetic-correct-token"
BAD_TOKEN = "synthetic-wrong-token"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mcp-auth-probe-") as temp:
        app = create_app(
            session_token=GOOD_TOKEN,
            profile_root=Path(temp) / "profile",
            secret_backend=UnavailableSecretBackend(),
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical", access_log=False)
        )
        thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
        thread.start()
        results: list[bool] = []
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.02)
            if not server.started:
                print("server_start: FAIL")
                return 1

            for entrypoint in ("module", "console_script"):
                command = (
                    [str(ROOT / ".venv/bin/python"), "-m", "summit_everything.mcp_server"]
                    if entrypoint == "module"
                    else [str(ROOT / ".venv/bin/summit-everything-mcp")]
                )
                for case, token, expected in (
                    ("wrong_token", BAD_TOKEN, "API token 无效或已过期"),
                    ("correct_token_without_workspace", GOOD_TOKEN, "请先在 SummitEverything 应用中打开工作库"),
                ):
                    env = dict(os.environ)
                    env["SUMMIT_API_URL"] = f"http://127.0.0.1:{port}"
                    env["SUMMIT_MCP_TOKEN"] = token
                    env.pop("SUMMIT_MCP_TOKEN_FILE", None)
                    env.pop("SUMMIT_WORKSPACE_ID", None)
                    if entrypoint == "module":
                        env["PYTHONPATH"] = str(ROOT / "src")
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=15,
                        check=False,
                    )
                    safe = token not in result.stdout + result.stderr and "Traceback" not in result.stderr
                    passed = (
                        result.returncode == 2
                        and result.stdout == ""
                        and expected in result.stderr
                        and safe
                    )
                    print(
                        f"{entrypoint}/{case}: {'PASS' if passed else 'FAIL'} "
                        f"exit={result.returncode} stdout_empty={not result.stdout} "
                        f"friendly_message={expected in result.stderr} "
                        f"no_traceback={'Traceback' not in result.stderr} no_token_echo={safe}"
                    )
                    if not passed:
                        print(f"  stderr={result.stderr[:500]!r}")
                    results.append(passed)
        finally:
            server.should_exit = True
            thread.join(timeout=10)
        print(f"summary: {sum(results)}/{len(results)} passed")
        return 0 if len(results) == 4 and all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
