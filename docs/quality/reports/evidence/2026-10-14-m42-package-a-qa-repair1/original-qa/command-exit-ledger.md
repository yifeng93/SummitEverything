# M4.2 Package A QA repair1 command ledger

All results target source SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28` in this checkout. Product source remained unchanged. Logs and exit files are local under `.local/qa/m42-a-repair1/`.

| Command / scope | Exit | Saved output |
|---|---:|---|
| `uv sync --locked --group dev` | 0 | `automated-results-captured-2026-10-14.txt` |
| `npm --prefix web ci` | 0 | same combined transcript |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q .local/qa/m42-a-repair1/test_package_a_contract_probe.py` (original 3 probes) | 0 | same combined transcript |
| same guarded focused harness after additional assertions | 1, then 0 after correcting assertions to match API/durable-ledger contract | `p1-repair1-probe.log/.exit` (initial assertion failure retained); `probe-assertion-correction-history.txt` (second failure's raw was overwritten and loss disclosed); `p1-repair1-probe-final.log/.exit` (3 passed) |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | `full-guarded-pytest.log` (513 passed; StarletteDeprecationWarning) |
| `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy src`; `uv lock --check && uv build`; `npm --prefix web test -- --run` | 0 each | exact stdout and exits in `automated-results-captured-2026-10-14.txt`; 65 Web tests passed |
| `npm --prefix web run api:types` | 0 | `schema-generation.log/.exit`; generated files did not leave tracked diffs |
| `npm --prefix web run typecheck` | 0 | `web_typecheck.log/.exit` |
| `npm --prefix web run lint` | 0 | `web_lint.log/.exit`; two existing React set-state-in-effect warnings |
| `npm --prefix web run build` | 0 | `web_build.log/.exit` |
| `swift test --package-path native` | 0 | `swift_tests.log/.exit` (5 passed) |
| `git diff --check` before report | 0 | `git_diff_check.log/.exit`; final pre-report check in `final-git-diff-check.log/.exit` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_feishu_real_gate.py -k 'live_acceptance_plan_owner_remains_executing or interrupted_acceptance_plan_is_reported_unknown_without_replay'` | 0 | `p1-tracked-regressions.log/.exit` (2 passed) |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_real_model_approval_flow.py` | 0 | `real-journal-runtime-mockhttp.log/.exit` (2 passed) |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_c19_topic_scope_normalization.py` | 0 | `shared-planner-c19.log/.exit` (41 passed) |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_qualified_retrieval.py -k 'open_action_questions_keep_context_and_result_clause_as_one_evidence_unit or comma_clause_for_another_known_object_is_not_sent_as_evidence or open_action_question_keeps_existing_topic_dimension_filter or c19_general_comparison_keeps_multiple_material_path_without_object_gate'` | 0 | `planner-retrieval-targeted.log/.exit` (4 passed) |
| Candidate DMG SHA-256 via `shasum -a 256` | output captured; no separate exit file | `dmg-sha256.log`; expected and observed `2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a` |
| `hdiutil verify <candidate DMG>` | 0 | `dmg-verify.log/.exit` |
| Read-only mount / mounted and copied app manifest `shasum -a 256 -c` | 0 each | `dmg-mount.log/.exit`, `mounted-dmg-app-manifest.log/.exit`, `copied-app-manifest.log/.exit` |
| `codesign --verify --deep --strict <copied app>` | 0 | `copied-app-codesign.log/.exit` |
| `spctl --assess --type execute --verbose=2 <copied app>` | 3 | `copied-app-spctl.log/.exit` (`rejected`, ad-hoc signing); no Gatekeeper bypass or quarantine change |
| Corrected pre-UI process guard/profile check and native/backend image/port association | 0 | `native-backend-guard-profile-corrected-launch.log/.exit`, `corrected-process-image-paths.log/.exit`, `cua-window-port-match.log/.exit` |
| Late post-context CUA launch sanitized guard check and exact-image SIGTERM | returned booleans false; exact PIDs were terminated | `late-launch-unverified-tool-transcript.txt` is an explicit transcription (not original redirected stdout); see UI observation note and report |
| `hdiutil detach <QA read-only mount>` | 0 | `dmg-detach.log/.exit` |

`automated-results-captured-2026-10-14.txt` is the actual tool-result transcript for commands grouped there. Focused log pairs retain their own stdout and exit. The second exploratory probe failure was emitted by the tool but overwritten before it was separately copied; this is expressly disclosed and not recreated as raw.
