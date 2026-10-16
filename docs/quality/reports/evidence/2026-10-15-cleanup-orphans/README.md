# 2026-10-15 清理：孤儿与冗余归档（原始字节 + 实测证据）

本目录保存 2026-10-15「PR #21 合并前仓库清理」C3 中被删除的孤儿**原件字节**。归档原因见 §2：
仓库内既有的同名副本与原件内容不同，因此必须归档原件本身，不能用既有副本代替。
本文件所有命令输出均为 2026-10-15 在本 worktree `codex/frontend-ux-20261015` 实测粘贴，未改写。

## 0 · 归档清单与校验值

命令：`shasum -a 256 first-use-real.spec.ts build_macos_app.sh verify_tree_digest.py > MANIFEST.sha256`

```
0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3  first-use-real.spec.ts
1983dbf08374f063bc9334da46b9a8603487388eea7fc3a3c8716663f5312c2a  build_macos_app.sh
59788e9044587e516e8cf0583ceb1f23cbce64432d62c4ec56da2a1bc5b820fd  verify_tree_digest.py
```

其中 `first-use-real.spec.ts` = `0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3`，
与清理计划 C3 表格记载的待删 SHA 一致；归档后逐字节相同（MANIFEST 即归档目录内实测值）。

## 1 · 4 个 playwright config 的 testMatch 实测

命令：`grep -n testMatch web/playwright*.ts`

```
web/playwright.config.ts:5:  testMatch: ['viewport.spec.ts', 'first-use.spec.ts'],
web/playwright.frontend-c-view.config.ts:11:  testMatch: ['frontend-c-view.spec.ts'],
web/playwright.frontend-c.config.ts:11:  testMatch: ['frontend-c-flow.spec.ts'],
web/playwright.integration.config.ts:11:  testMatch: ['approval-today.spec.ts'],
```

四个 config 的 testMatch 命中集合为 `viewport.spec.ts`、`first-use.spec.ts`（默认）、
`frontend-c-view.spec.ts`、`frontend-c-flow.spec.ts`、`approval-today.spec.ts`（integration）；
无一条命中 `first-use-real.spec.ts`。

## 2 · 三份 `first-use-real.spec.ts` 的 SHA-256 实测

命令：`shasum -a 256 <仓库原件> <frontend-a repair1 QA harness 副本> <.local dev harness 副本>`

```
0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3  web/e2e/first-use-real.spec.ts
539bfb7ec6f02f9af67a957cb891c7cbd46257103650ecf49779d6f4114f651c  docs/quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/harness/first-use-real.spec.ts
297e580ab395e7071da766ea3385f1bd0e2f066d58c9b34f31cb06e4d162a26d  .local/dev/frontend-a/repair1/integration-harness/first-use-real.spec.ts
```

三者互不相同：

- 仓库原件 `web/e2e/first-use-real.spec.ts` = `0592629563c9e7f8181e92b8707f058fa42ee5399cd0ad0dc75920618a656fc3`（本目录归档件）
- `docs/quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/harness/first-use-real.spec.ts` = `539bfb7ec6f02f9af67a957cb891c7cbd46257103650ecf49779d6f4114f651c`
- `.local/dev/frontend-a/repair1/integration-harness/first-use-real.spec.ts` = `297e580ab395e7071da766ea3385f1bd0e2f066d58c9b34f31cb06e4d162a26d`

因此既有两份 harness 副本都不能代表被删原件，归档原件本身是唯一可校验来源。

## 3 · `scripts/build_macos_app.sh` 无引用证据

命令：`git grep -n "build_macos_app.sh" -- .`（完整输出，无截断）

```
docs/handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md:21:| 其他孤儿 | `scripts/build_macos_app.sh` 全仓 0 引用；`tasks/plan.md` + `tasks/todo.md` 仍是 Stage B/C「当前计划」 |
docs/handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md:106:| `scripts/build_macos_app.sh` | 全仓 0 引用（仅自身 usage 提及）；已被 `release-macos.sh` 取代 | 归档原件 → 删 |
scripts/build_macos_app.sh:5:    echo "Usage: scripts/build_macos_app.sh OUTPUT.app [--dmg OUTPUT.dmg]" >&2
```

除该脚本自身第 5 行的 usage 提示外，唯一命中来自清理计划文档
`docs/handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md`（第 21、106 行的清理清单本身），
没有任何可执行文件、CI workflow 或 npm script 调用它。

命令：`grep -n build_macos_app scripts/release-macos.sh`

```
12:exec uv run --locked python scripts/build_macos_app.py "$1" --dmg "$2"
```

发布脚本 `scripts/release-macos.sh` 第 12 行直接调用 `scripts/build_macos_app.py`（不是 `.sh`），
即 `.sh` 已被 `.py` 取代，删除不影响任何发布路径。

## 4 · 覆盖结论

命令：`npm --prefix web run test:e2e -- --list`

```

> web@0.0.0 test:e2e
> playwright test --list

Listing tests:
  first-use.spec.ts:15:1 › first use stays in one app-owned flow and resumes to a requested step
  viewport.spec.ts:35:1 › offline viewport and theme baseline for today, approvals, tools and settings
Total: 2 tests in 2 files
```

命令：`npm --prefix web run test:e2e:integration -- --list`

```

> web@0.0.0 test:e2e:integration
> playwright test --config playwright.integration.config.ts --list

Listing tests:
  approval-today.spec.ts:6:1 › FastAPI Fake flow keeps intake, knowledge confirmation, indexing and actions separate
Total: 1 test in 1 file
```

