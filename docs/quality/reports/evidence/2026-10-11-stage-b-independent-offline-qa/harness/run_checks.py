"""Independent exact-SHA check runner; product files remain untouched."""

import json
import os
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[6]
out = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env["PYTHONPATH"] = f"{root}/scripts/offline_guard:{root}/src"
commands = [
    (
        "pytest-full",
        ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider"],
    ),
    ("ruff-check", ["uv", "run", "--locked", "--no-sync", "ruff", "check", "src", "tests"]),
    (
        "ruff-format",
        ["uv", "run", "--locked", "--no-sync", "ruff", "format", "--check", "src", "tests"],
    ),
    ("mypy", ["uv", "run", "--locked", "--no-sync", "mypy", "src"]),
    ("lock-check", ["uv", "lock", "--check"]),
    ("package-build", ["uv", "build"]),
    ("api-types-1", ["npm", "--prefix", "web", "run", "api:types"]),
    ("api-types-2", ["npm", "--prefix", "web", "run", "api:types"]),
    ("web-test", ["npm", "--prefix", "web", "test", "--", "--run"]),
    ("web-typecheck", ["npm", "--prefix", "web", "run", "typecheck"]),
    ("web-lint", ["npm", "--prefix", "web", "run", "lint"]),
    ("web-build", ["npm", "--prefix", "web", "run", "build"]),
]
results = []
for name, command in commands:
    start = time.time()
    with (out / f"{name}.log").open("wb") as log:
        proc = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    results.append(
        {
            "name": name,
            "argv": command,
            "exit": proc.returncode,
            "elapsed_seconds": round(time.time() - start, 3),
            "PYTHONPATH": env["PYTHONPATH"],
        }
    )
    (out / "check-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"{name}: exit={proc.returncode}", flush=True)
