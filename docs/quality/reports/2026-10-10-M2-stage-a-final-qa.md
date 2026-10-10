# Stage A Final Independent QA — 2026-10-10

## Verdict

**BLOCKED / NOT PASSED.** The fixed source candidate has no failing results in the automated matrix and the key A-01–A-04 regression tests pass independently. Browser UI evidence passes the exercised save → explicitly confirmed first index → automatic incremental index → retrieval path. Stage A cannot be accepted or merged because the required native-shell window could not be bound to this candidate with sufficient identity evidence. Several broader browser UI scenarios were not replayed. This report does not authorize or imply a main merge.

## Fixed object and independence

- Tested source: `32da67e9c0280e3dae18fd374e30c925565b0b82` (`32da67e`).
- QA branch: `codex/qa-stage-a-final`; this report and its evidence are to be committed after the tested source, without changing product code.
- Checkout: `/Users/yifengstudio/.codex/worktrees/qa-stage-a-final/SummitEverything`.
- The original report [`2026-10-10-M2-stage-a-original-qa.md`](2026-10-10-M2-stage-a-original-qa.md) remains unchanged. Its failure evidence applies to the original candidate; this report is a new review of `32da67e`.
- Independently reread README, progress, product specification, architecture, workspace/API contracts, tester handoff, acceptance, latest implementation handoff, full v1 plan, original QA report, M2/M2.1/M2.2/M2.3 reports and M2.2 SDD report. Product scope and future real gates remain unchanged.
- Runtime dependencies were installed in an external isolated environment at `/Users/yifengstudio/.codex/worktrees/qa-stage-a-final-env-2`; the project `uv.lock` remained unchanged. Only Fake providers, synthetic records/workspace, and Fake embedding were used.

## Automated matrix

All commands below ran against the fixed candidate. Final exit code was **0** for each entry.

| Command | Result |
|---|---|
| `uv sync --frozen --group dev` | PASS (external `UV_PROJECT_ENVIRONMENT`; lock unchanged) |
| `uv run --frozen pytest -q` | PASS, **142 passed**; one existing Starlette/httpx `TestClient` deprecation warning |
| `uv run --frozen ruff check src tests scripts` | PASS |
| `uv run --frozen ruff format --check src tests scripts` | PASS, 43 files already formatted |
| `uv run --frozen mypy src` | PASS, 30 source files |
| `uv lock --check` | PASS, 32 packages resolved |
| `uv build` | PASS, sdist and wheel |
| `cd web && npm ci` | PASS, 126 packages added, 0 vulnerabilities |
| `cd web && npm run api:types` | PASS; generated OpenAPI TypeScript types |
| `cd web && npm test` | PASS, 8 files / 32 tests |
| `cd web && npm run typecheck` | PASS |
| `cd web && npm run lint` | PASS with **3 existing warnings** (`react(set-state-in-effect)` in TodayView, ProjectsView and AskView); warnings were not suppressed |
| `cd web && npm run build` | PASS |
| `cd native && swift build` | PASS |
| `git diff --check` | PASS |
| `uv run --frozen pytest -q tests/integration/test_stage_a_original_qa.py` | PASS, **4 passed**; same existing Starlette/httpx warning |

No dependency change or lock regeneration was needed. Warnings were retained and reported.

## Defects A-01 through A-05

| Finding | Status | Independent evidence and limits |
|---|---|---|
| A-01: overview save drops metadata and implicitly restores validity | **PASS** | `test_a01_overview_title_update_preserves_validity_and_metadata` exercises API → PageWriter/index/retrieval qualification; preserves `superseded`, tags, source references and custom metadata, and proves the old fact is not cited as current. |
| A-02: uncompleted task response recorded as successful | **PASS** | `test_a02_same_guid_uncompleted_task_is_not_successful_completion`; the same-GUID old task and requested-field response checks are covered, including explicit clears/normalization by adjacent action tests. |
| A-03: unrelated task accepted as unknown-action evidence | **PASS** | `test_a03_unrelated_task_does_not_reconcile_unknown_create_as_success`; unrelated task evidence leaves the action unknown. `tests/integration/test_actions.py` also covers missing/foreign execution evidence and no re-post. |
| A-04: approved save does not update active index | **PASS** | `test_a04_approved_journal_is_incrementally_indexed_without_manual_job` proves automatic incremental update using Fake embedding and retrieval eligibility. Actual browser replay below independently observes the same lifecycle. |
| A-05: status/docs overstate confirmation or shipped capability | **PARTIAL PASS** | `JournalView.test.tsx` checks confirmed/invalid/superseded display; reviewed plan and handoff language now distinguishes Fake behavior, unimplemented real adapters/resources, historical console-only evidence and untested native UI. No full browser replay of externally edited journal status was run. |

