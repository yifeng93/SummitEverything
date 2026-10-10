# 给 Sol：阶段 B 独立评估与下一步 Luna 执行提示词

以下内容可整段发给 Sol。当前任务是独立审查开发候选、判断是否达到固定 SHA 正式 QA 的条件，并据证据生成下一段 Luna 执行提示词。不要把尚未固定的工作树自签成阶段通过。

---

你是 SummitEverything 的独立技术评定者。请只读检查阶段 B 候选，给出可复验的验收就绪度报告，并在报告后附上一段可直接交给下一位 Luna 的完整执行提示词。不要修改产品代码、依赖、分支或验收期望；不要提交、推送、创建 PR 或合并。

## 目标与仓库状态

- 仓库：`/Users/yifengstudio/Documents/GitHub/SummitEverything`
- 开发 worktree：`/Users/yifengstudio/.codex/worktrees/stage-b-real-providers/SummitEverything`
- 分支：`codex/stage-b-real-providers`
- 已知基础 HEAD：`ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`
- 最近一次开发报告记录候选仍有未提交更改、没有固定实现 SHA。先实际检查 worktree、branch、HEAD、tracked diff 和 untracked files；不要假设以上状态仍然准确。

因为候选可能仍是 dirty tree，本次默认做**独立 DEV 候选评估 / QA readiness review**，不是固定 SHA 的正式阶段验收。如果没有干净、明确、可复现的源码 SHA，报告必须写明正式 B QA 尚未开始，不能给 B PASS。若代码树已经固定，则记录该完整 SHA，并说明本轮是否具备独立 checkout 和独立上下文；不可只基于开发者报告下结论。

## 必读资料

按仓库 `AGENTS.md` 顺序阅读 README、PROGRESS、PRODUCT-SPEC、ARCHITECTURE、WORKSPACE-v1、API-v1、IMPLEMENTER、TESTER、全 v1 计划、ACCEPTANCE；之后读：

- `docs/handoff/LATEST-IMPLEMENTATION.md`
- `docs/handoff/PROMPT-STAGE-B-C-LUNA.md`
- `docs/quality/reports/2026-10-10-STAGE-B-partial-DEV.md`
- `docs/architecture/PROVIDER-PROTOCOL-MATRIX.md`
- `tasks/plan.md` 与 `tasks/todo.md`
- 与 Stage A / B 相关的原始报告和证据索引

使用源码和测试独立核对报告；历史通过结论不自动转移到当前候选。按 `docs/quality/ACCEPTANCE.md` 保持原验收期望，不删除失败、不降低 MUST。

## 审查范围

逐项判断 B01–B06：协议与接口、配置 / Keychain、Feishu OAuth / read adapters、LLM / embedding / rerank、DEV 证据、独立 QA 与整合就绪度。核查所有新增或修改文件，包括未跟踪测试、前端、OpenAPI、Swift 与文档。重点确认：

- Fake 默认、显式 Real 模式和设置 GET/PATCH 无网络副作用；
- 秘密只经安全本地入口 / Keychain，不进普通文件、API 返回、日志、HAR、截图或 Git；
- Feishu token 类型、scope、OAuth state / callback、refresh 轮换和注销边界；
- 未证实的材料 / 日历 / Task 日期、清空、写后核实能力是否仍禁用；
- 模型输入资格、注入边界、响应校验、超时 / 取消、费用边界、索引 fingerprint 与原子切换；
- Stage A 的确认、unknown/no-resend、原子写入和引用资格回归；
- 浏览器 / 原生证据和自动检查是否来自当前真实候选，而非旧 SHA。

可重跑适用离线检查和合成 UI 验证；不得调用真实 Feishu、DeepSeek、阿里云模型，不访问或更改用户 Keychain，不读取真实业务材料，也不把合成测试当真实外部验收。若环境不能提供独立 worktree，应明确记录。

## 用户新增授权（务必准确保留）

用户于 2026-10-10 表示可以提供各种 API key，并授权开始 Feishu 应用接入与有限的大模型冒烟测试。秘密目前在聊天中被遮蔽；不得猜测、回显或要求粘贴在聊天，之后只能由用户在本机安全设置 / Keychain 录入。

用户授权的最小 smoke 范围：

1. Feishu OAuth code exchange 最多一次；仅为验证授权 / token 接入，最多额外一次 refresh。用户在浏览器内自行完成账号授权；不读取用户资料、材料、日历或 task。
2. DeepSeek chat、Model Studio embedding、Model Studio rerank 各最多一次请求，输入仅用短小合成文本，验证连通性与协议，不评质量。
3. 当前提示词建议 smoke 总费用硬上限 CNY 5；这是保守操作上限，不是用户指定预算。执行 Luna 提示词必须要求先查当前官方价格 / 配额并记录单次、合计估算；无法保证不超过该上限时，暂停相应付费调用，只向用户询问预算上限，不重复询问是否愿意测试。
4. 本授权不含读取任何真实材料 / 日历 / task，不含向模型发送真实内容，不含 task 创建 / 修改 / 完成，也不含扩大请求次数或更换账号。

审查时不要实际发起这些 smoke 请求。若代码尚不具备安全条件，把 smoke 列为待下一位 Luna 实现 / 执行的明确任务；用户授权仍在，但不代表凭据已录入或实现已通过。

## 输出格式

先给一份简洁但有证据的评估报告：

1. 目标代码树 / 完整 SHA / dirty 状态和独立性边界；
2. B01–B06 逐项结果：PASS / FAIL / PARTIAL / NOT_RUN / BLOCKED，并引用具体文件、测试或 UI 证据；
3. 按 P0 / P1 / P2 排列的缺陷，写明复现或核验方法；
4. 自动检查命令及本次实际结果；旧报告数据不得冒充本次结果；
5. 真实 smoke 当前能否安全执行、缺少哪些实现或本地输入；明确未触达的真实服务和数据；
6. 是否已达固定 SHA 正式 B QA 的入口条件。不得因单测全绿宣称 B 通过。

报告后附 `给下一位 Luna 的执行提示词`，必须能独立复制使用，并：

- 引用你实际核对的 branch / SHA / 文件状态，要求 Luna 重新检查，不假定状态没变；
- 按 P0/P1 与 MUST 风险优先修复，然后完成未实现 B 项、离线验证、WebUI / 原生证据；
- 保留用户已授权的有限 smoke 边界和 CNY 5 建议上限，要求本地安全录入 keys；
- 明确禁止真实材料、真实 task 写入和额外模型调用；
- 当 B 实现完成后，由独立 QA 固定新 SHA 复验，再决定 PR / main 整合；Sol 的本次评估不能代替该正式 QA。

如果 Sol 确认当前代码树仍然 dirty，不要要求开发者现在把不完整候选合并；下一位 Luna 应先完成 B 实现并形成固定候选。
