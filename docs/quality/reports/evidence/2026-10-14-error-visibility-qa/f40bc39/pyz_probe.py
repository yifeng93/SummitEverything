"""Read-only probe: does the packaged backend embed the fixed event_log module?

PyInstaller stores the ``summit_everything`` package in the ``PYZ`` archive
embedded in the ``summit-backend`` executable, zlib-compressed, so a plain string
search cannot see it. This script parses the PYZ with the standard library only
(no PyInstaller, no network), loads the ``event_log`` / ``api.app`` code objects
and inspects their constants and names. It never executes bundled code and never
writes to the bundle.

Measured format at this build: header ``PYZ\\0`` + ``importlib.util.MAGIC_NUMBER``
(4 bytes) + big-endian ``toc_offset`` (4 bytes); the TOC at ``toc_offset`` is raw
``marshal`` data (not zlib); each entry is ``(name, (typecode, pos, length))``
with a zlib-compressed marshalled code object at ``pos`` (relative to the PYZ).
"""

from __future__ import annotations

import marshal
import struct
import sys
import zlib
from pathlib import Path

TARGETS = ("summit_everything.local.event_log", "summit_everything.api.app")
NEEDLES = (
    "unrecorded",
    "sk-***",
    "sk-[A-Za-z0-9_-]{8,}",
    "invalid diagnostic reason",
    "record_diagnostic",
    "_REASON_FORBIDDEN",
    "_CREDENTIAL_SHAPE",
    "_MASKED_CREDENTIAL",
    "FALLBACK_REASON",
    "clean_reason",
)


def load_pyz(blob: bytes) -> tuple[int, list[tuple[str, tuple[int, int, int]]]]:
    offset = blob.find(b"PYZ\x00")
    if offset < 0:
        raise SystemExit("FAIL: no PYZ archive magic found")
    toc_offset = struct.unpack("!i", blob[offset + 8 : offset + 12])[0]
    toc = marshal.loads(blob[offset + toc_offset :])
    return offset, toc


def walk_str_consts(code: object) -> list[str]:
    found: list[str] = []
    pending = [code]
    while pending:
        node = pending.pop()
        for const in getattr(node, "co_consts", ()) or ():
            if isinstance(const, str):
                found.append(const)
            elif hasattr(const, "co_consts"):
                pending.append(const)
    return found


def all_names(code: object) -> set[str]:
    names: set[str] = set()
    pending = [code]
    while pending:
        node = pending.pop()
        names |= set(getattr(node, "co_names", ()) or ())
        names |= set(getattr(node, "co_varnames", ()) or ())
        for const in getattr(node, "co_consts", ()) or ():
            if hasattr(const, "co_consts"):
                pending.append(const)
    return names


def main(argv: list[str]) -> int:
    executable = Path(argv[1])
    blob = executable.read_bytes()
    base, toc = load_pyz(blob)
    print(f"executable   : {executable}")
    print(f"size         : {len(blob)} bytes")
    print(f"PYZ at       : {base}, {len(toc)} modules")
    by_name = {name: entry for name, entry in toc}
    failures: list[str] = []
    for target in TARGETS:
        if target not in by_name:
            failures.append(f"{target} missing from the PYZ")
            continue
        _typecode, position, length = by_name[target]
        code = marshal.loads(zlib.decompress(blob[base + position : base + position + length]))
        consts = walk_str_consts(code)
        names = all_names(code)
        print(f"\n--- {target} ({length} compressed bytes) ---")
        for needle in NEEDLES:
            present = needle in consts or needle in names
            print(f"  {needle!r:34} present={present}")
    print("\n=== verdict ===")
    event_log = by_name.get(TARGETS[0])
    app = by_name.get(TARGETS[1])
    if event_log is None or app is None:
        print("FAIL: required modules absent")
        return 1
    _t, position, length = event_log
    code = marshal.loads(zlib.decompress(blob[base + position : base + position + length]))
    consts, names = walk_str_consts(code), all_names(code)
    checks = {
        "new masker constant _CREDENTIAL_SHAPE": "_CREDENTIAL_SHAPE" in names,
        "new fallback constant FALLBACK_REASON": "FALLBACK_REASON" in names,
        "new cleaner callable clean_reason": "clean_reason" in names,
        "literal regex sk-[A-Za-z0-9_-]{8,}": "sk-[A-Za-z0-9_-]{8,}" in consts,
        "literal fallback unrecorded": "unrecorded" in consts,
        "old rejector _REASON_FORBIDDEN removed": "_REASON_FORBIDDEN" not in names
        and "_REASON_FORBIDDEN" not in consts,
    }
    _t, position, length = app
    app_code = marshal.loads(
        zlib.decompress(blob[base + position : base + position + length])
    )
    app_names = all_names(app_code)
    checks["api.app imports FALLBACK_REASON"] = "FALLBACK_REASON" in app_names
    checks["api.app defines record_diagnostic"] = "record_diagnostic" in app_names
    for label, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            failures.append(label)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
