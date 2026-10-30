# External Markdown repair round 1

- Base candidate: `5d76fe20b0300fb846b6af01475f55f4e75859ab`
- Repair candidate SHA: `4358c7b2b410d8c5bcc6ab4dd7d219ce9d349a25`
- Branch: `codex/external-watch-20261030`
- Worktree after commit: clean
- Repair scope: four findings from the fixed QA candidate plus Sol's overview probe.

## Changes

1. Updated the precise internal identifier/hash allowlist counts and corresponding attributions. No guard was removed or relaxed.
2. Project inline detail reads now use a fresh AbortController and five-second deadline per attempt, up to three bounded automatic retries. Budget is keyed by page ID and content hash, so a new version resets it; a 409 starts a directory refresh automatically and stays within the same budget if the hash does not change. Exhaustion leaves a manual retry/refresh path.
3. Revision monitor failures now show a workspace-level freshness warning in the normal app shell; the warning clears on a successful scan. It does not invent pending content or display internal IDs.
4. Overview refresh keeps a same-page PageReader mounted, marks its content synchronizing while refreshing, and retains the previous snapshot after temporary read errors. This preserves the component's receipt and reader position. ADR 0035 records the bounded retry policy.

## Verification

| Command / probe | Exit | Result |
|---|---:|---|
| `npm test` (web) | 0 | 34 files, 313 tests passed |
| `npx vitest run src/App.shell.test.tsx src/components/ProjectsView.test.tsx src/ui-contract.test.ts` | 0 | 47 tests passed after the final retry-bound change |
| `npm run typecheck` | 0 | Passed |
| `npm run build` | 0 | Passed; existing large-chunk advisory remains |
| `npm run lint` | 0 | Passed with existing warnings |
| `git diff --check` | 0 | Passed |
| Sol project-inline browser probe, adjusted to wait for the recovered east body | 0 | one injected 503; reads 1 → 3; east body recovered without a revision change; monitor 503 warning visible |
| Sol project-overview browser probe | 0 | scroll 2000 → 2019; confirmation receipt visible after refresh; six overview reads observed |

No backend, model, Feishu, Keychain, real workspace, or installation-app action was performed. Independent QA of the repair SHA is still pending; this report is implementation handoff, not acceptance.

## Captured command output

The terminal stdout returned by the recorded command invocations has been copied to `repair1-raw/*.stdout.log`; corresponding process exit codes and exact command strings are in `repair1-raw/exit-codes.txt`. These are captured stdout transcripts from this repair session, not a new test run. The product worktree remains at the same clean SHA.
