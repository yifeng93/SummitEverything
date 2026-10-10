# 给 LUNA：阶段 B / C 完整执行提示词

以下正文可整段复制给下一个 LUNA。它授权开发、离线检查、独立 QA 和通过验收后的源码整合；真实外部操作须按下述测试门另获用户逐项确认。不要把本提示词当作真实登录、材料传输、收费或任务写入的授权。

---

你是 SummitEverything 的阶段 B / C 执行负责人，使用 LUNA。请完成 B 的实现、离线独立验收与 main 整合，再在用户明确授权的范围内完成 C 的受控真实验收与整合。持续推进已授权工作；需要真实操作授权时，继续不依赖该授权的离线工作。不能自签阶段通过，不能以测试数量推断通过。

## 1. 固定基线与接手

仓库：`/Users/yifengstudio/Documents/GitHub/SummitEverything`。

- Stage A 最终受测修复代码：`30903c4cdf73855af71a201e3edea6c535ee8199`。
- Stage A 收口 main：`117086eb2075726730cd7aa62ea0b61498e96f0c`；随后环境整理提交仅修改文档，不改产品实现、测试或历史证据。
- 从接手时的最新 `origin/main` 建立独立 worktree，记录完整 SHA；确认它包含 `117086eb…`。确认整理后基线的 `src/tests/web/native` 与 `30903c4` 一致。若已出现其他产品改动，先识别并记录受测边界，不能强行重置或照搬旧结论。
- 不在共享 checkout 切分支、改依赖或实现。实现分支使用 `codex/stage-b-real-providers` 或含义相同的新名称；不要复用归档分支、旧 QA profile、端口、工作库或凭据。
- 旧分支已做本地 archive tag / Git bundle 归档，部分带 `.local` QA 证据的目录以 detached 保留。按 `docs/implementation/2026-10-10-STAGE-A-CLEANUP.md` 查证；不清理它们或读取其私有状态。

按 AGENTS.md 顺序读 README、PROGRESS、PRODUCT-SPEC、ARCHITECTURE、WORKSPACE-v1、API-v1、IMPLEMENTER、TESTER、全 v1 计划、ACCEPTANCE；随后读 LATEST-IMPLEMENTATION、报告索引以及 M2 DEV、M2.1/M2.2/M2.3、M2.2 P2、阶段 A 原始 QA、第四轮纠正和恢复 UI / C18 修复复验报告。使用实际代码核对 provider 接口、运行入口与配置，不以历史聊天代替源码。

使用适用的 skills：using-superpowers、planning-and-task-breakdown、api-and-interface-design、source-driven-development、security-and-hardening、incremental-implementation、test-driven-development、git-workflow-and-versioning、browser-testing-with-devtools、verification-before-completion、code-review-and-quality。缺少能力时如实记录，不能编造浏览器、原生或独立 QA 证据。

Stage A 已在 Fake-only 范围收口：C16 恢复 / 并发、C18 回执恢复、C23 无成功证明等必需 UI 已补齐。旧 FAIL、撤回截图和指纹限制继续保留。当前缺少真实 Feishu、LLM / embedding / rerank、生产本地配置和 Keychain adapter。M3 完整会话 / 角色 / 记忆、M4 DMG / 五日、M5 双机仍是独立范围，B/C 不代替这些阶段。

## 2. 权限与不可降低的边界

用户已准备 App ID、App secret、callback、模型、材料和 Keychain，并可参与测试；其值没有写入本提示词或仓库。这表示可安排测试，不表示 adapter 已存在或真实协议已通过。

现在可做：通用代码开发、官方文档研究、隔离合成材料、stub HTTP / Fake-only 测试、专用合成 Keychain 项测试、独立审查与 QA、代码 / 文档提交、推送、PR，以及通过独立验收后的 main 合并。GitHub 整合属于源码操作，报告应与真实业务调用分别计数。优先使用 SSH Git，不改变用户全局配置。

现在不可做：登录真实飞书、读取真实账号或材料、发送真实材料到 provider、调用付费模型、创建 / 修改 / 完成真实 task、读取或覆盖用户已有 Keychain 项。先列目的、数据、目标、范围、费用和停止条件，再由用户在执行前逐项确认。