Additional security regression: the final source logs only workspace UUID and exception class for automatic-index failure. The implementation’s caplog regression excludes an exception-message probe. Full pytest, mypy, Ruff and format checks pass on the fixed source.

## Required acceptance cases

Statuses below distinguish automated integration evidence from live browser replay. Automated tests exercise product routes, writer/reader, transaction recovery and Fake adapters. A **PASS** here is not evidence of a real provider or a complete browser UI journey.

| Case | Result | Evidence / limitation |
|---|---|---|
| C09 journal/thought, associations, direct confirmation and explicit AI suggestion | **PASS (automated)** | `test_journal_supports_no_association_line_only_and_line_with_project`, invalid association rejection, `test_journal_ai_assist_is_explicit_and_returns_an_uncommitted_suggestion`, API write/retry tests. No model call is needed for normal save. UI variants were not all replayed. |
| C15 Fake auth/OAuth, selected-only import, callback/state, expiry/scope, pagination, bytes/hash/source, restart/interruption, calendar range/errors | **PASS (automated); UI PARTIAL** | `tests/integration/test_feishu.py` covers success/denial/expiry/missing scope, callback/state replay/cross-run, selected-body import, partial failures, source-byte recovery/restart, safe provider errors, calendar ranges and pagination. Actual browser materials/calendar pagination and cross-page select/cancel were **NOT_RUN**. |
| C16 independent action confirmation, invalidation, duplicate/concurrent/restart, payload conflict, unknown no-resend | **PASS (automated)** | `tests/integration/test_actions.py`: confirmation replay, stale hash, concurrency durability, restart/unknown, changed payload, no re-post and delayed response protections. |
| C17 task create/edit/clear/date/all-day/offset/completion and evidence | **PASS (automated)** | Task tests cover selected fields, explicit clears, date/time canonicalization, no invented dates, already-completed idempotency, requested-field response validation and unknown evidence. No actual UI task submission or real Feishu side effect. |
| C18 knowledge vs project progress, conflict and recovery | **PASS (automated)** | `test_project_progress_separate_from_knowledge_and_version_conflict`, writer version conflict/recovery tests, and lost-receipt recovery. |
| C04/C10/C11/C12/C13 content eligibility, outside edit, stale cache, incremental index | **PASS (automated); browser PARTIAL** | `tests/integration/test_qualified_retrieval.py` covers source/draft exclusion, external edit and reapproval, stale cached chunks, unchanged-chunk reuse, superseded knowledge, stale plans and failed model change; `test_app_lifecycle.py` covers failed index/stale citations. Browser verified first index is user-confirmed and later approved save incrementally indexes and retrieves. |
| C23 interruption/concurrency/receipt/archive/conflict/corruption | **PASS (automated)** | `test_workspace_mutations.py` covers interrupted multi-file write, external conflict and corrupt journals; `test_actions.py` covers durable running/unknown, receipt corruption, summary interruption and unresolved archive preservation. |
| Security boundaries in Stage A | **PASS (automated); real integrations NOT_RUN** | Loopback/Bearer/Origin, callback exception, safe errors, path containment, source-command-as-data, isolated profile/workspace and safe exception logging have integration/regression coverage. Browser Network capture was limited to `127.0.0.1:15203`. |

Future M3/M4/M5 scenarios, real Feishu access, real LLM/embedding/rerank, real material/keychain, five-day/two-machine gates, DMG and release verification are **NOT_RUN by scope**.

## Browser replay (fixed candidate)

The isolated browser path succeeded despite the CUA browser providers being unavailable. A separate Chrome 155 process used user-data dir `/tmp/qa-stage-a-final-chrome-32da-20261010`, CDP `127.0.0.1:19222`, with its executable and profile verified from process arguments. It visited only candidate localhost WebUI `127.0.0.1:15203` (API `127.0.0.1:18803`), run ID `qa-stage-a-final-32da67e9-20261010`. Workspace ID was `7eeee377-01df-4311-9a8a-48402f1180f6`; profile and workspace paths are recorded in `evidence/2026-10-10-stage-a-final-browser/run.json`.

Observed through actual UI:

