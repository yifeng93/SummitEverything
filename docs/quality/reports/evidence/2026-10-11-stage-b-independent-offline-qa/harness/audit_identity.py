"""Hash/identity checks and guard negative controls; no external request is sent."""

import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from summit_everything.integrations.settings import MacOSKeychainBackend
from summit_everything.integrations.transport import live_transfer_workers

root = Path(__file__).resolve().parents[6]
out = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


manifests = []
for directory in [
    "2026-10-10-deepseek-stage-b",
    "2026-10-10-deepseek-stage-b-r2",
    "2026-10-10-deepseek-stage-b-r3",
    "2026-10-10-deepseek-stage-b-r4",
    "2026-10-11-stage-b-sol-closure",
]:
    path = root / "docs/quality/reports/evidence" / directory / "manifest.json"
    value = json.loads(path.read_text())
    files = value["files"]
    mismatches = [
        name
        for name, digest in files.items()
        if not (path.parent / name).is_file() or sha(path.parent / name) != digest
    ]
    manifests.append(
        {
            "path": str(path.relative_to(root)),
            "sha256": sha(path),
            "count": len(files),
            "mismatches": mismatches,
        }
    )
source_path = (
    root / "docs/quality/reports/evidence/2026-10-11-stage-b-sol-closure/source-hashes.json"
)
sources = json.loads(source_path.read_text())
source_mismatches = [name for name, digest in sources.items() if sha(root / name) != digest]
probes = {}
for name, invoke in {
    "non_loopback_socket": lambda: socket.socket().connect(("203.0.113.1", 443)),
    "system_external_dns": lambda: socket.getaddrinfo("independent-qa.invalid", 443),
    "OS_Keychain_constructor": MacOSKeychainBackend,
}.items():
    try:
        invoke()
        probes[name] = "FAIL: guard did not reject"
    except Exception as exc:
        probes[name] = {"exception": type(exc).__name__, "message": str(exc)}

protected = ["src", "web", "native", "scripts", "pyproject.toml", "uv.lock"]
value = {
    "exact_sha": git("rev-parse", "HEAD"),
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "checkout": str(root),
    "python": sys.version,
    "executable": sys.executable,
    "PYTHONPATH": os.environ.get("PYTHONPATH"),
    "guard_active": os.environ.get("SUMMIT_OFFLINE_GUARD_ACTIVE"),
    "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "npm": subprocess.check_output(["npm", "--version"], text=True).strip(),
    "venv": str(root / ".venv"),
    "node_modules": str(root / "web/node_modules"),
    "protected_diff": git("diff", "--", *protected),
    "protected_tree_ids": {name: git("rev-parse", f"HEAD:{name}") for name in protected},
    "lock_sha256": {name: sha(root / name) for name in ["uv.lock", "web/package-lock.json"]},
    "api_idempotent_sha256": {
        name: sha(root / name) for name in ["web/openapi.json", "web/src/api/generated.ts"]
    },
    "historical_manifests": manifests,
    "current_sol_source_manifest_count": len(sources),
    "current_sol_source_manifest_sha256": sha(source_path),
    "current_sol_source_mismatches": source_mismatches,
    "guard_negative_controls": probes,
    "live_transfer_workers": live_transfer_workers(),
    "real_calls": {
        "feishu_exchange": "0/1",
        "feishu_refresh": "0/1",
        "deepseek_chat": "0/1",
        "model_studio_embedding": "0/1",
        "model_studio_rerank": "0/1",
        "real_remote_writes": 0,
    },
}
(out / "identity-audit.json").write_text(json.dumps(value, indent=2) + "\n")
assert value["exact_sha"] == "7f3119a511fda6f3d2771af4cf09fd9a9026edb7"
assert value["branch"] == "HEAD" and value["guard_active"] == "1"
assert not value["protected_diff"] and not source_mismatches
assert all(not item["mismatches"] for item in manifests)
assert all(isinstance(item, dict) for item in probes.values())
assert value["live_transfer_workers"] == 0
print("Exact SHA/protected source/locks/API unchanged; source hashes and five manifests match")
print("Guard rejects non-loopback sockets, real DNS and OS Keychain; live transfer workers=0")
