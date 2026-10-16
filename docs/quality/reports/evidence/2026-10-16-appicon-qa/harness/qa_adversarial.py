#!/usr/bin/env python3
"""Independent QA adversarial harness for scripts/build_macos_app.py (D).

Written from scratch for this QA pass; it does not import or reuse
tests/unit/test_build_app_icon.py.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BUILD_SCRIPT = REPO / "scripts" / "build_macos_app.py"

results = []


def record(name, ok, detail):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def load():
    spec = importlib.util.spec_from_file_location("_qa_build_under_test", BUILD_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load()
    print(f"module ROOT={mod.ROOT}")

    with tempfile.TemporaryDirectory(prefix="qa-adv-") as td:
        tmp = Path(td)
        res = tmp / "Resources"
        res.mkdir()

        # D1 missing path
        try:
            mod.embed_app_icon(res, source=tmp / "nope.icns")
            record("D1 missing path raises RuntimeError", False, "no exception raised")
        except RuntimeError as e:
            record("D1 missing path raises RuntimeError", True, f"RuntimeError: {e}")
        except Exception as e:  # noqa: BLE001
            record("D1 missing path raises RuntimeError", False, f"{type(e).__name__}: {e}")
        record("D1 nothing copied on failure", list(res.iterdir()) == [], f"dir={list(res.iterdir())}")

        # D1b a directory instead of a file
        d = tmp / "adir.icns"
        d.mkdir()
        try:
            mod.embed_app_icon(res, source=d)
            record("D1b directory as source raises", False, "no exception")
        except RuntimeError as e:
            record("D1b directory as source raises", True, f"RuntimeError: {e}")

        # D2 short file (4 bytes)
        s = tmp / "short.icns"
        s.write_bytes(b"icns")
        try:
            mod.embed_app_icon(res, source=s)
            record("D2 4-byte 'icns' raises RuntimeError", False, "no exception")
        except RuntimeError as e:
            record("D2 4-byte 'icns' raises RuntimeError", True, f"RuntimeError: {e}")

        for n, payload in [("3 bytes", b"icn"), ("0 bytes", b""), ("7 bytes", b"icns\x00\x00\x00"),
                           ("wrong magic", b"not-an-icns"), ("png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)]:
            f = tmp / f"bad-{n.replace(' ', '')}.icns"
            f.write_bytes(payload)
            try:
                mod.embed_app_icon(res, source=f)
                record(f"D2 {n} wrong-header raises", False, "no exception")
            except RuntimeError as e:
                record(f"D2 {n} wrong-header raises", True, f"RuntimeError: {e}")

        # D3 valid icns
        real = REPO / "native" / "Resources" / "AppIcon.icns"
        res3 = tmp / "Resources3"
        res3.mkdir()
        try:
            stem = mod.embed_app_icon(res3, source=real)
            ok = stem == "AppIcon" and (res3 / "AppIcon.icns").read_bytes() == real.read_bytes()
            record("D3 valid icns copied, returns 'AppIcon'", ok, f"stem={stem!r} identical="
                   f"{(res3 / 'AppIcon.icns').read_bytes() == real.read_bytes()}")
        except Exception as e:  # noqa: BLE001
            record("D3 valid icns copied", False, f"{type(e).__name__}: {e}")

        # D3b default source is the committed path
        res4 = tmp / "Resources4"
        res4.mkdir()
        stem = mod.embed_app_icon(res4)
        record("D3b default source == committed icon",
               stem == "AppIcon" and (res4 / "AppIcon.icns").read_bytes() == real.read_bytes(),
               f"stem={stem!r}")

        # D3c probe: header-only validity (8 bytes, bogus total length)
        probe = tmp / "probe.icns"
        probe.write_bytes(b"icns\x00\x00\x00\x08")
        res5 = tmp / "Resources5"
        res5.mkdir()
        try:
            mod.embed_app_icon(res5, source=probe)
            record("PROBE header-only 8-byte file is ACCEPTED", True,
                   "accepted (validation is header+length only; no chunk/ length check)")
        except RuntimeError as e:
            record("PROBE header-only 8-byte file rejected", True, f"RuntimeError: {e}")

        # PROBE: truncated real icns (valid header, cut body)
        trunc = tmp / "trunc.icns"
        trunc.write_bytes(real.read_bytes()[:4096])
        res6 = tmp / "Resources6"
        res6.mkdir()
        try:
            mod.embed_app_icon(res6, source=trunc)
            record("PROBE truncated real icns ACCEPTED", True, "accepted; no structural validation")
        except RuntimeError as e:
            record("PROBE truncated real icns rejected", True, f"RuntimeError: {e}")

    # D6 run_hdiutil surfaces command + stderr
    try:
        mod.run_hdiutil(["verify", "/definitely/not/here.dmg"])
        record("D6 run_hdiutil raises on failure", False, "no exception")
    except RuntimeError as e:
        msg = str(e)
        has_cmd = "hdiutil verify /definitely/not/here.dmg" in msg
        has_detail = "hdiutil" in msg and len(msg.splitlines()) >= 2
        record("D6 run_hdiutil raises with command + stderr", has_cmd and has_detail,
               f"cmd_present={has_cmd} multi_line={len(msg.splitlines())} msg={msg[:200]!r}")

    # D6b resolve_setfile error paths via monkeypatched subprocess
    real_check_output = subprocess.check_output
    try:
        def raise_fnf(*a, **k):
            raise FileNotFoundError(2, "No such file or directory", "xcrun")

        subprocess.check_output = raise_fnf
        try:
            mod.resolve_setfile()
            record("D6b resolve_setfile: xcrun absent raises", False, "no exception")
        except RuntimeError as e:
            record("D6b resolve_setfile: xcrun absent raises", True, f"RuntimeError: {e}")

        def raise_cpe(*a, **k):
            raise subprocess.CalledProcessError(1, "xcrun")

        subprocess.check_output = raise_cpe
        try:
            mod.resolve_setfile()
            record("D6b resolve_setfile: xcrun -f fails raises", False, "no exception")
        except RuntimeError as e:
            record("D6b resolve_setfile: xcrun -f fails raises", True, f"RuntimeError: {e}")

        subprocess.check_output = lambda *a, **k: ""
        try:
            mod.resolve_setfile()
            record("D6b resolve_setfile: empty path raises", False, "no exception")
        except RuntimeError as e:
            record("D6b resolve_setfile: empty path raises", True, f"RuntimeError: {e}")
    finally:
        subprocess.check_output = real_check_output

    # D6c resolve_setfile happy path on this host
    try:
        p = mod.resolve_setfile()
        record("D6c resolve_setfile on this host", Path(p).is_file(), f"path={p}")
    except Exception as e:  # noqa: BLE001
        record("D6c resolve_setfile on this host", False, f"{type(e).__name__}: {e}")

    print("\n==== SUMMARY ====")
    bad = [n for n, ok, _ in results if not ok]
    for n, ok, d in results:
        print(f"{'PASS' if ok else 'FAIL'}  {n}")
    print(f"total={len(results)} failures={len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
