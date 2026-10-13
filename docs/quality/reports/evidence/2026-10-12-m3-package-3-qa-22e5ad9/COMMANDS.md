# 固定 SHA QA 命令与日志

所有 Python 服务/测试均使用 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`，只连 Fake 模型/Feishu、MemorySecretBackend 与隔离合成 workspace。每项命令的原始输出及实际退出码在 `raw-logs/<name>.log` 和 `.exit`。

| 名称 | 实际命令 | 退出码 |
|---|---|---:|
| uv-sync | `uv sync --locked --group dev` | 0 |
| npm-ci | `npm --prefix web ci` | 0 |
| backend | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 |
| ruff | `uv run ruff check src tests` | 0 |
| format | `uv run ruff format --check src tests` | 0 |
| mypy | `uv run mypy src` | 0 |
| lock | `uv lock --check` | 0 |
| build | `uv build` | 0 |
| api-types | `npm --prefix web run api:types` | 0 |
| web-test | `npm --prefix web test -- --run` | 0 |
| web-typecheck | `npm --prefix web run typecheck` | 0 |
| web-lint | `npm --prefix web run lint` | 0（2 条既有 warning） |
| web-build | `npm --prefix web run build` | 0 |
| bulk | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python scripts/m3_package3_bulk_sample.py` | 0 |
| package3-core-regressions | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/unit/test_workspace_archives.py tests/unit/test_profile_event_log.py tests/integration/test_intake_review.py tests/integration/test_stage_b_refresh_restart.py tests/integration/test_actions.py tests/integration/test_feishu.py` | 0 (97 passed) |
| package3-qualification-mutations | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_answer_context.py tests/integration/test_qualified_retrieval.py tests/integration/test_workspace_mutations.py` | 0 (37 passed) |
| known-c19 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa/m3-package-3/repro_known_c19.py` | 0（复现产品反例） |
| archive-failure-matrix | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa/m3-package-3/repro_archive_failure_matrix.py` | 0 |
| reconcile-archived-progress | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa/m3-package-3/reconcile_archived_progress.py` | 0 |
| running-receipt-failure | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa/m3-package-3/repro_running_receipt_failure.py` | 0（断言检查报告中的实际反例） |

另外两服务分别以 `scripts/run_dev.py` 在 ports 15173/18793 与 15174/18794 启动，配置独立合成 profile 根目录、共享合成 workspace 和不同 session token。已向两服务发 Ctrl-C 并确认四端口无 LISTEN。
