# 2026-10-15 删除可追溯主表（C2 登记 · C4/C5 追加实测）

日期：2026-10-15。分片：C2 · 证据归档与索引。
本文件是「删除前身份与判定」的主表；C4（分支清退）与 C5（worktree 清退）会在对应小节追加**实测输出**。
本轮 C2 **不删任何 worktree、不删任何分支**，只登记删除前身份与判定依据。
被删 worktree 的原件归档见 [README.md](README.md) 与各 `MANIFEST.sha256`。

## 0 · 用户决策（判定总依据）

用户 2026-10-15 选定：**只保留 `main` + `codex/frontend-ux-20261015`**；其余 worktree 与分支先归档
证据再清退。候选 `.app`/`.dmg` 二进制**随 worktree 一起删**，只留 SHA-256 + `build-info.json`。
计划原文见 `docs/handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md`（§一 决策表、§二 分片）。

---

## 1 · 19 个待删 worktree（删除前身份）

以下 `HEAD` 与 `status` 为 2026-10-15 C2 实测；`git status --porcelain` **19 个全部为空**
（输出为空串，即 clean），符合清理前提。「归档索引」指向本目录内该 worktree 的全量 SHA-256 清单。

| worktree | 绝对路径 | `git rev-parse HEAD` | `git status --porcelain` | 用途 | 归档索引 | 判定理由 |
|---|---|---|---|---|---|---|
| `frontend-a-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything` | `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad` | 空 | 前端 A 初次独立 QA checkout | [MANIFEST](frontend-a-qa-initial/MANIFEST.sha256) | 一次性 QA checkout，工作已并入 `9d6e097`；用户选定只保留 main + `frontend-ux-20261015` |
| `frontend-a-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-repair1/SummitEverything` | `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` | 空 | 前端 A 修复轮 1 QA checkout | [MANIFEST](frontend-a-qa-repair1/MANIFEST.sha256) | 同上，修复已并入主线 |
| `frontend-b-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-b-qa-initial/SummitEverything` | `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` | 空 | 前端 B 初次独立 QA checkout | [MANIFEST](frontend-b-qa-initial/MANIFEST.sha256) | 同上 |
| `frontend-b-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-b-qa-repair1/SummitEverything` | `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c` | 空 | 前端 B 修复轮 1 QA checkout | [MANIFEST](frontend-b-qa-repair1/MANIFEST.sha256) | 同上 |
| `frontend-c-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-c-qa-initial/SummitEverything` | `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` | 空 | 前端 C 独立 QA checkout | [MANIFEST](frontend-c-qa-initial/MANIFEST.sha256) | 同上 |
| `frontend-d-build` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build/SummitEverything` | `944634c0795930426b41110052e3ba1eaeebaf52` | 空 | 前端 D 初次候选构建 worktree | [MANIFEST](frontend-d-build/MANIFEST.sha256) | 构建已由 repair2/repair3 取代；`.local` 已不存在，MANIFEST 为空属正常 |
| `frontend-d-build-repair2` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair2/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | 前端 D 修复轮 2 候选构建 worktree | [MANIFEST](frontend-d-build-repair2/MANIFEST.sha256) | 中间构建，二进制随删（身份见 [CANDIDATE-IDENTITY.md](CANDIDATE-IDENTITY.md) §3） |
| `frontend-d-build-repair3` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair3/SummitEverything` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 空 | 前端 D **最终**候选构建 worktree | [MANIFEST](frontend-d-build-repair3/MANIFEST.sha256) | 受测最终构建，二进制随删（身份见 [CANDIDATE-IDENTITY.md](CANDIDATE-IDENTITY.md) §1） |
| `frontend-d-final` | `/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | 前端 D 初次候选收尾 / 发布构建 worktree | [MANIFEST](frontend-d-final/MANIFEST.sha256) | 已被 repair3 取代，二进制随删（身份见 [CANDIDATE-IDENTITY.md](CANDIDATE-IDENTITY.md) §2） |
| `frontend-d-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | 前端 D 初次独立 QA checkout | [MANIFEST](frontend-d-qa-initial/MANIFEST.sha256) | 一次性 QA checkout |
| `frontend-d-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1/SummitEverything` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 空 | 前端 D 修复轮 1 QA checkout | [MANIFEST](frontend-d-qa-repair1/MANIFEST.sha256) | 同上 |
| `frontend-d-qa-repair1-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1-parent/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | 前端 D 修复轮 1 QA 父端 harness checkout | [MANIFEST](frontend-d-qa-repair1-parent/MANIFEST.sha256) | 仅承载父端构建 / 后端侧日志，证据已归档 |
| `frontend-d-qa-repair2` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | 前端 D 修复轮 2 QA checkout | [MANIFEST](frontend-d-qa-repair2/MANIFEST.sha256) | 同上 |
| `frontend-d-qa-repair2-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2-parent/SummitEverything` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 空 | 前端 D 修复轮 2 QA 父端 harness checkout | [MANIFEST](frontend-d-qa-repair2-parent/MANIFEST.sha256) | 同上 |
| `frontend-d-qa-repair3` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3/SummitEverything` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 空 | 前端 D **最终** QA checkout | [MANIFEST](frontend-d-qa-repair3/MANIFEST.sha256) | 最终 QA 已完成并留下结论，checkout 可清退 |
| `frontend-d-qa-repair3-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3-parent/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | 前端 D 最终 QA 父端 gate harness checkout | [MANIFEST](frontend-d-qa-repair3-parent/MANIFEST.sha256) | 同上 |
| `m41-internal-app` | `/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything` | `52d0f3419bf10ad9cb719efed0580256bd059022` | 空 | M4.1 构建 worktree（5 个 `.app` bundle） | [MANIFEST](m41-internal-app/MANIFEST.sha256) | 中间构建，二进制随删（身份见 [CANDIDATE-IDENTITY.md](CANDIDATE-IDENTITY.md) §4） |
| `m41-qa-b9321d6` | `/Users/yifengstudio/.codex/worktrees/m41-qa-b9321d6/SummitEverything` | `acd3ef95e199f6af2714df10f548779b6db3aed8` | 空 | M4.1 QA checkout | [MANIFEST](m41-qa-b9321d6/MANIFEST.sha256) | 一次性 QA checkout |
| `m41-qa-repair1-3f6eaa4` | `/Users/yifengstudio/.codex/worktrees/m41-qa-repair1-3f6eaa4/SummitEverything` | `2437f9c771ff7da3aaf2b39a387903654fde5b9d` | 空 | M4.1 修复轮 1 QA checkout | [MANIFEST](m41-qa-repair1-3f6eaa4/MANIFEST.sha256) | 同上 |

`frontend-ux-20261015`（本 worktree）与 `main`（`/Users/yifengstudio/Documents/GitHub/SummitEverything`）
**不在删除集**；`m3-package-1-qa` 等其他目录名不在本轮 19 个之中（更早已移除，见
[DELETED-PATHS-INDEX.md](../../DELETED-PATHS-INDEX.md)）。

## 2 · 6 个待删分支（4 本地 + 2 远端）

实测命令与退出码（2026-10-15，在本 worktree 执行）：

```sh
git rev-parse <b>
git merge-base --is-ancestor <b> origin/main   # 期望 exit 0
git rev-list -1 <b>
```

| 分支 | 类型 | `git rev-parse <b>` | `--is-ancestor origin/main` 退出码 | `git rev-list -1 <b>` |
|---|---|---|---|---|
| `codex/frontend-baseline-20261014` | 本地 | `38986493bfbac24e216663922d6a793fda574cbb` | **0** | `38986493bfbac24e216663922d6a793fda574cbb` |
| `codex/internal-candidate-20261014` | 本地 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **0** | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` |
| `codex/origin-guard-error-20261014` | 本地 | `258f7d820d68673183e62a5b998879ad0d9ca59d` | **0** | `258f7d820d68673183e62a5b998879ad0d9ca59d` |
| `codex/settings-ux-20261014` | 本地 | `6f9191d8b8b62f3957ac5eacb207d34202e69abf` | **0** | `6f9191d8b8b62f3957ac5eacb207d34202e69abf` |
| `origin/codex/frontend-baseline-20261014` | 远端 | `38986493bfbac24e216663922d6a793fda574cbb` | **0** | `38986493bfbac24e216663922d6a793fda574cbb` |
| `origin/codex/internal-candidate-20261014` | 远端 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **0** | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` |

六个分支的 `--is-ancestor origin/main` 退出码**全部为 0**，即在 `origin/main` 历史中，
删除不丢失任何未合并提交。

**C4 将执行的命令**（本轮 C2 不执行）：

```sh
git branch -d codex/frontend-baseline-20261014
git branch -d codex/internal-candidate-20261014
git branch -d codex/origin-guard-error-20261014
git branch -d codex/settings-ux-20261014
git push origin --delete codex/frontend-baseline-20261014
git push origin --delete codex/internal-candidate-20261014
```

说明：`git push origin --delete` **只删远端分支，不 push 到 main**，与用户决策一致。

## 3 · 2 个被删 tracked 文件（C3 已完成，此处登记）

| 被删路径 | 判定理由 | 无引用证据 | 归档索引 |
|---|---|---|---|
| `web/e2e/first-use-real.spec.ts` | 不被 4 个 playwright config 的任何 `testMatch` 命中，删除不减少任何门的测试数 | 4 个 config 的 `testMatch` 实测命中共 5 个 spec，无一为该文件；两份既有 harness 副本 SHA 与原件均不同（`05926295…` vs `539bfb7e…` / `297e580a…`） | [../2026-10-15-cleanup-orphans/](../2026-10-15-cleanup-orphans/)（§0–§2） |
| `scripts/build_macos_app.sh` | 全仓 0 引用（仅自身 usage 提及），已被 `scripts/build_macos_app.py` / `release-macos.sh` 取代 | `git grep -n "build_macos_app.sh"` 除自身 usage 与清理计划清单外无命中；`release-macos.sh` 第 12 行调用的是 `.py` | [../2026-10-15-cleanup-orphans/](../2026-10-15-cleanup-orphans/)（§0、§3） |

两者原件字节已归档于 `docs/quality/reports/evidence/2026-10-15-cleanup-orphans/`，SHA 见该目录
`MANIFEST.sha256` / `README.md` §0。

## 4 · 2 个被迁移文件（C3 已完成，此处登记）

| 原路径 | 迁移后路径 | 说明 |
|---|---|---|
| `tasks/plan.md` | `docs/handoff/history/2026-10-11-STAGE-B-C-PLAN.md` | 仍是 Stage B/C「当前计划」，无当前入口引用；源码停在 `576895f`，顶部加历史归档声明。**移动非删除**，正文保留 |
| `tasks/todo.md` | `docs/handoff/history/2026-10-11-STAGE-B-C-TODO.md` | 同上。`tasks/` 已清空 |

## 5 · `/tmp` 记录

`/tmp` 的**主机级**清理不属本仓库操作范围，C3 的实测记录见
[../2026-10-15-cleanup-orphans/README.md](../2026-10-15-cleanup-orphans/README.md) §5：
白名单只含 `/tmp/summit-ws` 与 0 字节空目录，有内容的一律保留。

主机级说明：`/tmp` 内容会由 **macOS periodic cleaner 在 00:00 清理 3 天未访问的文件**；
因此 `/tmp` 内的临时产物（含本轮 C2 写出的 `/tmp/c2-report-rows.txt`、`/tmp/c2-copy-list.txt`、
`/tmp/c2-app-digests.txt`）**不保证长期存在**，不能作为唯一追溯来源。本轮由 Luna 只删除
`/tmp/summit-ws`（及当时的 0 字节空目录）；C2 的长期证据全部落在本仓库本目录内。

## 6 · 归档副本与源文件逐字节抽样复核（16/16 一致）

复制后对**每个有复制件的 worktree 各抽 1 个文件**（取该 worktree 复制集中字节最大者）重新
`shasum -a 256` 比对 `docs/quality/reports/evidence/2026-10-15-worktree-archive/<wt>/<rel>` 与
`/Users/yifengstudio/.codex/worktrees/<wt>/SummitEverything/.local/<rel>`：

| worktree | 复核文件（相对 `.local`） | 字节 | SHA-256 | 结论 |
|---|---|---|---|---|
| `frontend-a-qa-initial` | `qa/frontend-a-initial/QA-REPORT.md` | 11412 | `5084ec95ce6ef23c882741f0066ee77e9add67ed5e74b7a2cdf4f6d337e4d577` | 一致 |
| `frontend-a-qa-repair1` | `qa/frontend-a-repair1/QA-REPORT.md` | 8327 | `0de123a8cdfdb7c0303577a4ab6a54b3f4b0580cd6f03d17f2f3c7342df55f22` | 一致 |
| `frontend-b-qa-initial` | `qa/frontend-b-initial/evidence-manifest.json` | 16393 | `f3aba213d396040ff0002f0f298e7c48acda45787fcf4a5740c3748088696611` | 一致 |
| `frontend-b-qa-repair1` | `qa/frontend-b-repair1/QA-REPORT.md` | 5727 | `a3038530f85457459577ba0ea7b4c40a92c9f98150e12606de3698dd67a6118e` | 一致 |
| `frontend-c-qa-initial` | `qa/frontend-c-initial/fastapi-integration/frontend-c-flow-manifest.json` | 5169 | `0a9ced7e8f7649a433f0477ea3dc23e5da55e6aee9adadfa1f7ba36e8416cb7b` | 一致 |
| `frontend-d-final` | `dev/frontend-d-final/release-build.log` | 20917 | `2cee76ddc767aea146e2d777cc7918c29532a2863d8c06127220914ada3a2f30` | 一致 |
| `frontend-d-qa-initial` | `qa/frontend-d-initial/evidence-manifest.json` | 36169 | `9cebf32f4ea0cb29af3e676e070ff8044e45cf598ecf8d01eec59e4f174e4f7f` | 一致 |
| `frontend-d-qa-repair1` | `qa/frontend-d-repair1/QA-REPORT.md` | 20518 | `ddbf22f0dfdff040ecb4720310e774e814d0368120d716d82298b11dab0e6c29` | 一致 |
| `frontend-d-qa-repair1-parent` | `qa/frontend-d-repair1/harness/parent-build.log` | 755 | `811fae546c2269d0d73b831ad3599cf29bae7304cdc8b85c35f47fac33ac39d8` | 一致 |
| `frontend-d-qa-repair2` | `qa/frontend-d-repair2/QA-REPORT.md` | 29340 | `ad218f10692d3e5b5efe5ec87d025121286d4b0ab6b0a1c23645c4132612cad0` | 一致 |
| `frontend-d-qa-repair2-parent` | `qa/frontend-d-repair2/logs/08-parent-faa1edd-control.log` | 8232 | `341ed99b97604d99b36d560c069d756017e190bca46df3c17bb009b4f11d21dc` | 一致 |
| `frontend-d-qa-repair3` | `qa/frontend-d-repair3/QA-REPORT.md` | 23886 | `619893cb7f5dfbb121ce25b29afdfc4f6ac10c99a3fe3fa2ddc467dd210d0c93` | 一致 |
| `frontend-d-qa-repair3-parent` | `qa/frontend-d-repair3-parent/logs/01-d6-gate-96fdf4d.log` | 3022 | `55d9d1bb3852579c94fda8fbcd327fd955086a99fc2a4a3bc2a9d38497b26191` | 一致 |
| `m41-internal-app` | `sol/ci/pr-run.log` | 92193 | `428a3752182afe28107b35ae68934c54bee11964c5af03129a6648088a107f52` | 一致 |
| `m41-qa-b9321d6` | `qa/m41/guarded-pytest.log` | 6731 | `ea57028152645f16700bc74bec08dc1f186abbc6d3315a5d05fea558c653dbde` | 一致 |
| `m41-qa-repair1-3f6eaa4` | `qa/2026-10-13-m41-repair1/swift-test.log` | 2329 | `eaa0c6936a7dcb14e8eeedd7c5b77adf6339be70ccc533712a7bf51cd4ab863c` | 一致 |

**16/16 逐字节一致，0 mismatch。** 其余 3 个 worktree（`frontend-d-build`、
`frontend-d-build-repair2`、`frontend-d-build-repair3`）的 `.local` 内只有 `.app`/`.dmg` 二进制，
不满足复制规则、无复制件可复核；其身份由 MANIFEST 的 `TREE` 行与整文件 SHA-256 覆盖。

## 7 · 三个 D 候选 DMG 实测 SHA-256（删除前独立复算）

| 候选 | DMG 路径（相对对应 worktree 的 `.local`） | 整文件 SHA-256 |
|---|---|---|
| `e8e1dba` | `dev/frontend-d-repair3/SummitEverything-D-e8e1dba.dmg` | `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b` |
| `876008e` | `dev/frontend-d-final/SummitEverything-D-876008e.dmg` | `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9` |
| `96fdf4d` | `dev/frontend-d-repair2/SummitEverything-D-96fdf4d.dmg` | `bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765` |

三者均与对应 `MANIFEST.sha256` 内的记录一致（独立 `shasum -a 256` 复算）。

---

## C4 · 分支清退实测输出

执行者：Developer **Luna（High）**，2026-10-15，工作目录
`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`，分支
`codex/frontend-ux-20261015`（tip `207b8f92a5921f630219323d17deee4735450c14`，删除前 `git status --porcelain` 为空）。

### C4.1 删除前身份与并入判定（实测）

```sh
git rev-parse <b>; git merge-base --is-ancestor <b> origin/main; echo "  ancestor_exit=$?"
```

| 分支 | 类型 | 删除前 SHA | `ancestor_exit` |
|---|---|---|---|
| `codex/frontend-baseline-20261014` | 本地 | `38986493bfbac24e216663922d6a793fda574cbb` | **0** |
| `codex/internal-candidate-20261014` | 本地 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **0** |
| `codex/origin-guard-error-20261014` | 本地 | `258f7d820d68673183e62a5b998879ad0d9ca59d` | **0** |
| `codex/settings-ux-20261014` | 本地 | `6f9191d8b8b62f3957ac5eacb207d34202e69abf` | **0** |
| `origin/codex/frontend-baseline-20261014` | 远端 | `38986493bfbac24e216663922d6a793fda574cbb` | **0** |
| `origin/codex/internal-candidate-20261014` | 远端 | `32d9b9e71b447be7ce647a7bdeb54432fe3f1b92` | **0** |

**6/6 `ancestor_exit=0`**（期望值即 0），全部在 `origin/main` 历史中，删除不丢失未合并提交。

### C4.2 本地分支删除（用 `-d`，非 `-D`）

```sh
git branch -d codex/frontend-baseline-20261014 codex/internal-candidate-20261014 \
               codex/origin-guard-error-20261014 codex/settings-ux-20261014
