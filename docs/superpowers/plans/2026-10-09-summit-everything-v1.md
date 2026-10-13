# SummitEverything v1 Implementation Plan

**Goal:** 在一个可安装的 Mac 应用中完成可信工作知识积累、检索问答和飞书日常工作。

**Architecture:** 单一 FastAPI 后端与 React WebUI，薄 macOS 壳；普通 Markdown / JSON 业务状态可迁移，SQLite / 会话 / 记忆 / 凭据留本机。

**Tech Stack:** Python 3.12+、FastAPI / Pydantic、React / TypeScript / Vite、SQLite / NumPy、Swift / WKWebView、uv / lockfiles。

**Spec:** [产品规格](../../product/PRODUCT-SPEC.md)、[工作库契约](../../contracts/WORKSPACE-v1.md)、[API](../../contracts/API-v1.md)。

## 当前阶段记录（2026-10-13）

M3 三个离线功能包与离线模拟正式验收均已通过；用户批准的产品合并点为 `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`。`879c82464903a7aed91b30955d7355064fa85088` 是本轮清理前 main 基线，不是本轮维护验收 SHA。固定 C19 源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 的独立 QA 与合并后复验见[报告索引](../../quality/reports/README.md)。本计划中的验收要求保持有效；各轮旧状态只描述其固定 SHA。

2026-10-13 用户新增授权离线 M4.1 Internal App/DMG 的连续开发、自测、最终 clean SHA 重建及交独立 QA；此授权不包含 M4.2 真实验收或用户安装、Developer ID/公证、五日试用、M5 双机与发布。M4.1 DEV 状态见[DEV 报告](../../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)，Sol 的独立 QA 与阶段门仍待执行。真实模型质量、Feishu / 业务材料、OS Keychain 均 NOT_RUN；runtime 元数据 UNVERIFIED。

## 全局执行规则与验收门

B/C 是衔接真实 adapter 与受控真实验收的补充顺序，不改写 M0–M5，也不删除任何 MUST。Stage B adapter 已实现，模拟 HTTP / 合成凭据范围经离线 QA；真实账户 / 协议、OS Keychain 与 R03 质量仍未验收。Stage C 的真实连接和质量验收尚未启动，必须逐项取得真实操作授权并验证具体协议和模型质量。M4.1 的用户授权仅覆盖离线 Internal App/DMG 工程实现与开发者自测；不能提前标记 M4.2、真实样板、五日或双机完成。下方 M3.1 / M3.2 功能清单现均完成并由 M3 离线正式验收及固定 merge QA 收口；历史逐项 DEV / QA 记录仍只适用于各自 SHA。当前状态见本文顶部与 [M3 验收索引](../../quality/reports/README.md)。

当前 Sol / Luna 开发与验收分工见 [ADR 0008](../../decisions/0008-sol-luna-development-workflow.md)；这里不重复工作流全文。

每任务顺序：读输入契约 → 添加指定反例并实际看失败 → 最小实现 → 跑任务测试及已有相关检查 → 小逻辑提交 → 更新 PROGRESS。测试必须命中实际行为，不能 mock 掉整个服务；界面行为由独立 QA 用真实浏览器检查。

当前 Python 通用检查：

~~~sh
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
~~~

新增依赖先核对官方协议 / API，更新 lock。M1 已建立 web/package.json 的实际脚本，前端验收使用 README 命令；M4 建立打包脚本。不能引用不存在的命令作为通过证据。

两个门分开：DEV 是实现者自测与交接；QA 是另一 Luna 对固定提交独立复验。M4 / M5 另有真实人工门。无凭据只会使相应外部场景未测，不阻塞模拟实现；未测不得成为通过。

## M0 — 已建立的框架

- [x] 产品规格、ADR、模块与来源基线。
- [x] 内容 canonical hash、来源 / 稿件排除、当前版本与缓存版本门禁。
- [x] 独立 hash 样例及关键反例，最小 Python 项目与 lock。
- [x] 完整 v1 实施 / 验收手册与提示词。
- [ ] 真实样板整组业务确认（独立数据门，可在后续合适阶段完成）。

Foundation 仅自检，不标 M1 / 真实外部能力通过。

