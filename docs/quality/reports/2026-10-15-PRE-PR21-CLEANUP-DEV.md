# PR #21 合并前仓库清理 · Developer 报告（2026-10-15）

日期：2026-10-15 / 2026-10-16（UTC）。分片：C7 · 起点交接 + 清理报告。
执行者：Developer **Luna（High）**。分支 `codex/frontend-ux-20261015`。
工作目录：`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`。

本报告是**本轮清理的 Developer 报告**，逐项给出 路径 / 判定 / 证据 / 动作 / 验证命令与退出码。
对照基准是本轮开始前落盘的分片计划 [2026-10-15-PRE-PR21-CLEANUP-PLAN.md](../../handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md)。

> **本报告是 DEV 自测记录，不是独立 QA 或 Sol 门判断。** 新鲜 QA 将在固定 tip 的独立 checkout 上另行验收。
> 报告内的结论只对本轮实测的 SHA 有效。

## 0 · 结论摘要

| 分片 | 目标 | 结果 |
|---|---|---|
| C0 | 计划落盘 | 完成（`8973b5a`） |
| C1 | 文档事实收敛 + 报告索引补全 + 修 1 条相对路径笔误 | 完成（`9a9aba8`）；broken 8 → 7 |
| C3 | 孤儿与冗余处置（先归档再删） | 完成（`9d6e097`） |
| C2 | 19 个 worktree 证据归档 + 删除路径索引 | 完成（`207b8f9`）；1679 行清单 / 395 复制件 / 凭据 0 |
| C4+C5 | 6 个分支清退 + 19 个 worktree 清退 | 完成（`32aa10c`）；`worktree list` 21 → 2 |
| C5.5 | 范围外残留目录清理（用户另授权） | 完成；55 条删除，目录 56 → 1 / 1.1G → 804M |
| C6 | CI 显示名 + 清理后 tip 的真实 CI 绿 | 完成（`af65f04` / `68c3639` / Sol 纠正 `ebb6b6f0`）；真实 run success |
| C7 | 本报告 + 起点交接 | 本报告与 [NEXT-STAGE-2026-10-16.md](../../handoff/NEXT-STAGE-2026-10-16.md) |

**产品面逐字节未变**（`git diff e8e1dba <tip>` 冻结面 pathspec → exit 0，空 diff），
**前端指纹未变**（`784ae1ee…`），**自动检查计数无一下降**。

## 1 · 分片与 commit 链（实测）

计划原本的编号顺序是 C2 → C3；实际提交顺序是 **C0 → C1 → C3 → C2 → C4+C5 → C6**。
差异只影响提交次序，不影响门限：计划的唯一硬约束是「C2 归档必须先于 C5 删除」，实测满足
（`207b8f9` < `32aa10c`）。下表为 `git log --oneline` 实测：

| SHA | 分片 | 内容 | 提交者 |
|---|---|---|---|
| `8973b5a` | C0 | `docs/handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md` | Luna |
| `9a9aba8` | C1 | PROGRESS 补 PR #21 三次 run；`reports/README.md` 补 86 行完整索引；修 1 条相对路径笔误 | Luna |
| `9d6e097` | C3 | 归档并删除 2 个孤儿文件；`tasks/plan.md`、`tasks/todo.md` 移入 `docs/handoff/history/`；删 `/tmp/summit-ws` | Luna |
| `207b8f9` | C2 | 19 个 worktree 全量 SHA-256 清单 + 395 个小原件 + `DELETED-PATHS-INDEX.md` | Luna |
| `32aa10c` | C4+C5 | 本地 4 + 远端 2 分支删除；19 个 worktree 删除 | Luna |
| `af65f04` | C6 | workflow `name:` 改名（恰好 1 行） | Luna |
| `68c3639` | C6 | CI 证据 `docs/quality/reports/evidence/2026-10-15-cleanup-ci/README.md` | Luna |
| `ebb6b6f0` | C6 | **Sol 追加**：纠正「docs-only 不再触发 run」的假设，并记录第二次真实 run | Luna（Sol 指令） |
| `412e0fd` | C7 | 本报告 + [NEXT-STAGE-2026-10-16.md](../../handoff/NEXT-STAGE-2026-10-16.md) 起点交接（4 files changed, 636 insertions(+)） | Luna |
| `7a448c3` | C7b | 修 `DELETIONS.md` 内 2 条 `../DELETED-PATHS-INDEX.md` 链接笔误；`reports/README.md` + `DELETED-PATHS-INDEX.md` 补全索引（3 files changed, 19 insertions(+), 2 deletions(-)） | Luna |
| `904a38d` | QA | 独立 QA 报告 `docs/quality/reports/2026-10-15-PRE-PR21-CLEANUP-QA.md` 及其证据（19 files changed, 1411 insertions(+)） | 全新 QA |

