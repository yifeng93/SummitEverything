# 开发与独立验收报告索引

2026-10-12 DSH C19 repair 3（**DEV PASS；独立 QA NOT_RUN**）：[DEV 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-3-DEV.md)与 [evidence](evidence/2026-10-12-m3-package-2-c19-unified-repair-3-dsh-0107d58/README.md)。用户指定 Deepseek Harness V4.1 flash 在分支 `codex/dsh-c19-20261012` 独立试修；起点 `b3d0dff587c94ee295dfe5379bd67916c98184ec`，受测固定源码 `0107d581487345c85a4406cf4b17f772fa795a28`。修复请求外壳与主题内容的共享归一化边界：信息性限定词（设备/年度/专项/工作）不再被全局删除，`专项` 不再充当对象名后缀，伪对象 `的专项` 被拒绝，对象跨度与主题跨度分离。RED 12+22 矩阵 7 failed/27 passed → GREEN 34 passed；新增 tracked 回归 18 项；全量后端 468 passed、Web 56/12 与静态/构建检查全部 exit 0；隔离 loopback API/SSE 13/13 观测 PASS（含 partial/zero 与 history reopen）。DSH 子代理对抗性预验证另发现三项反例（礼貌查词伪对象、`term:` 泄漏、截断措辞），已在本轮修复并加回归；1 项标题/别名归属契约问题保留待 QA 独立判定。历史 FAIL 不改写；本轮不宣告 C19/M3 通过、不合并 main。独立 QA 由 Sol 在另一个 checkout 对固定 SHA 调度。

2026-10-12 收尾交接：用户要求更新文档、清理临时环境，并准备由 Deepseek Harness V4.1 flash 在独立分支尝试 C19。此次只做收尾，产品源码仍为 `f79f613a902758da3173a5b27219fa568a912f5e`，C19 独立 QA / Sol 仍为 FAIL；包 1 / 包 3保持既有离线 PASS，M3 正式门及合并未通过。交接固定引用为 `handoff/c19-dsh-2026-10-12`；下一位先读 `docs/handoff/DSH-C19.md` 和 `docs/handoff/2026-10-12-M3-CLEANUP.md`，不可从缺少 M3 的 main 开始修复，也不可在基线目录写源码。原 Sol / Luna 周期已停止；本轮未启动额外修复或 QA。

2026-10-12 最近受测结果（收尾前）：包 1、包 3保持各自离线集成 PASS；包 2 C19 统一修复 repair 2/2 在源码 `f79f613a902758da3173a5b27219fa568a912f5e`、QA 固定 `262f4eaa418d70f983f3b0b260d3635cd2e28c92` 上由独立 QA / Sol 判 FAIL（P1）。旧12项与纠正后9项holdout通过，新增矩阵15 PASS/7 FAIL同根因：信息性主题词被剥除，现有资料被错误判为缺失。450后端/Web56与静态/构建检查通过不能抵销产品失败。两轮自动返工已用完，停止自动源码修改、原周期已停止；M3正式验收和合并未通过。真实/发布门 NOT_RUN，runtime UNVERIFIED，smoke未消费。 见[Sol最终门](2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)和[最终独立QA](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md)。

## 收尾清理证据（不改变产品门）

[清理记录](../../handoff/2026-10-12-M3-CLEANUP.md)、[DSH 专项提示词](../../handoff/DSH-C19.md) 和 [14项收尾核证](evidence/2026-10-12-m3-cleanup/verification.json)。只整理文档与本地环境，产品源码和旧证据不变，没有新产品 QA。

## 最近 C19 周期：最终 repair 2/2 FAIL，原周期停止

