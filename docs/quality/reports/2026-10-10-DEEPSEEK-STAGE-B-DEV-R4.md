# DeepSeek Stage B DEV R4 — remediation of the R3 final-review findings (2026-10-10)

## 1. Baseline and independence

| Object | Value |
|---|---|
| Trial branch | `codex/deepseek-stage-b-trial` |
| Trial directory | `/Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial` |
| HEAD (unchanged, no commit) | `0a1db5d72e6ac11184d28e65dea3ba008762ba43` |
| R1/R2/R3 changes | preserved and extended |
| R1/R2/R3 evidence | untouched; manifests still verify 22/22, 22/22, 38/38 |
| R3-start source snapshot | `evidence/2026-10-10-deepseek-stage-b-r4/r3-start-snapshot/` + hashes |
| This round | **uncommitted**; 34 modified + 21 untracked entries (55 paths) |

This closes the three findings Sol reproduced in the R3 final read-only review. It is **not**
independent QA: every independent QA item stays `NOT_RUN`; no commit/push/PR/merge happened; the
smoke ledger stays at 0/1 for every provider.

Every closure case runs the real chain — FastAPI route → real `FeishuService` + auth coordinator →
real `CredentialVault`/`VaultCredentialStore` → real `FeishuHttpProvider` → synthetic remote. The
only replacements are the OS secret backend (`MemorySecretBackend`) and the external HTTP boundary
(`MockTransport` or a local `127.0.0.1` server). No `InstrumentedStore`, no whole-provider fake and
no mocked identity/lease/deadline logic is used as closure evidence.

## 1b. Before/after summary

| Finding | R3 baseline (replayed, `before/*.log`) | This tree (`after/*.log`) |
|---|---|---|
| R4-01 | **2 failed**, 3 passed — A, B (old callback returned 200 after logout) | **5 passed** |
| R4-02 | **3 failed**, 7 passed — trickling incomplete headers, its 10-run case, and the adapter variant (the live pre-fix run additionally failed the worker-liveness assertion at ~5.18 s) | **10 passed** |
| R4-03 | **1 failed**, 5 passed — A (unrelated new operation accepted after retire) | **6 passed** |
| Combinations | **1 failed**, 1 passed — combination 2 (old trickling read) | **2 passed** |

The baseline was replayed against the archived R3 source snapshot (5/5 files verified by SHA-256);
see `evidence/2026-10-10-deepseek-stage-b-r4/before/OVERLAY-README.md`.

## 2. R4-01 / P1 — a logout no longer lets an old callback restore authorization

**Before (R3 baseline, replay + a live pre-fix run):** cases A and B failed. State was popped, the
application-credential read blocked, and the authorization version was captured only *after* that
read — so a logout that completed while the read was blocked was treated as the callback's own
baseline. The old callback then returned **200** with `authorized=true`, and in case B it could
overwrite a newer authorization.

**Fix:**
- `authorize()` binds each pending state to the authorization generation that issued it
  (`_states[state] = (session, expiry, issued_version)`).
- `callback()` validates the session, expiry and **issued generation before any possibly-blocking
  credential read**, re-validates after the read and before the token request, and validates again
  under the shared write lock before persisting. A mismatch is `invalid_state` (400) and nothing is
  written.
- The generation is shared per credential identity, so a logout or a new authorization through any
  service instance invalidates an old callback. A successful callback still bumps the generation
  (new authorization), and the consumed-refresh no-resend mechanism is unchanged.
- The network call is never performed under the shared write lock, and logout never waits on a
  network request.

**After:** 5/5 pass. Case A (blocked app-credential read → logout → resume) yields a rejection,
zero token-endpoint calls, an empty user credential slot and `authorized=false`. Case B keeps the
new authorization byte-for-byte (access/refresh token) and sends only the new authorization's
exchange. Case C (logout while the token request is in flight) does not persist the result. Case D
rejects a state issued by a previous service instance. Case E keeps the one-use semantics (second
callback rejected, exactly one exchange).

