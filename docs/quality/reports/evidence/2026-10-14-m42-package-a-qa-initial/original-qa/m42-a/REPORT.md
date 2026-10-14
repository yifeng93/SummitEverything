# M4.2 Work Package A independent QA report

## Verdict

**FAIL for the tested code SHA** `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`. This is an initial QA result for the offline preparation portion of M4.2 A only; it does not certify the overall M4.2 package or B/C real-service gates.

- **P1 / FAIL — M42-QA-001:** After a confirmed Feishu-read plan has atomically reserved its bounded requests and the app restarts while the operation is unresolved, querying the plan should return HTTP 200 with `state=unknown`, retaining the reservation and never replaying the external action. The independent QA harness observes HTTP 500 instead of 200. The operation retry is rejected (409), and reservation count remains consumed. Evidence: `qa-contract-probe-final.log`, harness `test_package_a_contract_probe.py`; the earlier raw traceback is retained as `qa-contract-probe.log`. Root observed in stack trace: response model validation requires `finished_at` for terminal `unknown`, while GET constructs unknown without it. No product code or tracked tests were changed.
- **P2 / observed Fake-mode quality anomaly:** the native UI flow indexed and cited the correct approved page/version, but exact and synonymous questions failed to retrieve the complete, directly relevant sentence and one answer incorrectly declared supporting evidence missing. See `ui-observations.md`. This is not evidence of real-provider answer quality, nor enough to attribute the problem to Fake adapter vs shared QueryService. Keep as an investigation item; do not suppress or reinterpret it as a pass.

## Fixed target and environment

- Source checkout: `/Users/yifengstudio/.codex/worktrees/m42-package-a-qa/SummitEverything`
- Fixed detached HEAD: `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`; final check confirmed HEAD unchanged and tracked index/worktree diffs empty. QA harness and all QA files are ignored `.local/qa` outputs only.
- Environment: macOS 27.0.1 build 26A434; host Python 3.9.6, uv project environment Python 3.12; Node v24.15.0 / npm 11.12.1; Swift 6.4.
- Candidate app: `/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/final-20261014/artifacts/SummitEverything Internal fe47339.app`.
- Candidate DMG: `/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/final-20261014/artifacts/SummitEverything-Internal-fe47339.dmg`; expected and observed SHA-256 `0b1404971711b0823c2a236882bb619fe891612704bf9d02de32050c03c16f5f`.
- Build metadata matched tested source SHA, `dirty=false`, build ID `20261013T233919Z-2aab5e81a62d`, and frontend digest `2aab5e81a62dbabd517c132014df2cf86f7e157718ed1f2c8f8981ba41f66627`. Read-only DMG mount verified and its 156-file app tree matched source candidate; isolated copy matched as well. `codesign --verify --deep --strict` passed. `spctl --assess` returned rejected / exit 3 for this Internal build; no Gatekeeper bypass, quarantine removal, or system security changes were attempted. This is the observed assessment result, not a claim that LaunchServices blocked launch.
- Guarded native run used a fresh directory under `DARWIN_USER_TEMP_DIR`, `open -n --env SUMMIT_OFFLINE_GUARD_ACTIVE=1 --env SUMMIT_INTERNAL_TEST_PROFILE_ROOT=<fresh root> <isolated candidate>`. Guard/profile verification passed before Fake UI actions and after restart. An initial QA-only checker false result was due to checking backend `SUMMIT_INTERNAL_TEST_PROFILE_ROOT`; actual backend receives `SUMMIT_PROFILE_ROOT`. Original output is retained; corrected checker and successful output are retained. No full process environment or secret was printed.
- QA runtime model/reasoning metadata was not exposed: **UNVERIFIED**.

## Automated checks and raw output

All commands ran in the fixed QA checkout. Exit codes are observed command exit codes.

