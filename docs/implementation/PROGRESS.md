# 实施进展账本

初始记录：2026-10-09。实现者维护，验收者另写报告；状态不从测试数量推断。

## 更新记录

- 2026-10-10：独立 QA 对修复源码 SHA `32da67e9c0280e3dae18fd374e30c925565b0b82` 完成 Fake-only M2.1–M2.3 阶段 A 验收，最终报告提交 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`（第四轮）；原候选缺陷初验与新候选各轮复验报告提交依次为 `f64c565b7c5105867e0c19e7e1e716dc726f8ff7`、`bb5231d5d31a64f57605bf8443f5f57752aac50d`、`91b0a93c615b3a16f5cf428b7f131a443d3ff59e`、`7f785c033bb96a43ae50ad6cf55b9c20474db85b`、`0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`。A-01–A-05 和 C09、C15–C18、C23 的报告关系与边界见 [验收矩阵](../quality/ACCEPTANCE.md) 及最终独立报告。结论：模拟范围 PASS，未关闭 P0/P1/P2=0；UI 无 OAuth cancel 控件的变体为 NOT_RUN，API denial 已覆盖。PR 与 main 合并后核验待进行。真实 Feishu / 模型 / 业务材料 / Keychain / DMG / 五日 / 双机按范围 NOT_RUN，M3–M5 未开始。
- 2026-10-10：阶段 A 原候选 `09398fcae597b2478001d40aedf580ea91322c11` 经独立定向 QA 发现 A-01 P0、A-02–A-04 P1 和 A-05 P2（报告提交 `f64c565b7c5105867e0c19e7e1e716dc726f8ff7`）。执行者在 `codex/m2-stage-a-closeout` 修复并固定代码 SHA `32da67e9c0280e3dae18fd374e30c925565b0b82`；后端 142 passed，前端 32 passed，静态检查、类型、构建及 Swift build 通过，保留 1 条 Starlette/httpx 弃用警告和 3 条既有 React lint 警告。索引错误日志限制为工作库 UUID 与异常类型；A-01 查询回归使用正文独特词检验真实引用门。A-01–A-05 当前仅为 DEV 修复状态，独立完整复验、真实浏览器 / 原生壳复演、PR 与 main 合并均待完成；详见 [阶段 A 修复 DEV 报告](../quality/reports/2026-10-10-M2-stage-a-fix-dev.md)。
- 2026-10-09：整理并纳入两份针对旧实现 SHA `f364c0122a1a74580009bf9342e6e864df6d975d` 的独立验收原报告；同步记录报告结论差异、模拟材料边界和新实现 SHA `7b41ca272b14c38a7b6ebf0e9766766749ccf001` 待独立复验状态。当时没有据开发自测宣告 M1 通过；最终状态见后续记录。
- 2026-10-09：本轮修复 C05 来源 / 整理作业 / 稿件状态与重复生成门禁、补充 C07 最终正文结果、修复本地开发服务身份及退出清理，更新 API / 工作库契约、执行 / 测试交接和当前阶段计划。候选代码固定在 `73ec81a06f2557c006f98ff88fa81b08d14ef315`；DEV 命令与浏览器 / 原生复演证据见 [自测记录](../quality/reports/2026-10-09-M1-close-DEV.md)。记录该条时独立 QA 尚未完成；后续发现 C03 P1 并修复，最终 QA 与收口结果见下一条记录及下方报告。
- 2026-10-09：首轮独立 QA 在 `73ec81a` 发现 C03 P1；执行者补齐目录管理与页面移动 / 链接 UI，并在最终受测代码 SHA `f349fe6cb5da86c3fdafff11738e2a55335d8874` 重新提交 QA。独立复验 M1 模拟范围通过，P0/P1=0、P2=1；PR #1 以 merge commit `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa` 合入 main，合并后完整检查通过。报告与外部门边界见下方记录。
- 2026-10-10：M2.1–M2.3 初始 Fake-only 开发自测固定于 `09398fcae597b2478001d40aedf580ea91322c11`；后续独立 QA 的定向缺陷和阶段 A 整改状态见本节首条及独立报告。初始候选原生壳 UI 未验收；真实 Feishu、Keychain、模型、DMG 等未测。详见 [M2 DEV 报告](../quality/reports/2026-10-10-M2-DEV.md)。
- 2026-10-10（用户补充）：真实飞书 App ID / secret / 回调地址、LLM / embedding / rerank、测试材料和 Keychain 均已准备好；用户可随时参与测试并补充配置。M2 固定代码尚未接入或调用这些资源，真实门继续标 NOT_RUN；后续评定应区分“测试条件已具备”和“实现/协议/真实 UI 已验证”。评估提示词见 [Sol 6.1 进度评估](../handoff/PROMPT-M2-ASSESSMENT-SOL-6.1.md)。

| 阶段 | 实施状态 | 独立验收 | 备注 |
|---|---|---|---|
| Foundation | 完成本阶段本地闭环基础能力 | QA通过（模拟范围） | 完整 M1 范围、P0/P1=0；DMG 与真实外部门未测 |
| M1 本地闭环 | 已合入 main | QA通过（模拟范围） | 受测代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；PR #1 merge commit `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`；详见独立报告和合并后检查记录 |
| M2 阶段 A（Fake-only） | 修复候选 `32da67e9c0280e3dae18fd374e30c925565b0b82` | QA通过（模拟范围） | 最终独立报告提交 `0531e0d`；A-01–A-05 及 C09/C15–C18/C23 的结果和限制见报告；PR 与 main 合并后核验待完成；真实门 NOT_RUN |
| M3 完整问答 / 连续状态 | 未开始 | 未开始 | 角色 / 记忆 / 历史各机本地 |
| M4 单机交付 / 五日试用 | 未开始 | 未开始 | 真实业务与模型质量不能由 mock 代替 |
| M5 双机 | 未开始 | 未开始 | 先通过单机门 |

## 当前下一步

M1 已在模拟材料与 Fake providers 范围内完成独立验收并合入 main。M2 阶段 A 固定修复代码 `32da67e9c0280e3dae18fd374e30c925565b0b82` 已通过 Fake-only 独立验收（最终报告提交 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`）；当前进行合并前审查与 PR 合并，随后须在独立 main checkout 重跑自动检查并对关键保存 / 索引 / 任务确认路径冒烟。真实 Feishu、模型、材料与 Keychain 条件虽由用户备妥，但本轮未接入或调用；真实门继续 NOT_RUN。M3–M5 未开始。

