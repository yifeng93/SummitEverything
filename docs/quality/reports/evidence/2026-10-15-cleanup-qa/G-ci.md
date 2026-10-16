# G · 真实 CI（`gh` 实测，2026-10-16 QA 独立查询）

工作流：`.github/workflows/m41-internal-app.yml`，`name: offline-arm64 checks (python, web, native, DMG)`，
单一 job `offline-arm64`（`runs-on: macos-14`）。四个验收对象在该 job 内是**步骤（steps）**，
不是四个 job —— 见下方 `gh run view --json jobs` 的 steps 展开。

## 1 · 分支上的 run 列表

```sh
gh run list --branch codex/frontend-ux-20261015 --limit 8 --json databaseId,headSha,status,conclusion,event
```

| databaseId | headSha | 事件 | conclusion |
|---|---|---|---|
| 38832106964 | `ebb6b6f0c9a8c57d7eb5108e497661b7d50e11f5` | pull_request | success |
| 38831643643 | `68c36399c3ecc02b35be3fa2110c97fae3fcde0d` | pull_request | success |
| **38831085564** | **`af65f049a12caebbcb932a86e610282702e1ffc3`** | pull_request | **success** |
| 38758825657 | `e76244ebd6d4ff897dd019c77f1a86197017a20f` | pull_request | success |
| 38758095886 | `0a311f37faab92d5f63e7e034d0688a4952943b6` | pull_request | success |
| 38757225760 | `289947fac15ec5e79fe0122195f9cbe32f59d629` | pull_request | success |
| 38756944004 | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | pull_request | **failure**（仅 `Build and verify internal App and DMG`，`hdiutil: create failed - Resource busy`，DEV/PROGRESS 已如实记录） |

## 2 · 指定 run 38831085564

```sh
gh run view 38831085564 --json headSha,status,conclusion,jobs
```

```
headSha    = af65f049a12caebbcb932a86e610282702e1ffc3   （== af65f04，清理后 tip）✔
status     = completed
conclusion = success                                    ✔
JOB offline-arm64 -> success
  step 6 Guarded Python checks              -> success   ✔
  step 7 Web checks and API types           -> success   ✔
  step 8 Native upload policy tests         -> success   ✔
  step 9 Build and verify internal App and DMG -> success ✔
```

**四项步骤全部 success → PASS。**

## 3 · PR #21 上后续 run 的 headSha / conclusion

```sh
gh pr checks 21
# offline-arm64  pass  3m42s  https://github.com/yifeng93/SummitEverything/actions/runs/38832106964/job/116752970185
```

| 后续 run | headSha | conclusion | 说明 |
|---|---|---|---|
| 38831643643 | `68c36399c3ecc02b35be3fa2110c97fae3fcde0d`（`68c3639`，C5.5 残留清理提交） | success | 该 PR 上 push 再次触发 workflow |
| 38832106964 | `ebb6b6f0c9a8c57d7eb5108e497661b7d50e11f5`（`ebb6b6f`，C6 文档修订） | success | **`gh pr checks 21` 当前显示的即此 run** |

工作流 `on.pull_request` **无分支过滤**，仅有 `paths` 过滤：`src/**`、`tests/**`、`web/**`、`native/**`、
`scripts/**`、`pyproject.toml`、`uv.lock`、`.github/workflows/m41-internal-app.yml`。

「该 PR 上任何 push 都会触发该 workflow」的**实测支持**：`68c3639`（`chore(cleanup): record the real CI
result on the cleaned tip`）**自身只改 1 个 `docs/**` 文件**（`git show --stat 68c3639` = 1 file changed,
221 insertions，路径 `docs/quality/reports/evidence/2026-10-15-cleanup-ci/README.md`），按 `paths` 字面
**不匹配任何条目**，但它仍产生了 run `38831643643`（`headSha=68c3639`）。这与 GitHub 对 `pull_request`
路径过滤按**整个 PR diff**（base…head）判定一致；加上 `af65f04`（改 workflow 自身）触发 `38831085564`，
三次 push 各产生一次 run，实测成立。

**未测边界（如实记录）**：`412e0fd` 与 `7a448c3` 两个提交**未 push**（`git ls-remote --heads origin`
显示远端 branch tip 停在 `ebb6b6f`），因此 **CI 从未在 `7a448c3` 这个受测 SHA 上跑过**；
这两个提交也**没有**任何对应 run。本节 success 的 run 全部对应 `af65f04` 及更早/平行的其它 SHA。
（基于 `68c3639` 的实测，若 `412e0fd`/`7a448c3` 被 push，预期会触发新 run；但该预期**未被观测**，
不作为结论。）