> **与任务书基线的偏差（如实登记）**：任务书写的分支 tip 是 `68c3639`。本报告的写作 tip 为
> **`ebb6b6f0c9a8c57d7eb5108e497661b7d50e11f5`**（Sol 的 CI 证据纠正提交，已 push）；其后
> `412e0fd` / `7a448c3` 为本轮后续 docs 提交，`904a38d` 是 QA 的独立验收报告。

验证：

```sh
git log --oneline -8
git rev-parse HEAD          # 写作时 = ebb6b6f0c9a8c57d7eb5108e497661b7d50e11f5
git status --porcelain      # 空
```

## 2 · C1 · 文档事实收敛

**改动面（恰好 3 个文件，`git show --stat 9a9aba8` 实测：3 files changed, 95 insertions(+), 2 deletions(-)）**

| 路径 | 判定 | 动作 | 证据 |
|---|---|---|---|
| `docs/implementation/PROGRESS.md` | 「远端离线 CI」行仍只写 M4.2 run `38550700081`，未记 PR #21 的三次 run | 只纠正文该行：补 `38756944004`（失败＝仅 `Build and verify internal App and DMG`，原因 `hdiutil: create failed - Resource busy`）、`38757225760`（4m42s success）、`38758095886`（4m0s success） | 该 commit 的 diff hunk `@@ -40,7 +40,7 @@`，其余行未动 |
| `docs/quality/reports/README.md` | 直接层历史报告未被索引，索引与文件不一一对应 | **只追加**「历史报告完整索引」小节，标签一律取该文件 H1 原文 | 该 commit 新增 **86 行**索引行（`git show 9a9aba8 -- docs/quality/reports/README.md \| grep -c '^+| \['` = 86） |
| `docs/quality/reports/evidence/2026-10-15-frontend-b-dev/README.md` | 相对路径笔误 `../2026-10-15-FRONTEND-B-DEV-REPAIR1.md` | 改为 `../../2026-10-15-FRONTEND-B-DEV-REPAIR1.md` | 该 commit 的 1 行 diff；目标文件此时已可解析 |

**索引缺口核查（逐 revision 实测）**

| revision | `docs/quality/reports/` 直接层报告数（不含 `README.md`） | 未被 `reports/README.md` 引用 |
|---|---|---|
| `9a9aba8`（C1 后） | 118 | **0** |
| `9d6e097`（C3 后，追加 2 行 `tasks/*` 归档行） | 118 | 0 |
| `ebb6b6f0`（C6 后） | 119（新增 `DELETED-PATHS-INDEX.md`） | 1 = `DELETED-PATHS-INDEX.md` 自身 |

即 **C1 时点的直接层报告缺口为 0**；C6 后变成 1，因为 C2 在 C1 之后新增了
`docs/quality/reports/DELETED-PATHS-INDEX.md`（它是索引文件，不是报告），而 `reports/README.md`
不在本片允许面内，未再补行。**此项已列入上报项（见 §11 第 2 条），并已由 `7a448c3` 收口。**

**相对链接失效 8 → 7（实测）**

链接检查脚本 `/tmp/linkcheck.py`（口径：所有 tracked `*.md`，跳过 `http(s)` / `mailto:` / `#`）：

```sh
python3 /tmp/linkcheck.py
```

| revision | broken |
|---|---|
| `e76244e`（C1 前） | **8**（7 条 `/Users/…` 历史绝对路径快照 + 1 条 `frontend-b-dev/README.md` 相对路径笔误） |
| `9a9aba8`（C1 后） | **7**（余下的 7 条全部是历史报告正文里的 `/Users/…/.codex/worktrees/…` 绝对路径快照） |

7 条的分布见 [DELETED-PATHS-INDEX.md](DELETED-PATHS-INDEX.md) §0：`2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md`
3 条、`2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md` 4 条，历史正文逐字保留、未改写。

**动作**：只纠正文事实 + 补索引 + 修 1 条笔误；**未删任何历史报告、未改任何历史报告正文**。
**回滚**：`git revert 9a9aba8`（纯文档，无损）。

## 3 · C2 · 证据归档与索引

**路径**：`docs/quality/reports/evidence/2026-10-15-worktree-archive/`（19 个子目录 + `README.md`
+ `CANDIDATE-IDENTITY.md` + `DELETIONS.md` + `generate-manifest.py`）与
`docs/quality/reports/DELETED-PATHS-INDEX.md`。commit `207b8f9`（419 files changed, 16431 insertions(+)）。

**判定**：19 个待删 worktree 的 `.local/` 不在 Git 内，删除即永久消失 → **必须先归档原件字节并全量记账**。

