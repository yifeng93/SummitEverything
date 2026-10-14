# 实施进展账本

本页只记当前状态；逐轮历史仍保存在原始 DEV / QA 报告与[历史账本副本](PROGRESS-HISTORY-2026-10-13.md)。验收状态以 Sol 对固定 SHA 的门判断为准。

## 当前状态

M4.2 工作包 A 初始固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 经独立 QA 判 FAIL；修复轮 1 目前固定产品 SHA 为 `419bb865b334389d1efd0f4a1a855cd0d5324d28`。`4c6b0bd` 修复 unknown 计划 GET 和完整问句 planner 并完成 v1 多文件/文件夹导入及 Journal Assist；`419bb86` 最小修复可信原生文件面板中混选零字节文件时静默失败，保留严格整批拒绝并显示通用提示。历史产品树完整检查为 Python 513/Web 65/Swift 4，lint 两条 React warning；新 SHA Swift 5 通过。干净候选 source SHA 为 `419bb86`、dirty=false，App/DMG 与 WK 原生面板 mixed reject/Cancel/valid multiselect UI 均已记录。旧候选 `bc5018d` 的 exact body/query 与 journal reopen 记录不冒充新候选复演。fresh QA 正待 Sol 在新独立 checkout 对固定 `419bb86` 复核；Developer 自测不等于 QA PASS。所有真实 provider / materials / Keychain / install / notarization / five-day / two-device / release 均 NOT_RUN，runtime model metadata UNVERIFIED。见[初始 QA](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-INITIAL.md)、[修复轮 1 DEV handoff](../quality/reports/2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md)、[最新交接](../handoff/LATEST-IMPLEMENTATION.md)。

| 范围 | 当前结果 | 证据 |
|---|---|---|
| M3 包 1：会话与历史 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) |
| M3 包 2：问答、角色、记忆（C19） | 离线集成 PASS | [固定源码 QA](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)、[Sol 门](../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md) |
| M3 包 3：连续工作与归档 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) |
| M3 离线模拟正式验收 | 用户批准并合入 | [验收记录](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)、[合并后 QA](../quality/reports/2026-10-13-M3-POSTMERGE-QA-47a3971.md) |
| M4.1 初始候选 | 源码 `b9321d6` 的独立 QA 发现原生 HTML 文件面板缺失（历史 FAIL） | [初始 DEV](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)、[QA 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-b9321d6.md) |
| M4.1 修复轮 1 | 固定源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4`；独立离线 QA 与 Sol 技术门 PASS；用户批准离线正式收口，PR #17 已合入 main | [fresh QA](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md)、[Sol 门](../quality/reports/2026-10-13-M41-SOL-GATE.md) |
| M4.2 工作包 A 初始 QA | 固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`：FAIL；发现 P1/P2，QA 已停止 | [QA 初始报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-INITIAL.md)、[原样证据副本](../quality/reports/evidence/2026-10-14-m42-package-a-qa-initial/) |
| M4.2 修复轮 1 | 固定产品 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28`；Developer checks/UI 已完成，fresh QA pending | [DEV handoff](../quality/reports/2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md)、[候选与原始证据](../quality/reports/evidence/2026-10-14-m42-package-a-repair1/README.md) |
| M4.2 fresh QA | PENDING | Sol 已准备新独立 checkout；对 fixed `419bb86` 全量复核后由 Sol 判门 |
| 真实 provider / Feishu / 业务材料 / OS Keychain | NOT_RUN；错误首轮候选的 Keychain 查询/profile 路径 UNVERIFIED | 需要独立真实环境与用户选择的材料、范围和动作 |
| M4.2真实验收、用户安装、Developer ID/公证、五日试用、双机与发布 | NOT_RUN | Internal 候选不代表实际安装或发布门通过 |
| 远端离线 CI | 两次 success，记录 head `f7ad5e4`；与固定 QA 产品树一致 | [CI 证据](../quality/reports/evidence/2026-10-13-m41-ci/README.md)；macOS 14.8.9 自动检查，不代替完整 GUI / 安装 |
| Runtime 配置元数据 | UNVERIFIED | 没有实际观测值 |

初始候选位于 worktree `.local/dev/m42-package-a/final-20261014/artifacts/`，仅对应已 FAIL 的 SHA，不得供新 QA 使用。首轮 shell 直接启动的 Keychain 查询与 profile 路径继续 UNVERIFIED。初始 Developer native UI 只复演 Settings 与 Fake 导入；本轮修复的实际批量/文件夹 UI 尚未验证。C24/C25 与所有真实外部门仍 NOT_RUN。

## 当前开发交接

初始 Developer 对 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 的 508 Python 等记录仅是历史自测，独立 QA 已判 FAIL。修复提交 `4c6b0bd` 的完整自动检查实际 exit 0；clean packaged candidate 与 WK 实际复演仍在准备，不要将自测写成 QA PASS。细节见 [LATEST](../handoff/LATEST-IMPLEMENTATION.md) 与本地 SDD ledger。

## 历史索引

- [旧进展账本与各轮状态](PROGRESS-HISTORY-2026-10-13.md)
- [M3 离线验收与最终技术门](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)
- [历史状态汇总](../handoff/history/2026-10-13-m3-offline-closeout.md)
