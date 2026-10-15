# 开发与独立验收报告索引

## 当前已验收范围

M3 离线模拟范围已获用户批准并合入 main。C19 / 包 2 固定源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 经全新独立 QA 通过；固定 merge `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2` 的合并后 QA 通过。完整批准范围和未测项见[M3离线验收](2026-10-13-M3-OFFLINE-ACCEPTANCE.md)；逐轮原始报告和 evidence 保持不变。

本轮仓库 / 文档清理的受测产品源码 `6a33259224097167cfdde689da93258fe925964e` 已通过独立离线 QA，并由 PR #15 合入，合并点为 `2238f1b47d4c7ee073e1d420dc86b23d7e75ffb6`；该合并点产品树与固定 QA 源码一致。QA-only 提交 `da76f56b765308a365eafd0927c84e88caec492e` 的 37 项 manifest SHA-256 为 `88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3`，已由 Sol 核验。清理后文档收口未改变产品源码；Git 与远端最终状态以工作结束时实际查询及本机私有回执为准。

M4.1 固定产品 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 经 fresh QA 与 Sol 核验，适用离线技术门 PASS；用户已批准离线正式收口，PR #17 已合入 main。旧候选 `b9321d6` 的文件面板 FAIL 原件保留，修复使用 1/2 轮；真实安装、签名公证、M4.2、五日、双机和发布未通过。

M4.2 Package A 初始 QA 对固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 判 FAIL。修复轮 1 最终产品 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28` 已由独立 fresh QA 验收；Sol 判**适用工作包 A 离线技术场景 PASS**，不是整个 M4.2/C25/Stage C/产品 PASS。`4c6b0bd` 包含 P1/P2 与规格范围实现，`419bb86` 的 Native 修复为有效/零字节混选给出通用拒绝提示并保留 Cancel 无提示。QA 指定 UI/API/自动检查结果和限制见 [QA 报告](2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)及 [Sol gate](2026-10-14-M42-PACKAGE-A-SOL-GATE.md)。真实服务、材料、Keychain 与人工交付门仍 NOT_RUN 或 UNVERIFIED；用户已批准离线正式收口与合入 main；PR #18 于 2026-10-14T10:42:19Z 合并，run 38550700081 全步骤成功（workflow 显示名沿用 M4.1，但适用于本 PR）。main 产品/tests/lock 树与 fixed `419bb86` 一致。

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

真实 provider / Feishu、真实业务材料、OS Keychain 生命周期、runtime 元数据、正式用户安装/公证、五日试用、双机与发布不因离线 QA 通过而变为 PASS。M4.2 PR #18 的远端 CI run 38550700081 已全步骤成功；其工作流显示名沿用 M4.1。本轮原始压缩日志与校验值见 [M4.2 CI evidence](evidence/2026-10-14-m42-ci/README.md)。完整验收要求见[验收矩阵](../ACCEPTANCE.md)。原始报告、manifest、SHA256SUMS、命令输出和截图不在本索引中重写。
