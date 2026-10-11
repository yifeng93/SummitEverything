# DeepSeek Stage B DEV report — 2026-10-10

## 1. Candidate identity and independence

| Object | Value |
|---|---|
| Trial branch | `codex/deepseek-stage-b-trial` |
| Trial directory | `/Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial` |
| Base (fixed documentation commit) | `0a1db5d72e6ac11184d28e65dea3ba008762ba43` |
| Last committed source candidate | `7dc7114595704f34ba386c96324dffa77d529ba4` |
| Base vs last candidate | documentation only (`README.md`, `docs/`, `tasks/`); no `src/tests/web/native/scripts` or dependency diff |
| This round's tree | **uncommitted**, 26 modified + 7 new paths |

This is an implementation and self-check report. It is **not** independent review, fixed-SHA
formal QA, Stage B exit, real-provider verification or integration approval. Every independent
QA item remains `NOT_RUN`. No commit, push, PR, merge or force push was performed.

## 2. What this round implements (DEV)

1. **Real Feishu HTTP adapter** — `src/summit_everything/integrations/feishu/http.py` (new).
   Application (tenant) identity first; user identity only for the two endpoints that document
   `user_access_token` as required (minutes search, task list). Single attempt, bounded reads,
   overall deadline, no redirects, no retries, sanitized error mapping. Implements authorize,
   code exchange, refresh, tenant token, minimum user identity, minutes metadata paging,
   transcript download with artifacts fallback, calendar explicit-range read, and task
   read/create/patch. `task_result()` returns no evidence because no documented endpoint proves a
   write by `client_token`.
2. **One credential slot system** — `VaultCredentialStore` in `feishu/provider.py`. The Feishu
   app secret occupies the same vault slot the settings UI writes (`feishu_app:<account hash>`);
   the user token occupies `feishu_user:<account hash>` in the same profile namespace, keyed by
   app ID. `CredentialVault.PROVIDERS` gained `feishu_user`. `KeychainCredentialStore` now
   delegates to the same store so there is exactly one slot scheme.
3. **Server-side real-data gate** — `feishu.real_data_enabled` (default false). In real mode,
   materials/imports/calendar/tasks/task execution return `409 stage_c_authorization_required`
   (or `provider_not_configured` without an app ID). Capability summary and the executable path
   now agree.
4. **Model HTTP hardening** — model adapters pass an overall deadline (LLM 60 s, embedding and
   rerank 30 s) and reject an HTTP 200 body carrying a non-zero `code` or an `error` field.
5. **Client release** — `QueryService.close()` releases operation-scoped provider clients exactly
   once; the SSE query path and `index_execute` call it.
6. **Protocol evidence** — official Feishu documentation is readable as raw Markdown through a
   `.md` path suffix. Every Feishu row in `docs/architecture/PROVIDER-PROTOCOL-MATRIX.md` was
   re-read that way on 2026-10-10 and now quotes first-party prose for endpoint, token type,
   scope, parameters, pagination, size, time and error codes.

## 3. Offline checks (all executed in the trial tree)

| # | Command | Result |
|---|---|---|
| 01 | `uv run pytest -q -p no:cacheprovider` | exit 0 — **253 passed**, 1 existing Starlette/httpx deprecation warning |
| 02 | `uv run ruff check src tests` | exit 0 |
| 03 | `uv run ruff format --check src tests` | exit 0 — 57 files already formatted |
| 04 | `uv run mypy src` | exit 0 — 35 source files |
| 05 | `uv lock --check` | exit 0 |
| 06 | `git diff --check` | exit 0 |
| 07 | `uv build` | exit 0 — sdist + wheel |
| 08 | `npm --prefix web run api:types` | exit 0 — generated OpenAPI/TS idempotent on re-run |
| 09 | `npm --prefix web test -- --run` | exit 0 — 10 files / 39 tests |
| 10 | `npm --prefix web run typecheck` | exit 0 |
| 11 | `npm --prefix web run lint` | exit 0 — 3 existing `react(set-state-in-effect)` warnings |
| 12 | `npm --prefix web run build` | exit 0 |
| 13 | `swift build --package-path native` | exit 0 — compile only, not native acceptance |
| 14 | `PYTHONPATH=<guard>:src uv run pytest -q -p no:cacheprovider` | exit 0 — **253 passed** with the archived guard active (non-loopback sockets and macOS Keychain blocked), proving the automated suite cannot reach a real provider or the user's Keychain |

