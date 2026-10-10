# M2 阶段 A 修复者 DEV 记录

日期：2026-10-10。身份：执行者。此记录不代替独立 QA。

## 固定对象关系

- 原始代码候选：`09398fcae597b2478001d40aedf580ea91322c11`。
- 原始文档 checkpoint：`0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`。
- 交接文档分支头：`53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。原 QA 已核实 `09398fc` 与 `53ad048` 的 `src/`、`tests/`、`web/`、`native/` 相同；差异为文档。
- 原候选独立 QA 代码对象：`09398fc`；QA 测试 / 报告提交：`f64c565b7c5105867e0c19e7e1e716dc726f8ff7`，独立分支 `codex/qa-m2-stage-a-original`。报告：[原候选定向 QA](2026-10-10-M2-stage-a-original-qa.md)。
- 整改分支：`codex/m2-stage-a-closeout`，初始文档头 `53ad048`。
- 修复实现提交：`7e3ed6062fe44a9f0f16a284686d6c9d00f9326e`。
- 最终固定修复代码 SHA：`d113cf43268982b747e8833c7d936b586156d92a`，在 `7e3ed60` 后增加异常日志脱敏和回归：索引失败只记工作库 UUID、异常类型，不写异常消息 / traceback；测试断言异常中的合成敏感探针未进入日志。本代码提交包含整改、回归测试、OpenAPI / TS 生成文件与 Fake-only UI 提示，不含本 DEV 文档。
- 当前文档在代码提交之后单独提交；独立复验报告应引用代码 SHA `d113cf4`，不得把后续文档 SHA 写成受测实现。

## 缺陷处置与本地证据

| 缺陷 | 处置 | 当前 DEV 证据 | 独立复验 |
|---|---|---|---|
| A-01 P0 | 概览更新基于已保存元数据，只覆盖明确编辑的业务字段；知识效力与正文确认分开。回归经概览 API、PageWriter、当前 SQLite 与 `QueryService.query` 检查，移除手动索引步骤；保留 superseded、tags、source_refs、自定义字段，不能成为当前引用。 | 原反例在 `09398fc` 上 4 条 QA 断言全部失败；整改后 `test_a01_overview_title_update_preserves_validity_and_metadata` 通过。 | 等待最终固定 SHA QA。 |
| A-02 P1 | 创建 / 编辑 / 完成回执验证请求目标及明确请求字段；日期验证 timestamp 与全天语义；完成要求响应同 GUID 且 `completed_at > 0`。结果不一致时动作保持 unknown，不再重放。 | `test_a02_same_guid_uncompleted_task_is_not_successful_completion` 与 `test_task_results_validate_requested_fields_and_explicit_clears` 覆盖同 GUID 未完成、错误创建结果、明确清空，动作测试通过。 | 等待最终固定 SHA QA。 |
| A-03 P1 | Fake 结果改用带 client token、动作类型、目标 GUID 与实际任务的 `TaskExecutionEvidence`；业务层再次验证 token / kind / target / 请求结果。普通任务对象或冲突证据不足以核实 unknown。未实现真实 Feishu 查询端点。 | `test_a03_unrelated_task_does_not_reconcile_unknown_create_as_success` 与 `test_reconciliation_rejects_execution_evidence_with_another_token` 通过；验证未知状态不重发。 | 等待最终固定 SHA QA。 |
| A-04 P1 | 首次索引仍显式确认；已有 fingerprint 后，在批准页面创建 / 更新、日志、概览、稿件确认和外部编辑重新确认后尝试同 fingerprint 增量。成功、未启用、失败由 MutationResult 与 `/index/status` 表示；失败不伪装 ready，检索引用仍按当前页 hash 复核。 | `test_a04_approved_journal_is_incrementally_indexed_without_manual_job`、`test_failed_automatic_incremental_index_is_visible_and_stale_chunks_are_rejected`、生命周期外部编辑复确认测试通过；Fake embedding 计数确认不重复嵌入未变内容。 | 等待最终固定 SHA QA。 |
| A-05 P2 | Journal 列表从 approval_state / validity 派生状态；实施计划更正 Keychain 实际仅 MemoryCredentialStore、M2 当前执行状态及真实资源状态。历史 DEV / console 记录不改写。 | Journal UI 组件回归通过；规格与计划文档交叉检查。 | 等待最终固定 SHA QA。 |

## 自动检查

实现者 checkout：`/Users/yifengstudio/.codex/worktrees/m2-stage-a-closeout`；隔离 profile / Fake remote / 临时工作库由测试框架在系统临时目录创建并清理，无真实凭据、材料、服务账户、模型或外部副作用。

| 命令 | 结果 |
|---|---|
| `UV_PROJECT_ENVIRONMENT=.venv uv sync --frozen --group dev` | PASS，使用锁定依赖；无依赖升级 |
| `UV_PROJECT_ENVIRONMENT=.venv uv run --frozen pytest -q` | PASS，最终 SHA `d113cf4` 上 142 passed；1 条既有 Starlette/httpx 弃用警告 |
| `UV_PROJECT_ENVIRONMENT=.venv uv run --frozen ruff check src tests scripts` | PASS |
| `UV_PROJECT_ENVIRONMENT=.venv uv run --frozen ruff format --check src tests scripts` | PASS |
| `UV_PROJECT_ENVIRONMENT=.venv uv run --frozen mypy src` | PASS，30 source files |
| `UV_PROJECT_ENVIRONMENT=.venv uv lock --check` | PASS |
| `UV_PROJECT_ENVIRONMENT=.venv uv build` | PASS，sdist / wheel |
| `npm ci` | PASS，无 audit 漏洞；不含安装额外依赖 |
| `npm run api:types` | PASS，OpenAPI / TS 生成文件同步 |
| `npm test` | PASS，8 files / 32 tests |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS；保留 3 条既有 react(set-state-in-effect) 警告 |
| `npm run build` | PASS |
| `cd native && swift build` | PASS；只证明编译，不证明窗口 / Quit 行为 |
| `git diff --check` | PASS |

## 当前限制与状态

- 该报告只记录执行者自测。浏览器关键流程、最终候选 console 导出、原生壳候选窗口归属、完整 C09 / C15–C18 / C04/C10/C11/C12/C13/C23 独立矩阵尚未由独立 QA 复验；未因这些自动检查通过而宣告阶段通过。
- 原始候选报告保留原有 FAIL；不得用本报告改写历史结论。最终报告应另行记录并固定到本次受测 SHA。
- 真实 Feishu、用户账户、真实模型 / embedding / rerank、业务材料、Keychain、DMG、五日 / 双机均 NOT_RUN。用户准备好的资源未消费。
- 没有启动 M3–M5。
