# DeepSeek Stage B DEV R3 — remediation of the R2 review findings (2026-10-10)

## 1. Baseline and independence

| Object | Value |
|---|---|
| Trial branch | `codex/deepseek-stage-b-trial` |
| Trial directory | `/Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial` |
| HEAD (unchanged, no commit) | `0a1db5d72e6ac11184d28e65dea3ba008762ba43` |
| R1 / R2 changes | preserved; this round modifies them in place |
| R1 / R2 evidence | untouched; manifests still verify 22/22 each |
| This round | **uncommitted**; 34 modified + 14 untracked entries |

This closes the five P1 findings from Sol's review of R2. It is **not** independent QA: every
independent QA item stays `NOT_RUN`, no commit/push/PR/merge happened, and no real provider
request was made (all smoke counters remain 0/1).

Method: every finding has an integrated regression that drives the real FastAPI route through the
real service, identity selector, refresh coordinator, lifecycle management, parsers and credential
adapter, replacing only the external HTTP boundary (MockTransport or a local loopback server).
Concurrency tests prove the dangerous window with `Event`s, join and inspect every worker, and
assert API result, credential state, upstream request counts and client lifecycle. Each "before"
log was produced either by the live pre-fix run during this round or by replaying the tests
against a copy of the tree with only the R3 changes reverted
(`evidence/2026-10-10-deepseek-stage-b-r3/before/OVERLAY-README.md`).

## 2. Findings

### R3-01 / P1 — an old refresh overwrote a newer authorization

**Before (live run on the pre-fix tree):** 4 of 6 regressions failed. With a refresh in flight, a
logout, a subsequent new authorization, or a service rebuilt under a new configuration did not
stop the in-flight refresh from writing its result back over the newer credential state. The
single-service generation counter could not see changes made through another service instance for
the same profile/app.

**Fix:** a `FeishuAuthCoordinator` shared per credential identity (profile namespace + app ID).
- `logout`, a successful `callback` and a refresh write-back all use one monotonically increasing
  authorization version under a shared write lock.
- A refresh records the version and the credential snapshot before the network call and re-checks
  under the shared lock before writing; if the version changed, the stale result is discarded and
  the current (newer) credential is used.
- `logout` invalidates first and deletes under the same lock so it never waits on a network call;
  lock order is always `refresh_lock → write_lock → state_lock`, with no inverse acquisition.
- A consumed single-use refresh token is recorded; a failed or lost refresh attempt is never
  retried with the same token (the next read reports `token_expired` instead).
- Removing credentials is version-aware: a logout during a refresh cannot delete or resurrect a
  later authorization.

**After:** 6/6 pass, including logout+re-authorization during a refresh, a new-configuration login
during an old-configuration refresh, a callback superseded by a logout, and the no-retry rule.
Cross-instance refresh is still single-flight (exactly one refresh consumed).

### R3-02 / P1 — the OAuth response still allowed invalid fallbacks

**Before:** 3 regressions failed — a refresh response without a new `refresh_token` was written
back with the consumed old token, and a missing `token_type` was accepted.

**Fix (official source: [刷新 user_access_token](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/refresh-user-access-token)
`.md`, which states the refresh token is single-use and the original is invalidated):**
- `fallback_refresh` is deleted. A refresh grant always requires a new `refresh_token`; a response
  that omits it or returns the consumed value is rejected (`malformed_response`).
- `token_type` must be exactly `Bearer`; a missing value is rejected.
- `expires_in` must be an integer, positive and finite; `bool`, `NaN`, `Infinity`, `0`, a negative
  or a non-numeric value are rejected.
- The effective `scope` must come from *this* response; the previous scope is never reused.
- A corrupt response never reaches the credential store.

**After:** 17/17 pass, asserting the stored credential state and that the consumed token is sent
exactly once. Covered: legal rotation, missing/duplicate refresh token, missing/wrong token type,
seven malformed expiry shapes, missing/empty scope, HTTP and business errors, and a lost response.

