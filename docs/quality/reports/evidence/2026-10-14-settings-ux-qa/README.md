# 设置 UX 分支：独立 QA 证据归档（2026-10-14）

本目录保存 `codex/settings-ux-20261014` 分支各轮独立 QA 报告的**逐字副本**。原始文件位于各轮 QA 独立 worktree 的 `.local/qa/`（该目录不入 Git），副本仅用于留存，未做任何改写。

| 副本 | 对应固定 SHA | 原始路径 | SHA-256 |
|---|---|---|---|
| `REPORT-round1-e4f15cd.md` | `e4f15cdfe54be2e8b2b426d9b440eecf2b5ff7e9` | `~/.codex/worktrees/settings-ux-qa-e4f15cd/SummitEverything/.local/qa/REPORT-e4f15cd.md` | `1ec36de42959506aa69f253efaf484959d0b8919d543c99e284add27e446f74e` |
| `REPORT-round2-6d41d35.md` | `6d41d35782422d56b8ee8c8000c9a00479c729cd` | `~/.codex/worktrees/settings-ux-qa-6d41d35/SummitEverything/.local/qa/REPORT-round2.md` | `227251a870c3e245c54455fd5af582f529ac77adca06ff1c9ea6b1de96952a60` |
| `REPORT-round3-8c4f81c.md` | `8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b` | `~/.codex/worktrees/settings-ux-qa-8c4f81c/SummitEverything/.local/qa/REPORT-round3.md` | `27ee30243224a84479d33824df9348ea76411116c647322c6afbb7902632b7d0` |
| `REPORT-round4-ea90828.md` | `ea90828c4eae50873faf3a8f2f7007e6a31d4a1f`（仅测试改动） | `~/.codex/worktrees/settings-ux-qa-ea90828/SummitEverything/.local/qa/README.md` | `1149bfbaadaf574805fcabced594d51faeadbeac1e75adac6fc01172a562775b` |

## 各轮结论摘要（细节以副本原文为准）

- **第一轮（`e4f15cd`）**：身份、全量 558、静态检查、前端 90、契约未变、注入语义黑盒 26 项、前端证伪 7 项、候选哈希与冻结端到端全部 PASS；三条主张（向导导航零 provider 请求、取消不发请求、密钥不进持久化）未被证伪。发现缺陷 **D1**：section 级损坏被注入掩盖。
- **第二轮（`6d41d35`）**：D1 确认修复（同一 harness 在只读导出的旧源码树上 56 failed / 36 passed 作为对照）；其余全项 PASS（全量 561、前端 90、包内 defaults 与来源逐字节一致、DMG 已挂载复核、冻结端到端 19/19）。发现缺陷 **F1**（字段级同类不对称）与既有问题 **F2**（损坏 profile 经中间件返回裸 500 而非设计的 JSON 503，与本功能无关）。

- **第三轮（`8c4f81c`）**：F1 确认修复——自建 149 项检查全绿，同一字节的 harness 在只读导出的 `6d41d35` 旧源码树上得到 72 项失败（恰为「有注入」的 24 store + 24 API + 24 handler），作为前后对照；D1 section 级回归 66/66；注入语义 38/38 与边界 21/21；全量 591、前端 90（lint 2 条 warning 已在功能前树复现为既有）、候选 DMG 哈希/包内三方等值/manifest 指纹/smoke 全部 PASS；冻结端到端 85/85，字段级损坏 20 组与 section 级 12 组均为 500、无一 200。同时发现 **F3**：测试套件不固定注入源，导出该环境变量会让 33 个无关 Feishu 测试失败（默认门禁仍全绿）。

- **第四轮（`ea90828`，仅测试提交）**：聚焦复核 F3 修复。A2（导出注入源）与 B2（未导出）**均 591 passed / exit 0**；同一 worktree 里对 `8c4f81c` 全树副本做的修复前对照 P_A（导出）为 **33 failed / 558 passed**、P_B（未导出）为 591 passed，与第三轮数字完全一致，证明该 conftest 正是消除差异的原因。两个注入测试文件在导出条件下 71 passed（unit 65 + integration 6），未被跳过。产品树（`src`/`web`/`scripts`/`pyproject.toml`/`uv.lock`）在该区间零变化，已归档候选 DMG 不受影响。
  - 该轮同时指出两点实现者表述不准：区间 `8c4f81c..ea90828` 含一个未申报的 docs-only 提交（`ea90828` 自身确实只有 `tests/conftest.py`）；`tests/` 下引用 `create_app` 的模块实测为 22 个而非 23 个。
  - **残余限制（Sol 裁决：保持现状并记录）**：`tests/conftest.py` 的作用域是目录级，只保护 `tests/**`（即 `testpaths`，套件覆盖完整）；`tests/` 之外临时 harness 仍会继承该环境变量。将其上移为根级 conftest 会扩大到被忽略的临时 harness，收益不抵又一次改动与复核，故不在本分支实施。

**结论状态**：D1、F1、F3 均已修复并经后续 QA 复核。**F2 仍开放**：`origin_guard` 中间件读取损坏 profile 时抛错，返回裸 500 而非设计中的 JSON 503，导致 profile 损坏后连用于修复的 PATCH 也 500；该行为在功能前提交 `a6faf7e` 上同样存在，与本功能无关，已记录在 [DEV 报告](../../2026-10-14-SETTINGS-UX-DEV.md)。