秘密只能由用户在安全本地输入界面 / Keychain 录入；不得让用户贴在聊天、工单或 Git。不要把秘密放命令行参数、shell history、URL、前端 storage、源码配置、HAR、截图、日志或构建产物。普通非秘密配置与秘密引用分开。真实模式在 Keychain 不可用时失败关闭，不能静默回退内存或明文文件。

保持产品 MUST、契约和原验收要求：正式当前内容才进语料；原件 / 待审 / helper 排除；单一权威事实与主归属；用户确认知识不等于批准任务或项目进度；模型输出不能批准；unknown 动作不自动重发；真实任务事实由飞书返回；内容资格统一调用 `domain/content.py`；工作库无 Git；本地凭据 / 索引 / 历史 / 日志不随 OneDrive 工作库迁移。真实「场地与酒店」仍需专门内容确认，不能自动导入。

## 3. 阶段 B：实现真实适配，离线独立验收

### B1 — 协议与接口冻结

目标：把真实 provider 接到现有业务，而不是另外建立一套 API / UI。

1. 在实现前核对官方最新文档，建立协议 / 能力矩阵：真实 Feishu OAuth、user access token / refresh、精确 scope、材料类型与分页、日历、Task GET/POST/PATCH、完成与清除日期、结果核实；LLM、embedding、rerank 的 endpoint、鉴权、模型 ID、输出 schema、维度、错误与费用。
2. 每项写官方来源、核对日期、接口、请求 / 返回映射、未知项和对应 fixture。不要把 Fake `task_result` 当作真实接口；不要凭记忆认定午夜 timestamp 就是 Task 全天日期规则。
3. 检查旧仓库仅按 REUSE-MAP 的固定模块作参考，不运行或修改旧应用 / vault，不引入旧项目 import。
4. 建立小范围 typed provider / CredentialStore / 配置契约，业务与 Swift、绝对路径、provider HTTP 分离；同步 API / 工作库契约或 ADR，不静默改变产品决议。
5. 需要用户实际 provider、模型 ID、地区、维度或 callback 时，只问非秘密选项。规格中的模型名称只能作待核对候选；未确认账号支持和官方协议的配置不能默认为可用。

验收证据：协议矩阵、接口 / ADR、官方来源和风险列表。停止条件：关键写入 / 日期语义无法证实，相关能力保持禁用或 BLOCKED；继续独立的配置、读取和模型工作，不以猜测填补。

### B2 — 本地配置与 Keychain

目标：用户能在应用内配置 provider 并在重启后安全使用。

- 新增真实 provider 的显式模式和非秘密配置入口；默认 Fake / 离线。更改或保存设置、刷新页面、预览不得触发外部调用。需要外部请求的连接测试属于 C 授权门。
- App secret、模型 key、用户 token / refresh token 通过独立 Keychain adapter 存储；命名空间至少隔离应用 / 本地 profile / 账号 / provider，防止双机和不同库串用。工作库只保存允许共享的业务内容，不保存秘密或本机会话状态。
- WebUI 不回显秘密，API 仅返回配置状态与脱敏错误。处理拒绝、锁定、缺失、更新 / 删除、注销、重启与 token 轮换失败，避免刷新并发和丢失新 token。新测试只使用专用合成 Keychain 项，结束清除自己创建的项，不能查用户原有项。
- 原生能力通过薄桥接供同一 FastAPI / WebUI 使用；开发壳实际 Keychain 路径和浏览器路径都要验证。不能用 Swift build 或 MemoryCredentialStore 证明 Keychain 行为。

可并行：B1 契约确定后，配置 / Keychain 与 HTTP provider 分开实现。汇合条件：统一的配置生命周期、SecretStore 错误契约、运行入口和测试注入已稳定。

### B3 — 真实 Feishu adapter

目标：保留现有审批 / action 状态机与可靠写入，在真实协议层实现 M2 能力。

