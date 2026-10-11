# Stage B Luna independent UI retest — 576895f

**Result: PASS for the offline browser and native UI scope on exact source SHA `576895f6983ca41cacbbad45a9075b97b9986189`.** This is a fresh detached QA worktree at that commit. It does not modify product source, dependency locks, or commits. The prior `fd2042385c4916598337239f5259b3ef1889372a` FAIL remains a separate historical report and is not overwritten.

## Candidate and environment

- Checkout: `/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-ui-retest-576895f/SummitEverything`, detached at `576895f6983ca41cacbbad45a9075b97b9986189`.
- Independent environment: `uv sync --locked`, `npm ci`, and `swift build` completed successfully; logs are in the evidence directory. The test runner used `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`.
- Browser API/Web ports: 18903 / 15183. Native ordinary runs: 18904 / 15184. Delayed npm: 18905 / 15185. Missing-uv fault: 18906 / 15186. Each used a distinct app profile and custom bundle ID. No native run reused another checkout's app or profile.
- `HEAD` is exactly the tested SHA, and the checkout contains only untracked QA report/evidence artifacts; no product source diff or commit was created.

## Actual browser UI

A new isolated IAB tab loaded `http://127.0.0.1:15183/`. Using only synthetic Fake data, the UI completed workspace creation, line/project creation, Fake Feishu authorization, synthetic material import, draft edit/approval, Fake index plan/confirmation, a citation-backed query, Fake calendar range display (two events for 2026-10-09–10), and an independently confirmed local project-progress action. The workspace manifest shows `progress_version: 1` and the expected synthetic progress.

The settings flow switched to Real using only synthetic non-secret App ID `cli_synthetic_luna_576895f` and loopback callback. No secret was entered. The UI reported missing app secret and unverified identity; Feishu material search/calendar actions and real task creation remained disabled. The local progress action remained available and completed through separate confirmation. Browser API logs show only loopback traffic for the app flow; no OAuth URL was opened, no real Feishu/model call was made, and no real task was written. CUA `Tab.dev.logs({levels:["log","warn","error"]})` returned an empty list after the flow. AX/DOM evidence and provider settings are retained in the evidence directory; this is a browser-console log capture, not a HAR.

## Native macOS shell

The exact checkout binary loaded its WebUI in the ordinary cold run and the hot restart. Both API health responses were 200 and both Web responses were 200 at the exact configured root URL ending in `/`. The cold API run ID was `782254AC-2F3B-45B2-BFC5-5C0F54AE53E2`; the hot run ID was `9015EB8F-5ADE-4553-9142-94417DF3F230`. The actual native window showed the workspace chooser; neither run showed a blank WebView or readiness alert.

With a shim that delayed `npm` for exactly five seconds, after the exact five-second npm delay, both services returned 200; the saved probe began immediately after the shim completed, so it records the successful state rather than the earlier API-only interval. Health run ID `C81110EC-B6CC-49AC-A327-7EC3EC5A4CDC` matched the child `SUMMIT_RUN_ID`; the native WKWebView subsequently loaded the chooser at `http://127.0.0.1:15185/` without restart, blank view, or alert. The shim timestamps and availability polling are in the evidence directory. Initial CUA binding timed out while a separate cold app was still open; after that app was quit and its ports closed, CUA bound the exact delay bundle and exposed its window. The timeout and resolution are retained in `native-ui-observations.txt`.

The native UI opened the synthetic browser-created workspace and saved only a synthetic App ID and loopback callback. It displayed “钥匙串不可用” and “真实模式保存会失败关闭”; no secret was entered or stored. On the Today view, status showed no app secret and identity unverified, material search/calendar refresh and real Feishu task creation disabled, and local project progress independently available. The actual native AX observations are retained in the evidence directory.

A fourth unique native wrapper intentionally omitted `uv` and Node.js from PATH. The actual UI showed the expected “本地服务未就绪” alert with installation guidance. After dismissing it, the app exited and its ports remained closed.

## Cleanup and boundaries

After closing the native windows and IAB test tab, checks found no listeners or owned processes on ports 18903/15183, 18904/15184, 18905/15185, or 18906/15186. Existing services belonging to other worktrees were left untouched. Browser profile/workspace contents are synthetic and stay in this QA checkout's ignored `.local` directory; only safe settings/log/manifest/DOM evidence is copied to the report evidence directory.

No real OAuth, account identity, Feishu materials/calendar/tasks, model provider, API key, OS Keychain, DMG, or external browser authorization was tested. UI credential failure was checked with synthetic configuration and missing-secret state; the detailed provider credential fault matrix is covered by the candidate's separate backend test run (25 cases), not re-run through the actual UI. OS Keychain remains **NOT_RUN**. Full DEV suite counts (388 backend / 45 Web) are recorded by the implementation handoff and were not repeated by this UI-only independent pass; this worktree independently repeated environment setup and Swift build, then exercised the browser/native paths described above. The previous fd204 URL normalization failure is closed only for this fixed SHA because the root-path response is now observed loading in the native WKWebView.

## Evidence

Evidence directory: `docs/quality/reports/evidence/2026-10-11-stage-b-luna-ui-retest-576895f/`. It includes the browser DOM snapshot and console result, browser API access log, native UI observations, native API/Web readiness timeline, five-second npm shim log, synthetic provider settings, workspace manifest, setup/build logs, and a SHA-256 manifest. CUA screenshots were displayed inline during the test, but the exposed screenshot API returned bytes with no documented filesystem export method; no screenshot file is claimed in this archive.
