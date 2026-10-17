#!/usr/bin/env python3
"""Read-only document batch QA for pinned base/target commits."""
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse

BASE = "6f8fe80558d6e51481f6a3dd203c7e53e6faad89"
TARGET = "f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796"
ROOT = Path.cwd()

def git(*args):
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout

def fail(msg):
    print("FAIL:", msg)
    return False

ok = True
head = git("rev-parse", "HEAD").strip()
status = git("status", "--porcelain")
print(f"HEAD={head}; expected={TARGET}")
print(f"initial tracked/untracked status entries={len(status.splitlines())}")
if head != TARGET:
    ok = fail("tested HEAD differs from pinned target") and ok

changed = git("diff", "--name-only", BASE, TARGET).splitlines()
print(f"base-to-target changed paths={len(changed)}")
# Product source, test, UI/native/script, workflow and dependency trees must be identical.
protected_prefixes = ("src/", "tests/", "web/", "native/", "scripts/", ".github/workflows/")
protected_files = {"pyproject.toml", "uv.lock", "package.json", "package-lock.json", "web/package.json", "web/package-lock.json"}
changed_protected = [p for p in changed if p.startswith(protected_prefixes) or p in protected_files]
print(f"protected tree changed paths={changed_protected}")
if changed_protected:
    ok = fail("product/test/web/native/scripts/dependency/workflow tree changed") and ok

# Protected specs and frontend contracts must be byte-identical.
for p in ["docs/product/PRODUCT-SPEC.md", "docs/product/FRONTEND-GUIDE.md", "docs/product/FRONTEND-PAGE-SPECS.md"]:
    same = git("rev-parse", f"{BASE}:{p}").strip() == git("rev-parse", f"{TARGET}:{p}").strip()
    print(f"protected spec {p}: {'PASS' if same else 'FAIL'}")
    if not same:
        ok = fail(f"protected specification changed: {p}") and ok

# All pre-existing report/evidence blobs are immutable except the report index; the new DEV report is permitted.
def tree_blobs(rev):
    raw = subprocess.run(["git", "ls-tree", "-rz", "--full-tree", "-r", rev, "docs/quality/reports"], check=True, capture_output=True).stdout
    out = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        out[path.decode("utf-8")] = meta.decode("ascii").split()[2]
    return out

base_blobs = tree_blobs(BASE)
target_blobs = tree_blobs(TARGET)
base_paths = set(base_blobs)
target_paths = set(target_blobs)
preexisting = base_paths - {"docs/quality/reports/README.md"}
removed = sorted(preexisting - target_paths)
changed_blobs = []
for p in sorted(preexisting & target_paths):
    a = base_blobs[p]
    b = target_blobs[p]
    if a != b:
        changed_blobs.append(p)
print(f"pre-existing report/evidence files checked={len(preexisting)}; removed={removed}; changed_blobs={changed_blobs}")
if removed or changed_blobs:
    ok = fail("pre-existing reports/evidence content or paths changed") and ok

# C01-C31 rows must remain byte-identical; R01-R05 gate rows must remain present and unchanged.
base_accept = git("show", f"{BASE}:docs/quality/ACCEPTANCE.md")
target_accept = git("show", f"{TARGET}:docs/quality/ACCEPTANCE.md")
def matrix_rows(s, prefix):
    return {m.group(1): m.group(0) for m in re.finditer(r"^\|\s*((?:C|R)\d{2})\s*\|.*$", s, re.M) if m.group(1).startswith(prefix)}
for prefix, expected in [("C", 31), ("R", 5)]:
    a, b = matrix_rows(base_accept, prefix), matrix_rows(target_accept, prefix)
    same = a == b and len(b) == expected
    print(f"ACCEPTANCE {prefix} rows base={len(a)} target={len(b)} byte-equal={same}")
    if not same:
        ok = fail(f"{prefix} matrix rows changed or missing") and ok

# Check current-entry Markdown local file links and heading anchors.
current = [
    "README.md", "AGENTS.md", "docs/README.md", "docs/implementation/PROGRESS.md",
    "docs/handoff/LATEST-IMPLEMENTATION.md", "docs/handoff/IMPLEMENTER.md", "docs/handoff/TESTER.md",
    "docs/quality/ACCEPTANCE.md", "docs/quality/reports/README.md", "docs/product/PRODUCT-SPEC.md",
    "docs/product/FRONTEND-GUIDE.md", "docs/product/FRONTEND-PAGE-SPECS.md", "docs/architecture/ARCHITECTURE.md",
    "docs/contracts/API-v1.md", "docs/contracts/WORKSPACE-v1.md", "docs/decisions/0008-sol-luna-development-workflow.md",
    "docs/superpowers/plans/2026-10-09-summit-everything-v1.md", "docs/superpowers/plans/2026-10-17-ponytail-cleanup.md",
]
def slug(h):
    h = re.sub(r"<[^>]*>", "", h).strip().lower()
    h = re.sub(r"[^\w\-\s]", "", h, flags=re.UNICODE)
    return re.sub(r"\s+", "-", h)
errors=[]; nlinks=0
for rel in current:
    src = ROOT / rel
    if not src.is_file():
        errors.append((rel, "current document missing")); continue
    body = src.read_text(encoding="utf-8")
    # Inspect links line-by-line so malformed prose examples cannot absorb later paragraphs.
    link_body = body
    headings=[]
    for line in body.splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if m:
            headings.append(slug(m.group(1)))
    for source_line in link_body.splitlines():
      if "未完成的链接" in source_line:
        continue  # prose example, not an actual document link
      for m in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", source_line):
        raw = m.group(1).strip().split()[0].strip("<>")
        nlinks += 1
        if not raw or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("#"):
            if raw.startswith("#") and urllib.parse.unquote(raw[1:]) not in headings:
                errors.append((rel, f"anchor not found: {raw}"))
            continue
        path, sep, frag = urllib.parse.unquote(raw).partition("#")
        dest = (src.parent / path).resolve()
        if not dest.exists():
            errors.append((rel, f"file not found: {raw}")); continue
        if sep and dest.is_file() and dest.suffix.lower() in {".md", ".markdown"}:
            dbody = dest.read_text(encoding="utf-8")
            dheads=[]
            for line in dbody.splitlines():
                hm = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
                if hm: dheads.append(slug(hm.group(1)))
            if urllib.parse.unquote(frag) not in dheads:
                errors.append((rel, f"anchor not found: {raw}"))
print(f"current-entry local links checked={nlinks}; link/anchor errors={len(errors)}")
for e in errors: print("LINK_ERROR:", *e)
if errors: ok = fail("current-entry links or anchors unresolved") and ok

# Required README content and actual command entry points.
readme = (ROOT / "README.md").read_text(encoding="utf-8")
for term in ["能力", "本地开发", "常用检查", "文档导航"]:
    if term not in readme: ok = fail(f"README missing section: {term}") and ok
# Confirm npm script names in package manifest and script paths exist for the listed runtime commands.
manifest = (ROOT / "web/package.json").read_text(encoding="utf-8")
for s in ["test", "typecheck", "lint", "build"]:
    if not re.search(r'"' + re.escape(s) + r'"\s*:', manifest): ok = fail(f"README npm script missing in web/package.json: {s}") and ok
for p in ["scripts/run_dev.py", "native/Package.swift", "pyproject.toml", "uv.lock", "web/package-lock.json"]:
    if not (ROOT / p).exists(): ok = fail(f"README command input missing: {p}") and ok

print("RESULT=" + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
