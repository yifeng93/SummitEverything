# 前端 UX 里程碑 D · Sol 最终门判断

- **最终固定产品源码 SHA：`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（分支 `codex/frontend-ux-20261015`，父 `96fdf4d`）。
- 最终 native 候选：`SummitEverything-D-e8e1dba.app` / `.dmg`，DMG SHA-256 `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b`，build ID `20261015T144744Z-784ae1ee176a`，`frontend_sha256=784ae1ee…`、`dependencies_sha256=cab2747…`、`source_sha=e8e1dba`、`dirty=false`。
- 本判断基于：Developer 报告、三轮 QA 报告原件与 raw 日志、真实退出码与计数、两个候选包内 `build-info.json` 与 `Resources/web` 指纹、`git diff` 与 tree 状态，以及 Sol 自己执行的 native 实机验证（截图 + 本机 Vision OCR）。
- 本轮之后的 docs 提交都不是受测产品 SHA；`git diff e8e1dba <docs tip> -- src tests web pyproject.toml uv.lock` 为空。

## 判定

| 范围 | 判定 |
|---|---|
| **repair1 的 P1**（首配进度重启后丢失 → 被拉回向导 step 2） | **CLOSED** |
| **native WKWebView 同 profile 重启**（D 门此前唯一硬缺口） | **PASS**（Sol 实机，机器 OCR 判读；QA **未能独立复现**，已在报告注明） |
| **D 里程碑门 —— 限「离线 + 内部候选」范围** | **PASS** |
| 自动修复轮次 | D 初次 QA FAIL 后使用 **2/2**（repair1 关闭 P1；repair3 关闭 repair2 QA 发现的 D-6）。repair2 的 D-1/D-4 是用户另行要求的定点改进，不占 QA 失败修复轮 |
| 真实服务 / Keychain / 安装 / 公证 / 五日 / 双机 / 发布 / 页面缩放 | **NOT_RUN**（各自独立门，未包含在本 PASS 内） |

## Sol 的核对动作

| 核对项 | 结果 |
|---|---|
| 受测 SHA 可解析、产品树自固定后未变 | ✅ `e8e1dba..tip` 只含 docs（PR 之前） |
| Developer / QA / 构建 worktree 状态 | ✅ 取证时均 clean；QA 报告的开发者 worktree 非空仅为未跟踪 docs（N-1），随后已提交 |
| QA 是否独立（未复用开发者测试） | ✅ 三轮各自自建 harness |
| harness 是否具备判别力 | ✅ repair1 轮在父 `876008e` 复现 P1（20 checks/8 failed/exit 1）；repair2 轮在父 `faa1edd` 复现 D-1（23/18/exit 1）；repair3 轮在父 `96fdf4d` 复现 D-6 门 exit 1 |
| 计数与退出码 | ✅ pytest 692、vitest 222/26 files/0 todo、e2e 2、e2e:integration 1、typecheck/lint(2 warnings 0 errors)/build/ruff check/ruff format/mypy(47)/uv lock/uv build 全 exit 0；与 Developer 声称零差异 |
| OpenAPI CI 门 | ✅ `e8e1dba` exit 0；父 `96fdf4d` exit 1（门未变软） |
| 证据可继承性论证 | ✅ 三处指纹同为 `784ae1ee…`、两次构建产物逐字节相同、`src` diff 为空。Sol 采纳 QA 的边界说明：可继承的是**产物行为结论**，不可继承的是「在该 SHA 上运行过」——QA 仍在新 SHA 重跑了功能检查 |
| native 候选身份与预检 | ✅ 两候选 `dirty=false`；启动前 18793 无 listener；backend 进程环境只有 allowlist 的 11 个变量名、`SUMMIT_OFFLINE_GUARD_ACTIVE=1`、profile 为我传入的 canonical TMPDIR 子目录；token 存在但从未打印；`/api/v1/health` 与 manifest 一致；`/` 200；启动时 `workspace_open=false` |
| 包内 runtime（自建 harness） | ✅ 15/15 exit 0，两个候选各一次；含 P15「杀进程另起新进程后 completed 记录仍读回」 |
| GUI 结束后清理 | ✅ 三轮启动的 app/backend PID 均已退出，18793 无 listener，无候选残留 |
| 是否触碰真实服务/凭据/安装/生产 | ✅ 无 |
| 是否 push / merge / 删 branch 或 worktree | ✅ 未 push、未 merge、未删除；所有旧候选（`876008e`、`96fdf4d`、`main-bce8843`）与三个 QA checkout、两个 build worktree 全部保留 |
| 证据是否含 token / 真实数据 | ✅ 凭据形状扫描无命中 |

## Native 实机验证（Sol 执行，逐条标注证据强度）

| 路径 | 预置条件 | 判读方式 | 结果 |
|---|---|---|---|
| 已完成 → 重启 → 打开已有 | 记录 `{step:5,completed:true,open:false}`（前一次 native 首配真实写入） | **机器 OCR**：出现「今日」导航与今日内容，无「连接向导 / 第 2 步 · 模型与密钥」 | **PASS** |
| 未完成且 open → 恢复原 step | 注入 `{step:3,completed:false,open:true}`（**公开披露的预置条件**） | **机器 OCR**：「第 3 步 · 检查连接」 | **PASS** |
| 明确关闭 → 重启不自动弹 | 记录 `{step:3,completed:false,open:false}`，由用户在真实 UI 点「关闭向导」写出 | 记录由 UI 真实写入已核验；启动后 `workspace_open=false`。**「落到今日且无向导」只有用户观察，未抓到该瞬间截图** | 用户观察（非 agent 证据） |
| 设置里手动续接原 step | 同上 | **机器 OCR**：「第 3 步 · 检查连接」 | **PASS** |

**限制（必须随 PASS 一并阅读）**：macOS Accessibility 未授权（`AXIsProcessTrusted=false`，System Events `-1719`），所以**点击全部由用户完成**，Sol 无法自动驱动 UI；Screen Recording 已授权，截图有效，但本会话模型不支持图像输入，故 Sol 自建本机 Vision OCR 工具把截图转成文本后断言。`websiteDataStore = .nonPersistent()` 已在 `native/Sources/SummitEverythingApp/App.swift` 源码核对。**QA 未独立复现任何 native GUI 结论**，其结论只覆盖浏览器/HTTP/制品层。

## 缺陷台账与处置

| 编号 | 级别 | 处置 |
|---|---|---|
| P1 首配进度重启丢失 / 被拉回 step 2 | **P1** | **已关闭**（repair1 `faa1edd`），native 实机复验 |
| D-1 pre-repair1 老工作库被再次 onboarding 且遮挡 Today | P3 | **已修**（repair2 `96fdf4d`，create/open 区分），QA 在 `96fdf4d` 与 `e8e1dba` 均判 PASS |
| D-2 StrictMode dev 下迁移 PUT 发 2 次 | P3（dev 专属） | 文档收紧为「生产构建语义」；产品不改 |
| D-3 OpenAPI 未声明 401/404/503 | INFO | 记录为后续契约补全项，本 SHA 不改 |
| D-4 整数值浮点 `3.0` 被归一化接受 | INFO | **已修**（repair2 严格整数校验），QA 判 PASS |
| D-5 新建后未推进即 reload/重启会落到 Today | P3 | **用户决议接受为记录项**；「新建仍走向导」的表述已限定为「点击创建那一刻」 |
| D-6 `generated.ts` 与 `openapi.json` 失同步（CI 门失败） | **P2** | **已修**（repair3 `e8e1dba` 只重生成该文件），QA 判 PASS 并给了父 SHA 非空对照 |
| D-7 repair1 交接文档与代码不一致 | INFO | 已在 docs 提交纠正 |
| N-1 开发者 worktree 取证期间存在未跟踪 docs | Nit | 已在 docs 提交中落盘 |

## 证据口径决定

- **876 的十条守卫变异：不可继承。** 前端 bundle 指纹已从 876 变为 `784ae1ee…`，那不是同一产物；因此不以 876 的十变异充当本轮结果。本轮改由 **5 条定向变异**覆盖被改动行为（repair1 三条：重演 P1、忽略写入失败、忽略 durable 读取；repair2 两条：打开已有被再次 onboarding、整数值浮点被接受），全部 red exit 1、恢复后绿，日志在 `.local/dev/frontend-d-repair1/mutation/` 与 `.local/dev/frontend-d-repair2/mutation/`。
- **全站视口矩阵：已在 `e8e1dba` 重跑。** 默认 `test:e2e`（`viewport.spec.ts` + `first-use.spec.ts`）2/2、`frontend-c-view.spec.ts`（项目/阅读/问答 × 五档 × 深浅）1/1、`frontend-c-flow.spec.ts`（引用更新闭环）1/1，全部 exit 0，产出 92 张矩阵截图（`.local/dev/frontend-c/`）。日志在 `.local/dev/frontend-d-repair3/viewport-matrix-c-view.log`、`frontend-c-flow.log`。
- 876 的 204 Web tests / 候选 / CSS zoom 模拟同样只作历史，不作为本轮证据。

## 真实远端 CI（本轮首次运行）

PR [#21](https://github.com/yifeng93/SummitEverything/pull/21) 触发 `.github/workflows/m41-internal-app.yml`（`pull_request` 事件；该 workflow 的 push 触发分支只覆盖 `codex/m41-internal-app-*`，所以此前的 CI 门都只是本地精确复现）。

- run `38757225760`（job `offline-arm64`）：**completed / success，4m42s**，headSha `289947fac15ec5e79fe0122195f9cbe32f59d629`（docs tip；其祖先即受测产品 `e8e1dba`，docs 提交不改产品树）。
- run `38758095886`：**completed / success，4m0s**，headSha `0a311f37faab92d5f63e7e034d0688a4952943b6`（再一个 docs tip，产品树仍与 `e8e1dba` 相同）。
- 全部步骤 success，包含：`Guarded Python checks`（`pytest -q` + `ruff check` + `ruff format --check` + `mypy src` + `uv lock --check` + `uv build`）、`Web checks and API types`（`api:types` + **`git diff --exit-code -- web/src/api/generated.ts`** + `vitest` + `typecheck` + `lint` + `build`）、**`Native upload policy tests`（`swift test --package-path native`）**、`Build and verify internal App and DMG`。
- **必须一并记录的一次基础设施抖动**：PR 创建时的首个 run `38756944004`（headSha `e8e1dba`）**失败**，失败步骤只有 `Build and verify internal App and DMG`，原因是 `hdiutil: create failed - Resource busy`（GitHub macOS runner 的 DMG 创建瞬时故障），不是产品缺陷——同一 run 里 `Guarded Python checks`、`Web checks and API types`（含 D-6 那条门）与 `Native upload policy tests` **全部 success**；随后两个 headSha 的同一产品树上该步骤均成功。日志：`.local/dev/frontend-d-repair3/pr21-ci-failed-run.log`。
- 意义：**D-6 那条 CI 门已在真实远端 CI 上通过**；此外它顺带关闭了两个此前记为 NOT_RUN 的项——**`swift test` 真实运行通过**，以及 **App/DMG 的构建与校验在 CI 中完成**（仍不含 GUI 交互）。DMG 步骤本身存在 runner 侧抖动风险，后续若再见到该步骤失败应先看是否为 `Resource busy` 后重跑，而不是直接判产品失败。
- 原始证据：`gh run view … --json` 输出与 `gh pr checks --watch` 日志在 `.local/dev/frontend-d-repair3/`（`pr21-ci-run.json`、`pr21-ci-run-final.json`、`pr21-ci.log`、`pr21-ci-final.log`、`pr21-ci-failed-run.log`，watch 退出码均 0）。

## 合入

用户已批准「同时开 PR 到 main」。本轮分支 `codex/frontend-ux-20261015` 相对 `main` 的 merge-base 是 `e84e9e5`，PR 实际包含**整条前端 UX 线 A→D**（217 文件、+15341/−1755），不是仅 D。PR 链接与合入状态见[最新交接](../../handoff/LATEST-IMPLEMENTATION.md)；**合并动作本身仍需用户明确批准**（AGENTS：重要里程碑合并需用户批准）。

## 本 PASS 明确不覆盖

真实 provider / 飞书 OAuth / Keychain 生命周期 / 真实业务材料 / 已安装 App / Developer ID 与公证 / 五日 / 双机 / 生产与发布；200% 浏览器菜单缩放与原生 `pageZoom`；native GUI 的**独立**复现（native 三条路径由 Sol 实机以机器 OCR 判读，QA 未独立复现；`swift test` 与 App/DMG 构建校验已由真实 CI 覆盖，但仍不含 GUI 交互）。
