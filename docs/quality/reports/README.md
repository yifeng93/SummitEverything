# 开发与独立验收报告索引

当前状态只维护在 [PROGRESS](../../implementation/PROGRESS.md)。本页导航各固定 SHA 的报告；历史 PASS/FAIL、合并及 CI 记录不得直接作为当前 HEAD 的结论。

## Ponytail 精简（2026-10-17）

- [集中 DEV 记录](2026-10-17-PONYTAIL-CLEANUP-DEV.md)：文档处置、代码/依赖/测试审计与保留理由。
- [文档专项 QA](2026-10-17-PONYTAIL-CLEANUP-DOCS-QA.md)：固定 `f57c7ed` 的入口、契约和原始证据核验。
- [代码与内部包 QA](2026-10-17-PONYTAIL-CLEANUP-CODE-QA.md)：固定 `5835faa` 的离线回归、包身份与实际退出码。
- [Sol 最终门判断](2026-10-17-PONYTAIL-CLEANUP-SOL-GATE.md)：两次验收范围、证据核验与后续门。

## 历史固定版本报告

今日/审批的前轮结论见[Sol 门](2026-10-16-FRONTEND-USABILITY-SOL-FINAL.md)及[合并收口](2026-10-17-FRONTEND-USABILITY-MERGE-CLOSEOUT.md)，其[初验 FAIL](2026-10-16-FRONTEND-USABILITY-SOL-INITIAL.md)与原件保留。以下均为对应阶段的历史版本导航。

