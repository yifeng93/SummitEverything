# Independent QA report: external Markdown discovery

- Fixed candidate: `5d76fe20b0300fb846b6af01475f55f4e75859ab`
- Base: `417117401a0a165b14a67abd1e8b27d1ea76d4ca`
- Checkout: detached `/Users/hanwenbo/.codex/worktrees/qa-external-watch-20261030/SummitEverything`
- Environment: macOS, Python 3.13.2, Node 24.12.0; isolated temporary profile and synthetic workspace. No user workspace or Keychain used.
- Model boundary: cached local BGE `46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59` ran for embedding/retrieval; DeepSeek was replaced by the harness MockTransport. Feishu was not called. Browser made zero external-origin attempts.

## Results

| Case | Result | Evidence |
|---|---|---|
| Python revision contract, reader/cache, lifecycle and qualified retrieval tests | PASS, 65 tests | command in `command-results.md` |
| Frontend App shell, Projects, PageReader and Approval component tests | PASS, 76 tests | command in `command-results.md` |
| External Markdown main browser flow with actual FastAPI, actual workspace files, real BGE and mocked DeepSeek | PASS, 1 test | `logs/playwright-final.log`, `logs/external-watch-flow.json`, `logs/browser-network.json`, screenshots 05, 07 and 08 |
| External edit automatically updates same standalone reader to east/pending without reload or manual refresh | PASS | Screenshot `screenshots/07-external-change-pending.png`; browser test and network trace |
| Page remains read-only in standalone reader | PASS | Browser assertion and pending screenshot |
| Previous confirmation is invalidated before reconfirmation; old indexed chunk is stale and excluded | PASS | `logs/external-watch-flow.json`: `approvalState=invalid`, `current_pages=0`, `stale_pages=1` before confirmation |
| Explicit same-page confirmation with existing first-index gate already established | PASS | Initial index was prepared through the UI confirmation gate; confirmation returned HTTP 200 and `index_update=updated` |
| New version is reindexed and usable, previous citation marked updated, subsequent query returns east | PASS | `logs/external-watch-flow.json`, `logs/provider-evidence-summary.json`; final index `ready`, `current_pages=1`, `stale_pages=0` |
| One transient 503 on the external reader detail fetch | PASS in this standalone reader run | One injected 503; the page showed the new body without user refresh; three matching detail reads were observed (includes the injected request and post-confirm reload). See the caveat below. |
| TypeScript typecheck and production frontend build | PASS | command in `command-results.md` |
| Ruff, mypy, uv lock and changed-file format checks | PASS | command in `command-results.md` |
| Frontend lint | PASS with warnings | exit 0; existing React lint warnings remain in `logs` only as terminal output, not treated as errors |
| UI contract tests | FAIL, 20/21 | `ui-contract.test.ts` reports allowlist/source count mismatches in App, ApprovalView, PageReader and ProjectsView; render guards passed. No allowlist changes made. |

The candidate's UI contract failure is an actionable candidate defect. It must be corrected in its own change and rechecked against a new fixed SHA; this QA checkout did not alter the allowlist or tracked source.

### Transient detail-read probe caveat

The complete real-backend standalone-reader path recovered after one deliberately injected detail `503`; its evidence records three matching reads and the latest Markdown body arrived without a manual retry. Sol's focused simulated browser probe on this candidate separately observed that a one-off detail failure in the project-detail path did not retry successfully. These observations exercise different reader branches; keep the project-detail retry case open for the repair SHA rather than treating the standalone-reader pass as coverage of the overview/project branch.

Sol also separately reproduced a persistent `/pages/revision` error with no visible monitor warning on the reader. The evidence is in the shared main QA directory: `sol-ui-probe.cjs`, `sol-ui-probe.json`, `sol-detail-transient.png`, and `sol-monitor-error.png`. That focused mock probe is a FAIL for the corresponding project-detail recovery and monitor-error visibility cases.

## Not run on this candidate

The successful browser path covers a standalone reader opened from an old citation. It does not close the full checklist. These cases remain for fresh repair-SHA QA:

- Project-inline reader and project overview refresh, including scroll retention and save receipt retention.
- External new-file discovery, deletion/unavailable behavior, invalid UTF-8/YAML correction recovery, and active-page deletion return behavior.
- Draft-review input and journal entry preservation during external discovery.
- Workspace/profile switch isolation and late page/list responses; unchanged-revision transient list failure recovery.
- Metadata-only cost at 150–200 pages; same-size/same-mtime replacement, symlink/outside/temp exclusions and initial-baseline races beyond the focused automated tests.
- Mobile, installed app/DMG, signing, real providers, real Feishu and release gates.

## Isolation and repository state

All harness, logs, and screenshots were written under this checkout's `.local/qa/external-watch-20261030/`. The candidate stayed at the fixed detached HEAD; `git status --short --branch` showed no tracked or untracked product changes after moving one early harness screenshot into the QA evidence directory. No branch/worktree was deleted.
