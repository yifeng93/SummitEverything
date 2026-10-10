# Stage B / C Checklist

## Phase 1: Protocol and contract freeze
- [ ] B1.1 Partial: protocol matrix covers model mappings and Feishu unknowns; official SDK source pins OAuth token path/request/response, while data endpoint scope and semantics remain unresolved
- [x] B1.2 Typed provider/settings/credential contracts and ADR/API docs (DEV implementation; review pending)
- [x] B1.3 User supplied callback, account/model endpoint details and confirmed admin ability to grant additional scopes

## Phase 2: Local configuration and credentials
- [x] B2.1 Persisted non-secret settings; Fake/offline default (DEV implementation; independent review pending)
- [ ] B2.2 Partial: fail-closed Keychain adapter and browser synthetic save/delete; offline-tested Feishu token/app-secret store is not service-wired. Denial/lock/restart and native-shell evidence remain
- [ ] B2.3 Partial: settings UI and synthetic browser replay done; smoke controls visibly disabled without credentials; archived screenshot/network evidence and candidate native-shell replay remain

## Phase 3: Feishu adapter
- [ ] B3.1 Partial: offline Fake refresh-before-expiry, rotation, failure and logout are covered; standalone token storage is not wired. Real OAuth adapter absent; callback access-log query redaction is unit-tested
- [ ] B3.2 Not implemented: offline DTO/fakes can proceed; endpoint-level scopes, content endpoint and calendar time semantics remain unverified
- [ ] B3.3 Not implemented: task writes remain disabled pending date mapping and independently verifiable result semantics

## Phase 4: Model and retrieval adapters
- [ ] B4.1 Partial: structured adapter wired to explicit operations; business calls are disabled server-side. Separate one-use synthetic smoke only; cancellation/stale/injection offline coverage and live-call lifecycle remain
- [x] B4.2 Atomic SQLite generation switching and failed-model-change preservation are covered offline; live dimension validation remains
- [x] B4.3 Stub-tested rerank adapter with bounded HTTP and result validation (DEV implementation; review pending)

## Phase 5: DEV evidence
- [x] B5.1 Full offline checks (DEV candidate)
- [ ] B5.2 Partial: synthetic browser workspace/settings smoke-controls replay done; screenshot archive and full network evidence missing. Native candidate NOT_RUN (window loaded a different QA worktree)
- [ ] B5.3 Independent code review
- [ ] B5.4 Source SHA `7dc7114595704f34ba386c96324dffa77d529ba4` fixed; independent formal QA pending because Feishu B implementation/protocol gates remain incomplete

## Phase 6: Independent QA and integration
- [ ] B6.1 Independent fixed-SHA QA (pending B implementation completion; no result claimed)
- [ ] B6.2 Defect repair and fresh-SHA retest, if needed
- [ ] B6.3 PR, main merge, tree/manifest verification

## Phase 7: Stage C
- [ ] C0 Limited OAuth / synthetic model smoke pre-authorized but NOT_RUN (zero counts); business operations excluded
- [ ] C1 Approved OAuth and read-only flows
- [ ] C2 Approved bounded model quality flows
- [ ] C3 Approved isolated task writes
- [ ] C4 Re-enter B QA for any Stage C code fix

## Current status (2026-10-10)

- User authorized a narrow smoke-test batch: Feishu OAuth connection/code exchange, at most one token refresh if needed, and at most one synthetic request each for DeepSeek chat, Model Studio embedding and rerank. The current prompt proposes CNY 5 as a conservative operating cap (not user-specified); check official pricing first and ask only if that cap cannot bound spend. API keys must be entered through local secure settings/Keychain. This excludes business materials, Feishu calendar/task/material reads, real-content model prompts and every task write.
- B1.1 partial, B1.2 implemented in DEV: matrix and typed settings exist; OAuth endpoint/identity/authorize parameters and Feishu data endpoint details remain unfinished. User is app admin, so scope grant availability is not a blocker. App/provider/configured account labels participate in hashed Keychain item keys.
- B2.1 implemented in DEV: atomic profile settings, strict allowlist validation, Fake default. B2.2/B2.3 partial: macOS Keychain backend and settings page exist; synthetic browser save/delete and Fake Feishu authorize/logout/reload replays are documented. Native shell, deny/lock/restart, archived screenshots and full browser DevTools evidence are missing.
- B3 partial: Fake token refresh/rotation and logout work through service/API/UI tests. A durable token store passes offline tests but is not service-wired; actual OAuth and data endpoints remain unavailable pending implementation and evidence.
- B4 partial: stub-tested adapters are wired to explicit model call paths; atomic SQLite generation replacement and failed model-change preservation are covered offline. Live dimension behavior and full failure/cancellation lifecycle coverage remain open.
- B5 offline checks pass on source SHA `7dc7114595704f34ba386c96324dffa77d529ba4`; browser replay only establishes synthetic UI state and is not fully archived. Native candidate evidence, independent review/QA and integration are pending; Stage B is incomplete. C remains NOT_RUN; no real provider requests were made.
