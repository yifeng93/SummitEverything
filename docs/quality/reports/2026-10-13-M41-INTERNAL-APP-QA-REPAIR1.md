# M4.1 Internal App QA — Repair 1

**Result:** applicable offline acceptance passed; `M41-QA-001` is closed on the tested artifact. No product-source defect was found. Sol owns the final gate decision.

## Fixed target and environment

- Source SHA tested: `3f6eaa408a8860ff5a438be8a874a2c3904733e4` (detached checkout; clean at start and after verification except this QA report/evidence).
- Candidate: `SummitEverything Internal fix1 3f6eaa4.app`; embedded source SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4`, `dirty=false`, app version `0.1.0`, build `20261013T060945Z-577f0cc805f2`, frontend SHA `577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`, dependency SHA `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`.
- Host: arm64, macOS 27.0.1 (build 26A434). Intel and macOS 13 were not tested.
- Candidate app tree: 156 files, canonical digest `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb`; main executable SHA-256 `b23fa16046cfe39c1aa8885f08b6bbbfe1b90e0d9744919f91f950e42f60cc64`.
- DMG SHA-256 `554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8`. Mounted read-only; the mounted app had the same 156-file tree digest. `codesign --verify --deep --strict` passed for both app copies; `codesign -dv` showed `Signature=adhoc`. `spctl --assess` returned exit 3 (`rejected`). Developer ID, notarization and Gatekeeper acceptance remain **NOT_RUN**; no Gatekeeper or quarantine setting was changed.
- UI bundle copied under `DARWIN_USER_TEMP_DIR` to `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/m41-qa-repair1.1intRJ/SummitEverything QA.app`; test profile and workspace were isolated below that root. Every controlled valid App launch used an explicit `SUMMIT_INTERNAL_TEST_PROFILE_ROOT` and empty `PATH`. One invalid earlier CUA auto-launch had no test-profile environment and is documented separately under failed attempts. The copied app's lock file was verified in the isolated profile. The main end-to-end run used app PID `89086`; the persisted restart used PID `89313`. No system Python, Node, Docker, real model, Feishu service, Keychain, business source files, or production workspace was used.

## Acceptance results

| Scenario | Result | Observed evidence |
|---|---|---|
| Native TXT/MD upload panel and `M41-QA-001` | **PASS** | Clicked upload in the real packaged WebView; macOS Open panel appeared. Cancel returned to inbox with count unchanged at 0. Selecting synthetic TXT and MD files produced two pending inbox items, not approvals. SHA-256 values matched the fixture bytes (`qa-upload.txt`: `71a37402b1c6146a57023cc11a4843a476c68ac2006634ca30e34e7ed600299c`; `qa-upload.md`: `576debf8ddb3990039507d63efe449d23584e6e14130f5cbbfff831f1adb2190`).
| Explicit organize/approval/index/query loop | **PASS** | Created a synthetic line/project; invoked the explicit Fake organize action; inspected and separately approved both generated drafts; explicitly created the two-page index. Two synthesized questions returned their expected facts and usable citations. A Markdown literal containing `rm -rf /` remained inert source text; this workflow used Fake only and no command/tool provider.
| Workspace directory picker and restart persistence | **PASS** | Native folder picker selected the isolated temporary workspace. After normal app restart, both approved sources remained complete; the index reopened with 2 pages/2 chunks, and the two conversation questions remained in history. No SQLite or diagnostic state appeared in the selected workspace; app/profile state remained in the isolated profile.
| Normal quit lifecycle | **PASS** | Independently observed Cmd+Q, File-menu Quit, and closing the last window. Each ended the observed App/backend and freed loopback port 18793. Commands and UI observations are recorded in the evidence README; no second launch was triggered after expected exit.
| Missing backend UI | **PASS** | In a copied candidate only, moved the embedded backend aside, launched with isolated profile and observed the actual native error alert: “SummitEverything Internal 无法启动 / 内部应用无法启动。请保留这个候选包并联系维护者。” After acknowledging it, shell checks confirmed the owned App PID and port were gone.
| Wrong-identity server / occupied port | **PASS with tool-action limitation** | A QA-owned synthetic server held `127.0.0.1:18793` and returned a deliberately mismatched health identity. The running copied App held its isolated `instance.lock`; the actual window displayed “本地应用服务未就绪…候选包身份或本机端口可能不匹配。” The App did not load the fake server root. The server PID remained alive and bound after the exact App PID was terminated. CUA could not activate the alert's OK action (`procNotFound`/inactive-app error), so the test process was terminated from the shell; this is recorded separately from the observed fail-closed result. Request logs contain health paths only, but requests during an earlier auto-launch overlap cannot all be assigned to one PID.
| Delayed readiness | **PASS** | QA-owned black-box harness ran a copied bundle with a synthetic loopback backend delayed by 4 seconds. Captured request order was `/api/v1/health` then `/`; health matched the build manifest and the app run identity before root was requested. Harness exited 0 and verified listener cleanup. App exit `-15` is the harness's intentional SIGTERM cleanup.
| Parent SIGKILL / pipe EOF cleanup | **PASS** | QA-owned harness observed the matching candidate health identity and backend child PID `90391`, then sent SIGKILL to only its own App PID `90389`. Parent returned `-9`; the child and port 18793 were gone within the bounded wait. Harness exit 0.
| Packaged static-resource tamper | **PASS** | QA harness copied the bundle, altered only copied `web/index.html`, and launched the embedded backend with empty `PATH` and a synthetic token. Backend exited 1 and exposed no readiness listener (`bundle-tamper.log`).
| C24 auth, origins, secret handling and errors | **PASS, offline synthetic route harness** | `test_provider_settings_api.py`, `test_release_app.py`, and `test_http_sse_lifecycle.py`: 16 passed. Route harnesses exercised successful requests with a known synthetic Bearer, missing/invalid auth, disallowed Origin, local credential/settings flows with synthetic in-memory secret backend, keychain-denied failure injection, secret redaction, credential/path non-echo, release-resource identity, and tampered frontend fail-closed. No app-process environment, random session token, real Keychain or account credential was read.
| SSE cancel/disconnect/history | **PASS, real loopback TCP** | `test_live_http_sse_cancel_disconnect_and_reopen` ran Uvicorn on a real 127.0.0.1 socket and used `httpx` streams. It verified cancellation state after reopen, disconnect state `interrupted`, and server shutdown; no automatic query replay was observed in the packaged-app restart workflow.
| Native bridge trust policy | **PASS, unit-level plus trusted UI path** | `swift test --package-path native` executed 3 XCTest cases with 0 failures. Trust policy covers the actual main-frame/WebView/origin/frame URL/page URL and exact loopback port, rejecting wrong port, `localhost`, external origins, credential-bearing URLs, and directories; allowed TXT/MD selection and cancellation were also exercised in the real panel.
| OpenAPI/generated type isolation | **PASS** | Exported OpenAPI and generated TypeScript into `.local/qa/.../typegen`; `diff -u web/src/api/generated.ts <isolated-generated.ts>` returned 0 with no diff. Tracked generated types were not overwritten.
| App/DMG identity and portability | **PASS for this arm64 internal candidate** | Candidate build identity matched the exact tested source SHA and clean flag; empty-PATH app launch/readiness and self-contained embedded backend worked. DMG file SHA, read-only mount, signature integrity and app-tree digest matched the standalone candidate. Developer ID/notarization/Gatekeeper acceptance are **NOT_RUN**.

## Automated checks and actual exit codes

All commands below returned exit 0 unless a limitation is explicitly noted. Complete captured outputs are under [`evidence/2026-10-13-m41-qa-repair1/logs`](evidence/2026-10-13-m41-qa-repair1/README.md).

| Command | Result |
|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q` | 499 passed, 1 Starlette deprecation warning; exit 0. |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q tests/integration/test_provider_settings_api.py tests/integration/test_release_app.py tests/integration/test_http_sse_lifecycle.py` | 16 passed, 1 Starlette deprecation warning; exit 0. |
| `uv run --locked ruff check src tests` | All checks passed; exit 0. |
| `uv run --locked ruff format --check src tests` | 82 files already formatted; exit 0. |
| `uv run --locked mypy src` | 44 source files, no issues; exit 0. |
| `uv lock --check` | Resolved 48 packages; exit 0. |
| `npm ci --prefix web` | Added 126 packages, 0 vulnerabilities; exit 0. |
| `npm --prefix web test` | 12 files / 56 tests passed; exit 0. |
| `npm --prefix web run typecheck` | Exit 0. |
| `npm --prefix web run lint` | Exit 0; two React set-state-in-effect warnings in `TodayView.tsx` and `ProjectsView.tsx`. |
| `npm --prefix web run build` | Vite build succeeded; exit 0. |
| `swift test --package-path native` | XCTest: 3 passed, 0 failures; supplementary Swift Testing runner: 0 tests; exit 0. |
| `uv build` | sdist and wheel built; exit 0. |
| Isolated delayed-readiness, SIGKILL-cleanup and tamper harnesses | Exit 0 for each. |
| DMG SHA/read-only mount/tree digest/`codesign --verify --deep --strict`/detach | Hash, attach, tree, code-signature integrity, and detach exit 0. `spctl --assess` exit 3 (`rejected`); no bypass attempted. |

## Failed setup attempts and tool limitations

- The first wrong-identity listener was launched as a background child of a short-lived shell; the listener stopped with the shell. That attempt is invalid and not counted. A subsequent `getApp` auto-launch used no test-profile environment and created a new synthetic default Internal-profile state. I did not read or change that profile. The later valid run used a persistent listener session and an explicitly configured test profile; a brief overlap means the raw health-request log is not a complete per-PID trace.
- CUA printed `sandbox_extension_issue_file_to_process ... Operation not permitted` around several launches, but exact App PIDs, isolated lock files, readiness, and UI state were independently observed. This line alone was not treated as a product failure. On wrong-identity, CUA's alert acknowledgement returned `procNotFound`; a later key action reported the app inactive. These failures are retained in the raw logs and are why shell cleanup was used.
- A first `npm ci` was run at repository root, which has no root npm workspace; it failed during setup. Correct command `npm ci --prefix web` succeeded. An initial wrapper also used zsh's read-only `status` variable after running the delayed harness; the corrected run used `rc`, exited 0, and produced the recorded PASS output.
- `spctl` rejects the unsigned/notarization-excluded internal package. This QA did not remove quarantine, change Gatekeeper, install the app, or attempt notarization.

## Not run / unverified gates

**NOT_RUN:** installation or replacement in `/Applications`, launch over the existing installed app, Developer ID signing/notarization, Gatekeeper acceptance (`spctl` returned rejected for this ad-hoc signature), Intel/macOS 13, multi-machine, five-day soak, real model/provider credentials, real Keychain, Feishu, business content, production workspaces, Stage C and M4.2. Runtime model and reasoning-effort metadata were not exposed by the app and remain **UNVERIFIED**. No real external service or user data was accessed.

## Evidence and checkout state

Raw command output, QA-owned harnesses, candidate/DMG hashes, and QA observations are recorded in [`evidence/2026-10-13-m41-qa-repair1/README.md`](evidence/2026-10-13-m41-qa-repair1/README.md); the structured command/exit ledger is [`commands-results.json`](evidence/2026-10-13-m41-qa-repair1/commands-results.json). A `SHA256SUMS` file there covers all evidence files except the checksum file itself. Final cleanup check found no QA-owned App process, backend, 18793 listener, or mounted DMG volume. Product source, tracked tests, dependencies, lockfiles, app configuration and snapshots were not changed. At the end of verification, exact tested source SHA remained `3f6eaa408a8860ff5a438be8a874a2c3904733e4`; only this QA report and its evidence were added.
