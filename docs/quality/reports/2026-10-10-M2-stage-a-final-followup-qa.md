# Stage A Final QA follow-up — 2026-10-10

## Verdict

**BLOCKED / NOT PASSED.** This supplement adds live Fake-only UI/API and native lifecycle evidence against the fixed candidate. The original independent report remains unchanged and its BLOCKED verdict is not superseded. Some requested UI flows now pass, but C16 concurrency/idempotency variants, C23 recovery fault variants, several C15 authorization/import/calendar paths, and A05 outside-edit confirmation remain unverified. Do not treat this supplement as a Stage A merge gate.

## Fixed candidate and evidence provenance

- Product source SHA: `32da67e9c0280e3dae18fd374e30c925565b0b82`.
- QA checkout: `/Users/yifengstudio/.codex/worktrees/qa-stage-a-final/SummitEverything`; QA branch `codex/qa-stage-a-final`.
- Initial independent report commit: `bb5231d5d31a64f57605bf8443f5f57752aac50d`. This follow-up adds a new report/evidence commit and does not rewrite that report or product code.
- Original browser evidence is tracked at the full repository-relative path `docs/quality/reports/evidence/2026-10-10-stage-a-final-browser/` (not `evidence/2026-10-10-stage-a-final-browser/`, the shorter path stated in the earlier report). It contains the prior Chrome/CDP events, run identity, screenshots, journal and workspace manifest. Hashes and prior UI observations are anchored by original report commit `bb5231d…`; this follow-up did not rerun or claim those observations as new.
- Scope was synthetic content/workspaces, Fake Feishu and Fake embeddings only. No real credentials, real materials, real Feishu, real task side effects, or the old M1 process PID 23745 were accessed.
- CUA IAB was used for the new browser UI; it is not the native WebView. IAB did not expose console/network event inspection, so this follow-up makes no console-clean claim. The prior isolated Chrome/CDP console evidence applies only to that earlier run.

## New follow-up results

| Case / path | Status | Evidence and limits |
|---|---|---|
| C09 direct confirmation, no association | **PASS (UI)** | Saved a synthetic journal using “确认并保存在本机”; UI stated first indexing still requires explicit confirmation. AI assistance was not invoked, so this demonstrates the direct path without a model call. |
| C09 invalid association | **PASS (API)** | Fake API POST with a fabricated line ID returned 422 `workspace_error`; no file was written for the invalid request. |
| C09 line/project association variants and suggested AI cancel/accept | **PASS (prior UI evidence)** | These were exercised in the initial report; see its evidence committed at `bb5231d…`. Not repeated in this supplement. |
| C15 material pagination/cross-page selection/cancel | **PASS (UI, synthetic provider injection)** | Query returned >20 rows, next-page control appeared; selected page 1, moved to page 2 with selection retained, selected a second item, then cancel reset selected count. QA-only harness patches only `FakeFeishu.materials`. This covers page navigation and selection retention, not every pagination/filter combination. |
| C15 material visibility filter | **PASS (API + partial UI)** | API returned the expected 12 synthetic shared rows; owner/shared behavior was observed in UI. Other filter combinations were not exhaustive. |
| C15 auth start, denied callback, consumed-state replay | **PASS (API)** | Start 200, denied callback 403, exact consumed state replay 400. No expired-state timing test or cross-run replay in this follow-up. |
| C15 selected-only import, auth success/cancel, calendar populated/empty UI | **PASS (prior UI evidence)** | Existing browser evidence/report records Fake auth success, cancellation, selected-only material body import, and calendar data/empty state. Not repeated here. |
| C15 expiry, missing scope, bad item alongside good item, calendar invalid range/timezone | **PASS (automated) / PARTIAL (API)** | Prior automated integration matrix covers expiry/scope and partial failure. This follow-up API requests confirmed reversed interval and invalid timezone each return 422. Calendar UI error/empty behavior and mixed bad+good item UI import remain **NOT_RUN**. |
| C16 task independent confirmation and execute | **PASS (UI, one action)** | UI required separate confirmation before execution and showed success. No UI double-click/concurrency or same-intent duplicate attempt was made. |
| C16 unknown response and read-only verification | **PASS (UI, limited)** | QA-only Fake injection persisted one remote task then raised timeout. UI showed “结果未知，请核实；此动作不会重发”; only read-only verification was clicked and UI found explicit evidence. The final receipt and provider storage contain one matching record. Dedicated pre/post remote-count trace was not captured, so exact numeric no-second-create assertion is **NOT_RUN**. |
| C16 duplicate/concurrent, changed payload, version conflict, confirm replay/invalidation | **PASS (automated only)** | See original report’s fixed-SHA integration matrix. These variants were not independently repeated in live UI. |
| C17 task success | **PASS (UI, one create)** | A synthetic task was independently confirmed and executed; refreshed task list showed it. Task edit/clear/date/time/completion UI variants, duplicate invocation and concurrency were **NOT_RUN** this round. |
| C18 knowledge/progress separation | **PASS (UI, one project)** | Saving synthetic project overview left Today progress at “尚未记录”; a separately prepared, independently confirmed progress action then executed and set version 1. No stale-version or competing approval UI test was run. |
| C23 restart persistence | **PARTIAL (UI)** | After restart and reauthorization, the succeeded task receipt remained visible in action history. The unknown receipt was read-only reconciled before restart; unknown/running retention across restart was not demonstrated. |
| C23 error recovery | **PASS (automated only) / NOT_RUN (injected live UI)** | The fixed-SHA automated suite covers selected recovery cases. This follow-up did not live-inject interrupted file mutation, corrupt receipt/journal, unresolved archive, external conflict, or unknown-preserve-across-restart. |
| A05 external edit then reconfirmation | **NOT_RUN (UI)** | No external workspace edit/reapproval state was changed or observed in the browser this follow-up. |
| Native directory picker and isolated workspace creation | **PASS (native UI)** | Unique QA bundle opened a `.local` synthetic workspace through NSOpenPanel, created Fake workspace, and loaded embedded WebUI. The selected workspace had no Git repo. |
| Native last-window close and Cmd+Q | **PASS (native lifecycle)** | Both were run from fresh uniquely identified candidate launches. Each exited with status 0 and released its own API/Web listeners. |
| Native startup failure feedback and exit | **PASS (native UI/lifecycle)** | Candidate targeted an isolated local dummy listener returning HTTP 503. The native alert displayed the service-not-ready message and dependency guidance. Dismissing it ended that candidate run with status 0. |

