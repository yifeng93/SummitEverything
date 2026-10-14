# 实施进展账本

本页只记当前状态；逐轮历史仍保存在原始 DEV / QA 报告与[历史账本副本](PROGRESS-HISTORY-2026-10-13.md)。验收状态以 Sol 对固定 SHA 的门判断为准。

## 当前状态

M4.2 工作包 A 初始固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 经独立 QA 判 FAIL；修复轮 1 最终受测产品源码 SHA 为 `419bb865b334389d1efd0f4a1a855cd0d5324d28`。Fresh QA 对该固定 SHA 已复核，Sol 判定**适用 Package A 离线技术场景 PASS**。QA 无新产品缺陷；此次范围不等于 M4.2 全部/C25/Stage C/产品最终 PASS。用户已于 2026-10-14 批准工作包 A 离线正式收口与合入 main。PR #18 已合并（2026-10-14T10:42:19Z，head `0e8fc4633d4b1409fb7da0354d4474a4faeef430`）；run [38550700081](https://github.com/yifeng93/SummitEverything/actions/runs/38550700081) 全步骤成功。CI 工作流旧显示名为 M4.1，但该运行适用于本 PR。当前 main 产品/tests/lock 树与 fixed `419bb86` 相同；收口 docs commit 不是受测产品 SHA。

修复轮 1 包含：P1 unknown plan 重启查询、P2 完整 planner 问句证据、已确认范围的批量文件/文件夹与 Journal Assist；Native 追加修复混选零字节文件时明确提示、仍整批拒绝，主动 Cancel 无提示。独立 QA 对 P1/P2、Native 多选/目录、Fake JournalAssist、Real ProviderRuntime + MockHTTP API、C19 planner、final clean candidate 逐场景判定见[QA 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)与[Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)。完整命令与限制见[DEV handoff](../quality/reports/2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md)。

自动检查针对固定源码树：guarded Python 513、Web 65、Swift 5 passed；ruff/format/mypy、lock/build、OpenAPI 类型生成/diff、TS typecheck/lint/build exit 0。lint 有 2 条 React warnings，保留在 raw logs。候选 source SHA 匹配、dirty=false；包摘要与 61 项 QA raw archive 独立校验见各 evidence README/manifest。开发证据、QA docs-only commit 与产品 SHA 分开记；报告提交不改变 candidate identity。

| 范围 | 当前结果 | 证据 |
|---|---|---|
| M3 包 1：会话与历史 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) |
| M3 包 2：问答、角色、记忆（C19） | 离线集成 PASS | [固定源码 QA](../quality/reports/2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)、[Sol 门](../quality/reports/2026-10-13-M3-C19-DSH-SOL-GATE.md) |
| M3 包 3：连续工作与归档 | 离线集成 PASS | [QA 报告](../quality/reports/2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) |
| M3 离线模拟正式验收 | 用户批准并合入 | [验收记录](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)、[合并后 QA](../quality/reports/2026-10-13-M3-POSTMERGE-QA-47a3971.md) |
| M4.1 修复轮 1 | 固定 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4`；独立离线 QA 与 Sol 技术门 PASS，用户批准并合入 PR #17 | [fresh QA](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md)、[Sol 门](../quality/reports/2026-10-13-M41-SOL-GATE.md) |
| M4.2 工作包 A 初始 QA | 固定 SHA `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`：FAIL；初始报告和原始 QA evidence 保持不变 | [QA 初始报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-INITIAL.md)、[evidence](../quality/reports/evidence/2026-10-14-m42-package-a-qa-initial/) |
| M4.2 Package A repair1 fresh QA | 固定 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28`：适用离线技术场景 PASS | [QA 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)、[Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)、[原始 QA archive](../quality/reports/evidence/2026-10-14-m42-package-a-qa-repair1/README.md) |
| M4.2 离线正式收口 / main 合并 | 用户批准；PR #18 已于 2026-10-14T10:42:19Z 合并，merge 后 main 产品/tests/lock 树与 fixed `419bb86` 一致 | [收口报告](../quality/reports/2026-10-14-M42-OFFLINE-CLOSEOUT.md)、[合并 CI](../quality/reports/evidence/2026-10-14-m42-ci/README.md) |
| 设置 UX 与内置非秘密默认值（分支 `codex/settings-ux-20261014`） | 固定产品 SHA `8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b`；自动检查（591/90）、完整打包、包内注入端到端 27/27 通过；三轮全新独立 QA 均 PASS，D1/F1/F3 已修复，**F2 开放（既存）** | [DEV 报告](../quality/reports/2026-10-14-SETTINGS-UX-DEV.md)、[QA 证据归档](../quality/reports/evidence/2026-10-14-settings-ux-qa/README.md)、[ADR 0010](../decisions/0010-first-use-configuration-ux.md) |
| 工作包 B/C 真实模型、Feishu、资料、Keychain、账单/答案质量 | NOT_RUN；runtime model metadata UNVERIFIED | 依据[具体授权准备卡](../handoff/M42-PACKAGE-A-READINESS.md)，先取得精确资料路径、动作与范围授权 |
| Stage B 用户单机真实验收 / install / 公证 / 五日 / 双机 / M5 / release | NOT_RUN | Internal App/DMG 技术包验证不等于正式用户安装或完整产品验收；该 Stage 名称沿用验收矩阵 |
| Gatekeeper assessment | 本机 `spctl` exit 3 / ad-hoc rejected；未绕过 | 详见固定 SHA [QA 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) |
| 远端离线 CI | M4.2 PR #18 的 run 38550700081 全步骤 success（源 head `0e8fc46`）；工作流显示名沿用 M4.1，但适用于本 PR。M4.1 的 f7ad success 仍为独立历史记录 | [M4.2 CI 原始证据](../quality/reports/evidence/2026-10-14-m42-ci/README.md)、[M4.1 CI 历史](../quality/reports/evidence/2026-10-13-m41-ci/README.md) |

本轮也有未前置 process checker 的较早 UI 启动，以及恢复上下文后的 late CUA guard=false 启动；late attempt 在 UI 输入前终止 QA 自有进程。Keychain 查询次数和默认 profile 回退继续 UNVERIFIED，不宣称本轮零 Keychain 查询或全程正确隔离。QA 一条错误 P1 assertion 有完整 raw；另一临时 assertion 失败 raw 已被覆盖，QA 报告明确披露且不补造。CUA 内容是观察转录，不是 screenshot/AX raw dump。完整边界见[Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)。

## 当前开发与授权交接

固定产品 SHA 是 `419bb865b334389d1efd0f4a1a855cd0d5324d28`；QA docs-only SHA `e3983569dbbb7093107c63fca1986e29cfcfd867` 与本次收口文档提交均不是受测产品 SHA。QA evidence archive 复制了 manifest 指定的 61 个原始文件及原 manifest，并使用新的独立相对路径清单逐项校验。PR #18 已合并且对应离线 CI 全步骤成功；当前 main 产品/tests/lock 树与固定受测 SHA 一致。收口报告和 CI evidence 是 docs-only，不改变受测产品身份。后续真实资料/模型/Feishu 工作仍需按 readiness 卡逐项授权，真实工作尚未开始。

## 历史索引

- [旧进展账本与各轮状态](PROGRESS-HISTORY-2026-10-13.md)
- [M3 离线验收与最终技术门](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)
- [历史状态汇总](../handoff/history/2026-10-13-m3-offline-closeout.md)
