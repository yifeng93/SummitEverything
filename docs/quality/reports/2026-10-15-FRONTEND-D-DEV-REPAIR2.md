# 前端 UX 里程碑 D Developer 报告 · repair2 / repair3 + native 候选验证

日期：2026-10-15。**最终固定产品源码 SHA：`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（分支 `codex/frontend-ux-20261015`）。

SHA 链：初次 `876008e`（QA FAIL / P1）→ repair1 `faa1edd`（P1 修复，QA PASS 限定范围）→ repair2 `96fdf4d`（D-1 + D-4，QA 判 D-6 FAIL）→ **repair3 `e8e1dba`（只重生成 `generated.ts`）**。本报告只记录 Developer 实测与证据索引；**fresh QA 对 `e8e1dba` 的结论与 Sol 门判断见对应报告**。产品 SHA 固定后本轮只再做文档。

## repair2 的行为变化（D-1、D-4）

**D-1（P3，QA 观察）**：pre-repair1 已配好、本机无首次配置记录的工作库，会被再次拉进向导第 2 步，而且 `.wizard-backdrop` 在关闭前**挡住今日**。修法是让「工作库 gate 把用户意图上抛」：

- `WorkspaceGate.onOpened(workspace, mode)`，`mode` 为 `'create' | 'open'`——这是真实的用户意图，不是对凭据的推断；
- `App` 在本机**没有**记录时：`create`（新建）仍自动开始向导第 2 步（首次使用语义不变）；`open`（打开已有）**落到今日**并给出指向设置的非阻塞中性提示，不再遮住今日；
- 页面 reload 时工作库已经开着，一律按 `open` 处理。

**D-4（INFO，QA 观察）**：`FirstUseProgress.step` 的 `Literal[2,3,4,5]` 会把整数值 JSON 浮点（`3.0`）在 lax 模式下归一化接受。新增 `mode="before"` 的整数校验器：只接受真整数，`3.0 / 2.0 / 2.5 / 4.5 / true / "3" / null / -1 / 0 / 6` 全部 422。OpenAPI 仍是 `integer enum [2,3,4,5]`。

## repair3 的修复（D-6）

QA 对 `96fdf4d` 判 FAIL 的唯一一条：`web/openapi.json` 重新导出了，但派生的 `web/src/api/generated.ts` 没有重新生成，导致仓库 CI 步骤 `npm run api:types && git diff --exit-code -- generated.ts` 失败（父 SHA 上该门 exit 0，故为本轮引入）。

`e8e1dba` 只重生成 `web/src/api/generated.ts`（+5 行 JSDoc，位于 `FirstUseProgress` 类型声明内）。`git diff --stat 96fdf4d e8e1dba` **只有**这一个文件，`git diff 96fdf4d e8e1dba -- src` 为空。

## 用户决议

- **D-5（P3，QA 观察，接受不改）**：`create` 意图只存在内存里，所以「新建后一步都没走就 reload/重启」会退出向导落到今日并给出同一条提示（父 SHA 是回到向导第 2 步）。用户明确接受为已记录限制，不在本 SHA 修改；本报告据此把「新建工作库仍自动开始向导」限定为**点击创建那一刻**，跨 reload/重启不成立。
- **D-3（INFO，未改）**：OpenAPI 未声明该路由实际存在的 401/404/503，继续作为后续契约补全项。
- **D-7（INFO）**：repair1 交接文档在 `96fdf4d` 时点仍把 D-1 写成「待用户决议」、D-4 写成「可选小修」，已在随本轮的文档提交中纠正。

## Developer 自测（先红后绿）

| 检查 | 结果 | 原始证据 |
|---|---|---|
| repair2 后端 red | **RED**，exit 1，4 failed / 27 passed | `.local/dev/frontend-d-repair2/red/backend.log`、`red/backend.exit` |
| repair2 前端 red | **RED**，exit 1，1 failed / 7 passed | `red/frontend.log`、`red/frontend.exit` |
| Python guarded pytest（`e8e1dba`） | **PASS**，**692 passed**，exit 0 | `.local/dev/frontend-d-repair3/python.log`、`python.exit` |
| Web 单测（`e8e1dba`） | **PASS**，26 files、**222 passed / 0 todo**，exit 0 | `frontend-d-repair3/web.log` |
| **CI 门 `npm run api:types` + `git diff --exit-code`** | **PASS**，exit 0（`96fdf4d` 上为 exit 1，D-6） | `frontend-d-repair3/api-types.log` |
| TypeScript / Oxlint / build | **PASS**，exit 0；lint 保留既存 2 条 warning、build 保留既存 chunk 提示 | `typecheck.log`、`lint.log`、`build.log` |
| Offline Playwright（默认门） | **PASS**，2/2，exit 0 | `e2e.log` |
| FastAPI + Fake 集成 E2E | **PASS**，1/1，exit 0 | `e2e-integration.log` |
| ruff check / ruff format / mypy / uv lock | **PASS**，exit 0（mypy 47 files） | 同上目录 |
| Swift | **NOT_RUN**；`git diff 876008e e8e1dba -- native` 为空，native 源码未变，不继承旧 5/5 作为本轮结果 | — |

repair2 两条定向变异（先破坏、确认红、再完整恢复，无 `.mutbak` 残留）：

| 变异 | 破坏方式 | 结果 |
|---|---|---|
| 04 | 让「打开已有且无记录」重新自动走向导（重演 D-1） | **RED**，exit 1，1 failed / 7 passed |
| 05 | 去掉 `step` 整数校验器 | **RED**，exit 1，4 failed / 27 passed |

## Native 候选（两次构建，身份可分）

按用户授权构建，未安装、未覆盖。注：本会话没有 Codex native `create_worktree` 工具，改用 `git worktree add --detach <path> <sha>` 创建 detached 构建 worktree，这是流程上的替代做法，已如实记录。构建前 18793 无 listener；只把主仓库 `.local/first-use/defaults.json` 复制到构建 worktree 的 ignored 同路径，未打印内容。两个候选均 `dirty=false`。

| 项 | repair2 候选 | **最终（repair3）候选** |
|---|---|---|
| Source SHA | `96fdf4d` | **`e8e1dba`** |
| App | `…/frontend-d-build-repair2/…/.local/dev/frontend-d-repair2/SummitEverything-D-96fdf4d.app` | `…/frontend-d-build-repair3/…/.local/dev/frontend-d-repair3/SummitEverything-D-e8e1dba.app` |
| DMG SHA-256 | `bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765` | `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b` |
| Build ID | `20261015T142919Z-784ae1ee176a` | `20261015T144744Z-784ae1ee176a` |
| frontend SHA-256 | `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0` | **同左（逐字节相同）** |
| dependencies SHA-256 | `cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7` | 同左 |

**证据可继承性（已实测）**：两个 SHA 之间只有 `web/src/api/generated.ts` 不同；该文件是 types-only、构建时被擦除。实测本 worktree 的 `web/dist` 指纹、候选包内 `Resources/web` 指纹、以及两次构建记录的 `frontend_sha256` **三者都是 `784ae1ee…`**，且 `git diff 96fdf4d e8e1dba -- src` 为空。因此 QA 对生产构建 `web/dist` 的浏览器结论覆盖的就是候选包内同一个 bundle。

两个候选上 `scripts/smoke_packaged_app.py` 均 **PASS**（identity 与 manifest 一致、静态入口 200、未授权读写 401、端口冲突、parent-pipe 清理）。

## 包内 runtime 验证（自建 harness，无 GUI、无凭据、无外网）

`.local/dev/frontend-d-repair2/harness/packaged_progress_restart.py` 直接启动候选包内的 backend（与 smoke 相同的做法），用隔离临时 profile 与合成 token 取证，**15/15 passed，exit 0**（在 `96fdf4d` 与 `e8e1dba` 两个候选上各跑一次）：

- 包内 identity 与 manifest 一致；`Resources/web` 内确实带有 `first-use/progress`；静态入口 200；未授权读 401；
- 工作库 profile 目录落在隔离 profile root 内；无记录 → 404 `first_use_progress_absent`；
- 写入 completed 记录后，`first-use-progress.json` 位于该工作库 profile 目录且**只有**三个白名单键；
- `3.0` → 422；带 `secret` 字段 → 422 且 `DEADBEEF` 从未落盘；被拒写入不改动既有记录；
- **P15（P1 核心）**：杀掉 backend 进程、用同一 profile root 另起新进程、重新打开同一工作库后，completed 记录仍然读回。

## Native WKWebView 验证（最终候选，真实点击 + 机器 OCR 判读）

启动方式：LaunchServices `open -n --env SUMMIT_INTERNAL_TEST_PROFILE_ROOT=<canonical TMPDIR child> --env SUMMIT_OFFLINE_GUARD_ACTIVE=1 <app>`，从未直接执行 `.app/Contents/MacOS/…`。预检实测：backend 进程环境**只有** allowlist 的 11 个变量名（`HOME PATH` + 9 个 `SUMMIT_*`），`SUMMIT_OFFLINE_GUARD_ACTIVE=1`、`SUMMIT_PROFILE_ROOT` 等于我传入的 canonical 临时子目录，session token 存在但**从未打印**；`/api/v1/health` 的 `source_sha=e8e1dba…`、`build_id` 与 manifest 一致；`/` 返回 200；启动时 `workspace_open=false`（不自动打开上次工作库）。全程未触碰真实 Keychain / provider / 飞书 / 用户资料。

本会话模型不支持图像输入，因此截图后统一用本机 Vision OCR（`.local/dev/frontend-d-repair2/tools/ocr.swift`）转成文本再断言，截图与 OCR 文本都留在 `.local/dev/frontend-d-repair3/`。

| 路径 | 预置条件 | 用户操作 | 判读方式 | 结果 |
|---|---|---|---|---|
| 1 已完成 → 今日 | 记录 `{step:5,completed:true,open:false}`（由前一次 native 首配真实写入） | 打开已有 → `/tmp/summit-ws` → 打开工作库 | **机器 OCR**：出现「今日」导航与今日内容，且无「连接向导 / 第 2 步 · 模型与密钥」 | **PASS** |
| 2 未完成且 open → 恢复原 step | 注入 `{step:3,completed:false,open:true}`（**公开披露的预置条件，不是证据**） | 同上 | **机器 OCR**：向导出现在「第 3 步 · 检查连接」，且无第 2 步 | **PASS** |
| 3a 明确关闭后重启不自动弹 | 记录 `{step:3,completed:false,open:false}`，由用户在真实 UI 点「关闭向导」写出 | Cmd+Q 后由我重新启动 → 打开已有 | 记录由 UI 真实写入已核验；启动后 `workspace_open=false`。**「落到今日且不出现向导」这一条只有用户观察，我没有抓到该瞬间的截图** | 用户观察（非 agent 证据） |
| 3b 设置里手动续接原 step | 同上 | 设置 → 打开连接向导 | **机器 OCR**：向导从「第 3 步 · 检查连接」继续 | **PASS** |

GUI 结束后只退出我启动的 PID（20617/20820、20824/20827、20904/20907），每次均确认 app 与 backend 进程消失且 18793 无 listener；没有其他候选残留。

**限制**：macOS Accessibility 未授权（`AXIsProcessTrusted=false`，System Events 报 `-1719`），所以点击全部由用户完成、我无法自动驱动 UI；Screen Recording 已授权，截图与 OCR 有效。`pageZoom` / 200% 菜单缩放仍 **NOT_RUN**（640 CSS px 只是 reflow）。

## 未验证项与边界

- **真实 provider / 飞书 OAuth / Keychain / 真实材料 / 已安装 App / Developer ID 与公证 / 五日 / 双机 / 生产与发布**：未触碰、未测。
- **`WKWebView 丢弃 localStorage 而 local_profile_dir 持久` 这一前提**：本轮在 **native 实机**上间接确认了「完成向导后记录真的落在 profile 目录、重启后能读回并据此进入今日」；`websiteDataStore = .nonPersistent()` 也已在 `native/Sources/SummitEverythingApp/App.swift` 源码中核对，但未做专门的存储语义对照实验。
- **D-5**（新建后未推进即 reload/重启会落到今日）：用户接受为记录项。
- **D-3**（OpenAPI 未声明 401/404/503）：记录项。
- 876 的十条变异与全站视口矩阵本轮未重跑；受影响 E2E 已重跑。
- 候选是 **ad-hoc、未公证**的内部验证包；`spctl` 结论沿用历史记录，不代表用户安装或发布通过。

## Fresh QA 交接

请对 **`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`** 独立复核：(a) D-6 门 exit 0、且在父 `96fdf4d` 上 exit 1；(b) `96fdf4d → e8e1dba` 只差 `generated.ts` 且 `src/` 未变；(c) 前端指纹一致性是否成立（决定 repair2 的 D-1/D-4/P1 证据能否继承）；(d) 抽验 D-1 / D-4 / P1 与全套自动检查。native GUI 结论**未由 QA 独立复现**，应在报告中明确标注。
