# 2026-10-15 清理：CI 显示名纠正 + 清理后 tip 的真实 CI 绿（实测证据）

本目录保存「C6 · CI 显示名纠正 + 真实 CI 绿」的实测证据。
除注明外，所有命令输出均为 2026-10-15 / 2026-10-16（UTC）在本 worktree
`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`、
分支 `codex/frontend-ux-20261015` 上原样粘贴，未改写、未转述。
本报告只记录**实测**值；未观测到的项明确标为未观测。

## 0 · 改动范围

只改 `.github/workflows/m41-internal-app.yml` 的 workflow 显示名（第 1 行）。
`on:`、`permissions:`、`jobs:` 与全部 steps 未改动（证明见 §2）。

改动前 tip：`32aa10c`（`chore(cleanup): retire merged branches and archived worktrees`），worktree clean。

## 1 · 显示名前后 diff（原文）

命令：`git diff -U0 HEAD^ HEAD -- .github/workflows/m41-internal-app.yml`

```
diff --git a/.github/workflows/m41-internal-app.yml b/.github/workflows/m41-internal-app.yml
index f73f459..1ef142c 100644
--- a/.github/workflows/m41-internal-app.yml
+++ b/.github/workflows/m41-internal-app.yml
@@ -1 +1 @@
-name: M4.1 internal macOS app
+name: offline-arm64 checks (python, web, native, DMG)
```

即 diff 内容**只有**上述 `-` / `+` 两行，`@@ -1 +1 @@` 之外无任何 hunk。
`git diff --numstat HEAD^ HEAD -- .github/workflows/m41-internal-app.yml` 实测：

```
1	1	.github/workflows/m41-internal-app.yml
```

改动后第 1 行实测（`sed -n '1p' .github/workflows/m41-internal-app.yml`）：

```
name: offline-arm64 checks (python, web, native, DMG)
```

## 2 · 触发面未变核对

### 2.1 `sed` 实测输出（改动后）

命令：`sed -n '3,27p' .github/workflows/m41-internal-app.yml`

```
on:
  push:
    branches:
      - codex/m41-internal-app-*
    paths:
      - "src/**"
      - "tests/**"
      - "web/**"
      - "native/**"
      - "scripts/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/m41-internal-app.yml"
  pull_request:
    paths:
      - "src/**"
      - "tests/**"
      - "web/**"
      - "native/**"
      - "scripts/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/m41-internal-app.yml"
  workflow_dispatch:
```

要点核对：

- `push.branches` 仍为 `codex/m41-internal-app-*`（单条，未增减）——本分支名为
  `codex/frontend-ux-20261015`，不匹配该 pattern，因此本次 push **本身**不触发 `push` run（与预期一致）。
- `pull_request` 无 `branches` 限制（只有 `paths`）。
- `push.paths` 与 `pull_request.paths` 两份列表逐字相同，共 8 条：
  `src/**`、`tests/**`、`web/**`、`native/**`、`scripts/**`、`pyproject.toml`、`uv.lock`、
  `.github/workflows/m41-internal-app.yml`。
- `workflow_dispatch:` 仍在。

### 2.2 逐字节证明（比目视更强）

把第 1 行以外的全部内容（第 2 行至文件末）分别从改动前后取出做 SHA-256：

命令：`git show HEAD^:.github/workflows/m41-internal-app.yml | tail -n +2 | shasum -a 256`（HEAD 同理）

```
0e39da273864688b5ea2acefab4342262a098322fbc0e7869d8db7c55a5761e8  -   (HEAD^，第 2 行起)
0e39da273864688b5ea2acefab4342262a098322fbc0e7869d8db7c55a5761e8  -   (HEAD，第 2 行起)
```

`diff <(HEAD^ 去掉第 1 行) <(HEAD 去掉第 1 行)` 退出码 0，输出 `BODY_IDENTICAL=yes`。
**结论：除第 1 行外，workflow 文件逐字节完全未变；触发面未变。**

改动后整个文件的 SHA-256（附记）：

```
0747236ffb54063730a09bb1a30d1bf28c7165af99ab42a52e3a5dfe1c1a5eb5  .github/workflows/m41-internal-app.yml
```

## 3 · push 结果

命令：

```
git push origin codex/frontend-ux-20261015
echo "PUSH_EXIT=$?"
git rev-parse HEAD
git ls-remote --heads origin codex/frontend-ux-20261015
```

实测输出：

```
To github.com:yifeng93/SummitEverything.git
   e76244e..af65f04  codex/frontend-ux-20261015 -> codex/frontend-ux-20261015
PUSH_EXIT=0
af65f049a12caebbcb932a86e610282702e1ffc3
af65f049a12caebbcb932a86e610282702e1ffc3	refs/heads/codex/frontend-ux-20261015
```

- 退出码 `PUSH_EXIT=0`（非 force，正常 fast-forward `e76244e..af65f04`）。
- 本地 HEAD SHA = `af65f049a12caebbcb932a86e610282702e1ffc3`。
- 远端 `refs/heads/codex/frontend-ux-20261015` SHA = 同一值。**两者一致。**
- 推送目标是分支 `codex/frontend-ux-20261015`，**不是** main；未做 merge / rebase / force push。

