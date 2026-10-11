# Stage B independent offline UI/native QA — fd2042385 (FAIL)

**Fixed source:** `fd2042385c4916598337239f5259b3ef1889372a`  
**Checkout:** `/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-ui/SummitEverything` (detached, outside the implementation checkout)  
**Conclusion:** Browser Fake-only flow and Real task write gate passed in the exercised UI. Native startup failed with a P1 readiness defect. Stage B UI/native QA is **FAIL**; do not merge this SHA.

## Identity and boundary

Read the current README, PROGRESS, PRODUCT-SPEC, ARCHITECTURE, WORKSPACE/API v1 contracts, TESTER, ACCEPTANCE and LATEST-IMPLEMENTATION. Installed this checkout's own locked Python environment, `web/node_modules`, and Swift debug binary. Product source was not edited; no branch switch or commit was made. All runtime Python processes used `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`; browser and native services bound only to unique loopback ports. UI library and profile were under this checkout's ignored `.local/qa-stage-b-luna-final-ui/` tree.

No real account, user identity, credential, material, calendar, task, Feishu endpoint, model endpoint, or OS Keychain was accessed. Real provider call counters stayed at `0/1`; no real task write was attempted. `provider-settings.json` contains only a synthetic App ID and loopback callback. DMG, installed app, external OAuth browser, real provider behavior, model quality, and OS Keychain remain NOT_RUN.

## Environment setup

| Command | Exit | Evidence |
|---|---:|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv sync --locked --group dev` | 0 | `evidence/2026-10-11-stage-b-luna-final-ui-qa/uv-sync.log` |
| `npm --prefix web ci` | 0 | `.../npm-ci.log` |
| `cd native && swift build` | 0 | `.../swift-build.log` |

The above only establishes an independent UI runtime; root's offline backend QA separately covers the full Stage B suite. The QA checkout's source SHA remained fixed throughout this UI run.

## Results

| Scope | Result | Observation |
|---|---|---|
| B05 / browser library flow | PASS (synthetic) | Created isolated library, line and project; Fake authorization, synthetic material selection/import, Fake organization, draft edit and explicit approval, first-index plan and confirmation, query and citation. UI states are summarized in `evidence/.../browser-ui-observations.md`; approved synthetic page and manifest are preserved separately. |
| B05 / Fake calendar | PASS (synthetic) | Explicit one-day range and Asia/Shanghai displayed two seeded Fake events. No real calendar read. |
| B05 / Real settings and task gate | PASS (synthetic configuration) | Saved Real mode with synthetic non-secret app ID and loopback callback. Real task creation was disabled; setting said no app secret, no verified user identity, and no provider capability. No secret or external call. |
| C18 / independent local progress | PASS (synthetic) | Reviewed proposal, separately confirmed and executed local progress action. Manifest `progress_version` moved to 1. This did not create a Feishu task. |
| B05 / native window and readiness | **FAIL (P1)** | Native app showed a blank WKWebView and then `本地服务未就绪` although its API health had `service=ready`, its child `SUMMIT_RUN_ID` exactly matched the health `run_id`, and the Web endpoint returned HTTP 200. See QA-UI-B-02. |
| B05 / hot restart and delayed npm | NOT_RUN | Stopped after deterministic native cold-start failure; rerun on the repaired fixed SHA is required. |
| Browser console | NOT_CAPTURED | CUA Target accessibility/interaction surface did not expose a console-log method. No console-zero claim. |
| Browser network | PARTIAL | Actual uvicorn method/path/status log only; 124 API lines (117 × 200, 5 × 201, 2 initial workspace 409), not a HAR and does not capture request bodies. Runtime services used offline guard and Fake providers. |
| OAuth link / external browser, DMG, OS Keychain, real providers | NOT_RUN | Outside offline synthetic scope. |

## QA-UI-B-02 — P1: native readiness rejects the successful Web URL

Native wrapper: `local.summit.stageb.luna.final.ui.qa`, exact checkout binary `native/.build/debug/SummitEverything`, API port 18901, Web port 15181, independent profile. CUA showed a blank white WebView, followed by the readiness alert. The alert's “OK” closed the app; both listeners and checkout-owned runner processes were then absent.

API `/api/v1/health` returned HTTP 200 and `run_id=C73B316A-CFDF-4123-8A52-B0489FC22845`. The actual native child environment held the same `SUMMIT_RUN_ID`. `GET http://127.0.0.1:15181/` returned HTTP 200. A separate Foundation `URLSession` loopback probe reproduced the comparison used in `native/Sources/SummitEverythingApp/App.swift`: configured `webURL` is `http://127.0.0.1:15181` (empty path), while `URLSession` reports `response.url` as `http://127.0.0.1:15181/` (slash path); Swift `URL` equality is false despite status 200. Raw result: `evidence/2026-10-11-stage-b-luna-final-ui-qa/web-url-probe.log`; run identity and alert: `native-run-identity.json` and `native-cold-start-alert.txt`.

The implementation's readiness guard compares `webResponse?.url == webURL`; it therefore discards this successful response, keeps polling, and eventually shows the readiness error. This prevents normal native startup. This is a reproducible, user-visible P1 in B05. The readiness repair is not accepted until a new fixed SHA loads both ordinary and delayed npm startup on a fresh independent checkout.

## Evidence and cleanup

Adjacent evidence directory: [evidence/2026-10-11-stage-b-luna-final-ui-qa](evidence/2026-10-11-stage-b-luna-final-ui-qa). It includes exact native identity, URLSession probe, browser API access log, UI observations, synthetic workspace manifest/page, settings and cleanup result. The CUA screenshot was visible during the failed native run but is not present as a file; this limitation is stated in the evidence. The evidence manifest records SHA-256 for preserved files.

No code, tests, dependency lock, or product behavior was changed in this QA checkout. Browser server was stopped with Ctrl+C (exit 130); native app terminated after alert acknowledgement. Cleanup: API 18901 closed, Web 15181 closed, no owned native/service process remained. Historical 7f and 8b FAIL reports remain untouched.

Evidence manifest SHA-256: `e8b80cffe44ce6854ca21b58a0a82786ccf2e8109c6858c5fc1e59fc63a8e433` (12 evidence files; manifest excludes itself). This report and evidence remain an uncommitted QA-only record in the detached fd204 checkout so the fixed-source P1 history remains intact.