[Sol最终门](2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)核证[最终独立QA](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md)：固定源码 `f79f613a902758da3173a5b27219fa568a912f5e`，QA `262f4eaa418d70f983f3b0b260d3635cd2e28c92`，57项manifest匹配；原12+纠正9项通过，新结构矩阵15 PASS/7 FAIL同归一化P1。450后端/Web56/静态/构建与隔离OpenAPI生成PASS；浏览器真实复现并history reopen保留。两轮自动返工均已结束，停止源码修改，未批准第三轮或M3正式合并。

[repair2 DEV](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-DEV.md)保留当时自测/待QA记录；后续结果以固定SHA独立QA与Sol门为准。此前的初验、repair1 FAIL及更早extra历史不撤销；旧错误missing断言的纠正只在独立副本进行，原证据未改。

## 包 2 C19 统一修复 repair 1/2（2026-10-12，历史 DEV 与独立 QA 完成；P1 FAIL）

[C19 repair 1 DEV 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-1-DEV.md)：固定源码 `df1aac288a002e86a24132a9954fbe0b18d41d1f`。unknown information topics 按 exact scope 处理；礼貌请求、对象名内含维度词、无“的”并列、主题有资料/缺资料、开放属性问题和泛化方案均有回归。Developer 自测 qualified retrieval 27 passed、QA holdout 12 passed、guarded pytest 449 passed、Web 56 tests / 12 files。全新 QA 固定该产品源码复跑全矩阵，发现 `(白鹭工程,预算)` 与 `(赤陶项目,活动证章领取)` 被折成同一缺失范围，三种回答模式均漏掉两份已有依据，判 P1 FAIL；旧 QA 12 项与本轮共享维度正控通过。见[C19 repair 1/2 QA 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-1-QA-04a0239.md)及 evidence。统一候选初验和先前 extra 2 P1 FAIL 与原报告/证据保留；Sol 可协调 repair 2/2；M3 未正式通过。

## M3 已判门与历史失败（2026-10-12）

[包 3 Sol 门判断](2026-10-12-M3-PACKAGE-3-SOL-GATE.md)：产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f` 的 repair 1/2 已由全新 QA 固定 `7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2` 复验，Sol核验53项manifest、真实退出码及源码diff0后判包3离线集成 PASS。[独立复验报告](2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md)、[初验 FAIL](2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md)与所有原始证据保留。包2 extra 2 的[最新 C19 P1 FAIL 门](2026-10-12-M3-SOL-EXTRA-2-GATE.md)继续作为历史 QA 结论；当前重新授权的候选状态见上方 DEV 报告。M3正式验收和合并未通过。

## M3 功能包 3 repair 1 Developer（2026-10-12，历史 DEV；后续独立 QA PASS）

[repair 1 DEV 报告](2026-10-12-M3-PACKAGE-3-REPAIR-1-DEV.md)：初验 QA 固定源码 `22e5ad9` 在 C22 发现 action running receipt 保存失败后 lease 依赖 GC 才释放；初验报告与证据见[固定 SHA QA](2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md)。repair 1 固定源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`，为 action running receipt 发布与 intake job jobs-directory 创建两处 acquire 后发布前异常路径补显式 lease 清理，并新增异常 traceback 保持存活时的回归。定向集成 105 passed、全量 guarded pytest 440 passed；Ruff/format/mypy/lock/build exit 0。120 条 FakeLLM 流程复跑后 active lease 0。此段为当时 DEV 自测；随后新 SHA 已完成独立 QA，当前门见上方 Sol / QA 报告。包 2 C19 P1 FAIL 不变。

[初验包 3 DEV 报告](2026-10-12-M3-PACKAGE-3-DEV.md)：受测源码 `d03c548b69a4ec48a947486df191bd4af009b6e2`；初验 QA 的 lease 缺陷已由上述 repair 1 处理。其 438 后端 / 56 Web 自测与 120 条 bulk 统计仍为该历史源码的 Developer 记录，当前修复 SHA 及检查见 repair 1 DEV 报告。

## M3 功能包 2 extra 2 Developer（2026-10-12，QA FAIL 历史）