- OAuth：真正的浏览器授权流程、精确注册 callback、一次性有期限 state 与本次本地会话绑定、拒绝 / 取消 / 错误、code 交换、user token scope、到期刷新与注销。tenant token 不能冒充用户权限；scope 不足应停用对应能力并给用户可理解的原因。
- callback 和访问日志避免泄漏 code / state / token；不向错误 Origin 开放、不缓存秘密响应。真实 OAuth 的跨域 / 跳转应按官方流程验证，不能直接套用 Fake fetch callback 的行为。
- 材料：metadata 检索 / 分页 / 权限边界；只有用户选中项才下载。按正式支持的材料类型获取内容、完整处理分页和部分失败、保存来源字节 / hash 与待审状态；不把材料导入等同于正文确认或自动 LLM 发送。明确哪些类型目前不支持，不能冒充全部 PDF / Word / OCR 已实现。
- 日历：用户指定起止范围、结束不含、IANA 时区、分页、空结果、无权限、过期和错误；禁止静默扩大范围。
- 任务：GET、POST、PATCH 和完成的精确映射；标题、无日期、全天、具体时间 / offset / IANA 时区；编辑仅发送选定字段，明确清空、完成时间和目标 task ID。不要复制 Fake 日期规则到真实 HTTP 层。
- 执行结果核实：写前独立确认，journal / receipt / 崩溃恢复与 unknown/no-resend 保留。用真实响应和可证明的只读查询绑定动作类型、目标、请求字段与实际结果。读取一个同标题任务不是动作成功证明；不能虚构按 client_token 查结果的端点。协议不能证明时保留 unknown 并提供明确独立人工结果流程，不能重发“试一下”。
- 重试只用于证明安全的只读操作；有副作用请求超时 / 回执丢失时不能盲重试。Provider 的幂等支持必须有真实文档与测试依据。

### B4 — 真实 LLM / embedding / rerank

目标：接通当前已实现的整理、日志思考 AI 辅助、检索和 grounded answer 路径，不提前宣称完整 M3。

- LLM adapter：结构化整理 / 辅助输出验证、可编辑待审、取消 / 超时 / 部分失败、注入防护；不授予模型工具批准权限。真正 grounded answer 需调用所选真实 LLM，引用只来自合格当前页面，拒绝 stale / 越界来源；不能把现有摘录拼接说成真实模型问答。
- embedding：维度、模型 fingerprint、批量与错误、索引代际 / 原子切换、首次 / 重建确认、改模型后旧向量失效或明确迁移；已批准内容的增量更新沿用现有产品约定。不能在切换配置时偷偷收费重建。
- rerank：真实请求 / 响应排序映射、结果索引边界、分数 / 异常校验；无效响应、超时和禁用状态有明确错误或可解释降级，不能显示已重排却实际跳过。
- 保持本地索引和配置隔离；外发最少数据，检索候选只包含经确认当前正文。真实材料内容不进入 Git，诊断只保存必要脱敏字段。

可并行：B2/B3/B4 在接口冻结后可分别推进。模型质量、账号权限和真实数据适配留到 C；离线协议 fixture 能证明 mapping，不能证明真实 provider 可用。

### B5 — 自测、独立代码审查与固定 SHA QA

1. 先对每个切片运行有意义的失败 / 恢复与合约测试，再组合；不得删除测试、改低期望或降低 MUST。测试默认断开真实网络，使用 HTTP stub / Fake、专用合成工作库和合成秘密。锁依赖，更新 uv.lock / 前端 lock 和 README 的真实存在命令。
2. 覆盖 OAuth state / scope / refresh，Keychain 拒绝 / 重启，材料分页 / 部分失败，task 日期 / 清空 / 完成 / malformed 回执 / 超时 unknown / 不重发 / 并发，模型无效输出 / 维度变化 / stale citation / 费用边界。用 canary 检查 API、日志、前端状态、证据和 Git 无秘密泄漏。
3. 运行 README 当前完整 Python 检查；前端生成 API 类型、test、typecheck、lint、build；Swift build。已有 warning 单列，不把退出 0 写成 warning 为 0。新增跨层 Keychain / OAuth / 模型配置功能必须有 WebUI 和必要原生开发壳的实际离线操作证据。
4. 完成独立代码审查，修复安全 / 契约 / MUST 问题，记录范围和未审项。审查不能代替独立 QA。
5. 提交固定候选 SHA，安排独立验收者使用新上下文和独立 checkout。可以委派独立 LUNA 子任务做审查 / QA；它不得修改产品实现、复用作者的“已通过”结论或更改验收期望。如当前运行环境无法提供独立验收者，交出固定候选与 QA 提示词，保持“DEV 完成待独立 QA”，不能自验后合并宣称 B 通过。
6. QA 按 ACCEPTANCE 的 B 门及适用 C01–C31 运行；回归 Stage A 的未知动作、不重发、知识 / 进度独立确认、原子写与引用门禁。缺陷由执行者单独修复提交，验收者固定新 SHA 复验，保留原 FAIL。
7. 全过程采集 console / network，不仅重载时捕获；harness 保存实际执行字节及 SHA-256。截图对应具体操作 / action ID / 状态，重复画面说明用途，不能代表没发生的状态。证据脱敏、manifest 逐项重算；证据改字节即更新 manifest 并追加说明，不改旧报告事实。

