# Offline ask flow DEV handoff

- Branch: `codex/offline-ask-schema-20261029`
- Base: supplemental interface-contract commit `e92682122790003992818f952e048e79853b01f5` (it descends from product-spec baseline `62f42818db7e927f272e0a3cc70af6986f6e39d6`)
- Fixed source SHA: `b737a4c1a2c14c6641347353414f1a0cf7631e6f`
- Commit: `b737a4c 修复离线问答 schema 与索引门禁`
- Worktree: `/Users/hanwenbo/.codex/worktrees/offline-ask-schema/SummitEverything`
- Working tree clean after commit. No remote push performed.
- Source import evidence: `uv run python` resolved `summit_everything.api.app` and `summit_everything.integrations.llm` from this worktree's `src/summit_everything`; `PYTHONPATH` was unset.
- Task-only patch from base: `task-only.patch` (binary-capable `git diff e926821 b737a4c`).

## Changes

- Clarified the organizer JSON-output prompt with the complete typed shape while retaining strict schema parsing/validation.
- Added safe schema diagnostics that whitelist known field names and integer indexes, redact unknown keys, and bound output size; raw model values are not surfaced.
- Added 18 captured successful organize responses as a local replay fixture and schema regressions covering valid output, malformed output, source preservation, and explicit reprocess behavior.
- Added/retained regression coverage for settings migration into Ask Preferences, source-organizer copy, and scoped UI-contract allowlist movement.
- Added server-side Real query checks before acceptance-plan creation/reservation and before query dispatch. They require an active index fingerprint matching current embedding settings and request scope; same-fingerprint partial content staleness remains eligible for query with per-page qualification checks.
- Added AskView recovery behavior that keeps the question and directs the user to Approval on `index_not_ready`; each new ask clears the prior Approval CTA. The retry-preview regression checks the CTA no longer sticks.
- Synchronized frontend tri-state and API contract wording. Preserved the rule that users explicitly rebuild from confirmed Markdown through an initial index plan.
- Added a structurally valid empty synthetic LanceDB generation to the pre-existing query-plan test, avoiding a bypass of the new index gate and avoiding any provider call.

## Verification

- Initial full backend run recorded at `backend-full.log`: `791 passed, 3 failed`. The failures were the query-plan fixture plus two deadline tests that exceeded their unchanged timing bounds under the concurrent run.
- Both timing failures were rerun independently with original parameters: `test_r4_02_deadline_cases_hold_over_ten_consecutive_runs[0.15-cfg1-False]` passed (`1 passed`, 4.18s); `test_tls_handshake_timeout_closes_the_connection_before_return` passed (`1 passed`, 0.47s). No tolerance or deadline was changed.
- After the synthetic active-index fixture: serialized full backend suite `794 passed, 1 warning` in 170.23s. Output: `backend-full-after.log`.
- Related backend files rerun after final formatting: `116 passed, 1 warning` in 15.26s.
- AskView focused Vitest: `22 passed`.
- `npm run typecheck`: passed.
- `npm run build`: passed; Vite emitted the existing >500 kB JS chunk size advisory.
- `npm run lint`: exit 0; emitted existing React effect/fast-refresh warnings in unrelated files.
- Ruff check and format check for changed Python files: passed.
- `git diff --check`: passed.
- No paid/model calls, no real credentials, no Keychain writes, and no real workspace content were used.

## QA handoff

Run independent black-box QA against fixed SHA `b737a4c1a2c14c6641347353414f1a0cf7631e6f`; use a separate checkout. Do not use live credentials or paid providers. Focus on organizer schema replay + sanitized diagnostics/source preservation, Fake-index to Real query blocking before plan/reservation, AskView question retention and CTA reset, and same-fingerprint partial-staleness behavior. Keep full frontend 289/289 from the same base as the existing root evidence; focused AskView result above covers this task's final UI change.

## Operational incident note

During an early process inventory, an unrelated oversized process command line was emitted in tool output and included credential-like argv values. No values were copied into this report, source, tests, or patch. The root executor was notified to handle it as a potential exposure event.
