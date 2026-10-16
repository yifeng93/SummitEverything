# D · 删除可追溯性 · E · 归档完整性与凭据 · H · 对抗性检查（QA 独立实测）

全部命令在 `/Users/yifengstudio/.codex/worktrees/qa-cleanup-verify`（detached HEAD =
`7a448c39092b81d0afcb15ce4dc57d91faaa7e5e`）实测。

## D1 · 两个被删文件确已不存

```sh
git ls-files -- web/e2e/first-use-real.spec.ts scripts/build_macos_app.sh   # 无输出
ls -la web/e2e/first-use-real.spec.ts scripts/build_macos_app.sh
#   ls: scripts/build_macos_app.sh: No such file or directory
#   ls: web/e2e/first-use-real.spec.ts: No such file or directory
```

**Git 索引与文件系统双重确认：两者均不存在 → PASS。**

## D2 · 删除理由与归档件 SHA-256（QA 重算）

`docs/quality/reports/evidence/2026-10-15-worktree-archive/DELETIONS.md` §3「2 个被删 tracked 文件」
给出两行，含「判定理由 / 无引用证据 / 归档索引」三列：

| 被删路径 | DELETIONS.md 记录的 SHA | QA 重算归档件 SHA-256 | 一致 |
|---|---|---|---|
| `web/e2e/first-use-real.spec.ts` | `05926295…` | `0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3` | 是 |
| `scripts/build_macos_app.sh` | （见 cleanup-orphans `MANIFEST.sha256`） | `1983dbf08374f063bc9334da46b9a8603487388eea7fc3a3c8716663f5312c2a` | 是 |

归档目录 `docs/quality/reports/evidence/2026-10-15-cleanup-orphans/` 内含
`first-use-real.spec.ts`、`build_macos_app.sh`、`verify_tree_digest.py`、`MANIFEST.sha256`、`README.md`。

```sh
shasum -a 256 -c MANIFEST.sha256
# first-use-real.spec.ts: OK
# build_macos_app.sh: OK
# verify_tree_digest.py: OK
# CHECK_EXIT=0
```

DELETIONS.md §3 另记两份既有 harness 副本与原件**不同**；QA 复算其中一份：

```sh
shasum -a 256 docs/quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/harness/first-use-real.spec.ts
# 539bfb7ec6f02f9af67a957cb891c7cbd46257103650ecf49779d6f4114f651c   （与 DELETIONS.md 记载一致）
```

→ 既有副本确不能代表被删原件，归档原件本身是唯一可校验来源。**PASS。**

## D3 · 删除 `first-use-real.spec.ts` 不降低覆盖

`web/playwright*.config.ts` 共 **4** 个 tracked config，`testMatch` 实测：

```
web/playwright.config.ts:5:  testMatch: ['viewport.spec.ts', 'first-use.spec.ts'],
web/playwright.frontend-c-view.config.ts:11:  testMatch: ['frontend-c-view.spec.ts'],
web/playwright.frontend-c.config.ts:11:  testMatch: ['frontend-c-flow.spec.ts'],
web/playwright.integration.config.ts:11:  testMatch: ['approval-today.spec.ts'],
```

命中集合 5 个 spec，**无一为 `first-use-real.spec.ts`**。实测 `--list`：

```sh
npm --prefix web run test:e2e -- --list              # 2 tests in 2 files: first-use.spec.ts, viewport.spec.ts
npm --prefix web run test:e2e:integration -- --list  # 1 test in 1 file: approval-today.spec.ts
```

两份清单中 `first-use-real` 命中数均为 **0**（`grep -c` 实测 0 / 0）→ **PASS。**

## D4 · 随机抽查 5 项（种子 20261016，从 19 个待删 worktree 池随机取）