### R3-03 / P1 — retirement protection did not cover a complete business operation

**Before:** 3 regressions failed. The in-flight counter only covered a single HTTP call, so a
calendar read paused between the primary-calendar lookup and the events request, or an import
between two body downloads, could be closed by a configuration change and fail with
`provider_unavailable`.

**Fix:** operation-scoped leases. `FeishuHttpProvider.operation()` holds a lease for one complete
operation; the provider is retired from new work immediately but closes its client only when the
last lease and the last HTTP call have finished. Leases are re-entrant, so internal steps of a
running operation (a nested task-detail read, a transcript→artifacts fallback, every item of a
multi-item import, refresh followed by the resource read) still execute. `FeishuService` and
`FeishuTasks` hold the lease at the business-operation boundary. Configuration changes are applied
to new operations immediately; the ledger-driven credential rules of R3-01 still win over an old
operation completing.

**After:** 7/7 pass. Asserted with a real `client.close()` counter (not only a boolean): the client
stays open while an operation is in flight and closes exactly once after the last lease ends;
a further rotation does not re-close it; a failed body call still releases the lease.

### R3-04 / P1 — application-identity detail still depended on the user token

**Before (overlay replay):** 6 regressions failed. `identity_for_any` read the user credential slot
to decide a fallback and `FeishuTasks._detail_identity`/`_list_reader` read it directly, so a
corrupt or denied user slot broke calendar, body and task-detail operations that only need the
application identity.

**Fix:** identity is decided from configuration *before* any credential is read. With
`identity=app` and a real profile, an application-capable endpoint reads only the app slot; a
missing app secret is reported directly as `credential_missing` with no silent user fallback and
no widening of access. The user slot is read only for user-identity operations, and a corrupt or
denied user slot is reported as a readable `credential_unreadable` (401) rather than an internal
error. `status()` reports `authorized=false`, `app_configured`, and `credential_error` without
leaking token values.

**After:** 7/7 pass. For missing/corrupt/denied user slots, calendar, selected-body and task-detail
operations all reach the synthetic endpoint with `user slot reads == 0`; search and task list still
require a valid user authorization; a missing app secret yields `credential_missing` with zero user
reads; status never claims authorization for a corrupt slot and never contains a token.

### R3-05 / P2 — the deadline was only checked after the response arrived

**Before (live run on the pre-fix tree):** with a 300 ms deadline, headers at ~220 ms and a body
wait of 250 ms, the request *completed successfully* at ~470 ms instead of failing: httpcore
derives each socket read timeout from the request timeout, so the body received a fresh full
budget after a slow header wait. Two loopback regressions failed.

**Fix:** the transfer now runs under a cancellable deadline runner. When the remaining budget
reaches zero the runner shuts the underlying socket down (and closes the response) and **joins** the
worker before raising, so no request continues after the call returns; there is no
"future timed out while the request keeps going". No thread-future is used as fake cancellation,
and per-phase timeouts, the size cap, no-redirect, no-retry and error sanitisation are preserved.
Injected clients cannot re-enable redirects.

**After:** 7/7 loopback tests pass with a real `httpx.Client(trust_env=False)` against a local
server. Measured timings (`loopback-timings.txt`):

| Scenario | Deadline | Result | Elapsed |
|---|---|---|---|
| slow headers (0.5 s) | 0.2 s | TimeoutError | **0.203 s** |
| headers 0.22 s + body wait 0.25 s | 0.3 s | TimeoutError | **0.305 s** (old: completed ~0.47 s) |
| normal response | 0.3 s | 200 OK | 0.092 s |

Also covered: trickle-then-stall, normal empty body, oversized body, a redirect that is not
followed, and no further request after the deadline. The local servers are stopped by the fixture.

## 3. Combination regressions

- **Config switch + refresh + logout + new authorization:** the newest authorization survives, the
  old refresh runs exactly once and is discarded, status reports `real` and authorized.
