import json
import subprocess

workspace = "/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-repair-1-qa/SummitEverything"
checks = {}
for port in (18874, 15180):
    result = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    checks[f"lsof_{port}"] = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "interpretation": "no listener" if result.returncode == 1 and not result.stdout else "listener or lsof error",
    }
ps = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True, check=True)
matching = []
for line in ps.stdout.splitlines():
    parts = line.strip().split(None, 2)
    if len(parts) < 3:
        continue
    pid, _ppid, command = parts
    if workspace not in command or "check_stopped.py" in command or command.endswith("/zsh -lc"):
        continue
    executable = subprocess.run(["ps", "-p", pid, "-o", "comm="], capture_output=True, text=True, check=False).stdout.strip()
    if executable.lower().endswith(("python", "python3", "uvicorn", "node", "vite")):
        matching.append(line)
checks["qa_checkout_process_lines"] = matching
print(json.dumps(checks, ensure_ascii=False, indent=2))
if matching or any(item["returncode"] != 1 or item["stdout"] for key, item in checks.items() if key.startswith("lsof_")):
    raise SystemExit(1)