### 3.1 19 个 worktree 的 MANIFEST 行数（逐条实测）

| worktree | MANIFEST 行数 | 其中 `TREE` 行 | 归档文件数 | 归档字节 |
|---|---|---|---|---|
| `frontend-a-qa-initial` | 47 | 0 | 47 | 4042096 |
| `frontend-a-qa-repair1` | 72 | 0 | 72 | 7408051 |
| `frontend-b-qa-initial` | 125 | 0 | 125 | 8881225 |
| `frontend-b-qa-repair1` | 211 | 0 | 211 | 10577552 |
| `frontend-c-qa-initial` | 87 | 0 | 87 | 2472667 |
| `frontend-d-build` | 0 | 0 | 0 | 0（`.local` 本机已不存在，已知例外） |
| `frontend-d-build-repair2` | 3 | 1 | 2 | 22145475 |
| `frontend-d-build-repair3` | 3 | 1 | 2 | 22145235 |
| `frontend-d-final` | 21 | 1 | 20 | 22226878 |
| `frontend-d-qa-initial` | 178 | 0 | 178 | 12922381 |
| `frontend-d-qa-repair1` | 240 | 0 | 240 | 15752645 |
| `frontend-d-qa-repair1-parent` | 24 | 0 | 24 | 819369 |
| `frontend-d-qa-repair2` | 268 | 0 | 268 | 15848221 |
| `frontend-d-qa-repair2-parent` | 33 | 0 | 33 | 714237 |
| `frontend-d-qa-repair3` | 208 | 0 | 208 | 12981047 |
| `frontend-d-qa-repair3-parent` | 6 | 0 | 6 | 5761 |
| `m41-internal-app` | 96 | 5 | 91 | 109999472 |
| `m41-qa-b9321d6` | 22 | 0 | 22 | 18179 |
| `m41-qa-repair1-3f6eaa4` | 35 | 0 | 35 | 369027 |
| **合计** | **1679** | **8** | **1671** | — |

复算命令（2026-10-16 在 `ebb6b6f0` 上重跑，与归档 README §3 一致）：

```sh
for f in docs/quality/reports/evidence/2026-10-15-worktree-archive/*/MANIFEST.sha256; do
  printf "%s lines=%s tree=%s\n" "$f" "$(wc -l < "$f")" "$(grep -c '^TREE ' "$f")"; done
# 实测 TOTAL_LINES=1679 TREE_LINES=8 FILE_LINES=1671，exit 0
```

### 3.2 复制件、凭据扫描、重算

| 项 | 实测 | 验证方式 |
|---|---|---|
| 复制原件数 | **395** | `find …/2026-10-15-worktree-archive -type f ! -name MANIFEST.sha256 ! -name generate-manifest.py \| wc -l` = 398，减去 3 个顶层说明文档（`README.md` / `DELETIONS.md` / `CANDIDATE-IDENTITY.md`）= **395** |
| 复制原件字节 | **888861** | 同集合 `stat -f%z` 求和 = 932695，减 43834（三个顶层文档）= **888861** |
| 凭据扫描命中 | **0** | 本次独立重跑 7 类正则（`bearer_token` / `sk_key` / `gho_token` / `ghp_token` / `session_token_assign` / `app_secret` / `api_key`）覆盖全部 **395** 个复制件 → `CREDENTIAL hits= 0` |
| MANIFEST 逐条重算 | **0 缺失 / 0 不符** | 删除前由 `/tmp/sol-verify-archive.py` 对 **1671** 条文件行逐条比对源文件 SHA-256；复制件比对 **395** 条 → `copy mismatch: 0`（**删除后不可重跑**，因为源已随 worktree 消失） |
| 复制件抽样逐字节复核 | **16/16 一致** | 每个有复制件的 worktree 各抽 1 个（取字节最大者）重新 `shasum -a 256`，记录见 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) §6 |
| MANIFEST 格式 | `<sha256> <size> <relpath>`，`.app` 为 `TREE <tree_sha256> <count> <relpath>` | 生成器 [generate-manifest.py](evidence/2026-10-15-worktree-archive/generate-manifest.py) 随提交入库 |

> 40 位十六进制串在该批文件中大量出现（SHA-256 与 commit SHA），**未列为凭据类别**——否则会把正常哈希记账误判成泄漏。

### 3.3 8 个 `.app` 目录树摘要（删除前实测）

