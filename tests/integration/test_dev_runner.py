from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _is_listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.1)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def test_runner_uses_its_ports_and_stops_only_its_owned_services(tmp_path: Path) -> None:
    api_port = _free_port()
    web_port = _free_port()
    while web_port == api_port:
        web_port = _free_port()
    env = os.environ.copy()
    run_id = "test-" + secrets.token_hex(8)
    env.update(
        {
            "SUMMIT_API_PORT": str(api_port),
            "SUMMIT_WEB_PORT": str(web_port),
            "SUMMIT_API_TARGET": f"http://127.0.0.1:{api_port}",
            "SUMMIT_PROFILE_ROOT": str(tmp_path / "profile"),
            "SUMMIT_RUN_ID": run_id,
        }
    )
    process = subprocess.Popen(
        [sys.executable, "scripts/run_dev.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    api_url = f"http://127.0.0.1:{api_port}/api/v1/health"
    web_url = f"http://127.0.0.1:{web_port}/"
    try:
        deadline = time.monotonic() + 30
        ready = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"runner exited before readiness: {process.returncode}")
            try:
                with urlopen(api_url, timeout=0.5) as response:
                    health = json.loads(response.read())
                with urlopen(web_url, timeout=0.5) as response:
                    web_ready = response.status == 200
                if (
                    health.get("service") == "ready"
                    and health.get("run_id") == run_id
                    and web_ready
                ):
                    ready = True
                    break
            except OSError:
                time.sleep(0.1)
        assert ready, "the configured API and WebUI ports did not become ready"
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=10)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (_is_listening(api_port) or _is_listening(web_port)):
            time.sleep(0.1)
        assert not _is_listening(api_port)
        assert not _is_listening(web_port)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def test_runner_leaves_an_existing_port_owner_untouched(tmp_path: Path) -> None:
    with socket.socket() as incumbent:
        incumbent.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        incumbent.bind(("127.0.0.1", 0))
        incumbent.listen()
        api_port = int(incumbent.getsockname()[1])
        web_port = _free_port()
        env = os.environ.copy()
        env.update(
            {
                "SUMMIT_API_PORT": str(api_port),
                "SUMMIT_WEB_PORT": str(web_port),
                "SUMMIT_API_TARGET": f"http://127.0.0.1:{api_port}",
                "SUMMIT_PROFILE_ROOT": str(tmp_path / "profile"),
                "SUMMIT_RUN_ID": "port-collision-test",
            }
        )
        process = subprocess.Popen(
            [sys.executable, "scripts/run_dev.py"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            assert process.wait(timeout=10) != 0
            assert _is_listening(api_port)
            assert not _is_listening(web_port)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
