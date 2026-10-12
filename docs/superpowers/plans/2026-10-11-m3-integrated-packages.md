# M3 功能包实施计划

2026-10-12 收尾交接：用户要求更新文档、清理临时环境，并准备由 Deepseek Harness V4.1 flash 在独立分支尝试 C19。此次只做收尾，产品源码仍为 `f79f613a902758da3173a5b27219fa568a912f5e`，C19 独立 QA / Sol 仍为 FAIL；包 1 / 包 3保持既有离线 PASS，M3 正式门及合并未通过。交接固定引用为 `handoff/c19-dsh-2026-10-12`；下一位先读 `docs/handoff/DSH-C19.md` 和 `docs/handoff/2026-10-12-M3-CLEANUP.md`，不可从缺少 M3 的 main 开始修复，也不可在基线目录写源码。原 Sol / Luna 周期已停止；本轮未启动额外修复或 QA。

日期：2026-10-11。用户已明确授权执行及实施顺序优化。产品规格和全 v1 计划不变。本计划替代逐小切片启动独立 QA 的节奏；不替代原 M3 验收要求。

## 起点与执行规则

- 2026-10-12 当前：包 1、包 3保持各自离线集成 PASS；包 2 C19 统一修复 repair 2/2 在源码 `f79f613a902758da3173a5b27219fa568a912f5e`、QA 固定 `262f4eaa418d70f983f3b0b260d3635cd2e28c92` 上由独立 QA / Sol 判 FAIL（P1）。旧12项与纠正后9项holdout通过，新增矩阵15 PASS/7 FAIL同根因：信息性主题词被剥除，现有资料被错误判为缺失。450后端/Web56与静态/构建检查通过不能抵销产品失败。两轮自动返工已用完，停止自动源码修改、等待用户决定；M3正式验收和合并未通过。真实/发布门 NOT_RUN，runtime UNVERIFIED，smoke未消费。 见[Sol最终门](../../quality/reports/2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)和[最终独立QA](../../quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md)。
- 复用 M1/M2 的资格门、QueryService、SSE、稿件、事务、身份锁及 action receipts，不重复开发已完成能力。
- Developer Luna 连续完成一包，允许多个逻辑提交，持续自测；Sol 只读协调和审查。
- 包完成固定源码 SHA，停止实现修改；全新 QA Luna 在独立 checkout 验收整包，保留实际日志、退出码和黑盒证据。
- 每包首次 QA 失败后最多两轮自动修复；每轮新 SHA、全新 QA。不得删测试或降低门。
- 普通实现、自测、交接无需再问用户；M3 正式验收及重要里程碑合并需用户批准。包之间可在本功能分支接续开发，不先合并 main。
- 默认隔离合成库、Fake providers、guard；真实材料、模型、飞书、凭据、Keychain、DMG、五日、双机均不在本执行授权内。

## 包 1：会话与历史

依赖：现有 QueryService、profile context、API-v1 query/conversations、AskView/PageReader。

- [x] 本机每 workspace 会话持久化：列表、读取/重开、删除、稳定 request/message 身份；重启可读，两 profile 和库切换隔离（整包 QA 已 PASS）。
- [x] API 与 WebUI 完整接通；会话重开后可继续提问，不把历史当已确认知识（整包 QA 已 PASS）。
- [x] SSE 严格有序、唯一终态；完成、错误、取消、断流和进程重启有准确历史状态，不保存假完整答案；未知请求不自动重发（整包 QA 已 PASS）。
- [x] 引用保留原 content hash / excerpt / validity；历史显示更新/不可用，打开稳定页并提示版本变化，不悄悄替换原依据（整包 QA 已 PASS）。
- [x] Developer 定向单元/契约/集成/UI 检查及 README 后端 / Web 门禁已记录真实退出码（DEV 自测不代表阶段通过）。
- [x] 固定 SHA 的整包独立 QA：首次固定 SHA `c90fe6e2` QA 判 FAIL（原报告保留）；repair 1/2 源码 `a9078bd` 由独立 QA 固定 `bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4` 复验，Sol 判包 1 离线集成 PASS。报告：[首轮 FAIL](../../quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md)、[repair 1 PASS](../../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md)。限制：浏览器 request body/response header 未导出，console NOT_RUN、runtime UNVERIFIED；full multi-turn belongs package 2；真实及发布门 NOT_RUN。

初始 DEV 与 repair 1 SHA、命令结果和完整 QA 报告链见 [M3 包 1 DEV 报告](../../quality/reports/2026-10-11-M3-PACKAGE-1-DEV.md)、[repair 1 DEV 报告](../../quality/reports/2026-10-11-M3-PACKAGE-1-REPAIR-1-DEV.md)、两个独立 QA 报告与[最新交接](../../handoff/LATEST-IMPLEMENTATION.md)。Sol 的 PASS 只覆盖离线集成包 1，不等同 M3 正式验收。

## 包 2：完整问答能力、角色与记忆

