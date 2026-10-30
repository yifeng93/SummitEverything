# Command log

All commands ran from the detached candidate worktree unless noted. stdout/stderr and actual process exit codes are retained under `logs/`.

| Command | Exit | Log |
|---|---:|---|
| `uv sync` | 0 | environment setup; isolated `.venv` |
| `npm ci` (cwd `web/`) | 0 | environment setup; isolated `web/node_modules`; npm reported existing engine warnings and one high-severity audit finding |
| `npm test -- --run src/App.shell.test.tsx src/components/ProjectsView.test.tsx src/components/PageReader.test.tsx src/components/ApprovalView.test.tsx src/ui-contract.test.ts src/ui-contract.render.test.tsx` | 0 | `logs/ui-components.log` |
| `npm run typecheck` (cwd `web/`) | 0 | `logs/typecheck.log` |
| `uv run pytest -q tests/contract/test_workspace_api.py tests/integration/test_workspace_mutations.py tests/integration/test_qualified_retrieval.py` | 0 | `logs/backend-revision-reader-retrieval.log` |
| `web/node_modules/.bin/playwright test ...` with `NODE_PATH=web/node_modules`, config `.local/qa/external-watch-20261030/playwright.config.ts` | 0 | `logs/playwright-final.log`; original focused flow |
| Same Playwright command after adding lifecycle steps to the local, untracked harness | 1 | `logs/playwright-lifecycle.log`; harness-only accessible-label assertion error |
| Same Playwright command after correcting the harness assertion | 0 | `logs/playwright-lifecycle-retry.log`; full flow plus lifecycle scenarios |
| `npm test -- --run src/components/JournalDialog.test.tsx src/components/DraftReview.test.tsx` (cwd `web/`) | 0 | `logs/journal-draft-preservation.log` |
| `npm run build` (cwd `web/`) | 0 | `logs/build.log`; existing large-chunk advisory |
| `git diff --check` | 0 | candidate tracked tree clean; all evidence/harness under ignored `.local/qa` |

Initial wrapper without `NODE_PATH` exited 1 because the config module could not resolve `@playwright/test`; retained at `logs/playwright-wrapper.stdout.log` and `logs/playwright-wrapper.exit`.