显示名提交：

```
af65f04 chore(ci): give the offline-arm64 workflow an accurate display name
```

## 4 · 清理后 tip 上的 CI run（实测）

`pull_request.paths` 含 `.github/workflows/m41-internal-app.yml`，所以本次改动确实触发了一次真实 run。

命令：`gh run list --branch codex/frontend-ux-20261015 --limit 6 --json databaseId,headSha,status,conclusion,event,createdAt`

命中的 run（`headSha` == 清理后 tip）：

| 字段 | 实测值 |
| --- | --- |
| `databaseId` | `38831085564` |
| `headSha` | `af65f049a12caebbcb932a86e610282702e1ffc3` |
| `event` | `pull_request` |
| `status` | `completed` |
| `conclusion` | `success` |
| job 名 | `offline-arm64`（job id `116749770298`） |
| `createdAt` | `2026-10-16T00:43:17Z` |
| `updatedAt` | `2026-10-16T00:48:02Z` |
| run 墙钟耗时 | `4m45s`（createdAt → updatedAt） |
| job 耗时 | `4m34s`（`00:43:27Z` → `00:48:01Z`，与 `gh pr checks` 显示的 4m34s 一致） |
| URL | https://github.com/yifeng93/SummitEverything/actions/runs/38831085564 |

### 4.1 四个步骤名与结论（`gh run view <RUN_ID> --json …jobs` 实测）

| 步骤 | status | conclusion |
| --- | --- | --- |
| `Guarded Python checks` | completed | **success** |
| `Web checks and API types` | completed | **success** |
| `Native upload policy tests` | completed | **success** |
| `Build and verify internal App and DMG` | completed | **success** |

同 job 内其余步骤同样全部 `completed / success`：`Set up job`、`Checkout`、`Install Node.js`、
`Install uv`、`Install locked Python and Web dependencies`、`Post Install uv`、`Post Install Node.js`、
`Post Checkout`、`Complete job`。

### 4.2 PR 检查面（`gh pr checks 21` 实测）

```
offline-arm64	pass	4m34s	https://github.com/yifeng93/SummitEverything/actions/runs/38831085564/job/116749770298
```

### 4.3 显示名在 run 上生效的实测（含一处如实说明）

`gh run view 38831085564 --json name,workflowName` 实测：

```
name         = "offline-arm64 checks (python, web, native, DMG)"
workflowName = "M4.1 internal macOS app"
```

即该 run 的显示名（`name`）已是新名，说明新 workflow 文件确实被本次 run 使用。
`workflowName` 与 `gh workflow list` 仍是旧名，因为 `pull_request` run 读取的是 PR 合并提交里的
workflow 文件，而 workflow 注册记录（Actions 侧的 workflow 条目）取自默认分支 main，main 上仍是旧名；
待本分支合入 main 后该条目才会更新。此处如实记录，不推断为已全局生效。

### 4.4 是否重跑

**未发生重跑。** 首跑即 `completed / success`，没有出现 `hdiutil: create failed - Resource busy`，
`gh run view 38831085564 --log-failed` 输出为 0 字节（无失败日志），因此未执行
`gh run rerun --failed`，也没有可记录的首次失败步骤或失败原因原文。

（附注：该 run 的两条 annotation 为既有前端告警
`src/components/ProjectsView.tsx:62:26` 与 `src/App.tsx:124:26`（effect 内同步 setState），
以及一条 macOS arm64 runner 排队容量提示；二者都不是失败，run 结论仍为 success。）

## 5 · 结论声明

- 上述 run `38831085564` 的 `headSha` = `af65f049a12caebbcb932a86e610282702e1ffc3`，
  **就是清理后的 tip**（即 §1 显示名提交后的分支 HEAD，也是本地 HEAD 与远端 ref 的同一 SHA）。
  该 run 的 `success` 对应清理后的 tip，对应显示名改动后的 workflow 文本。
- **CI 运行于 commit `af65f04` 的 tip；其后的 docs-only 提交不改变 CI 相关树。**
  本 README 及后续只改 `docs/**` 的提交，按该 workflow 自身的 `paths` 过滤器（无 `docs/**`
  条目）不会再次触发 run——这是预期行为，不是漏跑。
- 判定规则满足：`status=completed`、`conclusion=success`、`headSha` == 清理后 tip；
  Python / Web / native / DMG 四个步骤全部 success，无需要重跑的抖动失败。

## 6 · 原始证据留存

原始大 JSON / 日志仅留在本机被 Git 忽略的 `.local/`（不提交）：

- `.local/dev/cleanup-c6/run.json`（`gh run view --json` 原件）
- `.local/dev/cleanup-c6/failed.log`（0 字节，无失败步骤日志）
- `.local/dev/cleanup-c6/pr-checks.txt`
- `.local/dev/cleanup-c6/name-diff.patch`、`.local/dev/cleanup-c6/sed-3-27.txt`
