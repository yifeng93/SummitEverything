# 2026-10-15 PR #21 合并前清理 · 独立 QA 证据（脱敏）

QA：全新独立 **Luna（High）**，未参与本轮清理实现。
受测固定源码 SHA：**`7a448c39092b81d0afcb15ce4dc57d91faaa7e5e`**（`git rev-parse 7a448c3`，
分支 `codex/frontend-ux-20261015`）。
QA checkout：`/Users/yifengstudio/.codex/worktrees/qa-cleanup-verify`（`git worktree add --detach`，
独立于 Sol / Luna 工作目录；验收完成后已 `git worktree remove --force` + `prune` 删除）。
结论正文见 [../../2026-10-15-PRE-PR21-CLEANUP-QA.md](../../2026-10-15-PRE-PR21-CLEANUP-QA.md)。

产品受测基线 SHA：`e8e1dba0c1fed9a5f02babcc29d5f67dc1d374`（前端 D 最终固定产品 SHA，本轮清理未改动）。

## 依赖安装

| 命令 | 退出码 |
|---|---|
| `uv sync --locked --group dev` | 0 |
| `npm --prefix web ci` | 0（`added 226 packages, and audited 227 packages`，0 vulnerabilities） |

## 本目录文件

| 文件 | 内容 |
|---|---|
| `A-product-freeze.txt` | A1/A2/A3 真实命令与输出（产品面冻结 + 判别力对照 + exclude 反例对照） |
| `B-and-C-checks.txt` | B1–B13 逐项期望 / 实测 / 退出码表；C 前端指纹实测值 |
| `D-E-F-H-details.md` | D 删除可追溯性、E 归档完整性与凭据扫描、F 链接与索引、H 对抗性检查的完整方法与实测 |
| `E-manifest-selfcheck.txt` | 19 个归档目录 `MANIFEST.sha256` 逐条自校验的逐目录输出（ok=395 / mismatch=0 / 1679） |
| `E-credential-scan-scope.txt` | 凭据扫描面 = `e8e1dba..7a448c3` 的 440 个新增/修改 tracked 文件清单 |
| `E-credential-scan-strict-hits.txt` | 严格凭据形态扫描命中（**空文件 = 0 命中**） |
| `F-linkcheck.txt` | 独立链接检查器输出（TOTAL broken = 23 及逐条明细） |
| `linkcheck.py` | QA 自写的链接检查器（口径写在脚本 docstring 内，可复跑） |
| `D-random-sample.txt` | D4 随机抽查的 5 个 worktree 逐项核验输出 |
| `D3-e2e-list.txt` / `D3-integration-list.txt` | 两份 playwright `--list` 清单（证明不含 `first-use-real.spec.ts`） |
| `G-ci.md` + `G-run-list.json` + `G-pr-checks-21.txt` | G 真实 CI：run 列表、指定 run 的 headSha/conclusion、`gh pr checks 21` |
| `verify_manifests.py` | E2 的独立自校验脚本（可复跑） |

## 大日志去向（不入库）

原始完整日志（pytest / vitest / playwright / build / lint 全量 stdout 与 64 行宽口径凭据命中明细）
留在 QA checkout 的 `.local/qa/cleanup-verify/`（Git 忽略），随 QA worktree 一并删除；
其中可复跑的判定性摘要已脱敏摘入本目录。宽口径凭据命中的**类别与误报理由**逐条写在
[D-E-F-H-details.md](D-E-F-H-details.md) §E3，未把合成测试标记原文以外的内容带出。

## 限制（摘要）

1. 结论**只对 `7a448c3` 有效**。
2. 归档 `MANIFEST` 只能**自校验**：源 worktree 已在 C5 删除，无法再由源目录独立复证；
   仅 C3 的两个被删文件可由 Git 对象库独立复证（见 H2）。
3. CI **从未在 `7a448c3` 上运行**（该提交未 push）；G 的 success 对应 `af65f04` 等其它 SHA。
4. 完整「本 PASS 明确不覆盖」清单见结论报告的对应小节。
