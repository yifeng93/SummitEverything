# How the "before" logs were produced

The R2 tree is uncommitted, so the pre-fix behaviour was replayed against a
**copy** of the current source tree with only the R3 changes reverted
(`/tmp/r3-before-src`). No file in the working tree was modified.

Copy: `cp -R src/summit_everything /tmp/r3-before-src/`

Reverted to the R2 implementation (exactly the code this round replaced):

| Finding | Reverted in the copy |
|---|---|
| R3-01 | `api/app.py`: each service gets its **own** `FeishuAuthCoordinator` sharing only the refresh lock (R2 behaviour), so the authorization version is per-service instead of per-identity. `FeishuService`: per-instance generation semantics restored. |
| R3-02 | `integrations/feishu/http.py::_tokens`: `token_type` optional and `refresh_token` falls back to the consumed value when the response omits it. |
| R3-03 | `FeishuService.operation()` returns `nullcontext()`; `FeishuHttpProvider._enter`/`_maybe_close_locked` close on in-flight count only (no operation lease). |
| R3-04 | `FeishuService.identity_for_any` reads `self.credentials.get()` to decide a fallback; `FeishuTasks._detail_identity` and `_list_reader` read the user slot directly. |
| R3-05 | `http_boundary._read_bounded` clamps the phase timeout once at request start and never cancels the transfer. |

Run:

```sh
.venv/bin/python -m pytest -q tests/integration/test_stage_b_r3_regressions.py \
  tests/integration/test_stage_b_r3_loopback.py -k r3_0N \
  -p no:cacheprovider -o pythonpath=/tmp/r3-before-src
```

`-o pythonpath=...` overrides the project's `pythonpath = ["src"]` so the copy is
imported. The direct live observation during the round (before any revert) is
also recorded in the R3 report; both agree on the defect.
