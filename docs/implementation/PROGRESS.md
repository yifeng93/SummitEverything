# 实施进展账本

本页只记当前状态；逐轮历史仍保存在原始 DEV / QA 报告与[历史账本副本](PROGRESS-HISTORY-2026-10-13.md)。验收状态以 Sol 对固定 SHA 的门判断为准。

## 当前状态

已验收 M3 与清理维护的历史 SHA 继续由对应报告约束，不作为当前 M4.1 结论。当前工作分支 `codex/m41-internal-app-20261013` 执行 2026-10-13 用户明确授权的离线 M4.1：唯一 FastAPI + React 前端、内置 PyInstaller onedir Python、Swift 薄壳和独立未公证 Internal DMG 候选。初始候选 `b9321d6` 的独立 QA 报告记录了文件选择面板缺失；修复轮 1 将产品源码固定为 `3f6eaa408a8860ff5a438be8a874a2c3904733e4`，已重建候选并完成开发者侧实际原生面板与 Fake 导入 UI 自测。fresh QA 待启动，阶段判断尚未作出。详见[最新交接](../handoff/LATEST-IMPLEMENTATION.md)。

| 范围 | 当前结果 | 证据 |
|---|---|---|
| M3 包 1：会话与历史 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) |
| M3 包 2：问答、角色、记忆（C19） | 离线集成 PASS | [固定源码 QA](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)、[Sol 门](../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md) |
| M3 包 3：连续工作与归档 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) |
| M3 离线模拟正式验收 | 用户批准并合入 | [验收记录](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)、[合并后 QA](../quality/reports/2026-10-13-M3-POSTMERGE-QA-47a3971.md) |
| M4.1 初始候选 | 源码 `b9321d6` 的独立 QA 发现原生 HTML 文件面板缺失（历史 FAIL） | [初始 DEV](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)、[QA 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-b9321d6.md) |
| M4.1 修复轮 1 | 固定源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4`；候选重建，开发者实际 UI 复演 PASS；fresh QA 待验 | [修复轮 1 DEV](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV-REPAIR1.md)；不表示 M4.1 / M4 通过 |
| 真实 provider / Feishu / 业务材料 / OS Keychain | NOT_RUN | 需要独立真实环境与用户选择的材料、范围和动作 |
| M4.2真实验收、用户安装、Developer ID/公证、五日试用、双机与发布 | NOT_RUN | 内部未公证候选不代表实际安装或发布门通过 |
| Runtime 配置元数据 | UNVERIFIED | 没有实际观测值 |

本轮复现开发 runner 启动期间 Ctrl+C 后返回负子进程码（shell exit 241），未复现历史 `PermissionError`；runner 中断清理现在正常返回，tracked 子进程回归覆盖该路径。App UI / 生命周期与仅 backend smoke 分开记录；C24/C25 未逐项复演者继续列为 NOT_RUN。

## 当前开发交接

修复轮 1 Developer 已在产品源码 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 完成全门回归、clean-SHA App/DMG 重建与实际原生 UI 自测；fresh QA 将在独立 checkout 对此固定 SHA 验收。初始 SHA `b9321d6` 的文件面板缺陷仍按历史 QA 报告记录；未收到本轮独立 QA 前，不将 M4.1 记录标为验收通过；未获用户授权的真实连接、M4.2 和发布动作仍不执行。原清理维护的逐命令证据仍见[历史 DEV 报告](../quality/reports/2026-10-13-PRE-NEXT-STAGE-CLEANUP-DEV.md)及其独立 QA 报告。

## 历史索引

- [旧进展账本与各轮状态](PROGRESS-HISTORY-2026-10-13.md)
- [M3 离线验收与最终技术门](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)
- [历史状态汇总](../handoff/history/2026-10-13-m3-offline-closeout.md)