## 独立验收报告（旧 SHA）

以下两份报告均固定在 `f364c0122a1a74580009bf9342e6e864df6d975d`，报告范围和观察不同，结论存在差异。它们是各自验收者的原始记录，不互相覆盖，也不能作为 `7b41ca272b14c38a7b6ebf0e9766766749ccf001` 的验收结果：

- [2026-10-09-M1-f364c01.md](../quality/reports/2026-10-09-M1-f364c01.md)：C08/C10 FAIL（P1）；C03/C06/C13/C14 未整体验证；自动测试 67 passed。
- [2026-10-09-M1.1-M1.5-f364c01.md](../quality/reports/2026-10-09-M1.1-M1.5-f364c01.md)：C05/C06/C13 FAIL（P1）；C03/C07/C11/C12/C14 未整体验证；C08/C10 PASS；自动测试 67 passed。

两份报告均只用合成材料和 Fake providers，未运行真实模型、飞书写入、真实样板、五日试用或双机验收。修复代码加入了对应整改和自测证据；仍须对新固定 SHA 独立复验，不能据此标记 QA 通过。

## 独立数据 / 外部门

- G-SAMPLE：场地与酒店真实内容未整组确认；允许通用编码，初始化真实样板前需专门 grillme。
- G-MODELS：未调用真实模型；需用户明确选择材料、调用范围和凭据配置。
- G-FEISHU：未核实真实新权限，未创建真实测试任务；外部写须指定测试动作。
- G-SINGLE：单机全流程与五个实际工作日尚未开始。
- G-DUAL：双机正常往返与接续尚未开始。

## M1 切片记录

