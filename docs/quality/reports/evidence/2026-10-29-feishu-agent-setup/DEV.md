# Feishu assistant setup entry — DEV handoff

- Branch: `codex/mcp-workbench-prototype-20261023`
- Candidate: `7d9dcc4b73663ca2d414b286f22d1dbd4b2bf288`
- Commit: `将飞书连接入口改为助手自动配置提示词`
- Commit contains only the task patch (13 files). The shared checkout's unrelated dirty UI/API work was not staged or committed.
- Remote status: not pushed. The source branch remains local.
- QA: pending independent review. QA-only combined UI snapshot is owned by the parent task.

## Implementation

Today and Settings share a prompt builder and clipboard component. The prompt uses only the current origin, guides the assistant to inspect MCP/API docs and the local setup runbook, reuse supported settings/credentials safely, and report separate MCP, Feishu authorization, and application-read gates. Clipboard rejection displays selectable prompt text and retry. Manual setup remains in the advanced/compatibility area. Product spec, frontend guide/page specs, ADR 0029, and `docs/handoff/FEISHU-AGENT-SETUP.md` were updated.

## Checks and evidence

| Check | Candidate / input | Result | Log |
|---|---|---:|---|
| `git apply --cached --check` | isolated task patch against starting HEAD | exit 0 | `.local/dev/feishu-agent-setup/task.patch` |
| `git diff --cached --check` | isolated task index | exit 0 | command output |
| Standalone Web typecheck | candidate archive at `standalone-final2` | exit 0 | `standalone-final2-typecheck.log` |
| Standalone retry of previously timed-out tests, `--maxWorkers=1` | Settings prompt-copy and Today nonempty-layout tests | 2 passed, 23 unrelated tests skipped; exit 0 | `standalone-final2-rerun.log` |
| Standalone first targeted run | 3 test files, parallel run | Vitest reported 2 failures due the default 5-second timeout; no assertion failures. The `tee` pipeline returned 0, so this is recorded as a Vitest failure, not a passing check. | `standalone-final-tests.log` |
| Combined targeted tests, `--maxWorkers=1` | shared dirty checkout | 25 passed; command exit 0 | `combined-tests.log` |
| Combined Web typecheck | shared dirty checkout | exit 0 | `combined-typecheck.log` |
| Combined Web lint | shared dirty checkout | exit 0 | `combined-lint.log` |

Initial focused test iteration also exposed and fixed one matcher issue; the first combined typecheck exposed and fixed an unused callback destructuring, and a later Settings test type error was corrected. The final candidate standalone typecheck and the two cases that initially timed out both pass.

The branch index was refreshed with `git read-tree HEAD` after confirming the startup staged-index snapshot was empty (`baseline/index.patch` is 0 bytes). `git diff --cached --exit-code` is clean. Original dirty worktree files remain in place.

## Remaining gates

- Independent QA and broad combined UI regression remain with the parent task.
- Browser review is performed by the parent; it reported the copy action succeeded without opening a dialog.
- No real Feishu connection, credentials, authorization, external request, task write, formal knowledge confirmation, or paid model call was performed here.
