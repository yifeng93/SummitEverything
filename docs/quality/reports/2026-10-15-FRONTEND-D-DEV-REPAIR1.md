# 前端 UX 里程碑 D Developer 报告 · 修复轮 1

日期：2026-10-15。固定产品源码 SHA：`faa1edd611a74dcdc26bff234de810bdf47761cb`，父产品 SHA：`876008e1d33420f57fb31772c76e471379e6b98d`（分支 `codex/frontend-ux-20261015`）。本报告只记录 Developer 实测与证据索引；**fresh QA 尚未验收、Sol 尚未判门，不声称 D PASS、不声称 P1 已关闭**。产品 SHA 固定后本轮只再做文档/evidence。

本轮严格按用户选择执行「完整 dev 闭环、不建包」：没有构建新的 App/DMG 候选，也没有启动原生 GUI。因此**原始 P1 被观察到的那条 native WKWebView 同 profile 重启路径本轮 NOT_RUN**，见文末边界。

## 初次 P1 与根因

D 初次固定 SHA `876008e` 经 fresh QA 判 **FAIL / P1**：完成首次配置后，同 profile/同一工作库重启，workspace gate 重现，打开已有工作库后再次进入向导「模型与密钥」第 2 步，今日页不可达。脱敏报告见 [D 初次 QA](2026-10-15-FRONTEND-D-QA-INITIAL.md)，原始证据保留在 QA checkout 的 ignored `.local/qa/frontend-d-initial/`。

根因有两处，缺一不可：

1. 进度只写浏览器 `localStorage`（旧 `web/src/components/firstUseProgress.ts` 的 `writeFirstUseProgress`），而打包应用运行在数据存储为 nonPersistent 的 WKWebView 里，重启后这份副本必然为空。
2. `web/src/App.tsx` 的 `WorkspaceGate onOpened` 无条件执行 `setSection('settings')` 与 `setFirstUse({ open: true, step: 2 })`，完全无视本机是否已经记录过进度。

## 修复行为

进度真源移到本机后端，按 profile + 工作库隔离，只保存非秘密的三个字段。

**存储层**：新增 `src/summit_everything/local/first_use_progress.py`。文档位于活动工作库自己的 `local_profile_dir` 下（`first-use-progress.json`），因此不同工作库、不同 profile 天然看不到彼此。写入使用锁文件 + `mkstemp`/`fsync`/`os.replace`/目录 `fsync` 的原子替换；`FirstUseProgress` 是 `extra="forbid"` + 严格布尔的白名单模型，非法 `step`、未知字段、密钥形状字段一律在写盘前被拒绝；损坏或含未知字段的文档读取时失败关闭（`FirstUseProgressError`），不会被静默解释成「还没有进度」。

**契约层**：`src/summit_everything/api/app.py` 新增

- `GET /api/v1/first-use/progress`：返回 `{step, completed, open}`；本机没有记录时返回 404 `first_use_progress_absent`——「还没有记录」是可区分的答案，不是默认值；
- `PUT /api/v1/first-use/progress`：写入并回显；读写失败通过新的 `FirstUseProgressError` handler 返回 503 `progress_unavailable`，不假装保存。

两者都要求活动工作库（无库时沿用 409 `workspace_not_open`）和会话 token。`web/openapi.json` 与 `web/src/api/generated.ts` 已同步，diff 为纯新增（+234 行、0 删除），未改动任何既有 schema。

**前端**：`web/src/components/firstUseProgress.ts` 现在只导出后端读写与一次性迁移；`loadFirstUseProgress` 把 404 `first_use_progress_absent` 映射为「无记录」，其余失败抛出；后端返回形状不合法时失败关闭，不会把看不懂的载荷当成进度。旧 localStorage 键只用于一次性迁移：后端已有记录时后端优先、不迁移；后端没有记录且旧副本形状合法时先写后端、成功后删除浏览器副本，此后不再有任何 localStorage 写入。

`App.tsx` 按本机记录决定落点：

- `completed` → 直接今日，不再打扰；
- 未完成且 `open` → 恢复到保存的那一步；
- 用户明确关闭过（`open: false`）→ 不自动出现，设置里仍可手动续接原步骤；
- 本机没有记录 → 新工作库，从第 2 步开始首次配置。

