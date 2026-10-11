# M3 功能包实施计划

日期：2026-10-11。用户已明确授权执行及实施顺序优化。产品规格和全 v1 计划不变。本计划替代逐小切片启动独立 QA 的节奏；不替代原 M3 验收要求。

## 起点与执行规则

- clean main `5fd91c78930c80b2365957197b8a605757694a91`；M3 未开始。
- 复用 M1/M2 的资格门、QueryService、SSE、稿件、事务、身份锁及 action receipts，不重复开发已完成能力。
- Developer Luna 连续完成一包，允许多个逻辑提交，持续自测；Sol 只读协调和审查。
- 包完成固定源码 SHA，停止实现修改；全新 QA Luna 在独立 checkout 验收整包，保留实际日志、退出码和黑盒证据。
- 每包首次 QA 失败后最多两轮自动修复；每轮新 SHA、全新 QA。不得删测试或降低门。
- 普通实现、自测、交接无需再问用户；M3 正式验收及重要里程碑合并需用户批准。包之间可在本功能分支接续开发，不先合并 main。
- 默认隔离合成库、Fake providers、guard；真实材料、模型、飞书、凭据、Keychain、DMG、五日、双机均不在本执行授权内。

## 包 1：会话与历史

依赖：现有 QueryService、profile context、API-v1 query/conversations、AskView/PageReader。

- [ ] 本机每 workspace 会话持久化：列表、读取/重开、删除、稳定 request/message 身份；重启可读，两 profile 和库切换隔离。
- [ ] API 与 WebUI 完整接通；会话重开后可继续提问，不把历史当已确认知识。
- [ ] SSE 严格有序、唯一终态；完成、错误、取消、断流和进程重启有准确历史状态，不保存假完整答案；未知请求不自动重发。
- [ ] 引用保留原 content hash / excerpt / validity；历史显示更新/不可用，打开稳定页并提示版本变化，不悄悄替换原依据。
- [ ] Developer 定向单元/契约/集成/UI 检查，收口运行 README 的后端与 Web 检查并记录实际退出码。
- [ ] 固定 SHA 的整包独立 QA：C14、C21 历史部分、C13 历史引用部分及相关资格回归；实际浏览器列表/重开/取消/版本更新/库切换复演。

## 包 2：完整问答能力、角色与记忆

依赖：包 1 会话/message 身份。主要模块 retrieval、integrations/llm、local roles/memory、对应 API / WebUI。

- [ ] 事实、跨材料比较、工作方案三类明确路径和独立合成问题；来源陈述、推断/建议、缺失资料分开；引用及效力清晰，无资料不补造业务数字。
- [ ] 本地每库角色 CRUD、预算与实际问答上下文；不能解除证据/批准/工具权限，不改变整理忠实性。
- [ ] 仅可从可核验的明确用户表达生成记忆候选；来源/assistant 不能自成用户事实，接受/编辑后才活跃；活跃记忆管理和预算。
- [ ] 两 profile 同库各自历史/角色/记忆/索引独立；答案不自动写知识；当前/历史依据始终复验统一资格门。
- [ ] Developer 持续定向检查，收口全量后端/Web/静态/类型/构建与生成契约检查。
- [ ] 固定 SHA 的整包独立 QA：C19、C20、C21，C13/C14 回归及实际浏览器三类问答、角色、记忆确认与删除。

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
