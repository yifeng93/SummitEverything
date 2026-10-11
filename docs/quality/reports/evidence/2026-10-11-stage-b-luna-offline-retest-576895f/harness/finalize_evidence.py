"""Hash the exact-SHA retest evidence and report."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/quality/reports/2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

files = {str(path.relative_to(OUT)): sha(path) for path in sorted(OUT.rglob("*")) if path.is_file() and path.name != "manifest.json"}
manifest = {
    "algorithm": "sha256",
    "exact_sha": "576895f6983ca41cacbbad45a9075b97b9986189",
    "file_count": len(files),
    "files": files,
    "report": {"relative_to_repo": str(REPORT.relative_to(ROOT)), "sha256": sha(REPORT)},
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Wrote manifest for {len(files)} evidence files and report {sha(REPORT)}")
