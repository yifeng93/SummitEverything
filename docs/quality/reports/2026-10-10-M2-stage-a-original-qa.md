# M2 阶段 A 原始候选定向独立验收

日期：2026-10-10。身份：独立 QA。范围仅为对固定原始候选的缺陷复现，不是阶段 A 最终报告。

## 固定对象与来源

- 受测代码：`09398fcae597b2478001d40aedf580ea91322c11`。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/qa-m2-stage-a-original`，分支 `codex/qa-m2-stage-a-original`。
- 独立依赖环境：checkout 内 `.qa-env`；`UV_PROJECT_ENVIRONMENT=.qa-env uv sync --frozen --group dev` 退出 0，按 `uv.lock` 安装 31 个包，无依赖升级。
- 代码候选父提交：`791f3a63d9483e4ddd97774a4e083d59ed52ffdc`；原始代码候选树与后续 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb` 的 `src/`、`tests/`、`web/`、`native/` 比较无差异。两者间文档树有差异。
- 文档 checkpoint：`0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4` 是原代码候选的直接子提交；交接文档分支 `53ad048` 也保留同一实现树，且祖先包含关系成立。
- 原提交 `09398fc` 中没有 `docs/quality/reports/2026-10-10-M2-DEV.md`；该文件在 `53ad048` 的文档差异中新增。其余指定产品规格、架构、工作库/API 契约、实施/测试交接、完整 v1 计划、ACCEPTANCE、LATEST-IMPLEMENTATION、M2.1/M2.2-review/M2.3 DEV 报告及 M2.2 SDD 报告已阅读。所有文档只作规格和开发者主张来源，未当作 QA 通过证据。
- 独立测试与本报告由本报告提交承载；代码和本报告的 SHA 关系在 QA 分支提交历史中可查。测试文件：`tests/integration/test_stage_a_original_qa.py`。

## 独立缺陷复现

命令：

```sh
UV_PROJECT_ENVIRONMENT=.qa-env uv run --frozen pytest -q tests/integration/test_stage_a_original_qa.py
UV_PROJECT_ENVIRONMENT=.qa-env uv run --frozen pytest -q tests/integration/test_stage_a_original_qa.py tests/integration/test_actions.py tests/integration/test_journal_overviews.py
```

第一条结果：4 failed。第二条结果：4 failed、28 passed，1 条既有 Starlette/httpx TestClient 弃用警告。失败仅来自新增 QA 断言；三个既有集成文件合计的 28 项通过。测试使用真实 API、PageWriter、SQLite 索引、查询资格检查及 Fake Feishu；无真实账号、凭据、材料、模型、网络或外部副作用。

| 缺陷 | 结果 | 复现与观察 |
|---|---|---|
| A-01 / P0 | FAIL | 合成项目概览含 `validity: superseded`、tags、source_refs 和合法自定义元数据。经 PageWriter 显式确认并建立本地 Fake 索引后，只经概览确认 API 修改标题且正文保持不变。API 返回 201，但 `validity`、tags、source_refs、自定义字段均未保留。再执行真实增量索引并走查询资格门，原 superseded 概览成为 1 条当前引用。回归断言输出：`metadata_preserved=False; overview_cited=True; citations=1`。证明内容确认隐式恢复知识效力并误导当前问答。 |
| A-02 / P1 | FAIL | 先创建 Fake 合成任务，再拟定并独立确认完成动作；provider 的 PATCH 对同一 GUID 返回未变更旧任务（`completed_at=0`）。动作回执状态为 `succeeded`，Fake 远端仍未完成。测试失败：`actual.completed_at == 0`。 |
| A-03 / P1 | FAIL | 将已确认的 Fake 创建动作执行到 provider 已写后 timeout，动作进入 `unknown`；Fake 的 `task_result` 随后返回一条预先创建的无关任务。核实路由把动作置为 `succeeded`。测试失败：预期 `unknown`，实际 `succeeded`。这证明普通 FeishuTask 对象不能关联到当前动作。 |
| A-04 / P1 | FAIL | 合成库已有明确确认并索引的正式页。经 `/api/v1/journal/log` 保存一条独特新日志，API 返回 201；未手动触发索引时 SQLite 仍为 1 页而非 2 页。测试断言自动增加页数失败。没有调用任何真实 embedding。 |
| A-05 / P2 | FAIL | `JournalView.tsx` 将每条已保存日志/思考硬编码显示“已确认”，不读取实际 approval_state/validity；外部编辑停用旧批准后 UI 会继续显示虚假批准。计划顶部仍写“最早未实施任务为 M2.1”，与同版中 M2.2/M2.3 DEV 完成状态矛盾。计划把“长期秘密交钥串”标成已完成，但架构和 M2.1 报告注明当前只有 MemoryCredentialStore / 内存凭据，没有 OS Keychain adapter。历史 console 0 错误、Swift build 和资源准备不作为最终候选浏览器/壳或真实接入证据。前两项为错误状态展示；Keychain 项为实现状态误记。 |

## 范围矩阵（本轮原始候选）

| 案例 / 范围 | 结果 |
|---|---|
| A-01 至 A-04 必须修复的反例 | FAIL（均由新增独立 API/文件/索引黑盒测试复现） |
| A-05 状态与文档准确性 | FAIL（代码/规格交叉检查） |
| C09 / 日志、思考、概览既有自动集成回归 | 部分 PASS：新增前已存在的相关 28 项 actions / journal 集成用例通过；不代表独立 UI 验收或整行 C09 PASS |
| C15 / Fake 授权、材料、分页、导入、日历和实际 UI | NOT_RUN：原候选已出现 P0/P1，按交接不进行昂贵浏览器复演；本报告不复用 DEV 报告结论 |
| C16–C18 / Fake 动作及进度 | FAIL：A-02/A-03 已分别命中成功证据错误和错误核实；C16–C18 整行未测 |
| C04/C10/C11/C12/C13/C23 与原件/稿件/失效及恢复 | NOT_RUN：未执行完整交叉矩阵 |
| 浏览器 console、浏览器端到端 | NOT_RUN：本轮用 API/服务黑盒复现；没有最终 UI 证据 |
| 原生开发壳窗口、目录选择、Quit / 进程清理 | NOT_RUN：原候选已有关键 P0/P1，不进行壳复演；历史 M1 壳记录不能替代此版本证据 |
| 真实 Feishu、真实模型/材料、真实 Keychain、DMG、五日/双机 | NOT_RUN：超出授权和本阶段模拟范围，资源没有使用 |

## 结论与交接

原始候选存在 1 个 P0、3 个 P1、至少 1 个 P2，不能通过阶段 A，也不应以该候选执行完整 UI/壳验收或合并。必须保留本报告和回归测试，执行者在新代码 SHA 修复后交回独立 QA。下一候选须重新固定 SHA 并重验受影响业务；本报告结论仅适用于 `09398fcae597b2478001d40aedf580ea91322c11`。