## M1 — 首个本地知识闭环

### M1.1：DTO、库打开、组织管理

文件：domain/models.py、domain/content.py、workspace/manifest.py、workspace/reader.py、workspace/writer.py、workspace/transactions.py、api/app.py（工作区路由）；测试 tests/contract/test_workspace_api.py。DTO 位于 `domain/models.py`；工作区路由未单独拆成 `api/routes/workspaces.py`。

输入：WORKSPACE §1–4、API 基础对象、现有 content.py。输出：WorkspaceContext、PageSnapshot、line / project CRUD 和正式页读取。

- [x] 创建 Pydantic DTO、FastAPI 本机会话认证和错误处理，保留原始 hash 元数据与未知合法字段。
- [x] 测试：旧库不能静默初始化；缺 token 不写；重复 ID / 路径逃逸 / 归属不一致拒绝；名称变更 ID 不变；非空删除拒绝。
- [x] 实现 manifest 及注册表、目录读取和初始化；工作库与本地 profile 分开。
- [x] 组织管理写入先建立最小共用 WorkspaceWriter / 事务路径，遵守意图、身份锁和恢复契约；M1.2 在同一路径扩展页面确认，不另起一套落盘。
- [x] 验证临时库独立打开、线 / 项目增改归档，OpenAPI 类型可生成；当前骨架测试持续通过。

### M1.2：可靠本地写入与用户确认

文件：workspace/transactions.py、workspace/writer.py、intake/review.py；测试 tests/integration/test_workspace_mutations.py。

输出：WorkspaceWriter.apply(operation_id, expected_versions, changes) → MutationResult；PageWriter 支持新增、更新、外部编辑确认和直接撰写。

- [x] 测试：基准被外部改动不能覆盖；相同意图重试一次生效，不同 payload 拒绝；写到一半失败后恢复；未批准不产生正式页。
- [x] 实现本地身份锁、意图认领、完整 changed_paths、同目录原子替换和 journal。
- [x] 用户确认后计算证明；直接撰写保存复用同一写路径；仅正文明确保存产生知识，不猜业务进度。
- [x] 验证链接维护、移动恢复、来源 / 稿件无法伪造通过、批准后的旧缓存仍不可用。

### M1.3：来源、随手记录和多稿整理

文件：intake/sources.py、intake/review.py、integrations/llm.py、api/app.py（整理与审阅路由）；测试 tests/integration/test_intake_review.py。整理编排由现有 intake 模块承担，没有单独的 intake/service.py。

输入：选定 txt/md / 粘贴与 item_ids。输出：SourceRecord、完整 Draft 列表、独立 Action 候选。

- [x] FakeLLM 在网络适配层提供完整的合法、多项目、冲突、malformed / timeout 响应。
- [x] 测试：保存 / 列表零模型调用；导入保存原字节；多份稿部分确认；未处理重要冲突阻止确认，明确未决允许确认；取消保留来源。
- [x] 实现任务执行与本地恢复状态，输出 schema 不接受 approval、任意路径或执行命令。
- [x] 提供完整新稿、差异和来源；稿件编辑只改稿；明确按钮才调用模型。

### M1.4：增量索引、基本问答与引用

文件：retrieval/chunking.py、retrieval/store.py、retrieval/query.py、retrieval/planner.py、integrations/embedding.py、integrations/rerank.py、api/app.py；测试 tests/integration/test_qualified_retrieval.py。增量索引与问答编排位于现有 query 模块，没有单独的 retrieval/index.py。

输入：当前 PageSnapshot、model fingerprint。输出：本机 SQLite 索引、Query Answer 与版本引用。

- [x] 按复用地图吸收 SK 分块 / SQLite / 混合召回；重写所有旧目录与 type 判断。
- [x] 测试：原件与无批准页零召回；外部修改立即阻止旧片段；新版本批准后旧 chunk 仍拒绝；邻页及引用同样受检；不变分块不重复嵌入。
- [x] 实现显式首次 / full / model_change 计划和费用估计，批准变化自动增量；不同 fingerprint 不混用，重建失败不破坏旧代。
- [x] Fake embedding / rerank / answer 完成可复验闭环。
- [ ] 真实 provider adapter 按独立协议实现；真实质量测试另列授权门。

