# 最新实现交接

## 当前任务：整合本机 LanceDB 索引（2026-10-28）

- 目标分支：`codex/mcp-workbench-prototype-20261023`；基线 `67b8169115fe166c819e2a5c410831798809c874`。固定候选 SHA：待提交后填入。
- 来源分支：`codex/lancedb-local-20261023`，候选 `596ddab6b6c1b82ad43f283990f4a1076694fa9a`；索引实现始于 `c2f7afa`，旧 SQLite 自动迁移于 `c042a4f` 撤销。来源历史证据只适用于其固定候选，不替代目标组合 QA。
- 本次范围：LanceDB 索引存储与依赖锁、旧向量显式重建策略、必要检索/并发修复、相关离线回归、构建兼容脚本及索引契约。无 UI/native 产品实现变更。
- 目标原有未提交 UI/原型与其它 dirty 改动保留。`query.py` 与 `test_qualified_retrieval.py` 的原修改继续保留在工作树；性能修改复用页面快照，答案 provider 返回后引用资格由磁盘实时复验。
- 启动时 dirty 字节备份及 SHA 清单：`.local/dev/lancedb-integration/start-dirty/manifest.json`。集成测试合成库隔离；没有重建 `.local/dev`、调用 seed/provider、清理索引、打包或重启其他 App。
- 固定代码候选：本任务的中文集成提交 HEAD（具体 full SHA 由 Git commit 回执给 QA；源 QA 报告不外推到此提交）。
- 离线验证：目标 `.venv` 的 `uv sync --offline --locked --group dev` exit 0；索引/资格/并发/检查器回归 exit 0（107 passed）；Ruff check、format check、mypy exit 0。完整 Python 回归 exit 1（748 passed、1 failed）：失败仅为既有 `test_stage_b_r4_loopback.py::test_r4_02_deadline_cases_hold_over_ten_consecutive_runs[0.15-cfg1-False]` 的首轮冷连接时序（0.404s > 0.25s），原样重跑 exit 0（1 passed）。Starlette/httpx deprecation warning 保留。
- 日志：`.local/dev/lancedb-integration/logs/`；初始 dirty 原字节与 SHA 清单：`.local/dev/lancedb-integration/start-dirty/manifest.json`。对目标原有 query/qualified-test 修改以源分支版本进入候选提交；用户原性能优化保留在工作树 dirty；对现有未跟踪 inspect_index/test_inspect_index 已适配并随任务提交。其它 UI/native/web 与 prototype dirty 不入提交，启动时字节副本保留于上述备份目录。
- 未测：真实 provider、真实工作库/材料、真实索引迁移或重建、包与 App、runtime model metadata（**UNVERIFIED**）、真实外部能力和发布门。

## 历史交接

任务开始时的原型交接全文保存在[2026-10-28 集成前交接快照](history/2026-10-28-pre-lancedb-integration-LATEST-IMPLEMENTATION.md)。之前 10 月 17 日及更早的固定版本交接仍按各自历史 SHA 理解。
