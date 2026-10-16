#!/usr/bin/env python3
"""C2 evidence-archive generator for the 2026-10-15 pre-PR21 cleanup.

Read-only with respect to the repository unless --out points inside it.
Records a full SHA-256 manifest of every archived worktree's ignored .local
evidence, copies the small human-readable originals, and verifies every copy.

Method notes
------------
* .venv trees are skipped; their contents carry no evidence value.
* *.app bundles are recorded as a single directory tree digest using the
  repository's established convention (see verify_tree_digest.py):
      sha256 over concat(relative_posix_path + b"\0" + sha256(file_bytes))
* *.dmg files are recorded with their whole-file sha256.
* Copy rule (size-capped, human-readable only):
      *.md <= 512 KiB
      *.sha256 <= 512 KiB
      *.json whose name contains manifest|command-results|evidence <= 512 KiB
      *.log <= 256 KiB
      *.txt <= 256 KiB
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WT_ROOT = Path("/Users/yifengstudio/.codex/worktrees")
KEEP_WORKTREES = {"frontend-ux-20261015"}

CRED_PATTERNS = {
    "bearer_token": re.compile(rb"Bearer\s+[A-Za-z0-9\-_\.]{20,}"),
    "sk_key": re.compile(rb"sk-[A-Za-z0-9]{16,}"),
    "gho_token": re.compile(rb"gho_[A-Za-z0-9]{20,}"),
    "ghp_token": re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    "session_token_assign": re.compile(rb"SUMMIT_SESSION_TOKEN\s*[=:]\s*['\"]?[A-Za-z0-9\-_\.]{16,}"),
    "app_secret": re.compile(rb"app_secret\s*[=:]\s*['\"]?[A-Za-z0-9]{16,}"),
    "api_key": re.compile(rb"api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9\-_]{20,}", re.I),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(root: Path) -> tuple[str, int]:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    d = hashlib.sha256()
    for p in files:
        rel = p.relative_to(root).as_posix().encode()
        d.update(rel + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return d.hexdigest(), len(files)


def inside_app(rel: Path) -> bool:
    return any(part.endswith(".app") for part in rel.parts)


def inside_venv(rel: Path) -> bool:
    return any(part == ".venv" for part in rel.parts)


def should_copy(name: str, size: int) -> bool:
    low = name.lower()
    if name.endswith(".md") and size <= 512 * 1024:
        return True
    if name.endswith(".sha256") and size <= 512 * 1024:
        return True
    if low.endswith(".json") and size <= 512 * 1024:
        if any(k in low for k in ("manifest", "command-results", "evidence")):
            return True
    if low.endswith(".log") and size <= 256 * 1024:
        return True
    if low.endswith(".txt") and size <= 256 * 1024:
        return True
    return False


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    ).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="destination archive directory")
    ap.add_argument("--repo", required=True, help="repository worktree used for git queries")
    ap.add_argument("--dry-run", action="store_true", help="do not copy, only report")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    repo = Path(args.repo).resolve()
    out.mkdir(parents=True, exist_ok=True)

    worktrees = []
    for name in sorted(os.listdir(WT_ROOT)):
        if name in KEEP_WORKTREES:
            continue
        wt = WT_ROOT / name / "SummitEverything"
        if wt.is_dir():
            worktrees.append((name, wt))

    report: list[str] = []
    copy_report: list[tuple[str, str, int]] = []
    cred_hits: list[tuple[str, str, str]] = []
    app_records: list[tuple[str, str, int, str]] = []

    for name, wt in worktrees:
        head = git(["rev-parse", "HEAD"], wt)
        local = wt / ".local"
        dest = out / name
        if args.dry_run:
            dest = Path("/tmp/c2-dryrun") / name
        dest.mkdir(parents=True, exist_ok=True)

        manifest_lines: list[str] = []
        file_count = 0
        total_bytes = 0

        if local.is_dir():
            # .app bundles -> one tree digest each (top-level only)
            app_dirs = [
                p
                for p in local.rglob("*.app")
                if p.is_dir() and not inside_app(p.relative_to(local).parent)
            ]
            for app in sorted(app_dirs):
                digest, n = tree_digest(app)
                rel = app.relative_to(local).as_posix()
                manifest_lines.append(f"TREE {digest} {n} {rel}")
                app_records.append((name, rel, n, digest))

            for dirpath, dirnames, filenames in os.walk(local):
                dirnames[:] = [d for d in dirnames if d != ".venv" and not d.endswith(".app")]
                for fname in filenames:
                    p = Path(dirpath) / fname
                    rel = p.relative_to(local)
                    if inside_venv(rel) or inside_app(rel):
                        continue
                    try:
                        size = p.stat().st_size
                    except OSError:
                        continue
                    digest = sha256_file(p)
                    manifest_lines.append(f"{digest} {size} {rel.as_posix()}")
                    file_count += 1
                    total_bytes += size
                    if should_copy(fname, size):
                        if not args.dry_run:
                            target = dest / rel
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(p, target)
                            copied = sha256_file(target)
                            if copied != digest:
                                print(f"COPY MISMATCH {name}/{rel}", file=sys.stderr)
                                return 2
                        copy_report.append((name, rel.as_posix(), size))
                        data = p.read_bytes()
                        for cname, rx in CRED_PATTERNS.items():
                            if rx.search(data):
                                cred_hits.append((name, rel.as_posix(), cname))

        (dest / "MANIFEST.sha256").write_text(
            "\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8"
        )
        report.append(
            f"| `{name}` | `{head}` | {file_count} | {total_bytes} | "
            f"{len(manifest_lines)} | [{name}/MANIFEST.sha256]({name}/MANIFEST.sha256) |"
        )
        print(f"{name}: files={file_count} bytes={total_bytes} manifest_lines={len(manifest_lines)}")

    print(f"\nTOTAL worktrees={len(worktrees)}")
    print(f"COPY candidates={len(copy_report)} bytes={sum(s for _, _, s in copy_report)}")
    print(f"APP tree digests={len(app_records)}")
    for r in app_records:
        print("   APP", r)
    print(f"CREDENTIAL hits={len(cred_hits)}")
    for h in cred_hits:
        print("   CRED", h)

    Path("/tmp/c2-report-rows.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    Path("/tmp/c2-copy-list.txt").write_text(
        "\n".join(f"{w}  {r}  {s}" for w, r, s in copy_report) + "\n", encoding="utf-8"
    )
    Path("/tmp/c2-app-digests.txt").write_text(
        "\n".join(f"{w}  {r}  files={n}  tree_sha256={d}" for w, r, n, d in app_records) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
