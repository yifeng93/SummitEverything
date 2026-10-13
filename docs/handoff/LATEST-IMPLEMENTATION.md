# 最新实现交接

2026-10-13 最新技术状态：**C19 / 包2离线集成PASS，包1/3保持既有离线PASS；M3正式批准与合并待用户确认。** 固定产品源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07`，全新QA报告提交 `93bbf45e296abb7d2b234059138cf9f8cad84351`；85个不同C19回归、guarded后端491、Web56及适用静态/类型/构建与隔离生成检查通过，实际合成HTTP/SSE、Chrome UI完整/部分/零证据与history重开/重启通过。71项QA证据由Sol实际核对全匹配。见[独立QA](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)与[Sol最终技术门](../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md)。整合分支 `codex/c19-dsh-sol-gate`；main / M3冻结 / DSH交接不变且干净。本轮1/2返工收口，第2轮未使用。

未关闭风险：开发脚本Ctrl+C清理PermissionError/exit1，后验无残留服务或监听；不冒称清理全绿。真实服务/材料/凭据/Keychain、native/DMG、五日/双机/发布NOT_RUN，runtime UNVERIFIED、smoke未消费；本结论不能替代完整v1验收。下方日期状态为各SHA历史，不能覆盖本段。

2026-10-13 DEV/初验历史：C19 DSH 候选统一返工1/2由 Developer 完成并固定产品源码 **`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`**，DEV 自测 PASS，等待 Sol 调度全新独立 QA。guarded 后端 491 passed；C19/初验 holdout 执行 107 次、去掉字节相同矩阵副本后 85 个不同测试 ID；Web 56/12 与适用静态、类型、构建门 PASS。Fake loopback complete / partial / zero SSE 与 history reopen PASS。工作树 `/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-sol-gate/SummitEverything`，分支 `codex/c19-dsh-sol-gate`。代码 SHA 与文档 HEAD 分开列于 [DEV 报告与 evidence](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-DEV.md)；main、M3 冻结基线、DSH 交接目录未改。独立 QA 未运行，包2 / M3 未判通过，未合并。真实 provider / 服务、材料、凭据 / Keychain、native / DMG、五日 / 双机与发布 NOT_RUN；runtime UNVERIFIED。此前 `be4e72f` 的 QA FAIL 仍是历史固定 SHA 结论，当前状态以本行及后续 Sol QA 为准。

2026-10-12 DSH C19 repair 3 交接（**DEV PASS；独立 QA NOT_RUN**）。分支 `codex/dsh-c19-20261012`，工作树 `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012`，起点 `b3d0dff587c94ee295dfe5379bd67916c98184ec`，受测固定源码 **`be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`**（修复 `18fe80a`+`0107d58`+`be4e72f`；起点产品源码等同 `f79f613`）。修复请求外壳与主题内容的共享边界：信息性限定词（设备/年度/专项/工作）不再被 `_TOPIC_FILLER` 全局删除，`专项` 不再充当对象名后缀，伪对象 `的专项` 被拒绝，对象跨度与主题跨度分离。RED 12+22 矩阵 7 failed/27 passed → GREEN 34 passed；新增 tracked 回归 19 项；全量后端 469 passed、Web 56/12 与全部静态/构建检查 exit 0；隔离 loopback API/SSE 13/13 观测 PASS（含 partial/zero 与 history reopen）；DSH 子代理对抗性预验证发现的三项反例已在本轮修复，1 项标题/别名归属契约待 QA 判定。详见 [repair 3 DEV 报告](../quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-3-DEV.md) 与 [evidence](../quality/reports/evidence/2026-10-12-m3-package-2-c19-unified-repair-3-dsh-be4e72f/README.md)。下一步由 Sol 在另一个 checkout 对该 SHA 调度全新独立 QA；包 2 门、M3 正式验收与合并 main 仍待用户批准，历史 FAIL 不改写。真实服务/材料/凭据/Keychain、native/DMG、五日/双机、发布均 NOT_RUN；runtime UNVERIFIED；有限 smoke 0/1 未消费。
2026-10-12 DSH C19 repair 3 三轮预验收口：DSH 子代理在独立 checkout 对 `80cabed`、`9836365`、`7e772ea` 做了三轮对抗性黑盒预验证（**非官方独立 QA**）。第 3 轮（产品源 `be4e72f`）判定：产品树一致；冻结 34、tracked 19、全量 469、子代理 harness 27 项与 loopback 全 PASS；D2/D3/D4/D5 均已修复（D5 的 65 名矩阵相对基线 `f79f613` 0/65 行为改变）；唯一遗留 FAIL 为 D1「标题/别名元数据是否可把页面绑定到另一对象名」，已按计划「项目/页元数据可确定归属」声明为产品契约待定项，交 QA/Sol 判定。子代理 harness 与矩阵原始日志已存入 evidence 的 `subagent-preqa/`。

2026-10-12 收尾交接：用户要求更新文档、清理临时环境，并准备由 Deepseek Harness V4.1 flash 在独立分支尝试 C19。此次只做收尾，产品源码仍为 `f79f613a902758da3173a5b27219fa568a912f5e`，C19 独立 QA / Sol 仍为 FAIL；包 1 / 包 3保持既有离线 PASS，M3 正式门及合并未通过。交接固定引用为 `handoff/c19-dsh-2026-10-12`；下一位先读 `docs/handoff/DSH-C19.md` 和 `docs/handoff/2026-10-12-M3-CLEANUP.md`，不可从缺少 M3 的 main 开始修复，也不可在基线目录写源码。原 Sol / Luna 周期已停止；本轮未启动额外修复或 QA。

2026-10-12 最近受测结果（收尾前）：包 1、包 3保持各自离线集成 PASS；包 2 C19 统一修复 repair 2/2 在源码 `f79f613a902758da3173a5b27219fa568a912f5e`、QA 固定 `262f4eaa418d70f983f3b0b260d3635cd2e28c92` 上由独立 QA / Sol 判 FAIL（P1）。旧12项与纠正后9项holdout通过，新增矩阵15 PASS/7 FAIL同根因：信息性主题词被剥除，现有资料被错误判为缺失。450后端/Web56与静态/构建检查通过不能抵销产品失败。两轮自动返工已用完，停止自动源码修改、原周期已停止；M3正式验收和合并未通过。真实/发布门 NOT_RUN，runtime UNVERIFIED，smoke未消费。 见[Sol最终门](../quality/reports/2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)和[最终独立QA](../quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md)。

## 当前接续入口（2026-10-13 C19 候选返工）

C19 最新开发状态、固定产品 SHA、退出码和 evidence 清单见 [repair 1/2 DEV 报告](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-DEV.md)。下一步由 Sol 对固定产品 SHA `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 安排全新独立 QA；QA 应在另一 checkout 验收该 SHA，不在本工作树并行修改产品源码。QA 结论待出。

