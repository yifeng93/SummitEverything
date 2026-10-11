"""Run requested exact-SHA backend and Swift checks under the offline guard."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1]
PYTHONPATH = f"{ROOT}/scripts/offline_guard:{ROOT}/src"
ENV = os.environ | {"PYTHONPATH": PYTHONPATH}
commands = [
    ("uv-sync", ["uv", "sync", "--locked", "--group", "dev"], ROOT),
    ("npm-ci", ["npm", "ci"], ROOT / "web"),
    ("pytest-full", ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider"], ROOT),
    ("independent-boundaries", ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider", str(OUT / "harness/test_independent_boundaries.py"), str(OUT / "harness/test_independent_refresh_faults.py")], ROOT),
    ("swift-build", ["swift", "build"], ROOT / "native"),
]
results = []
for name, argv, cwd in commands:
    started = time.monotonic()
    proc = subprocess.run(argv, cwd=cwd, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    elapsed = round(time.monotonic() - started, 3)
    (OUT / f"{name}.log").write_text(proc.stdout)
    record = {"name": name, "argv": argv, "cwd": str(cwd), "exit_code": proc.returncode, "elapsed_seconds": elapsed, "log": f"{name}.log", "PYTHONPATH": PYTHONPATH}
    results.append(record)
    print(f"{name}: exit={proc.returncode} elapsed={elapsed}s", flush=True)
summary = {"exact_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "python": sys.version, "commands": results}
(OUT / "check-results.json").write_text(json.dumps(summary, indent=2) + "\n")
if any(item["exit_code"] for item in results):
    raise SystemExit(1)