| `.app`（相对 `.local`） | 文件数 | 树摘要 |
|---|---|---|
| `dev/m41/artifacts/SummitEverything Internal 2.app` | 156 | `942fcfa9a60b74d522ab66e5e2f48408918d8da0ee96b7815aacdb052fc87a02` |
| `dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app` | 156 | `96face5e21c4d237018bc86e8ab89d74651ac4bad5caaea653580a93475def73` |
| `dev/m41/artifacts/SummitEverything Internal M4.1-DV3.app` | 156 | `b583b068c0148574aec25f1712f2b15a2bb0d090aa685d0d05e573cee99b57de` |
| `dev/m41/artifacts/SummitEverything Internal.app` | 156 | `533583d11cb1430f719ba17a8e72abaf57f94c8325c35acbe204a3f6ac628c99` |
| `dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app` | 156 | `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb` |
| `dev/frontend-d-repair2/SummitEverything-D-96fdf4d.app` | 157 | `6944d670f936a746d860315bd15a6f91977f45919c2193b8e402619744288cc9` |
| `dev/frontend-d-repair3/SummitEverything-D-e8e1dba.app` | 157 | `f634fc05101a21ead924ea80cb755c40a5a02145b507f23dedd3dfbb791e635f` |
| `dev/frontend-d-final/SummitEverything-D-876008e.app` | 157 | `01fb7046ce4c291a0525d2b085370ad94196bb23beac0e904e2b3f8ea1b5a9f8` |

### 3.4 三个 D 候选 DMG 实测 SHA-256（删除前独立复算）

| 候选 | DMG 整文件 SHA-256 |
|---|---|
| `e8e1dba`（最终） | `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b` |
| `876008e`（初次） | `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9` |
| `96fdf4d`（修复轮 2） | `bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765` |

三者与对应 `MANIFEST.sha256` 内记录一致；`.app` / `.dmg` 二进制按用户决定**随 worktree 删除、不另存**，
此后身份只由 SHA-256 与 `build-info.json` 全文保留，见 [CANDIDATE-IDENTITY.md](evidence/2026-10-15-worktree-archive/CANDIDATE-IDENTITY.md) §5。

### 3.5 `DELETED-PATHS-INDEX.md` 的 7 条

[DELETED-PATHS-INDEX.md](DELETED-PATHS-INDEX.md) 用不硬编码的扫描脚本列出所有 tracked `*.md` 中
指向上级目录 worktree 的**绝对路径链接**，实测**恰好 7 条**：

- `docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md` 3 条（第 9 / 9 / 13 行，均指向 `m3-package-1-qa`）——
  该 worktree 在 2026-10-15 之前即已移除，**无原件可归档**，属历史快照；指向的源码行以固定 SHA 可复现。
- `docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md` 4 条（第 60 / 68 / 68 / 76 行，均指向
  `frontend-a-qa-initial`）——该 checkout 属本轮删除集，证据已归档（47 文件 / 4042096 字节），
  指向的源码行可用该 worktree 的 HEAD `9ed544ab…` 取出。

**动作**：只建索引、映射去向；历史正文一字不改。**回滚**：`git revert 207b8f9`（此时 worktree 尚未删除，无损）。

## 4 · C3 · 孤儿与冗余处置

commit `9d6e097`（8 files changed, 217 insertions(+)；两个被删文件以 rename 语义归档）。

| 路径 | 判定 | 动作 | 无引用 / 一致性证据 | 验证命令与退出码 |
|---|---|---|---|---|
| `web/e2e/first-use-real.spec.ts`（`0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3`） | 4 个 playwright config 的 `testMatch` 全部未命中；两份既有 harness 副本 SHA 均不同（`539bfb7e…` / `297e580a…`） | 归档原件到 `evidence/2026-10-15-cleanup-orphans/` → 删 | `grep -n testMatch web/playwright*.ts` 命中集合为 `viewport.spec.ts`、`first-use.spec.ts`、`frontend-c-view.spec.ts`、`frontend-c-flow.spec.ts`、`approval-today.spec.ts`，无一条为该文件 | `npm --prefix web run test:e2e -- --list` → **2 tests / 2 files**；`test:e2e:integration -- --list` → **1 test / 1 file**（删除后计数未降） |
| `scripts/build_macos_app.sh`（`1983dbf08374f063bc9334da46b9a8603487388eea7fc3a3c8716663f5312c2a`） | 全仓 0 引用，已被 `.py` 取代 | 归档原件 → 删 | `git grep -n "build_macos_app.sh"` 除自身 usage 与清理计划清单外无命中；`scripts/release-macos.sh:12` 调用的是 `build_macos_app.py` | 同上；冻结面 pathspec → 0 |
| `tasks/plan.md` → `docs/handoff/history/2026-10-11-STAGE-B-C-PLAN.md` | 仍是 Stage B/C「当前计划」，SHA 停在 `576895f`，无当前入口引用 | **移动**（非删除），顶部加 1 行归档声明 | 逐字一致性：与 `576895f` 时的 `tasks/plan.md` 逐行比对，**除顶部 1 行声明外完全一致** | 程序化比对输出 `IDENTICAL after 1 leading line(s)` |
| `tasks/todo.md` → `docs/handoff/history/2026-10-11-STAGE-B-C-TODO.md` | 同上 | 同上 | 同上 | 同上 |
| `/tmp/summit-ws` | 主机级一次性测试工作库（非真实业务材料） | 删（`rm -rf`），另有内容的 `/tmp/summit-*` 一律保留 | 清理前 4 个文件的 SHA-256 已记录；`conventions.md` 内容为通用占位，仓库内已有可复现副本 | 清理前 `ls -d /tmp/summit-*` = 16 项 → 清理后 15 项；`find /tmp -maxdepth 1 -type d -name 'summit-*' -empty` 前后均为空 |