| 报告 | 范围 |
|---|---|
| [前端 UX 里程碑 B 初始 DEV 报告](2026-10-15-FRONTEND-B-DEV.md) | 历史固定 SHA `613d453`；首次 QA 后续判 FAIL，错误描述已明确修正；原自测结论仅适用于该 SHA |
| [前端 UX 里程碑 B 初始 QA 归档](evidence/2026-10-15-frontend-b-initial-qa/README.md) | 固定 `613d453` 的首次独立 QA FAIL；报告、命令、脱敏 harness 与必要证据保留 |
| [前端 UX 里程碑 B repair1 DEV 报告](2026-10-15-FRONTEND-B-DEV-REPAIR1.md) | 固定产品 SHA `a0ccad8`；开发者自测及未测边界 |
| [前端 UX 里程碑 B repair1 fresh QA 与 Sol gate](2026-10-15-FRONTEND-B-QA-REPAIR1.md) | 固定产品 SHA `a0ccad8`；Sol 判定适用 B 离线核心与两项修复 PASS，不代表全站 / C/D / Stage C |
| [前端 UX 里程碑 B repair1 QA evidence](evidence/2026-10-15-frontend-b-repair1-qa/README.md) | 脱敏命令退出码与关键网络/Fake 证据哈希索引；原件留在 QA `.local` |
| [前端 UX 里程碑 B repair1 DEV evidence](evidence/2026-10-15-frontend-b-repair1/README.md) | 开发命令、失败历史、Frozen SourceOrganizer scope harness 与 Import Drawer 5×2 焦点截图 |
| [前端 UX 里程碑 C DEV 报告](2026-10-15-FRONTEND-C-DEV.md) | 固定产品 SHA `1b1efda`；DEV 自测与 Fake/矩阵/变异证据，4 个全站守卫归 D，fresh QA pending |
| [前端 UX 里程碑 C 独立 QA](2026-10-15-FRONTEND-C-QA.md) | 固定产品 SHA `1b1efda`；Sol 判适用 C 离线前端场景 PASS，4 个全站守卫与真实/打包门留 D 或未测；[证据索引](evidence/2026-10-15-frontend-c-qa/README.md) |
| [前端 UX 里程碑 A Sol gate](2026-10-15-FRONTEND-A-SOL-GATE.md) | 固定 `9c33a9d` 适用离线技术门 PASS；8 项 todo / 3 条 lint warning 保留，真实门未重跑 |
| [前端 UX 里程碑 A repair1 fresh QA 归档](evidence/2026-10-15-frontend-a-repair1-qa/README.md) | fresh QA 固定 SHA `9c33a9d` 的脱敏报告、harness、raw logs、Mock/FastAPI evidence 与截图 |
| [前端 UX 里程碑 D 初次 QA（FAIL / P1）](2026-10-15-FRONTEND-D-QA-INITIAL.md) | 固定 `876008e` 的首次独立 QA FAIL：完成首配后同 profile/workspace 重启仍弹 workspace gate 与向导第 2 步；原件留在 QA `.local` |
| [前端 UX 里程碑 D repair1 DEV 报告](2026-10-15-FRONTEND-D-DEV-REPAIR1.md) | 固定 `faa1edd`；进度改为本机 profile+workspace 隔离 typed API 持久化、旧 localStorage 一次性迁移、durable write 失败可见可重试；红绿与三条定向变异 |
| [前端 UX 里程碑 D repair1 独立 QA](2026-10-15-FRONTEND-D-QA-REPAIR1.md) | 固定 `faa1edd`；同一自建 harness 在父 `876008e` 复现 P1（20 checks/8 failed/exit 1）、受测 64/64/exit 0；D-1..D-4 记录 |
| [前端 UX 里程碑 D repair1 Sol gate](2026-10-15-FRONTEND-D-SOL-GATE.md) | Sol 判 repair1 的 P1 在 API+生产 WebUI+真实后端进程重启范围内 CLOSED；当时 D 门未通过（缺 native 候选） |
| [前端 UX 里程碑 D repair2/3 DEV 报告（含 native 候选验证）](2026-10-15-FRONTEND-D-DEV-REPAIR2.md) | 固定最终产品 SHA `e8e1dba`；D-1 create/open 区分、D-4 严格整数、D-6 重生成；两个候选身份、包内 runtime 15/15、native WKWebView 三条路径机器 OCR 判读 |
| [前端 UX 里程碑 D repair2 独立 QA（FAIL / D-6）](2026-10-15-FRONTEND-D-QA-REPAIR2.md) | 固定 `96fdf4d`；D-1/D-4/P1 与 12 条自动检查 PASS，但 CI 门 `api:types` 失败（D-6）；含父 SHA 非空性对照 |
| [前端 UX 里程碑 D 最终独立 QA](2026-10-15-FRONTEND-D-QA-FINAL.md) | 固定 `e8e1dba`；D-6 收口 + 改动面最小性 + 可继承性 + 12 条自动检查 + D-1/D-4/P1 在新 SHA 重取证，判 PASS（限定范围） |
| [前端 UX 里程碑 D Sol 最终门判断](2026-10-15-FRONTEND-D-SOL-GATE-FINAL.md) | 固定 `e8e1dba`；P1 CLOSED、native 同 profile 重启 PASS（Sol 实机 OCR，QA 未独立复现）、D 门限「离线 + 内部候选」PASS；真实/安装/发布门仍 NOT_RUN |
| [M4.2 Package A 初始 QA](2026-10-14-M42-PACKAGE-A-QA-INITIAL.md) | 固定 `fe473399` 初始 FAIL；原始 34 项证据及 hash 副本在对应 evidence 目录 |
| [M4.2 Package A 修复轮 1 DEV handoff](2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md) | 固定产品 SHA `419bb86`；最终候选、UI 自测、未测边界与 fresh QA handoff |
| [M4.2 Package A 修复轮 1 fresh QA](2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) | 固定 `419bb86`；仅报告实际验收的离线/API/Mock/packaged UI 场景及 NOT_RUN / UNVERIFIED 限制 |
| [M4.2 Package A Sol gate](2026-10-14-M42-PACKAGE-A-SOL-GATE.md) | Sol 判适用离线技术场景 PASS；已合入 PR #18，CI run 38550700081 全步骤 success；工作包 B 须按准备卡单独授权 |
| [M4.2 Package A DEV](2026-10-13-M42-PACKAGE-A-DEV.md) | 固定产品 SHA `fe47339`、命令 exit/raw evidence、clean候选和正确/错误隔离 UI 启动边界；fresh QA pending |
| [M4.2 离线收口记录](2026-10-14-M42-OFFLINE-CLOSEOUT.md) | PR #18 merge/CI、固定 QA 产品树等价、交付包与真实门限制 |
| [M4.1 修复轮 1 fresh QA](2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md) | 固定 `3f6eaa4` 适用离线验收 PASS，文件面板 P1 实际关闭；真实门 NOT_RUN |
| [M4.1 Sol 门](2026-10-13-M41-SOL-GATE.md) | 固定候选 / 证据 / 代码审查，离线技术 PASS；用户批准离线收口并合入 PR #17 |
| [M4.1 初始 DEV](2026-10-13-M41-INTERNAL-APP-DEV.md) | 初始候选与首次 QA 前自测，产品源码 SHA `b9321d6` |
| [M4.1 初始 QA](2026-10-13-M41-INTERNAL-APP-QA-b9321d6.md) | 固定 `b9321d6` 的独立 QA；文件面板缺失为历史 FAIL |
| [M4.1 修复轮 1 DEV](2026-10-13-M41-INTERNAL-APP-DEV-REPAIR1.md) | 固定源码 SHA `3f6eaa4`、新候选、开发者实际 UI、逐命令 exit 与 NOT_RUN；独立结论见 fresh QA |
| [本轮清理 DEV](2026-10-13-PRE-NEXT-STAGE-CLEANUP-DEV.md) | 文档收拢、私有 helper 审计、DEV 自测与恢复记录；验收结果见独立 QA |
| [本轮清理独立 QA](2026-10-13-PRE-NEXT-STAGE-CLEANUP-QA-6a33259.md) | 固定源码 `6a33259` 的离线清理验收 PASS；真实 / 人工门仍按报告标记未测 |
| [C19 固定源码 QA](2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md) | C19 新回归、API/SSE、浏览器与离线自动检查 |
| [Sol C19 门](2026-10-13-M3-C19-DSH-SOL-GATE.md) | 71 项证据核验与包 2 离线结论 |
| [M3 离线正式验收](2026-10-13-M3-OFFLINE-ACCEPTANCE.md) | 用户批准的范围、结果和边界 |
| [合并后独立 QA](2026-10-13-M3-POSTMERGE-QA-47a3971.md) | 固定 merge 的复验与 49 项证据核验 |
| [历史状态索引](HISTORY-INDEX-2026-10-13.md) | 旧 SHA 的 DEV/QA 报告目录；结论仅对各自固定 SHA 有效 |

