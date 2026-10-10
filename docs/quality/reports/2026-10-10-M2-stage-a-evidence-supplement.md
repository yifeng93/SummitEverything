# Stage A evidence correction and supplemental UI retest

Date: 2026-10-10. This is an additive correction to the fourth-round QA record. It preserves the earlier report and artifacts; it does not revise their conclusions in place. Product source, tests, and expected results were not changed.

## Fixed revisions and scope

- Independent QA checkout: `/Users/yifengstudio/.codex/worktrees/qa-stage-a-evidence/SummitEverything`, branch `codex/qa-stage-a-evidence-supplement`.
- Checkout/base SHA: `5351a3ac6f9b6a64fd4916b06cd9269a7628bc09`.
- Product candidate checked: `32da67e9c0280e3dae18fd374e30c925565b0b82`.
- Fake-only UI runs used a disposable synthetic workspace and isolated headless Chrome profile. Services bound only to loopback ports 18917 (API), 5173 (Vite), and 19317 (CDP). No real Feishu, model, credential, or material calls were made.
- The first C17 authorization attempt returned 401 because the isolated Fake profile had not yet been authorized. This was an invalid harness/profile observation and counts as neither product PASS nor product FAIL. The profile was then authorized through the Fake UI flow, and the C17 cases below were rerun; only that authorized run is scored.

## Fourth-round screenshot audit

The archived fourth-round evidence directory is `docs/quality/reports/evidence/2026-10-10-stage-a-final-fourth-followup/`. Its 82-entry SHA manifest was checked: every listed file exists and matches its recorded SHA-256. The screenshot folder has 72 PNGs; the C16/C17/C18/C23 subset has 70 PNGs, 35 unique byte hashes, and 15 exact-duplicate groups (35 redundant filename entries). The following filename labels therefore do not independently establish distinct UI states. Existing API, disk, and automated evidence remain available in the old report and are not discarded by this screenshot correction.

| Hash prefix | Exact duplicate labels | Consequence for old UI claim; independent evidence retained |
|---|---|---|
| `b3c57c1d` | C16 after-restart; C18 restarted-initial; C23 atomic-workspace-gate | Generic workspace view only; restart and gate claims rely on old API/disk/automated evidence. |
| `7e36df69` | C16 before-confirm; concurrent-final; confirmed | Cannot prove confirm or concurrency UI transition. Existing API/Fake/disk counts remain the evidence for those transitions. |
| `c74d417a` | C16 crash-reconciled; C16 unknown-before-reconcile; C17 all-day-preview/result; C17 no-due-preview; C17 time-preview/result | Cannot substantiate any named detail state. C17 date cases were rerun in this supplement; C16 crash-specific UI was not rerun because its API/disk/restart evidence is retained. |
| `a970ec5e` | C16 crash-restart-unknown; C18 after-reload; C18 Fake-auth; C23 atomic-workspace-open | Generic workspace page; old restart/auth-specific screenshot claims invalid. Relevant API/disk evidence retained. |
| `ff360985` | C16 process-exit-before-confirm; process-exit-confirmed | Cannot show these two different states. Retained process-exit/API/disk evidence supports the backend case; no duplicate UI claim is carried forward. |
| `caddf20b` | C16 restart-replay; C18 reopened-workspace; C23 atomic-restart-unknown; workspace-open | Generic workspace page; restart/replay UI state not proven by these images. Retained API/disk evidence. |
| `d62892ed` | C17 mismatch confirmed; preview; reconciled; replay-unknown; unknown | Cannot prove proposal, confirmation, unknown, or reconciliation individually. Replaced for C17 by five distinct, visually reviewed run7 screenshots except the expected identical unknown-before/after-replay pair. |
| `4a4f6222` | C18 confirmed-not-executed; progress-awaiting-confirmation; progress-executed; progress-preview; version-conflict | Cannot prove UI progression or version conflict. Progress approval/execute UI chain rerun; stale-version API/disk/automation evidence retained, not rerun. |
| `f943ca84` | C18 receipt-confirmed; receipt-proposal | No UI distinction. Receipt API/disk evidence retained; receipt UI not rerun. |
| `3f294120` | C18 receipt-reconciled; receipt-recovered-unknown; receipt-unknown-detail | No UI distinction. Receipt recovery/reconciliation API/disk/restart evidence retained; receipt UI not rerun. |
| `286bc4b2` | C23 archive-completed-action; archive-delete-interrupted; archive-summary-interrupted | Cannot show separate archive outcomes. Old archive API/disk evidence retained. |
| `9f66a4ed` | C23 archive-conflict-copy; archive-conflict-recovered; archive-corrupt-receipt | Cannot distinguish conflict, recovery, and corruption UI. Old API/disk evidence retained; not rerun. |
| `b9aaae45` | C23 atomic-confirmed; atomic-preview | Cannot establish preview/confirmation UI transition. Atomic-write API/disk evidence retained. |
| `52e778a2` | C23 atomic-no-proof; atomic-unknown-detail | Cannot show an atomic fault's UI detail state. No atomic-fault UI rerun; underlying API/disk evidence retained. |
| `cf6cc60b` | C23 unresolved-action-preview; unknown; preserved-during-archive | Cannot prove these separate transitions. The minimum unresolved-visible-during-archive UI state was rerun below; no atomic/no-proof UI rerun. |