### 4.1 `/tmp` 其它目录内容消失的原因（**非 agent 删除**）

C3 之后观测到 `/tmp/summit-*` 中若干目录内容变空。实测 **mtime 全部是整点 `00:00:00`**，
符合 **macOS periodic cleaner 在 00:00 清理 3 天未访问文件**的签名：

```
2026-10-15 00:00:00 /tmp/summit-deepseek-stage-b-replay
2026-10-14 00:00:00 /tmp/summit-m1-fix-replay-nwyhoS
2026-10-15 00:00:00 /tmp/summit-m2-final-workspace
2026-10-15 00:00:00 /tmp/summit-m23-browser-workspace
2026-10-15 00:00:00 /tmp/summit-stage-b-browser-workspace
2026-10-15 00:00:00 /tmp/summit-stage-b-sol-mypy-cache
```

对照：非 cleaner 触及的目录 mtime 均为常规时间（`2026-10-13 09:45:49`、`2026-10-13 12:45:56` 等）。
**结论**：这些内容的消失是主机级自动清理，**不是**本轮 agent 删除；本轮 agent 只删了 `/tmp/summit-ws`
与当时存在的 0 字节空目录。`/tmp` 不属于本仓库操作范围，故不作为唯一追溯来源（长期证据全部落在仓库内）。

## 5 · C4 · 分支清退（实测输出见 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) §C4）

| 分支 | 类型 | 删除前 SHA | `git merge-base --is-ancestor <b> origin/main` |
|---|---|---|---|
| `codex/frontend-baseline-20261014` | 本地 | `38986493bfbac24e216663922d6a793fda574cbb` | **exit 0** |
| `codex/internal-candidate-20261014` | 本地 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **exit 0** |
| `codex/origin-guard-error-20261014` | 本地 | `258f7d820d68673183e62a5b998879ad0d9ca59d` | **exit 0** |
| `codex/settings-ux-20261014` | 本地 | `6f9191d8b8b62f3957ac5eacb207d34202e69abf` | **exit 0** |
| `origin/codex/frontend-baseline-20261014` | 远端 | `38986493bfbac24e216663922d6a793fda574cbb` | **exit 0** |
| `origin/codex/internal-candidate-20261014` | 远端 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **exit 0** |

**6/6 `ancestor_exit=0`**，即全部在 `origin/main` 历史中，删除不丢失未合并提交。

```sh
git branch -d codex/frontend-baseline-20261014 codex/internal-candidate-20261014 \
               codex/origin-guard-error-20261014 codex/settings-ux-20261014
# 实测 4 行 "Deleted branch …"，BRANCH_DELETE_EXIT=0（用 -d，非 -D）
git push origin --delete codex/frontend-baseline-20261014 codex/internal-candidate-20261014
# 实测 2 行 " - [deleted]"，REMOTE_DELETE_EXIT=0；--delete 只删分支，未 push 到 main
```

删除后：`git branch -vv` 只剩 `codex/frontend-ux-20261015` + `main`；
`git ls-remote --heads origin`（exit 0）只剩
`refs/heads/codex/frontend-ux-20261015`（`68c3639`，写作时为 `ebb6b6f0`）+ `refs/heads/main`（`e84e9e5`）。
**未删** `main` 与 `codex/frontend-ux-20261015`，**未 force**，**未改产品树**。

## 6 · C5 · worktree 清退（实测输出见 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) §C5）

**前置门（缺一不删）**：C2 归档已由 Sol 复核通过；`DELETIONS.md` 已含每个 worktree 的原件索引。
实测 `ls -d …/2026-10-15-worktree-archive/*/ | wc -l` = **19**；18 个 `MANIFEST.sha256` 非空，
`frontend-d-build` 为空清单（§3.1 的已知例外）。

