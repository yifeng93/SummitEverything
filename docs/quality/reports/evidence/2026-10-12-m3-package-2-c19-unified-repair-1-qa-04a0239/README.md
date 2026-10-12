# C19 unified repair 1/2 QA evidence

Tested product source: `df1aac288a002e86a24132a9954fbe0b18d41d1f`.
Tested checkout HEAD: `04a0239012068598123966ab31340127a6f8ff76`.
The source tree at HEAD is identical to the source commit; HEAD adds only handoff documentation. The checkout was clean before QA.

## Commands and results

- `npm --prefix web ci`: exit 0; 126 packages, 0 vulnerabilities (`raw-logs/npm-ci.log`).
- `uv sync --locked --group dev`: exit 0 (`raw-logs/uv-sync.log`).
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q .local/qa/c19-unified-r1/harness/test_c19_previous_holdout.py`: 12 passed, exit 0 (`raw-logs/previous-holdout.log`).
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`: 449 passed, one existing Starlette/httpx deprecation warning, exit 0 (`raw-logs/guarded-pytest.log`).
- `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy src`, `uv lock --check`, `uv build`, `npm --prefix web test -- --run`, `npm --prefix web run typecheck`, `npm --prefix web run lint`, and `npm --prefix web run build`: all exit 0. Web: 56 tests / 12 files. Raw output is in `raw-logs/`; actual exits are summarized in `raw-logs/matrix-summary.txt`.
- New bounded holdout: 5 passed / 3 failed, exit 1 (`raw-logs/fresh-holdout-final.log`). The three failing assertions reproduce one mixed-topic scope defect, including reversed topic order. Shared budget/schedule coverage, explicit-topic negative controls, exact-topic positive control, short-alias negative control, broad title collision, open address query, and generic plan control passed.
- Browser UI: actual Chrome Incognito session against loopback services. Created an isolated workspace and synthetic confirmed page through the UI, manually approved first Fake index, queried the mixed-topic comparison, and reopened it from local history. The UI rendered zero citations and the same false missing-pair claims as the API query. Accessibility observations are in `ui-observations.md`.
- Final `lsof -nP -iTCP:18931 -sTCP:LISTEN` and `lsof -nP -iTCP:15131 -sTCP:LISTEN`: both exit 1 (no listeners), recorded in `raw-logs/listener-summary.txt`.

OpenAPI/TypeScript generation was NOT_RUN because the documented generator writes `web/openapi.json` and `web/src/api/generated.ts`; the independent QA rules prohibit writing product files. No product files were changed. Browser DevTools console/network export and PNG capture were NOT_RUN because this CUA session exposed accessibility observations only. Real model/provider/Feishu, Keychain, materials, native/DMG, five-day, two-machine, and release gates were NOT_RUN; runtime remains UNVERIFIED; smoke use remains 0.

## Defect: C19-QA-R1-01 (P1)

Fixture: a confirmed `白鹭工程` page states `白鹭工程预算上限为十八万元。`; a confirmed `赤陶项目` page states `赤陶项目活动证章领取须出示邀请函。`. Fake embedding, a deterministic high-score reranker and a recording answerer use the real PageWriter, SQLite IndexStore, and QueryService.

Question: `比较白鹭工程预算与赤陶项目的活动证章领取办法`.

Expected: preserve the separate requested pairs `(白鹭工程, 预算)` and `(赤陶项目, 活动证章领取)`; cite the respective confirmed passages, report no missing pair, and pass supporting excerpts to the answer provider. Both individual passages are directly relevant to their respective half of the question.

Actual in fact, comparison, and plan modes: zero citations and zero answer-provider calls; missing information incorrectly says both objects lack the combined `预算（活动证章领取）` evidence. Reversing topic order also yields zero citations and turns trailing object words into the exact missing topic. A fresh real-browser query showed the same false-negative result; reopening local history preserved it.

Reproduction: `harness/test_c19_fresh_holdout.py::test_fresh_mixed_topics_are_not_collapsed_into_one_dimension`; reversed-order reproduction is `::test_fresh_reversed_mixed_topics_still_keep_the_supported_pair`. The original C19 QA holdout 12/12 and the shared A/B budget-plus-schedule positive control pass, so this is a narrower per-subject heterogeneous-dimension parsing/assignment defect. Do not treat it as solved by the passing summary; Developer should repair the local subject/topic association and QA should rerun both orderings and the positive controls on a new fixed SHA.

All fixtures are synthetic and local. No real provider or business material was used. Product source, tracked tests, dependencies, and lockfiles were not edited.
