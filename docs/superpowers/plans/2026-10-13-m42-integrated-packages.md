# M4.2 真实业务闭环集成执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development；以用户明确指定的整个工作包为单位执行 Developer → fresh QA，不逐接口 QA。用户本轮直接授权覆盖普通技术决策和离线开发，优先于技能重复审批、五轮修复及删除工作树的默认流程。

**Goal:** 完成真实验收所需离线能力，随后在对应授权下完成真实业务闭环。
**Architecture:** 保留唯一 FastAPI、现有 React WebUI、原生壳和 provider adapters；在现有本机 profile 与原子事务机制中增加有限、明确范围的真实验收计划及独立确认。配置、预览和状态读取不联网；普通设置不能签发业务外发授权。
**Tech Stack:** 项目现有 Python/Pydantic/FastAPI、TypeScript/React、SQLite、Swift；无新增框架。
**Spec:** docs/product/PRODUCT-SPEC.md、docs/contracts/API-v1.md、docs/contracts/WORKSPACE-v1.md、docs/quality/ACCEPTANCE.md；本轮用户提供的 M4.2 三包请求。

## 基线与边界

- 本地 main 起点 69a8bb0572da8687ad7f73c0f75d5e51b5457d7e，干净；不重复核对远端或拉取。
- M4.1 离线受测源码 3f6eaa408a8860ff5a438be8a874a2c3904733e4 的结论保持历史；整个 M4 未通过。
- 开发目录独立 worktree，分支 codex/m42-readiness-20261013；保留 main、旧应用、工作树与材料。
- 只用合成材料、Fake / Mock HTTP、隔离空工作库和 profile。禁止真实 Keychain、服务、业务文件、真实任务及付费请求。
- 真实材料位置/版本/内容的检查也先取得授权；文件存在不等于批准。
- 真实模型、飞书、Keychain、安装、五日、M5、公证/发布分别 NOT_RUN；未暴露模型 runtime 元数据 UNVERIFIED。
- 首次 QA 失败后最多两轮自动修复，每轮固定新 SHA 和 fresh QA；不削弱 tracked tests / Must。

## 当前执行状态（2026-10-14）

