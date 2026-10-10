# Stage B / C Execution Plan

## Overview

Implement and offline-verify the real provider adapters and local configuration required by Stage B, then obtain independent review and fixed-SHA QA before source integration. The user has since authorized a narrow smoke-test track for Feishu OAuth connection and paid model adapters using synthetic inputs; broader Stage C, real business materials, data reads and task operations remain separately gated.

## Baseline

- Starting `origin/main`: `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`.
- Contains Stage A closeout `117086eb2075726730cd7aa62ea0b61498e96f0c`.
- `src/tests/web/native` matches Stage A tested tree `30903c4cdf73855af71a201e3edea6c535ee8199`.
- Implementation branch: `codex/stage-b-real-providers` in isolated worktree.
- Existing `tasks/plan.md` and `tasks/todo.md` were absent at start.

## Assumptions and fixed boundaries

- Real provider use stays opt-in; defaults remain Fake / offline.
- Settings previews, saves, reloads, and rendering never perform provider requests.
- Secrets are entered locally and stored only via a fail-closed macOS Keychain adapter; no secret value enters chat, files, CLI arguments, logs, or frontend storage.
- Tests use HTTP stubs, fake providers, synthetic workspace data, and dedicated synthetic Keychain items only.
- Feishu writes remain capability-disabled wherever official sources do not establish exact date semantics or independently verifiable results. Unknown outcomes are never retried as writes.
- No real Stage C action occurs until B passes independent QA and the user approves an itemized scope, request count, and cost ceiling.
- Exception: user authorization dated 2026-10-10 permits preparation and a bounded synthetic smoke-test batch before full B closure: one Feishu OAuth/code exchange (and at most one refresh if needed) plus at most one synthetic request each to DeepSeek chat, Model Studio embedding and rerank. Use keys entered through the local secure UI only. CNY 5 is a conservative operating cap proposed in this prompt, not a user-specified budget; verify current official prices first and ask only for a higher ceiling if the estimate cannot fit under it.
- This smoke authorization excludes Feishu material/calendar/task reads, all business content, any real material sent to a model, and every real task write. No raw keys or tokens in chat, source, terminal arguments, logs, HAR or screenshots.
- Stage C does not include M3–M5, DMG, five-day use, or dual-machine acceptance.

## Task List

### Phase 1: Protocol and contract freeze

- [ ] B1.1 Read official Feishu, DeepSeek, and Alibaba Model Studio documentation; record source URL, review date, request/response mapping, scopes, pagination, limits, error behavior, cost and unresolved questions in a protocol matrix.
- [ ] B1.2 Freeze typed provider, settings, credential-store, and capability contracts without changing product MUST; update API / workspace contracts or ADR where needed.
- [x] B1.3 Confirm local non-secret provider selections with the user if their account region, callback URI, model IDs, or embedding dimensions affect endpoint configuration. User supplied Feishu callback `http://localhost:8765/callback`, stated admin can grant additional scopes, and provided model/provider endpoint and model details; no secret values were supplied.

### Phase 2: Local configuration and credentials

- [ ] B2.1 Add persisted, validated, non-secret settings with Fake/offline default and explicit real-provider mode; no network side effects on GET/PATCH/reload/preview.
- [ ] B2.2 Add secret references and a namespaced Keychain adapter for app/provider/profile/account, plus set/update/delete/logout/rotation failure handling.
- [ ] B2.3 Add settings UI and safe error/state reporting; exercise browser and native development-shell Keychain flows with only synthetic test items.

### Phase 3: Feishu adapter

- [ ] B3.1 Add real OAuth authorization/code exchange/refresh/logout, one-use session-bound state, exact registered callback, user-scope checks, and safe callback/log behavior.
- [ ] B3.2 Add metadata pagination and selected TXT/Markdown body download, calendar range pagination, and task reads using stubs and malformed/partial/error fixtures.
- [ ] B3.3 Add task create/edit/complete only where source evidence proves mapping; preserve action journal, independent confirmation, receipt verification and no-resend. Disable any unresolved date/result capability.

### Phase 4: Model and retrieval adapters

- [ ] B4.1 Add structured LLM requests for intake, journal assist, and grounded answers; validate output, cancellation, timeout, injection boundaries, stale citations, and no implicit approval.
- [x] B4.2 Embedding batch/dimension/model fingerprint validation and atomic SQLite generation switching; no implicit paid rebuild on config change. Offline model-change failure preserves the previous active generation; live account dimension behavior remains unverified.
- [ ] B4.3 Add rerank mapping/result validation and explicit observable failure or degradation.

### Phase 5: Fixed-candidate DEV evidence

- [x] B5.1 Full offline checks pass in DEV (Python, Web API generation/tests/typecheck/lint/build, lock, Python package build, Swift build); existing warnings are recorded separately.
- [ ] B5.2 Exercise the settings/provider paths in a real browser and native development shell using isolated synthetic fixtures; capture actual harness bytes, hashes, console/network summary, and sanitized evidence.
- [ ] B5.3 Complete independent code review and fix required findings in separate commits; keep DEV, review, QA and actual-provider results distinct.
- [ ] B5.4 Commit a fixed candidate SHA and request independent QA in a new context and checkout. If an independent QA environment cannot be provided, leave status DEV complete / QA pending.

### Phase 6: Independent QA and source integration

- [ ] B6.1 QA tests the fixed SHA against B gates, applicable C01–C31 and Stage A regressions without changing implementation or expected outcomes.
- [ ] B6.2 Repair any defects separately and have QA re-test the new SHA; preserve prior FAIL reports.
- [ ] B6.3 Create PR, merge without squashing away the tested SHA, verify main source-tree identity, report and evidence manifest hashes, and run appropriate post-merge smoke checks.