1. Saved a synthetic journal titled `阶段A浏览器合成日志 2026-10-10`; the UI showed “内容已保存；首次索引仍需你在知识问答中确认”. The corresponding Markdown file is retained in the evidence directory.
2. Asked the UI to prepare and explicitly confirm the first index. The plan showed 1 page / 1 chunk, Fake embedding, ¥0; after confirmation the UI showed a ready local index.
3. Queried `鲸蓝九七`; the answer cited the saved synthetic page.
4. Saved a second synthetic journal after indexing was enabled. The UI showed “本机索引已更新”; index status became 2 pages / 2 chunks. Querying `琥珀岛四二` returned the second page citation without manual reindex.

CDP captured 29 final-page events: only API calls to `127.0.0.1:15203/api/v1/index/status` and `/api/v1/queries`; zero uncaught exceptions and zero console Log errors. Console contained Vite debug connection notices and the React DevTools informational notice; no warning/error was observed. This is the captured console for the tested browser run, not a claim about all native-shell consoles.

Screenshots and filesystem/API evidence:

- `evidence/2026-10-10-stage-a-final-browser/journal-saved.png`
- `evidence/2026-10-10-stage-a-final-browser/search-after-incremental-index.png`
- `evidence/2026-10-10-stage-a-final-browser/cdp-events-final.json`
- `evidence/2026-10-10-stage-a-final-browser/workspace-manifest.json`
- `evidence/2026-10-10-stage-a-final-browser/journal.md`
- `evidence/2026-10-10-stage-a-final-browser/run.json`

Replay steps: start candidate services with the same isolated API/Web ports and Fake workspace, open `http://127.0.0.1:15203`, create and save a synthetic log with a unique query phrase; open Knowledge Q&A, prepare and explicitly confirm the first index; query its phrase; save a second log with a different phrase; verify “本机索引已更新” and the 2-page/2-chunk status; query the second phrase and verify its citation. No real materials, credentials or external provider calls are involved.

## Native shell: BLOCKED

The exact candidate executable was launched from this checkout and its initial process path/PID and run identity were recorded. The first attempt used native PID 23289 and API run ID `AF71FD2D-8EFB-44A2-81B9-879060E633DF` on API 18804. CUA inventory exposed app ID `local.qa.summiteverything.m1` and window “SummitEverything QA”, but its embedded WebView reported `127.0.0.1:5173`, so no workspace or controls were touched. After a bounded relaunch, candidate PID 23689 had API run ID `0827535B-2FD6-4265-87AC-3923A60BE508` on API 18805 and Vite on 15205, while the CUA-bound window still reported 5173. That does not prove the window belongs to either candidate process. Process inspection showed a separate old M1 QA app at PID 23745 under `/Users/yifengstudio/.codex/worktrees/qa-m1-close-daf726e/...`; it was not touched.

The candidate processes and their own runner children were stopped after the mismatch. The old QA process was left running. Directory picker, app-owned WebUI workflow, normal Quit, last-window cleanup and startup-failure feedback are **BLOCKED / NOT_RUN**. User help needed: identify which “SummitEverything QA” window (if any) belongs to the candidate’s unique 15205 port/run identity, or close the old QA window and confirm the correct candidate window is visible. Do not treat a Swift build as native UI evidence.

An earlier attempt to bind the existing Chrome app selected a user page (`yifengluo.com`); interaction stopped immediately. That incident is not candidate evidence and no user-page action or data entry followed. The successful isolated Chrome/CDP path above is separate and used a fresh temporary profile.

## Findings and exit status

- New independent failures: **0 observed** in the completed automated matrix and exercised browser path.
- A-01 through A-04: **0 open P0/P1** after their regression tests passed on `32da67e`.
- A-05: UI/docs corrections are present; external-edit display was not re-enacted in a browser.
- P0 open: **0**. P1 open: **0** based on tested behaviors. P2 open: **1 acceptance blocker class** — native shell/UI and broader browser journeys still lack live evidence; no source defect was confirmed.
- The required native-shell window and several material/calendar/action UI journeys remain unverified, so the candidate is **NOT ACCEPTED** and Stage A is **not complete**. No PR merge was performed.

## Unresolved action

The user must help identify the native window that actually corresponds to the candidate `15205` WebView/run identity, or close the unrelated old QA window so the candidate can be displayed unambiguously. After that, independently finish native shell UI checks and the remaining browser workflows, update a new QA report against the same or a newly fixed SHA, then reassess the Stage A gate. No Stage B/C work has started.