| 项 | 实测 |
|---|---|
| 删除前逐个 `git -C <path> status --porcelain` | **19/19 为空（DIRTY_COUNT=0）** |
| `git worktree remove --force <path>` | **19/19 removed，exit 0** |
| `git worktree prune` | `PRUNE_EXIT=0`，无 `prunable` |
| `git worktree list \| wc -l` | **2**（期望 2）：main `e84e9e5` + `frontend-ux-20261015` |
| 目录体积 | `du -sh /Users/yifengstudio/.codex/worktrees` **8.8G → 1.1G** |
| 保留项 | 主仓库目录与 `.local/internal-builds/{3f6eaa4,internal-f40bc39,m42-419bb86,main-bce8843}` 四个目录均保留 |

**偏差（如实登记）**：删除后目录仍是两类残留（父目录壳 + 范围外历史孤立目录），故 1.1G 而非约 0.7G。
两类残留均由用户在 2026-10-15 **另行授权**后清理，见 §7。

## 7 · C5.5 · 范围外残留目录清理（用户 2026-10-15 另授权）

| 项 | 实测 |
|---|---|
| 授权来源 | 用户在 2026-10-15 单独授权（两项询问均选 A）；**不在**原清理计划的 19 个 worktree 删除集内 |
| 删除条数 | **55** |
| 删除前 | `/Users/yifengstudio/.codex/worktrees` = **56 条 / 1.1 G** |
| 删除后 | **1 条 / 804 M**（唯一保留 `frontend-ux-20261015`） |
| 构成 | 19 个 0B 父目录壳（只剩 `.codex-worktree-name` 标记，部分全空）+ 36 个范围外历史孤立目录（32 个 0B、`m1-close` 8.0K、3 个 Python venv 共 **334 MB**：`qa-stage-a-final-env` 113M、`qa-stage-a-final-env-2` 113M、`qa-stage-a-final-venv` 108M） |
| 守卫条件 | 只删 ①绝对路径位于 `/Users/yifengstudio/.codex/worktrees/` 之下、②非保留项、③不在 `git worktree list` registry 中的条目 |
| 逐条清单与分类 | 见 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) §C5.5（55 行表） |
| 快照 | 删除前后逐条体积快照：`/tmp/sol-worktrees-dir-before.txt`（56 行）与 `/tmp/sol-worktrees-dir-after.txt`（1 行），**主机级、未入库** |

**唯一 tracked 引用（实测校正）**：3 个 venv 中只有 `qa-stage-a-final-env-2`
被 tracked 报告按路径提及——`docs/quality/reports/2026-10-10-M2-stage-a-final-qa.md` 第 14 行记为
「安装运行依赖的外部隔离环境」。该句作为**历史陈述仍成立**，且该目录不是证据原件（venv 不入清单、不复制）。
补充实测：36 个范围外项里被 tracked 文档以 **Markdown 链接**形式指向的只有 `m3-package-1-qa`
（3 条，已在 §3.5 索引）；其余提及均为行内代码 / 原始日志里的路径快照，**不是链接**，不影响链接面。
`git grep` 粗筛显示 402 个 tracked 文件命中至少一个范围外目录名——但它们全部是历史陈述与原始日志，
本轮**没有**改写（符合 AGENTS「历史报告正文保留原样」）。

## 8 · C6 · CI 显示名与清理后 tip 的真实 CI

**改动面**：只改 `.github/workflows/m41-internal-app.yml` 第 1 行 `name:`。

```sh
git diff -U0 af65f04^ af65f04 -- .github/workflows/m41-internal-app.yml
```

```diff
@@ -1 +1 @@
-name: M4.1 internal macOS app
+name: offline-arm64 checks (python, web, native, DMG)
```

`git diff --numstat` = `1  1  .github/workflows/m41-internal-app.yml`（恰好 1 行）。
**触发面未变**（逐字节证明）：改动前后去掉第 1 行后的全文 SHA-256 均为
`0e39da273864688b5ea2acefab4342262a098322fbc0e7869d8db7c55a5761e8`，`diff` 退出码 0
（`push.paths` / `pull_request.paths` 各 8 条逐字相同，`workflow_dispatch:` 仍在）。

**真实 run（`gh` 实测）**