### Phase 7: Stage C controlled external validation

- [ ] C0 Limited synthetic smoke scope is pre-authorized as stated above. Before use, record exact endpoint, synthetic payload, per-provider request count, current official price estimate, proposed total CNY 5 operating cap, and stop conditions. Broader C operations still require an itemized authorization table after B passes. User enters secrets only through the local secure UI/Keychain.
- [ ] C1 Run only approved OAuth/read-only tasks and selected material access, with synthetic workspace intake; record unapproved or unsupported items as NOT_RUN/BLOCKED.
- [ ] C2 Run only approved bounded model calls, first on approved non-sensitive synthetic materials; separate provider availability from quality evaluation and preserve user judgments.
- [ ] C3 Perform only explicitly approved isolated test-task creation/edit/completion. Require final-field confirmation before each write and stop on timeout/unknown; do not clean up real test resources without separate approval.
- [ ] C4 If Stage C fixes code, return to B fixed-SHA review/QA and obtain any required renewed real-operation authorization before re-test.

## Checkpoints

- [ ] Protocol matrix and contract are reviewable before implementation.
- [ ] Each implementation slice has failing-then-passing focused tests before the next slice.
- [ ] Candidate is fixed and DEV evidence complete before independent QA begins.
- [ ] Main integration happens only after independent QA passes.
- [ ] Stage C starts only after B passes and user authorization is recorded.

## Current implementation ledger (2026-10-10)

- **Partial:** B1.1 official protocol matrix exists. DeepSeek and Model Studio mappings are recorded. User's listed Feishu scopes and admin status remove scope-grant availability as a blocker; exact per-endpoint scope requirements still need verification. Official generated SDK models support offline DTO/fake coverage for OAuth code/refresh, minutes search/transcript, calendar pagination and task timestamps, but readable official endpoint docs did not confirm routes/headers, time-window semantics, or write reconciliation. Feishu real capabilities stay disabled.
- **Partial:** B1.2 typed settings, credential-store boundary, ADR and API contract update exist. Provider secrets now include a hashed account identity in the Keychain key; Feishu OAuth user identity and runtime wiring remain open.
- **Done in DEV scope:** B2.1 atomic local non-secret settings, strict validation, Fake default, and no-network GET/PATCH behavior are implemented.
- **Partial:** B2.2 fail-closed macOS Keychain backend and synthetic save/delete flow work in the browser; profile/provider/account-label separation is implemented. A `KeychainCredentialStore` now persists Feishu user-token pairs and a separate app secret through the existing `SecretBackend`; offline tests cover restart, rotation, logout, profile/App ID isolation, app-secret separation, identity mismatch and sanitized corrupt data. It is not yet wired to the Feishu API lifecycle. Denial/lock/restart lifecycle and native-shell evidence remain outstanding.
- **Partial:** B2.3 settings WebUI exists and was manually replayed with synthetic credentials, including the user-provided exact callback URI in Fake mode. A local Fake Feishu authorize/disconnect/reload replay was recorded in `docs/quality/reports/evidence/2026-10-10-stage-b-browser/replay.md`. Archived screenshot, full console/network capture and native-shell replay are missing.
- **Partial:** B3.1 has offline coverage for refresh-before-expiry, rotation to the newest refresh token, refresh failure and logout, plus a tested durable Keychain storage component. The real OAuth provider and concrete token HTTP adapter remain unimplemented; storage is not service-wired. Official LarkSuite SDK source confirms the v2 token path `/open-apis/authen/v2/oauth/token`, JSON request fields, and token response fields. Endpoint scope/expiry and revoke semantics remain unresolved; no Feishu request has been made.
- **Partial:** B4.1/B4.3 direct model adapters are stub-tested and wired to explicit intake/journal-assist, index execute, and query operations. Real-model indexing requires explicit manual execution; provider change fingerprint checks prevent stale plans. B4.2 atomic SQLite generation switching and failed-model-change preservation are implemented and covered offline; live dimension validation and durable live-path evidence remain outstanding.
- **Not ready for fixed-SHA QA:** B5 and B6 remain open. This checkout is a dirty development candidate; independent QA and main integration have not started.
- **Not started:** The narrow OAuth / synthetic-model smoke is newly authorized but has not been executed; no real provider request or account access has occurred. Broader C0–C4 work (business data reads, model use on real content, task writes) remains outside authorization.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Feishu task all-day timestamp or result lookup cannot be proven | Duplicate/misdated real tasks | Keep affected writes disabled; retain unknown and no-resend semantics. |
| Keychain prompts or rejects access in dev/browser contexts | Secret persistence unavailable | Fail closed; distinguish native shell from browser path; no file/memory fallback in real mode. |
| Provider account does not support configured model/region/dimensions | Cost or unusable calls | Keep model IDs, endpoint and dimensions configurable; verify account support before C calls. |
| Scope expands into M3–M5 | Large, unreviewable candidate | Keep conversations/roles/memory, DMG, five-day and dual-machine work explicitly out of B/C. |

## Open questions

- Whether official Feishu documentation establishes a safe task result lookup, precise endpoint-level scope mapping, and exact all-day due-date semantics; if not, task writes stay disabled. User is an app administrator and can grant scopes once the concrete endpoint requirements are established.
- User's Aliyun key and account-specific host are intentionally kept local and were not entered in chat or source. Embedding dimension still requires account/runtime validation before any real index build.
