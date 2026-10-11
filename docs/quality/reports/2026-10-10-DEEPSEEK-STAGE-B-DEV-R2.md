# DeepSeek Stage B DEV R2 — review-finding remediation (2026-10-10)

## 1. Identity and independence

| Object | Value |
|---|---|
| Trial branch | `codex/deepseek-stage-b-trial` |
| Trial directory | `/Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial` |
| HEAD (unchanged, no commit) | `0a1db5d72e6ac11184d28e65dea3ba008762ba43` |
| Last committed source candidate | `7dc7114595704f34ba386c96324dffa77d529ba4` |
| Round-1 DEV report | [2026-10-11-DEEPSEEK-STAGE-B-DEV.md](2026-10-11-DEEPSEEK-STAGE-B-DEV.md) (kept as written) |
| This round | **uncommitted**; round-1 changes preserved and extended |

This resolves the five P1 findings and the one P2 finding from Sol's independent DEV review of
round 1. It is **not** independent QA: every independent QA item stays `NOT_RUN`. No commit,
push, PR, merge or force push happened. No real provider request was made.

## 2. Findings, failing regression first, then result

Each finding has a regression that failed on the round-1 tree and passes now. All are in
[tests/integration/test_stage_b_r2_regressions.py](../../../tests/integration/test_stage_b_r2_regressions.py)
unless noted.

### R2-01 (P1) — real task writes were reachable

**Before:** `feishu_task_write.available=false` / `disabled_reason=result_proof_unavailable`,
yet with `real_data_enabled=true` and a synthetic user token, an independently confirmed task
action executed and returned `200 succeeded` after one stub `task_create`. The route used only
the generic read gate.

**Fix:** an independent write-capability gate at two layers.
- `FeishuService.require_task_write()` refuses any non-fake profile with
  `FeishuError("result_proof_unavailable")` → HTTP 409.
- `ActionService._require_write(kind)` calls it (plus the per-operation user scope) *before*
  claiming a durable `running` receipt, so the API returns a stable readable rejection instead
  of marking the action unknown.
- `FeishuTasks.execute` repeats the check so no other caller bypasses it.
- `real_data_enabled` now controls reads only; `project_progress` is never gated by the Feishu
  read gate.

**After:** create/update/complete each return `409 result_proof_unavailable` with
`task_create`/`task_patch`/`exchange`/`refresh` call counts all 0; the capability summary agrees;
Fake task confirmation/execution/unknown semantics unchanged; local `project_progress` succeeds
even with reads disabled. 6 tests (`r2_01`).

### R2-02 (P1) — application identity did not reach the service layer

**Before:** the HTTP adapter could use a tenant token, but `FeishuService.calendar()` called
`_user(...)` first and returned `not_authorized` with only an app secret. `imports()` required the
minutes-search user scope for the body download. `FeishuTasks.get` had the same user-first
precondition.

**Fix:** per-operation identity selection.
- `identity_for(scope, app_capable=...)` / `body_identity()` / `identity_for_any(...)`: for a real
  profile with `identity=app`, an endpoint that documents `tenant_access_token` uses the
  application token and never reads, refreshes or requires a user token.
- Minutes search and task list still require `user_access_token` (documented requirement).
- The body download accepts the transcript **or** artifacts scope and no longer accepts the
  search scope as a substitute.
- Missing app secret → `credential_missing`; no user token → `not_authorized`; insufficient scope
  → `missing_scope`. A permission error never switches identity to widen access.
- `FeishuProvider`, `FeishuHttpProvider` and `FakeFeishu` signatures accept
  `UserCredentials | None` for app-capable endpoints.

**After:** through real API → service → HTTP `MockTransport`, an app-secret-only profile reaches
the calendar and transcript endpoints with no `user_info` or `oauth/token` request; search and
task list still return 401; deleting the app secret returns 503 `credential_missing`. 4 tests
(`r2_02`).

### R2-03 (P1) — primary calendar was parsed from the wrong shape

**Before:** `data.calendar.calendar_id`; the official `data.calendars[].calendar.calendar_id` shape
returned `malformed_response`.

**Fix:** parse the official list, skip `is_deleted` entries, require a string `calendar_id`, skip
the lookup entirely when an explicit `calendar_id` is configured, and refuse to guess:
empty → `404 no_primary_calendar`; more than one candidate → `409 ambiguous_calendar` (no
verified identity is held, and no user-info call is made). No assumption that the app's primary
calendar is the user's personal calendar.

**After:** official shape accepted; explicit id performs no primary request; empty, deleted-only,
ambiguous and malformed payloads fail distinctly; permission error maps to `missing_scope`.
10 tests (`r2_03`).

