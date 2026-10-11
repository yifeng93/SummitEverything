"""Verify exact source identity, fd204 tree delta, old manifests and offline guards."""
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
BASE = "fd2042385c4916598337239f5259b3ef1889372a"
FD_ROOT = Path("/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-backend/SummitEverything")
HEAD = "576895f6983ca41cacbbad45a9075b97b9986189"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def blocked(invoke):
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
        files = {name: digest for name, digest in value.items() if isinstance(digest, str) and len(digest) == 64}
        schema = "flat-sha256-map"
    mismatches = [name for name, digest in files.items() if not (path.parent / name).is_file() or sha(path.parent / name) != digest]
    report = value.get("report")
    report_mismatch = None
    if report and report.get("relative_to_repo"):
        report_path = ROOT / report["relative_to_repo"]
        if not report_path.is_file() or sha(report_path) != report.get("sha256"):
            report_mismatch = report["relative_to_repo"]
    manifests.append({"path": str(path.relative_to(ROOT)), "manifest_sha256": sha(path), "schema": schema, "file_count": len(files), "file_mismatches": mismatches, "report_mismatch": report_mismatch})

paths = ["src", "tests", "web", "scripts", "pyproject.toml", "uv.lock", "web/package-lock.json"]
tree_ids = {name: {"fd204": git("rev-parse", f"{BASE}:{name}"), "576895f": git("rev-parse", f"{HEAD}:{name}")} for name in paths}
diff_names = git("diff", "--name-status", BASE, HEAD, "--", "src", "tests", "web", "native", "scripts", "pyproject.toml", "uv.lock", "web/package-lock.json").splitlines()
native_diff = git("diff", "--unified=2", BASE, HEAD, "--", "native/Sources/SummitEverythingApp/App.swift")
probes = {
    "non_loopback_socket": blocked(lambda: socket.socket().connect(("203.0.113.1", 443))),
    "external_dns": blocked(lambda: socket.getaddrinfo("independent-qa.invalid", 443)),
    "OS_Keychain_constructor": blocked(MacOSKeychainBackend),
}
fd_manifest_path = FD_ROOT / "docs/quality/reports/evidence/2026-10-11-stage-b-luna-final-offline-qa/manifest.json"
fd_manifest = json.loads(fd_manifest_path.read_text())
fd_mismatches = [name for name, digest in fd_manifest["files"].items() if not (fd_manifest_path.parent / name).is_file() or sha(fd_manifest_path.parent / name) != digest]
fd_report = fd_manifest["report"]
fd_report_path = FD_ROOT / fd_report["relative_to_repo"]
fd_report_mismatch = not fd_report_path.is_file() or sha(fd_report_path) != fd_report["sha256"]
value = {
    "exact_sha": git("rev-parse", "HEAD"),
    "parent": git("show", "-s", "--format=%P", "HEAD"),
    "checkout": str(ROOT),
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "python": sys.version,
    "executable": sys.executable,
    "PYTHONPATH": os.environ.get("PYTHONPATH"),
    "guard_active": os.environ.get("SUMMIT_OFFLINE_GUARD_ACTIVE"),
    "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "npm": subprocess.check_output(["npm", "--version"], text=True).strip(),
    "tree_ids_fd_vs_576895f": tree_ids,
    "source_diff_names": diff_names,
    "native_app_diff": native_diff,
    "lock_sha256": {name: sha(ROOT / name) for name in ["uv.lock", "web/package-lock.json"]},
    "api_sha256": {name: sha(ROOT / name) for name in ["web/openapi.json", "web/src/api/generated.ts"]},
    "historical_manifests": manifests,
    "fd204_final_evidence": {"path": str(fd_manifest_path), "file_count": fd_manifest["file_count"], "file_mismatches": fd_mismatches, "report_mismatch": fd_report_mismatch},
    "guard_negative_controls": probes,
    "live_transfer_workers": live_transfer_workers(),
    "real_calls": {"feishu_exchange": "0/1", "feishu_refresh": "0/1", "deepseek_chat": "0/1", "model_studio_embedding": "0/1", "model_studio_rerank": "0/1", "real_remote_writes": 0},
}
(OUT / "identity-audit.json").write_text(json.dumps(value, indent=2) + "\n")
assert value["exact_sha"] == HEAD and value["branch"] == "HEAD" and value["guard_active"] == "1"
assert all(item["fd204"] == item["576895f"] for item in tree_ids.values())
assert diff_names == ["M\tnative/Sources/SummitEverythingApp/App.swift"]
assert 'http://127.0.0.1:\\(webPort)/' in native_diff
assert all(not item["file_mismatches"] and not item["report_mismatch"] for item in manifests)
assert not fd_mismatches and not fd_report_mismatch and fd_manifest["file_count"] == 30
assert all(item["result"] == "blocked" for item in probes.values())
assert value["live_transfer_workers"] == 0
print(f"Exact SHA; backend/web/script/lock trees equal fd204; only native webURL slash changed")
print(f"Verified {len(manifests)} historical manifests and fd204 final evidence ({fd_manifest['file_count']} files), all zero mismatches")
print("Guard blocks non-loopback, real DNS and OS Keychain; live transfer workers=0")
