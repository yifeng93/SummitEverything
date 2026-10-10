# Stage B partial DEV report — 2026-10-10

## Scope and fixed source

- Worktree: `/Users/yifengstudio/.codex/worktrees/stage-b-real-providers/SummitEverything`
- Branch: `codex/stage-b-real-providers`
- HEAD / starting baseline: `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`
- Candidate: **not fixed**. The worktree is dirty and has no implementation commit or QA SHA.
- Shared `main` checkout: untouched.
- Materials and credentials: synthetic only. No real Feishu, model, business-material or task request was made.
- User-provided provisioning context: the user is an administrator of the custom Feishu app and can grant further scopes. They provided tenant/user scope inventories, a registered loopback callback, and account-specific Model Studio endpoints. No values from that message are copied into source control except non-secret protocol notes; masked secrets were not available and no real provider request was made.
- Additional smoke authorization (2026-10-10): the user is willing to enter API keys through local secure settings and authorized a limited Feishu OAuth connection (one code exchange; at most one refresh) plus at most one synthetic request each to DeepSeek chat, Model Studio embedding and rerank. This authorization is recorded for future execution only; no such request has occurred. The handoff proposes CNY 5 as a conservative operating cap, not a user-selected budget; current official pricing must be checked before any paid call. It excludes business-material / calendar / task reads, real-content model prompts and all task writes.

This is a partial implementation and developer self-check report. It is not an independent review, fixed-SHA QA, Stage B exit report, or external-service result.

## Implementation recorded

- Added typed local provider settings, atomic profile-local updates, strict field/model allowlists, Fake/offline defaults, and status APIs that do not connect to providers.
- Added a fail-closed macOS Keychain backend and a test-only memory backend. Provider secrets are keyed by profile namespace, provider, and a SHA-256 digest of the selected account label / Feishu app ID. Also added a standalone `KeychainCredentialStore` that stores Feishu user token pairs and app secret as separate items; five offline tests cover restart, rotation, logout, profile/App ID isolation, identity mismatch and sanitized corrupt data. It is not yet wired to the Feishu API lifecycle. Denial/lock/restart coverage and native-shell evidence remain open, so B02 is still partial.
- Added a settings page for local settings and secret entry/deletion. One isolated browser replay saved and removed a synthetic DeepSeek credential using the app API and macOS Keychain. A later replay saved synthetic Model Studio endpoints and callback configuration in a temporary profile; no secret was entered in that later replay.
- Added Fake-only user-token lifecycle handling: refresh an expiring user token before a protected operation, validate that the refreshed token remains valid and retains the required scope, save the rotated refresh token, and clear the user authorization on logout. No refresh call or token was persisted outside the process-only Fake store.
- Added direct stub-tested DeepSeek JSON chat, Model Studio embedding and rerank adapters, plus operation-scoped runtime wiring for explicit intake, index and query actions. Settings reads/saves do not instantiate a remote provider; approval-triggered automatic indexing is deferred for real embedding and index/query fingerprints are checked against current configuration. No provider request was made.
- Model Studio supports HTTPS Alibaba Cloud hosts, compatible-mode embedding and `/api/v1` rerank paths. The user supplied account-specific Beijing endpoints; they remain local settings and were not copied into source control. Live account behavior remains unverified.
- Feishu real OAuth, material, calendar and task adapters are not implemented. Scope availability is not a blocker because the user is an administrator who can grant more scopes. Official LarkSuite SDK source confirms the v2 token path `/open-apis/authen/v2/oauth/token`, JSON request fields for code/refresh grants, and token response fields. Official Feishu token docs still do not expose readable endpoint-level scope/expiry and revoke semantics through this review path. The SDK review also does not establish data endpoint scope mapping, calendar interval semantics, or task date clearing and safe lost-write reconciliation. Real Feishu capabilities remain disabled until the adapters and these behaviors are pinned.

## Offline checks