## Browser/native identity and shutdown

Native executable was copied from the fixed candidate build into an ignored temporary bundle under `.local/qa/stage-a-final-followup/SummitEverything-stage-a-final.app`. Bundle ID: `com.qa.summiteverything.stageafinalfollowup.32da67e`; executable SHA-256 `1702ef5f65d7c3bbe6853e80c356555c9ac1c3609af03a71da9bf343d643e3f5`. Successful run: candidate PID 36567, API 18806, Web 15206, run ID `1296F068-807D-4FE2-80AA-2E6ED59D40BC`; UI binding used this unique bundle identity. Full process/run/port evidence is in `evidence/2026-10-10-stage-a-final-followup/native-run.json`.

The startup-failure dummy listener owned only `127.0.0.1:18811`; candidate target ports were API 18811 and Web 15211. After dismissal, that attempted candidate exited. A later CUA `getApp` lookup auto-relaunched this uniquely identified QA bundle with defaults 8793/5173. PID 36780 executable path matched the QA bundle and runner PID 36784 cwd matched the QA checkout; both were terminated. The brief default-port page was not used as UI validation. Final audit found no listeners on 18806, 15206, 15211, 18811, 8793 or 5173 and no candidate runner. The unrelated old M1 PID 23745 was not touched.

## Reproduction assets and evidence

New evidence lives at `docs/quality/reports/evidence/2026-10-10-stage-a-final-followup/`:

- `ui-observations.md` — UI/API scope, limitations and cleanup record.
- `api-checks.json` — request methods/paths/status and sanitized response bodies; no credentials or callback state values.
- `synthetic-state-summary.json` — sanitized Fake workspace/action receipt summary.
- `native-run.json` — unique app/process/port identity and shutdown audit.
- `harness/pagination-sitecustomize.py` — SHA-256 `a3b54a4528cecdb57e19d47b79d86f9deef4dbd221c73ab6591132f6199430d5`.
- `harness/unknown-task-sitecustomize.py` — SHA-256 `d273bcf0995fc5895eb7b2068cf8fcdbccb1b89a3afe559a774c86618ebe830f`.
- `harness/startup-failure-server.py` — SHA-256 `3d99c4f7e5b011a9036760f18e49d280e12bfc75cb24449b0bf8491f122456dd`.

The two Python `sitecustomize` files are QA-only external provider patches. Reproduce only in a disposable QA checkout, with synthetic workspace/profile and Fake provider settings; place the selected harness directory first on `PYTHONPATH` when launching the normal API runner. Pagination harness replaces only `FakeFeishu.materials`; unknown harness wraps only `FakeFeishu.task_create` for its exact synthetic title, persists via original Fake method, then raises a timeout. Startup harness binds loopback port 18811 and serves HTTP 503. None modifies product source.

## Gate decision

Original report’s automated fixed-SHA matrix remains PASS as recorded there; this supplement adds no product-source changes and no new product defect was found in exercised paths. Stage A remains **NOT ACCEPTED / BLOCKED** because the listed UI and injected recovery cases remain untested, including the exact count-before/after unknown assertion, C16 concurrency and duplicate pathways, several C23 restart/fault variants, selected-item mixed failure UI, and A05 outside-edit reconfirmation. Main merge remains the user’s decision after all required gates are satisfied.
