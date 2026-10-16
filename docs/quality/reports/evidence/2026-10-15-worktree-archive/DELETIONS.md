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
[DELETED-PATHS-INDEX.md](../DELETED-PATHS-INDEX.md)）。

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

（待 C4 追加）

## C5 · worktree 清退实测输出

（待 C5 追加）