| 任务 | 实施状态 | 实现代码 SHA | 检查 / 覆盖 | 材料边界 | 备注 |
|---|---|---|---|---|---|
| M1.1 DTO、库打开、组织管理 | QA通过（模拟范围；最终矩阵见独立报告） | `005e7a4`（本地提交） | 原始切片自测：32 passed；最终独立验收及最终树检查结果见下方报告。 | 合成线、项目和页面；没有真实业务内容或外部调用 | 切片记录保留其当时的命令与限制；最终 M1 结论以固定 SHA 的独立报告为准。 |
| M1.2 可靠本地写入与用户确认 | QA通过（模拟范围；最终矩阵见独立报告） | `ce650ba0516b36753aeb94b246cdc1714a8901e8` | 原始切片自测：50 passed；最终独立验收及最终树检查结果见下方报告。 | 临时隔离库与合成事实；无真实 provider / 飞书动作 | 原始切片记录保留其当时的覆盖范围；最终结论以固定 SHA 的独立报告为准。 |
| M1.3 来源、随手记录和多稿整理 | QA通过（模拟范围；最终矩阵见独立报告） | `4a1fc293bbc6520cb6819cbc1902f53841cc6fea` | 原始切片自测：59 passed；最终独立验收及最终树检查结果见下方报告。 | 临时隔离库、合成文本与 FakeLLM；无真实模型或飞书调用 | 最终 C05 来源状态与重复整理复验见独立报告。 |
| M1.4 增量索引、问答与引用门禁 | QA通过（模拟范围；最终矩阵见独立报告） | `0aae5a2718a792b7e9b35afaf401987ed1d9ccaa` | 原始切片自测：64 passed；最终独立验收及最终树检查结果见下方报告。 | SQLite 位于隔离 profile；Fake embedding / rerank / answer，无网络模型或费用 | 跨阶段引用场景的 M1 范围与未测边界按独立报告记录。 |
| M1.5 WebUI 与本地运行壳 | QA通过（模拟范围；最终矩阵见独立报告） | `f364c0122a1a74580009bf9342e6e864df6d975d` | 原始切片自测：67 passed；最终浏览器及壳复演结果见最终独立报告和后续修复记录。 | 临时合成工作库与 Fake providers；无真实材料、模型或飞书调用 | 原始观察按当时状态保留；后续开发壳生命周期问题已修复并由 QA 复验。DMG 未做。 |
| M1 QA 修复与补充证据 | QA通过（模拟范围；最终矩阵见独立报告） | `f349fe6cb5da86c3fdafff11738e2a55335d8874` | 受测代码与最终树检查结果见独立报告；开发者早期 `7b41ca2` 自测记录保留在下方及 DEV 报告。 | 仅隔离合成内容与 Fake providers；无真实业务材料、模型或飞书调用 | C06 用户先选定一个项目后生成多稿；不做自动跨项目分流。独立复验关闭 C03 P1，保留 1 个 P2。M3 历史会话 / 旧引用 UI、M4 打包 / DMG 及真实外部门仍未测。 |

### 本轮 M1 收口候选（固定代码 SHA `73ec81a06f2557c006f98ff88fa81b08d14ef315`）

