# Independent QA: query provider configuration guard

- Fixed source SHA: `2e85af7ef580246b10d7d359849f2584a2bad0bb`
- Synthetic parent baseline: `f39c15b4f1a691757c92c214bf11eb11f5b9ce39`
- Checkout: `/Users/hanwenbo/.codex/worktrees/summit-ask-provider-config-qa-20261029/SummitEverything` (detached at the fixed SHA)
- Report scope: query provider preflight, settings status, server 409 mapping, query stream termination and index status UX. This is not full product/C01–C31 acceptance.
- Runtime model metadata: **UNVERIFIED**.

## Isolation

Environment: Python 3.13.2 and Node 24.12.0. All UI replay used headless Chromium against the detached checkout's Vite server on `127.0.0.1:5191`. Every `/api/v1` request was handled by a synthetic Playwright route; non-local network requests were aborted. Synthetic-only settings and API responses were used. No real profile, existing 5173 service, Keychain, paid model, Feishu API, or installed app was read or called. The harness records console responses from unrelated, unmatched background API requests as `OBSERVED`; those routes returned synthetic 500s and are outside this ask/settings scope. The browser run validates rendered frontend behavior; the actual settings API 409 guard was independently exercised with FastAPI tests below.

## Results

| Case | Result | Evidence |
|---|---|---|
| Real mode with Fake/disabled model selections | **PASS**: shows specific missing-configuration guidance, keeps the question, sends no plan or query, and shows neither “连接中断” nor “没有找到可引用的依据”. | `real-preflight-missing.png`; `browser-results.json` (`Q1-*`) |
| Keychain reported unavailable | **PASS**: local preflight blocks plan/query; Settings explains that secret saving fails closed. | `keychain-unavailable-settings.png`; `browser-results.json` (`Q1-keychain-*`) |
| Settings round trip | **PASS**: edited all three model selections and submitted synthetic sentinel credentials through intercepted local routes; returning to Ask retained the question. Status wording describes incomplete setup and per-call confirmation. | `settings-saved.png`; `browser-results.json` (`Q1-return-*`, `Q6-*`) |
| Fully configured Real preview → confirm → query | **PASS**: a plan marked `available=false` / `acceptance_plan_required` still rendered the preview; explicit confirmation sent exactly one query. | `real-query-preview.png`; `browser-results.json` (`Q2-*`) |
| Completed answer followed by history read failure | **PASS**: completed answer remained completed and visible; history failure did not replace it with an interruption. | `completed-history-read-failed.png`; `browser-results.json` (`Q4-completed-history-fail`) |
| SSE ends without a terminal event | **PASS**: actual partial text remained, interruption was stated, and the query was not replayed. | `truncated-query-partial.png`; `browser-results.json` (`Q4-truncated-no-replay`) |
| Provider configuration changes at preview / query gate | **PASS**: both synthetic 409 responses were shown as recoverable errors; no false disconnect and no automatic query replay. | `query-config-race-409.png`; `browser-results.json` (`Q3-*`) |
| Index state loading / failure / retry | **PASS**: a deferred API response showed loading without “未建立”; a synthetic read error showed “读取失败”; explicit retry reached ready. | `index-loading.png`, `index-read-failed.png`; `browser-results.json` (`Q5-*`) |
| Fake query path | **PASS** in the AskView component suite: the no-Real-mode first-conversation and continuation case sends query requests without a Real acceptance plan. This was component-level, not a separate browser case. | `vitest-targeted.log`, AskView test “creates a first conversation on the server, adopts its ID, then continues it” |

## Commands and exit codes

Executed from the detached checkout, reusing the pre-existing repository `.venv` and `web/node_modules` read-only (a symlink was placed in the QA checkout; no dependency installation or lock changes):

| Command | Exit | Result |
|---|---:|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" /Users/hanwenbo/ai/SummitEverything/.venv/bin/python -m pytest -q tests/integration/test_provider_settings_api.py` | 0 | 12 passed; one Starlette/httpx deprecation warning |
| `npm --prefix web test -- --run src/components/AskView.test.tsx src/components/SettingsView.cards.test.tsx` | 0 | 38 passed |
| `npm --prefix web run typecheck` | 0 | TypeScript check passed |
| `/Users/hanwenbo/ai/SummitEverything/.venv/bin/ruff check src/summit_everything/api/app.py tests/integration/test_provider_settings_api.py` | 0 | Ruff passed |
| `node .local/qa/ask-query-provider-config-20261029/chromium-acceptance.mjs` | 0 | Chromium synthetic-route scenarios above passed; detailed results in `browser-results.json` |
| `npm --prefix web test -- --run src/ui-contract.test.ts src/ui-contract.render.test.tsx` | 1 | 18 passed, 3 failed out of 21 |
| Same UI-contract command on an archive checkout of `f39c15b4f1a691757c92c214bf11eb11f5b9ce39` | 1 | Same 18 passed / 3 failed |

The three UI-contract failures are baseline failures, not introduced by this patch: `ProjectsView.tsx` has two excess `content_sha256` / `page_id` occurrences versus its allowlist; the project-status fixture expects “在推进” but gets “暂不可用”; and the project-reading fixture cannot find the “中文事实页面” button. The changed-file diff does not include `ProjectsView.tsx`, `web/src/ui-contract.allowlist.json`, or `web/src/ui-contract.render.test.tsx`. Target and baseline full logs are `ui-contract.log` and `ui-contract-baseline.log`; no guard was edited or waived.

## Bug replay and boundaries

The reported symptom was replayed with synthetic Real-mode settings that had Fake/disabled model capability states. On the fixed SHA, the UI now presents configuration guidance before plan/query submission, retains the question, and does not label the state as connection interruption or unsupported evidence. This confirms the corrected UI path under intercepted responses; it does not establish real provider availability or quality.

Real model calls, real Keychain behavior, the real development profile and its index, runtime model metadata, real query quality, Feishu, installed app/DMG, and release gates are **NOT_RUN** (runtime metadata is **UNVERIFIED**). No product source or tracked test was changed in this QA checkout.

## Evidence files

- `browser-results.json` — final machine-readable per-case result and screenshot list
- `chromium-acceptance.log` — successful final run output and exit 0
- `pytest-provider.log`, `vitest-targeted.log`, `typecheck.log`, `ruff.log`
- `ui-contract.log`, `ui-contract-baseline.log`
- `*.png` — original Chromium screenshots
- `chromium-acceptance.mjs` — QA-only synthetic route harness

The earlier `.partial.json` records contain failed harness iterations (including an initial short-delay index-loading attempt); they were retained for audit and are superseded by the final `chromium-acceptance.log` and `browser-results.json`.