## 3. R4-02 / P1 — the overall deadline now cancels a trickling header wait

**Before (R3 baseline):** for an unterminated trickling header block with a 0.15 s deadline, the
call returned only after ~5.18 s, `live_transfer_workers() == 1`, and the server kept sending. The
R3 abort needed a parsed `Response`, and no response exists while headers are incomplete, so the
5 s join grace expired and the daemon worker survived.

**Fix:** the deadline cancels the transfer at the **transport** level. `abort_active_transfer()`
walks the httpx sync transport's connection pool (defensively; unknown shapes are ignored) and
shuts down every live connection socket — a handle that exists while the headers are still being
read. The runner then joins its worker with a bounded wait, retries once, and if the worker still
did not stop it raises instead of returning with work in flight. The previous "close the Response
if we have one" path is retained. The overall deadline remains a monotonic clock spanning connect,
headers, body and end; per-phase timeouts, the size cap, no-redirect, no-retry and error
sanitisation are unchanged, and a borrowed client is still not closed by the boundary.

The adapter test also exposed a real gap: `_application_token()` called the boundary without the
common error wrapper, so a timeout escaped as a raw `TimeoutError` (a 500) instead of a sanitized
`FeishuError`. It now goes through `_call`.

**After:** 10/10 loopback tests pass with a real `httpx.Client(trust_env=False)` against a local
server. Measured timings (fixed tolerance 0.10 s), 10 consecutive runs each:

| Case | Deadline | Worst of 10 | All values (s) |
|---|---|---|---|
| unterminated trickling headers | 0.15 s | **0.1554** | 0.1549 0.1553 0.1554 0.1534 0.1553 0.1525 0.1554 0.1553 0.1539 0.1531 |
| slow headers (0.5 s) | 0.15 s | **0.1532** | 0.1521 0.1522 0.1532 0.1523 0.1523 0.1526 0.1526 0.1524 0.1526 0.1523 |
| trickling body, incomplete length | 0.30 s | **0.3056** | 0.3056 0.3049 0.3056 0.3029 0.3054 0.3054 0.3054 0.3054 0.3054 0.3053 |

Cancellation evidence per case: `live_transfer_workers() == 0` at the moment of return; the
server-side connection is observed closed (FIN/reset) within a bounded window; for the two
trickling cases the byte count settles and the trickle loop did **not** run to completion; each
test also performs a follow-up request to prove the client still works. Also covered: late headers
with a body wait, empty body before/after the deadline, normal, oversize, redirect-not-followed,
connection error, and the real adapter path. Every local server is stopped by the fixture.

## 4. R4-03 / P2 — a retired provider no longer accepts unrelated new work

**Before (R3 baseline):** case A failed. The retire check was `self._retired and self._active_ops
== 0`, so while *any* thread held a lease another thread's brand-new operation was accepted.

**Fix:** lease ownership is now per calling thread. A thread that already owns a lease (including
nested steps) may finish on a retired provider; a brand-new operation from any thread is refused,
and a direct adapter call from a thread without a lease is refused even while another operation is
still running. The global counter is used only to decide when the client may close.

**After:** 6/6 pass — new-operation refusal with an unchanged HTTP request count, legal nested
steps and a second HTTP call completing after retire, direct adapter refusal, two leases with
nesting and an exception closing the client exactly once, and the API-level configuration switch
where the old multi-item read keeps its snapshot while a new request uses the new provider and
calendar.

## 5. Combination regressions

1. **Blocked app-credential read + logout + new authorization + old refresh returning + config
   switch:** only the legitimate new authorization survives (access/refresh token recorded), the
   old refresh runs exactly once and is discarded, `authorized=true`.
2. **Old multi-request read holding a lease + retire/config switch + new request + old request
   trickling past its deadline:** the old transfer is cancelled (`live_transfer_workers()==0`, the
   server observes termination and the trickle stops), the old client closes exactly once after the
   operation, and the new request uses the new configuration and provider.

## 6. Offline checks

