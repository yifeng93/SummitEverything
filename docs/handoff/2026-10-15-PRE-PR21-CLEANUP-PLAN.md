# PR #21 合并前仓库清理 · 分片计划（Sol）

日期：2026-10-15。作者：Sol。
目标：在合并 PR #21 之前，把仓库整理成干净的下一个阶段起点——文档事实收敛、证据归档、孤儿与冗余处置、分支与 worktree 清退（**先归档证据再删**）。本轮**不是**功能开发，**不新增产品能力**。

唯一工作目录：`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`，分支 `codex/frontend-ux-20261015`。
清理提交加在本分支上，与前端 UX 线 A→D 一起合入。**合并动作本身由用户批准，Sol 不 merge、不 push 到 main。**

## 零 · 只读巡检实测基线（2026-10-15）

| 项 | 实测 |
|---|---|
| main HEAD（会话目录） | `e84e9e5a56475a19f68ca1a684366fba7f9fee83`，worktree clean |
| 清理目标分支 tip | `e76244ebd6d4ff897dd019c77f1a86197017a20f` = `origin/codex/frontend-ux-20261015`，worktree clean |
| 受测产品 SHA | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` |
| 待清分支 | `codex/frontend-baseline-20261014`、`codex/internal-candidate-20261014`、`codex/origin-guard-error-20261014`、`codex/settings-ux-20261014` — 四者均为 `origin/main` 祖先 |
| 远端分支 | `origin/main`、`origin/codex/frontend-ux-20261015`、`origin/codex/frontend-baseline-20261014`、`origin/codex/internal-candidate-20261014` |
| worktree | 21 个（main + 20）；全部 clean；目录合计 8.8 GB，`.local` 合计约 1167 MB / 文本证据 4244 文件 |
| 文档 | docs md 263（main 230）、`docs/quality/reports/*.md` 209、handoff md 22、evidence 74 目录 / 2353 文件 |
| 孤儿线索 | `web/e2e/first-use-real.spec.ts` 不被 4 个 playwright config 的任何 `testMatch` 命中；CI workflow `name:` 仍为 `M4.1 internal macOS app` |
| 其他孤儿 | `scripts/build_macos_app.sh` 全仓 0 引用；`tasks/plan.md` + `tasks/todo.md` 仍是 Stage B/C「当前计划」 |
| 链接 | 838 条相对链接，失效 8 条：7 条为历史报告正文里的 `/Users/…/.codex/worktrees/…` 绝对路径快照，1 条为 `docs/quality/reports/evidence/2026-10-15-frontend-b-dev/README.md` 相对路径笔误 |

### 冻结基线（本轮开始前实测，全部 exit 0）

- pytest **692 passed**
- vitest **222 passed / 26 files / 0 todo**
- `test:e2e` **2 passed**；`test:e2e:integration` **1 passed**
- typecheck 0 / lint 0（2 条既存 warning）/ build 0
- ruff check 0 / ruff format 0 / mypy 0（47 files）/ uv lock 0 / uv build 0
- `npm --prefix web run api:types` 后 `git diff --exit-code -- web/src/api/generated.ts` → 0
- `fingerprint_web_dist('web/dist')` = `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`

## 一 · 用户已确认的决策（不得重开）

| 项 | 决定 |
|---|---|
| worktree 保留 | **只保留 main + `frontend-ux-20261015`**；其余 19 个先归档再删 |
| 候选二进制 | **随 worktree 一起删**，只留 SHA-256 + `build-info.json`（`.app`/`.dmg` 不入 Git、不另存） |
| 证据归档位置 | 沿用 `docs/quality/reports/evidence/<轮次>/` |
| 归档粒度 | 全量 SHA-256 清单入库；只复制被引用 / 人类可读的小原件 |
| 孤儿处置 | 先归档原件（既有副本 SHA 不一致时归档原件本身）再删；每项给出「无引用」证据 |
| CI 显示名 | 只改 `name:`，触发条件与全部步骤逐字不动 |
| 分支清退 | 本地 4 个 + **远端 2 个**（`git push origin --delete`，不是 push 到 main） |
| 文档策略 | 只纠正文事实 + 补索引 + 修 1 条相对路径笔误；**历史报告正文逐字保留**，另建「已删路径 → 归档索引」对照表 |
| `/tmp` | 只清 `/tmp/summit-ws` 与 0 字节空目录；有内容的一律保留 |

## 二 · 分片

总规则（对每片生效）：

- 每片一个 `chore(cleanup):` 小提交；每片结束回报 `git status --porcelain`、`git log --oneline -1`、改动清单、**每条验证命令的真实退出码**。
- 禁止：push 到 main、merge、`push --force`、切分支、改冻结面、删测试、降低任何验收门。
- 碰到以下任一项立刻停下上报 Sol：需改冻结面；无法 100% 证明无引用；任何计数下降；发现被 tracked 文档引用但未归档的原件。
- 回滚：每片记录 pre-slice SHA；文档/代码类 `git revert <sha>`；删除类不可逆，故删除前一律先落盘证据。

### C0 · 计划落盘

- 目标：本文件成为后续分片的对照基准。
- 允许面：`docs/handoff/**`。禁止面：其余全部。
- 验证：`git diff --exit-code -- src web/src pyproject.toml uv.lock native` → 0。

### C1 · 文档事实收敛

目标：清除仍在宣称过期结论的「当前页」，补索引，修 1 条相对路径笔误。**不删任何历史报告，不改历史报告正文。**

1. `docs/implementation/PROGRESS.md`「远端离线 CI」行仍只写 M4.2 run 38550700081，未记 PR #21 的三次 run（`38756944004` 失败＝仅 `hdiutil: create failed - Resource busy` runner 抖动；`38757225760` success 4m42s；`38758095886` success 4m0s）→ 纠正文。
2. `README.md`「内部候选与证据」行仍只列到设置 UX 与前端基线切片 1–2，未指 D → 纠正文。
3. `README.md` / `PROGRESS.md` 中「前端基线切片 1–2」类表述与「D 已 PASS」并存的段落 → 统一为一条当前事实。
4. 补 `docs/quality/reports/README.md` 索引：对每个 `docs/quality/reports/*.md`（不含 `README.md` 自身），若其文件名未作为链接目标出现在 README.md 中，则补一行索引。新增行**必须使用该报告自身的 H1 标题原文**作为标签，不得自行概括或推断结论；放在新增的「历史报告完整索引」小节内，按文件名排序。
5. 修笔误：`docs/quality/reports/evidence/2026-10-15-frontend-b-dev/README.md` 中 `../2026-10-15-FRONTEND-B-DEV-REPAIR1.md` → `../../2026-10-15-FRONTEND-B-DEV-REPAIR1.md`。
6. **不做文件移动**：把「被取代的当前页」拟移动清单（候选：`docs/handoff/FRONTEND-EXECUTION-PLAN.md`、`docs/handoff/NEXT-AFTER-FRONTEND-D.md`）连同判定理由交回 Sol；由 Sol 决定是否移入 `docs/handoff/history/`，需要时由 Sol 问用户。

- 允许面：`README.md`、`docs/implementation/PROGRESS.md`、`docs/quality/reports/README.md`、`docs/quality/reports/evidence/2026-10-15-frontend-b-dev/README.md`。
- 禁止面：`src/**`、`web/**`、`native/**`、`scripts/**`、`pyproject.toml`、`uv.lock`、`.github/**`、任何历史报告正文。
- 验证与期望：
  - `git diff --exit-code -- src web/src pyproject.toml uv.lock native` → 0
  - 相对链接失效数 **8 → 7**（余 7 条为历史绝对路径快照，由 C2 对照表解释）
  - `git ls-files -- 'docs/quality/reports/**' | grep -c '\.md$'` **≥ 209**（只增不减）
- 证据落点：`docs/quality/reports/evidence/2026-10-15-cleanup-docs/`（改前/改后摘要与链接检查输出）。
- 回滚：`git revert`。
- 停下问用户：任何涉及历史报告正文的改写。

### C2 · 证据归档与索引（**必须先于 C5**）

目标：让 19 个待删 worktree 的原件在删除前可追溯、可校验。

1. 记录删除前身份：`git worktree list --porcelain`、每个 worktree 的 `git rev-parse HEAD`、`git status --porcelain`（必须为空）。
2. 对 19 个 worktree 的 `.local`（排除 `.venv/`、`*.app`、`*.dmg`）生成 `MANIFEST.sha256`：每行 `sha256  size  relpath`；`*.app`/`*.dmg` 只记实际 SHA-256，不复制。
3. 复制「被引用 / 人类可读」小原件（`*REPORT*.md`、`*README*.md`、`*observations*.md`、`*manifest*.json`、`*command-results*.json`、`*COMMANDS*.md`、关键 `*.log`，且 ≤512 KB）到 `docs/quality/reports/evidence/2026-10-15-worktree-archive/<worktree>/`，逐个 SHA-256 校验与源文件一致。
4. 写 `docs/quality/reports/evidence/2026-10-15-worktree-archive/README.md`：每个 worktree 一行（名称 / HEAD SHA / 用途 / 归档目录 / MANIFEST 路径 / 文件数与总字节）。
5. 写 `docs/quality/reports/evidence/2026-10-15-worktree-archive/CANDIDATE-IDENTITY.md`：`e8e1dba`（DMG `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b`）、`876008e`、`96fdf4d` 的 `build-info.json` 全文 + `.app`/`.dmg` SHA-256，并**明确声明二进制随本轮删除、不再可取**。
6. 写 `docs/quality/reports/DELETED-PATHS-INDEX.md`：把 tracked 文档里指向已删 worktree 的绝对路径快照逐条映射到归档索引；**历史报告正文一字不改**。

- 允许面：`docs/quality/reports/evidence/**`、`docs/quality/reports/DELETED-PATHS-INDEX.md`。
- 禁止面：`src/**`、`web/**`、`native/**`、`scripts/**`、`.github/**`、历史报告正文、`pyproject.toml`、`uv.lock`。
- 验证与期望：清单行数 == 源文件数（逐 worktree）；被复制文件 SHA-256 全量比对 0 mismatch；`git diff --exit-code -- src web/src pyproject.toml uv.lock native` → 0。
- 回滚：`git revert`（此时 worktree 尚未删除，无损）。
- 停下问用户：出现 >512 KB 但被 tracked 文档直接引用的原件；`build-info.json` 的 SHA 与文档记载不一致。

### C3 · 孤儿与冗余处置

| 项 | 判定 | 动作 |
|---|---|---|
| `web/e2e/first-use-real.spec.ts`（`0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3`） | 4 个 config 的 `testMatch` 全部未命中；与 `evidence/2026-10-15-frontend-a-repair1-qa/harness/first-use-real.spec.ts`（`539bfb7e…`）及 dev harness 副本（`297e580a…`）SHA 均不同 | 先把原件复制进 `docs/quality/reports/evidence/2026-10-15-cleanup-orphans/` 并记 SHA → 再删 |
| `scripts/build_macos_app.sh` | 全仓 0 引用（仅自身 usage 提及）；已被 `release-macos.sh` 取代 | 归档原件 → 删 |
| `tasks/plan.md`、`tasks/todo.md` | 仍是 Stage B/C「当前计划」，SHA 停在 `576895f`；无当前入口引用 | **移入** `docs/handoff/history/2026-10-11-STAGE-B-C-PLAN.md` / `-TODO.md`，清空 `tasks/` |
| npm scripts / playwright configs | 逐个反查引用 | 全部有引用 → 不动 |
| `/tmp/summit-ws` + 0 字节 `/tmp/summit-*` | 主机级过期临时目录 | 删；有内容的（`summit-cleanup-api-types-before`、`summit-deepseek-stage-b-replay`、`summit-m41-ui.RcoGly` 及散落文件）保留 |

- 允许面：`web/e2e/**`、`scripts/**`、`tasks/**`、`docs/handoff/history/**`、`docs/quality/reports/evidence/**`、`/tmp` 白名单。
- 禁止面：`web/src/**`、`src/**`、`native/**`、`.github/**`、`pyproject.toml`、`uv.lock`、任何仍被引用的资产。
- 验证与期望：vitest 222 / 0 todo；`test:e2e` 2；`test:e2e:integration` 1；build 0；冻结面 pathspec → 0。
- 删除清单落点：`docs/quality/reports/evidence/2026-10-15-worktree-archive/DELETIONS.md`（路径 / 判定理由 / 无引用证据 / 归档索引 / 验证方式）。
- 回滚：`git revert`；`/tmp` 删除不可逆（已先记清单）。

### C4 · 分支清退

先取证（写入 `DELETIONS.md`）：每个分支的 `git rev-parse <b>`、`git merge-base --is-ancestor <b> origin/main`（期望 exit 0）、`git rev-list -1 <b>`。

```sh
git branch -d codex/frontend-baseline-20261014 codex/internal-candidate-20261014 \
               codex/origin-guard-error-20261014 codex/settings-ux-20261014
git push origin --delete codex/frontend-baseline-20261014 codex/internal-candidate-20261014
```

- 允许面：Git ref 面 + `docs/quality/reports/evidence/**`。
- 禁止面：不删 `main`、不删 `codex/frontend-ux-20261015`、不 force、不改产品树。
- 验证与期望：`git branch -vv` 只剩 `main` + PR 分支；`git branch -r` 只剩 `origin/main` + `origin/codex/frontend-ux-20261015`。
- 回滚：本地 `git branch <name> <recorded-sha>`；远端需重新 push（已记 SHA）。
- 停下问用户：任一分支 `-d` 失败（即并非完全并入）。

### C5 · worktree 清退

前置门（缺一不删）：C2 归档已由 Sol 复核通过；`DELETIONS.md` 已含每个 worktree 的原件索引。

```sh
git worktree list --porcelain   # 存证
# 逐个确认 git -C <path> status --porcelain 为空
git worktree remove --force <path>
git worktree prune
```

- 允许面：`/Users/yifengstudio/.codex/worktrees/**`（19 个）+ `docs/quality/reports/evidence/**`。
- 禁止面：不删 main 仓库目录、不删 `frontend-ux-20261015`、不删主仓库 `.local/internal-builds/{3f6eaa4,internal-f40bc39,m42-419bb86,main-bce8843}`。
- 验证与期望：`git worktree list | wc -l` == 2；无 `prunable`；工作区目录从 8.8 GB 降到约 0.7 GB；主仓 `git status --porcelain` 为空。
- 回滚：`git worktree add <path> <recorded-sha>` 可重建空 worktree；`.local` 原件不可逆，已有哈希与索引。
- 停下问用户：删除后若发现被 tracked 文档引用却未进归档索引的原件。

### C6 · CI 显示名 + 最终门

- 只改 `.github/workflows/m41-internal-app.yml` 第 1 行 `name:` → `offline-arm64 checks (python, web, native, DMG)`；`on:` 与全部 steps 逐字不动。
- 该文件在 `pull_request.paths` 过滤器内，因此**放在最后一个 commit**，正好触发一次覆盖清理后 tip 的真实 run。
- 验证与期望：`git diff -U0 HEAD~1 -- .github/workflows/m41-internal-app.yml` 只有 1 行 `-/+ name:`；`gh pr checks 21` exit 0；`gh run view <id> --json conclusion,headSha` = success + headSha == 清理 tip。
- 遇 `hdiutil: create failed - Resource busy`：**先重跑再判断**，不判产品失败。

### C7 · 起点交接 + 清理报告 + 最终门

- `docs/handoff/NEXT-STAGE-*.md`：干净基线、下一个阶段候选方向、仍未关闭项（D-3 OpenAPI 401/404/503、D-5、pageZoom、真实门）。
- `docs/quality/reports/2026-10-15-PRE-PR21-CLEANUP-DEV.md`：逐项 路径 / 判定 / 证据 / 动作 / 验证命令与退出码。
- `docs/quality/reports/2026-10-15-PRE-PR21-CLEANUP-SOL-GATE.md`：Sol 最终门判断。
- 允许面：`docs/**/*.md`。禁止面：其余全部。

## 三 · 硬验收不变量（每条都要证据，缺一不通过）

1. **产品面逐字节冻结**：

```sh
git diff e8e1dba <cleanup-tip> -- \
  src \
  'web/src' \
  ':(exclude)web/src/*.test.ts' ':(exclude)web/src/*.test.tsx' \
  ':(exclude)web/src/**/*.test.ts' ':(exclude)web/src/**/*.test.tsx' \
  web/package.json web/package-lock.json pyproject.toml uv.lock native