| worktree | DELETIONS.md 判定理由 | 归档索引 | 归档目录 | MANIFEST 非空 | §C5.2 删除记录 |
|---|---|---|---|---|---|
| `frontend-a-qa-initial` | 一次性 QA checkout，工作已并入 `9d6e097`；用户选定只保留 main + `frontend-ux-20261015` | `[MANIFEST](../2026-10-15-worktree-archive/frontend-a-qa-initial/MANIFEST.sha256)` | 存在（`MANIFEST.sha256`, `qa/`） | 是 | 有（removed exit 0） |
| `frontend-d-qa-repair3` | 最终 QA 已完成并留下结论，checkout 可清退 | `[MANIFEST](../2026-10-15-worktree-archive/frontend-d-qa-repair3/MANIFEST.sha256)` | 存在（`MANIFEST.sha256`, `dev/`, `qa/`） | 是 | 有 |
| `m41-qa-b9321d6` | 一次性 QA checkout | `[MANIFEST](../2026-10-15-worktree-archive/m41-qa-b9321d6/MANIFEST.sha256)` | 存在（`MANIFEST.sha256`, `qa/`） | 是 | 有 |
| `m41-internal-app` | 中间构建，二进制随删（身份见 CANDIDATE-IDENTITY.md §4） | `[MANIFEST](../2026-10-15-worktree-archive/m41-internal-app/MANIFEST.sha256)` | 存在（`MANIFEST.sha256`, `dev/`, `sol/`） | 是 | 有 |
| `frontend-b-qa-repair1` | 同上 | `[MANIFEST](../2026-10-15-worktree-archive/frontend-b-qa-repair1/MANIFEST.sha256)` | 存在（`MANIFEST.sha256`, `qa/`) | 是 | 有 |

**5/5 均具备「判定理由 + 归档索引 + 验证方式（§6 源件逐字节抽样复核 + §C5.2 删除前 clean/HEAD 记录 + removed exit 0），
且对应归档目录实际存在 → PASS。**

补充抽查 2 个被删分支（DELETIONS.md §2 / §C4.1 有 SHA 与 `--is-ancestor origin/main` 记录）：
`codex/settings-ux-20261014`（`6f9191d…`）、`origin/codex/internal-candidate-20261014`（`32d9b9e…`）。
QA 独立复验其 commit 对象**仍在对象库**且 `git merge-base --is-ancestor <sha> origin/main` = **0**
（`git cat-file -t` = commit）→ 删除未丢失任何未合并提交，可追溯。

## D5 · 分支与远端

```sh
git branch --format='%(refname:short)'     # main / codex/frontend-ux-20261015（QA worktree 内另显 (no branch)，即 detached QA checkout）
git ls-remote --heads origin
# ebb6b6f0c9a8c57d7eb5108e497661b7d50e11f5  refs/heads/codex/frontend-ux-20261015
# e84e9e5a56475a19f68ca1a684366fba7f9fee83  refs/heads/main
```

**本地恰好 2 个分支；远端恰好 2 个 head（`refs/heads/main` + `refs/heads/codex/frontend-ux-20261015`）→ PASS。**

## D6 · worktree

```sh
git worktree list      # 3 行：main、frontend-ux-20261015、qa-cleanup-verify（QA 自身）
```

**恰好 3 条（把 QA checkout 计入）→ PASS。**

## E1 · 归档区无二进制

```sh
git ls-files 'docs/quality/reports/evidence/2026-10-15-worktree-archive/**' | grep -iE '\.(app|dmg)(/|$)'
# 无输出
git diff --name-only --diff-filter=A e8e1dba 7a448c3 | grep -iE '\.(app|dmg)'      # 无输出
git ls-tree -r --name-only 7a448c3 | grep -iE '\.(app|dmg)$'                      # 无输出
```

归档区共 **418** 个 tracked 文件，**0 个 `.app`/`.dmg`** → PASS。

## E2 · 归档 MANIFEST 自校验（见 E-manifest-selfcheck.txt）

`MANIFEST.sha256` 行格式两种：`<sha256> <size> <relpath>` 与 `.app` 的
`TREE <tree_sha256> <file_count> <relpath>`。QA 独立脚本逐条对**归档目录内实际存在**的文件重算 SHA-256：