| run | 事件 | headSha | 结论 | 墙钟 | 四步骤 |
|---|---|---|---|---|---|
| [`38831085564`](https://github.com/yifeng93/SummitEverything/actions/runs/38831085564) | `pull_request` | `af65f049a12caebbcb932a86e610282702e1ffc3`（= 清理后 tip） | **completed / success** | 4m45s | `Guarded Python checks` / `Web checks and API types` / `Native upload policy tests` / `Build and verify internal App and DMG` **全部 success** |
| [`38831643643`](https://github.com/yifeng93/SummitEverything/actions/runs/38831643643) | `pull_request` | `68c36399c3ecc02b35be3fa2110c97fae3fcde0d` | **completed / success** | 4m08s | 同上，全部 success |

两次 run 均未出现 `hdiutil: create failed - Resource busy`，`--log-failed` 为 0 字节，**未重跑**。
证据与原始输出见 [evidence/2026-10-15-cleanup-ci/README.md](evidence/2026-10-15-cleanup-ci/README.md)。

**更正（Sol `ebb6b6f0`）**：原假设「docs-only 提交不再触发 run」**被实测推翻**——
`68c3639`（只改 `docs/**`）仍然触发了 `38831643643`。可得结论：**在本 PR 上，任何 push（含 docs-only）
都会触发该 workflow**，因为 `pull_request` 的 `paths` 过滤器按 PR 相对 base 的整体 diff 判定。
因此 `ebb6b6f0` 自身又触发了一次 run（`38832106964`，写作时 `in_progress`）；按该文件的既定决定，
**不再回写该文件以免形成「改文档 → 又触发 run」的循环**。本报告同样不因自身提交而回写 run 结果。
更正命令的退出码：`git diff -U0 af65f04^ af65f04` → 0；`git show --stat 68c3639` → 0。

## 9 · 硬不变量（实测退出码与计数）

| 不变量 | 实测 | 验证命令 |
|---|---|---|
| 产品面逐字节冻结 | **exit 0，空 diff** | `git diff e8e1dba HEAD -- src 'web/src' ':(exclude)web/src/*.test.ts' ':(exclude)web/src/*.test.tsx' ':(exclude)web/src/**/*.test.ts' ':(exclude)web/src/**/*.test.tsx' web/package.json web/package-lock.json pyproject.toml uv.lock native; echo "FROZEN=$?"` → `FROZEN=0` |
| 前端指纹 | **`784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`** | `PYTHONPATH=src python3 -c "from summit_everything.release import fingerprint_web_dist; print(fingerprint_web_dist('web/dist'))"` → exit 0，与 `e8e1dba` 的 `build-info.json` 一致 |
| pytest | **692 passed** | 本轮分片实测（C1–C6 期间），Sol 复核 |
| vitest | **222 passed / 26 files / 0 todo** | 同上 |
| `test:e2e` / `test:e2e:integration` | **2** / **1** | 同上；删除 C3 孤儿 spec 后计数未降 |
| typecheck / lint / build | **exit 0 / exit 0（2 条既存 warning）/ exit 0** | 同上 |
| `ruff check` / `ruff format --check` / `mypy` / `uv lock --check` / `uv build` | **全 exit 0**（mypy 47 files） | 同上 |
| `api:types` 后生成文件稳定 | `git diff --exit-code -- web/src/api/generated.ts` → **0** | 同上 |
| 相对链接失效 | **C1 口径 8 → 7**（见 §2）；**全仓 broken = 23**（`904a38d` 实测，`7a448c3` 已修 2 条后） | C1 脚本口径（所有 tracked `*.md`）：`e76244e` = 8 → `9a9aba8` = 7。**全仓 broken = 23**，分解为 **7** 条历史报告正文的 `/Users/…` 绝对路径快照 + **16** 条位于 `evidence/2026-10-15-worktree-archive/` 下被 `MANIFEST.sha256` 固定的逐字归档副本内部 + **其它 0**。C1 的「8 → 7」口径指的是**非归档、自撰文档**的失效率，与全仓口径不同，**不可混用** |
| `docs/quality/reports/**` markdown 数 | **268**（只增不减；计划阈值 ≥ 209） | `git ls-files -- 'docs/quality/reports/**' \| grep -c '\.md$'` |
| 归档完整性 | MANIFEST **1671** 文件行逐条重算 → **0 缺失 / 0 不符**；复制件 **395** → **0 不一致** | `/tmp/sol-verify-archive.py`（删除前，Sol 脚本） |
| 凭据泄漏 | 395 个复制件 × 7 类形态 → **命中 0** | 本报告 §3.2 的独立重跑 |
| CI 绿 | run `38831085564` 与 `38831643643` 均 **completed / success** | `gh run list --branch codex/frontend-ux-20261015` |

> 上表中 pytest / vitest / e2e / 静态检查的计数来自**本轮分片的实测输出并经 Sol 复核**（任务基线），
> 本报告没有再重跑这些较重的项；本报告**重跑**了冻结面 pathspec、前端指纹、归档复制件凭据扫描、
> MANIFEST 行数复算、链接检查与仓库/远端状态，实测值见上表与各节。

## 10 · 本轮不覆盖的内容（明确不宣称）

- **真实服务与真实门**：真实 provider、飞书 OAuth、Keychain 生命周期、真实业务材料、已安装 App、
  Developer ID 与公证、五日、双机、生产与发布 —— 全部 **NOT_RUN**，各自需用户按准备卡单独授权。
- **`pageZoom`**：200% 浏览器菜单缩放与原生 `pageZoom` **NOT_RUN**（640 CSS px 只是 reflow，
  root CSS zoom harness 只是 simulation）。
- **native GUI 的独立复现**：D 门的三条 native 路径由 **Sol 实机以本机 Vision OCR 判读**通过，
  QA 无 GUI 能力、**未独立复现**；如需第三方独立验证，必须另行授权。
- **D-3（INFO）**：`GET/PUT /api/v1/first-use/progress` 的 OpenAPI 只声明 200/422，
  未声明实际存在的 401/404/503；前端依赖 404 `first_use_progress_absent` 做控制流。**本片未并入**。
- **D-5（P3，用户已决议接受）** 与 **D-2（P3，dev 专属）**：按既有表述记录，本片不改。
- **合并本身**：**Sol 未 merge，也不会 merge**；PR #21 仍未合并，需用户明确批准。

## 11 · 上报项及其处置（已收口）

本节原文写于写作 tip `ebb6b6f0`，标题原为「需 Sol 裁决的残留（如实上报）」。其中第 1、2、3 条
**已由 C7b `7a448c3`（及 QA 报告入库）处置完毕**；下列**原文保留以便追溯**，每条后加一行「处置：」。

1. **链接口径**：C1 口径（所有 tracked `*.md`）在 `9a9aba8` 时是 7。到 `ebb6b6f0` 时，同一脚本给出
   **25**，差额 18 全部由 C2/C5 引入：**2** 条是
   `docs/quality/reports/evidence/2026-10-15-worktree-archive/DELETIONS.md` 里
   `../DELETED-PATHS-INDEX.md`（应为 `../../DELETED-PATHS-INDEX.md`，文件实际在
   `docs/quality/reports/DELETED-PATHS-INDEX.md`）；**16** 条在逐字归档的 QA 报告副本内部，
   指向未被复制的兄弟证据文件（归档为逐字复制，按设计不改写）。
   本片允许面只包含该文件的**末尾追加**，故**未修**这 2 条；如 Sol 认为该修，请扩面或由 Sol 直接改 2 个字符。
   **处置：已由 `7a448c3` 处置** —— `DELETIONS.md` 的 2 条链接已改为 `../../`；全仓 broken
   25 → **23**（= 7 条历史报告 `/Users/…` 快照 + 16 条逐字归档副本内部 + 其它 0，见 §9）。
2. **索引缺口**：C1 后新增了 `docs/quality/reports/DELETED-PATHS-INDEX.md`（C2）与本 DEV 报告（C7），
   `docs/quality/reports/README.md` 的索引未再补行（不在允许面内）。**建议 Sol 决定**是补索引行还是
   接受「索引文件与小节本身不计缺口」的口径。
   **处置：已由 `7a448c3` 补全** —— `reports/README.md` 补入缺失索引行，缺口 **0/121**；
   QA 报告入库后为 **121/0**（索引缺口 0）。
3. **范围外清理条数**：任务书写「34 个范围外历史孤立目录」，**实测为 36**（19 个壳 + 36 = 55 条删除）。
   36 = 32 个 0B + `m1-close` 8.0K + 3 个 venv。逐条清单以 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) §C5.5 为准。
   **处置：以实测 36 为准**（任务书的 34 为口径差异，已按 36 记录，不再改动数据）。
4. **「唯一 tracked 引用」措辞**：准确表述见 §7——`qa-stage-a-final-env-2` 是 venv 三件套中唯一被
   tracked 报告按路径提及者；范围外项中唯一被 **Markdown 链接**指向的是 `m3-package-1-qa`（3 条，已在索引）。
   **处置：已按 §7 的准确表述记录**，无待裁决项。

## 12 · 边界与自测声明

- 本片只改 / 建了 4 个 `docs/**` 文件（本报告、`docs/handoff/NEXT-STAGE-2026-10-16.md`、
  `docs/handoff/FRONTEND-EXECUTION-PLAN.md` 顶部状态块、
  `docs/quality/reports/evidence/2026-10-15-worktree-archive/DELETIONS.md` 末尾附录）。
- **未** push（Sol 统一处理）、**未** merge、**未** rebase、**未**改 `src/**` / `web/**` / `native/**` /
  `scripts/**` / `.github/**` / `pyproject.toml` / `uv.lock`，**未**改任何已有历史报告正文。
- 失败不得靠删测试、降低验收门收口；本片未删任何测试、未降低任何门。
- **本报告是 DEV 自测记录，不是独立 QA 或 Sol 门判断；新鲜 QA 将在固定 tip 的独立 checkout 上另行验收。**