## 历史接续入口（2026-10-12 DSH 准备）

[DSH 完整交接](DSH-C19.md) 与 [环境清理记录](2026-10-12-M3-CLEANUP.md) 已准备。main 仍为 `5fd91c78930c80b2365957197b8a605757694a91`；M3 产品源码为 `f79f613a902758da3173a5b27219fa568a912f5e`。文档整理后的固定引用 `handoff/c19-dsh-2026-10-12` 只增加交接文档，未经产品修复、独立复验或正式合并。历史 `.local` 路径可能已归档，重新复演应使用 tracked evidence 的 harness 副本。

## 最近受测状态（2026-10-12）

### 包 2 C19：统一周期结束，repair 2/2 QA / Sol FAIL

产品源码 `f79f613a902758da3173a5b27219fa568a912f5e`；固定QA交接 `262f4eaa418d70f983f3b0b260d3635cd2e28c92`；QA-only提交 `2061b6260ece1b3887fc1ba34cc3960e61716b2a` 已导入功能分支。57项证据逐项经Sol匹配，生成物隔离核对通过，产品diff0/QA clean/服务停止。当前HEAD仅报告与状态文档增量，产品源码冻结。

原12及纠正后的9项holdout通过；新15 PASS/7 FAIL集中为未知主题“访客设备领用”被改成“访客领用”，现有正文无法匹配。真实浏览器/history reopen复现。自动450后端、Web56/静态/类型/lock/build与OpenAPI隔离生成PASS不改变C19 FAIL。完整材料见[最终QA](../quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md)和[Sol门](../quality/reports/2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)；历史失败不改写，旧harness中错误missing断言仅在副本纠正并加强完整/partial对照。

本次用户重新授权的统一周期已用完自动修复1/2、2/2，按AGENTS第62行停止源码修改并请用户决定。提议由Sol直接收口请求外壳与主题内容的归一化边界、主题内伪对象识别，再固定SHA交全新QA；尚未批准。主分支仍未合并，正式M3/真实门未通过，不重启旧Stage B、Stage C或M4/M5。

### M3 包 3：独立离线集成 PASS

