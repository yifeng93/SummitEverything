# Stage B Luna follow-up DEV report — 2026-10-10

## Candidate identity

- Source / test candidate: `7dc7114595704f34ba386c96324dffa77d529ba4` (`codex/stage-b-real-providers`). This is the exact tested product source and test tree.
- Parent worktree baseline: `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`. Earlier Sol implementation and review checkpoints remain in Git history; neither is replaced by this candidate.
- Working tree was clean immediately after the source commit. Documentation is committed separately after the source checkpoint; no product code changes were made after `7dc7114`.
- This is an implementation and self-check report. It is not independent review, fixed-SHA formal QA, Stage B exit, real-provider verification, or integration approval.

## Fixed findings and offline evidence

The source candidate addresses Sol's SB findings as follows:

| Finding | Candidate change and offline coverage |
|---|---|
| SB-01 / SB-02 P0 | Filter unqualified cached chunks before remote rerank; cap candidates; re-read and qualify sources after model generation before returning citations/answer. Synthetic regression tests cover ineligible and stale evidence. |
| SB-03 | Check cancellation between retrieval/provider stages; disconnects signal the in-flight query and do not start later model calls. |
| SB-04 | Rerank only a bounded local candidate set with ID/index mapping; candidate count and provider body sizes are bounded. |
| SB-05 / SB-06 | Settings and Feishu service instances are keyed by active workspace/profile/app/callback. Task reads and action execution now resolve the active workspace service. A Feishu workspace-switch regression proves authorized task access in one workspace does not leak to another. |
| SB-07 / SB-08 | Logout invalidates pending authorization and in-flight callback/refresh generations; refresh is serialized and uses the latest token. Offline race tests cover logout and concurrent refresh. |
| SB-09 | Save Model Studio account selection; secret operations bind to the persisted account and the UI prevents unsaved account credential actions. |
| SB-10 | Real business model calls are rejected server-side. Dedicated smoke routes accept only fixed synthetic payloads, require saved Real-mode provider settings, and enforce an app-profile atomic one-attempt ledger. |
| SB-11 | DeepSeek / embedding / rerank use streaming response caps and bounded timeout settings, close oversized responses, disable redirects/retries, and sanitize errors. Tests cover oversize, truncation, timeout and no retry. |
| SB-12 | Original R03 real-model quality and independent-QA acceptance is restored. Finite connectivity smoke is an additional separate note and does not satisfy R03. |
| SB-13 | Protocol matrix, progress, handoff, acceptance, task ledger and this report are updated. The prior partial report has a historical correction appendix; original observations are preserved. |

One full-suite run before the workspace task-service fix exposed 22 failures: tests found task reads/actions remained bound to the app's initial Fake service after workspace-scoped authorization was added. The candidate now resolves both through the active workspace. Focused verification passed `56 passed` across the Feishu and task-action integration suites; the final full suite passed `213 passed`.

## Offline checks

| Check | Result |
|---|---|
| `uv run pytest -q` | PASS — 213 passed; one Starlette/httpx TestClient deprecation warning |
| `uv run ruff check src tests` | PASS |
| `uv run ruff format --check src tests` | PASS — 53 files already formatted |
| `uv run mypy src` | PASS — 34 source files |
| `uv lock --check` | PASS |
| `uv build` | PASS — sdist and wheel built |
| `npm --prefix web run api:types` | PASS — OpenAPI and generated TypeScript written consistently |
| `npm --prefix web test -- --run` | PASS — 39 tests across 10 files |
| `npm --prefix web run typecheck` | PASS |
| `npm --prefix web run lint` | PASS — three existing `react(set-state-in-effect)` warnings in TodayView, ProjectsView and AskView |
| `npm --prefix web run build` | PASS |
| `swift build --package-path native` | PASS |
| `git diff --check` | PASS |

These are developer checks only. They do not establish external protocol compatibility, OS Keychain lifecycle, model quality, or acceptance.

## Browser / native evidence

