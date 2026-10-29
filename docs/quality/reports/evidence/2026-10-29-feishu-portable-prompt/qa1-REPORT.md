# QA report: Feishu portable setup prompt

- Fixed source SHA: `71c670e48e6556c2c276e057b85c234c337be945`
- Checkout: `/Users/hanwenbo/.codex/worktrees/summit-feishu-portable-prompt-qa/SummitEverything`
- Dependency boundary: `web/node_modules` is a symlink to `/Users/hanwenbo/ai/SummitEverything/web/node_modules`; no dependency install or package change was made.
- Runtime boundary: no Feishu service, credentials, external authorization, task creation, or knowledge confirmation was used.

## Results

| Check | Result | Evidence |
|---|---|---|
| Prompt self-contained across cwd/source availability, runtime-match gating, safe origin handling, 14-tool boundary and authorization rules | PASS | `target-tests.log`, 2 files / 4 tests, exit 0 |
| Requested typecheck | PASS | `typecheck.log`, exit 0 |
| ADR API-origin wording consistent with prompt / product spec / handoff | FAIL | `docs/decisions/0029-feishu-agent-setup-entry.md` says categorically “网页 origin 不是 API origin”; prompt/product spec/handoff say it must not be assumed equivalent and permit verified same-origin API or supported local proxy. |
| Real-browser component clipboard readback | BLOCKED | Clipboard harness reached neither button nor readback. Initial Vite root/import issues were corrected; final attempt still failed before target because the imported React module exposed no named `createElement` export (`inspect.cjs` output). Default 30s click timeout was unchanged. No screenshot was produced. See `clipboard-readback.log`, `inspect.cjs`, and `clipboard-readback.cjs`. |

## Original check output

`target-tests.log` and `typecheck.log` preserve command output and actual exit codes. Browser harness diagnostics are preserved in `clipboard-readback.log` and the Vite server transcript was observed from its terminal output. The failed browser attempt is not a product defect determination.

## Scope note

This QA only assesses fixed SHA `71c670e48e6556c2c276e057b85c234c337be945`. The sole confirmed content defect is the ADR wording inconsistency; the clipboard gate remains blocked by the isolated browser harness/runtime setup.