解析在读不出来时不猜结果：留在今日、明确提示失败，设置里仍能手动打开向导。**没有**按「有凭据」推断首次配置已完成，也**没有**新增自动打开上次工作库的行为；WKWebView nonPersistent 隔离保持不变。

`FirstUseWizard` 的步骤变化、关闭和完成现在都必须等 durable write 成功才动界面：写入失败时保留这一次跳转、停在原步骤、显示「这一步还没有保存到本机」并提供「重试保存」，绝不假装已保存或已关闭。密钥仍然只停留在组件内存，不进入任何持久化。

设置页「打开连接向导」由原来的固定第 2 步改为从本机记住的那一步续接（`resumeWizardStep`）；「连接 / 重新授权飞书」仍显式直达第 4 步。

## Developer 自测

先红后绿。红测在实现之前运行，日志与退出码保留在 `.local/dev/frontend-d-repair1/red/`。

| 检查 | 结果 | 原始证据 |
|---|---|---|
| 新增 store 单测（先红） | **RED**，exit 2（模块不存在，collection error） | `red/backend-store.log`、`red/backend-store.exit` |
| 新增 API 集成测试（先红） | **RED**，exit 1，7 failed | `red/backend-api.log`、`red/backend-api.exit` |
| 新增/改写 Web 测试（先红） | **RED**，exit 1，14 failed / 2 passed | `red/frontend.log`、`red/frontend.exit` |
| Python guarded pytest | **PASS**，**686 passed**，exit 0 | `green-python.log`、`green-python.exit` |
| Web 完整单测 | **PASS**，26 files、**220 passed、0 todo**，exit 0 | `green-web-final.log` |
| TypeScript (`tsc -b`) | **PASS**，exit 0 | `typecheck.log`、`static.exit` |
| Oxlint | **PASS**，exit 0；仍有 **2 条既存** React effect warning，无新增 | `lint.log`、`static.exit` |
| Vite build | **PASS**，exit 0；保留既存 >500 kB chunk 提示 | `build.log`、`static.exit` |
| Offline Playwright（含首配闭环与五档/深浅基线） | **PASS**，**2/2**，exit 0 | `green-e2e.log`、`green-e2e.exit` |
| `ruff check src tests` | **PASS**，exit 0 | `ruff-check.log`、`static.exit` |
| `ruff format --check src tests` | **PASS**，exit 0 | `ruff-format.log`、`static.exit` |
| `mypy src` | **PASS**，exit 0，47 source files | `mypy.log`、`static.exit` |
| `uv lock --check` | **PASS**，exit 0 | `uv-lock.log`、`static.exit` |
| Swift | **NOT_RUN（本轮未改 native）**；不继承 876 的 5/5 作为本轮结果 | — |

计数变化可核对：Web 由 876 的 204 增至 **220**（新增 16 条：`firstUseProgress.test.ts` +6、`FirstUseWizard.test.tsx` +3、新增 `App.firstUseProgress.test.tsx` 7 条）；Python 由 876 的 661 增至 **686**（新增 25 条：store 18、API 7）。876 的 204 / 661 / 十 mutation 属于旧 SHA，未在本轮重跑，不作为 repair1 证据。

三条 repair1 定向变异，每条都先破坏、确认红、再完整恢复（临时副本已删除，`git status` 干净）：

| 变异 | 破坏方式 | 结果 | 证据 |
|---|---|---|---|
| 01 | 重演 P1：`applyResolvedFirstUse` 无视本机记录，永远回向导第 2 步 | **RED**，exit 1，4 failed / 3 passed | `mutation/01-onopened-always-step2.log` |
| 02 | `FirstUseWizard.commit` 忽略写入失败，照样前进 | **RED**，exit 1，3 failed / 23 passed | `mutation/02-commit-ignores-write-failure.log` |
| 03 | `resolveFirstUseProgress` 跳过 durable 读取 | **RED**，exit 1，3 failed / 4 passed | `mutation/03-durable-read-ignored.log` |

本轮**没有**重跑 876 的全站视口矩阵与全部十条变异；受影响 E2E（首配闭环 + 五档/深浅基线）已重跑通过。

## 测试契约的显式更新

以下既有测试因新契约而被改写，改动都是**加强或等价**，没有删除用例、没有降低断言：

