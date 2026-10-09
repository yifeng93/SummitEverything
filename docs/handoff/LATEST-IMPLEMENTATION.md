# Latest implementation handoff

## Fixed implementation

- **Stage:** M1 local knowledge loop, M1.1–M1.5 DEV complete; waiting for independent QA.
- **Product baseline:** `PRODUCT-SPEC.md`, 2026-10-09 decisions.
- **Fixed code SHA:** `f364c0122a1a74580009bf9342e6e864df6d975d` (`feat(m1): complete local knowledge loop UI`).
- **Branch at implementation:** `codex/project-foundation`.
- **Working tree:** implementation code remains at the fixed SHA above; this follow-up adds native-shell verification evidence only.
- **Independent QA:** not run. Do not treat the DEV checks below as an acceptance pass.

## What is implemented

- Authenticated loopback FastAPI API, workspace and profile separation, line / project / page browsing, transactional page confirmation and update.
- Local source intake, original-content reading and hash verification, deterministic FakeLLM drafts, source-linked review, partial confirmation, and action suggestions that are never executed.
- Incremental local index planning and execution, query SSE with ordered events and cancellation, citations rechecked against current page content before opening.
- React / TypeScript WebUI for Today, Projects & Knowledge, Knowledge Ask, and Settings; OpenAPI-generated TypeScript types.
- A thin macOS SwiftUI / WKWebView development shell that starts the local services, waits for API readiness, provides a native folder chooser, and stops its owned process.
- One-command local API + browser preview in `scripts/run_dev.py`.

The implementation uses only temporary synthetic materials and fake model / embedding / reranking providers. No real “场地与酒店” materials were read, imported, approved, committed, or used to initialize a workspace. No real model or Feishu endpoint was called.

## Startup command

From the repository root, install dependencies and launch the browser preview:

~~~sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
~~~

Open `http://127.0.0.1:5173`. The script creates an ephemeral session token, starts the API on `127.0.0.1:8793` and Vite on `127.0.0.1:5173`, and stops both services on Ctrl+C. Readiness can be checked at `http://127.0.0.1:8793/api/v1/health`.

The native development shell command is `cd native && swift run`. After unlock, a temporary debug `.app` wrapper around the `swift build` output rendered the SwiftUI window and embedded WebUI; switching to workspace setup and selecting the synthetic replay folder through the native chooser populated the setup path field. No workspace was created through that picker flow. Separately, `cd native && swift run` started its own API and Vite services; `/api/v1/health` returned `ready`. Interrupting that terminal-launched process with Ctrl+C left its child services running. I sent SIGTERM to the `run_dev.py` parent I had started, and confirmed both listeners stopped. Closing the normal app window / choosing Quit while it owns the services still needs verification.

## Browser replay with synthetic data

1. Start the preview with the command above. Create a fresh empty temporary directory and choose it as a new workspace in the setup screen.
2. In **项目与知识**, create one synthetic line and one synthetic project.
3. In **今日**, save two clearly synthetic notes to **待整理**. Select both items, select their line and project, and explicitly generate drafts.
4. Open both drafts and verify the full draft and original source are available. Confirm only one draft; verify the other remains pending.
5. Save another synthetic note, generate its draft, select the existing confirmed page in **整理到**, inspect the current-page / draft comparison, and confirm the update.
6. In **知识问答**, prepare and confirm the first index plan, ask about a fact in the confirmed synthetic page, then click its citation and verify the current page opens.
7. Edit that page outside the app, then ask about its indexed text again without rebuilding. The expected result is “没有找到经确认且仍为当前版本的相关资料” and no citation. This guards against stale index evidence.
8. Stop services with Ctrl+C. Keep this isolated workspace for inspection or discard it after QA.

This replay was performed in a temporary folder under the system temp directory. It exercised line / project setup, multiple drafts, partial confirmation, an authoritative page update, index build, query, citation navigation, and stale-content exclusion after an external edit.

## Verification evidence

- `uv run pytest -q`: **67 passed**, with one Starlette `TestClient` / httpx deprecation warning.
- `uv run ruff check src tests scripts`: passed.
- `uv run ruff format --check src tests scripts`: passed.
- `uv run mypy src`: passed; 22 source files.
- `uv lock --check`: passed.
- `uv build`: source distribution and wheel built.
- `npm run api:types`: OpenAPI contract exported and TypeScript types generated.
- `npm test`: **2 passed**.
- `npm run typecheck`: passed.
- `npm run build`: production assets built.
- `npm run lint`: exited 0, with three `react/set-state-in-effect` warnings on async initial data loading effects in `ProjectsView`, `TodayView`, and `AskView`.
- `swift build`: passed.
- Browser replay: the actual app was used through the local WebUI; after an external page edit, a query against stale indexed content returned no citation.
- Native shell spot check: launched temporary debug wrapper, rendered the WebUI, opened the native folder chooser, selected the already-created synthetic replay workspace, and observed its path in setup. No real user files were opened.
- Native service startup: `cd native && swift run` launched API + Vite; health returned `{"service":"ready","workspace_open":false,"version":"1.0.0"}`. Ctrl+C did not stop the child listeners; after SIGTERM to this test's `run_dev.py` parent, both API and Vite listeners were absent.

## Not tested / remaining gates

- Independent Luna QA against this fixed SHA and `docs/quality/ACCEPTANCE.md` has not run.
- Native shell normal UI Quit / close-window cleanup is not verified. The terminal Ctrl+C path left API and Vite child processes running, which were stopped manually; independent QA should exercise normal application termination and report this observation.
- The picker test did not create or initialize a workspace.
- No `.app` archive, DMG, clean-machine install, update, restart, or release identity verification; these belong to M4.
- No real business material or “场地与酒店” sample confirmation / workspace initialization.
- No real cloud model quality, credential, cost, Feishu read/write, or real task creation test.
- No five-day single-device use or two-device round trip.
- The frontend lint warnings and Starlette/httpx deprecation warning are recorded above; neither was hidden by relaxing a check.

## QA handoff

Please check out exactly `f364c0122a1a74580009bf9342e6e864df6d975d` in an independent checkout / worktree. Follow `docs/handoff/TESTER.md` and `docs/quality/ACCEPTANCE.md`, record each M1 scenario as passed / failed / untested with evidence, and write the independent report separately. Do not edit the implementation or infer a pass from this DEV report.
