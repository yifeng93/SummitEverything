# M3 功能包实施计划

日期：2026-10-11。用户已明确授权执行及实施顺序优化。产品规格和全 v1 计划不变。本计划替代逐小切片启动独立 QA 的节奏；不替代原 M3 验收要求。

## 起点与执行规则

- 计划起点为 clean main `5fd91c78930c80b2365957197b8a605757694a91`（历史）；包 1 离线集成由 Sol 判 PASS。包 2 repair 2/2 与 extra 1 QA 曾 FAIL；用户随后明确批准仅一轮 extra 2，Developer 自测固定源码 `c41147fe54bf95103c741df192fc76eb9df0f9e7`，现待全新独立 QA。M3 完整验收仍未完成。
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

2026-10-12 当前状态：包 1 离线集成由 Sol 判 PASS；包 2 extra 1 QA 曾 FAIL。用户明确批准仅一轮 extra 2，Developer 固定产品源码 `c41147fe54bf95103c741df192fc76eb9df0f9e7` 并完成全量自动自测，当前待全新独立 QA，尚无 extra 2 QA/Sol PASS。若该轮 QA 仍 FAIL，自动修复额度耗尽，交用户决定。包 3只读准备完成、实现未开始；M3 正式门与合并未执行。细节及 QA 复演范围见[extra 2 DEV 报告](../../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-2-DEV.md)；extra 1 历史门见[Sol 报告](../../quality/reports/2026-10-12-M3-SOL-EXTRA-1-GATE.md)。

依赖：包 1 会话/message 身份。主要模块 retrieval、integrations/llm、local roles/memory、对应 API / WebUI。

- [x] 事实、跨材料比较、工作方案三类明确路径和独立合成问题；来源陈述、推断/建议、缺失资料分开；引用及效力清晰，无资料不补造业务数字（Developer extra 2 自测完成；新 QA pending，不能视为包级通过）。
- [x] 本地每库角色 CRUD、预算与实际问答上下文；不能解除证据/批准/工具权限，不改变整理忠实性（Developer 完成；QA pending）。
- [x] 仅可从可核验的明确用户表达生成记忆候选；来源/assistant 不能自成用户事实，接受/编辑后才活跃；活跃记忆管理和预算（extra 1 的实现保持真实 user message、原文跨度、本人表达声明和单独确认门；extra 2 新 QA pending）。
- [x] 两 profile 同库各自历史/角色/记忆/索引独立；答案不自动写知识；当前/历史依据始终复验统一资格门（Developer 完成；QA pending）。
- [x] Developer extra 2 定向检查及 README 全量后端/Web/静态/类型/构建与生成契约检查；guarded pytest 417 passed、Web 55 tests / 12 files，所有自动门 exit 0（自测结果见[extra 2 DEV 报告](../../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-2-DEV.md)；不等于包级通过）。
- [ ] 固定 SHA `c41147fe54bf95103c741df192fc76eb9df0f9e7` 的整包独立 QA：重跑历史 QA 的 C13/C14/C19/C20/C21 与浏览器问答/角色/记忆场景；重点核验 fresh ready 索引无关主体缺资料提示不再误报缓存/资格异常，未就绪/空索引、CURRENT 排除 history/无批准、真实旧 hash 及生成中页面变化/不可用分别给出准确说明；三模式 missing 与主文一致、零引用不调用 answer provider，同时复核历史批准/效力、记忆 provenance、CURRENT/HISTORY、比较/方案多材料及 earlier repairs。QA 尚待 Sol 调度；若 FAIL，停止自动修复并交用户决定。

包 2 原首轮独立 QA 固定源码 `082744738f300525e57dfd6655245adb98e13628` 判 FAIL，[报告与证据](../../quality/reports/2026-10-11-M3-PACKAGE-2-QA-0827447.md)保留；repair 1/2 源码 `0df323efc26e388d62f234e0471f853b2b54be4d` 与 repair 2/2 源码 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15` 的独立 QA 也均判 FAIL，原报告不改写。extra 1 是用户明确批准的单轮额外修复，固定源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，行为、自测、限制和全新 QA 复演范围见[extra 1 DEV 报告](../../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)。extra 1 QA 最终 FAIL，用户随后明确批准 extra 2；extra 1 的旧 QA pending 文案仅保留为历史。当前 extra 2 QA pending；若 QA 仍 FAIL，不能自行启动下一轮。

## 包 3：连续工作与归档压缩

依赖：现有 source/intake/review、writer journals、action receipts；复用已有月汇总，补全未完成部分。主要模块 workspace state/archives、local logging 和对应 API/UI。

- [ ] 中断整理后另一 profile 接续可见，部分完成稿件/流程准确，未知模型请求不自动重发，显式重新处理说明可能新增调用。
- [ ] 待处理只有当前业务记录，完成按月归档；receipt 可查且同意图幂等，unknown/running 不清除；不删除原件与稿件正文。
- [ ] 原子归档/压缩中断、并发相同意图、重复或冲突副本可解释恢复，不丢确认内容，不让未确认内容入库。
- [ ] 同步库无 SQLite/WAL、凭据、历史、角色、记忆、诊断日志；本地日志轮转，模拟大量流程并报告文件数量随流程/月数变化。
- [ ] Developer 持续定向检查，收口全量自动检查及完整 v1 Fake UI 链路。
- [ ] 固定 SHA 的整包独立 QA：C22、C23、C21 存储边界、C13/C14/C19/C20 回归，跨 profile 和故障恢复黑盒证据。

## 完成与正式门

每包更新 PROGRESS、LATEST-IMPLEMENTATION、README 及 DEV/QA 报告索引。Sol 根据原始证据逐项判 PASS/FAIL/BLOCKED/NOT_RUN，未经观测 runtime 元数据保留 UNVERIFIED。

三个包独立通过后，提交 M3 模拟范围的正式验收/合并请求；真实质量、Stage C、M4/M5 保持独立未测门。任何验收未完成项必须明确披露，不能把 DEV 或 mock 全绿等同完整 v1 交付。