### M1.5：真实 WebUI 与首个可运行应用

文件：web/、native/、api/app.py（问答路由）；测试 web 的浏览器套件及 tests/integration/test_app_lifecycle.py。API query 路由没有单独拆成 `api/routes/query.py`。

默认导航：今日（随手记、待处理、日志 / 思考及日历待办入口）、项目、知识问答、设置。未实现功能明确未配置 / 未实现，不显示假的数据或成功状态。

- [x] 建立 React / TS / Vite 与生成的 API 类型，提供实际 dev / build / test / typecheck 命令。
- [x] 做线 / 项目 / 页面浏览、导入、待处理、多稿完整审阅、差异、冲突处理、引用打开与外部编辑重新确认。
- [x] 基本问答 SSE 与取消：seq、有终态、错误可恢复；页面导航不丢待审编辑，不重复操作。
- [x] 薄原生壳能启动唯一服务、注入本机会话、选择目录、显示 readiness、关闭自己拥有的进程。使用模拟 provider 的内部应用可以运行，未配置云模型明确显示。

**M1 DEV 门：** 用隔离库从 UI 新建线 / 项目、导入文字、生成多稿、部分确认、更新权威页、增量索引、问答点击引用；外部修改之后旧内容不再作为依据。构建 / 类型 / 浏览器测试通过。提交固定 SHA 和复演步骤给 QA；模拟链路不记真实模型质量通过。

