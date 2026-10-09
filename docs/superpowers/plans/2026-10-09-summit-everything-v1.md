# SummitEverything v1 Implementation Plan

> 给 agent：按 executing-plans 的逐任务方式执行。用户将在另一聊天使用独立 Luna 验收；不要自动创建聊天或假设已经有人验收。当前已获准用隔离模拟材料直接编码。

**Goal:** 在一个可安装的 Mac 应用中完成可信工作知识积累、检索问答和飞书日常工作。

**Architecture:** 单一 FastAPI 后端与 React WebUI，薄 macOS 壳；普通 Markdown / JSON 业务状态可迁移，SQLite / 会话 / 记忆 / 凭据留本机。

**Tech Stack:** Python 3.12+、FastAPI / Pydantic、React / TypeScript / Vite、SQLite / NumPy、Swift / WKWebView、uv / lockfiles。

**Spec:** [产品规格](../../product/PRODUCT-SPEC.md)、[工作库契约](../../contracts/WORKSPACE-v1.md)、[API](../../contracts/API-v1.md)。

## 全局执行规则与验收门

当前 Foundation 只建立共同信任门禁。最早未实施任务为 M1.1；既有代码不是应用原型。

每任务顺序：读输入契约 → 添加指定反例并实际看失败 → 最小实现 → 跑任务测试及已有相关检查 → 小逻辑提交 → 更新 PROGRESS。测试必须命中实际行为，不能 mock 掉整个服务；界面行为用真实浏览器测试。

当前 Python 通用检查：

~~~sh
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
~~~

新增依赖先核对官方协议 / API，更新 lock。M1 建立 web/package.json 中 dev、build、test、typecheck 脚本，验收再使用实际 npm 命令；M4 建立打包脚本。不能引用不存在的命令作为通过证据。

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

文件：domain/models.py、workspace/manifest.py、workspace/reader.py、workspace/writer.py、workspace/transactions.py、api/app.py、api/routes/workspaces.py；测试 tests/contract/test_workspace_api.py。

输入：WORKSPACE §1–4、API 基础对象、现有 content.py。输出：WorkspaceContext、PageSnapshot、line / project CRUD 和正式页读取。

- [ ] 创建 Pydantic DTO、FastAPI 本机会话认证和错误处理，保留原始 hash 元数据与未知合法字段。
- [ ] 测试：旧库不能静默初始化；缺 token 不写；重复 ID / 路径逃逸 / 归属不一致拒绝；名称变更 ID 不变；非空删除拒绝。
- [ ] 实现 manifest 及注册表、目录读取和初始化；工作库与本地 profile 分开。
- [ ] 组织管理写入先建立最小共用 WorkspaceWriter / 事务路径，遵守意图、身份锁和恢复契约；M1.2 在同一路径扩展页面确认，不另起一套落盘。
- [ ] 验证临时库独立打开、线 / 项目增改归档，OpenAPI 类型可生成；当前骨架测试持续通过。

### M1.2：可靠本地写入与用户确认

文件：workspace/transactions.py、workspace/writer.py、intake/review.py；测试 tests/integration/test_workspace_mutations.py。

输出：WorkspaceWriter.apply(operation_id, expected_versions, changes) → MutationResult；PageWriter 支持新增、更新、外部编辑确认和直接撰写。

- [ ] 测试：基准被外部改动不能覆盖；相同意图重试一次生效，不同 payload 拒绝；写到一半失败后恢复；未批准不产生正式页。
- [ ] 实现本地身份锁、意图认领、完整 changed_paths、同目录原子替换和 journal。
- [ ] 用户确认后计算证明；直接撰写保存复用同一写路径；仅正文明确保存产生知识，不猜业务进度。
- [ ] 验证链接维护、移动恢复、来源 / 稿件无法伪造通过、批准后的旧缓存仍不可用。

### M1.3：来源、随手记录和多稿整理

文件：intake/sources.py、intake/service.py、integrations/llm.py、api/routes/intake.py、api/routes/review.py；测试 tests/integration/test_intake_review.py。

输入：选定 txt/md / 粘贴与 item_ids。输出：SourceRecord、完整 Draft 列表、独立 Action 候选。

- [ ] FakeLLM 在网络适配层提供完整的合法、多项目、冲突、malformed / timeout 响应。
- [ ] 测试：保存 / 列表零模型调用；导入保存原字节；多份稿部分确认；未处理重要冲突阻止确认，明确未决允许确认；取消保留来源。
- [ ] 实现任务执行与本地恢复状态，输出 schema 不接受 approval、任意路径或执行命令。
- [ ] 提供完整新稿、差异和来源；稿件编辑只改稿；明确按钮才调用模型。

### M1.4：增量索引、基本问答与引用

文件：retrieval/chunking.py、retrieval/index.py、retrieval/store.py、retrieval/query.py、integrations/embedding.py、integrations/rerank.py；测试 tests/integration/test_qualified_retrieval.py。

输入：当前 PageSnapshot、model fingerprint。输出：本机 SQLite 索引、Query Answer 与版本引用。

- [ ] 按复用地图吸收 SK 分块 / SQLite / 混合召回；重写所有旧目录与 type 判断。
- [ ] 测试：原件与无批准页零召回；外部修改立即阻止旧片段；新版本批准后旧 chunk 仍拒绝；邻页及引用同样受检；不变分块不重复嵌入。
- [ ] 实现显式首次 / full / model_change 计划和费用估计，批准变化自动增量；不同 fingerprint 不混用，重建失败不破坏旧代。
- [ ] Fake embedding / rerank / answer 完成可复验闭环；真实 provider adapter 按独立协议实现，真实质量测试另列授权门。

