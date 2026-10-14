from __future__ import annotations

import pathlib
import re
import subprocess
import sys

app = pathlib.Path(sys.argv[1]).resolve()
profile = pathlib.Path(sys.argv[2]).resolve()
rows: list[tuple[int, int, str]] = []
for line in subprocess.check_output(["ps", "-Ao", "pid=,ppid=,comm="], text=True).splitlines():
    fields = line.strip().split(None, 2)
    if len(fields) == 3:
        rows.append((int(fields[0]), int(fields[1]), fields[2]))

native_pid = next(
    (
        pid
        for pid, _parent, command in rows
        if pathlib.Path(command).resolve() == app / "Contents" / "MacOS" / "SummitEverything"
    ),
    None,
)
if native_pid is None:
    print("native_found=false")
    raise SystemExit(1)

descendants = {native_pid}
pending = [native_pid]
while pending:
    parent = pending.pop()
    children = [pid for pid, ppid, _command in rows if ppid == parent and pid not in descendants]
    descendants.update(children)
    pending.extend(children)

targets: list[tuple[str, int]] = [("native", native_pid)]
targets.extend(
    ("backend", pid)
    for pid, _ppid, command in rows
    if pid in descendants
    and pathlib.Path(command).resolve().name == "summit-backend"
    and str(app) in str(pathlib.Path(command).resolve())
)

all_pass = True
for name, pid in targets:
    command = subprocess.check_output(
        ["ps", "eww", "-p", str(pid), "-o", "command="], text=True
    )
    guard = re.search(r"(?:^|\s)SUMMIT_OFFLINE_GUARD_ACTIVE=([^\s]+)", command)
    profile_key = (
        "SUMMIT_INTERNAL_TEST_PROFILE_ROOT" if name == "native" else "SUMMIT_PROFILE_ROOT"
    )
    actual_profile = re.search(rf"(?:^|\s){profile_key}=([^\s]+)", command)
    guard_ok = guard is not None and guard.group(1) == "1"
    profile_ok = actual_profile is not None and pathlib.Path(actual_profile.group(1)).resolve() == profile
    print(f"{name}_pid={pid} guard_is_1={guard_ok} profile_matches_fresh_root={profile_ok}")
    all_pass = all_pass and guard_ok and profile_ok
if not any(name == "backend" for name, _pid in targets):
    print("backend_found=false")
    all_pass = False
raise SystemExit(0 if all_pass else 1)