### R2-04 (P1) — settings changes did not reach the execution path

**Before:** the service cache key was `(profile, app_id, redirect_uri, mode)` only, so changing
`identity` / `calendar_id` / `material_content` kept serving the old configuration.

**Fix:**
- The key now includes `identity`, `calendar_id` and `material_content`.
- A superseded service for the same profile/app is retired: its HTTP provider stops accepting new
  work and closes once its last in-flight call ends (`FeishuHttpProvider.retire()` with in-flight
  accounting), so an operation started under the old configuration keeps its snapshot and no
  client leaks.
- Pending OAuth state is per-service, so an old state is rejected by the new configuration
  (`invalid_state`).
- Refresh coordination moved to a lock shared by every service instance of the same
  profile/app; the token is re-read under that lock, so a rebuild cannot consume a single-use
  refresh token twice, and a logout during a refresh cannot resurrect credentials.

**After:** changing identity/calendar/body mode takes effect on the next request (verified by the
upstream calendar path, the transcript-vs-artifacts path and the Authorization header); an old
pending state is rejected after the change; two service instances sharing one refresh lock consume
exactly one refresh; a retired provider closes only after its in-flight call returns and refuses
new work afterwards. 4 tests (`r2_04`).

### R2-05 (P1) — calendar limit hidden the upstream cap and truncation

**Before:** the API allowed `limit` 1–30 while the adapter requested at least `page_size=50` and
returned every item; a legal 21-item response became `malformed_response`.

**Fix:** the explicit range is still a single request with `page_size = max(50, limit)` and no
auto-expansion, `anchor_time` or follow-up request. All upstream items are validated first, then at
most `limit` are returned. `CalendarPage.truncated` (default `false`) is true when the upstream
count exceeded the local limit, reached the upstream `page_size`, or the response reported
`has_more`. A real explicit range always returns `next_cursor=null`. The UI shows
"仅显示部分日程，请缩小时间范围。" and hides the next-page control when truncated. Malformed
items are still rejected rather than sliced away.

**After:** 0/20/21/50-item responses and `limit` 1/20/30 behave as specified, 21 items no longer
errors, item count never exceeds `limit`, `has_more` reports truncation, malformed entries still
fail, and exactly one upstream range request is made. 11 tests (`r2_05`) + 2 component tests.

### R2-06 (P2) — the overall deadline missed part of the lifecycle

**Before:** `_read_bounded` checked the deadline only when a body chunk arrived; a 10 ms deadline
with a ~66 ms empty response was accepted.

**Fix:** one overall deadline now spans connecting, waiting for response headers, every body chunk
(including an empty body) and read completion. Phase timeouts are clamped to the remaining budget
so waiting cannot renew a full budget per phase, and `follow_redirects=False` is forced per request
even when the injected client would follow. No thread-future timeout is used as fake cancellation.

**After:** with an injected deterministic clock, slow headers, a slow first byte and sustained
small chunks all raise `TimeoutError` and close the response; a normal empty body inside the
deadline is accepted; oversize still fails; a redirecting handler is not followed (exactly one
request). 6 tests (`r2_06` in [test_http_boundary.py](../../../tests/unit/test_http_boundary.py)).

## 3. Status and source-attribution fixes

- `FeishuStatus.mode` now reflects the real configuration; a real profile never reports `fake`.
- `FeishuStatus` separates `authorized` (usable **user** token) from `app_configured` (stored app
  secret) and reports `identity`; `user_identity_verified` stays `false` because no real identity
  lookup was executed (user-info remains `NOT_RUN`).
- Real adapter imports record `external_identity.provider = "feishu"` and the actual
  `token_type` (`app` or `user`); Fake imports stay `feishu-fake`/`user`.
- The UI shows real-mode copy ("授权飞书用户身份", "用户已授权/用户未授权", an explicit
  "应用密钥已配置；用户身份尚未授权或验证。") and only the Fake mode keeps the 模拟 wording.
- OAuth parsing is strict: documented `expires_in` (positive), non-empty effective `scope` and
  `Bearer` `token_type` are required; a missing field is an error instead of an invented default,
  and a first exchange without `offline_access`/`refresh_token` reports `missing_scope`. Refresh
  rotation is preserved and reuses the previous refresh token only when the server omits a new one.

## 4. Offline checks