## Supplemental UI observations

All screenshot files are in `docs/quality/reports/evidence/2026-10-10-stage-a-evidence-supplement/screenshots/`; structured, sanitized request/state summaries sit beside them. Each image was checked for file hash and visually reviewed. The 32 new screenshots have 30 unique hashes. The only remaining collisions are deliberate stable-state pairs: C16 unknown vs same-action replay remains unknown, and C17 mismatch unknown vs same-action replay remains unknown. Their separate request/remote-count records show no second Fake write.

- **C16 no-resend UI:** action `b9905f0f-2380-4ea1-bb91-3763a325f0c0`. The detail says “结果未知，请核实；此动作不会重发。” A same-ID replay returned HTTP 200/state `unknown`; Fake remote task count stayed 10→10; the detail remained unknown. Then the history view was opened and an unknown record reopened. CDP summary records the replay and `GET /api/v1/action-intents`/detail requests, each 200. The final detail screenshot is `c16-supplement-replay-unknown.png`; C16 crash/restart reconciliation UI is not newly claimed.
- **C17 no due:** `6caf8379-67da-409a-83f5-17a804ea81de`, form explicitly selected `none`, preview/final UI says no due date. POST proposal 201, confirmation 200, execute 200/succeeded.
- **C17 all-day:** `8455dc87-c509-4257-a68b-3a8db59f49f5`, form date `2026-10-14`, zone `Asia/Shanghai`; preview and result show that date, all-day, and zone. Proposal 201, confirmation 200, execute 200/succeeded. Fake remote due was timestamp `1791907200000`, all-day true.
- **C17 concrete offset/timezone:** `c592eee6-250f-4f75-92b7-0f3b25d68a98`, form `2026-10-15T09:30:00+08:00`, `Asia/Shanghai`; preview and final UI retain both. Proposal 201, confirmation 200, execute 200/succeeded. Fake remote due was timestamp `1792027800000`, all-day false.
- **C17 mismatch:** `a615dff8-e0f9-4548-9c86-e4fe61cc1707`, form `2026-10-16T11:00:00+08:00`, `Asia/Shanghai`. UI sequence is preview → independently confirmed → unknown/no-resend. First execute and same-ID replay both returned HTTP 200/state `unknown`; Fake task count stayed 4→4 across replay. The read-only `/reconciliations` request for this same ID returned HTTP 200/state `succeeded`; final UI changed to “动作已成功”. Fake remote contains one corresponding task with due timestamp `1792119600000`, all-day false. The screenshot pair for unknown-before/after-replay is intentionally byte-identical because the displayed state must remain unchanged.
- **C18 knowledge vs progress:** after separately confirming synthetic line/project knowledge, project progress was still empty/version 0. New progress action `31483476-2522-47ea-bb7d-e0dec8f968b2` previews `尚未记录 → 独立确认后的进度`; separately confirming that action still left the project API at empty/version 0. Only executing it changed the project to `独立确认后的进度`, version 1. The preview, confirmed-not-executed, and executed screenshots are visually and hash distinct. Receipt lost-write/recovery UI remains NOT_RUN; its prior API/disk evidence is retained.
- **C23 unresolved/records view:** run `qa-stage-a-evidence-supplement-run7-c18-c23` opened the action-records view. The screen visibly listed unknown records alongside succeeded records. It then reopened unknown record `08bfd640-9a7b-4975-895e-9e1279a4aa15`; the detail still showed unknown/no-resend. The archive listing API returned 200 and its sanitized records included this same action ID/state. The two archive-view/detail screenshots are distinct. Atomic no-proof UI remains NOT_RUN; prior API/disk evidence is retained.

Browser CDP `Runtime`, `Network`, `Page`, and `Log` domains were enabled before each scripted UI operation and left enabled through the final state. Evidence records whitelisted methods, endpoint paths, selected business fields, response HTTP code/state, and console counts; request bodies were whitelisted and confirmation identifiers/hash values redacted. C17 event summary includes POST 201/200/200 for each normal action, mismatch execute/replay 200 unknown, and read-only reconciliation 200 succeeded. Inline SVG data URLs were normalized to `<inline-resource-redacted>`. No raw archive response was committed: only record count plus action ID/kind/state were retained. The UI details do not expose attempt-session values, and the `attempt_session` field was removed from the sanitized archive excerpt.