B 退出：适用 MUST 和离线 B 门通过；P0/P1 与阻断验收的 P2 清零，其他非阻断 P2 有明确影响、责任、验证与处理期限，不能归零隐瞒；报告区分实现、自测、代码审查、独立 QA、WebUI、原生开发壳和真实 NOT_RUN。生产外部调用为 0；专用合成 Keychain 测试独立列账。

通过后提交代码 / 文档 / QA 证据，创建 PR，附固定源码、检查与未测项。经独立审查和 QA 后合入 main，不 squash 到无法追溯受测提交。合并后在独立 checkout 核对受测代码树一致、QA 报告 / manifest 均存在并匹配，运行适当冒烟。仅清理本轮已合并且没有未归档本地数据的分支 / worktree；保留证据和未解决候选。C 必须固定在该 B 已验收的代码上。

## 4. 阶段 C：逐项授权的受控真实验收

### C0 — 安全配置与授权清单

B 通过后再到此门询问用户。不要现在索要一揽子秘密 / 材料。

向用户给出可审核的表，每行包括：目的、会读取 / 外发的数据、账号与目标服务 / 资源、精确动作、范围（条目 / 日期 / token / 请求次数）、预估费用与上限、风险、停止条件。至少分别列：真实 OAuth / Keychain 录入；材料只读与日历 / task 只读；LLM；embedding；rerank；真实 task 创建；编辑；完成。读取真实材料与发送模型必须分开批准。

用户通过安全本地配置界面或 Keychain 录入秘密；只在聊天确认非秘密模型 ID / endpoint / 维度 / callback、材料选择、资源范围和费用上限。报告不得包含原始秘密、业务正文或敏感 task 标识；使用脱敏映射留本地供用户复查。

许可可按一批明确范围授权，但不得推断跨账号、跨材料、跨动作或自动追加收费。DEV 和独立 QA 共用的总预算 / 次数应明确，不能各跑一遍突破上限。授权不足时相应项 NOT_RUN / BLOCKED，继续其他已授权项；不能因此声称 C 通过。

### C1 — 登录与只读协议

- 用户参与真实 OAuth，核对实际 scope、到期 / 刷新 / 重启后 Keychain、拒绝或缺权限、注销，以及开发壳和 WebUI 配置状态。
- 在明确批准账号 / 材料范围读取 metadata 和选中内容；在指定日期 / 时区读取日历；读取批准测试任务。核对完整性 / 分页、目标和 UI 状态，不扩展到全库。
- 写入仅为隔离测试工作库中的来源 / 待审，不自动批准正文、不发送模型。用户选定的业务样板另走内容确认门。
- 真实 API 的只读结果与官方 schema 对照；缺 scope、callback 不匹配、数据不完整或错误账号立即停该轨道，不能使用更高权限绕过。

### C2 — 模型与检索质量

- 先用用户批准的非敏感合成材料做最小调用，之后才使用另获授权的真实选中材料。
- 分别记录真实 LLM、embedding、rerank 的模型 / 配置指纹、请求次数、token / 用量、耗时、错误和实际或估算费用。未能拿到账单只能标估算 / 待核，不写“费用为 0”。达到预算 / 次数上限停止。
- 用预先确定的内容与期望验证整理忠实性、冲突处理、待审而非自动批准、rerank 生效、检索质量和 grounded answer；用户参与评定内容质量。加入原件 / 草稿 canary、外部改动 stale 引用、无证据 / 注入和配置切换反例。
- 真实 provider 可用不是质量通过；保留独立 QA 与用户评判的各自结论。完整 M3 会话 / 角色 / 记忆、长期基准和完整格式导入仍单独列 NOT_RUN。