## 保留的独立验收边界

离线 QA 不替代真实 provider/飞书、业务材料、Keychain、用户安装/公证、五日、双机或发布验收。完整标准见[验收矩阵](../ACCEPTANCE.md)，当前未测项见 PROGRESS。历史 CI 的原始日志示例见 [M4.2 CI evidence](evidence/2026-10-14-m42-ci/README.md)；原始报告、manifest、校验值、命令输出和截图保持原样。

## 历史报告完整索引

本小节由 2026-10-15 仓库清理机械补全：收录 `docs/quality/reports/` 直接层中此前未出现在上方索引里的历史报告，标签一律取该文件自身的 H1 标题原文，未做任何结论概括。历史结论仅对各自固定 SHA 有效。

| 报告 | 范围 |
|---|---|
| [SummitEverything 独立验收报告 — M1 收口候选](2026-10-09-M1-close-73ec81a.md) | 历史报告（标签取自该文件 H1 原文） |
| [M1 收口候选 DEV 自测记录](2026-10-09-M1-close-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [SummitEverything M1 收口独立复验报告](2026-10-09-M1-close-retest-f349fe6.md) | 历史报告（标签取自该文件 H1 原文） |
| [SummitEverything 独立验收报告 — M1](2026-10-09-M1-f364c01.md) | 历史报告（标签取自该文件 H1 原文） |
| [SummitEverything M1.1–M1.5 独立验收报告](2026-10-09-M1.1-M1.5-f364c01.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2.1 Feishu authorization, materials and calendar — DEV report](2026-10-09-M2.1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [DeepSeek Stage B DEV R2 — review-finding remediation (2026-10-10)](2026-10-10-DEEPSEEK-STAGE-B-DEV-R2.md) | 历史报告（标签取自该文件 H1 原文） |
| [DeepSeek Stage B DEV R3 — remediation of the R2 review findings (2026-10-10)](2026-10-10-DEEPSEEK-STAGE-B-DEV-R3.md) | 历史报告（标签取自该文件 H1 原文） |
| [DeepSeek Stage B DEV R4 — remediation of the R3 final-review findings (2026-10-10)](2026-10-10-DEEPSEEK-STAGE-B-DEV-R4.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2.1–M2.3 开发者自测与固定 SHA 交接](2026-10-10-M2-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A C18 recovery UI retest on fixed repair SHA 30903c4](2026-10-10-M2-stage-a-c18-recovery-ui-retest-30903c4.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A evidence correction and supplemental UI retest](2026-10-10-M2-stage-a-evidence-supplement.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A Final QA follow-up — 2026-10-10](2026-10-10-M2-stage-a-final-followup-qa.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A Final QA — fourth independent follow-up (2026-10-10)](2026-10-10-M2-stage-a-final-fourth-followup-qa.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A Final Independent QA — 2026-10-10](2026-10-10-M2-stage-a-final-qa.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A Final QA — third independent follow-up (2026-10-10)](2026-10-10-M2-stage-a-final-third-followup-qa.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2 阶段 A 修复者 DEV 记录](2026-10-10-M2-stage-a-fix-dev.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2 阶段 A 原始候选定向独立验收](2026-10-10-M2-stage-a-original-qa.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2 Stage A 合并后核验记录（2026-10-10）](2026-10-10-M2-stage-a-postmerge.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage A recovery UI supplement for fixed candidate 409b907](2026-10-10-M2-stage-a-recovery-ui-supplement.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2.2 独立审查修复：核实依据不能为空](2026-10-10-M2.2-review-fix.md) | 历史报告（标签取自该文件 H1 原文） |
| [M2.3 开发者自测与交接](2026-10-10-M2.3-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B Luna follow-up DEV report — 2026-10-10](2026-10-10-STAGE-B-LUNA-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 独立 DEV 候选评估 — Sol — 2026-10-10](2026-10-10-STAGE-B-SOL-DEV-REVIEW.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B partial DEV report — 2026-10-10](2026-10-10-STAGE-B-partial-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [C03 非空组织删除提示本地化 DEV（2026-10-11）](2026-10-11-C03-DELETE-COPY-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [C03 非空组织删除提示独立 QA（2026-10-11）](2026-10-11-C03-DELETE-COPY-QA-141bd96.md) | 历史报告（标签取自该文件 H1 原文） |
| [C03 文档整合候选独立 QA（2026-10-11）](2026-10-11-C03-INTEGRATION-QA-75bfe25.md) | 历史报告（标签取自该文件 H1 原文） |
| [C03 合并后独立核验（2026-10-11）](2026-10-11-C03-POSTMERGE-2f08c76.md) | 历史报告（标签取自该文件 H1 原文） |
| [DeepSeek Stage B DEV report — 2026-10-10](2026-10-11-DEEPSEEK-STAGE-B-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包 1：会话与历史 — Developer 报告](2026-10-11-M3-PACKAGE-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 1 独立 QA — bc3deab](2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 1 独立验收 — c90fe6e](2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 1 首轮整改：会话首问与历史引用提示 — Developer 报告](2026-10-11-M3-PACKAGE-1-REPAIR-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [历史报告链接兼容说明](2026-10-11-M3-PACKAGE-1-REPAIR-1-QA-bc3deab.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 Developer 报告：完整问答、角色与记忆](2026-10-11-M3-PACKAGE-2-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包 2 独立验收](2026-10-11-M3-PACKAGE-2-QA-0827447.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包 2 repair 1 Developer 报告](2026-10-11-M3-PACKAGE-2-REPAIR-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 工作区收口与恢复记录](2026-10-11-STAGE-B-CLEANUP.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 独立离线 QA — 7f3119a（2026-10-11）](2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 独立离线复验 — 8b6259a（中间提交，2026-10-11）](2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-RETEST-8b6259a.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 固定 7f3119a 独立 UI / 原生壳 QA](2026-10-11-STAGE-B-INDEPENDENT-UI-QA.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 8b6259a 独立 UI 复验](2026-10-11-STAGE-B-INDEPENDENT-UI-RETEST-8b6259a.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 最终固定源码离线后端 QA — 2026-10-11](2026-10-11-STAGE-B-LUNA-FINAL-OFFLINE-QA.md) | 历史报告（标签取自该文件 H1 原文） |
| [Luna High final code review — fd20423](2026-10-11-STAGE-B-LUNA-FINAL-REVIEW.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B independent offline UI/native QA — fd2042385 (FAIL)](2026-10-11-STAGE-B-LUNA-FINAL-UI-QA.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 固定源码后端离线复验 — 576895f（2026-10-11）](2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B Luna independent UI retest — 576895f](2026-10-11-STAGE-B-LUNA-UI-RETEST-576895f.md) | 历史报告（标签取自该文件 H1 原文） |
| [原生开发壳双服务就绪修复 DEV（2026-10-11）](2026-10-11-STAGE-B-NATIVE-READINESS-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [原生 readiness 根 URL 修复 DEV](2026-10-11-STAGE-B-NATIVE-URL-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B 离线源码合并后核验与收口](2026-10-11-STAGE-B-POSTMERGE.md) | 历史报告（标签取自该文件 H1 原文） |
| [QA-B-01 重启刷新防重发 DEV修复（2026-10-11）](2026-10-11-STAGE-B-REFRESH-RESTART-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [Stage B Sol 收口 DEV（2026-10-11）](2026-10-11-STAGE-B-SOL-CLOSURE-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [本地刷新消费标记严格解析 DEV（2026-10-11）](2026-10-11-STAGE-B-STRICT-MARKER-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 C19 统一修复周期：Sol 最终门判断](2026-10-12-M3-C19-UNIFIED-SOL-GATE.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一证据范围修复（Developer 交接）](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一候选独立初验](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-QA-400dc98.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一范围 repair 1 Developer 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 unified repair 1/2 独立 QA](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-1-QA-04a0239.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一范围 repair 2 Developer 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一 repair 2/2 独立 QA](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 统一修复 repair 3（DSH 试修）DEV 报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-3-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 extra 1 Developer 报告](2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 Package 2 Extra 1 QA — 2026-10-12](2026-10-12-M3-PACKAGE-2-EXTRA-1-QA-507cc1f.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 extra 2 Developer 报告（2026-10-12，待全新独立 QA）](2026-10-12-M3-PACKAGE-2-EXTRA-2-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 extra 2 独立 QA 报告](2026-10-12-M3-PACKAGE-2-EXTRA-2-QA-d2236c2.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包 2 repair 1 独立 QA](2026-10-12-M3-PACKAGE-2-REPAIR-1-QA-0df323e.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 repair 2 Developer 报告](2026-10-12-M3-PACKAGE-2-REPAIR-2-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包 2 repair 2 独立 QA](2026-10-12-M3-PACKAGE-2-REPAIR-2-QA-94854ba.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 3 Developer 报告：连续状态与归档压缩](2026-10-12-M3-PACKAGE-3-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 开发包 3 独立验收](2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 3 repair 1 Developer 报告：lease 发布前异常清理](2026-10-12-M3-PACKAGE-3-REPAIR-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 3 repair 1/2 独立复验](2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 3 Sol 门判断](2026-10-12-M3-PACKAGE-3-SOL-GATE.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 extra 1：Sol 门判断与接续](2026-10-12-M3-SOL-EXTRA-1-GATE.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 extra 2：Sol 门判断](2026-10-12-M3-SOL-EXTRA-2-GATE.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 功能包接续与 Sol 门判断](2026-10-12-M3-SOL-GATE.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 / C19 DSH 修复独立验收](2026-10-13-M3-PACKAGE-2-C19-DSH-QA-be4e72f.md) | 历史报告（标签取自该文件 H1 原文） |
| [M3 包 2 C19 DSH 候选统一返工 1/2：Developer 报告](2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [内测候选记录：`6fe1aa8`（设置 UX + F2 整合）](2026-10-14-INTERNAL-CANDIDATE-6fe1aa8.md) | 历史报告（标签取自该文件 H1 原文） |
| [F2 修复报告：origin guard 对损坏 profile 的失败形态](2026-10-14-ORIGIN-GUARD-SETTINGS-ERROR.md) | 历史报告（标签取自该文件 H1 原文） |
| [内测候选首次真实使用：真实故障链与修复](2026-10-14-REAL-FIRST-USE-FINDINGS.md) | 历史报告（标签取自该文件 H1 原文） |
| [设置 UX 与内置非秘密默认值：DEV 报告](2026-10-14-SETTINGS-UX-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [前端 UX 里程碑 A · 修复轮 1 开发报告](2026-10-15-FRONTEND-A-DEV-REPAIR1.md) | 历史报告（标签取自该文件 H1 原文） |
| [前端 UX 里程碑 A：开发交接](2026-10-15-FRONTEND-A-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [前端 UX 里程碑 D 开发自测与候选交接](2026-10-15-FRONTEND-D-DEV.md) | 历史报告（标签取自该文件 H1 原文） |
| [PR #21 合并前仓库清理 · Developer 报告（2026-10-15）](2026-10-15-PRE-PR21-CLEANUP-DEV.md) | 本轮清理 DEV 报告（2026-10-15 仓库清理） |
| [PR #21 合并前仓库清理 · 独立 QA 报告（Luna · High，2026-10-15）](2026-10-15-PRE-PR21-CLEANUP-QA.md) | 全新独立 QA 对固定 `7a448c3` 的清理验收（A–H 全项 PASS；含未覆盖清单与 Nit） |
| [已删路径 → 归档索引（2026-10-15 清理）](DELETED-PATHS-INDEX.md) | 已删路径 → 归档索引（本轮清理） |

| [Stage B / C 当前工作计划](../../handoff/history/2026-10-11-STAGE-B-C-PLAN.md) | 历史归档（Stage B/C 计划） |
| [Stage B / C 当前检查单](../../handoff/history/2026-10-11-STAGE-B-C-TODO.md) | 历史归档（Stage B/C 检查单） |
| [PR #21 合并前仓库清理 · Sol 最终门判断（2026-10-16）](2026-10-16-PRE-PR21-CLEANUP-SOL-GATE.md) | Sol 最终门判断（PR #21 合并前清理） |
| [App 图标 + DMG 卷图标 · Sol 门判断（PR #22，2026-10-16）](2026-10-16-APP-ICON-SOL-GATE.md) | App 图标 + DMG 卷图标（PR #22）Sol 门判断 |
| [App 图标 + DMG 卷图标 独立 QA（固定 SHA `deed704`）](2026-10-16-APP-ICON-QA.md) | App 图标 + DMG 卷图标（PR #22）独立 QA 报告 |