- A local development browser was run against the candidate using isolated profile `/tmp/summit-stage-b-dev-profile` and synthetic workspace `/tmp/summit-stage-b-browser-workspace`. The settings page showed no configured real provider secrets; the three model smoke buttons were disabled and each had one attempt remaining. No secret was entered and no external request was issued. The screenshot was visible during the CUA replay but its bytes, browser console/network capture, and evidence manifest were not archived; therefore this is limited manual DEV observation, not durable B05 evidence.
- The native app window displayed `127.0.0.1:5173`. Process inspection showed that Vite port belonged to a separate QA worktree (`/Users/yifengstudio/.codex/worktrees/qa-m1-close-daf726e/web`), not this candidate. The native window was not interacted with further and does not count as candidate evidence. Native candidate replay is **NOT_RUN**. Swift build success does not substitute for it.
- Only this run's browser and native launch sessions were stopped. The unrelated QA worktree process was left untouched.

## Limited smoke and external scope

The user pre-authorized at most one Feishu OAuth code exchange, at most one refresh if needed, and one request each to DeepSeek chat, Model Studio embedding and rerank using short synthetic inputs. This candidate implements only the three model smoke endpoints. Feishu OAuth is not implemented. Actual calls consumed: **0 of 1 per provider**. No API key/App secret was entered in the UI; no user identity, material, calendar, task, real business text or task write was accessed. No provider bill was generated by this run; provider billing was not queried.

The synthetic model input ceiling and current first-party pricing checked on 2026-10-10 are recorded in [PROVIDER-PROTOCOL-MATRIX](../../architecture/PROVIDER-PROTOCOL-MATRIX.md). The estimated three-call combined cost is below CNY 0.01 under the listed peak rates and fixed payload caps; this is an estimate, not a user-selected budget or provider invoice. CNY 5 is only the handoff's proposed ceiling.

## B01–B06 status and remaining gates

- **B01 — Partial / independent QA NOT_RUN.** DeepSeek and Model Studio wire shapes and pricing are recorded. Feishu OAuth token route/body are partly evidenced by official SDK source, but authorize parameters, identity binding, exact endpoint scopes, refresh expiry/revoke guarantees and business data schemas remain incomplete.
- **B02 — Partial / independent QA NOT_RUN.** Local settings, fail-closed Keychain backend and account-bound credential UI exist. The standalone Feishu `KeychainCredentialStore` has offline tests but is not connected to a real Feishu lifecycle. No OS denial/lock/restart or candidate native Keychain replay was performed.
- **B03 — Incomplete / NOT_RUN.** Real Feishu OAuth, material metadata/content, calendar and task HTTP adapters are absent. Unsupported or unverified capabilities remain disabled. No Feishu request was made.
- **B04 — Partial / independent QA NOT_RUN.** Model adapters and operation wiring have offline coverage. General real business calls remain server-disabled; bounded synthetic smoke is implemented but unused. Live dimensions, account/model behavior, failure billing and original R03 quality assessment remain unverified.
- **B05 — Partial / NOT_RUN as a full gate.** Offline checks passed. Browser controls were observed in an isolated synthetic workspace, but screenshot/console/network archive is missing; candidate native replay is NOT_RUN.
- **B06 — NOT_RUN.** No independent review, independent fixed-SHA QA, PR, main merge, or main tree/manifest verification has occurred.

The two Sol P0 findings are addressed in DEV tests, not independently cleared. No claim of Stage B completion or B QA PASS is made. Remaining product MUST and C01–C31 acceptance remain intact; Stage C, M3–M5, DMG, five-day use and dual-machine acceptance have not started.

## Next handoff

Keep B incomplete and QA pending until Feishu protocol evidence and adapters, credential-store service wiring, required browser/native/Keychain evidence, and remaining B implementation gates are complete. Then issue a new fixed-SHA handoff for a fresh-context independent checkout. The QA must not repeat or exceed the already authorized finite smoke counts. Do not create a PR or integrate this partial candidate.