产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`；QA 固定交接 `7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`；报告提交 `a251c6cb3bad8b99fdac8abb5b9f16dc7090092b`。分支 `codex/m3-integrated-packages`，开发工作目录 `/Users/yifengstudio/.codex/worktrees/m3-integrated-packages/SummitEverything`。后续 HEAD 为报告和门账本文档增量，产品树保持受测源码。main 未合并。

初验 FAIL 仅在 repair 1/2 的新 SHA 上关闭：Action 首次 running receipt 保存失败、整理 job 目录创建失败都立即清理 lease，异常 traceback 存活时仍无锁/无 provider 调用；同意图重试仅一次副作用。新 QA 独立后端 440、核心 99、资格/变更 37、Web 56 及静态/类型/lock/build/OpenAPI 检查通过；120 流程跨四月归档和 provider 重放计数通过。两 profile 实际浏览器查看共享待审稿、unknown及显式重处理提示通过。53 项证据哈希全部经 Sol 匹配；产品 diff 0、QA clean、服务停止。首次 fresh checkout 缺 Web 依赖的 runner 失败日志保留，npm ci 后全套通过。

本机 lease 不保证跨机同步锁；工作库轮流写入的产品边界不变。legacy undated记录不伪造完成日期，unknown不自动重发；原件和完整稿保留，恢复不自动批准知识。DevTools console/network/PNG、真实服务/材料/Keychain/native/DMG/五日/双机/发布 NOT_RUN，runtime UNVERIFIED，有限 smoke 各项保持 0/1。包 2 C19 P1仍阻塞整体 M3；用户已重新授权当前统一修复，仍未授权重要里程碑合并。旧 Stage B、Stage C 或 M4/M5不在此交接范围。

历史交接（extra 1）：当时记录包 2 repair 2/2 QA FAIL 后用户批准一轮额外修复，源码固定 `bb997a42ed1d218e10527e3e07e6c587fc9929f6` 并等待独立 QA。该状态已由本文当前状态与 extra 2 交接取代；Sol 后续门与 QA 结果见 extra 1 历史报告。

### 包 2 extra 2 Developer 交接（历史 DEV；QA 已 FAIL）

extra 2 起点 `09fd94c6127cdd4bb60827a102446cb352eb32be`，产品源码提交 `c41147fe54bf95103c741df192fc76eb9df0f9e7`，分支 `codex/m3-integrated-packages`。本轮是用户在 extra 1 QA FAIL 后明确批准的唯一追加轮次；README 全量自动检查已完成，日志及 `.exit` 在 `.local/dev/m3-package-2-extra-2/raw-logs/`。行为、命令和复演范围见[extra 2 DEV 报告](../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-2-DEV.md)。QA 后由 Sol 判 C19 P1 FAIL；该 FAIL 保留，包 2 当前未获准修复。

C19 的无引用诊断现区分无相关证据、资格/hash 排除和生成期间页面变化；missing 与主文同步。fresh ready index 的无关查询不会误称缓存问题；hash 不匹配仍报告版本/资格原因，页面在生成中不可读先报告不可用。三种回答模式及零 provider 调用回归见固定源码。QA 已判 FAIL，用户明确直接开始包 3；本轮不继续修复包 2。

### 包 2 extra 1 Developer 历史交接（已 QA FAIL）

extra 1 起点 `36a0cc32757f761bd1c31abcddde07f1a2a426c6`，源码提交 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，分支 `codex/m3-integrated-packages`。文档-only 交接提交会另行固定；Developer 工作区收口后 clean。额外轮由用户明确批准，仅此一轮，历史 repair 1/2、repair 2/2 计数不重置。实现和自测说明见[extra 1 DEV 报告](../quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)，日志与真实 `.exit` 位于开发 checkout 的 `.local/dev/m3-package-2-extra-1/raw-logs/`（本地忽略目录，不提交）。

本轮分离页面“内容批准 hash 有效”与 `current / superseded / invalid` 知识效力：阅读端用统一 `retrieval_eligibility(..., HISTORY)` 检查批准证明/当前正文 hash，页面 validity 独立显示；PageWriter 允许确认 invalid 但仍保持其 invalid 效力。外部编辑产生的真实 hash mismatch 仍显示待确认并保留版本警告；current/history 查询资格门没有放宽。记忆候选仅在真实 user 历史、精确原文跨度及明确 user-expression 声明基础上创建；API 再检查候选跨度附近的 source attribution / quote framing，不因“资料 / 引用 / 来源”一般词汇拒绝自然第一人称偏好，也不会接受从“材料原文：‘我偏好…’”截取出来的本人式片段。候选仍为 pending，必须另行确认才进入 active。

Developer 自测：guarded pytest 407 passed，Web 55 passed / 12 files；Ruff check/format、mypy 40 files、uv lock/build、OpenAPI type generation、Web typecheck/lint/build 全部 exit 0；安装 `npm --prefix web ci` 126 packages / 0 vulnerabilities，`uv sync --locked --group dev` exit 0。保留 1 条既有 Starlette/httpx deprecation 与 2 条既有 React lint warnings。新增 C13/C20 单元/API/组件回归见 DEV 报告；这些是自测，不代表 QA 或包级通过。

全新 QA 请固定产品源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，独立 checkout 后按此前 repair 2 QA/evidence 的完整 C13/C14/C19/C20/C21 与 README/browser 复演范围进行整包验收。重点实测已批准 superseded 和 invalid 页打开状态、hash 相同与真实外部编辑 mismatch / 再确认、CURRENT 不引历史页与 HISTORY 效力标记；通过真实 user message 创建自然偏好（至少包含“资料”“引用来源”）候选，并验证其只进入 pending、显式确认后才 active；材料 attribution quote 内的“我偏好…”截取、转述/粘贴、assistant source、fake message ID 仍拒。回归早期礼貌事实主体、多轮指代、资格复核、comparison / plan 多资料、角色/记忆预算和 replay。保留所有历史 FAIL，不修改旧 QA 报告、不降低验收门。若本次 QA 仍 FAIL，用户额外额度已耗尽，停下交 Sol/用户决定。真实模型/服务、材料、凭据/Keychain、native/DMG、五日/双机及发布门 NOT_RUN，runtime UNVERIFIED。

### repair 2 Developer 历史交接（本轮 QA 结束前）

M3 包 1 会话与历史已由 Sol 判离线集成 PASS；包 2 完整问答、角色与记忆的最后自动修复轮次 repair 2/2 已完成 Developer 自测，源码固定于 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15`，全新独立 QA 待 Sol 调度。repair 1 QA 仍是其固定 SHA `0df323efc26e388d62f234e0471f853b2b54be4d` 的 FAIL；首轮 QA 与 repair 1 QA 原报告和证据均保留，Developer 自测不构成 QA PASS，Sol 尚未判包 2 状态。当前分支为 `codex/m3-integrated-packages`。