**当前结果：** M1 DEV 门与模拟范围独立 QA 均通过，固定受测代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 已合入 main。见 [独立 QA 报告](../../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。真实模型质量、真实飞书、DMG 与实际试用不包含在此 PASS 中。

## M2 — 飞书与独立日常入口

### M2.1：飞书授权、材料和日历

文件：integrations/feishu/{provider,fake,service,http}.py、api/app.py、web/src/components/FeishuPanel.tsx。Fake、service 与 HTTP adapter 按现有边界组织，不使用早期拟定的 auth/materials/calendar 文件拆分。

- [x] Fake 范围落实 OAuth / session 边界，state 绑定发起会话；scope、redirect 和 endpoint 使用配置值。Fake 流程使用进程内凭据；真实 Keychain adapter、设置入口与 fail-closed 实现已存在，但真实 OS Keychain 验收仍为 NOT_RUN。
- [x] 测试完整响应、过期 token、拒绝、分页、逐字稿文件内容、只获取被选材料；列表不调模型。
- [x] 实现可见材料列表 → 明确选择 → 来源 / item；导入不隐式生成或批准正式页。
- [ ] 账户准备好后验证真实 scope、列表和正文读取；缺失权限给具体指引，保留手动文字入口。

**M2.1 初始开发记录（阶段 A 独立 QA 后重开）：** Fake 模拟范围的 DEV 检查点曾固定于 `09398fcae597b2478001d40aedf580ea91322c11`；该 SHA 后续发现阶段 A 缺陷，当前修复与 QA 状态见本计划顶部、[进展账本](../../implementation/PROGRESS.md) 和 [最新交接](../../handoff/LATEST-IMPLEMENTATION.md)。真实 OAuth / user scope / 钥匙串配置仍属外部验收门，不因 Fake 开发自测勾选真实账户步骤。

### M2.2：正式任务与独立 action

文件：integrations/feishu/tasks.py、intake/actions.py、workspace/action_receipts.py、api/routes/actions.py。

- [x] 测试：未确认零外部写、重复执行同意图只建一次、不同 payload 冲突、HTTP 超时后不重 POST、完成态重复完成成功。
- [x] 实现 action ledger / receipt、原子认领、确认与运行、核实 unknown，以及创建 / 编辑 / 完成。
- [x] UI 独立任务确认卡和日期输入，不猜日期、不用知识确认代替 task / project_progress 确认。
- [x] 使用模拟 provider 验证跨重启 / 月归档后幂等。真实外部写未测，仍只允许用户明确指定的测试任务。

**M2.2 初始开发记录（阶段 A 独立 QA 后重开）：** 初始代码 `a7f76e4d188dad607ac069047e76ffaa3135707d`，P2 修复 `c552d143f051efe13ebfcdd29815e776147794aa`，当时的整体候选为 `09398fcae597b2478001d40aedf580ea91322c11`；该 SHA 后续发现阶段 A 缺陷。当前修复及新 SHA 独立复验状态见本计划顶部。真实全天 timestamp 规则及真实执行证据查询仍未验证，Fake 映射不得直接用于真实 adapter。

### M2.3：工作日志、思考与项目总览

文件：api/app.py（日志路由）、web/src/components/JournalView.tsx、web/src/components/ProjectsView.tsx；测试 tests/integration/test_journal_overviews.py。该实现没有单独的 intake/journal.py 或 api/routes/journal.py。

- [x] 测试：日志 / 思考不绑项目可保存，关联线 / 项目也可；直接确认落盘使用同一 PageWriter；浏览不调模型；项目进度不被自动改。
- [x] 提供自由正文、可选关联和显式 AI 辅助；建议独立可编辑 / 可取消，不自动覆盖已保存内容。
- [x] 项目总览用稳定 overview_id 经明确确认创建 / 版本保护更新，目录可重开导航；具体事实可链接子页，不生成重复总库。

M2.3 功能提交 `ee1c727412ee1a9a9ea787bb8bec8e990cea26b7`；M2 原始候选固定于 `09398fcae597b2478001d40aedf580ea91322c11`。该候选的问题已在阶段 A 修复；固定修复代码 `32da67e9c0280e3dae18fd374e30c925565b0b82` 独立 Fake-only QA、PR #4 合并及合并后核验均通过。原候选与最终复验报告链见[阶段 A QA 报告](../../quality/reports/2026-10-10-M2-stage-a-final-fourth-followup-qa.md)、[合并后核验记录](../../quality/reports/2026-10-10-M2-stage-a-postmerge.md)和最新交接。

**M2 DEV 门（历史开发记录）：** 当时 WebUI Fake 日常流程、任务 unknown 防重与重启恢复通过；原生壳 UI 尚未由执行者完成归属复演。之后阶段 A 独立 QA 已在固定修复代码 `32da67e9c0280e3dae18fd374e30c925565b0b82` 完成 Fake-only 验收，当前合并状态见本计划顶部与最新交接。真实 read / write 仍单独列示。

## M3 — 完整问答与连续工作

### M3.1：三类问答与本地角色 / 历史 / 记忆（离线验收 PASS）

固定源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 已通过全新独立 QA；详见[QA 报告](../../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)与[Sol 门](../../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md)。

文件：retrieval/planner.py、retrieval/query.py、local/{conversations,answer_context,event_log}.py、api/app.py、web/src/components/AskView.tsx。角色与记忆使用现有本地上下文及 API 实现，没有单独的 retrieval/answer.py 或 local/roles.py / memory.py。

- [x] 事实、跨材料汇总比较和工作方案有独立测试问题；缺资料时不补造，方案区分已有依据与推断。
- [x] 实现本机每库历史、角色 CRUD 和预算；库切换不串上下文，角色不能改变批准 / 证据 / 工具权限。
- [x] 记忆候选只能来自用户明确表达，用户接受 / 编辑才活跃；源材料和 assistant 回答不能自己生效。
- [x] 测试两套本地 profile 指向同库时历史 / 角色 / 记忆独立；答案不自动写知识；引用绑定当前版本，旧历史引用显示已更新。

### M3.2：状态可迁移与归档压缩

文件：workspace/state.py、workspace/archives.py、local/event_log.py。包3离线集成PASS，受测源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`；[全新独立QA](../../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md)和[Sol核证](../../quality/reports/2026-10-12-M3-PACKAGE-3-SOL-GATE.md)。

- [x] 另一profile读取待审流程与部分完成稿；活owner、dead owner unknown/no-resend、checkpoint本地恢复、迟到结果CAS、显式reprocess和旧undated版本链验收通过。
- [x] 完成intake items/jobs、capture/mutation/SHA write-intent/Feishu import回执的active+月摘要回放；摘要故障及冲突/损坏/非法桶阻断、unknown保留与原件/完整稿保留验收通过。
- [x] 诊断日志只在本机profile并轮转；120合成流程、四业务月归档及provider重放计数通过；本机两profile存储边界已测，真实双机NOT_RUN。
- [x] README适用检查、固定SHA整包独立QA与双profile真实浏览器短复演通过；首轮C22 lease异常FAIL经自动返工1/2在新SHA关闭，初验报告和失败日志保留。

**M3门：** 包1、包2、包3离线集成PASS；用户批准的离线模拟正式验收已合入 main 并完成固定 merge QA。历史 FAIL 仍保留在各自报告中，只对应当时受测 SHA。真实样板、外部能力、native/DMG、五日试用、双机与发布门仍单独验收，产品规格和完整 MUST 不变。

## M4 — 单机交付与实际试用

### M4.1：包、配置和生命周期

文件：scripts/build-macos-app.sh、scripts/release-macos.sh、native 生命周期模块、CI 配置。

- [x] 实现依赖锁定、强制 WebUI 构建、内部 bundle/DMG 构建和 manifest 身份 / 指纹检查脚本；开发者命令及对应退出码见本轮 DEV 报告。
- [ ] 由独立 QA 固定 SHA 实测无需系统 Python / Node / Docker、完整窗口生命周期、失败 / 延迟 readiness、SSE 与钥匙串故障反馈；Developer 观察仅作交接证据，不代替验收。
- [ ] 由独立 QA 对固定包复验 loopback、Bearer、Markdown、资料命令与旧 App 隔离；Developer 测试项见 DEV 报告，真实安装、签名和公证保持 NOT_RUN。

### M4.2：真实验收门

- [ ] 在用户方便时，专门 grillme 四份场地与酒店来源；最终版与明确未决项整体确认，再由正式路径初始化新库，保留桌面原文件。
- [ ] 建立黄金问题：合同进展、成本分子 / 分母、跨期比较、证据缺失、下一步方案；答案依据由用户确认材料决定，不硬编码先前待审数字。
- [ ] 用户明确选择模型调用与飞书测试动作；核对真实模型整理质量、Qwen 检索 / 重排和真实权限，记录范围与费用。
- [ ] 独立 QA 和用户现场完整流程通过，再连续五个实际工作日试用；关键缺陷修复后复验。没有凭据 / 真实确认时明确标部分完成。

**M4 门：** 截至 M4 应完成的 Must（C01–C28）已验证、无未关闭 P0 / P1，用户确认现场业务结果及五日试用。M5 场景在此之后验收。测试绿、DMG 构建成功均不能单独代替这一门。

## M5 — Studio / Air 往返

- [ ] 同库身份在不同绝对路径打开；各机单独配置凭据和显式首次索引。
- [ ] 停写、确认 OneDrive 完成后切换写端；另一端可继续待审稿和读取最终页，往返更新不丢状态。
- [ ] 两端索引自动追上已批准变化；本地历史 / 角色 / 记忆不随库出现。
- [ ] 隔离自动测试模拟半写、重复 ID、冲突副本、unknown receipt；真实人工做正常往返与中途接续，不用真实库制造破坏性异常。
- [ ] 记录两台包身份、库 ID、批准 / 稿件版本与实际观察；未实测异常仍记未测。

**M5 门：** 正常往返及接续通过，边界说明准确；真实库没有旧 Git 写入、误称云端完成或共享本地状态。

## 每阶段交接

实现者提交代码 / 测试 / 必要契约，取得固定 SHA；再填写 LATEST-IMPLEMENTATION.md，写明阶段、代码 SHA、规格版本、命令结果、UI / 包复演、真实 / 模拟边界、未测项和已知问题。

测试者用该 SHA 的独立 checkout 执行 ACCEPTANCE 对应场景，并提交独立报告 / 缺陷。实现者依据失败复现修复、增补回归测试，再给新 SHA；旧报告保留，不把旧通过结论套给新提交。

只有验收证据能推进阶段状态。样板与凭据门等待期间，推进不依赖它们的模拟实现和维护工作，不静默删掉真实质量门。