| Command | Exit | Result / raw evidence |
|---|---:|---|
| `npm --prefix web ci` | 0 | Dependencies installed. No raw log file was retained. |
| `uv sync --locked --group dev --group build` | 0 | Dependencies installed. No raw log file was retained. |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | 508 passed, one Starlette deprecation warning; `pytest.log`. |
| `uv run ruff check src tests` | 0 | `ruff-check.log`. |
| `uv run ruff format --check src tests` | 0 | 86 files formatted; `ruff-format.log`. |
| `uv run mypy src` | 0 | 45 files, no issues; `mypy.log`. |
| `uv lock --check` | 0 | `lock.log`. |
| `uv build` | 0 | Wheel and sdist built; `uv-build.log`. |
| `npm --prefix web test` | 0 | 12 files / 61 tests passed; `web-test.log`. |
| `npm --prefix web run typecheck` | 0 | `web-typecheck.log`. |
| `npm --prefix web run lint` | 0 | `web-lint.log`; two existing `react(set-state-in-effect)` warnings. |
| `npm --prefix web run build` | 0 | `web-build.log`. |
| `swift test --package-path native` | 0 | 3 tests passed; `swift-test.log`. |
| targeted Feishu/model/ledger integrations: `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_real_model_approval_flow.py tests/integration/test_feishu_real_gate.py tests/unit/test_acceptance_plan_ledger.py` | 0 | 13 passed; `targeted-integrations.log`. |
| QA-only positive probes: `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q .local/qa/m42-a/test_package_a_contract_probe.py -k 'not reserved_request_survives_application_restart'` | 0 | 2 passed, 1 deselected; `local-probe-positive.log`. |
| Full independent QA-only contract probe: `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q .local/qa/m42-a/test_package_a_contract_probe.py` | 1 | 2 passed, 1 failed due M42-QA-001; `qa-contract-probe-final.log`. |
| OpenAPI generated-client comparison in QA scratch copy | 0 | Generated file byte-identical to committed `web/src/api/generated.ts`; copy retained under `schema-copy/generated.ts`. |

Candidate integrity evidence is in `candidate-integrity.log`; read-only attach/detach evidence in `dmg-attach-verified.log` / `dmg-detach-verified.log`; code signing, Gatekeeper and DMG validation observations are in candidate integrity log. `native-ui-open.log`, corrected `native-guard-process-check.log` and `native-guard-process-check-restart.log` document the guarded UI lifecycle. Independent synthetic harness and the fixture are in this directory.

## UI and boundaries

The actual native app/WKWebView completed an offline synthetic flow: create isolated workspace/mainline/project, import one synthetic Markdown file with the native picker, explicitly organize, edit the complete draft, save, explicitly confirm, create a Fake local embedding index, ask a factual query, quit, relaunch guarded app, reopen the same workspace, and verify source state, index, query history and citation-version status persisted. Settings before/after restart showed Fake offline; Keychain unavailable; key save/delete disabled; no secret was entered. The detailed transcript, exact UI text, and answer behavior are in `ui-observations.md`.

No Chrome DevTools/network panel was available in this native WKWebView run; no such console/network assertion is claimed. The initial checker false result was QA harness configuration, not product evidence. LaunchServices/open succeeded; candidate process was closed through its own UI and final process listing showed it absent.

## Not run / known limitations

These remain independent gates or known product-scope limits; they were not silently treated as passing:

- B1's four administrative/logistics/venue-and-hotel desktop Markdown files were not opened or searched; real material access was not authorized.
- Real macOS Keychain lifecycle, OAuth, paid model/embedding/rerank requests, real Feishu API, actual user installation, account billing/quality, five working days, two-machine behavior, notarized release and publishing: **NOT_RUN**.
- Runtime model configuration metadata: **UNVERIFIED**. The first DEV bad-launch Keychain query count/profile fallback remains **UNVERIFIED**; it was not converted to zero calls.
- First-version batch file/folder import remains unimplemented (single-file import only); real journal assist has no one-shot plan; real Feishu task writes remain disabled. These are not inferred to pass from this QA run.
- Fake UI answer quality anomaly recorded above. No claim about real-provider model quality.
- Scope is package A offline preparation. This is not an A-wide gate, and not M4.2 overall, B or C acceptance.

## Working tree and next action

Final `git rev-parse HEAD` remained the fixed SHA. `git status --short --branch` showed `## HEAD (no branch)` with no tracked changes; `git diff --exit-code` and `git diff --cached --exit-code` both exited 0. All files in this report's directory are QA-only ignored evidence/harness. Preserve the failing test and expected behavior; Developer should repair M42-QA-001 on a new SHA. A fresh QA instance should retest it and separately triage the Fake-mode answer/evidence mismatch without changing the acceptance standard.
