# Local Retrieval + DeepSeek Independent QA

## Scope and verdict

- Tested product commit: `a67e12bf580bcf01be611578f1e8c163a66a63f0`
- Base: `b737a4c1a2c14c6641347353414f1a0cf7631e6f`
- Branch: `codex/local-retrieval-deepseek-20261029`
- QA checkout: `/Users/hanwenbo/.codex/worktrees/qa-local-retrieval-20261029/SummitEverything`
- Product HEAD was checked again after testing and remained the fixed SHA. Final `git status --porcelain=v1 --untracked-files=no` was empty. QA harnesses, logs, screenshots, and this report are under ignored `.local/qa/`; no tracked product source or tracked tests were changed.
- Result: the tested local-retrieval and synthetic DeepSeek flow gates below PASS. This is offline/synthetic QA, not real DeepSeek, user credential, real business material, DMG, or release acceptance. No product defect was identified in the exercised gates.

## Gate results

| Gate | Result | Evidence / boundary |
|---|---|---|
| Fixed SHA, isolated checkout, tracked-clean | PASS | Explicit managed worktree at the SHA above; final HEAD unchanged and tracked tree clean. |
| Fake remains usable; legacy DashScope profile remains readable and cannot invoke retired retrieval provider | PASS | Full Python suite, provider settings and Fake regressions. Legacy setup UI explicitly switches to local; synthetic browser verified prior `dashscope: true` remains present and no credential delete/write request is made. |
| Status/prepare lifecycle and missing-model handling | PASS (synthetic) | Full Python suite covers read-only status, explicit prepare, missing model, failure/retry, timeout, existing injected model protection. Browser simulated a failed prepare followed by a successful explicit retry; no paid acceptance plan. Root separately supplied fixed-SHA public download/hash verification evidence; QA did not download the 95 MB model again. |
| Actual local model retrieval, network blocked | PASS (bounded probes) | 7 tests passed with the pinned local model and Python 3.13 environment. Probes cover synonyms in QueryService, contradictory number as counterevidence, cross-project isolation, unrelated question with no citations, tokenizer/source spans through long input tail, long-tail fact retrieval, and approval/index flow. Test network sockets are rejected. This is a small synthetic corpus, not a broad quality claim. |
| Local indexing and query authorization | PASS (synthetic) | HTTP harness checked local indexing with no acceptance plan or remote embedding/rerank, runtime secret reads only for DeepSeek, query plan `request_limit=1`, one mocked answer call, and SSE/citation final hash validation. No real provider request occurred. MCP tool path itself was not exercised (NOT_RUN). |
| Fake64 → local512 explicit generation change | PASS (synthetic) | Migration probe verified stable Fake fingerprint, old generation becomes stale, approval before rebuild remains `manual_required`, wrong-generation request gets `409 index_not_ready`, and only an explicit `model_change` rebuild permits grounded query. No paid plan. |
| Synthetic HTTP organize → approve → local index → query SSE | PASS | Both normal and migration probes passed using an isolated temporary workspace, in-memory credential backend with a DeepSeek-only test override, `MockTransport`, actual pinned local weights, and socket rejection. Normal flow: one indexed page/chunk, exactly two mocked chats (organize + answer), zero socket attempts. Migration flow: two pages/chunks, same two mocked chats, zero socket attempts. Citation page was re-read and matched its current content hash and confirmed state. |
| Browser AskView send-confirm and current citation | PASS (route-mocked UI) | At 1440×900, UI settings were `mode=real`, local model `ready`, DeepSeek configured, `credential_status.dashscope=false`. AskView reached the one-DeepSeek-request confirmation; before confirmation there was no `/queries` POST. After confirmation exactly one POST returned mocked SSE status/citation/delta/completed events. The current citation had `availability=available`; clicking it called page GET with matching `expected_content_sha256` and displayed the matching confirmed page body. No cloud endpoint was reachable from the browser. This browser gate is route-mocked and complements, but does not replace, the actual FastAPI/QueryService HTTP harness above. |
| Browser missing local model / Settings CTA | PASS (route-mocked UI) | Query remained in the input; setup message appeared; Settings action opened Settings without creating plan or query request. |
| Browser Settings prepare failure/retry and explicit legacy migration | PASS (route-mocked UI) | Legacy configuration produced an explicit migration action; resulting settings switched embedding/rerank to local. Synthetic prior DashScope credential state remained true and no delete request was made. First prepare returned synthetic failure, retry returned ready; two prepare requests, zero acceptance-plan requests. |
| Browser approval local index preview/confirm | PASS (route-mocked UI) | One confirmed synthetic page; explicit range preview and user confirmation submitted local index plan/job. Preview estimated cost was zero; no `/acceptance-plans` call. |
| 390 px/mobile layout | NOT_RUN (out of acceptance scope) | Product owner clarified desktop Web is the required surface; acceptance checks used 1440×900. Early exploratory 390 px route-mock runs and screenshots are retained but do not count toward this gate. |
| Runtime model metadata | UNVERIFIED | Runtime status exposed a ready state to the actual HTTP harness; this QA did not independently assert/render all model metadata fields from the real profile/status endpoint. Browser state was mocked. |
| Real DeepSeek, real keychain/credentials, real source materials, DMG/install, public release, five-day/two-machine gates | NOT_RUN | No real DeepSeek/paid call or real credential access was authorized; no user library/config/index/material was modified; no Feishu, DMG, install, or release action was performed. |
| Remaining C01–C31 and unrelated feature gates | NOT_RUN | This report covers only the fixed candidate's local retrieval + DeepSeek scope and the specific regression gates listed in the brief; it is not a full-product acceptance report. |