| 任务 | 实施状态 | 实现代码 SHA | 检查 / 覆盖 | 材料边界 | 备注 |
|---|---|---|---|---|---|
| C05 来源状态与重复整理修复 | QA通过（模拟范围） | `4939abc`，包含于最终受测候选 `f349fe6` | `uv run pytest -q`：77 passed；来源状态覆盖 pending / processing / reviewing / completed / failed / cancelled、部分确认、全部确认、失败显式重试与完成后显式重新处理；真实 UI 显示多稿审核中与完成状态。 | FakeLLM 与独立模拟工作库 / profile | QA 确认新 operation ID 不能绕过在途 / 待审门禁，失败或完成后的重处理须明确操作。 |
| C07 冲突最终正文 | QA通过（模拟范围） | `4939abc`，包含于最终受测候选 `f349fe6` | 测试覆盖选择 / 明确未决写入正式正文；未决明确为非确定事实；前端显示预期最终处理结果；见最终 QA 案例矩阵。 | FakeLLM 与隔离工作库 | 真实冲突方案、样板质量仍待真实外部门。 |
| 本地运行壳身份 / 清理 | QA通过（M1 开发壳范围） | `73ec81a`，包含于最终受测候选 `f349fe6` | 独立端口 / profile、防止误连、端口冲突不误杀、正常 Quit、关闭最后窗口及 Ctrl+C 清理都在隔离环境验证。 | 单独端口与模拟 profile / 工作库 | 不代表 DMG、干净机器安装或发布验收。 |
| 全量 M1 DEV 检查 | QA通过（模拟范围） | `f349fe6cb5da86c3fdafff11738e2a55335d8874` | 固定候选与最终 main 树上的后端、前端、OpenAPI、类型、lint、构建及 Swift 检查结果见 [最新交接](../handoff/LATEST-IMPLEMENTATION.md) 和 [独立复验报告](../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。 | 全部模拟与 Fake | 保留 1 条 Starlette/httpx 弃用提示和 3 条既有 frontend effect lint 警告；这不代表真实外部门通过。 |

### C03 界面补修候选（当前固定代码 SHA `f349fe6cb5da86c3fdafff11738e2a55335d8874`）

| 任务 | 实施状态 | 实现代码 SHA | 检查 / 覆盖 | 材料边界 | 备注 |
|---|---|---|---|---|---|
| C03 目录和页面结构 UI | QA通过（模拟范围） | `f349fe6cb5da86c3fdafff11738e2a55335d8874` | 真实浏览器覆盖稳定 ID 改名、显式链接确认、跨项目移动与入站链接修复、归档知识检索 / 恢复、非空项目和主线删除拒绝。 | QA 独立 workspace/profile + Fake provider | 首轮 `73ec81a` 的 C03 FAIL/P1 已关闭。保留 1 个 P2：两条非空删除拒绝提示为英文，后续 UI 本地化安排见 QA 报告。 |
| M1 自动检查与矩阵 | QA通过（模拟范围） | `f349fe6cb5da86c3fdafff11738e2a55335d8874` | 后端 77 passed；前端 10 passed；ruff / format、mypy、lock、uv build、OpenAPI 类型生成、前端 typecheck / lint / build 通过；Swift 在父 SHA 通过且 f349 无 native 差异。逐项结果见 [独立复验报告](../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。 | Fake providers 与模拟内容 | P0/P1=0；1 Starlette/httpx deprecation 与 3 条 React effect lint warning 不影响命令退出。M2–M5 和真实外部门未测。 |

### main 合并与最终树检查

- PR [#1](https://github.com/yifeng93/SummitEverything/pull/1) 以 merge commit `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa` 合并。远端 `main` 包含独立复验固定代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 与两份 QA 报告。
- 在合并后的独立 main checkout 完成最终复跑：后端 77 passed；前端 10 passed；OpenAPI 类型生成、typecheck、lint、production build、ruff check / format、mypy、lock check、uv build、Swift build 均退出 0。未发现实现树差异。保留 1 条 Starlette/httpx deprecation 与 3 条既有 React effect lint warning。
- 独立报告将两条非空删除拒绝提示仍为英文记为 P2，具体影响与后续本地化安排见 QA 报告；该项不阻断 M1。

真实业务样板、真实模型、飞书、五日实际工作及双机仍由各自授权门控制；执行者不填写 QA 通过。

## 更新格式

每个任务记录：任务 ID、实施状态、代码 SHA、检查命令与结果、相关验收案例 ID、真实 / 模拟范围、已知缺陷、下一步。

allowed 状态为 未开始 / 进行中 / DEV完成待验收 / 验收未通过 / QA通过 / 真实门待完成 / 完成。不能将“已交接”“mock 全绿”填写为 QA通过或实际交付完成。

## M2.1 飞书授权、材料与日历

最终整体结论及固定 SHA 的执行者证据见 [M2 DEV 报告](../quality/reports/2026-10-10-M2-DEV.md)。M2.1、M2.2、M2.3 均为 DEV完成待验收，不因自动检查或浏览器复演标成 QA通过。

- 状态：DEV完成待验收（仅 Fake 模拟范围）；代码 `e4f382956ab1beb381ab75ed5b1fab22c79bd682`、UI / 契约 `72612e641dd00a34c71f8424adbbf3b622309891`。
- 覆盖 C15、日历读流程与 OAuth 本机会话安全门；26 个新增真实路由 / 文件事务测试、完整后端 103 passed、前端 13 passed，ruff / format / mypy 与前端类型生成 / typecheck / lint / build 均退出 0。保留既有 1 条 Starlette 弃用与 3 条 React effect 警告；无新增警告。
- 合成工作库、FakeFeishu / 内存凭据；真实飞书登录 / scope / 原件 / 任务写、真实模型、钥匙串 / DMG、独立 QA 和真实浏览器跨阶段复演不在此自动检查结果内。
- 精确命令、红绿证据、文件清单、设计与未测边界见 [M2.1 任务报告](../quality/reports/2026-10-09-M2.1-DEV.md)。下一步由主执行会话复核本切片并推进 M2.2；本切片未实现任务动作。

### M2.1 首轮审查修正

固定修正代码 `cef2d4036b0579525c32d5746911ebf591c56a8b`：保留注册 callback 的不同端口目的地及窄 CORS 边界；来源文件名验证共享 writer 规则，坏项不阻断其余导入；过期授权与缺权限的 UI 状态分开；增加 app_id / AppCredentials / 独立合成秘密存储接口。DEV 状态仍为待验收，Fake only；无真实账户适配器、凭据入口或 OS Keychain 权限流。后端 107 passed（Feishu 30）、前端 18 passed，ruff / format / mypy 与前端 types / typecheck / lint / build 退出 0，仅保留既有警告；详细红绿和命令结果见 M2.1 DEV 报告。没有修改审查者证据。


## M2.2 正式任务与独立动作

- 状态：DEV完成待验收，Fake 模拟范围；基线候选 `a7f76e4d188dad607ac069047e76ffaa3135707d`，审查修复见 `c552d143f051efe13ebfcdd29815e776147794aa`。未启动 M3–M5、未 push / PR。
- C16–C18：19 个新增真实 API / 文件 / 锁 / writer / 子进程测试，10 个 TodayView / TasksPanel 组件测试；完整后端126 passed（保留1既有弃用warning）、前端28 passed，ruff / format / mypy / lock / uv build / OpenAPI / typecheck / lint / web build退出0（lint保留3既有warning）。
- 隔离 IAB 真实浏览器创建（无日期）及完成均经审阅、独立确认、另行执行、provider刷新；控制台warn/error0。断流、并发、子进程及跨月由服务测试覆盖。非独立QA。
- 本地 receipt 保留确切意图 / 证据，不维护本地正式任务库；Fake远端在库/profile外。原候选关联兼容，知识确认与进度分开。全天真实timestamp规则 / Fake结果查询的真实等价物仍未核证，不声称真实协议通过。实际账户 / 凭据 / 任务均未调用。
- 详细提交、红绿命令、请求映射、文件与concerns见 [M2.2任务报告](../../.superpowers/sdd/2026-10-09-summit-everything-v1/task-M2.2-report.md)。M2.2 当前等待独立 QA；后续 M2.3 开发记录见下节。

M2.2 独立审查 P2 追加修复：`UserOutcome.evidence` 现在去除首尾空白并拒绝无实质内容，API 回归验证拒绝请求后 action 仍为 unknown；红测初次以 200 接受空白证据，修复后该用例通过。单独代码提交 `c552d143f051efe13ebfcdd29815e776147794aa`；动作集成测试 19 passed，mypy 通过。详细追加证据见 [M2.2 review fix](../quality/reports/2026-10-10-M2.2-review-fix.md)。

## M2.3 日志、思考与项目概览

- 状态：DEV完成待验收（合成工作库 / FakeLLM）；固定代码 `ee1c727412ee1a9a9ea787bb8bec8e990cea26b7`。M2.2 独立 P2 修复随后作为单独提交 `c552d143f051efe13ebfcdd29815e776147794aa`，没有混入 M2.3 代码提交。
- 工作日志 / 思考复用 PageWriter；workspace+operation 派生稳定页面 ID，同请求重试重放、改正文 409；新增并发和 app restart 模拟丢响应回放。日志入口支持无关联、仅主线、主线+项目。AI 仅显式调用 FakeLLM，建议保持独立可编辑；普通保存和列表刷新零调用，取消 / 超时失败不改已存正文。
- 项目概览使用预分配 overview_id，只有用户显式创建；更新提交 expected content hash，旧版本 409。目录可重开导航，知识保存不会写入项目进度字段。
- 后端新集成 9 项及 PageWriter / intake / writer 回归合计 37 passed；UI 组件 6 passed；ruff / format / mypy、OpenAPI Types、前端 typecheck / build 通过。lint 保留原有三条 React effect 警告；1 条 Starlette/httpx deprecation。浏览器开发者复演记录在 [M2.3 DEV 报告](../quality/reports/2026-10-10-M2.3-DEV.md)。无独立 QA。
- 真实模型、业务材料、飞书账户 / scopes / 读写、真实任务副作用、Keychain、DMG、M3–M5 与独立 QA 均未运行。
