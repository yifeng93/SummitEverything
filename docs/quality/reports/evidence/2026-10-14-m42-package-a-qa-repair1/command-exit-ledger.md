# QA command / exit index

固定受测产品源码 SHA：419bb865b334389d1efd0f4a1a855cd0d5324d28。

输出原件及退出码位于 QA checkout .local/qa/m42-a-repair1/；不要从此 index 反推任何未执行场景。

- Dependency setup: uv sync --locked --group dev exit 0；npm --prefix web ci exit 0，输出在 automated-results-captured-2026-10-14.txt。
- Guarded full Python suite: PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q exit 0, 513 passed; full-guarded-pytest.log。
- Python static/build: ruff check, ruff format check, mypy, uv lock --check && uv build exit 0; exact output in automated-results-captured-2026-10-14.txt。
- Web: npm --prefix web test -- --run exit 0, 65 passed; api:types, typecheck, lint, build each exit 0; corresponding schema-generation, web_typecheck, web_lint, web_build .log/.exit pairs.
- Native: swift test --package-path native exit 0, 5 passed; swift_tests.log/.exit.
- QA P1 custom harness: initial 3 probes exit 0; expanded harness had explicitly retained exploratory failures explained in local correction history; corrected harness 3 passed/exit 0 (p1-repair1-probe-final.log/.exit). Existing active-owner + restart regression tests 2 passed/exit 0 (p1-tracked-regressions.log/.exit).
- Real JournalAssist Runtime + MockHTTP: 2 passed/exit 0 (real-journal-runtime-mockhttp.log/.exit). Planner C19: 41 passed/exit 0; selected retrieval counterexamples: 4 passed/exit 0 (shared-planner-c19 and planner-retrieval-targeted log/exit pairs).
- git diff --check exit 0.
- App manifest checks, DMG verify, copied app strict codesign, corrected process guard check, CUA port association and mount detach each exit 0. spctl returned exit 3 / rejected; see report. Full details are in matching .log/.exit files.
- CUA screenshots were not saved. The second exploratory harness failure output was overwritten before separate persistence; a short tool-output excerpt and the loss disclosure remain in probe-assertion-correction-history.txt.

Local evidence checksum manifest: .local/qa/m42-a-repair1/evidence-sha256.txt. It hashes harnesses and QA raw output; the manifest's own hash is recorded in the QA report. CUA screenshots were not saved. The second exploratory harness failure output was overwritten before separate persistence; this loss is disclosed.

