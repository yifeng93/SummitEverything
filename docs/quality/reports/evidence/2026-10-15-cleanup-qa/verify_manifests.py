#!/usr/bin/env python3
"""Independent QA self-check of the 2026-10-15 worktree archive manifests.

For every <dir>/MANIFEST.sha256 under the worktree-archive evidence directory:
  * split lines into TREE lines (directory digests, not file contents) and file lines
  * for each file line whose relative path exists inside the archive dir, recompute
    sha256 of the archived bytes and compare with the recorded digest
  * report ok / mismatch / absent (source-only, never copied) counts
Limitation: the source worktrees were removed in C5, so this is a SELF-check of the
archived bytes against the manifest written from the same bytes -- it cannot prove the
archived bytes equal what the deleted source held.  See the QA report.
"""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
dirs = sorted(p for p in root.iterdir() if p.is_dir())
tot_ok = tot_mismatch = tot_absent = tot_tree = tot_file_lines = 0
rows = []
for d in dirs:
    mf = d / "MANIFEST.sha256"
    if not mf.is_file():
        rows.append((d.name, "NO-MANIFEST", 0, 0, 0, 0, 0))
        continue
    ok = mismatch = absent = tree = file_lines = 0
    for line in mf.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("TREE "):
            tree += 1
            tot_tree += 1
            continue
        file_lines += 1
        tot_file_lines += 1
        digest, rest = line.split(" ", 1)
        _size, rel = rest.split(" ", 1)
        target = d / rel
        if not target.is_file():
            absent += 1
            continue
        got = hashlib.sha256(target.read_bytes()).hexdigest()
        if got == digest:
            ok += 1
        else:
            mismatch += 1
            rows.append((d.name, "MISMATCH " + rel, 0, 0, 0, 0, 0))
    tot_ok += ok
    tot_mismatch += mismatch
    tot_absent += absent
    rows.append((d.name, "ok", file_lines, ok, mismatch, absent, tree))

for name, status, file_lines, ok, mismatch, absent, tree in rows:
    print(f"{name:34s} {status:10s} file_lines={file_lines:5d} ok={ok:4d} mismatch={mismatch:3d} absent={absent:5d} TREE={tree}")
print("-" * 100)
print(f"TOTAL file_lines={tot_file_lines} ok={tot_ok} mismatch={tot_mismatch} absent={tot_absent} TREE={tot_tree}")
print(f"TOTAL MANIFEST entries = {tot_file_lines} file lines + {tot_tree} TREE lines = {tot_file_lines + tot_tree}")
print("RESULT:", "PASS" if (tot_ok == 395 and tot_mismatch == 0) else "CHECK")
