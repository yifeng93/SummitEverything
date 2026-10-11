# Browser UI observations — fd2042385

Browser: CUA in-app browser, actual WebUI at `http://127.0.0.1:15179/`.
Workspace: `/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-ui/SummitEverything/.local/qa-stage-b-luna-final-ui/workspace`, ID `eaf04b87-309b-4b51-b4ad-116aa103ec5d`.
Profile: `.local/qa-stage-b-luna-final-ui/profile/eaf04b87-309b-4b51-b4ad-116aa103ec5d`.

Observed in UI:

- Created the local library, synthetic line `合成项目线`, and project `离线 UI 验收`.
- Fake Feishu authorization changed to `用户已授权`; materials showed three synthetic rows. Selected and imported only `模拟会议`; UI marked it as source/original and pending, then Fake organization produced a draft. Edited its title, saved, explicitly confirmed it, and saw the intake item become complete.
- First indexing required a visible plan and second confirmation. The index became ready for one page/one chunk. A query returned the approved synthetic sentence and a citation to that page.
- Fake calendar query for `[2026-10-09, 2026-10-10)` in `Asia/Shanghai` displayed the two seeded synthetic events. No real calendar or account was read.
- Settings changed to `Real · 显式启用` and saved a synthetic, non-secret Feishu App ID plus the same-run loopback callback. Saved provider settings show `identity=app`, `real_data_enabled=false`, Fake LLM/embedding/rerank disabled, and no credentials. UI says the OS Keychain is unavailable, app secret is not configured, user identity is unverified, and all provider capabilities are unavailable. No key was entered and no OAuth URL was clicked.
- On Today, Real task creation was disabled with the result-proof gate explanation; local project progress remained enabled. The project progress proposal was reviewed, independently confirmed, and separately executed. The manifest has `progress_version=1`; this was a local write to the isolated synthetic library.

Actual uvicorn access log: 124 API lines, 117 responses 200, 5 responses 201, and 2 initial `GET /api/v1/workspaces/current` 409 responses while no library was open. The log contains request method/path/status only, not a HAR or request-body capture. CUA's exposed `Target` API provided live accessibility DOM but no browser-console accessor in this run; console status is `NOT_CAPTURED`, not asserted as zero.

Visual checks were made directly through CUA during the test. The tool displayed the native blank-window screenshot and the subsequent readiness alert, but did not expose a file-export method; no screenshot file is claimed.
