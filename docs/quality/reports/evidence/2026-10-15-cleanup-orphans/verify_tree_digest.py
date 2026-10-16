from __future__ import annotations

import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
files = sorted(path for path in root.rglob("*") if path.is_file())
digest = hashlib.sha256()
for path in files:
    relative = path.relative_to(root).as_posix().encode()
    digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
print(f"file_count={len(files)}")
print(f"tree_sha256={digest.hexdigest()}")
