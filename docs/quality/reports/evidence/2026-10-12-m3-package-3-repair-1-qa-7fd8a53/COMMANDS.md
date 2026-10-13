# 固定 SHA QA 命令

Checkout `/Users/yifengstudio/.codex/worktrees/m3-package-3-qa-r1/SummitEverything`，HEAD `7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`，产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`。Python service/tests 设置 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`。每项命令退出码以同名 `.exit` 为准，完整 stdout/stderr 位于 `raw-logs/`。

| 检查 | 命令 | 结果 |
|---|---|---|
| 依赖 | `uv sync --locked --group dev` | exit 0 |
| Web依赖 | `npm --prefix web ci` | exit 0，126 packages，0 vulnerabilities |
| full pytest 首轮 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | fresh checkout缺Web依赖：439 passed/1 failed；保留日志 |
| Web依赖后 full pytest | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 440 passed，exit 0 |
| 独立失败路径 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa/m3-package-3-repair-1/harness/repro_repaired_lease_failures.py` | 两个故障反例 PASS，exit 0 |
| 核心回归 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/unit/test_workspace_archives.py tests/unit/test_profile_event_log.py tests/integration/test_intake_review.py tests/integration/test_stage_b_refresh_restart.py tests/integration/test_actions.py tests/integration/test_feishu.py` | 99 passed，exit 0 |
| qualification / mutations | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_answer_context.py tests/integration/test_qualified_retrieval.py tests/integration/test_workspace_mutations.py` | 37 passed，exit 0 |
| 归档故障矩阵 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python docs/quality/reports/evidence/2026-10-12-m3-package-3-qa-22e5ad9/harness/repro_archive_failure_matrix.py` | PASS，exit 0 |
| 已归档 proof reconcile | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python docs/quality/reports/evidence/2026-10-12-m3-package-3-qa-22e5ad9/harness/reconcile_archived_progress.py` | PASS，exit 0 |
| bulk | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python scripts/m3_package3_bulk_sample.py` | 120流程/4业务月，exit 0 |
| Fake Feishu 导入重放 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/integration/test_feishu.py::test_selected_body_calls_and_restart_replay` | 1 passed，exit 0 |
| Python 静态 / build | `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy src`; `uv lock --check`; `uv build` | 全 exit 0 |
| OpenAPI types | `npm --prefix web run api:types` | exit 0 |
| Web tests | `npm --prefix web test -- --run` | 56 passed，exit 0 |
| Web typecheck / lint / build | `npm --prefix web run typecheck`; `npm --prefix web run lint`; `npm --prefix web run build` | 全 exit 0；lint保留2条既有warning |
| 本机双profile浏览器 | `SUMMIT_API_PORT=17993 SUMMIT_WEB_PORT=16173 SUMMIT_PROFILE_ROOT="$PWD/.local/qa/m3-package-3-repair-1/profile" uv run python scripts/run_dev.py`，以及 B 使用 17994/16174/profile-b | 两端实际 UI 观察 PASS；端口清理见 `services-stopped.txt` |
| final integrity | `git rev-parse HEAD`; `git diff --quiet <ea11...> HEAD -- src web native config tests`; `git status --porcelain=v1` | SHA 固定；product diff exit 0；clean |

没有运行真实 provider/Feishu、Keychain、真实材料、Native/DMG、五日、双机和发布验收。浏览器 console/network、截图文件为 NOT_RUN。