- **Config switch + multi-request read + mid-operation timeout:** a 3-item import stays on its
  original configuration snapshot, item 2 fails with `provider_timeout`, items 1 and 3 succeed
  (`partial`), and the retired client closes exactly once after the operation ends.

## 4. Offline checks

| # | Command | Result |
|---|---|---|
| 01 | `uv run pytest -q -p no:cacheprovider` | exit 0 — **351 passed**, 1 existing Starlette/httpx deprecation warning |
| 02 | `uv run ruff check src tests` | exit 0 |
| 03 | `uv run ruff format --check src tests` | exit 0 — 60 files already formatted |
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
| 14 | `PYTHONPATH=<guard>:src uv run pytest -q -p no:cacheprovider` | exit 0 — **351 passed** with the archived guard active |

Guard source: `docs/quality/reports/evidence/2026-10-10-stage-b-sol-dev-review/sitecustomize.py`,
SHA-256 `1fc6c24298e07a6fbc36e882515b11926e899ddc27bff37fa3e5d77d0d76e504`. It blocks
non-loopback `connect`/`connect_ex` and the macOS Keychain backend; the R3 loopback tests bind
`127.0.0.1` only, so the guard permits them while still excluding real providers. Raw stdout for
every command is in `checks/` with an `EXIT=` line. The R3 evidence manifest (`manifest.json`, 38
files) is self-verifying; its own SHA-256 at the time of writing is
`c4e53557e483dcadacd04e545c901e1a652d4bf55559b91fd0623038db389740`. The R1 and R2 evidence
directories are untouched and still verify 22/22 each.

New tests: `test_stage_b_r3_regressions.py` (39) and `test_stage_b_r3_loopback.py` (7). Two R2
fixtures were updated for the intentionally stricter token contract (a valid `Bearer` token type
added so they keep testing the path they were written for); no expectation was weakened.

The archived Sol harness is unchanged: 7 passed / 1 error and 1 passed / 1 assertion mismatch, the
same two known archived-harness issues (a construction deadlock and a renamed reason string); the
corrected concurrent harness passes 8/8. No R2 defence regressed.

## 5. R2 defences re-verified

Real task writes still return `409 result_proof_unavailable` with provider write calls 0; local
`project_progress` is not blocked by the Feishu read gate; app-first vs user-only endpoints remain
distinct; the official primary-calendar shape and its empty/ambiguous rejection are unchanged; the
calendar `limit`/`truncated`/UI behaviour is unchanged; canonical content qualification,
post-generation revalidation, cancellation and bounded candidates still pass; the Fake flows still
pass.

## 6. Still NOT_RUN

- Real Feishu OAuth / code exchange / refresh / identity, real material / calendar / task HTTP,
  real scope availability: **NOT_RUN** (counters 0/1).
- Real model calls, account/region/dimension support, billing, R03 quality: **NOT_RUN**.
- Browser DOM/console/network evidence for this tree: **NOT_RUN** (no browser tool in this
  session). Sol replay: start `uv run python scripts/run_dev.py` with an isolated
  `SUMMIT_PROFILE_ROOT`, `SUMMIT_API_PORT` and `SUMMIT_WEB_PORT`, open the WebUI, and check that
  real mode shows "授权飞书用户身份"/"用户未授权" (never the 模拟 wording), that task execution
  returns `result_proof_unavailable`, and that a truncated calendar shows
  "仅显示部分日程，请缩小时间范围。" with no next-page control.
- Native window, OS Keychain denial/lock/restart, synthetic Keychain fault evidence: **NOT_RUN**.
- User-info identity verification: **NOT_RUN** and explicitly reported as unverified.

## 7. Next

All five findings are fixed with integrated before/after evidence. Sol reviews this uncommitted
tree, decides what to keep and fixes a new source SHA; only then does a fresh independent context
run offline fixed-SHA QA from a checkout outside the source repository. Stage B remains
**整改完成待 Sol 复核**, not QA-passed, and no new source SHA exists.