```
TOTAL file_lines=1671 ok=395 mismatch=0 absent=1276 TREE=8
TOTAL MANIFEST entries = 1671 file lines + 8 TREE lines = 1679
RESULT: PASS
```

即 **ok=395、mismatch=0**，总条目 **1679 = 1671 + 8**，与期望完全一致 → PASS。
`absent=1276` 是**设计内**的：复制规则只收 `*.md` / `*.sha256` / 名称含
`manifest|command-results|evidence` 的 `*.json` / `*.log` / `*.txt`（各有体积上限），
其余（含 `.dmg`、`.app`、超限日志、全部截图 PNG）只进 MANIFEST 不进复制集。

## E3 · 凭据形态扫描（`e8e1dba..7a448c3` 全部新增/修改 tracked 文件）

扫描面 = `git diff --name-only --diff-filter=AM e8e1dba 7a448c3` = **440** 个文件
（`A` 与 `R` 的归档/迁移路径按新路径计入；`R100` 的两个归档件也在其中）。

- **严格形态扫描（真实凭据长度/形状）**：`Bearer[[:space:]]+[A-Za-z0-9_.-]{20,}`、`sk-[A-Za-z0-9]{20,}`、
  `gho_[A-Za-z0-9]{20,}`、`ghp_[A-Za-z0-9]{20,}`、`SUMMIT_SESSION_TOKEN` / `app_secret` / `api_key`
  的赋值形态（名称 + `=` + 非引号非空白值）、私有密钥头 → **命中 0**
  （`E-credential-scan-strict-hits.txt` 为空）→ PASS。
- **宽形态扫描（宽松子串，用于暴露误报）**：命中 64 行，**逐条均为误报**，类别分布：
  - `Bearer` ×12：源码片段/日志里的 `Authorization: f"Bearer {token}"` 与文档散文（无实际令牌值）；
  - `gho_` ×5 / `ghp_` ×5：`docs/quality/reports/evidence/2026-10-15-worktree-archive/generate-manifest.py`
    与 `README.md` 里**正则定义本身**（`gho_[A-Za-z0-9]{20,}` 等），及 DEV 报告对扫描类别的说明；
  - `sk-` ×多：全部是 `task-N` / `ask-320-dark.png` 之类**路径子串**，以及合成测试标记
    `sk-QA-LEAK` / `sk-QA-R2-LEAK`（QA 用例里用来断言「密钥不出现在界面」的假值）；
  - `api_key` ×2 / `app_secret` 等：`{"api_key": "sk-QA-R2-LEAK"}` 这类**注入测试载荷**与其断言输出。

**结论：真实凭据命中 0；64 条宽口径命中全部为哈希/路径/正则定义/合成测试标记误报 → PASS。**

## H · 对抗性检查

### H1 · 门是否空洞

- A2 判别力对照**非空**：`faa1edd..e8e1dba` 同一 pathspec 下 `--stat` 输出 4 文件 / 55 insertions / 21 deletions
  （`src/summit_everything/local/first_use_progress.py`、`web/src/App.tsx`、`web/src/api/generated.ts`、
  `web/src/components/WorkspaceGate.tsx`），diff 正文 175 行 → 门确实能看见产品改动。
- A3 反例对照：不排除测试文件时 `git diff faa1edd e8e1dba --name-only -- web/src | grep -c 'test\.tsx$'` = **2**
  → `exclude` 路径确实在做功（若 exclude 写错，A1 会因测试差异而变非空）。
- **结论：A1 的空是真空，不是空洞。**

### H2 · 归档是否自证循环

- **是自校验，存在真实局限**：源 worktree 已在 C5 删除（`git worktree list` 仅 3 条，其中 1 条是 QA 自己），
  因此 E2 的 395 条只能证明「归档字节 == 同目录 MANIFEST 记录」，**不能**由自身证明
  「归档字节 == 当时被删源目录里的字节」。此限制在报告「本 PASS 明确不覆盖」中列明。