# 期望：无输出，exit 0
```

> `web/src` 单个 pathspec 不够：`**/` 在 git 里要求至少一层目录，会漏掉 `web/src/App.firstUseProgress.test.tsx` 这类顶层测试文件。两条 exclude 缺一不可（已用 `faa1edd..e8e1dba` 对照区间验证判别力）。

2. **前端指纹不变**：`784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`。
3. **自动检查不低于基线**：见「零 · 冻结基线」全部条目。任何计数下降先停下问用户。
4. **链接与索引自洽**：新增 / 修改文档的相对链接可解析；报告索引与实际文件一一对应。
5. **删除可追溯**：每个被删的 tracked 文件 / 分支 / worktree 都能在清理报告里找到判定理由 + 归档索引 + 验证方式。
6. **CI 绿**：PR #21 的 `offline-arm64` 在清理后的 tip 上 success。

## 四 · 边界（对所有后续角色）

- 不触碰真实 provider / OAuth / Feishu / Keychain、用户真实资料、真实 App Support、已安装 App、付费、production。
- 不并入 D-3；不尝试 pageZoom；不本地重跑 swift。
- 不 push 到 main、不 merge；合并动作由用户在 CI 绿且 Sol 给出判断后执行。
- 失败不得靠删测试或降低验收门收口。
- 候选构建流程与安全约束（LaunchServices `open -n --env`、canonical TMPDIR child profile、`SUMMIT_OFFLINE_GUARD_ACTIVE=1`、端口 18793 预检、token 不落盘、不覆盖旧候选）见 [历史交接](history/2026-10-15-NEXT-FRONTEND-D-REPAIR1.md)。
- `src/summit_everything/domain/content.py` 仍是内容指纹与检索资格的唯一基准。