Raw stdout for every command is archived under
`docs/quality/reports/evidence/2026-10-10-deepseek-stage-b/checks/` with its `EXIT=` line. The
evidence manifest (`manifest.json`, 22 files) is self-verifying; its own SHA-256 at the time of
writing is `e27a0c98abf701771dc292ec6d1cafa3b27925387fa170947ad0dc398c0479ce`.

New test files: `test_feishu_http.py` (17), `test_http_boundary.py` (13),
`test_feishu_real_gate.py` (4); extended `test_feishu_credentials.py` (10) and
`test_stage_b_regressions.py` (7). All use `httpx.MockTransport`, in-memory secret backends and
synthetic workspaces; no real provider, Keychain item or business data is touched.

Dependency lock was **not** changed.

## 4. Sol SB-01–13 re-run on this candidate

Sol's archived harness was re-played against this tree from a replay directory outside the
repository, with the archived `sitecustomize.py` guard (non-loopback sockets and macOS Keychain
blocked). Logs: `sol-harness-regressions.log`, `sol-harness-additional.log`,
`sol-harness-frontend.log`.

| Harness | Old SHA (`1fede419`) | This candidate |
|---|---|---|
| `test_review_regressions.py` | 8 FAIL | **7 passed, 1 error** |
| `test_review_additional.py` | 2 FAIL | **1 passed, 1 assertion mismatch** |
| `SettingsView.review.test.tsx` | 1 FAIL | **1 passed** |

The two non-pass items are explained, not waived:

- `test_concurrent_refresh_must_not_overwrite_newest_refresh_token` — the harness blocks the
  first refresh inside the service lifecycle lock and only releases it *after* a synchronous
  second `materials()` call returns. With a correct single-flight lock the second call blocks on
  the first, so the harness's `release` is set too late and its `assert release.wait(5)` expires.
  The harness cannot both block and be released by construction. The underlying property is
  verified by the new product test
  `test_concurrent_near_expiry_refresh_is_single_flight`, which releases from an independent
  thread and asserts `provider.count == 1` and that the newest rotated token is retained.
- `test_capability_status_must_match_runtime_gate` — the security assertion holds (the spy LLM is
  never called; the product test asserts `provider_disabled` from the real route). The archived
  assertion compares the *reason string*, which the SB-10 fix intentionally renamed to
  `limited_synthetic_smoke_only` for a configured real provider. That is an expectation rename,
  not a regression.

## 5. SB-01–13 status on this candidate (DEV, not independently cleared)