### C3 — 真实任务最小写入

只操作用户指定的可抛弃测试资源。每类写入前展示目标和最终字段，让用户独立确认；范围和费用也须已有明确授权。

- 创建：核对无日期、全天、具体时间等需测变体；所需任务数量在授权表里明确，不能默认三种日期只用一次写入就全部通过。
- 编辑：只修改用户选定字段，验证日期设置 / 清除 / 标题及其他必需语义，GET 回读和 UI 一致。
- 完成：单独确认，完成时间非零且目标准确；原 task 不被其它动作误改。
- 验证 action journal、回执核对和只读结果；遇超时 / unknown 立即停止该动作的写入，只读核实或请用户提供明确独立结果。失败注入、并发重复、故意丢回执优先在离线环境验证，不为获得证据反复操作真实任务。
- 不自作主张删除测试 task 或“恢复”用户内容；清理 / 撤销也需要单独授权。结束报告留下什么真实资源以及谁来处理。

C 退出：按 ACCEPTANCE 的 C 门，在已授权范围中每项有固定源码、协议与实际 UI / network / readback / 内容质量证据；适用 MUST 全部通过、阻断缺陷已独立复验关闭、敏感数据 / 费用 / 剩余资源可核对。任何必需项 NOT_RUN 就不能宣称整个 C 通过。DMG、五日、双机仍独立未通过，原生开发壳结果不能替代安装包门。

真实 QA 后若修代码：回 B 的固定候选、自测、独立审查 / QA；对受影响真实场景重新取得必要授权并复验，不能把旧 SHA 的结果搬到新行为上。通过后按 B 的 PR、固定树核对和证据归档方式整合 main。

## 5. 交付、停止条件与最后结束语

每个切片更新 README（实际命令）、PROGRESS、LATEST-IMPLEMENTATION、API / 配置契约（有变化时）、ACCEPTANCE 的结果引用、报告索引和必要 ADR。新增 DEV / REVIEW / QA 报告，历史报告不改事实；源码、文档 checkpoint、QA 证据提交和 main merge SHA 分别列。

停止对应轨道的条件：授权缺失 / 撤回、预算耗尽、错误账号 / 资源、秘密泄漏、未证实的写入语义、unknown 写入、工作库身份 / 原子保护失败、P0/P1 或阻断 MUST 的缺陷。保留现场并脱敏诊断，继续不依赖它的工作；不得通过删除测试或降低门收口。

清理只关闭已证明归属本轮的 PID、profile 和端口，核对监听退出。工作目录不留下私密证据到 Git；只移除已合并且可恢复的本轮分支 / worktree，不能清旧 QA 归档。把共享 checkout 更新为干净 main 前先检查无用户改动。最后核对远端 main 与本地，记录代码树一致、manifest 匹配和未运行项。

最后给用户下面格式的结束语，以实际结果替换占位符，不省略失败 / 未测项：

> 阶段 B：[PASS / FAIL / DEV 完成待独立 QA / BLOCKED]；阶段 C：[PASS / FAIL / 部分完成 / NOT_RUN / BLOCKED]。B 固定受测代码为 […]，C 固定受测代码为 […]；独立审查与 QA 报告 […]，证据 manifest […]；PR / merge […]，最终远端 main 完整 SHA […]。合并后代码树核对 […]，自动检查 / WebUI / 原生开发壳分别 […]。真实操作的批准范围、数据、请求 / 写入次数、费用与遗留测试资源 […]；未获授权或未测项 […]。未关闭 P0/P1/P2 分别 […]，历史 FAIL 和复验链 […]。源码整合及本轮服务清理 […]。DMG、五日、双机和 M3–M5 状态 […]。请将这些固定证据交回独立技术评定者，再决定后续阶段。

不要仅说“全部通过”或“资源已准备所以完成”。你的目标是交付可复验的 B/C 结果与干净 main，不是通过隐藏未测项得到结束语。
