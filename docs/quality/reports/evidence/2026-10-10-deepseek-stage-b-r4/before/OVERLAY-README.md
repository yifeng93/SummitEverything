# R4 "before" evidence — how the R3 baseline was replayed

The R3 tree is uncommitted, so the pre-fix behaviour was replayed against the
**archived R3 source snapshot** taken before this round made any change
(`../r3-start-snapshot/`, hashes in `../r3-start-snapshot-hashes.txt`). No file in
the working tree was modified and the final sources were not hand-reverted.

## Construction (verified, reproducible)

```sh
BEFORE=/tmp/r4-before-src
rm -rf "$BEFORE"; mkdir -p "$BEFORE"
cp -R src/summit_everything "$BEFORE/"
for f in \
  src/summit_everything/integrations/http_boundary.py \
  src/summit_everything/integrations/feishu/service.py \
  src/summit_everything/integrations/feishu/http.py \
  src/summit_everything/integrations/feishu/tasks.py \
  src/summit_everything/api/app.py ; do
  cp "<evidence>/r3-start-snapshot/$f" "$BEFORE/${f#src/}"
done
```

Each restored file was compared byte-for-byte with the archived snapshot:
**5/5 files match** the recorded SHA-256 values. The copy therefore *is* the R3
source baseline for every file R4 touched.

## The one overlay-only shim

`live_transfer_workers()` was added by R4 (it is the product-side proof that no
transfer worker outlives a call), so the R3 baseline does not define it. The
overlay adds:

```python
# OVERLAY SHIM ONLY: the R4 worker counter did not exist in R3.
def live_transfer_workers() -> int:
    return 0
```

This keeps the R4 test modules importable. It does **not** weaken the assertions
that matter for the deadline defect: elapsed time, peer-closed detection and the
traffic-settled check are unaffected, and they are what fail on R3. The direct
`pytest.raises` on worker liveness is the assertion this shim neutralises; the
live pre-fix run performed during the round (before any R4 edit, with the real
counter present) reported exactly that failure — "a transfer worker outlived the
call" with `live_transfer_workers() == 1` and ~5.18 s elapsed for a 0.15 s
deadline — which is recorded in the R4 report.

## Running

```sh
.venv/bin/python -m pytest -q <test file> -k <case> -p no:cacheprovider \
  -o pythonpath=/tmp/r4-before-src
```

`-o pythonpath=...` overrides the project's `pythonpath = ["src"]` so the copy is
imported instead of the working tree. Each `before/*.log` in this directory was
produced with that command; the matching `after/*.log` used the working tree.
