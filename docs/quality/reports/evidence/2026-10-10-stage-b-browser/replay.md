# Stage B local browser replay — 2026-10-10

## Environment

- Candidate baseline: `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`; working tree was dirty and not fixed for independent QA.
- UI: Vite at `http://127.0.0.1:15180/`; API at `http://127.0.0.1:8765/`.
- Workspace: synthetic, isolated under `/tmp/summiteverything-stage-b-workspace-logout-20261010/`.
- Profile root: isolated under `/tmp/summiteverything-stage-b-ui-logout-20261010/`.
- Credentials/content: none entered; only Fake Feishu OAuth was used. No real Feishu, model, or business material request occurred.

## Replay and observed result

1. Created a new synthetic workspace in the UI — `POST /api/v1/workspaces` returned `201`.
2. Clicked **模拟授权飞书** — `POST /api/v1/integrations/feishu/authorizations` returned `200`; the callback used only the synthetic code `fake-ok` and a generated state.
3. Confirmed the home view showed **已授权** and the **断开飞书授权** control.
4. Clicked **断开飞书授权** — `DELETE /api/v1/integrations/feishu/authorizations` returned `204`.
5. Confirmed the view changed to **未授权** and the protected refresh controls became disabled.
6. Reloaded the page. The UI remained **未授权**; no logout reversion occurred.

## Evidence limits

- The browser accessibility snapshots and server access log observed the state transitions above. The final screenshot was captured in the local CUA session and showed the home view with **未授权**; screenshot bytes were not archived in this evidence directory.
- The server access log showed no outbound provider requests. It included only local workspace/auth/status/list endpoints and the local Fake callback.
- This is a developer UI replay of Fake behavior, not proof of real Feishu OAuth, durable token storage, real browser auth, native app behavior, or independent QA.
