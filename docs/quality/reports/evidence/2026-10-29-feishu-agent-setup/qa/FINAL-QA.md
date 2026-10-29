# Final QA: Feishu agent setup prompt

- Fixed source SHA: `666621d5315b2194e79bd274935dba81dc29c0fd`
- Source implementation: `7d9dcc4b73663ca2d414b286f22d1dbd4b2bf288`
- QA workspace: isolated `git archive` of the fixed SHA at `/Users/hanwenbo/.codex/worktrees/summit-feishu-prompt-final-qa`; only `web/` and relevant docs were extracted.
- Dependency source: `web/node_modules` is a read-only-use symlink to `/Users/hanwenbo/ai/SummitEverything/web/node_modules`; it was not modified.

## Results

- PASS — Source review. `FeishuAgentSetup` invokes only Clipboard API; it does not invoke app API, OAuth, or external request code. Both 今日 calendar and 设置 summary render the shared prompt component. The prompt sanitizes to `URL.origin`, so path/query/hash secrets are excluded; it names the MCP/API docs, credential path, supported host discovery, secret redaction, authorization gates, explicit limits, verification gaps, and safe reporting. On clipboard rejection, component renders a read-only full prompt and retry action.
- PASS — Agent prompt component + Settings entry targeted Vitest: 3 passed, 6 skipped, exit code 0. Command: `npm test -- --run src/components/FeishuAgentSetup.test.tsx src/components/SettingsView.regressions.test.tsx -t 'copies a self-contained prompt|offers selectable prompt|copies the agent setup prompt'`.
- PASS — Today entry targeted Vitest: 1 passed, 15 skipped, exit code 0. Command: `npm test -- --run src/components/TodayView.test.tsx -t 'copies an agent setup prompt'`.
- PASS — TypeScript check: `npm run typecheck`, exit code 0.
- NOT RUN — Browser flow could not reach the prompt. An isolated Vite server was started on `127.0.0.1:5297` with synthetic API interception; the incomplete fixture returned the wrong `intents` shape, causing `ApprovalView` to throw (`intents.data?.items.filter` with `items` undefined) and the settings navigation to unmount. The bounded browser attempt was stopped; it did not reach clipboard checks, retry flow, screenshot, or narrow viewport. Vite was stopped (exit 130 from Ctrl-C). This is a harness limitation, not a product pass/fail.
- UNVERIFIED — Runtime metadata/build identity.
- NOT RUN — Real Feishu authorization, Keychain, model calls, and external service checks.

## Evidence

- Vitest outputs were captured in the execution turn; exit codes above are from completed commands.
- Browser harness source: `.local/qa/e2e-check.mjs`; it failed before the requested prompt interaction. No screenshot was produced.