工作包 A 的固定产品 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28` 已由 fresh QA 验收；Sol 判定报告明确列出的离线/API/Mock/packaged UI 技术场景 PASS，不等于整个工作包 B/C、M4.2、C25 或产品最终 PASS。逐项范围与限制见 [Sol gate](../../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)、[QA report](../../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) 和 [证据 archive](../../quality/reports/evidence/2026-10-14-m42-package-a-qa-repair1/README.md)。原初始 QA FAIL 与其原报告/evidence 保留。

用户已于 2026-10-14 批准工作包 A 离线正式收口与合入 main；本轮 PR、远端 CI、merge 尚未发生，后续由 Sol 按仓库 PR 检查与保护规则办理。此批准不扩大真实资料、模型付费调用、Feishu、Keychain 或用户安装授权。

以下 Task 1 勾选项是原执行清单，不应把所有未勾选项解释为 fixed `419bb86` 仍待开发，也不据此把证据缺失说成已完成。采用上方固定 SHA 的 gate 结果和报告逐项状态：失败项保留原 operation ID 的真实 UI retry、Real JournalAssist packaged UI、真实 provider/Feishu/tasks、材料质量/账单、Keychain 生命周期、正式用户安装/公证、五日、双机及发布仍 NOT_RUN；runtime model metadata、误启动期间 Keychain/profile 访问及影响仍 UNVERIFIED。QA 一条失败 assertion 的完整 raw 保留，另一临时失败 assertion raw 被覆盖；不得勾称缺失输出已恢复。早期 baseline capture 的记录按 DEV/QA 证据所能证明的范围表述，不推断未留存的 exit code。

## 收口维护保留范围

Sol 后续 inventory/清理时拟保留固定 `419bb86` 的最终 App 与 DMG、全部 tracked QA/DEV 失败与通过证据及对应源码 checkpoint、当前仍在运行的旧 App、用户数据与工作库。先核对备份和实际引用关系；只有确认是未被使用的临时生成物且所需证据已保全后，Sol 才清理相应临时文件。此文档更新不删除文件、产物、分支或 worktree。

## 覆盖关系

| 验收 | 工作包 A 离线准备 | 工作包 B 对应真实证据 | 工作包 C |
|---|---|---|---|
| C26 | 合成最终页通过正式 writer 初始化的方案/回归；真实原件不进仓库 | 四份材料 grillme、批准事实/未决、黄金问题、整体批准后初始化；原件不复制且保留 | 用户查看最终正式知识 |
| C27 / R01 | 适配审计、范围门、次数/错误/用量账本；历史 smoke 授权与计数不重置 | 当日官方协议/价格、历史实际额度核对，独立批准服务/材料/次数/费用 | 真实引用与业务体验 |
| C27 / R02 | 飞书只读范围、metadata/选择/日历/tasks 与权限故障 | 账号身份、OAuth/refresh、scope、明确材料与日历/任务范围；OS Keychain | 用户选择和导入体验 |
| C27 / R03 | 忠实整理及三类问答合成 oracle；版本/引用反例 | 忠实事实/数字/未决、证据不足、跨页比较/方案与用户质量评定 | 真实整理→编辑→批准→索引→问答 |
| C27 / R04 | 独立动作/unknown no-resend 回归；真实写继续禁用直至协议和授权门满足 | 每次目标和最终值独立批准；结果核实不猜成功 | 写操作不与知识确认混合 |
| R05 / C24 / C25 | 固定源码、fresh QA、clean 候选身份、隔离离线启动 | 真实账户/凭据生命周期与用户实际安装分别记录 | 退出重启持久性 |
| C28 | 现场脚本、P0/P1/P2记录、五日表（空） | 真实准备齐备 | 完整闭环用户确认后，五个实际工作日，记录实际日期；M5 后续独立 |

## Task 1: 工作包 A（一个完整开发与集中 QA 单位）

**Ownership / Files:** Developer 独占本 worktree 的 src、tests、web、必要 scripts/native 及 docs；不改 domain/content.py 的信任规则。核心修改预计 integrations/settings.py、runtime.py、api/app.py/小范围 routes、现有 UI components 与 generated types；有限验收账本可建单一 local 模块，复用既有原子写/锁。按现有结构选择最少必要文件，记录实际清单。

**Interfaces / decisions:**
- 先完整审计设置→凭据→真实模式→调用→入库→索引/问答、Feishu gates 和 packaged app；写差距清单，再补齐所有不依赖真实资源的必要实现。
- 增加无网络的真实验收计划预览和独立确认，服务端绑定 workspace、profile、执行配置、具体动作/payload 与材料当前版本；允许的来源/页面/问题或飞书 query/选中 ID/日历区间/任务列表条件必须清楚显示。必要时限制验收到隔离工作库全部合格页面，界面明示具体页和版本；不能仅放开全局 real_data_enabled。
- 执行时复核预览范围/配置/版本，计划改变失效；未确认/取消/范围扩大/过期/异库/异profile 零外发。模型输出、资料正文、设置 PATCH 不可签发确认。
- 在网络前原子预留有限操作/调用次数；失败、timeout、进程中断计入且不自动重发。账本只存安全 ID/状态/计数/用量，不存秘密、prompt/正文或业务标题。费用显示估算/未知真实账单，不能虚构实际费用或把次数预算称金额硬上限。实时授权可先按一次操作确认，避免创建长期宽泛授权系统。
- 实际整理只发送用户选中的 input；index 只发送已批准当前页；query 的资格、rerank 前检查与最终引用复验仍调用唯一内容基准。问答历史/角色/记忆的外发边界必须在预览说明与版本绑定中处理，不悄悄扩大范围。
- 无真实授权时既有 Fake 流程可用；real 模式 provider 未启用/未配置要具体失败，不能冒充真实质量成功。普通列表/状态读取不得因 review_for 创建远端 provider 而阻断，也不联网。
- 分开 index 与 answer 需要的 provider：仅 index 不应创建无关 LLM/rerank client 或索取其凭据；操作终结关闭实际创建的 client。
- Feishu 支持能力的只读请求采用独立精确范围确认；认证/refresh 保持既有单次消费、generation/state 与安全入口。真实任务写尚缺独立结果证明，保留禁用并明确阻断原因，不因本轮授权开放。
- 本机密钥只经设置安全入口；不读/迁移现有真实 secret。MacOSKeychainBackend 类型/可用性不等于 OS 生命周期已通过；合成故障应可读反馈。
- 老 smoke ledger 不重置；profile 的 remaining 只说明该 profile 账本，不能称全局剩余额度。执行真实 smoke 前人工核对历史记录和目标 profile；本轮不执行。

- [ ] 按 README 安装本 worktree 依赖；保存 baseline guarded tests 实际退出码，不重复开发已完成部分。
- [ ] 先添加最小行为反例并保存 RED：未确认零外发、精确范围/版本/配置绑定、并发限次、失败/重启 no-resend、列表零调用、index 无关 provider、秘密脱敏、真实路径无 Fake 成功。
- [ ] 最小实现上述能力，并补 UI 的完整预览→独立确认→显式执行/撤销/状态体验，沿用现有设计；服务端是授权真源。更新 API 契约与生成类型。
- [ ] GREEN 定向检查，再正式整包：guarded pytest；ruff check/format；mypy；lock check；uv build；Web test/typecheck/lint/build；Swift tests（native 改动必须）；类型生成一致性。保存命令/退出码与脱敏 manifest。
- [ ] 真实浏览器合成闭环：列表/设置不联网、预览可审阅、取消零外发、确认后仅指定操作、失败/额度/计划变化可见；C04/C10/C11/C12/C14/C16/C19/C21/C22/C24 回归。只在本项目隔离 loopback 服务。
- [ ] 准备隔离合成工作库/profile、业务质量判定标准、黄金问题模板、用户一页操作说明、外部服务/费用/动作清单及空五日记录。复用 docs/handoff 与 reports，不创建另一管理体系。
- [ ] 小逻辑提交并固定 clean 产品 SHA；从该 SHA 强制重建独立 Internal App/DMG 至全新路径、非覆盖离线启动/静态前端身份与设置/验收路径复演；不绕过 Gatekeeper。包是新受测对象，旧 M41 QA 不能替代。
- [ ] DEV 交接：固定 SHA、差距清单与已补项、逐命令退出码、实际 UI/候选摘要、已知限制、所有真实 NOT_RUN。更新 README/PROGRESS/LATEST 的正文，历史证据原样保留。
- [ ] Sol 检查 diff 与交接，fresh QA 独立固定 SHA checkout 集中验收（不改产品或 tracked tests）；Sol 核日志/manifest/退出码与 QA 观察并判门。包不自动合并 main。

### 修复轮 1 的已确认 v1 完整范围补充

初始 QA 固定 SHA `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 判 FAIL 后，Sol 在固定新产品 SHA 前追加了产品规格中已确认但此前漏实现的批量导入与真实日志 AI 辅助。这是工作包 A 原范围补齐，需与 P1/P2 一起由一次 fresh QA 验收。

