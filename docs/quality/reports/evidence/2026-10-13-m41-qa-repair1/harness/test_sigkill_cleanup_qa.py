from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
import uuid

source = pathlib.Path(os.environ["SUMMIT_SOURCE_APP"]).resolve()
temp_root = pathlib.Path(os.environ["DARWIN_USER_TEMP_DIR"]).resolve() / (
    "summit-m41-sigkill-" + uuid.uuid4().hex[:8]
)
temp_root.mkdir(mode=0o700)
app = temp_root / source.name
subprocess.run(["/usr/bin/ditto", str(source), str(app)], check=True)
profile = temp_root / "profile"
profile.mkdir(mode=0o700)
home = temp_root / "home"
home.mkdir(mode=0o700)
log_path = temp_root / "native-app.log"
log = log_path.open("wb")
env = {
    "PATH": "",
    "HOME": str(home),
    "TMPDIR": os.environ["DARWIN_USER_TEMP_DIR"],
    "SUMMIT_INTERNAL_TEST_PROFILE_ROOT": str(profile),
}
app_binary = app / "Contents/MacOS/SummitEverything"
proc = subprocess.Popen(
    [str(app_binary)], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
)
children: list[int] = []
try:
    print(f"app_pid={proc.pid}")
    print(f"app_copy={app}")
    print(f"profile={profile}")
    deadline = time.monotonic() + 20
    identity = json.loads((app / "Contents/Resources/build-info.json").read_text())
    health = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"native app exited before readiness: {proc.returncode}")
        try:
            with urllib.request.urlopen("http://127.0.0.1:18793/api/v1/health", timeout=0.5) as response:
                candidate = json.loads(response.read())
            fields = (
                "source_sha",
                "dirty",
                "build_id",
                "app_version",
                "frontend_sha256",
                "dependencies_sha256",
            )
            if all(candidate.get(key) == identity[key] for key in fields):
                health = candidate
                break
        except (OSError, ValueError):
            time.sleep(0.1)
    if health is None:
        raise RuntimeError("candidate identity did not become ready")
    rows = subprocess.check_output(
        ["/bin/ps", "-A", "-o", "pid,ppid,command"], text=True
    ).splitlines()[1:]
    for row in rows:
        parts = row.strip().split(None, 2)
        if len(parts) == 3 and parts[1] == str(proc.pid) and "summit-backend" in parts[2]:
            children.append(int(parts[0]))
    if not children:
        raise RuntimeError("no owned backend child was observed")
    print("identity_readiness=PASS")
    print("backend_child_pids=" + ",".join(map(str, children)))
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10)
    print(f"parent_exit={proc.returncode}")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        port_open = False
        try:
            with socket.create_connection(("127.0.0.1", 18793), timeout=0.2):
                port_open = True
        except OSError:
            pass
        child_alive = False
        for child in children:
            try:
                state = subprocess.check_output(
                    ["/bin/ps", "-p", str(child), "-o", "stat="], text=True
                ).strip()
            except subprocess.CalledProcessError:
                continue
            if state and not state.startswith("Z"):
                child_alive = True
        if not port_open and not child_alive:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"cleanup timeout: port_open={port_open}, child_alive={child_alive}")
    if proc.returncode != -signal.SIGKILL:
        raise RuntimeError(f"expected SIGKILL parent result, got {proc.returncode}")
    print("pipe_eof_backend_cleanup=PASS")
finally:
    if proc.poll() is None:
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
    log.close()