### M1.5：真实 WebUI 与首个可运行应用

文件：web/、native/、api/routes/query.py；测试 web 的浏览器套件及 tests/integration/test_app_lifecycle.py。

默认导航：今日（随手记、待处理、日志 / 思考及日历待办入口）、项目、知识问答、设置。未实现功能明确未配置 / 未实现，不显示假的数据或成功状态。

- [ ] 建立 React / TS / Vite 与生成的 API 类型，提供实际 dev / build / test / typecheck 命令。
- [ ] 做线 / 项目 / 页面浏览、导入、待处理、多稿完整审阅、差异、冲突处理、引用打开与外部编辑重新确认。
- [ ] 基本问答 SSE 与取消：seq、有终态、错误可恢复；页面导航不丢待审编辑，不重复操作。
- [ ] 薄原生壳能启动唯一服务、注入本机会话、选择目录、显示 readiness、关闭自己拥有的进程。使用模拟 provider 的内部应用可以运行，未配置云模型明确显示。

**M1 DEV 门：** 用隔离库从 UI 新建线 / 项目、导入文字、生成多稿、部分确认、更新权威页、增量索引、问答点击引用；外部修改之后旧内容不再作为依据。构建 / 类型 / 浏览器测试通过。提交固定 SHA 和复演步骤给 QA；模拟链路不记真实模型质量通过。

## M2 — 飞书与独立日常入口

### M2.1：飞书授权、材料和日历

文件：integrations/feishu/{auth,materials,calendar}.py、api/routes/feishu.py、web 对应功能。

- [ ] 复用 SWB OAuth / session 经验，长期秘密交钥匙串，state 绑定发起会话；scope、redirect 和 endpoint 用实际注册配置。
- [ ] 测试完整响应、过期 token、拒绝、分页、逐字稿文件内容、只获取被选材料；列表不调模型。
- [ ] 实现可见材料列表 → 明确选择 → 来源 / item；导入不隐式生成或批准正式页。
- [ ] 账户准备好后验证真实 scope、列表和正文读取；缺失权限给具体指引，保留手动文字入口。

### M2.2：正式任务与独立 action

文件：integrations/feishu/tasks.py、intake/actions.py、workspace/action_receipts.py、api/routes/actions.py。

- [ ] 测试：未确认零外部写、重复执行同意图只建一次、不同 payload 冲突、HTTP 超时后不重 POST、完成态重复完成成功。
- [ ] 实现 action ledger / receipt、原子认领、确认与运行、核实 unknown，以及创建 / 编辑 / 完成。
- [ ] UI 独立任务确认卡和日期输入，不猜日期、不用知识确认代替 task / project_progress 确认。
- [ ] 使用模拟 provider 验证跨重启 / 月归档后幂等。真实外部写只用用户明确指定的测试任务。

### M2.3：工作日志、思考与项目总览

文件：intake/journal.py、api/routes/journal.py、web 对应入口。

- [ ] 测试：日志 / 思考不绑项目可保存，关联线 / 项目也可；直接确认落盘使用同一 PageWriter；不调模型；项目进度不被自动改。
- [ ] 提供自由正文、可选关联和显式 AI 辅助；取消辅助不影响本地已保存记录。
- [ ] 项目总览业务内容可确认，导航从目录展示；具体事实引用子页，不生成一份重复总库。

**M2 DEV 门：** 模拟飞书日常流、授权失败与 unknown 防重通过；单独列真实 read / write 的结果。QA 核对没有本地第二套正式待办。

## M3 — 完整问答与连续工作

### M3.1：三类问答与本地角色 / 历史 / 记忆

文件：retrieval/planner.py、retrieval/answer.py、local/{conversations,roles,memory}.py、对应 API / web。

- [ ] 事实、跨材料汇总比较和工作方案有独立测试问题；缺资料时不补造，方案区分已有依据与推断。
- [ ] 实现本机每库历史、角色 CRUD 和预算；库切换不串上下文，角色不能改变批准 / 证据 / 工具权限。
- [ ] 记忆候选只能来自用户明确表达，用户接受 / 编辑才活跃；源材料和 assistant 回答不能自己生效。
- [ ] 测试两套本地 profile 指向同库时历史 / 角色 / 记忆独立；答案不自动写知识；引用绑定当前版本，旧历史引用显示已更新。

### M3.2：状态可迁移与归档压缩

文件：workspace/state.py、workspace/archives.py、local/logging.py。

- [ ] 测试另一 profile 读取同一待审流程，部分完成状态正确，未知调用不会自动重发。
- [ ] 待处理一份当前记录，完成按月归档；完成 receipt 可查，unknown 不删；压缩中断可恢复。
- [ ] 验证同步区没有 SQLite / WAL、凭据、历史、角色、记忆和诊断日志。模拟大量流程，报告文件数量随流程 / 月份变化的实际结果。

**M3 DEV 门：** 完整 v1 业务界面和模拟链路均可用，准备真实样板 / 外部能力质量验收。历史范围、归档和跨材料方案均有引用与效力标记。

## M4 — 单机交付与实际试用

### M4.1：包、配置和生命周期

文件：scripts/build-macos-app.sh、scripts/release-macos.sh、native 生命周期模块、CI 配置。

- [ ] 依赖、测试、WebUI 构建与打包形成明确命令；包内身份、前端指纹和依赖清单真实可复核。
- [ ] 测试无需系统 Python / Node / Docker，启动 / 退出 / 重启、端口占用、断流 /取消、钥匙串失败及配置反馈。
- [ ] UI 服务不监听外网，Markdown 安全渲染，来源中的命令不变成工具动作。内部包不覆盖旧 App。

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