[extra 2 Developer 报告](2026-10-12-M3-PACKAGE-2-EXTRA-2-DEV.md)：用户明确批准的额外修复轮，固定产品源码 `c41147fe54bf95103c741df192fc76eb9df0f9e7`。修复 no-evidence 诊断不再把新鲜 ready 索引内的无关查询说成缓存/hash/资格故障，并区分资格/hash 拒绝、生成期间内容变化和页面不可用；三模式主文/missing 同步且零引用不调用 answer provider。README 自动矩阵全 exit 0：guarded pytest 417 passed、Web 55 tests / 12 files，ruff/format/mypy/lock/build/OpenAPI/typecheck/lint/Web build 完成。DEV 自测非 QA；随后独立 QA / Sol 判 C19 P1 FAIL，完整报告和证据保留。用户明确改序开始包 3；本轮未修复该缺陷。真实服务/资料/凭据、native/DMG、五日/双机及发布门 NOT_RUN，runtime UNVERIFIED。

## M3 功能包 2 extra 1 Developer（2026-10-12，QA FAIL 历史）

[extra 1 Developer 报告](2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)：用户在 repair 2/2 QA FAIL 后明确授权的唯一额外修复轮，固定源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`。区分历史页面批准 hash 与 current/superseded/invalid 效力；仅对真实 user 历史中的候选原文跨度核验归属语境，使自然偏好提及资料、引用、来源可建 pending 候选，同时拒绝材料 attribution、裸引号和 Markdown 引文中的第一人称片段。guarded pytest 407 passed、Web 55 tests / 12 files；README 全量检查及生成契约各命令的实际 `.exit` 均为 0，日志在 `.local/dev/m3-package-2-extra-1/raw-logs/`。这是 Developer 自测，非 QA；新 SHA 等待 Sol 调度的全新独立 QA。若 FAIL 不自动继续。真实服务/资料/凭据、native/DMG、五日/双机及发布门 NOT_RUN；runtime UNVERIFIED。

## M3 功能包 2 repair 2 Developer（2026-10-12，QA FAIL 历史）

[repair 2 Developer 报告](2026-10-12-M3-PACKAGE-2-REPAIR-2-DEV.md)：固定源码 `b7cfd32e1a1991db6e045f282bc0ab39d48aae15`，repair 2/2 是当时最后获准自动修复轮。该轮实施和自测保持原始记录；后续独立 QA 判 FAIL，历史批准/效力与本人偏好来源问题详见[固定 SHA QA 报告](2026-10-12-M3-PACKAGE-2-REPAIR-2-QA-94854ba.md)及后续 Sol 门报告。原报告与证据不改写；此处开发时的“待 QA”不代表当前状态。证据日志在 `.local/dev/m3-package-2-repair-2/`。

## M3 功能包 2 repair 1 独立 QA（2026-10-12）

[固定 SHA QA 报告](2026-10-12-M3-PACKAGE-2-REPAIR-1-QA-0df323e.md)：受测产品源码 `0df323efc26e388d62f234e0471f853b2b54be4d`，QA 固定 checkout `d38f546cac8fd923539bea6a8ef9db925e5d959c`。C13 UI current/history 选择、历史效力与引用可用性，C20 provenance/候选/预算，C21 workspace/profile 隔离及 C14 会话 replay/cancel/partial restart 恢复通过；README 全量检查 exit 0。真实浏览器 fresh-index 复验发现礼貌自然事实问句误判对象、连续短追问将另一主体作为事实支持两项缺陷，故本包 FAIL，等待 repair 2 与全新独立 QA。报告与脱敏 harness/raw logs/exit/hash manifest 见[证据目录](evidence/2026-10-12-m3-package-2-qa-repair-1-0df323e/)；DevTools console/Network、real/native/DMG/五日/双机为 NOT_RUN，runtime metadata UNVERIFIED。

## M3 功能包 2 repair 1：问答范围、追问召回与错误反馈（2026-10-11，QA FAIL 历史）

[repair 1 Developer 报告](2026-10-11-M3-PACKAGE-2-REPAIR-1-DEV.md)：固定源码 SHA `0df323efc26e388d62f234e0471f853b2b54be4d`，开发时修复首轮 QA 提出的 AskView 历史范围、短指代、422 错误反馈和事实主体筛选问题。其当轮检查和原始证据见 DEV 报告；后续固定 SHA 独立 QA 又发现礼貌事实问句无引用与连续追问混入旧主体，故该轮 QA FAIL，见[固定 SHA QA 报告](2026-10-12-M3-PACKAGE-2-REPAIR-1-QA-0df323e.md)。后续轮次与当前包状态见上方记录。

## M3 功能包 2：完整问答、角色与记忆（2026-10-11，QA FAIL 历史）

[包 2 Developer 报告](2026-10-11-M3-PACKAGE-2-DEV.md)：源码 SHA `daef5250b355179de93cc3d622b93e9b28f17286`。该报告保留当轮实现与 DEV 自测结果；后续独立 QA 连续发现缺陷，最终包 2 状态由 extra 2 Sol 门判 C19 P1 FAIL。开发时的 pending 不代表当前状态；失败原因及未修复边界见当前门记录。真实浏览器、runtime 与真实服务/发布门保持 NOT_RUN / UNVERIFIED。

## M3 功能包 1：会话与历史（2026-10-11，Sol 判离线集成 PASS）

[首次 Developer 报告](2026-10-11-M3-PACKAGE-1-DEV.md)：源码 `faf1563d406cf0cf092550f9845626efb9b09c72`，后续 QA 固定 `c90fe6e2bec5677deb7b069b86fa8971da1d8dcd` 判 FAIL；原始 report/evidence 保留。QA 揭示新库首问 404 和 updated 引用提示随页面导航丢失。

[Repair 1 Developer 报告](2026-10-11-M3-PACKAGE-1-REPAIR-1-DEV.md)：修复源码 SHA `a9078bd327f73f2cde3bab14a8665885d0f57c1c`。首问省略 conversation ID 并从响应头获取服务端会话 ID；updated 引用导航校验原 hash 并在目标页面保留版本提示。后端 **395 passed**、Web **49 passed / 12 files**，会话集成 **6 passed**，静态、类型、OpenAPI 生成、打包和 Web build 门禁 exit 0。后续固定 SHA 独立 QA 与 Sol 离线集成判 PASS，见其下方 QA 报告；该 DEV 自测本身不构成 QA PASS。实际浏览器 / 原生壳 / runtime 元数据分别 NOT_RUN / NOT_RUN / UNVERIFIED，真实 provider、资料、凭据与发布门未运行。

[Repair 1 独立 QA 报告](2026-10-11-M3-PACKAGE-1-QA-bc3deab.md)：受测集成 SHA `bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`，产品源码等同修复 SHA `a9078bd327f73f2cde3bab14a8665885d0f57c1c`；本轮 guarded pytest 395 passed、Web 49 passed / 12 files，README 适用自动门均 exit 0。真实 Fake 浏览器复验首问建会话、历史重开续问、updated 引用打开新正文并持续显示版本提示；真实 Uvicorn 复验幂等冲突、取消、非空 partial 中断重启与两 workspace/profile 隔离。53 项 manifest 零 mismatch、产品树一致；Sol 已判包 1 离线集成 PASS。QA 限制与逐项范围见[QA 报告](2026-10-11-M3-PACKAGE-1-QA-bc3deab.md)及[证据目录](evidence/2026-10-11-m3-package-1-qa-bc3deab/README.md)。

## C03 删除拒绝提示本地化跟进（2026-10-11，离线切片与合并后核验通过）

[C03 删除文案 DEV](2026-10-11-C03-DELETE-COPY-DEV.md)：固定源码 `9c953f095086a95e63edbce2169657dba9e71cd1`；固定 QA 提交 `141bd96d15039f1cd29461785fdd91e2ef297476`。Sol 根据[独立源码 QA](2026-10-11-C03-DELETE-COPY-QA-141bd96.md)判定本切片首轮 PASS、repair 0/2，37 项定向回归与实际 Fake WebUI 浏览器观察通过。文档整合 SHA `75bfe2548e947432e72767b0b7822d34685a8b61`；PR #11 merge SHA `2f08c764e740afa494a0445ec4d73382fdd55f3b`，C03 与规范已进入 main。固定 merge SHA 的 [postmerge QA](2026-10-11-C03-POSTMERGE-2f08c76.md) 记录 guarded pytest 389 passed，lock、祖先、源码树和证据校验通过。真实 / 发布门保持原状态。

- [文档整合独立 QA（75bfe25）](2026-10-11-C03-INTEGRATION-QA-75bfe25.md)：37 项既有 C03 回归与 Fake 浏览器证据保持原结论；该轮全量 pytest 在 fresh checkout 安装 Web 依赖前失败，按 README 安装后同一 SHA 复验 389 passed，日志均保留。
- [PR #11 合并后独立 QA（2f08c76）](2026-10-11-C03-POSTMERGE-2f08c76.md)：固定 merge SHA 的 guarded pytest 389 passed；本轮 Web、浏览器和 native 为 NOT_RUN。

计数勘误：原始 C03 QA 的目标回归为 37 项；原始 C03 证据 manifest 实为 16 个条目（15 项原始输入及 README）。Postmerge 报告中的原始证据条目数已更正为 16，整合 QA 日志 manifest 为 15 项；更正只修正文档计数，不改变测试结果或 QA 范围。原始报告及 FAIL 记录不覆盖、不删除。完整 M1、Stage B 与真实 / 发布门状态不变；原始日志与观察记录见[证据目录](evidence/2026-10-11-c03-delete-copy-qa-141bd96/README.md)。

## Stage B 离线收口（2026-10-11，当前）

[PR #10合并后核验与最终收口](2026-10-11-STAGE-B-POSTMERGE.md)：main产品树与576895f一致，13项检查通过；原始QA manifest保留，4项运行时pyc条目未发布，两份补充publication manifest核验实际归档证据。

[Sol DEV 修复与证据](2026-10-11-STAGE-B-SOL-CLOSURE-DEV.md)：采纳经复核的 DeepSeek 实现，补请求独立取消、资源所有权、边界与 Real 任务 UI 回归。固定576895f独立离线QA PASS；受测 SHA、QA / main 关系只以 [最新交接](../../handoff/LATEST-IMPLEMENTATION.md) 为准。

以下 R1–R4 的“未提交”“无新 SHA”和计数是历史当时状态；其 DEV 结论保留，不是当前 QA 结论。

## Stage B R4 整改（2026-10-10，历史 DEV）

[DeepSeek Stage B DEV R4](2026-10-10-DEEPSEEK-STAGE-B-DEV-R4.md)：Sol 对 R3 的最终只读复核实际复现 3 个问题（logout 后旧 callback 恢复授权；响应头未完成时整体 deadline 失效且返回后 worker 仍继续；退役 provider 借租约接受无关新操作），本轮全部整改。每项先对 R3 起点源码快照建立可复现失败反例（逐文件 5/5 校验），再用贯穿集成测试验证；R4-02 用真实 loopback 实测 deadline 0.15s 最差 0.1554s、0.3s 最差 0.3056s（各连续 10 次）。后端 374 passed（含 guard）、Web 42 tests，全部检查 exit 0。证据与 34 项自校验 manifest 见[R4 证据目录](evidence/2026-10-10-deepseek-stage-b-r4/README.md)。改动**未提交**，无新固定源码 SHA；正式 QA pending。

## Stage B R3 整改（2026-10-10，历史 DEV）

[DeepSeek Stage B DEV R3](2026-10-10-DEEPSEEK-STAGE-B-DEV-R3.md)：R2 自测通过后经 Sol 复核发现 5 个 P1，本轮全部整改（共享授权代次与 refresh 协调、严格 OAuth 响应解析、完整业务操作生命周期租约、应用身份与 user 槽隔离、可取消整体 deadline）。每项有 before/after 贯穿集成日志；R3-05 用真实 loopback socket 实测（deadline 0.3s → 0.305s，旧约 0.47s）。后端 351 passed（含 guard）、Web 42 tests，全部检查 exit 0。证据与 38 项自校验 manifest 见[R3 证据目录](evidence/2026-10-10-deepseek-stage-b-r3/README.md)。改动**未提交**，无新固定源码 SHA；正式 QA pending。

## Stage B R2 整改（2026-10-10，历史 DEV）

[DeepSeek Stage B DEV R2](2026-10-10-DEEPSEEK-STAGE-B-DEV-R2.md)：整改 Sol 复核第一轮发现的 5 个 P1 与 1 个 P2（真实任务写独立门、应用身份贯通服务层、官方主日历形状、设置变更即时生效与 client 生命周期/共享 refresh、日历截断如实上报、整体 deadline 完整生命周期），并修正状态与来源归属。每项先建失败反例再修产品；后端 305 passed（含归档 guard 复跑）、Web 42 tests，静态/打包/构建全部 exit 0。Sol 归档 harness 原件未改：并发反例的构造死锁另建修正版（8 passed）并保留旧失败与解释。证据与 manifest 见[证据目录](evidence/2026-10-10-deepseek-stage-b-r2/README.md)。改动**未提交**，无新固定源码 SHA；正式 QA pending。

## Stage B 初轮 DEV（2026-10-10 DeepSeek trial，历史 DEV）

[DeepSeek Stage B DEV](2026-10-11-DEEPSEEK-STAGE-B-DEV.md)：在独立试验工作区（分支 `codex/deepseek-stage-b-trial`，起点固定文档提交 `0a1db5d`，上一源码候选 `7dc7114` 与其只差文档）补齐真实 Feishu HTTP adapter、settings 与 Feishu token store 的统一 Keychain 槽、`feishu.real_data_enabled` 服务端数据门、模型整体 deadline / HTTP 200 业务错误拒绝 / client 释放。后端 253 passed（含 network/Keychain guard 复跑），其余检查逐条记录。改动**未提交**，没有新源码 SHA；浏览器/原生/OS Keychain 与所有真实请求 NOT_RUN。Sol SB-01–13 归档 harness 重跑结果及两处非 pass 的解释见报告 §4；证据与 manifest 见[证据目录](evidence/2026-10-10-deepseek-stage-b/README.md)。当前入口见[DeepSeek Stage B 交接](../../handoff/DEEPSEEK-STAGE-B.md)。

## Stage B 上一轮评定（2026-10-10）

[Luna Stage B DEV follow-up](2026-10-10-STAGE-B-LUNA-DEV.md)：修复 Sol SB-01–12 候选发现的问题并同步 SB-13，源码固定 `7dc7114595704f34ba386c96324dffa77d529ba4`。后端213 / Web39 与列出的离线构建检查通过；三个限额合成模型 smoke 均未运行，Feishu OAuth / 业务 adapters 仍不完整。浏览器截图与完整网络证据未归档，原生候选复演 NOT_RUN，Stage B 未完成，正式独立 QA pending；没有 PR/main 整合。

[Sol独立DEV候选评估](2026-10-10-STAGE-B-SOL-DEV-REVIEW.md)：开始时dirty base `ba0d330…`，后按用户授权原样固定实现 `1fede419…` 和开发文档 `4966a682…`。原矩阵后端190/前端36通过，独立反例后端10/前端1 FAIL；P0=2/P1=10/P2=1，尚未达到正式固定SHA QA入口。真实服务、用户Keychain、真实材料操作0；无PR/main整合。本条更新后文旧“未固定/未审查”状态，不追认正式QA。实际harness与失败log见[证据目录](evidence/2026-10-10-stage-b-sol-dev-review/README.md)；[下一执行Luna提示词](../../handoff/PROMPT-STAGE-B-LUNA-AFTER-SOL-REVIEW.md)要求修复、完成B、新SHA正式独立QA后再整合。

## 当前证据如何组合

Stage A 当前结论为 **PASS（Fake-only）**，最终受测修复代码 `30903c4cdf73855af71a201e3edea6c535ee8199`，收口 main `117086eb2075726730cd7aa62ea0b61498e96f0c`。之后环境整理只改文档。不能单独拿第四轮旧 PASS 摘要代表当前全部证据；须结合以下追加纠正和修复复验。

| 顺序 | 报告 | 被测对象 / 结论与边界 |
|---|---|---|
| 1 | [M2 汇总 DEV](2026-10-10-M2-DEV.md) | 原 M2 代码 `09398fca…`；执行者自测与 WebUI，不是独立 QA |
| 2 | [原候选 QA](2026-10-10-M2-stage-a-original-qa.md) | 固定 `09398fca…`，保留 A-01–A-05 的历史缺陷 |
| 3 | [修复 DEV](2026-10-10-M2-stage-a-fix-dev.md) | 修复代码 `32da67e9…`；自测，不替代独立 QA |
| 4 | [首轮 QA](2026-10-10-M2-stage-a-final-qa.md)、[第二轮](2026-10-10-M2-stage-a-final-followup-qa.md)、[第三轮](2026-10-10-M2-stage-a-final-third-followup-qa.md)、[第四轮](2026-10-10-M2-stage-a-final-fourth-followup-qa.md) | 固定 `32da67e9…` 的独立检查 / UI / 原生开发壳报告链。第四轮部分截图和脚本指纹证明被后续纠正；旧报告不改写 |
| 5 | [PR #4 合并后核验](2026-10-10-M2-stage-a-postmerge.md) | 固定 `0789f9eb…`，受测代码树一致与当轮自动 / 冒烟；不代表真实门 |
| 6 | [独立证据补验](2026-10-10-M2-stage-a-evidence-supplement.md) | 基线 `5351a3ac…`、同产品代码；纠正重复截图及无法追溯执行脚本指纹。C17 三种日期 / mismatch、C16 不重发、C18 分离、C23 未决记录补验；三项恢复 UI 子步骤当轮 NOT_RUN，随后报告补齐 |
| 7 | [恢复 UI 初验](2026-10-10-M2-stage-a-recovery-ui-supplement.md) | 固定 `409b9070…`：C16 崩溃 / 重启 / 并发、C23 无证明 PASS；C18 UI P2 **FAIL**。47 项 manifest；初次 Chrome 代理转发情况无法判定 |
| 8 | [C18 修复独立复验](2026-10-10-M2-stage-a-c18-recovery-ui-retest-30903c4.md) | 固定 `30903c4…`：C18 receipt 恢复、同 ID replay PASS，C23 no-proof 负对照 PASS；26 项 manifest。该轮独立自动测试 NOT_RUN，不能改写初验 FAIL |

完整 SHA、提交关系和合并后核对见 [LATEST-IMPLEMENTATION](../../handoff/LATEST-IMPLEMENTATION.md) 与 [ACCEPTANCE](../ACCEPTANCE.md)。初验 FAIL 只在新受测修复行为上关闭。旧截图撤回、脚本指纹未知与网络观察限制保留，不把所有历史通信说成零。

## 切片与 M1 历史报告

- M2.1：[DEV](2026-10-09-M2.1-DEV.md)。
- M2.2：[P2 审查修正](2026-10-10-M2.2-review-fix.md)；切片 DEV 位于 [task-M2.2-report](../../../.superpowers/sdd/2026-10-09-summit-everything-v1/task-M2.2-report.md)。窄范围 P2 复核不等于整个 M2 独立 QA。
- M2.3：[DEV](2026-10-10-M2.3-DEV.md)。
- M1：[首次报告](2026-10-09-M1-f364c01.md)、[M1.1–M1.5](2026-10-09-M1.1-M1.5-f364c01.md)、[收口 DEV](2026-10-09-M1-close-DEV.md)、[收口初验](2026-10-09-M1-close-73ec81a.md)、[收口复验](2026-10-09-M1-close-retest-f349fe6.md)。各报告只对应各自固定版本。

## 后续报告纪律

当前收口状态见最新交接。真实 Feishu / 模型 / 业务数据 / task 写入 / OS Keychain / DMG / 五日 / 双机门均 NOT_RUN；用户资源未被消费。

- Stage B partial DEV: [2026-10-10 report](2026-10-10-STAGE-B-partial-DEV.md) — dirty candidate at baseline `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`; offline self-check passed (Python 185, Web 36); model runtime, synthetic callback config, Fake token refresh/logout, and a local Fake Feishu disconnect/reload replay are documented. Replay details: [browser evidence note](evidence/2026-10-10-stage-b-browser/replay.md). Real Feishu adapters incomplete; no independent review / QA or integration.

新增报告必须记录代码 SHA、文档 checkpoint、QA 提交、PR / main 关系；分别记录 DEV、自测、独立审查、独立 QA、WebUI、原生开发壳、真实协议与质量。按 [REPORT-TEMPLATE](../REPORT-TEMPLATE.md)填写，维护本索引。保留历史 FAIL；追加整改 / 复验，不把旧文件重写成成功。证据只提交脱敏副本，harness 指纹必须是实际执行字节，manifest 必须与当前归档字节匹配。

## 2026-10-11 收口过程的历史检查点（结论仅对当时SHA）

- [首次独立离线QA：7f3119a FAIL / QA-B-01 P1](2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md)。
- [刷新重启防重发DEV修复](2026-10-11-STAGE-B-REFRESH-RESTART-DEV.md)：新源码8b6259a，后端386/Web45；当时正式复验pending，后续见8b复验。
- [闲置工作树可恢复清理](2026-10-11-STAGE-B-CLEANUP.md)。

- [首次固定7f UI/native独立证据](2026-10-11-STAGE-B-INDEPENDENT-UI-QA.md)：指定本机场景通过，整体候选因QA-B-01仍FAIL。

- [8b后端复验与严格字段P2](2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-RETEST-8b6259a.md)、[8b原生启动竞态P1](2026-10-11-STAGE-B-INDEPENDENT-UI-RETEST-8b6259a.md)均按旧SHA保留。
- [严格标记DEV](2026-10-11-STAGE-B-STRICT-MARKER-DEV.md)、[原生readiness DEV](2026-10-11-STAGE-B-NATIVE-READINESS-DEV.md)：当时源码fd204238，388/Web45；后续独立原生QA发现根URL比较P1。

- [fd后端独立QA](2026-10-11-STAGE-B-LUNA-FINAL-OFFLINE-QA.md)：388+25、Web45与构建通过，整体候选因原生冷启动P1仍未通过。
- [根URL修复DEV](2026-10-11-STAGE-B-NATIVE-URL-DEV.md)：新源码576895f，实际loopback URL before失败→after通过；后续独立复验见最终报告。


- [最终后端复验](2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md)、[最终实际UI复验](2026-10-11-STAGE-B-LUNA-UI-RETEST-576895f.md)：受测源码576895f；离线PASS，真实/OS/DMG等门NOT_RUN。
