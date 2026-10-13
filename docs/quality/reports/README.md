# 开发与独立验收报告索引

## 当前已验收范围

M3 离线模拟范围已获用户批准并合入 main。C19 / 包 2 固定源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 经全新独立 QA 通过；固定 merge `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2` 的合并后 QA 通过。完整批准范围和未测项见[M3离线验收](2026-10-13-M3-OFFLINE-ACCEPTANCE.md)；逐轮原始报告和 evidence 保持不变。

本轮仓库 / 文档清理的受测产品源码 `6a33259224097167cfdde689da93258fe925964e` 已通过独立离线 QA；QA-only 提交 `da76f56b765308a365eafd0927c84e88caec492e` 的 37 项 manifest SHA-256 为 `88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3`，已由 Sol 核验。清理后文档收口未改变产品源码；是否及何时合入 main 以 Sol 后续 Git/PR 查询为准。

| 报告 | 范围 |
|---|---|
| [本轮清理 DEV](2026-10-13-PRE-NEXT-STAGE-CLEANUP-DEV.md) | 文档收拢、私有 helper 审计、DEV 自测与恢复记录；验收结果见独立 QA |
| [本轮清理独立 QA](2026-10-13-PRE-NEXT-STAGE-CLEANUP-QA-6a33259.md) | 固定源码 `6a33259` 的离线清理验收 PASS；真实 / 人工门仍按报告标记未测 |
| [C19 固定源码 QA](2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md) | C19 新回归、API/SSE、浏览器与离线自动检查 |
| [Sol C19 门](2026-10-13-M3-C19-DSH-SOL-GATE.md) | 71 项证据核验与包 2 离线结论 |
| [M3 离线正式验收](2026-10-13-M3-OFFLINE-ACCEPTANCE.md) | 用户批准的范围、结果和边界 |
| [合并后独立 QA](2026-10-13-M3-POSTMERGE-QA-47a3971.md) | 固定 merge 的复验与 49 项证据核验 |
| [历史状态索引](HISTORY-INDEX-2026-10-13.md) | 旧 SHA 的 DEV/QA 报告目录；结论仅对各自固定 SHA 有效 |

## 保留的独立验收边界

真实 provider / Feishu、真实业务材料、OS Keychain、runtime 元数据、native/DMG、五日试用、双机与发布不因离线 QA 通过而变为 PASS。完整验收要求见[验收矩阵](../ACCEPTANCE.md)。原始报告、manifest、SHA256SUMS、命令输出和截图不在本索引中重写。