2026-10-12 当前状态：用户重新授权C19后，统一初验及两轮自动返工均已独立QA；最终repair2/2源码 `f79f613` 仍有主题词剥除P1，Sol判FAIL。停止自动修改、待用户决定。包1/3保持各自离线PASS，M3正式门未通过。

依赖：包 1 会话/message 身份。主要模块 retrieval、integrations/llm、local roles/memory、对应 API / WebUI。

- [x] 事实、跨材料比较、工作方案三类明确路径和独立合成问题；来源陈述、推断/建议、缺失资料分开；引用及效力清晰，无资料不补造业务数字（Developer extra 2 自测完成；QA 已最终判 C19 P1 FAIL；不能视为包级通过）。
- [x] 本地每库角色 CRUD、预算与实际问答上下文；不能解除证据/批准/工具权限，不改变整理忠实性（Developer 完成；QA 固定 SHA `d2236c2` 判 C19 P1 FAIL）。
- [x] 仅可从可核验的明确用户表达生成记忆候选；来源/assistant 不能自成用户事实，接受/编辑后才活跃；活跃记忆管理和预算（extra 1 的实现保持真实 user message、原文跨度、本人表达声明和单独确认门；extra 2 QA 后判 C19 P1 FAIL）。
- [x] 两 profile 同库各自历史/角色/记忆/索引独立；答案不自动写知识；当前/历史依据始终复验统一资格门（Developer 完成；QA 固定 SHA `d2236c2` 判 C19 P1 FAIL）。
- [x] Developer extra 2 定向检查及 README 全量后端/Web/静态/类型/构建与生成契约检查；guarded pytest 417 passed、Web 55 tests / 12 files，所有自动门 exit 0（DEV 自测非 QA；固定 SHA `d2236c2` 最终 QA 因 C19 P1 判 FAIL）。
- [x] 固定 SHA `d2236c243ac28c86b94acd8e8dd139dc865b7b75` 的整包独立 QA 已完成；Sol 判 C19 P1 FAIL，无资料比较仍引用不相关预算。用户随后直接授权包 3，未授权继续修包 2；完整证据见 extra 2 QA / Sol 门报告。

包 2 原首轮独立 QA 固定源码 `082744738f300525e57dfd6655245adb98e13628` 判 FAIL，[报告与证据](../../quality/reports/2026-10-11-M3-PACKAGE-2-QA-0827447.md)保留；repair 1/2 源码 `0df323efc26e388d62f234e0471f853b2b54be4d` 与 repair 2/2 源码 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15` 的独立 QA 也均判 FAIL，原报告不改写。extra 1 是用户明确批准的单轮额外修复，固定源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，行为、自测、限制和全新 QA 复演范围见[extra 1 DEV 报告](../../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)。extra 1 QA 最终 FAIL，用户随后明确批准 extra 2；extra 1 的旧 QA pending 文案仅保留为历史。extra 2 QA 最终由 Sol 判 C19 P1 FAIL；该结论对应当时受测 SHA 且原报告保留。用户随后直接授权包 3，后又重新授权 C19 统一修复；当前固定源码、最终QA FAIL及待用户决定状态见本节顶部。

## 包 3：连续工作与归档压缩（离线集成 PASS）

用户明确改为先执行包 3；包 2 C19 P1 FAIL不改写。产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`，全新 QA 固定 `7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`，[独立复验](../../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md)及[Sol 门判断](../../quality/reports/2026-10-12-M3-PACKAGE-3-SOL-GATE.md)。

- [x] 跨 profile 待审稿和部分完成状态接续；活 owner 与死 owner unknown/no-resend、checkpoint仅恢复本地稿、取消后迟到结果CAS、显式reprocess提醒及同意图幂等已验收。
- [x] intake items/jobs与capture、mutation、SHA write-intent、Feishu import完成回执按active+月摘要读取/重放；未知/运行中保持active，原件、完整稿及确认历史保留。
- [x] 摘要原子写中断、相同副本恢复、冲突/损坏/非法月份/意外副本阻断，以及legacy undated和版本parent链检查通过。
- [x] profile-only allowlist轮转诊断日志与存储隔离；120条合成流程跨四月计数和provider重放计数通过；真实双机与性能基准不作通过推断。
- [x] 初验C22锁清理FAIL保留；自动返工1/2后两异常路径已由全新QA证明即时清理、无provider副作用且同意图重试仅一次。
- [x] 固定SHA的整包独立QA及Sol核证：guarded440、核心99、资格/变更37、Web56及适用静态/类型/构建检查通过；双profile真实浏览器短复演通过。C19基线FAIL、真实/发布NOT_RUN与runtimeUNVERIFIED保持。

## 完成与正式门

每包更新 PROGRESS、LATEST-IMPLEMENTATION、README 及 DEV/QA 报告索引。Sol 根据原始证据逐项判 PASS/FAIL/BLOCKED/NOT_RUN，未经观测 runtime 元数据保留 UNVERIFIED。

三个包独立通过后，提交 M3 模拟范围的正式验收/合并请求；真实质量、Stage C、M4/M5 保持独立未测门。任何验收未完成项必须明确披露，不能把 DEV 或 mock 全绿等同完整 v1 交付。
