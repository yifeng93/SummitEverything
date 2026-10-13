# 实施进展账本

本页只记当前状态；逐轮历史仍保存在原始 DEV / QA 报告与[历史账本副本](PROGRESS-HISTORY-2026-10-13.md)。验收状态以 Sol 对固定 SHA 的门判断为准。

## 当前状态

当前 M4.2 工作包 A Developer 已固定产品 SHA `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 并完成本机自动检查及 clean Internal App/DMG 候选；fresh QA pending，Developer 检查不构成验收 PASS。隔离 native UI 只复演到带 guard 的设置页及 Fake 合成材料导入；第一次错误启动的 Keychain 查询与 profile 路径均 UNVERIFIED。M4.1 离线技术 PASS、PR #17 与 M3 状态都仍是各自原固定 SHA 的历史结论，不能替代 M4.2 验收。整个 M4 与所有真实门未通过。见[M4.2 DEV](../quality/reports/2026-10-13-M42-PACKAGE-A-DEV.md)、[M4.1 历史 Sol 门](../quality/reports/2026-10-13-M41-SOL-GATE.md)和[最新交接](../handoff/LATEST-IMPLEMENTATION.md)。

| 范围 | 当前结果 | 证据 |
|---|---|---|
| M3 包 1：会话与历史 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) |
| M3 包 2：问答、角色、记忆（C19） | 离线集成 PASS | [固定源码 QA](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)、[Sol 门](../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md) |
| M3 包 3：连续工作与归档 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) |
| M3 离线模拟正式验收 | 用户批准并合入 | [验收记录](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)、[合并后 QA](../quality/reports/2026-10-13-M3-POSTMERGE-QA-47a3971.md) |
| M4.1 初始候选 | 源码 `b9321d6` 的独立 QA 发现原生 HTML 文件面板缺失（历史 FAIL） | [初始 DEV](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)、[QA 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-b9321d6.md) |
| M4.1 修复轮 1 | 固定源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4`；独立离线 QA 与 Sol 技术门 PASS；用户批准离线正式收口，PR #17 已合入 main | [fresh QA](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md)、[Sol 门](../quality/reports/2026-10-13-M41-SOL-GATE.md) |
| M4.2 工作包 A Developer | 固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`；自动自测与clean候选 build 有原始日志；fresh QA pending | [DEV 报告](../quality/reports/2026-10-13-M42-PACKAGE-A-DEV.md)、[最终命令 evidence](../quality/reports/evidence/2026-10-13-m42-package-a-dev/final-20261014/) |
| M4.2 fresh QA | PENDING | 独立 checkout 验证固定 SHA；不得使用 Developer 自测作为结论 |
| 真实 provider / Feishu / 业务材料 / OS Keychain | NOT_RUN；错误首轮候选的 Keychain 查询/profile 路径 UNVERIFIED | 需要独立真实环境与用户选择的材料、范围和动作 |
| M4.2真实验收、用户安装、Developer ID/公证、五日试用、双机与发布 | NOT_RUN | Internal 候选不代表实际安装或发布门通过 |
| 远端离线 CI | 两次 success，记录 head `f7ad5e4`；与固定 QA 产品树一致 | [CI 证据](../quality/reports/evidence/2026-10-13-m41-ci/README.md)；macOS 14.8.9 自动检查，不代替完整 GUI / 安装 |
| Runtime 配置元数据 | UNVERIFIED | 没有实际观测值 |

产品固定 SHA 的清洁候选位于 worktree `.local/dev/m42-package-a/final-20261014/artifacts/`；fresh QA 应使用 `open -n` 加 temporary profile 和 offline guard，并先检查设置页显示“钥匙串不可用”。首轮 shell 直接启动的 UI 观察只作为失败/不确定记录，不能描述为零 Keychain 查询。此次 native UI 只复演 Settings 与 Fake 导入；organize/review/index/query 的完整 UI 流程仍待 QA/后续真实用户路径覆盖。App UI / 生命周期与仅 backend smoke 分开记录；C24/C25 未逐项复演者继续列为 NOT_RUN。

## 当前开发交接

产品源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 与新 clean 候选固定；后续仅文档/证据变更不改变产品 SHA。fresh QA 尚未开始，Developer 的 508 Python、61 Web、3 Swift、Ruff/mypy/uv lock/build 与 native build 日志均在报告证据目录。最终正确 UI 启动验证确认 native/backend guard 与 temp profile-root 对应，fake UI 只到材料导入；首次错误启动保持 UNVERIFIED。候选路径、身份及下一步见 [LATEST](../handoff/LATEST-IMPLEMENTATION.md)。M4.1 QA-only evidence 是此前固定 SHA 的历史验收，不应用到此 SHA。

## 历史索引

- [旧进展账本与各轮状态](PROGRESS-HISTORY-2026-10-13.md)
- [M3 离线验收与最终技术门](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)
- [历史状态汇总](../handoff/history/2026-10-13-m3-offline-closeout.md)
