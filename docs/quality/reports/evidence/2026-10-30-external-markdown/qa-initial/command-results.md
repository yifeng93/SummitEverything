# Commands and exits

All commands ran from the detached candidate worktree unless the working directory is noted. The independent Playwright command's stdout/stderr is preserved in `logs/playwright-final.log`; its actual exit is in `logs/playwright-final.exit`.

| Command | Work directory | Exit | Result |
|---|---|---:|---|
| `uv sync --locked --group dev` | repository root | 0 | Isolated `.venv` prepared from lock |
| `npm ci` | `web/` | 0 | Dependencies installed in this checkout; Node engine and audit warnings emitted |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/contract/test_workspace_api.py tests/unit/test_page_directory_cache.py tests/integration/test_app_lifecycle.py tests/integration/test_qualified_retrieval.py` | repository root | 0 | 65 passed, 1 deprecation warning |
| `npm test -- --run src/App.shell.test.tsx src/components/ProjectsView.test.tsx src/components/PageReader.test.tsx src/components/ApprovalView.test.tsx` | `web/` | 0 | 4 files, 76 tests passed |
| `npm run typecheck && npm run build` | `web/` | 0 | TypeScript and production Vite build passed |
| `npm test -- --run src/ui-contract.test.ts src/ui-contract.render.test.tsx` | `web/` | 1 | 20 passed, 1 failed; allowlist/source count mismatch |
| `uv run ruff check src/summit_everything/api/app.py src/summit_everything/domain/models.py src/summit_everything/workspace/reader.py tests/contract/test_workspace_api.py tests/unit/test_page_directory_cache.py && uv run mypy src` | repository root | 0 | Ruff clean; mypy clean across 49 source files |
| `uv lock --check && uv run ruff format --check src/summit_everything/api/app.py src/summit_everything/domain/models.py src/summit_everything/workspace/reader.py tests/contract/test_workspace_api.py tests/unit/test_page_directory_cache.py` | repository root | 0 | Lock valid; five files already formatted |
| `npm run lint` | `web/` | 0 | Oxlint completed with existing warnings |
| `web/node_modules/.bin/playwright test .local/qa/external-watch-20261030/external-watch.spec.ts --config .local/qa/external-watch-20261030/playwright.config.ts` | repository root | 0 (final run) | 1 browser test passed; exact output in `logs/playwright-final.log` |

Two early Playwright harness attempts exited 1 before reaching product behavior: the first used an outdated allowed-origin port; the second wrote diagnostics to a non-existent harness output directory. Both were corrected in `.local/qa` and left in the Playwright output artifacts. A later attempt on the initial harness reached an obsolete approval filter; the final flow explicitly selected the first-index UI gate and then followed the real reader route.
