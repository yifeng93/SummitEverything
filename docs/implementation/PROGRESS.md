# 实施进展账本

本页只记当前状态；逐轮历史仍保存在原始 DEV / QA 报告与[历史账本副本](PROGRESS-HISTORY-2026-10-13.md)。验收状态以 Sol 对固定 SHA 的门判断为准。

## 当前状态

前端 UX 里程碑 A 初始产品提交 `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad` 基于 `e84e9e5a56475a19f68ca1a684366fba7f9fee83`，经独立 QA 判 **FAIL**（F1 必填密钥提交前反馈、F2 AI 检查聚合状态、F3 飞书刷新失败缓存状态）。修复轮 1 产品固定 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` 经 fresh QA 与 Sol 核验，适用离线技术门 **PASS**；自动修复使用 1/2。QA 记录 8 项全站 todo、3 条 lint warning，不视为全站通过。真实 provider、OAuth、Feishu、Keychain、DMG、进程重启、五日和双机未在 A 重跑；历史真实链路成功事实保持原记录。QA 报告、脱敏 harness 与 raw evidence 归档见 [repair1 QA 证据目录](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/)，开发证据见 [repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-A-DEV-REPAIR1.md)。

前端 UX 里程碑 B 初次产品 SHA `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` 经独立 QA 判 **FAIL**：QA-001 来源整理 Real 冻结范围缺原件正文/可读目标；QA-002 Import Drawer 键盘焦点不可见。修复轮 1 产品固定 SHA `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`，Developer 自测完成、fresh QA 待开始，Sol 尚未判门。repair1 Web 单测 180 passed / 6 todo，离线 Playwright 2/2，Fake FastAPI 与冻结范围取消场景各 1/1，typecheck/lint/build exit 0。真实 provider、OAuth、Feishu、Keychain、安装与全站 todo 仍是独立未测边界；索引计划与来源整理 scope 是分开的流程。见 [B repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-B-DEV-REPAIR1.md)、[repair1 evidence](../quality/reports/evidence/2026-10-15-frontend-b-repair1/README.md)和[初次 QA FAIL 归档](../quality/reports/evidence/2026-10-15-frontend-b-initial-qa/README.md)。

M4.2 工作包 A 初始固定源码 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 经独立 QA 判 FAIL；修复轮 1 最终受测产品源码 `419bb865b334389d1efd0f4a1a855cd0d5324d28` 已经 Fresh QA 与 Sol 判定适用离线技术场景 PASS，并于 2026-10-14 按用户批准合入 main。该历史门不等于 M4.2 全部/C25/Stage C/产品最终 PASS；完整记录见本页下方与对应报告。

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
| 前端基线切片 1–2（ADR 0011：设计系统/深色/守卫基座、应用外壳） | 已合入 main（PR #20，CI `offline-arm64` 3m45s 通过）；web **147 passed | 10 todo**、typecheck/lint/build 全 0；守卫 ③⑦①部分+⑧前半 实现并各做过变异验证（18+19 条全红并恢复）；未实现守卫以 todo 标注归属切片 | [前端指南](../product/FRONTEND-GUIDE.md)、[逐页规格](../product/FRONTEND-PAGE-SPECS.md)、[ADR 0011](../decisions/0011-frontend-ux-baseline.md) |
| 前端 UX 里程碑 A 初始 QA | 固定产品 SHA `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`：独立 QA FAIL，发现 F1–F3；原报告/harness/证据已归档并保持原样 | [初次 QA 归档](../quality/reports/2026-10-15-FRONTEND-A-INITIAL/)、[初始 DEV 报告](../quality/reports/2026-10-15-FRONTEND-A-DEV.md) |
| 前端 UX 里程碑 A repair1 | 固定产品 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f`：适用离线技术门 PASS；8 项全站 todo 与 3 条 lint warning 保留，真实集成及人工门未覆盖 | [repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-A-DEV-REPAIR1.md)、[QA 报告与归档](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/README.md)、[原始 evidence manifest](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/evidence-manifest.json) |
| 前端 UX 里程碑 B 初次 QA | 固定产品 SHA `613d453ab1a47e2f0bfe78d685fb90817f70f4cc`：FAIL，QA-001 来源整理预览、QA-002 文件入口焦点；原报告失败状态保留 | [初次 QA 归档](../quality/reports/evidence/2026-10-15-frontend-b-initial-qa/README.md)、[历史 B DEV 报告](../quality/reports/2026-10-15-FRONTEND-B-DEV.md) |
| 前端 UX 里程碑 B repair1 | 固定产品 SHA `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`；Developer 自测完成，fresh QA pending，Sol gate pending；不宣称 PASS | [repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-B-DEV-REPAIR1.md)、[repair1 evidence](../quality/reports/evidence/2026-10-15-frontend-b-repair1/README.md)、[执行路线图](../handoff/FRONTEND-EXECUTION-PLAN.md) |
| 首次真实使用故障与「错误可见」修复（已合入 main，PR #19） | 固定产品 SHA `f40bc39445258d954166143e094156c788be36e1`；四类真实失败（密钥形状 / provider 拒绝 / 业务空间未授权 / 回答 schema 不符）全部定位并修复；**656 passed**、静态全 0、打包与包内 29/29 通过；三轮独立 QA 对 `a301b1b`/`19078de`/`f40bc39` 均 PASS；控制字符收紧 `4d7c8a9` 随后并入 | [真实使用报告](../quality/reports/2026-10-14-REAL-FIRST-USE-FINDINGS.md)、[QA 证据归档](../quality/reports/evidence/2026-10-14-error-visibility-qa/README.md) |
| 设置 UX 与内置非秘密默认值（分支 `codex/settings-ux-20261014`） | 固定产品 SHA `8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b`；自动检查（591/90）、完整打包、包内注入端到端 27/27 通过；三轮全新独立 QA 均 PASS，D1/F1/F3 已修复；F2 在该分支时点仍开放，已由 `codex/origin-guard-error-20261014` 修复并整合进内测候选分支 | [DEV 报告](../quality/reports/2026-10-14-SETTINGS-UX-DEV.md)、[QA 证据归档](../quality/reports/evidence/2026-10-14-settings-ux-qa/README.md)、[ADR 0010](../decisions/0010-first-use-configuration-ux.md) |
| 工作包 B/C 真实模型、Feishu、资料、Keychain、账单/答案质量 | NOT_RUN；runtime model metadata UNVERIFIED | 依据[具体授权准备卡](../handoff/M42-PACKAGE-A-READINESS.md)，先取得精确资料路径、动作与范围授权 |
| Stage B 用户单机真实验收 / install / 公证 / 五日 / 双机 / M5 / release | NOT_RUN | Internal App/DMG 技术包验证不等于正式用户安装或完整产品验收；该 Stage 名称沿用验收矩阵 |
| Gatekeeper assessment | 本机 `spctl` exit 3 / ad-hoc rejected；未绕过 | 详见固定 SHA [QA 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) |
| 远端离线 CI | M4.2 PR #18 的 run 38550700081 全步骤 success（源 head `0e8fc46`）；工作流显示名沿用 M4.1，但适用于本 PR。M4.1 的 f7ad success 仍为独立历史记录 | [M4.2 CI 原始证据](../quality/reports/evidence/2026-10-14-m42-ci/README.md)、[M4.1 CI 历史](../quality/reports/evidence/2026-10-13-m41-ci/README.md) |
| F2 修复：origin guard 对损坏 profile 的失败形态（分支 `codex/origin-guard-error-20261014`） | 固定产品 SHA `c9b3f7cc9af75d1bc46b9ab32e0950ba32995db9`；裸 500 → 设计好的 503 JSON 信封；全量 516 passed；**独立 QA 7 项全 PASS、未发现新缺陷** | [F2 报告](../quality/reports/2026-10-14-ORIGIN-GUARD-SETTINGS-ERROR.md)、[QA 证据](../quality/reports/evidence/2026-10-14-origin-guard-settings-error/README.md) |

