"""Fixed identity, artifact hashes, protected-tree and offline guard checks."""
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from summit_everything.integrations.settings import MacOSKeychainBackend
from summit_everything.integrations.transport import live_transfer_workers

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def negative_control(name, invoke):
    try:
        invoke()
    except Exception as exc:
        return {"result": "blocked", "exception": type(exc).__name__, "message": str(exc)}
    return {"result": "FAIL: not blocked"}


manifests = []
for path in sorted((ROOT / "docs/quality/reports/evidence").rglob("manifest.json")):
    if path.parent == OUT:
        continue
    value = json.loads(path.read_text())
    if isinstance(value.get("files"), dict):
        files = value["files"]
        schema = "files-envelope"
    else:
        # UI evidence manifests use a flat {relative_path: sha256} mapping.
        files = {
            name: digest
            for name, digest in value.items()
            if isinstance(digest, str) and len(digest) == 64
        }
        schema = "flat-sha256-map"
    mismatches = [
        name
        for name, digest in files.items()
        if not (path.parent / name).is_file() or sha(path.parent / name) != digest
    ]
    report = value.get("report")
    report_mismatch = None
    if report and report.get("relative_to_repo"):
        report_path = ROOT / report["relative_to_repo"]
        if not report_path.is_file() or sha(report_path) != report.get("sha256"):
            report_mismatch = report["relative_to_repo"]
    manifests.append({
        "path": str(path.relative_to(ROOT)),
        "manifest_sha256": sha(path),
        "schema": schema,
        "file_count": len(files),
        "file_mismatches": mismatches,
        "report_mismatch": report_mismatch,
    })

source_manifests = {}
for name in ["2026-10-11-stage-b-native-readiness-dev", "2026-10-11-stage-b-strict-marker-dev"]:
    source_path = ROOT / "docs/quality/reports/evidence" / name / "source-hashes.json"
    sources = json.loads(source_path.read_text())
    mismatches = [path for path, digest in sources.items() if sha(ROOT / path) != digest]
    source_manifests[name] = {"file_count": len(sources), "mismatches": mismatches, "manifest_sha256": sha(source_path)}

protected = ["src", "tests", "web", "native", "scripts", "pyproject.toml", "uv.lock"]
protected_diff = git("diff", "--", *protected)
lock_hashes = {name: sha(ROOT / name) for name in ["uv.lock", "web/package-lock.json"]}
api_hashes = {name: sha(ROOT / name) for name in ["web/openapi.json", "web/src/api/generated.ts"]}
probes = {
    "non_loopback_socket": negative_control("non_loopback_socket", lambda: socket.socket().connect(("203.0.113.1", 443))),
    "external_dns": negative_control("external_dns", lambda: socket.getaddrinfo("independent-qa.invalid", 443)),
    "OS_Keychain_constructor": negative_control("OS_Keychain_constructor", MacOSKeychainBackend),
}
value = {
    "exact_sha": git("rev-parse", "HEAD"),
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "checkout": str(ROOT),
    "python": sys.version,
    "executable": sys.executable,
    "PYTHONPATH": os.environ.get("PYTHONPATH"),
    "guard_active": os.environ.get("SUMMIT_OFFLINE_GUARD_ACTIVE"),
    "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "npm": subprocess.check_output(["npm", "--version"], text=True).strip(),
    "venv": str(ROOT / ".venv"),
    "node_modules": str(ROOT / "web/node_modules"),
    "protected_diff": protected_diff,
    "protected_tree_ids": {name: git("rev-parse", f"HEAD:{name}") for name in protected},
    "lock_sha256": lock_hashes,
    "api_idempotent_sha256": api_hashes,
    "historical_manifests": manifests,
    "fixed_candidate_source_manifests": source_manifests,
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
(OUT / "identity-audit.json").write_text(json.dumps(value, indent=2) + "\n")
assert value["exact_sha"] == "fd2042385c4916598337239f5259b3ef1889372a"
assert value["branch"] == "HEAD" and value["guard_active"] == "1"
assert not value["protected_diff"]
assert all(not item["file_mismatches"] and not item["report_mismatch"] for item in manifests)
assert not source_manifests["2026-10-11-stage-b-native-readiness-dev"]["mismatches"]
assert source_manifests["2026-10-11-stage-b-strict-marker-dev"]["mismatches"] == ["native/Sources/SummitEverythingApp/App.swift"]
assert all(item["result"] == "blocked" for item in probes.values())
assert value["live_transfer_workers"] == 0
print(f"Exact SHA; protected source/locks unchanged; {len(manifests)} historical manifests and referenced reports match")
print("Guard rejects non-loopback sockets, real DNS and OS Keychain; live transfer workers=0")
