# Stage A Final QA — fourth independent follow-up (2026-10-10)

## Verdict

**PASS — Fake-only M2.1–M2.3 acceptance on fixed candidate `32da67e9c0280e3dae18fd374e30c925565b0b82`.** This round closes the previously open C16–C18 browser/API and C23 live-fault gates using synthetic data, Fake Feishu, and a disposable local workspace. Aggregated evidence for earlier C09/C15/A05 paths is cross-referenced below without editing the original reports. No P0, P1, or P2 product defects were found in the exercised Fake scope; open Fake-scope P0/P1/P2 blockers: none.

This is not a claim that real Feishu, paid models, real business materials, Keychain, DMG/release, five-day, or two-machine gates passed. Those are **NOT_RUN by scope** and are outside this Fake-only M2.1–M2.3 decision. The UI does not provide an OAuth-cancel control; that UI variant remains **NOT_RUN**, while denial/state rejection is covered through API and automated tests. This unavailable control is not a product defect or a blocker for the Fake gate.

The user has already authorized merging when required gates are met. This report finds the specified Fake-only M2.1–M2.3 gates satisfied; it does not repeat an approval request.

## Candidate, provenance, and boundaries

- Product source SHA: `32da67e9c0280e3dae18fd374e30c925565b0b82`.
- QA checkout: `/Users/yifengstudio/.codex/worktrees/qa-stage-a-final/SummitEverything`, fourth-round base report commit `7f785c033bb96a43ae50ad6cf55b9c20474db85b`.
- This report, its evidence directory, and QA-only replay harness are new files. No product source or test was changed. Earlier reports `2026-10-10-M2-stage-a-final-qa.md`, `2026-10-10-M2-stage-a-final-followup-qa.md`, and `2026-10-10-M2-stage-a-final-third-followup-qa.md` remain unchanged.
- C09, A05 and C15 claims from earlier rounds are based on the committed evidence in `evidence/2026-10-10-stage-a-final-third-followup/` and its cited prior evidence, not recollection. The third report records the A05 before/after UI and restart status, C09 association/suggestion paths, C15 selected bad+good body partial import, pagination/cancel, Fake auth, calendar states, and callback/scope automated results. Its stated limitation that A05’s pre-edit raw copy was not retained remains explicit.
- All new content is synthetic. Only FakeFeishu/Fake embeddings were used. No real credentials, real Feishu, real tasks, real business materials, paid model calls, default Chrome profile, old M1 process PID 23745, or native candidate was operated in this round.
- The native lifecycle PASS evidence remains the separately committed prior follow-up (`native-run.json`, API 18806/Web 15206); no native window was launched for this round.

## Consolidated required-case matrix