本轮也有未前置 process checker 的较早 UI 启动，以及恢复上下文后的 late CUA guard=false 启动；late attempt 在 UI 输入前终止 QA 自有进程。Keychain 查询次数和默认 profile 回退继续 UNVERIFIED，不宣称本轮零 Keychain 查询或全程正确隔离。QA 一条错误 P1 assertion 有完整 raw；另一临时 assertion 失败 raw 已被覆盖，QA 报告明确披露且不补造。CUA 内容是观察转录，不是 screenshot/AX raw dump。完整边界见[Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)。

## 当前开发与授权交接

固定产品 SHA 是 `419bb865b334389d1efd0f4a1a855cd0d5324d28`；QA docs-only SHA `e3983569dbbb7093107c63fca1986e29cfcfd867` 与本次收口文档提交均不是受测产品 SHA。QA evidence archive 复制了 manifest 指定的 61 个原始文件及原 manifest，并使用新的独立相对路径清单逐项校验。PR #18 已合并且对应离线 CI 全步骤成功；当前 main 产品/tests/lock 树与固定受测 SHA 一致。收口报告和 CI evidence 是 docs-only，不改变受测产品身份。后续真实资料/模型/Feishu 工作仍需按 readiness 卡逐项授权，真实工作尚未开始。

## 历史索引

- [旧进展账本与各轮状态](PROGRESS-HISTORY-2026-10-13.md)
- [M3 离线验收与最终技术门](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)
- [历史状态汇总](../handoff/history/2026-10-13-m3-offline-closeout.md)