| # | Command | Result |
|---|---|---|
| 01 | `uv run pytest -q -p no:cacheprovider` | exit 0 — **305 passed**, 1 existing Starlette/httpx deprecation warning |
| 02 | `uv run ruff check src tests` | exit 0 |
| 03 | `uv run ruff format --check src tests` | exit 0 — 58 files already formatted |
| 04 | `uv run mypy src` | exit 0 — 35 source files |
| 05 | `uv lock --check` | exit 0 (lock unchanged) |
| 06 | `git diff --check` | exit 0 |
| 07 | `uv build` | exit 0 — sdist + wheel |
| 08 | `npm --prefix web run api:types` | exit 0 — regenerated OpenAPI/TS, idempotent on re-run |
| 09 | `npm --prefix web test -- --run` | exit 0 — 10 files / **42 tests** |
| 10 | `npm --prefix web run typecheck` | exit 0 |
| 11 | `npm --prefix web run lint` | exit 0 — 3 existing `react(set-state-in-effect)` warnings |
| 12 | `npm --prefix web run build` | exit 0 |
| 13 | `swift build --package-path native` | exit 0 — compile only, not native acceptance |
| 14 | `PYTHONPATH=<guard>:src uv run pytest -q -p no:cacheprovider` | exit 0 — **305 passed** with the archived guard active |

Guard source: `docs/quality/reports/evidence/2026-10-10-stage-b-sol-dev-review/sitecustomize.py`
(archived from Sol's round). It is copied verbatim to a replay directory outside the repository and
placed first on `PYTHONPATH`; the log header records the exact command and the guard path. It
blocks non-loopback `connect`/`connect_ex` and the macOS Keychain backend, so the suite cannot
reach a real provider or the user's keychain.

Raw stdout for every command is in `checks/` with an `EXIT=` line. The R2 evidence manifest
(`manifest.json`, 22 files) is self-verifying; its own SHA-256 at the time of writing is
`1ed3e718e2597b312f9b4f07b6f09f79fbe20a0aa6ba58d49f40c77787e3ca45`. The round-1 evidence
manifest is unchanged and still verifies 22/22. New tests this round: 46 in
`test_stage_b_r2_regressions.py`, 6 in `test_http_boundary.py`, 2 in `FeishuPanel.test.tsx`; one
existing status expectation in `test_feishu.py` was extended with the new explicit fields (its
original assertions are preserved).

## 5. Sol harness re-run and the corrected concurrency harness

Archived originals are untouched.

| Harness | Round-1 tree | This tree |
|---|---|---|
| `test_review_regressions.py` (archived) | 7 passed, 1 error | 7 passed, 1 error (same construction deadlock) |
| `test_review_additional.py` (archived) | 1 passed, 1 assertion mismatch | 1 passed, 1 assertion mismatch (renamed reason string) |
| `test_review_regressions_corrected.py` (**new**) | n/a | **8 passed** |

The corrected harness changes only the concurrent-refresh test: it releases the blocked refresh
from an independent thread instead of after a synchronous call that a correct single-flight lock
must block. With that change all 8 archived expectations pass, which shows the archived error was
the harness's own deadlock and not the product. The archived FAIL log and the explanation are both
retained. The capability reason-string mismatch is covered by a real security assertion in the
product test (`provider_disabled` from the live route) plus the new R2-01 write-gate tests.

## 6. Remaining gaps (unchanged)

- Real Feishu OAuth / code exchange / refresh, real material/calendar/task HTTP, real scope
  availability: **NOT_RUN**.
- Real model calls, account/region/dimension support, billing, R03 quality: **NOT_RUN**.
- Browser (DOM/console/network) and native window evidence for this tree: **NOT_RUN**.
- OS Keychain denial/lock/restart and multi-profile acceptance: **NOT_RUN**.
- User-info identity verification: **NOT_RUN** (and explicitly marked unverified).
- Task create/edit/complete live mapping: wire-level documented, capability still disabled.
- M3–M5, DMG, five-day, dual-machine: not started.

Consumed real calls after this round: Feishu code exchange 0/1, refresh 0/1, DeepSeek chat 0/1,
Model Studio embedding 0/1, rerank 0/1. No credential entered, no account accessed.

## 7. Correction to the round-1 summary

The round-1 report recorded "26 modified + 7 new paths". The final round-1 working tree had
29 modified + 7 new paths (the two documentation index files and one further edit were added after
that line was written). Round-1 evidence and its manifest are unchanged and still verify 22/22;
the final R2 working tree is 34 modified + 11 untracked entries (45 paths, no commit). No round-1 result is rewritten.

## 8. Next

All six findings are fixed in DEV with regression evidence. Sol reviews this uncommitted tree,
decides what to keep and fixes a new source SHA; only then does a fresh independent context run
offline fixed-SHA QA from a checkout outside the source repository. Stage B remains
**DEV complete pending review**, not QA-passed, and no new source SHA exists yet.