## Independent commands and exit codes

All commands were run from the QA checkout unless the command includes `--prefix web`. `set -o pipefail` was used for piped checks; raw output is in `.local/qa/logs/`.

| Command | Exit | Result |
|---|---:|---|
| `env -u SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR uv run --offline --frozen --python 3.13 pytest -q` | 0 | 808 passed, 6 skipped (the six explicitly model-enabled tests), one Starlette deprecation warning; `logs/pytest-no-model-rerun.log`. |
| `SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR=/Users/hanwenbo/ai/SummitEverything/.local/qa/local-retrieval-probe/models/46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59 uv run --offline --frozen --python 3.13 pytest -q tests/integration/test_local_retrieval_real_model.py tests/integration/test_real_model_approval_flow.py` | 0 | 7 passed; `logs/pytest-real-local-model.log`. |
| `env -u SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR uv run --offline --frozen --python 3.13 pytest -q tests/integration/test_dev_runner.py` | 0 | 4 passed after frontend dependencies were installed; `logs/pytest-dev-runner-rerun.log`. |
| `SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR=<pinned path> uv run --offline --frozen --python 3.13 python .local/qa/http_flow_probe.py '怎样办理青榆的访客登记？'` | 0 | Normal synthetic HTTP closed loop PASS; `logs/http-flow-natural-question.log`. |
| `SUMMIT_LOCAL_RETRIEVAL_MODEL_DIR=<pinned path> uv run --offline --frozen --python 3.13 python .local/qa/http_flow_probe.py '怎样办理青榆的访客登记？' --migration` | 0 | Fake-to-local migration closed loop PASS; `logs/http-flow-migration-natural-question.log`. |
| `./web/node_modules/.bin/playwright test --config .local/qa/playwright.config.cjs` | 0 | 4 browser route-mock tests passed at desktop size; `logs/playwright-ask.log`; screenshots in `.local/qa/screenshots/`. |
| `npm test -- --maxWorkers=4` (from `web/`) | 0 | 33 files, 295 tests passed; `logs/vitest.log`. |
| `npm --prefix web run typecheck` | 0 | `logs/typecheck.log`. |
| `npm --prefix web run build` | 0 | Production build passed; existing chunk-size advisory (~809 kB JS) retained; `logs/web-build.log`. |
| `npm --prefix web run lint` | 0 | Oxlint exited 0; existing React warnings remain; `logs/lint.log`. |
| `uv run --offline --frozen --python 3.13 ruff check src tests` | 0 | `logs/ruff-src-tests.log`. |
| `uv run --offline --frozen --python 3.13 ruff format --check src tests` | 0 | 114 files already formatted; `logs/ruff-format-src-tests.log`. |
| `uv run --offline --frozen --python 3.13 mypy src` | 0 | 49 source files clean; `logs/mypy.log`. |
| `uv lock --check` | 0 | Lock unchanged; `logs/uv-lock.log`. |
| `git diff --check` | 0 | Clean; `logs/diff-check.log`. |

### Setup chronology and non-product failures

- First full Python run happened before `web/node_modules` existed. It returned 1 with 805 passed, 6 skipped, and 3 `test_dev_runner` failures. The fixed `scripts/run_dev.py` deliberately returns 2 when frontend dependencies are absent. After `npm ci --offline` installed 231 packages in the QA checkout, the targeted runner suite passed 4/4 and full Python rerun passed 808/6 skipped. First and rerun logs: `logs/pytest-no-model.log`, `logs/pytest-dev-runner-rerun.log`, `logs/pytest-no-model-rerun.log`.
- First offline `uv run` could not find the locked ONNX Runtime wheel in the shared cache. The QA venv was seeded from the brief-authorized existing wheelhouse (no network download), then `uv sync --offline --python 3.13` succeeded. No project lockfile or tracked file changed.
- A repository-wide `ruff check` / `ruff format --check` invocation also traversed historical evidence under `docs/quality/reports/evidence/` and failed on pre-existing historical files (1514 lint findings; 168 files flagged for format). The applicable source/test scoped Ruff and formatter checks passed above; no files were changed to silence the broad-scope findings.
- An exploratory invocation passed `--migration` before the positional question, so argparse treated it as the question and correctly returned a no-evidence answer (exit 1 in `logs/http-flow-migration-before-approval.log`). The corrected positional-then-flag invocation passed; no product defect.
- An early browser harness iteration lacked the `/action-intents` mock response and another omitted `X-Conversation-ID`; those fixture issues were corrected. Final browser run is 4/4 PASS (`logs/playwright-ask.log`).

## Visual evidence

- AskView confirmation: `.local/qa/screenshots/ask-confirm-desktop.png`
- Current citation and opened confirmed page body: `.local/qa/screenshots/ask-citation-current-desktop.png`
- Missing model CTA is exercised in the browser test; test evidence is recorded in `logs/playwright-ask.log`.
- Settings explicit migration and prepare fail/ready states: `.local/qa/screenshots/settings-legacy-migration-desktop.png`, `settings-prepare-failure-desktop.png`, `settings-prepare-ready-desktop.png`
- Approval index preview/confirmation and resulting state: `.local/qa/screenshots/approval-index-confirm-desktop.png`, `approval-index-confirmed-desktop.png`

## Owned process cleanup

Playwright's `webServer` runner started and stopped its own Vite process. After the final run, `lsof -nP -iTCP:5174 -sTCP:LISTEN` returned no listener. No API server, real application, or external process was stopped.
