# 开发与独立验收报告索引

## 当前已验收范围

M3 离线模拟范围已获用户批准并合入 main。C19 / 包 2 固定源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 经全新独立 QA 通过；固定 merge `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2` 的合并后 QA 通过。完整批准范围和未测项见[M3离线验收](2026-10-13-M3-OFFLINE-ACCEPTANCE.md)；逐轮原始报告和 evidence 保持不变。

本轮仓库 / 文档清理的受测产品源码 `6a33259224097167cfdde689da93258fe925964e` 已通过独立离线 QA，并由 PR #15 合入，合并点为 `2238f1b47d4c7ee073e1d420dc86b23d7e75ffb6`；该合并点产品树与固定 QA 源码一致。QA-only 提交 `da76f56b765308a365eafd0927c84e88caec492e` 的 37 项 manifest SHA-256 为 `88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3`，已由 Sol 核验。清理后文档收口未改变产品源码；Git 与远端最终状态以工作结束时实际查询及本机私有回执为准。

M4.1 固定产品 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 经 fresh QA 与 Sol 核验，适用离线技术门 PASS；用户已批准离线正式收口，PR #17 已合入 main。旧候选 `b9321d6` 的文件面板 FAIL 原件保留，修复使用 1/2 轮；真实安装、签名公证、M4.2、五日、双机和发布未通过。

M4.2 Package A Developer 已在固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 完成本地自测、clean候选与有限 Fake 原生 UI；fresh QA pending。首轮错误 native launch 的 Keychain 查询/profile 路径 UNVERIFIED，不能称为 0 次。真服务和人工范围继续 NOT_RUN。

| 报告 | 范围 |
|---|---|
| [M4.2 Package A DEV](2026-10-13-M42-PACKAGE-A-DEV.md) | 固定产品 SHA `fe47339`、命令 exit/raw evidence、clean候选和正确/错误隔离 UI 启动边界；fresh QA pending |
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

真实 provider / Feishu、真实业务材料、OS Keychain、runtime 元数据、native/DMG、五日试用、双机与发布不因离线 QA 通过而变为 PASS。完整验收要求见[验收矩阵](../ACCEPTANCE.md)。原始报告、manifest、SHA256SUMS、命令输出和截图不在本索引中重写。