- **「删除前」源比对记录确实存在**：`DELETIONS.md` §6「归档副本与源文件逐字节抽样复核（16/16 一致）」
  与 `2026-10-15-worktree-archive/README.md` §6「复制件与源文件逐字节复核（抽样）」§112–115 行，
  逐条列出「复核文件（相对 `.local`）/字节/SHA-256/结论」并给出源路径
  `/Users/yifengstudio/.codex/worktrees/<wt>/SummitEverything/.local/<rel>`。
- **信任锚（QA 独立补强，实现者未主张）**：C3 的两个被删文件同时**在 Git 对象库中留有原件 blob**。
  QA 实测：
  ```
  git rev-parse e8e1dba:web/e2e/first-use-real.spec.ts     = 9e41cd80b467147a37f69baca72db0166757fb50
  git rev-parse 7a448c3:docs/.../cleanup-orphans/first-use-real.spec.ts = 9e41cd80b467147a37f69baca72db0166757fb50
  → 同一 blob；git diff --name-status 亦报 R100（100% 相似）
  git cat-file blob 9e41cd80… | shasum -a 256 = 0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3
  ```
  `scripts/build_macos_app.sh` 同理（blob `26e6a8bb…`，R100，SHA-256 `1983dbf0…`）。
  即：**这两个文件的「删除前 == 归档后」今天仍可由 Git 独立复证**，不依赖 `.local` 源目录。
  被删分支同理：§C4.1 记录的 6 个 SHA 至今仍是对象库内 commit 且 `--is-ancestor origin/main` = 0。
- **剩余信任锚**：19 个 worktree 的 `.local` 原件（共 1671 文件条目）**只有** §6 的 16 条抽样比对可证；
  其余 1655 条依赖 `DELETIONS.md`/`README.md` 的写入者诚实性 + MANIFEST 与仓库一起被 Git 提交固化。
  这是**可接受但有限**的锚：抽查抽样率 16/395 ≈ 4.1%，非全量。

### H3 · 计数是否靠删测试换绿

```sh
git diff --name-status --no-renames --diff-filter=D e8e1dba 7a448c3
# D  docs/handoff/NEXT-FRONTEND-D-REPAIR1.md
# D  scripts/build_macos_app.sh
# D  tasks/plan.md
# D  tasks/todo.md
# D  web/e2e/first-use-real.spec.ts
git diff --name-status e8e1dba 7a448c3 | grep -E '^R'
# R089 tasks/plan.md → docs/handoff/history/2026-10-11-STAGE-B-C-PLAN.md
# R087 tasks/todo.md → docs/handoff/history/2026-10-11-STAGE-B-C-TODO.md
# R085 docs/handoff/NEXT-FRONTEND-D-REPAIR1.md → docs/handoff/history/2026-10-15-NEXT-FRONTEND-D-REPAIR1.md
# R100 scripts/build_macos_app.sh → docs/quality/reports/evidence/2026-10-15-cleanup-orphans/build_macos_app.sh
# R100 web/e2e/first-use-real.spec.ts → docs/quality/reports/evidence/2026-10-15-cleanup-orphans/first-use-real.spec.ts
```

- 区间内 `web/**/*.test.ts*` 与 `tests/**` 的**删除数 = 0**（除 `web/e2e/first-use-real.spec.ts` 外无可归为测试的删除）。
- 文件数实测（`git ls-tree -r --name-only <rev>`）：

  | 计数 | `e8e1dba` | `7a448c3` | 差 |
  |---|---|---|---|
  | `web/**/*.test.ts(x)` | 26 | 26 | 0 |
  | `web/e2e/*.spec.ts` | 6 | 5 | −1（仅 `first-use-real.spec.ts`） |
  | `tests/**/*.py` | 53 | 53 | 0 |
- 该唯一被删的 spec **未被任何 `testMatch` 命中**（D3 证据），且其内容以 **R100** 逐字节移入归档，
  **不是丢失**。计数侧同证：vitest 222 / e2e 2 / pytest 692 / integration 1，全部**不降**。
- → **不存在「删测试换绿」；PASS。**