## Per-surface disposition

| Case | UI | API | Disk/Fake remote | Automated | Scope note |
|---|---|---|---|---|---|
| C16 no-resend/replay | PASS (supplemental) | PASS (supplemental + retained) | PASS (remote count unchanged) | PASS (retained old run; not rerun) | Crash-specific reconciliation UI NOT_RUN; old API/disk evidence retained. |
| C17 due-date and mismatch | PASS (supplemental) | PASS (supplemental) | PASS (Fake-only) | PASS (old run retained; not rerun) | All due variants and mismatch same-ID lifecycle directly captured. |
| C18 knowledge/progress independence | PASS (supplemental) | PASS (supplemental + retained) | PASS (synthetic project version) | PASS (retained old run; not rerun) | Receipt recovery UI NOT_RUN; API/disk evidence retained. |
| C23 unresolved record survives records view | PASS (supplemental) | PASS (supplemental) | PASS (retained old run; not rerun) | PASS (retained old run; not rerun) | Atomic no-proof UI NOT_RUN; API/disk evidence retained. |
| Real Feishu/model/materials, production credentials, native DMG | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | Not part of the authorized Fake-only supplement. |

## Capture script fingerprints

- Archived fourth-round `harness/cdp-capture-round4.mjs`: SHA-256 `12d46e207586f2e6244686b367e0d2f1aa2bbc7c937b55516cc449bc39f28bdd`. It is a compact attach/reload capture helper and does not itself drive all UI interactions.
- Prior report claimed executed script SHA `e09d5741caead2807da20465a58fa5266771824bc20be6745f3de162e0b00f7d`; retained source with that digest was not found, so this claim is unverifiable.
- Ignored QA helper `.local/qa/stage-a-final-round4/cdp.mjs`: SHA-256 `eff40dd27e1244607ba42004b6d0dfc9dcba7dd9d0c946e8eaada1ee2b982e6b`. Its retained contents provide interactive attach/evaluate/text/screenshot utilities, not the archived capture script. No invocation trace proves that it launched the archived script.
- Actual run7 executed UI scripts: `ui-c17-e2e.mjs` `8eccd313a508e71e1962e6b621b8104919cb302a7ce7f2c71acdacb1d9613413`; `ui-c16-no-resend.mjs` `187751d6e5a73e0e8b2b822137b10f97b811d73e03e248cc8d225196dc972fdb`; `ui-c18-c23-complete.mjs` `2c0c611838ebaddb827eac9fd9fbc7ef8234eda4a96f7df13c4da84489076d0a`; `ui-final-status-capture.mjs` `a7b547b37e82f92a6ef8209ddd6af37be7e8c97c01cf2fc82555a3f5df159255`. These are distinct from the archived helper. The C18/C23 script completed its capture but then exited with a QA harness `console` variable-shadowing error while printing its summary; its already-written sanitized JSON and screenshots were verified. This is a harness limitation, not a product result.

## Replay and cleanup

The checked-in artifacts are a sanitized record, not a command to contact external services. The scripts target the fixed QA checkout and loopback endpoints. To replay, start Fake-only uvicorn with a fresh disposable workspace/profile and `PYTHONPATH` including `harness/` so `sitecustomize.py` patches only `FakeFeishu`; start Vite on 5173; launch headless Chrome with `--remote-debugging-address=127.0.0.1 --remote-debugging-port=19317 --user-data-dir=<fresh isolated profile>`; authorize Fake within that profile; run `node harness/ui-c17-e2e.mjs`, then the C16/C18/C23 scripts against the matching synthetic state. Do not point this harness at real providers or existing user data. Exact run identity and process cleanup are recorded in `evidence/.../runtime-audit.json`.

At end of this run, API PID 45692, Vite PID 45705, and Chrome PID 45708 were verified by executable command line and their dedicated loopback ports/profile, stopped with SIGTERM, and rechecked. No process remained and no LISTEN socket remained on ports 18917, 5173, or 19317. Synthetic profile files remain ignored under `.local/qa/` for audit; no live services remain.

## Evidence integrity and redaction

`docs/quality/reports/evidence/2026-10-10-stage-a-evidence-supplement/sha256-manifest.json` hashes every committed artifact in this supplement directory except itself. Every manifest entry was recomputed after report finalization and validated. Sanitized JSON and image OCR/visual review were checked for credentials/state/session capability values; `attempt_session` is absent. The previous reports and their evidence remain unchanged.
