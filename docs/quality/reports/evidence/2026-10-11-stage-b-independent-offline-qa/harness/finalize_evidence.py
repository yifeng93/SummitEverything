"""Preserve raw logs while validating code/docs whitespace and byte manifests."""

import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[6]
out = Path(__file__).resolve().parents[1]
report = root / "docs/quality/reports/2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


check = subprocess.run(
    ["git", "diff", "--check", "HEAD", "--", ".", ":(exclude)**/*.log"],
    cwd=root,
    capture_output=True,
    text=True,
)
issues = []
for path in [report, *out.rglob("*.py"), *out.rglob("*.json")]:
    if path.name == "manifest.json":
        continue
    raw = path.read_text()
    for number, line in enumerate(raw.splitlines(), 1):
        if line.rstrip() != line:
            issues.append(f"{path.relative_to(root)}:{number}: trailing whitespace")
    if raw and not raw.endswith("\n"):
        issues.append(f"{path.relative_to(root)}: missing final newline")
    if raw.endswith("\n\n"):
        issues.append(f"{path.relative_to(root)}: extra terminal blank line")
(out / "code-docs-whitespace.log").write_text(
    f"tracked git diff --check exit={check.returncode}\n"
    + check.stdout
    + check.stderr
    + "untracked code/docs exact-byte scan:\n"
    + ("\n".join(issues) + "\n" if issues else "PASS\n")
    + "Only original raw .log bytes excluded; no log rewriting\n"
)
assert check.returncode == 0 and not issues
files = {
    str(path.relative_to(out)): sha(path)
    for path in sorted(out.rglob("*"))
    if path.is_file() and path.name != "manifest.json" and "__pycache__" not in path.parts
}
value = {
    "algorithm": "sha256",
    "file_count": len(files),
    "exact_sha": "7f3119a511fda6f3d2771af4cf09fd9a9026edb7",
    "files": files,
    "report": {"relative_to_repo": str(report.relative_to(root)), "sha256": sha(report)},
}
(out / "manifest.json").write_text(json.dumps(value, indent=2) + "\n")
assert all(sha(out / name) == digest for name, digest in files.items())
print(f"whitespace PASS; manifest {len(files)}/{len(files)}; report {sha(report)}")
print(f"manifest sha256={sha(out / 'manifest.json')}")