| ID | Status here | Where it is covered |
|---|---|---|
| SB-01 P0 outbound qualification | Fixed in DEV; regression passes | `test_stale_cached_text_must_not_reach_reranker`; `query.py` qualifies before rerank |
| SB-02 P0 post-generation revalidation | Fixed in DEV; regression passes | `test_citations_must_be_rechecked_after_answer_provider_returns` asserts the stale text is dropped |
| SB-03 cancellation | Fixed in DEV | `test_cancel_after_embedding_suppresses_later_provider_calls`, `test_cancel_during_rerank_suppresses_answer_provider`, `test_cancel_during_answer_provider_discards_generated_answer` |
| SB-04 bounded candidates | Fixed in DEV | `test_query_with_101_chunks_uses_bounded_candidates` asserts ≤20 documents leave the process |
| SB-05 config restore on reopen | Fixed in DEV | `test_persisted_callback_must_be_restored_on_restart` (archived harness, passes) |
| SB-06 workspace isolation | Fixed in DEV | `test_workspace_switch_must_not_reuse_feishu_settings_or_authorization` (archived harness, passes) |
| SB-07 logout invalidates pending state | Fixed in DEV | `test_logout_must_invalidate_pending_oauth_state` (archived harness, passes) |
| SB-08 concurrent refresh | Fixed in DEV; archived harness unrunnable by construction | new `test_concurrent_near_expiry_refresh_is_single_flight` asserts one refresh consumed and newest token retained |
| SB-09 Model Studio account save | Fixed in DEV | archived `SettingsView.review.test.tsx` now **passes**; product `SettingsView.regressions.test.tsx` |
| SB-10 capability/runtime consistency | Fixed in DEV; reason renamed | product `test_provider_settings_api.py` asserts `limited_synthetic_smoke_only` + real route `provider_disabled`; archived harness fails only on the old reason string |
| SB-11 bounded HTTP reads | Fixed in DEV | archived oversize harness now **passes**; `test_http_boundary.py` adds size/deadline cases |
| SB-12 restore original R03 gate | Fixed in the base documentation commit `0a1db5d` | `ACCEPTANCE.md` R03 is the original quality/independent-QA standard; unchanged by this round |
| SB-13 handoff consistency | Addressed in DEV | protocol matrix, API contract, ADR 0006, product spec, README, PROGRESS, LATEST, plan/todo, this report |

None of the above is an independent clearance. Sol's own harness remains the archived FAIL
evidence for the old SHA and must be re-run by the independent QA context on the new SHA.

## 6. B01–B06 status

- **B01 — DEV complete, QA NOT_RUN.** Protocol matrix now quotes first-party readable sources
  with a review date; remaining unknowns are named and disable the affected capability.
- **B02 — DEV complete, QA NOT_RUN.** Unified credential slot; OS Keychain denial/lock/restart and
  native replay remain `NOT_RUN`.
- **B03 — DEV complete, real requests 0.** Real adapters implemented and stub-tested; real OAuth
  and data reads remain `NOT_RUN`.
- **B04 — DEV complete, QA NOT_RUN.** Deadline, business-error rejection and client release added;
  real account/dimension/quality remain `NOT_RUN`.
- **B05 — partial, QA NOT_RUN.** Offline checks pass; browser and native evidence for this tree
  were not collected this round and none may be borrowed from another worktree.
- **B06 — NOT_RUN.** No review, fixed-SHA QA, PR or merge.

## 7. Evidence boundary and untested items

- Real Feishu OAuth / code exchange / refresh, real material/calendar/task HTTP, real scope
  availability: **NOT_RUN**.
- Real model calls, account/region/dimension support, billing and R03 quality: **NOT_RUN**.
- Browser (DOM/console/network) and native window evidence for this tree: **NOT_RUN**.
- OS Keychain denial/lock/restart and multi-profile acceptance: **NOT_RUN**.
- Task create/edit/complete live mapping: wire-level documented, capability disabled; **NOT_RUN**.
- M3–M5, DMG, five-day, dual-machine: not started.

Consumed real calls after this round: Feishu code exchange 0/1, refresh 0/1, DeepSeek chat 0/1,
Model Studio embedding 0/1, rerank 0/1. No credential was entered and no account was accessed.

## 8. Next

Sol reviews this uncommitted tree, decides what to keep, and fixes a new source SHA. Only then
does a fresh independent context run offline fixed-SHA QA from a checkout outside the source
repository. Stage B is **DEV complete pending review**, not QA-passed.

---

## Correction added during R2 (round-1 text above is preserved as written)

- The line "**uncommitted**, 26 modified + 7 new paths" understates the final round-1 tree: it was
  29 modified + 7 new paths (two documentation index edits and one further edit landed after that
  line was written). The round-1 evidence, its 22-file manifest and this report's results are
  otherwise unchanged and still verify.
- Round 2 remediated the five P1 and one P2 findings found in review of this tree. See
  [DeepSeek Stage B DEV R2](2026-10-10-DEEPSEEK-STAGE-B-DEV-R2.md) and
  [R2 evidence](evidence/2026-10-10-deepseek-stage-b-r2/README.md). This file is not rewritten.