repair 2 处理 repair 1 QA 的主体精度遗留缺陷：礼貌自然请求中的真实语料主体可以匹配，不把整个前缀当作过滤实体；连续指代从最多 8 条真实 user question 倒序找最近主题，跳过纯指代，但“那朱雀项目的预算呢？”等包含明确或未知主体的指代式换题会建立边界；完整无主题问题也会截断旧主题。subject hints 每次从当前 manifest 与 HISTORY 资格有效的页面重建，不持久化 NLP/别名索引；候选主体匹配还使用已通过本轮资格/expected hash 的正式页标题、别名和归属 project/line 名称，仅用于筛选，不伪装成引用正文。assistant 历史仍不是检索证据；每轮重新核对当前/历史资格、hash 和引用效力。未知主体仍安全返回无引用缺资料结果，comparison / plan 继续允许跨材料检索。完整实现和开发者测试边界见[repair 2 DEV 报告](../quality/reports/2026-10-12-M3-PACKAGE-2-REPAIR-2-DEV.md)。

包 2 原始实现源码 SHA `daef5250b355179de93cc3d622b93e9b28f17286`，repair 1 QA 固定源码 `0df323efc26e388d62f234e0471f853b2b54be4d`，当前 repair 2 固定源码 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15`。repair 2 全量自测：guarded pytest 405 passed；Web 52 tests / 12 files；ruff、format、mypy（40 source files）、lock check、uv build、OpenAPI 类型生成、Web typecheck/lint/build 均 exit 0。保留 1 条 Starlette/httpx deprecation 与 TodayView / ProjectsView 两条既有 lint warnings。日志和真实退出码位于 `.local/dev/m3-package-2-repair-2/`。repair 1 和 repair 2 的 DEV/QA 链见[报告索引](../quality/reports/README.md)；repair 1 的失败并不被本轮自测覆盖。

新 QA 应固定 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15`，重跑首轮报告 QA-1 至 QA-4 及 repair 1 报告的范围历史与修复项，并验证 repair 2：自然礼貌事实问句返回合格引用；青岚→“它呢”→“它什么时候启动”不混入朱雀；“那朱雀项目……”明确换题、未知主体与无主题完整问题边界；标题、显式 alias 或 manifest project 名是唯一主体线索时 fresh index 仍引用该正式页且不把名称添加到 excerpt；页面改版后旧 chunk/hash 失效；比较与 plan 仍跨材料。每轮资格复核、角色/记忆、幂等重放和 API/UI 行为按原 QA 报告验收。沿用原报告中隔离 Fake workspace / MockTransport harness，在 QA 独立 checkout 按报告步骤启动本地服务；QA 不在此开发 checkout 改实现或 tracked tests。

历史 repair 2 交接当时记录：包 3 尚未开始，repair 2 是当时已授权的最后修复轮。该状态已被当前包 2 C19 P1 FAIL 及用户直接开始包 3取代；不能用作当前执行指令。真实服务/材料/凭据、Keychain、native、DMG、五日、双机与发布门保持 NOT_RUN，runtime UNVERIFIED。

包 1 QA 覆盖包括真实浏览器新库首问/历史重开续问、SSE complete/cancel/non-empty partial restart、updated/unavailable/superseded 部分引用资格，以及 profile/workspace 隔离。包 2 还需由独立 QA 复核多轮上下文 provider payload 与 request hash、新旧会话 schema 兼容、角色/记忆上下文预算、确认来源与跨 profile 隔离。

**M3 包 1 历史报告链：** [初次 DEV](../quality/reports/2026-10-11-M3-PACKAGE-1-DEV.md) → [首轮 QA FAIL](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md) → [repair 1 DEV](../quality/reports/2026-10-11-M3-PACKAGE-1-REPAIR-1-DEV.md) → [repair 1 QA](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md)。

## 2026-10-11 C03 删除拒绝提示本地化（已合入 main；离线切片 PASS）

