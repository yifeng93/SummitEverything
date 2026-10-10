# 开发与独立验收报告索引

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

Stage B DEV 正在隔离 worktree 中进行；当前是部分实现，未固定候选、未独立审查 / QA、未整合。Stage C 尚未启动。真实 Feishu / 模型 / 材料 / 外部任务 / DMG / 五日 / 双机仍 NOT_RUN。用户已准备资源不改变这些状态。

- Stage B partial DEV: [2026-10-10 report](2026-10-10-STAGE-B-partial-DEV.md) — dirty candidate at baseline `ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`; offline self-check passed (Python 185, Web 36); model runtime, synthetic callback config, Fake token refresh/logout, and a local Fake Feishu disconnect/reload replay are documented. Replay details: [browser evidence note](evidence/2026-10-10-stage-b-browser/replay.md). Real Feishu adapters incomplete; no independent review / QA or integration.

新增报告必须记录代码 SHA、文档 checkpoint、QA 提交、PR / main 关系；分别记录 DEV、自测、独立审查、独立 QA、WebUI、原生开发壳、真实协议与质量。按 [REPORT-TEMPLATE](../REPORT-TEMPLATE.md)填写，维护本索引。保留历史 FAIL；追加整改 / 复验，不把旧文件重写成成功。证据只提交脱敏副本，harness 指纹必须是实际执行字节，manifest 必须与当前归档字节匹配。
