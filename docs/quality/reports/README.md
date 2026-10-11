# 开发与独立验收报告索引

## Stage B 离线收口（2026-10-11，当前）

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
