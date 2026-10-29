# Final QA rerun: Feishu agent setup prompt

This supplements, and preserves, the initial harness-failure record in [FINAL-QA.md](FINAL-QA.md). No product code or tracked test was changed. Target remains fixed source SHA `666621d5315b2194e79bd274935dba81dc29c0fd`.

## Harness repair and evidence

The first harness failure record remains in `FINAL-QA.md`. This one permitted harness-only repair added synthetic responses for `/api/v1/action-intents` (`{items: [], next_cursor: null}`), `/api/v1/integrations/feishu/status`, and `/api/v1/provider-smoke`, then used the verified accessible role locator for 设置 without force. The Playwright timeout remained 7 seconds per locator.

- PASS — Playwright browser run; process exit code 0.
- PASS — Granted browser-context `clipboard-read` and `clipboard-write`; copied prompt read back from clipboard and contained `http://127.0.0.1:5297` and `docs/contracts/MCP-v1.md`, without query/hash secret markers.
- PASS — Clipboard rejection showed full read-only prompt containing `PUT /credentials/{provider}`; retry succeeded.
- PASS — No dialog (`dialogCount: 0`), no application write/OAuth request after copying (`apiAfterCopy: []`), and no external requests (`outsideRequests: []`).
- PASS — Narrow viewport width 390px: scroll width 390px equals client width 390px.
- PASS — Browser console error list empty.
- PASS — Settings route was reached and its settings response was served from synthetic API.

Screenshot: [rerun-settings-feishu-prompt.png](rerun-settings-feishu-prompt.png). Harness: `e2e-check.mjs`.

The isolated Vite server used `127.0.0.1:5297` and was stopped after the run (Ctrl-C exit 130). Runtime metadata remains UNVERIFIED. Real Feishu authorization, Keychain, and model checks remain NOT RUN.