```

实测输出：

```
Deleted branch codex/frontend-baseline-20261014 (was 3898649).
Deleted branch codex/internal-candidate-20261014 (was 32d9b9e).
Deleted branch codex/origin-guard-error-20261014 (was 258f7d8).
Deleted branch codex/settings-ux-20261014 (was 6f9191d).
BRANCH_DELETE_EXIT=0
```

`git branch -d` 未报「not fully merged」，**BRANCH_DELETE_EXIT=0**，与 §2 的并入判定一致。

### C4.3 远端分支删除

```sh
git push origin --delete codex/frontend-baseline-20261014 codex/internal-candidate-20261014
```

实测输出（stdout 为空，以下为 stderr；`--delete` 只删分支，**未 push 到 main**）：

```
To github.com:yifeng93/SummitEverything.git
 - [deleted]         codex/frontend-baseline-20261014
 - [deleted]         codex/internal-candidate-20261014
REMOTE_DELETE_EXIT=0
```

### C4.4 删除后状态（实测）

`git branch -vv`：

```
* codex/frontend-ux-20261015 207b8f9 [origin/codex/frontend-ux-20261015: ahead 4] chore(cleanup): archive worktree evidence with manifests and deleted-path index
+ main                       e84e9e5 (/Users/yifengstudio/Documents/GitHub/SummitEverything) [origin/main] docs: add the handoff prompt for the frontend Sol session
```

`git branch -r`：

```
  origin/HEAD -> origin/main
  origin/codex/frontend-ux-20261015
  origin/main
