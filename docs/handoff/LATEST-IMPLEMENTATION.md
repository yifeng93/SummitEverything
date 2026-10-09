# Latest implementation handoff

## Fixed implementation

- **Stage:** M1 local knowledge loop remediation; implementation self-check complete, waiting for a new independent review.
- **Product baseline:** `docs/product/PRODUCT-SPEC.md`, decisions confirmed 2026-10-09.
- **Fixed code SHA:** `7b41ca272b14c38a7b6ebf0e9766766749ccf001`.
- **Branch:** `codex/project-foundation`.
- **Implementation commit:** the fixed code SHA is the implementation checkpoint; later documentation commits on this branch record QA history and handoff updates.
- **Prior independent QA:** two reports test the old implementation SHA `f364c0122a1a74580009bf9342e6e864df6d975d` and are now included in this branch. `docs/quality/reports/2026-10-09-M1-f364c01.md` (source report commit `c4f755f648324bf714000e2765fa99917909692b`) reports C08/C10 FAIL and C03/C06/C13/C14 incomplete. `docs/quality/reports/2026-10-09-M1.1-M1.5-f364c01.md` (source report commit `51b3654`) reports C05/C06/C13 FAIL, C08/C10 PASS, and C03/C07/C11/C12/C14 incomplete. The reports disagree on some case outcomes and remain separate evidence for their fixed SHA; neither is a result for this remediation SHA.
- **Independent review of this SHA:** not run. Do not mark M1 QA passed based on the self-check below.

## Remediation summary

- C08: draft review now reports a stale target as a conflict, refreshes the current page snapshot, displays the current-versus-draft comparison, and requires the reviewer to explicitly adopt the current version before retrying. The page writer still checks the version at confirmation time.
- C10: changed pages remain visible as needing confirmation. Page Reader now shows the current title and body and offers an explicit confirmation action. The new version is confirmed before it becomes eligible again; old cached chunks remain excluded until incremental indexing.
- C06: a selected source can produce multiple proposals using its Markdown H2 sections. Every proposal keeps source links and inherits the single line/project selected by the user. Each draft remains independently pending until confirmed. C06 has been revised to match the already-confirmed single-project boundary; automatic cross-project routing is out of scope.
- C03/C13 M1 portion: added checks for archived project knowledge remaining searchable, nonempty project deletion being rejected, superseded knowledge being excluded from current retrieval, and history citations carrying `superseded` validity.
- C14 M1 portion: SSE tests now check contiguous sequence numbers, a single terminal event, and cancellation without a false completion.
- The writer now permits a user-confirmed page whose validity is `superseded`; it remains history-only under the shared retrieval gate.

## Startup commands

From the repository root, start the browser preview:

~~~sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
~~~

Open `http://127.0.0.1:5173`. The script starts FastAPI at `127.0.0.1:8793` and Vite at `127.0.0.1:5173`; `http://127.0.0.1:8793/api/v1/health` returned `ready`. Ctrl+C on this script stopped both listeners.

Native development command: `cd native && swift run`. It started the API and Vite services in this environment. After the macOS Documents access prompt was approved, I also opened a temporary debug `.app` wrapper around the built shell. The API and Vite listeners were active; I sent the app's normal `⌘Q` Quit shortcut through the native UI, the app exited, and a subsequent `lsof` / process check showed no listeners on either port and no owned `run_dev.py`, Uvicorn, or Vite process. This verifies the development-shell normal-Quit cleanup path. The previously observed terminal Ctrl+C path for `swift run` can still leave child listeners running. M4 package/DMG, clean-install, and restart behavior remain unverified.

## Browser replay with isolated synthetic material

Replay workspace: `/tmp/summit-m1-fix-replay-nwyhoS` (synthetic only).

1. Start the browser preview and create a new workspace at that path.
2. Create line `模拟业务线` and project `用户选定的模拟项目`.
3. Save one note with H2 sections `预算` and `时间`. Select the one source and the one project, then explicitly generate drafts. The UI showed two independently reviewable drafts with one source each.
4. Confirm `预算` only. `时间` remained pending. Confirm it afterward to continue the page-update replay.
5. Edit the confirmed `时间.md` outside the app, changing `周五` to `周六`. Reload and open the page: the UI showed `待确认`, the current body, and `确认当前版本`. Confirm it and observe the page return to confirmed status.
6. Save another one-section note, generate its draft, select the existing `时间` page, and save the target selection. Edit that page externally from `周六` to `周一` while the draft is open. Confirming the draft returned a conflict; the UI displayed the externally changed body and disabled confirmation until `采用当前页面作为比较基准` was clicked. Save the draft and confirm again. The original external edit was not overwritten before explicit rebase.
7. All material, facts, and workspace state in this replay are synthetic and local. The replay did not initialize any real “场地与酒店” content.

## Verification evidence at the fixed SHA

- `uv run ruff check src tests scripts`: passed.
- `uv run ruff format --check src tests scripts`: passed.
- `uv run mypy src`: passed, 22 source files.
- `uv run pytest -q`: **72 passed**, one Starlette `TestClient` / httpx deprecation warning.
- `uv lock --check`: passed.
- `uv build`: source distribution and wheel built.
- `npm test`: **4 passed** across 3 files.
- `npm run typecheck`: passed.
- `npm run build`: passed.
- `npm run lint`: exited 0, with three existing `react/set-state-in-effect` warnings in `ProjectsView`, `TodayView`, and `AskView`.
- `swift build`: passed.
- Browser UI replay: C06, C08, and C10 flows above were manually exercised in the local UI.
- C03/C13/C14 additions are covered by automated service/integration tests; this is developer evidence, not independent acceptance.
- Local preview listeners were checked absent after stopping the preview and again after native app `⌘Q`.

## Not tested / remaining gates

- Independent Luna review of the new fixed SHA and a new report covering M1.1–M1.5.
- C03 full structural matrix (all line/project edits, moves, and deletion cases) requires independent review; the added developer test covers archive/search and nonempty deletion.
- C13 historical session UI and C14 disconnect recovery / old citation UI are M3 work and were not tested here. The M1 retrieval and stream portions are listed above.
- Native `.app` archive, DMG, clean-machine install, restart, and release identity verification (M4). The development wrapper Quit check does not cover those packaged scenarios.
- Real business sample confirmation and initialization; real model quality, credentials, costs, Feishu read/write, or task creation.
- Five-day single-device use and two-device round trip.
- The Starlette/httpx deprecation and three frontend lint warnings remain visible; no check was relaxed.

## QA handoff

Use an independent checkout/worktree at exactly `7b41ca272b14c38a7b6ebf0e9766766749ccf001`. Read `docs/handoff/TESTER.md` and `docs/quality/ACCEPTANCE.md`; record each relevant result with evidence. In particular, re-run C08/C10 against the new SHA, review the revised C06 boundary, and report C03/C06/C13/C14 scope without filling historical M3 or native M4 gaps as passes. Do not edit implementation code or infer independent approval from this handoff.