| # | Command | Result |
|---|---|---|
| 01 | `uv run pytest -q -p no:cacheprovider` | exit 0 — **374 passed**, 1 existing Starlette/httpx deprecation warning |
| 02 | `uv run ruff check src tests` | exit 0 |
| 03 | `uv run ruff format --check src tests` | exit 0 — 64 files already formatted |
| 04 | `uv run mypy src` | exit 0 — 35 source files |
| 05 | `uv lock --check` | exit 0 (lock unchanged) |
| 06 | `git diff --check` | exit 0 |
| 07 | `uv build` | exit 0 — sdist + wheel |
| 08 | `npm --prefix web run api:types` | exit 0 — regenerated, idempotent on re-run |
| 09 | `npm --prefix web test -- --run` | exit 0 — 10 files / 42 tests |
| 10 | `npm --prefix web run typecheck` | exit 0 |
| 11 | `npm --prefix web run lint` | exit 0 — 3 existing `react(set-state-in-effect)` warnings |
| 12 | `npm --prefix web run build` | exit 0 |
| 13 | `swift build --package-path native` | exit 0 — compile only |
| 14 | `PYTHONPATH=<guard>:src uv run pytest -q -p no:cacheprovider` | exit 0 — **374 passed** with the archived guard active |

Raw stdout for every command is archived in `checks/` with an `EXIT=` line. The R4 evidence
manifest (`manifest.json`, 34 files) is self-verifying; its own SHA-256 at the time of writing is
`90c8ecc3c004cb08e8528743285f23aecac9bf57ec0f5a0fc0e167cfe5c93250`. The R1/R2/R3 evidence
directories are untouched and still verify 22/22, 22/22 and 38/38.

Guard source: `docs/quality/reports/evidence/2026-10-10-stage-b-sol-dev-review/sitecustomize.py`,
SHA-256 `1fc6c24298e07a6fbc36e882515b11926e899ddc27bff37fa3e5d77d0d76e504`. It blocks
non-loopback sockets and the macOS Keychain; the R4 loopback tests bind `127.0.0.1` only, so the
guard permits them while still excluding real providers. The full check battery was executed after
the last product edit.

New tests: `test_stage_b_r4_regressions.py` (5), `test_stage_b_r4_loopback.py` (10),
`test_stage_b_r4_lifecycle.py` (6), `test_stage_b_r4_combinations.py` (2). Existing unit and Fake
tests were kept; no assertion was weakened. R2/R3 defences were re-run as part of the full suite:
real task writes still return `409 result_proof_unavailable` with zero write calls, local
`project_progress` is not gated by reads, app-identity operations never read the user slot, the
search/task-list user requirement, strict OAuth/refresh rotation, the official primary-calendar
shape and calendar truncation, canonical qualification, pre-publication revalidation, cancellation
and bounded candidates, the Fake flows and the model/HTTP error handling all still pass.

## 7. NOT_RUN

- Real Feishu OAuth / code exchange / refresh / identity, real material / calendar / task HTTP,
  real scope availability: **NOT_RUN** (ledger 0/1).
- Real model calls, account/region/dimension support, billing, R03 quality: **NOT_RUN**.
- Browser DOM/console/network for this tree: **NOT_RUN** (no browser tool in this session). Sol
  replay: isolated `SUMMIT_PROFILE_ROOT`/`SUMMIT_API_PORT`/`SUMMIT_WEB_PORT`, then check the
  real-mode authorization copy, the `result_proof_unavailable` task rejection and the truncated
  calendar notice.
- Native window, OS Keychain denial/lock/restart and synthetic Keychain fault evidence: **NOT_RUN**.
- User-info identity verification: **NOT_RUN** and reported as unverified.

## 8. Next

All three findings are fixed with reproducible before/after evidence. Sol reviews this uncommitted
tree, decides what to keep and fixes a new source SHA; only then does a fresh independent context
run offline fixed-SHA QA from a checkout outside the source repository. Stage B remains
**R4 DEV 整改完成待 Sol 复核**, not QA-passed, and no new source SHA exists.