```

`git ls-remote --heads origin`（exit 0）：

```
e76244ebd6d4ff897dd019c77f1a86197017a20f	refs/heads/codex/frontend-ux-20261015
e84e9e5a56475a19f68ca1a684366fba7f9fee83	refs/heads/main
```

结论：本地只剩 `codex/frontend-ux-20261015` + `main`；远端只剩 `codex/frontend-ux-20261015` + `main`
（`origin/HEAD -> origin/main` 是符号引用，非分支）。保留项 `main` 与
`codex/frontend-ux-20261015` 均未删除（本地或远端）。

## C5 · worktree 清退实测输出

### C5.1 前置：归档清单齐备性（缺一不删）

```sh
ls -d docs/quality/reports/evidence/2026-10-15-worktree-archive/*/ | wc -l
```

实测 = **19**（期望 19）。逐个 `MANIFEST.sha256` 非空检查：**18 个非空**，
`frontend-d-build` 为空清单，属 §1 已登记的已知例外（该 worktree 的 `.local` 内只有
`.app`/`.dmg` 二进制，不满足复制规则、无复制件）。

### C5.2 删除前逐个 clean 确认 + HEAD 记录

```sh
git -C "$p" status --porcelain          # 必须为空输出
git -C "$p" rev-parse HEAD >> /tmp/luna-worktree-heads.txt
```

**19/19 `status --porcelain` 为空（DIRTY_COUNT=0）**，无一例未提交改动。

| worktree | 路径 | 删除前 HEAD | `status --porcelain` 空？ | 归档索引 | 删除结果 |
|---|---|---|---|---|---|
| `frontend-a-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything` | `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad` | 空 | [MANIFEST](frontend-a-qa-initial/MANIFEST.sha256) | removed（exit 0） |
| `frontend-a-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-repair1/SummitEverything` | `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` | 空 | [MANIFEST](frontend-a-qa-repair1/MANIFEST.sha256) | removed（exit 0） |
| `frontend-b-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-b-qa-initial/SummitEverything` | `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` | 空 | [MANIFEST](frontend-b-qa-initial/MANIFEST.sha256) | removed（exit 0） |
| `frontend-b-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-b-qa-repair1/SummitEverything` | `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c` | 空 | [MANIFEST](frontend-b-qa-repair1/MANIFEST.sha256) | removed（exit 0） |
| `frontend-c-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-c-qa-initial/SummitEverything` | `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` | 空 | [MANIFEST](frontend-c-qa-initial/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-build` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build/SummitEverything` | `944634c0795930426b41110052e3ba1eaeebaf52` | 空 | [MANIFEST](frontend-d-build/MANIFEST.sha256)（空清单，已知例外） | removed（exit 0） |
| `frontend-d-build-repair2` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair2/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | [MANIFEST](frontend-d-build-repair2/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-build-repair3` | `/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair3/SummitEverything` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 空 | [MANIFEST](frontend-d-build-repair3/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-final` | `/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | [MANIFEST](frontend-d-final/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-initial` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | [MANIFEST](frontend-d-qa-initial/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair1` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1/SummitEverything` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 空 | [MANIFEST](frontend-d-qa-repair1/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair1-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1-parent/SummitEverything` | `876008e1d33420f57fb31772c76e471379e6b98d` | 空 | [MANIFEST](frontend-d-qa-repair1-parent/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair2` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | [MANIFEST](frontend-d-qa-repair2/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair2-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2-parent/SummitEverything` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 空 | [MANIFEST](frontend-d-qa-repair2-parent/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair3` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3/SummitEverything` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 空 | [MANIFEST](frontend-d-qa-repair3/MANIFEST.sha256) | removed（exit 0） |
| `frontend-d-qa-repair3-parent` | `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3-parent/SummitEverything` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 空 | [MANIFEST](frontend-d-qa-repair3-parent/MANIFEST.sha256) | removed（exit 0） |
| `m41-internal-app` | `/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything` | `52d0f3419bf10ad9cb719efed0580256bd059022` | 空 | [MANIFEST](m41-internal-app/MANIFEST.sha256) | removed（exit 0） |
| `m41-qa-b9321d6` | `/Users/yifengstudio/.codex/worktrees/m41-qa-b9321d6/SummitEverything` | `acd3ef95e199f6af2714df10f548779b6db3aed8` | 空 | [MANIFEST](m41-qa-b9321d6/MANIFEST.sha256) | removed（exit 0） |
| `m41-qa-repair1-3f6eaa4` | `/Users/yifengstudio/.codex/worktrees/m41-qa-repair1-3f6eaa4/SummitEverything` | `2437f9c771ff7da3aaf2b39a387903654fde5b9d` | 空 | [MANIFEST](m41-qa-repair1-3f6eaa4/MANIFEST.sha256) | removed（exit 0） |

删除命令（逐个执行，实测 19/19 `removed`）：

```sh
git worktree remove --force "/Users/yifengstudio/.codex/worktrees/$w/SummitEverything"
git worktree prune            # PRUNE_EXIT=0
```

### C5.3 删除后状态与体积（实测）

`git worktree list`（`wc -l` = **2**，期望 2）：

```
/Users/yifengstudio/Documents/GitHub/SummitEverything                      e84e9e5 [main]
/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything 207b8f9 [codex/frontend-ux-20261015]
```

体积：`du -sh /Users/yifengstudio/.codex/worktrees` **删除前 8.8G → 删除后 1.1G**。

保留项核对：主仓库 `/Users/yifengstudio/Documents/GitHub/SummitEverything` 未删，HEAD 仍为
`e84e9e5a56475a19f68ca1a684366fba7f9fee83`（`main`）；其 `.local/internal-builds/`
内 `3f6eaa4`、`internal-f40bc39`、`m42-419bb86`、`main-bce8843` **四个目录均保留**；
`frontend-ux-20261015` 未删（tip `207b8f9`，worktree clean）。

### C5.4 偏差与残留说明（如实登记）

`ls /Users/yifengstudio/.codex/worktrees` **未**达到计划中「只剩 `frontend-ux-20261015`」的形态，
实测残留两类内容，均**未**由本轮删除：

1. **19 个目标的父目录仍存在，但已空**：每个 0B，`find -mindepth 1` 只剩工具生成的
   `.codex-worktree-name` 标记文件（或完全为空）。19 个 `SummitEverything` checkout 本体
   已随 `git worktree remove` 删除，`git worktree list` 已无其登记。
   `git worktree remove` 删的是 `<name>/SummitEverything`，计划未授权删除父目录，故保留。
2. **约 25 个更早期的孤立目录**（`m1-close`、`m2-*`、`m3-*`、`m42-*`、`qa-stage-*`、
   `stage-b-*`、`summit-m2`、`8c6c` 等）**不在本轮 19 个删除集内**，其来源见
   [DELETED-PATHS-INDEX.md](../../DELETED-PATHS-INDEX.md)，其中 3 个目录
   （`qa-stage-a-final-env` 113M、`qa-stage-a-final-env-2` 113M、`qa-stage-a-final-venv` 108M）
   共约 334M 是残留体积的主要来源，另有 8.0K 的 `m1-close`。这些目录既非本轮授权删除项，
   也无 `.git` checkout（全目录仅 `frontend-ux-20261015` 保有 checkout），故**保留不动**。
   若要收尾到「只剩一个目录」，需用户单独授权删除父目录与这批历史孤立目录。

因此：**worktree 清退本身完成（登记 21 → 2，19/19 checkout 删除，`prune` 退出码 0）**，
残留仅为父目录壳与 scope 外的历史孤立目录。

## C5.5 · 范围外残留目录清理（用户 2026-10-15 另授权）

执行者：Developer **Luna（High）**，2026-10-15 / 2026-10-16（UTC），在同一 worktree
`codex/frontend-ux-20261015`。本节是 §C5.4 登记的残留的**后续清理实测**。

### C5.5.1 授权来源与范围

- **授权来源**：用户在 2026-10-15 **单独授权**（就「是否清理父目录壳与范围外历史孤立目录」
  的两项询问均选 A）。这两个集合**都不在原清理计划 §二 C5 的 19 个 worktree 删除集内**，
  按 AGENTS「不得未经授权删除 branch 或 worktree」，必须有这次单独授权才能删。
- **范围**：`/Users/yifengstudio/.codex/worktrees` 下两集合共 **55 条**：
  1. **19 个 0B 父目录壳**——C5 的 `git worktree remove` 只删 `<name>/SummitEverything`，
     计划未授权删父目录，故留下 19 个壳（每个 0B，`find -mindepth 1` 只剩工具生成的
     `.codex-worktree-name` 标记文件，或完全为空）。这 19 个名字与 §1 的 19 个待删 worktree 一一对应。
  2. **36 个范围外历史孤立目录**——更早期的孤立目录，均**无 `.git` checkout**
     （全目录只有 `frontend-ux-20261015` 保有 checkout）。构成：32 个 0B 目录、
     `m1-close`（8.0K），以及 3 个 Python venv 共 **334 MB**
     （`qa-stage-a-final-env` 113M、`qa-stage-a-final-env-2` 113M、`qa-stage-a-final-venv` 108M）。
- **口径差异登记**：本轮交接任务书写「34 个范围外历史孤立目录」，**实测为 36**
  （19 + 36 = 55 条删除，与删除前后快照 56 → 1 完全吻合）。以本节的逐条清单为准。

### C5.5.2 守卫条件（只删满足全部三项的条目）

1. 绝对路径位于 `/Users/yifengstudio/.codex/worktrees/` **之下**（不做任何通配到该目录之外）；
2. **不是**保留项（保留项只有 `frontend-ux-20261015`）；
3. **不在** `git worktree list` registry 中（即已不是任何已登记 worktree 的路径）。

### C5.5.3 55 条逐条清单（体积取自 `/tmp/sol-worktrees-dir-before.txt`）

类别列标明「C5 壳（19 之一）」与「范围外」。体积为删除前 `du -sh` 实测值。

| # | 目录 | 类别 | 删除前体积 | 说明 |
|---|---|---|---|---|
| 1 | `8c6c` | 范围外 · 历史孤立目录 | 0B | 工具生成的短名目录 |
| 2 | `frontend-a-qa-initial` | C5 壳（19 之一） | 0B | |
| 3 | `frontend-a-qa-repair1` | C5 壳（19 之一） | 0B | |
| 4 | `frontend-b-qa-initial` | C5 壳（19 之一） | 0B | |
| 5 | `frontend-b-qa-repair1` | C5 壳（19 之一） | 0B | |
| 6 | `frontend-c-qa-initial` | C5 壳（19 之一） | 0B | |
| 7 | `frontend-d-build` | C5 壳（19 之一） | 0B | |
| 8 | `frontend-d-build-repair2` | C5 壳（19 之一） | 0B | |
| 9 | `frontend-d-build-repair3` | C5 壳（19 之一） | 0B | |
| 10 | `frontend-d-final` | C5 壳（19 之一） | 0B | |
| 11 | `frontend-d-qa-initial` | C5 壳（19 之一） | 0B | |
| 12 | `frontend-d-qa-repair1` | C5 壳（19 之一） | 0B | |
| 13 | `frontend-d-qa-repair1-parent` | C5 壳（19 之一） | 0B | |
| 14 | `frontend-d-qa-repair2` | C5 壳（19 之一） | 0B | |
| 15 | `frontend-d-qa-repair2-parent` | C5 壳（19 之一） | 0B | |
| 16 | `frontend-d-qa-repair3` | C5 壳（19 之一） | 0B | |
| 17 | `frontend-d-qa-repair3-parent` | C5 壳（19 之一） | 0B | |
| 18 | `m1-close` | 范围外 · 历史孤立目录 | 8.0K | 范围外唯一非 0B 的小目录 |
| 19 | `m2-stage-a-evidence-postmerge` | 范围外 · 历史孤立目录 | 0B | |
| 20 | `m2-stage-a-postmerge` | 范围外 · 历史孤立目录 | 0B | |
| 21 | `m2-stage-a-recovery-ui-ledger` | 范围外 · 历史孤立目录 | 0B | |
| 22 | `m3-c19-unified-qa` | 范围外 · 历史孤立目录 | 0B | |
| 23 | `m3-c19-unified-qa-r1` | 范围外 · 历史孤立目录 | 0B | |
| 24 | `m3-c19-unified-qa-r2` | 范围外 · 历史孤立目录 | 0B | |
| 25 | `m3-package-1-qa` | 范围外 · 历史孤立目录 | 0B | 2026-10-15 之前即已移除；3 条历史绝对路径快照见 [DELETED-PATHS-INDEX.md](../../DELETED-PATHS-INDEX.md) |
| 26 | `m3-package-1-qa-r1` | 范围外 · 历史孤立目录 | 0B | |
| 27 | `m3-package-2-qa` | 范围外 · 历史孤立目录 | 0B | |
| 28 | `m3-package-2-qa-extra1` | 范围外 · 历史孤立目录 | 0B | |
| 29 | `m3-package-2-qa-extra2` | 范围外 · 历史孤立目录 | 0B | |
| 30 | `m3-package-2-qa-r1` | 范围外 · 历史孤立目录 | 0B | |
| 31 | `m3-package-2-qa-r2` | 范围外 · 历史孤立目录 | 0B | |
| 32 | `m3-package-3-qa` | 范围外 · 历史孤立目录 | 0B | |
| 33 | `m3-package-3-qa-r1` | 范围外 · 历史孤立目录 | 0B | |
| 34 | `m41-internal-app` | C5 壳（19 之一） | 0B | |
| 35 | `m41-qa-b9321d6` | C5 壳（19 之一） | 0B | |
| 36 | `m41-qa-repair1-3f6eaa4` | C5 壳（19 之一） | 0B | |
| 37 | `m42-package-a-qa` | 范围外 · 历史孤立目录 | 0B | |
| 38 | `m42-package-a-qa-repair1` | 范围外 · 历史孤立目录 | 0B | |
| 39 | `m42-readiness` | 范围外 · 历史孤立目录 | 0B | |
| 40 | `qa-m1-f364c01` | 范围外 · 历史孤立目录 | 0B | |
| 41 | `qa-stage-a-evidence` | 范围外 · 历史孤立目录 | 0B | |
| 42 | `qa-stage-a-final` | 范围外 · 历史孤立目录 | 0B | |
| 43 | `qa-stage-a-final-env` | 范围外 · Python venv | 113M | venv，3 个合计 334 MB |
| 44 | `qa-stage-a-final-env-2` | 范围外 · Python venv | 113M | venv；唯一被 tracked 报告按路径提及的项，见 C5.5.5 |
| 45 | `qa-stage-a-final-venv` | 范围外 · Python venv | 108M | venv |
| 46 | `qa-stage-b-luna-backend-576895f` | 范围外 · 历史孤立目录 | 0B | |
| 47 | `qa-stage-b-luna-final-backend` | 范围外 · 历史孤立目录 | 0B | |
| 48 | `qa-stage-b-luna-final-ui` | 范围外 · 历史孤立目录 | 0B | |
| 49 | `qa-stage-b-luna-ui-retest-576895f` | 范围外 · 历史孤立目录 | 0B | |
| 50 | `qa-stage-b-refresh-final` | 范围外 · 历史孤立目录 | 0B | |
| 51 | `qa-stage-b-sol-backend` | 范围外 · 历史孤立目录 | 0B | |
| 52 | `qa-stage-b-sol-ui` | 范围外 · 历史孤立目录 | 0B | |
| 53 | `qa-stage-b-ui-retest` | 范围外 · 历史孤立目录 | 0B | |
| 54 | `stage-b-real-providers` | 范围外 · 历史孤立目录 | 0B | |
| 55 | `summit-m2` | 范围外 · 历史孤立目录 | 0B | |

### C5.5.4 删除后结果（实测）

| 项 | 删除前 | 删除后 |
|---|---|---|
| `ls /Users/yifengstudio/.codex/worktrees` | **56 条 / 1.1 G** | **1 条 / 804 M** |

删除后唯一保留项为 `frontend-ux-20261015`（804M，即本 worktree）。
`git worktree list` 仍为 **2** 行；主仓库 `/Users/yifengstudio/Documents/GitHub/SummitEverything`
及其 `.local/internal-builds/` 四个目录**未删**。删除后 `git status --porcelain`（本 worktree）为空。

### C5.5.5 唯一被 tracked 文档提及的范围外项

3 个 venv 中只有 **`qa-stage-a-final-env-2`** 被 tracked 报告按路径提及：
`docs/quality/reports/2026-10-10-M2-stage-a-final-qa.md` **第 14 行**记为
「Runtime dependencies were installed in an external isolated environment at
`/Users/yifengstudio/.codex/worktrees/qa-stage-a-final-env-2`」。
该句是**历史陈述**，描述当时确实存在的隔离环境，删除该目录**不使该句失真**；
且该目录**不是证据原件**（venv 不入 MANIFEST、不复制），故无「被 tracked 文档引用却未归档的原件」问题。

补充实测：36 个范围外项中，被 tracked 文档以 **Markdown 链接**形式指向的只有 `m3-package-1-qa`
（3 条，已在 [DELETED-PATHS-INDEX.md](../../DELETED-PATHS-INDEX.md) §0/§1 登记）；其余提及都出现在
历史报告正文的行内代码或原始日志里，是路径快照、**不是链接**，本轮按 AGENTS 逐字保留、未改写。

### C5.5.6 快照与不可逆声明

删除前后的逐条体积快照保存在 **`/tmp/sol-worktrees-dir-before.txt`（56 行）** 与
**`/tmp/sol-worktrees-dir-after.txt`（1 行）**——两者均为**主机级、未入库**；55 条的删除清单
另存于 `/tmp/sol-worktrees-dir-delete.txt`。`/tmp` 内容会由 macOS periodic cleaner 清理，
因此**长期追溯以本节的 55 行表为准**。删除不可逆：这些目录既不在 Git 中，也无归档副本
（3 个 venv 按设计不入库；其余为 0B/8K 空壳或历史目录，其内容在更早轮次的 evidence 中另有记录）。