- [ ] 批量文件选择及目录选择复用单文件 `/intake/files` writer；顺序处理，最多 100 个 / 100 MB、20 MB 每文件，TXT/Markdown；显示路径、跳过项、逐项结果。部分失败不阻断其余项，只有失败项可用原 operation_id 重试；新选择重新生成意图，不能按同名同大小静默重放旧成功项。取消选择不写库、不调用模型。
- [ ] Native picker 只接受可信本机主 frame/origin；文件夹只从用户显式选择的根收集，排除隐藏和 package 内容、不跟随 symlink，限制遍历 2,000 项、100 文件 / 100 MB；读取不完整或超界时整批拒绝。浏览器 FileList 的相对路径过滤隐藏 / package 路径。需实际 WKWebView 复演多文件与目录选择，不能仅以单元测试替代。
- [ ] 日志 AI 辅助复用一次性 plan ledger，预览实际编辑正文、服务与输出上限；确认后最多一次真实 LLM organize，正文/配置变化、未确认、取消、重复和过期不可外发。失败/unknown 消耗预留且不自动重发；usage 只记安全计数与 request id，账本失败也关闭 client。建议只返回编辑态，不保存；保存仍需独立用户动作，Fake 浏览与保存行为保持原样。
- [ ] UI 在日志计划待确认时禁用保存、再次辅助、采用/清除旧建议或正文编辑；取消调用服务端 DELETE。状态枚举转为简体中文业务提示。
- [ ] 在 API-v1、当前 README、计划/进展与 DEV 证据说明以上契约、合成用例与真实 NOT_RUN；不改变 `domain/content.py`、真实 task 写仍禁用，真实密钥/provider/飞书/材料仍需单独 opt-in。