| Case | Status | Observed evidence / scope |
|---|---|---|
| A05 external edit invalidates confirmation and citation | **PASS (prior UI + API/disk)** | The third follow-up records approved/indexed content, an external byte edit, UI “需要重新确认”/“待确认”, no stale citation, and manual reopen status. Its before-hash reconstruction limitation remains in that report. |
| C09 direct save, associations, invalid associations, suggestion cancel/accept | **PASS (prior UI/API/automated)** | See the third report and `c09-api-summary.json`; direct save did not invoke AI assist; line/project and unassociated variants were read back; cancel left editor content unchanged; accept still required explicit save; invalid fabricated association returned 422. |
| C15 Fake auth, selected-only import, bad+good partial import, pagination/cross-page selection/cancel, calendar | **PASS (prior UI/API/automated)** | Third follow-up evidence records these paths, including failed body isolation and preserved good source bytes. Auth denial, expiry, missing scope, replay/cross-run and safe errors have named automated coverage. OAuth-cancel UI control itself is **NOT_RUN** because no such control is exposed; API denial is covered. |
| C16 independent confirmation, duplicate/concurrent execute, changed payload, restart and unknown no-resend | **PASS (UI + CDP/API + Fake remote + disk)** | The UI-created/confirmed `QA R4 concurrent double` action received overlapping execute calls: one returned 202/running and the other resolved succeeded; Fake remote `tasks/results` increased exactly once (0/0→1/1). Re-execute after restart did not increase counts. Reusing its action ID with changed payload returned 409. A separate UI-confirmed `QA R4 process exit` persisted the Fake task/result then called harness `os._exit(72)`; restart mapped running→unknown, remote remained 2/2, UI showed “不会重发”, and only explicit read-only reconciliation resolved it. Before/after screenshots are under `screenshots/c16-*`; state summary records action IDs/counts. |
| C17 dates, selected-field clear, completed idempotency, provider mismatch | **PASS (UI + CDP/API + Fake remote)** | UI previews, independent confirmation and execution were observed for no date, all-day `2026-10-14` Asia/Shanghai, and offset time `2026-10-15T09:30:00+08:00`. A description-only update explicitly sent `description:""` with `update_fields:["description"]`; provider title/due stayed unchanged. Completing an already completed task via a second independent action produced no second `task_patch` (first transition count 1, repeat count 0). `QA R4 mismatch result` persisted once, then the harness returned a mismatched summary: action stayed unknown with `malformed_response`; same action replay remained unknown and read-only reconciliation found the exact Fake result. Remote count advanced 5/7→6/8 once and stayed there after reconcile. |
| C18 knowledge approval vs project-progress approval, stale version, lost success receipt recovery | **PASS (UI + API + disk/restart)** | UI created a synthetic line/project and explicitly saved a line+project journal. Project progress stayed empty/version 0 after knowledge confirmation. Progress preview showed old→new; after separate action confirmation it was still version 0; only “执行已确认动作” advanced to version 1. A separately confirmed stale `expected_version=0` action returned `failed/version_conflict` after current version 1; value/version were unchanged. A second progress action wrote manifest version 2, then the QA harness made the success-receipt write fail. Before restart its active receipt was running; after restart it became unknown. UI read-only reconciliation used the local writer journal to mark succeeded. Replaying the same action returned succeeded while progress version remained 2; the operation journal count remained 1. |
| C23 process exit, atomic manifest write interruption, running/unknown persistence and no replay | **PASS (live Fake fault injection + UI/API/disk)** | Process exit is described under C16 and was an actual API-process `os._exit(72)`. In a distinct workspace, the harness wrote/fsynced a transaction temp file and raised before `os.replace` of `manifest.json`. Manifest SHA stayed unchanged, project version stayed 0, transaction journal and active receipt stayed running; after restart the receipt became unknown. UI/API read-only reconcile found no proof and left unknown; replay remained unknown and did not mutate manifest. The unresolved receipt stayed active. |
| C23 monthly archive summary interruption, active delete interruption, unresolved retention, conflicting/corrupt receipt | **PASS (live Fake fault injection + API/UI/disk)** | In a separate workspace, a succeeded synthetic receipt was placed in the prior month as explicit fixture setup. Injecting after summary replacement returned HTTP 500 with equal active+summary copies and one summary item; the next GET recovered by deleting only active. A second delete-before-remove failure also returned 500 with equal copies; retry recovered. An `unknown` Fake timeout receipt coexisted with a prior-month completed receipt: archive moved only the succeeded receipt, kept one summary item, and left unknown in active. A conflicting active/completed copy (synthetic evidence differed) returned 409; an identical copy restored normal dedup/archive. A temporarily truncated monthly summary returned 409; restoring its exact prior SHA returned 200 with one record. |
| C15 authorization-cancel UI control | **NOT_RUN (UI; no exposed control)** | No cancel affordance exists in the current UI flow. Denial is exercised via API/automated tests; this is a UI-control limitation, not a failed product action. |
| Real integrations / release gates | **NOT_RUN by scope** | Real Feishu account/permissions/tasks/materials, real models/embeddings/rerank, OS Keychain, production DMG, five-day usage and two-machine sync were not requested or touched in this Fake-only round. These remain separate gates, not Fake QA failures. |

## Automated checks and exact nodes

Command on the fixed candidate:

```sh
uv run pytest -q tests/integration/test_actions.py tests/integration/test_workspace_mutations.py tests/integration/test_journal_overviews.py
```

Result: **43 passed, 1 existing Starlette/httpx TestClient deprecation warning**. Captured output is `evidence/2026-10-10-stage-a-final-fourth-followup/pytest-round4.txt`; all 43 exact collected node IDs are in `pytest-collected-nodes.txt`.

Key direct mappings include:

- C16: `test_independent_confirmation_replay_and_identical_titles`, `test_edit_invalidates_confirmation_and_rejects_stale_hash`, `test_concurrent_running_is_durable_before_provider_call`, `test_process_exit_restarts_unknown_remote_survives_and_archive_lookup`, `test_unknown_timeout_lookup_and_no_evidence_never_reposts`, `test_reconciliation_rejects_execution_evidence_with_another_token`, `test_late_response_preserves_cross_session_reconciliation_evidence`, `test_late_response_does_not_overwrite_final_user_outcome`.
- C17: `test_task_selected_fields_date_and_completed_idempotently`, `test_task_validation_does_not_invent_dates`, `test_patch_bad_response_is_unknown_and_selected_only_validation`, `test_task_results_validate_requested_fields_and_explicit_clears`, `test_rest_time_strings_write_scope_reads_and_canonical_payload_hash`, `test_rejects_coerced_date_boolean_and_empty_confirmation_evidence`.
- C18: `test_project_progress_separate_from_knowledge_and_version_conflict`, `test_local_progress_lost_receipt_recovers_from_writer_evidence`, plus transaction conflict coverage `test_conflicting_file_version_is_rejected_before_any_write`.
- C23: `test_receipt_hash_corruption_blocks_writes_and_monthly_summary_keeps_unresolved`, `test_summary_write_interruption_keeps_receipts_and_unknown`, `test_interrupted_multi_file_write_recovers_without_losing_either_file`, `test_recovery_preserves_an_unexpected_external_edit`, `test_recovery_stops_on_a_corrupt_transaction_journal`, `test_conflicting_file_version_is_rejected_before_any_write`.
- C09: `test_journal_association_validation_rejects_mismatched_project`, `test_journal_supports_no_association_line_only_and_line_with_project`, `test_concurrent_journal_retries_commit_exactly_one_page`, `test_lost_journal_response_can_be_replayed_after_application_restart`, `test_journal_ai_assist_is_explicit_and_returns_an_uncommitted_suggestion`.

These automated nodes supplement, and do not replace, the actual browser and injected-fault cases in the matrix.

## Browser identity, console, and cleanup

The direct Chrome executable was launched with only the isolated profile `.local/qa/stage-a-final-round4/chrome-profile`, CDP port 19239, and URL `http://127.0.0.1:15228/`; it was not the default profile and was not a native WebView. Final CDP capture reloaded the app and recorded a 2.4-second window: 41 responses, 0 failed requests, all HTTP routes on `127.0.0.1:15228`; one inline SVG resource was normalized as an inline marker. Console counts were 0 warnings, 0 errors, 0 runtime exceptions (4 log and 2 info). The route summary and capture limitation are in `cdp-events-sanitized.json`; the capture does not assert behavior outside that interval.

At cleanup, service API PID 39469, Vite PID 39484, and Chrome PID 38642 were verified by command line/profile path and stopped. Listener audit found ports 18806, 15206, 15211, 18811, 8793, 5173, 18828, 15228, and 19239 closed. The exact identity/cleanup audit is `runtime-audit.json`. No native candidate was started in this round; prior native PASS evidence remains separate.

## Evidence and replay

New artifacts are under `docs/quality/reports/evidence/2026-10-10-stage-a-final-fourth-followup/`:

- `round4-state-summary.json` — sanitized action, progress version, remote count, fault mode, and recovery summary; excludes Fake client tokens.
- `provider-trace.jsonl` — synthetic task titles/counts, selected field names, harness PIDs, and fired fault mode; no provider credential/token values.
- `cdp-events-sanitized.json` — final console and route summary without query/state values.
- `screenshots/` — actual isolated Chrome UI captures for C16–C18 and C23 flows.
- `harness/round4-sitecustomize.py` — external deterministic Fake/failpoint harness; SHA-256 `e4f219992e49fd7a855c31281726d8ec639c06e18a9cd0baa2f7a94c16b176b3`.
- `harness/cdp-capture-round4.mjs` — isolated CDP capture script; SHA-256 `e09d5741caead2807da20465a58fa5266771824bc20be6745f3de162e0b00f7d`.
- `replay.md` — runner, isolation, failpoint control values, and exact repeat steps.

Disposable workspace/profile/remote JSON remain ignored under `.local`; no workspace repository or Git history was initialized there. `sha256-manifest.json` covers committed evidence files.