- `FirstUseWizard.test.tsx`：向导自己不再直接读写浏览器存储，持久化改为注入的 `persistProgress`；因此「步骤导航不产生任何请求」仍在断言 `fetchMock` 未被调用（向导本身不发请求），另新增 3 条用例断言「步骤变化先写本机」「写入失败停在原步骤并可重试」「关闭要等写入成功、失败时不报告已关闭」。
- 由于步骤切换现在要先等一次本机写入，若干既有用例中连点「稍后再说 / 上一步」的地方改为在每次点击后 `await` 目标步骤标题。这是真实行为变化（不再同步前进），不是放宽断言。
- `App.shell.test.tsx` 与 `App.test.tsx` 的 fetch 夹具补上了 `/api/v1/first-use/progress`：外壳夹具代表一个**已经配好**的工作库，因此返回 `{step: 5, completed: true, open: false}`。这使其余外壳断言含义不变。
- `web/e2e/first-use.spec.ts` 原先漏掉了新端点，被 catch-all 用 `[]` 应答；除补上真实的 GET/PUT 进度模拟外，客户端也据此加固为「载荷形状不合法即失败关闭」，不再静默接受。

## 未验证项与风险

- **Native WKWebView 同 profile 重启：NOT_RUN。** 本轮按用户决定不建包、不启动 GUI，因此原始 P1 的 native 复现环境没有被重新验证。本轮只证明「durable 存储 + 落点判定 + 失败可见」在 API/浏览器层成立；native 同 profile 重启仍需新候选独立复核。
- **新 macOS 候选/DMG：NOT_RUN。** 没有新的 App、DMG、package manifest、frontend/dependencies hash 或 build ID。876 的候选身份与 `.local/internal-builds/main-bce8843` 均原样保留。
- **pre-repair1 已配好的工作库会再看到一次向导。** 这类工作库既没有后端记录（旧版本没写过），重装后 WKWebView 里也没有浏览器副本，因此按「本机没有记录」处理会展示一次向导。这符合「不按『有凭据』猜测首次配置已完成」的约束；用户完成或明确关闭一次后，本机就有 durable 记录，之后不再打扰。
- **200% 浏览器菜单缩放与原生 `pageZoom`：NOT_RUN**（与 876 相同，未变化）。640 CSS px 仅是 reflow。
- 真实 provider / OAuth / 飞书 / Keychain / 用户材料 / 已安装 App / Developer ID 与公证 / 五日 / 双机 / 生产与发布：**未触碰、未测**。
- 读取进度失败时当前实现是「留在今日 + 提示 + 设置可手动打开向导」，失败场景下没有向导自动弹出；这是产品判断，测试只覆盖到「提示可见且不误报已完成」。

## Fresh QA 交接

请固定检查产品 SHA `faa1edd611a74dcdc26bff234de810bdf47761cb`（docs commit 不是受测产品 SHA），并在独立 worktree 复验：

1. 重跑 D 初次 QA 的还原路径：完成首次配置 → 同 profile/workspace 重启 → 手动打开已有工作库 → 直接 Today，不出现向导 step 2。浏览器 mock 用完成态记录独立复现；本机后端记录必须来自 GET/PUT 端点而不是浏览器存储。
2. 未完成且 `open` 的记录恢复到原 step；明确关闭的记录重启不自动弹、设置里手动续接原 step；「连接 / 重新授权飞书」直达第 4 步；无记录的新工作库从第 2 步开始。
3. 旧 localStorage 形状只迁移一次，迁移后浏览器副本被删除、后端成为唯一真源且无长期双写；非法形状不迁移。
4. store 的 profile/workspace 隔离、白名单与非法/密钥字段拒绝、原子性、并发写不损坏、损坏文档失败关闭、重启重读。
5. durable write 失败时：向导停在原步骤、失败可见、重试可用，且不显示完成/关闭成功；读失败留在今日且不误报。

QA 不应使用本轮 Developer 的 `.local/dev/frontend-d-repair1/` 临时 profile；本轮没有候选 App/DMG 可供 native 复验，native 同 profile 重启应如实记为 NOT_RUN 或由用户另行授权建包后单列。**Developer 自测不替代独立 QA 或 Sol gate。**