针对历史 M1 C03 P2，非空主线（有项目 / 目录有内容）及非空项目的删除拒绝提示已中文化。源码 SHA：`9c953f095086a95e63edbce2169657dba9e71cd1`；固定 QA 提交 `141bd96d15039f1cd29461785fdd91e2ef297476` 独立验证了 37 项定向回归与本地 Fake WebUI 浏览器流程。规范和 C03 随 [PR #11](https://github.com/yifeng93/SummitEverything/pull/11) 合入 main，merge SHA：`2f08c764e740afa494a0445ec4d73382fdd55f3b`。完整文档候选 `75bfe2548e947432e72767b0b7822d34685a8b61` 保留 QA 证据和工作流决议；合并后独立报告确认两个源码树相同。

Sol 判定 C03 离线切片首轮 PASS、repair 0/2。报告链：[DEV 报告](../quality/reports/2026-10-11-C03-DELETE-COPY-DEV.md)、[固定源码 QA](../quality/reports/2026-10-11-C03-DELETE-COPY-QA-141bd96.md)、[文档整合 QA（受测 `75bfe254…`）](../quality/reports/2026-10-11-C03-INTEGRATION-QA-75bfe25.md)、[合并后 QA（受测 `2f08c764…`）](../quality/reports/2026-10-11-C03-POSTMERGE-2f08c76.md)。固定源码 QA 使用 CUA 观察但没有导出截图；API envelope 由 contract tests 断言。此次合并后全量 guarded pytest 为 389 passed，lock、祖先关系、产品树一致性和既有证据校验通过。合并后没有重跑 Web、浏览器或 native；本轮相关状态按报告为 NOT_RUN。此切片不重开完整 M1，也不改变 Stage B 既有范围。真实 provider、真实材料、OS Keychain、DMG、五日、双机及 M3–M5 仍 NOT_RUN。

用户已确认的长期 Sol→Developer Luna→全新 QA Luna→Sol 流程及历史安装版 overlay 补丁均随 PR #11 进入 main，见 [ADR 0008](../decisions/0008-sol-luna-development-workflow.md) 与[历史补丁](history/2026-10-11-SOL-LUNA-INSTALL-OVERLAY.patch)。原主 checkout 的额外 stash `02c4801bc623ac2304bee18cceee64f4795602d8` 仍保留，供需要时恢复 overlay；历史安装文字不能用来重启已完成的 Stage B。main 已 fast-forward 到本次记录的 merge SHA，且 clean。

上述 C03 记录发布时的“推荐下一项 M3.1”状态已由本节顶部 M3 包 1 交接取代。Stage B 离线源码结论仍仅覆盖当时离线源码和开发壳，不延伸为 M3 或完整 v1 验收。

## 2026-10-11 Stage B 离线源码已合并

2026-10-11：Stage B 离线源码收口候选 `576895f6983ca41cacbbad45a9075b97b9986189` 已由 Luna High 在独立 checkout 复验：后端388项与25项独立失败路径通过，Web45项及类型/构建检查通过；实际浏览器、原生冷启动、重启、5秒Web启动延迟与退出清理已复验。已合入main（PR #10，merge `41207e5bfb81b535c0254fd4ac242df11da40d67`），合并后核验、证据发布更正及归档清理见[收口记录](../quality/reports/2026-10-11-STAGE-B-POSTMERGE.md)。已采纳 DeepSeek R1–R4 中经复核的实现，并修复传输取消/资源所有权/大小边界、未知refresh跨重启重发、严格凭据解析和原生就绪问题。历史FAIL与原始证据保留。此结论仅覆盖当时离线源码和开发壳；真实账户/协议运行、OS Keychain、模型R03质量、DMG、M4/M5、五日/双机仍NOT_RUN，不能称完整Stage B或v1验收通过。保留当时的Starlette弃用及3条React lint warning。

- 起点文档提交：`0a1db5d72e6ac11184d28e65dea3ba008762ba43`，上一源码 `7dc7114595704f34ba386c96324dffa77d529ba4`；两者产品源码无差异。
- 固定受测源码 SHA `576895f6983ca41cacbbad45a9075b97b9986189`；main已包含受测提交，试验/QA工作树归档后已清理。
- [最终后端复验](../quality/reports/2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md)、[最终实际UI复验](../quality/reports/2026-10-11-STAGE-B-LUNA-UI-RETEST-576895f.md)、[根URL修复DEV](../quality/reports/2026-10-11-STAGE-B-NATIVE-URL-DEV.md)。
- [严格标记DEV](../quality/reports/2026-10-11-STAGE-B-STRICT-MARKER-DEV.md)、[原生双服务readiness DEV](../quality/reports/2026-10-11-STAGE-B-NATIVE-READINESS-DEV.md)、[8b后端复验](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-RETEST-8b6259a.md)、[8b原生FAIL](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-UI-RETEST-8b6259a.md)。
- [刷新重启修复DEV](../quality/reports/2026-10-11-STAGE-B-REFRESH-RESTART-DEV.md)、[首次独立QA FAIL](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md)。
- [Sol DEV 收口报告](../quality/reports/2026-10-11-STAGE-B-SOL-CLOSURE-DEV.md)、[ADR 0007](../decisions/0007-request-owned-provider-transport.md)、[协议矩阵](../architecture/PROVIDER-PROTOCOL-MATRIX.md)。
- 独立 QA 使用固定源码 SHA、独立环境、外网/DNS/Keychain guard；允许替代 SecretBackend 与外部 HTTP，保留 route/service/存储/协调器/租约/索引真实实现。
- 需覆盖：资格/发布前复核、取消后不得开始后续调用、完整请求/响应限额、DNS/TCP/TLS/头/正文超时与无后台请求、并发不误伤、logout/callback/refresh/配置重建竞态、scope/格式/分页/截断、凭据拒绝/损坏/重启、真实写门、Fake 回归及实际浏览器/原生。
- 默认 Fake；真实 Feishu 数据读取为显式 `real_data_enabled=false`，真实任务写恒禁用 `result_proof_unavailable`，真实模型业务由服务端拒绝。项目进度仍需本地独立确认。
- 旧真实凭据迁移不在本轮范围：无真实调用/凭据迁入；缺消费标记的旧形状无法追溯历史，未来导入/恢复未知消费历史需先重新授权，不能当作安全未消费。
- user-info `user_identity_verified=false`；OS Keychain、真实 scope/数据/模型质量、DMG、M3–M5、五日和双机均 NOT_RUN。

已有有限 smoke 授权保持：code exchange ≤1、必要 refresh ≤1、DeepSeek chat / embedding / rerank 各 ≤1；实际次数全部 **0/1**。不索取或使用密钥，不读取真实身份/材料/日历/task，不执行真实任务写入，也不因新 profile 重置次数。真实材料另有内容确认门。CNY 5 为旧提示词建议操作上限，不是用户指定预算；真正使用既有授权前须核对官方当前价格。

## 历史交接：M2 阶段 A — 以下 SHA / 检查只对应当时版本

### 恢复路径 UI 补验（2026-10-10）

- **固定基线与修复代码：** 补验从当时 `main` 固定 SHA `409b90704046c623184846c09c873cec053e946d` 开始；该 SHA 在 C18 local-writer receipt 恢复后出现同一动作同时显示成功和“仍为未知”的 P2 UI 矛盾。执行者单独提交修复 `30903c4cdf73855af71a201e3edea6c535ee8199`，只涉及 TasksPanel 状态文案和组件回归测试。
- **独立报告链：** 固定 409b 的补验初报 `6eaf71d6c4e0ddf74b8c532d652296cb6a35b8d0` 保留 C18 UI FAIL。后续脱敏 / 证据清理提交依次为 `eae0f22dce4c7f15d97bd7d5cc1e17f7d7b148f4`、`1d62e24`、`1f0639a`；初报的当前证据树 manifest SHA-256 为 `64f77d13a0bcc0f9b1a4089641df056937647e5b375c3ab3925dab49349f8c10`。独立验收者将新 SHA 的复验报告提交为 `2d6254c4c2717857fda8ccaa97c210b41e0c695e`，再将其以 cherry-pick 方式串接进同一 QA 分支，分支报告树提交 `998b4d2fa1165cecb71c9baf8ff6610a516d3df0`。309 证据 manifest SHA-256 为 `599190944efaf82861b5d571b2364524ec1a06829d5055b1cadd0f0b6453e66f`。报告及可复演 harness 位于 `docs/quality/reports/` 与相邻 `evidence/` 目录。
- **补验结论：** 固定 409b 的 C16 崩溃后 unknown→只读核实成功、确认状态、双击及真实重叠请求 UI 过渡均 PASS；C23 manifest replace 前原子写中断后 unknown/no-resend PASS。固定 309 的 C18 receipt-loss→restart unknown→只读核实 succeeded→同 ID replay PASS：UI 只显示成功，本地 manifest / progress_version 重放前后不变。固定 309 的 C23 no-proof 负对照仍为 unknown。自动测试未在独立复验中重跑，状态为 NOT_RUN；实现者对 309 修复提交的组件与指定集成测试自测见其提交记录。该补验不改变原固定 409b 初报的 FAIL 事实，只表示缺陷在新 SHA 已整改并复验。
- **证据限制与范围：** 两轮均为隔离浏览器、合成工作库与 Fake providers；最终 309 复演全程仅观察到 loopback sockets。409b 初次候选 Chrome曾连接本机代理 `127.0.0.1:7890`，无法证明代理是否转发，故初报保留该限制。没有有意调用真实飞书、模型、业务材料或凭据；本轮没有真实业务外部操作。独立 UI console/network、请求响应、磁盘指纹、同一 action_id 与撤回重复截图说明见报告。该补验不重跑原生壳或整体 Stage A 自动矩阵。
- **合并后核验：** PR #7 以 merge commit `c655eb48f5ce7448edac77c0250f9ed9d2ac8e33` 合入 main；SSH 读取的远端 `main` 在本次核验时为该 SHA。独立 detached checkout 固定于该 merge commit，确认 `30903c4cdf73855af71a201e3edea6c535ee8199` 为祖先，且 `src/tests/web/native` 与受测修复 SHA 完全一致；两份补验报告均存在，47 项和 26 项 manifest 均逐项匹配。之后仅文档 ledger 更新不改变受测源码树。阶段 B/C 与 M3–M5 未开始。

- **该轮代码 SHA：** `32da67e9c0280e3dae18fd374e30c925565b0b82`，分支 `codex/m2-stage-a-closeout`，基线为原 M2 交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。
- **原候选：** `09398fcae597b2478001d40aedf580ea91322c11`。原候选 QA 测试与报告提交 `f64c565b7c5105867e0c19e7e1e716dc726f8ff7`；A-01 P0、A-02–A-04 P1、A-05 P2 复现结果见 [原候选定向 QA](../quality/reports/2026-10-10-M2-stage-a-original-qa.md)。报告结论保持原样。
- **该轮状态：** Fake-only M2.1–M2.3 阶段 A 已由独立 QA 在固定代码 SHA `32da67e9c0280e3dae18fd374e30c925565b0b82` 复验通过；最终报告提交 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`。原候选缺陷初验及后续各轮复验报告均保留，结论与受测 SHA 对应。
- **初始文档 checkpoint：** M2 核心规格 checkpoint `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`；执行交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。该轮文档已在修复代码后提交；最新基线见本文顶部。
- **自测摘要：** Python 142 passed；Web 8 files / 32 tests；Ruff、format、mypy、lock、uv build、OpenAPI 类型生成、typecheck、lint、web build 与 Swift build 退出 0。保留 1 条既有 Starlette/httpx 弃用警告和 3 条既有 React effect lint 警告。以上不是独立 QA 结论。
- **独立验收摘要：** A-01–A-05 与阶段 A Fake-only MUST 场景通过；未关闭 P0/P1/P2=0。浏览器 Fake 流程和 console、原生开发壳归属 / 窗口 / Quit / 退出清理均有独立报告和证据。API 没有 OAuth cancel UI 控件的变体记 NOT_RUN，API denial 已覆盖。
- **合并与合并后核验：** PR #4 以 merge commit `0789f9ebfee4a0352e2818510055a252ba374daf` 合入 main。独立 checkout 固定于该 SHA，自动检查全绿；Python 142 passed、Web 32 passed，另有关键路径 8 项冒烟通过。合并树 `src/tests/web/native` 与 QA 固定源码树一致。详细命令和结果见[合并后核验记录](../quality/reports/2026-10-10-M2-stage-a-postmerge.md)。
- **阶段状态：** Stage A 的 Fake-only 模拟范围 QA、PR 合并和合并后核验已完成；真实 provider、材料和发布门仍 NOT_RUN，不包含在本阶段结论内。
- **真实门：** 当前只有 Fake providers；本轮未访问真实 Feishu、付费模型、真实业务材料或 Keychain，未执行 DMG、五日或双机验证。用户备好的真实资源未被消费；真实门继续 NOT_RUN。
- **阶段边界：** 未启动 M3–M5；该轮结束时等待技术评定；现已收口，B/C 入口见顶部。

以下 `M1` 区域为历史交接记录。

下文保留 M1 独立 QA 历史。

## 固定候选

- **阶段：** M1.1–M1.5 DEV、独立模拟验收及 main 合并后检查均通过。
- **首次 QA 固定代码 SHA：** `73ec81a06f2557c006f98ff88fa81b08d14ef315`。
- **当前修复候选代码 SHA：** `f349fe6cb5da86c3fdafff11738e2a55335d8874`。
- **合并提交：** `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`（PR #1，merge commit；远端 `main` 已包含受测代码）。
- **分支：** `codex/m1-close`。
- **材料边界：** 只用隔离模拟工作库与 Fake providers；没有导入真实“场地与酒店”材料、付费模型或真实飞书。
- **DEV 自测记录：** [2026-10-09-M1-close-DEV.md](../quality/reports/2026-10-09-M1-close-DEV.md)（已提交，不是独立 QA 报告）。详细隔离运行记录另保存在 ignored `.local/m1-close/evidence/dev-self-check.md`。
- **独立 QA：** 首轮发现 C03 P1，已由执行者修复；同一 QA 在新 checkout 的 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 上复验通过。报告：[首次失败记录](../quality/reports/2026-10-09-M1-close-73ec81a.md)、[最终复验报告](../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。M1 模拟范围 P0/P1=0；报告记录 1 个 P2 英文删除拒绝提示及后续本地化安排。
- **合并后验证：** 在远端 `main` merge commit 的独立 checkout 上，后端 77 项、前端 10 项、OpenAPI 类型生成、类型 / lint / 构建、lock、uv build 与 Swift build 全通过；远端 `main` 包含受测 SHA 与两份 QA 报告。

## 修复摘要

- 修复 C05：来源状态由最新整理作业和关联稿件派生并持久化，覆盖 pending、processing、reviewing、completed、failed、cancelled；正在整理或仍有待审稿的来源不能用新 operation ID 另起作业。失败、取消或全部处理完成后，只有显式 `reprocess=true` 才能重新整理；相同 operation ID 按原意图幂等重试。
- C06：用户先选一个项目，一份多主题来源可生成多份稿件，逐份确认并保持完整来源关联；不进行自动跨项目分流。
- C07：未决或选择结果会写入最终正文，未决内容明确标为未确定；稿件编辑区预览结果。
- C08/C10：真实 UI 显示外部版本差异、阻止覆盖；保留稿件、显式比较基准、重新确认后，索引重建并恢复最新正文检索。
- C03/C13/C14 的 M1 部分：既有测试覆盖归档知识检索、非空删除保护、失效 / 被替代内容区分、SSE 顺序 / 唯一终态 / 取消不伪装完成。
- C03 初次 QA 暴露的界面缺口已修复：稳定 ID 重命名、归档项目查看 / 恢复、仅空目录可删除、页面移动及新增相对链接后明确确认。新增 ProjectsView / PageReader 界面回归；QA 已在真实浏览器复验移动、引用修复和链接确认。
- C11/C12/C23 的 M1 部分：旧版本资格门、邻页复核、索引 fingerprint 变化与失败重建保护、原子写恢复和同意图重试由自动测试覆盖；QA 已对固定候选完成 M1 范围复验。
- 本地开发壳：API / Web 端口与 profile 可隔离；run identity 防止误连其它 checkout 服务；runner 只清理自己启动的进程组。正常 Quit、最后窗口关闭、`swift run` Ctrl+C 均以本轮独立端口复演并确认无监听残留。

## 启动与检查

```sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
```

默认 API `127.0.0.1:8793`、Web `127.0.0.1:5173`。并发隔离可设 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT`、`SUMMIT_API_TARGET`、`SUMMIT_PROFILE_ROOT`。访问 `http://127.0.0.1:5173`。原生开发壳：`cd native && swift run`。

固定修复候选 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 与合并后的 main 树均完整复跑：后端 77 passed；前端 5 个测试文件 / 10 项测试；OpenAPI 类型生成、typecheck、lint、production build、ruff check / format、mypy、lock check、uv build、Swift build 均退出 0。保留 1 条 Starlette/httpx 弃用提示及 3 条既有 React effect lint 警告。

## 真实 UI 复演

完整隔离路径和步骤见 DEV 自测证据。真实浏览器复演覆盖 C06 的单项目多稿、部分与全部确认；C10 外部编辑、旧证据失效、重新确认及增量索引恢复；C08 目标外部变化的冲突保护、稿件保存 / 重新确认及最新正文检索。材料全部是本地合成文本。

## 尚未完成或未测

- M1 独立模拟验收已通过，详情按案例见最终复验报告。受测实现固定 SHA 为 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；执行者后续提交均为文档和 QA 报告导入。
- C13 历史会话 UI、C14 断流恢复 / 历史引用 UI 属 M3；C25 DMG、干净机器安装和发版身份属 M4；均不得记作 M1 PASS。
- 真实“场地与酒店”材料确认、真实模型质量、真实飞书权限 / 写入、五个实际工作日、双机往返未测且需要各自授权门。
- 1 条 Starlette/httpx 弃用提示和 3 条前端 effect lint 警告保留；未通过隐藏警告或降低期望获得绿灯。

## 合并后检查记录

- PR：[SummitEverything M1 closeout](https://github.com/yifeng93/SummitEverything/pull/1)，以 merge commit 合并至 `main`。
- 合并提交 SHA：`4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`；已确认该树包含受测代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 和 QA 报告提交 `0fd0102ad8a22fae336339e7fd635acc15438224` / `49ce008446339c723b83ee39cfe3e2ae029b4437`。
- 在该 main 树复跑：后端 77 passed，ruff check / format、mypy、`uv lock --check`、`uv build`、OpenAPI 类型生成、前端 10 tests、typecheck、lint、production build、Swift build 均退出码 0。保留 Starlette/httpx deprecation 和 3 条既有 React effect lint 警告。
- 合并后服务端口和 UI 服务均未启动；真实材料、模型、飞书、DMG 与多设备门仍未测。

## QA 交接

独立验收在源码仓库外的 `/Users/yifengstudio/.codex/worktrees/qa-m1-close-r3` 固定到 `f349fe6cb5da86c3fdafff11738e2a55335d8874`。报告与隔离模拟 UI 证据已保存；不修改产品实现。M2/M3/M4/M5 场景和真实外部门按最终复验报告保持 NOT_RUN。

## 下一阶段

此处保留阶段 A 开始前的历史交接状态：当时 M2.1–M2.3 等待固定 SHA 独立 QA，原代码 SHA 为 `09398fcae597b2478001d40aedf580ea91322c11`，核心文档 checkpoint 为 `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`。最新阶段状态见本文件顶部；真实资源的边界与 M3–M5 暂缓决议仍有效。