All commands ran from the candidate worktree on 2026-10-10:

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 190 passed; 1 existing Starlette/httpx TestClient deprecation warning |
| `uv run ruff check src tests` | PASS |
| `uv run ruff format --check src tests` | PASS — 48 files formatted |
| `uv run mypy src` | PASS — 32 source files |
| `uv lock --check` | PASS |
| `uv build` | PASS — sdist and wheel |
| `npm run api:types` | PASS — OpenAPI and generated TypeScript types refreshed |
| `npm test -- --run` | PASS — 9 files, 36 tests |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS exit; 3 existing `react(set-state-in-effect)` warnings in AskView, TodayView and ProjectsView |
| `npm run build` | PASS |
| `swift build` | PASS |
| `git diff --check` | PASS |

The test suite and HTTP fixtures are offline. These results prove only the current candidate's self-check; they do not prove account access, provider compatibility, model quality, charges, or Stage B acceptance.

## Manual UI and evidence limits

- Settings UI was opened in the isolated in-app browser with a synthetic workspace and synthetic Keychain item; save and delete completed. A later run saved synthetic account-specific Model Studio endpoints and the user-provided callback shape in a temporary profile, then completed Fake authorization through `http://localhost:8765/callback`.
- CUA console observation returned zero error/warn entries for that replay. No durable console capture, HAR, request/response archive, executed harness bytes, screenshot bundle or evidence manifest was produced. Do not treat this as a replayable console/evidence package.
- The native development-shell settings path, Keychain denial/lock/restart behavior, Feishu user-token logout, real Keychain multi-account isolation, and app-signing Keychain behavior remain NOT_RUN. Account-key hashing is covered only by the injected-memory unit/API tests.
- The Mac was locked during native-app inspection. No user-owned Keychain item was read or changed.
- A second local browser replay exercised Fake Feishu authorization, the disconnect action, and reload persistence in a fresh isolated profile/workspace. The local access log records the authorization POST (200), synthetic callback (200), and disconnect DELETE (204); the visible UI returned to **未授权** and stayed there after reload. The screenshot was captured in the CUA session but was not archived. Replay details and evidence limits are recorded in `docs/quality/reports/evidence/2026-10-10-stage-b-browser/replay.md`.

## B gate status

- B01: **partial**. Model source mappings are recorded in `docs/architecture/PROVIDER-PROTOCOL-MATRIX.md`; Feishu token and endpoint-specific details remain unresolved. Scope availability is not a blocker; user is the custom-app administrator and can grant required scopes once exact endpoint needs are established.
- B02: **partial**. Settings and browser Keychain save/delete exist; the Feishu token/app-secret store passes five isolated offline tests but is not service-wired. Native/lifecycle evidence, signed-app identity and actual Keychain isolation remain open.
- B03: **NOT_RUN / not implemented** for real Feishu. Fake refresh-before-expiry, refresh-token rotation, invalid refresh and logout are covered by API/service/UI tests. Durable user-token storage exists as an offline-tested component but is not service-wired; no actual Feishu endpoint, material/calendar adapter or task adapter exists. Capability states remain disabled.
- B04: **partial**. Direct model adapters are connected to explicit business call paths and have stub coverage. Embedding batch/index/dimension validation, fingerprint checks, explicit index execution, and atomic SQLite generation switching are covered offline; failed model-change builds preserve the previously active generation. Live account dimension behavior and complete failure/cancellation lifecycle coverage remain open.
- B05: **partial self-check only**. Full offline commands and a documented Fake Feishu WebUI replay pass, but there is no fixed SHA, archived screenshot bundle, native-shell replay, independent review or QA.
- B06: **NOT_RUN**. No PR or source integration.
- C0–C4: **NOT_RUN**. No real provider calls or external actions were authorized or performed.

## Next work

Continue offline Feishu DTO/Fake and callback/token fixtures while endpoint evidence is collected; keep actual Feishu operations disabled. Finish model failure/cancellation lifecycle coverage and live account dimension checks, then repeat offline and UI evidence collection on a complete fixed candidate before independent code review and QA. Do not integrate this partial candidate or claim Stage B completion.

## Historical correction — 2026-10-10 follow-up

The original line above saying “No real provider calls or external actions were authorized or performed” is too broad and conflicts with the earlier authorization note in this same report. Corrected interpretation: broad C0–C4 business operations were not authorized or performed; the user separately authorized only the narrow synthetic smoke listed in the authorization section, and no such smoke request has been made as of this correction. The original observations, FAIL/NOT_RUN results, and report-time evidence remain unchanged.
