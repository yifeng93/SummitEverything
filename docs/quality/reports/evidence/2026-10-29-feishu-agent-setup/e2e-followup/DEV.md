# Feishu setup E2E follow-up

- Branch: `codex/mcp-workbench-prototype-20261023`
- Base: `7d9dcc4b73663ca2d414b286f22d1dbd4b2bf288`
- Commit: `666621d5315b2194e79bd274935dba81dc29c0fd` (`修正飞书助手接入入口测试断言`)
- Commit scope: only `web/e2e/first-use.spec.ts`, `SettingsView.cards.test.tsx`, and `FirstUseWizard.test.tsx`.
- Startup staged index was empty (`baseline/index.patch` is 0 bytes); the real index was refreshed to the new HEAD and is clean. Existing dirty product/docs/UI files were not staged or committed.

## Changes

- The existing first-use E2E keeps its workspace, step-resume, completion, and reload assertions. Its final Settings Feishu action now grants clipboard permissions, checks copy feedback, confirms there is no wizard/dialog, checks that the API call count did not change, reads the clipboard, and validates the app origin and self-contained prompt markers. The origin is derived from the Playwright `baseURL`, so the tracked test supports the default and isolated ports.
- Updated stale Settings card and `FirstUseWizard` test expectations from the former wizard-opening action to the copy behavior. The standalone wizard step 4 tests remain unchanged.

## Checks

| Check | Result | Evidence |
|---|---:|---|
| Task patch apply-check against base | exit 0 | `task.patch` |
| Targeted component tests: Settings cards, FirstUseWizard, FeishuAgentSetup, TodayView, Settings regressions; one worker | Vitest reported 57 passed, 2 tests timed out at the existing 5 second limit; command exit 1 | `logs/component-tests-rerun.log` |
| TypeScript typecheck | exit 0 | `logs/typecheck-rerun.log` |
| oxlint | exit 0 | `logs/lint-rerun.log` |
| Existing full first-use E2E in the current dirty UI tree | FAIL before the target copy section: its preserved first-step text assertion expected “首次配置 · 第 1 步，共 5 步”, while the current page showed “新建工作库” | `logs/e2e.log` |
| Existing full first-use E2E in an isolated archive of base `7d9dcc4` with the updated test | NOT_PASS: reached the pre-existing `page.reload()` step, then hit Playwright's unchanged 30 second test timeout waiting for navigation to load. The clipboard target section was NOT_RUN. No timeout or assertion was relaxed. | `logs/standalone-e2e.log` |

Ports 5189 was already occupied and was left untouched. E2E attempts used isolated port 5285 and synthetic route fixtures; no real account, credentials, external provider, or real workspace data was used. The temporary Playwright config was removed. The parent task reported a separate browser copy/fallback observation against its current combined UI; that is not evidence for this fixed source SHA. Independent QA remains pending.
