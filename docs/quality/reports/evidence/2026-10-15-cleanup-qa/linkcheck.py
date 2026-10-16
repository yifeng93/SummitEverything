#!/usr/bin/env python3
"""Independent QA relative-link checker for tracked Markdown (口径 documented).

Scope: every tracked *.md in the checkout at the fixed QA SHA.
Links: inline Markdown  [text](target)  and  [text]: target  reference definitions.
Skipped targets: empty, bare anchors (#...), schemes http/https/mailto/tel/data.
Everything else is treated as a filesystem path resolved against the containing
file's directory (targets beginning with "/" are absolute), after stripping any
#anchor / ?query suffix and percent-decoding.  Nonexistent target => broken.

Usage: linkcheck.py <repo-root> [--only <subpath>]
"""
import os
import re
import subprocess
import sys
import urllib.parse

root = os.path.abspath(sys.argv[1])
only = None
if "--only" in sys.argv:
    only = sys.argv[sys.argv.index("--only") + 1]

files = subprocess.run(
    ["git", "-C", root, "ls-files", "*.md"], capture_output=True, text=True, check=True
).stdout.split()
if only:
    files = [f for f in files if f.startswith(only)]

INLINE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)>\s]+)>?\s*(?:\"[^\"]*\")?\)")
REFDEF = re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?\s*$", re.M)
SKIP_SCHEME = ("http://", "https://", "mailto:", "tel:", "data:", "ftp://")

broken = []
total = 0
for rel in files:
    ap = os.path.join(root, rel)
    try:
        text = open(ap, encoding="utf-8").read()
    except Exception:
        continue
    d = os.path.dirname(ap)
    for target in INLINE.findall(text) + REFDEF.findall(text):
        t = target.strip()
        if not t or t.startswith("#") or t.lower().startswith(SKIP_SCHEME):
            continue
        total += 1
        path = urllib.parse.unquote(t.split("#", 1)[0].split("?", 1)[0])
        if not path:
            continue
        if path.startswith("/"):
            resolved = os.path.normpath(path)
        else:
            resolved = os.path.normpath(os.path.join(d, path))
        if not os.path.exists(resolved):
            broken.append((rel, t, resolved))

print(f"tracked md files scanned: {len(files)}   relative-ish link targets: {total}")
print(f"TOTAL broken = {len(broken)}")
for rel, t, r in broken:
    print(f"BROKEN\t{rel}\t{t}")
