"""Run fixed-SHA offline QA commands with the repository guard active."""
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
    ("build-tool-install", ["uv", "pip", "install", "--python", str(ROOT / ".venv/bin/python"), "hatchling"], ROOT),
    ("pytest-full", ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider"], ROOT),
    ("independent-boundaries", ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider", str(OUT / "harness/test_independent_boundaries.py"), str(OUT / "harness/test_independent_refresh_faults.py")], ROOT),
    ("ruff-check", ["uv", "run", "--locked", "--no-sync", "ruff", "check", "src", "tests"], ROOT),
    ("ruff-format", ["uv", "run", "--locked", "--no-sync", "ruff", "format", "--check", "src", "tests"], ROOT),
    ("mypy", ["uv", "run", "--locked", "--no-sync", "mypy", "src"], ROOT),
    ("lock-check", ["uv", "lock", "--check"], ROOT),
    ("package-build-guarded", ["uv", "build", "--no-build-isolation"], ROOT),
    ("api-types-1", ["npm", "run", "api:types"], ROOT / "web"),
    ("api-types-2", ["npm", "run", "api:types"], ROOT / "web"),
    ("web-test", ["npm", "test", "--", "--run"], ROOT / "web"),
    ("web-typecheck", ["npm", "run", "typecheck"], ROOT / "web"),
    ("web-lint", ["npm", "run", "lint"], ROOT / "web"),
    ("web-build", ["npm", "run", "build"], ROOT / "web"),
    ("swift-build", ["swift", "build"], ROOT / "native"),
    ("diff-check", ["git", "diff", "--check"], ROOT),
]
results = []
for name, argv, cwd in commands:
    started = time.monotonic()
    proc = subprocess.run(argv, cwd=cwd, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    elapsed = round(time.monotonic() - started, 3)
    (OUT / f"{name}.log").write_text(proc.stdout)
    record = {"name": name, "argv": argv, "cwd": str(cwd), "exit_code": proc.returncode, "elapsed_seconds": elapsed, "log": f"{name}.log", "PYTHONPATH": PYTHONPATH}
    results.append(record)
    print(f"{name}: exit={proc.returncode} elapsed={elapsed}s")
summary = {"exact_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "python": sys.version, "commands": results}
(OUT / "check-results.json").write_text(json.dumps(summary, indent=2) + "\n")
if any(item["exit_code"] for item in results):
    raise SystemExit(1)