## Task 2: 工作包 B（真实授权后执行）

- [ ] 集中请用户授权四份样板材料的定位/读取，材料内容批次选择题 grillme；黄金依据与未决事项用户确认。最终整体批准后才初始化。
- [ ] 先核对既有 smoke 实际消费和目标 profile；官方模型/端点/价格于执行当日再次核对。说明外发内容、预计次数、估算与用户选定费用上限，取得对应批准；通过本机设置录入密钥。
- [ ] 先安全只读 Feishu：用户选定账号/metadata搜索词/所选材料/明确日历时间与任务范围；OAuth/Scope/refresh/Keychain 分开记录，任何任务写独立批准并满足结果证明门。
- [ ] 真实整理、embedding、rerank、版本引用及事实/比较/方案/证据缺失问题；用户参与质量判定。失败保留，必要修复经 Developer→fresh QA 最多两轮。

## Task 3: 工作包 C（满足真实条件后）

- [ ] 用户实际新位置安装/打开→选库→已批材料→真实整理→完整编辑→逐页确认→索引→问答/引用→退出→重开/状态复验。
- [ ] P0/P1 修复且复验，P2 留计划；用户确认业务闭环通过后再开始五日，逐实际工作日记录。M5、正式发布/公证未授权不执行。

## 自检与执行裁定

| 对象 | 产生/消费关系 | 检查 |
|---|---|---|
| A 内 settings/runtime/routes/UI | API 真源→生成类型→UI；门在服务端 | 一致；普通设置不是确认 |
| A→B | 固定离线代码/计划模板→用户授权/真实资源 | 真实材料不能在 A 读取；历史 smoke 未测不当当前余量 |
| B→C | 用户批准事实与实际质量→现场闭环→五日 | 条件顺序清楚，不提前通过 |
| A 自身 | 先反例→实现→固定 SHA→clean 包→fresh QA | 集中验收，不逐 API；SHA 与文档证据分开 |
| B 自身 | 资源选择→独立批准→执行→业务判定 | 无隐式权限扩大 |
| C 自身 | 实际闭环→关键缺陷关闭→用户确认→真实日期 | 不脚本模拟五日 |

Ruling: 按用户本轮直接授权实施上述准备，并由 Sol 自主决定普通接口/文件组织；不重复技能的逐段人工设计批准。错误成本为离线代码返工；外部资源与重要合并仍须明确批准。
Ruling: 用户已指定三包与每包集中 QA；用一个 Developer 连续完成 A，fresh QA 集中独立验证，最多两轮修复；不采用技能逐接口审查或五轮上限。错误成本为整包修复，验收门不降。