结论：`web/e2e/first-use-real.spec.ts` 既不在 `npm run test:e2e`（收集 2 tests / 2 files）的覆盖内，
也不在 `npm run test:e2e:integration`（收集 1 test / 1 file）的覆盖内；删除它不减少任何门的测试数，
也不会让任何既有门的计数下降。删除后两个命令的实测计数见本轮 C3 提交报告。

## 5 · `/tmp` 清理记录（白名单：仅 `/tmp/summit-ws` 与 0 字节空目录）

清理**前** `ls -d /tmp/summit-*`：

```
/tmp/summit-cleanup-api-types-before
/tmp/summit-deepseek-stage-b-replay
/tmp/summit-m1-fix-replay-nwyhoS
/tmp/summit-m2-assessment-tmdJrk
/tmp/summit-m2-fault-workspace
/tmp/summit-m2-final-workspace
/tmp/summit-m22-final-ui-workspace
/tmp/summit-m22-ui-workspace
/tmp/summit-m23-browser-workspace
/tmp/summit-m23-final-replay-workspace
/tmp/summit-m41-ui.RcoGly
/tmp/summit-pull.log
/tmp/summit-simulated-feishu-remote
/tmp/summit-stage-b-browser-workspace
/tmp/summit-stage-b-sol-mypy-cache
/tmp/summit-ws
```

清理前 `find /tmp -maxdepth 1 -type d -name 'summit-*' -empty`：

```
(无输出：当前无空目录)
```

被删的 `/tmp/summit-ws` 清理前完整内容（`find /tmp/summit-ws -mindepth 1 -exec ls -ld {} \;`）：

```
-rw-------@ 1 yifengstudio  wheel  86 Oct 15 22:42 /tmp/summit-ws/conventions.md
drwxr-xr-x@ 5 yifengstudio  wheel  160 Oct 15 22:42 /tmp/summit-ws/.summit-everything
drwxr-xr-x@ 3 yifengstudio  wheel  96 Oct 15 22:42 /tmp/summit-ws/.summit-everything/transactions
-rw-------@ 1 yifengstudio  wheel  298 Oct 15 22:42 /tmp/summit-ws/.summit-everything/transactions/workspace-create-78bb32db82384c7fb7e35d363538a5e662be1b7d4ea5f707ab288b205c28f73f.json
-rw-------@ 1 yifengstudio  wheel  179 Oct 15 22:42 /tmp/summit-ws/.summit-everything/manifest.json
-rw-r--r--@ 1 yifengstudio  wheel  0 Oct 15 22:42 /tmp/summit-ws/.summit-everything/workspace.lock
```

其内容为一次性测试工作库（模拟 workspace 契约，非真实业务材料），文件 SHA-256：

```
88e356eba73139c01ed51c5eb4bea96efa0d77ac97a24afe3796f3e012c4f873  /tmp/summit-ws/conventions.md
2c150c3f7d4c8ca37a8fec690e49d977b4a68484609791a5582f3dc5241df8ee  /tmp/summit-ws/.summit-everything/transactions/workspace-create-78bb32db82384c7fb7e35d363538a5e662be1b7d4ea5f707ab288b205c28f73f.json
f30c59406a3d75017f8d4bae5b1195861fd41b652fb491422189d889591b725f  /tmp/summit-ws/.summit-everything/manifest.json
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  /tmp/summit-ws/.summit-everything/workspace.lock
```

其中 `conventions.md` 内容为通用占位（`# SummitEverything workspace` / `See the workspace contract for page and approval rules.`），
仓库内已有可复现副本 `docs/quality/reports/evidence/2026-10-13-m3-package-2-c19-dsh-qa-be4e72f/ui-workspace/conventions.md`。

清理命令：`rm -rf /tmp/summit-ws` + `find /tmp -maxdepth 1 -type d -name 'summit-*' -empty -exec rmdir {} +`

清理**后** `ls -d /tmp/summit-*`：

```
/tmp/summit-cleanup-api-types-before
/tmp/summit-deepseek-stage-b-replay
/tmp/summit-m1-fix-replay-nwyhoS
/tmp/summit-m2-assessment-tmdJrk
/tmp/summit-m2-fault-workspace
/tmp/summit-m2-final-workspace
/tmp/summit-m22-final-ui-workspace
/tmp/summit-m22-ui-workspace
/tmp/summit-m23-browser-workspace
/tmp/summit-m23-final-replay-workspace
/tmp/summit-m41-ui.RcoGly
/tmp/summit-pull.log
/tmp/summit-simulated-feishu-remote
/tmp/summit-stage-b-browser-workspace
/tmp/summit-stage-b-sol-mypy-cache
```

清理后 `find /tmp -maxdepth 1 -type d -name 'summit-*' -empty`：

```
(无输出：无剩余空目录)
```

`/tmp` 下的普通文件（如 `/tmp/summit-pull.log`）与有内容的目录
（`summit-cleanup-api-types-before`、`summit-deepseek-stage-b-replay`、`summit-m41-ui.RcoGly` 等）全部保留。

## 6 · 本目录之外的 C3 动作（可追溯）

- 删除：`web/e2e/first-use-real.spec.ts`、`scripts/build_macos_app.sh`（原件已归档于本目录，SHA 见 §0）。
- 移动（非删除）：`tasks/plan.md` → `docs/handoff/history/2026-10-11-STAGE-B-C-PLAN.md`；
  `tasks/todo.md` → `docs/handoff/history/2026-10-11-STAGE-B-C-TODO.md`（固定源码停在 `576895f`，顶部加历史归档声明）。
- 验证：vitest、`test:e2e`、`test:e2e:integration`、build 与冻结面 pathspec，计数见本轮 C3 提交报告。
