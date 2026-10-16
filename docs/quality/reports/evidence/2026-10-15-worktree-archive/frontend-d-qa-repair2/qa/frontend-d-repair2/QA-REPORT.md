# 前端 UX 里程碑 D · repair2 · 独立 QA 报告

- 角色：**全新独立 QA**（GPT-6 Luna High 等效）。这是我第一次接触本里程碑的验收；上一轮 QA 的 PASS 只作为线索，不作为本轮结论依据。
- 日期：2026-10-15。
- **受测产品源码 SHA：`96fdf4d7cccfd71bd1719d4318e0e399309e8281`**（分支 `codex/frontend-ux-20261015`；提交标题 *fix: keep an opened configured workspace reachable and reject float steps*）。验收期间分支 tip 未移动，仍等于受测 SHA。
- 对照 SHA（非空性对照 / 修复前基线）：`faa1edd611a74dcdc26bff234de810bdf47761cb`（新建独立 worktree，同样自建 harness 实跑）。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2/SummitEverything`（`git rev-parse HEAD` 已核对）。
- 对照 checkout（仅用于「修复前」复现）：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2-parent/SummitEverything`。
- 全部 harness / 日志 / 截图 / 文本快照：`<QA checkout>/.local/qa/frontend-d-repair2/`（git ignored）。
- 我的 checkout `git status --porcelain` 为空（tracked 无改动）；开发者 worktree 我只读取，未写入，其 HEAD 仍为 `96fdf4d`、工作树干净。
- 未 push / merge / 删除任何 branch 或 worktree；未触碰真实 provider / OAuth / 飞书 / Keychain / 真实材料 / 已安装 App / 生产。

---

## 0. 判定

**FAIL（限定范围）——两条定点修复本身成立，但「必须独立验证 #5」的 OpenAPI/类型生成一致性门在本 SHA 上失败。**

精确范围：

| # | 项目 | 判定 | 说明 |
|---|---|---|---|
| 1 | **D-1**（工作库 gate 上抛用户意图；`open` 且无记录 → Today + 非阻塞提示，不再被 `.wizard-backdrop` 挡住） | **PASS** | 生产构建 + 真实 FastAPI + 真实后端新进程 + 全新 browser context 上全部成立；且同一 harness 在父 SHA `faa1edd` 上**精确复现修复前行为**（向导自动弹出、backdrop=1、Today 被遮罩拦截） |
| 2 | **D-4**（`FirstUseProgress.step` 严格整数校验；`3.0/2.0` 等整数值 JSON 浮点必须 422） | **PASS** | 真实 socket HTTP 上手写 JSON 逐条验证：7 种整数值浮点写法全部 422；bool/字符串/非整数/越界/null/数组/对象全部 422；真整数 2/3/4/5 全部 200 且落盘为 JSON 整数；OpenAPI 仍是 `integer enum [2,3,4,5]` |
| 3 | **P1 回归**（首配完成 → 真实后端新进程 + 全新 browser context → 手动打开已有工作库 → 直接 Today、无向导） | **PASS** | 本轮重新取证，未沿用上一轮结论 |
| 4 | **全部自动检查**（12 条命令，真实退出码） | **PASS** | 全部 exit 0；计数与开发者声称一致 |
| 5 | **OpenAPI 逐字节门** | **FAIL** | `web/openapi.json` 与 tracked **逐字节一致**；但 `openapi-typescript` 重生成后的 `web/src/api/generated.ts` **与 tracked 不一致**（+5 行 JSDoc 注释）。这正是仓库 CI `.github/workflows/m41-internal-app.yml` 的 `git diff --exit-code -- web/src/api/generated.ts` 步骤 → 在 CI 上应 exit 1。父 SHA `faa1edd` 上同一门 exit 0（对照证明是本轮引入） |

- **native WKWebView 同 profile 重启：本轮仍 NOT_RUN**（无新候选 App/DMG，未建包、未启动原生 GUI）。本报告的 D-1/P1 结论等价于「生产 Web 构建产物 + 真实后端进程重启 + 空浏览器存储」，**不能冒充 native 结论**。
- 我**无法在本会话内查看 PNG**（当前模型不支持图像输入）。所有结论都建立在 DOM 级断言、HTTP 响应、磁盘字节与文本快照（`screenshots-*/**.txt`）之上；PNG 仅供人工复核，**未经我视觉确认**。

---

## 1. 独立性与方法

自建两套 harness（本轮新写，未 import / 未运行开发者任何测试文件，也未复用上一轮 QA 的 harness 文件）：

1. `harness/qa_r2_http.py`（54 条断言）——自管 `uvicorn` 子进程，走**真实 TCP socket + 手写 JSON 字符串**（保证 `3.0` 真的以 `3.0` 上线），并读取真实落盘 `first-use-progress.json` 字节。
2. `harness/qa_r2_browser.mjs`（51 条断言）——Playwright 黑盒，自管后端与前端进程生命周期；「重启」= **杀掉后端进程并另起新进程** + **全新 browser context（storage 为空）**，最接近打包 App 的 nonPersistent 语义。前端跑**生产构建 `web/dist`**（`SUMMIT_QA_MODE=prod`，无 React StrictMode），并额外跑一遍 **vite dev server**（StrictMode 语义）作为次要轮。
   - `harness/qa_r2_app.py`：QA 自有 ASGI factory（真实 `create_app()`，隔离 profile root）。
   - `harness/qa_r2_static.mjs`：QA 自有静态服务 + `/api` 反向代理（注入 session token，与打包外壳一致）。

未触碰真实 provider / OAuth / 飞书 / Keychain / 用户真实材料 / 已安装 App / 生产；密钥后端由 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 强制不可用；隔离 profile root 在 `.local/qa/frontend-d-repair2/run-*/profile`。

### 1.1 非空性对照（本轮最关键的一条方法学证据）

同一份 `qa_r2_browser.mjs`（`SUMMIT_QA_ONLY=core,d1`），在生产构建上分别跑受测 SHA 与父 SHA：

| 检查 | 父 SHA `faa1edd` | 受测 SHA `96fdf4d` |
|---|---|---|
| G1.2 `create` → 向导第 2 步 | PASS | PASS |
| G2.7–G2.9 P1：重启后打开已配好的库 → Today、无向导 | PASS | PASS |
| G3.3 `open` 且无记录 → Today | **FAIL**（`wizard={"raw":"第 2 步 · 模型与密钥","step":2} today=false`） | PASS |
| G3.4 无 `.wizard-backdrop` 遮挡 Today | **FAIL**（`backdrop=1`） | PASS |
| G3.6 非阻塞提示 | **FAIL**（无 toast） | PASS |
| G3.8 主导航不被拦截 | **FAIL**（`navClickIntercepted=true`；Playwright 原文：`<div class="wizard-backdrop"> … intercepts pointer events`） | PASS |
| 小计 | **23 checks / 18 passed / 5 failed / exit 1** | 51/51 / exit 0 |

说明：父 SHA 上第 5 条失败是 harness 自身的终止错误（`TimeoutError: locator.click`，超时 30s），
原因正是同一件事——G3.8 之后要点回「今日」，而 `.wizard-backdrop` 持续拦截指针事件
（Playwright 原文：`<div class="wizard-backdrop">…</div> from <div class="main-shell">…</div> subtree intercepts pointer events`，
重试 62 次后超时）。因此产品行为失败是 4 条（G3.3 / G3.4 / G3.6 / G3.8），第 5 条是同因的harness 终止。
对照轮用的是 `SUMMIT_QA_ONLY=core,d1`（只跑 G1/G2/G3）。

→ 这排除了「harness 软弱、任何 SHA 都通过」的可能，并且**独立复现了 D-1 的修复前症状**（不依赖上一轮 QA 的结论）。父 SHA 上 G2 全绿也独立复现了「P1 在 `faa1edd` 已修好」。

### 1.2 证据处理纪律

本轮共有 3 次 harness 自身缺陷导致的失败运行，**每次的首次 raw 日志都先另存再修改 harness**，未覆盖：

- `logs/04-http-harness.failed-raw.log` — 我的断言误读错误信封（写成 `detail.code`，实际 API 是 `{"error":{"code":…}}`）；3 条 IUT 行为本身正确（409 `workspace_not_open` / 404 `first_use_progress_absent` / 503 `progress_unavailable`）。修 harness 后 54/54。
- `logs/01-03-browser-prod.failed-raw.log` — `step` 被 `if (want('core'))` 块级作用域遮蔽 → `ReferenceError`。27 通过。
- `logs/01-03-browser-prod.failed-raw-2.log` — 同类作用域问题（`created`）。29 通过。
- `logs/01-03-browser-prod.failed-raw-3.log` — 我的期望值差一（走完 2→3→4 后记录是 step 4，我断言 step 3）；产品行为正确。**这三条都是我的 harness bug，不是产品缺陷**，逐条对照后修正期望，最终 51/51。
- 通过态日志：`logs/01-03-browser-prod.log`（51/51，exit 0，主证据）、`logs/09-browser-prod-textdumps.log`（51/51，附带文本快照）、`logs/02-browser-dev.log`（51/51，exit 0）。

---

## 2. D-1 逐条判定（PASS）

场景复现方式：通过**真实 API**（`POST /api/v1/workspaces` mode=create，随后 `PATCH /api/v1/settings {"mode":"real"}`）造出「旧版本已配好、但本机从未有进度记录」的工作库——UI 全程未参与，因此记录确实不存在（`GET /first-use/progress` → 404）。然后重启后端进程 + 全新 browser context，用 UI 选「打开已有」。

| 要求 | 结果 | 证据 |
|---|---|---|
| `create`（新建）仍自动开始向导第 2 步 | **PASS** | 生产 `G1.2 landing=wizard step={"raw":"第 2 步 · 模型与密钥","step":2}`；`G5a.1` 用第二个库再验一次；dev 同样 |
| `open`（打开已有）无记录 → 落到今日 | **PASS** | `G3.3 wizard=null today=true` |
| 不再被 `.wizard-backdrop` 挡住今日 | **PASS** | `G3.4 backdrop=0`；`G3.8` 点击「项目」导航 `navClickIntercepted=false`；`G3.9` 点回「今日」成功 |
| 给出指向设置的非阻塞提示 | **PASS** | `G3.6`：`{"text":"这个工作库在本机还没有首次配置记录。需要配置真实模型或飞书时，可从设置里打开连接向导。 ✕","cls":"toast toast-neutral","role":"status"}`——中性色、`role=status`（不是 `alert`）、可关闭 |
| 提示不泄内部标识/路径/原始 JSON | **PASS** | `G3.7`、`G5g.1` 零命中；扫描正则覆盖 `sk-*`、`"step":N`、`first-use-progress.json`、`local_profile_dir`、`workspace_id`、绝对路径、`Bearer`、`request_id`、session token、profile/工作库根路径 |
| 仍不得按「有凭据」推断首配完成 | **PASS** | `G3.2` 工作库确实 `mode=real`（有配置）；`G3.5` 页面不含「首次配置已完成」；`G3.10`/`G3.11` 打开后记录仍 404 且**没有生成记录文件** |

文本快照（`screenshots-prod/06-g3-3-today-with-nonblocking-pointer.txt`）显示今日页完整渲染（导航 今日/审批/项目/知识问答/设置 全部在列），提示以页面末尾的 toast 形式出现，**没有任何 modal 遮罩**。

### 恢复闭环（PASS）

`G4.1–G4.7`：无记录工作库 → 设置可达 → 「打开连接向导」在步骤 2 打开 → 真实点击走到 5 → 记录 `{step:5,completed:true,open:false}` 落盘 → 重启 + 全新 context 再打开 → 直接 Today、无向导、**不再出现「没有记录」提示**（因为记录已存在）。

### 主动证伪（PASS，含 1 条新观察）

| 证伪目标 | 结果 | 证据 |
|---|---|---|
| 新建是否仍走向导 | PASS | `G1.2`、`G5a.1` |
| reload（已完成记录）是否合理且不误报 | PASS | `G5b.1` Today、无向导、无 backdrop；`G5b.2` **没有**误报「还没有首次配置记录」 |
| reload（记录存在但用户明确关闭过 `open:false`）是否误报 | PASS | `G5c.1–G5c.3` 落 Today、无向导、**提示不误触**（新增提示只在「无记录」时出现，未波及 `open:false` 分支） |
| reload（向导中途、尚无记录）行为 | **观察（新发现，见 §5 D-5）** | `G5d.2`：`wizard=null today=true`；`G5d.3` Today 可用、不被遮罩；`G5d.4` 不谎称完成；`G5d.5` **不写**假记录；`G5d.6` 设置里仍可手动开向导 |
| 老工作库是否真的不再被挡住今日 | PASS | `G3.3/G3.4/G3.8/G3.9` + 父 SHA 对照 |
| 向导第 4 步入口是否仍直达第 4 步 | PASS | `G5e.2 step={"raw":"第 4 步 · 飞书","step":4}` |
| 未完成 `open:true` 记录是否仍恢复原步骤（repair1 语义不回归） | PASS | `G5f.1–G5f.3`：记录 `{step:4,completed:false,open:true}`，重启后打开恢复到第 4 步 |
| dev / StrictMode 下提示是否重复 | PASS | `logs/02-browser-dev.log` G3.6 仍只有 **1** 条 toast |

---

## 3. D-4 逐条判定（PASS）

`harness/qa_r2_http.py`，真实 uvicorn + 真实 socket，`PUT /api/v1/first-use/progress` 手写 JSON body。

**必须 422（全部 422，且不落盘）**

| 载荷 | 结果 |
|---|---|
| `3.0` `2.0` `4.0` `5.0` `2e0` `3e0` `5.0e0`（整数值 JSON 浮点，含指数写法） | 全部 **422**（B3 组，7/7） |
| `3.5` `2.5` `4.5` `-4.0`（非整数/负浮点） | 全部 **422** |
| `true` `false`（bool 是 int 子类，必须显式排除） | 全部 **422** |
| `"3"` `"3.0"`（字符串） | 全部 **422** |
| `null` `[]` `{}` | 全部 **422** |
| `6` `1` `0` `-1`（越界整数） | 全部 **422** |
| `secret` / `api_key` / `path` 额外字段 | 全部 **422**，且密钥串未落盘（B7/B8） |
| 上述批次之后记录仍 404、文件不存在（fail-closed，不半写） | **PASS**（B5/B6） |

**必须 200**

| 载荷 | 结果 |
|---|---|
| `2` `3` `4` `5` | 全部 **200**，响应 `step` 是 JSON 整数（C1 组 4/4） |
| 落盘字节 | `"step": 5`，**无** `5.0`、无引号（C3） |

**失败关闭（新增覆盖）**

- 手工把记录文件写成 `{"step": 3.0, …}` → `GET` 返回 **503 `progress_unavailable`**（D1），**不会**被静默归一化成 3。
- `{"open": "yes"}` → 同样 **503**（D2）。

**OpenAPI**

- 活服务 `/openapi.json`：`FirstUseProgress.step` = `{"type":"integer","enum":[2,3,4,5],"title":"Step"}`，**无** `anyOf` / `number`（E1–E3）；`required=["step","completed","open"]`、`additionalProperties=false`（E4–E5）。
- `git diff faa1edd 96fdf4d -- web/openapi.json` 只有 1 行变化，正是随类文档生成的 `description`——与「只允许 description 变化」一致。

---

## 4. P1 回归（PASS，重新取证）

生产构建，完整闭环（`G1.2 → G2.1 → G2.2 → G2.3 → G2.4 → G2.5 → G2.7`）：

1. 新建工作库 → 向导第 2 步；
2. 真实点击走完 2→3→4→5→「完成并进入今日」→ Today；
3. 后端持有 `{step:5, completed:true, open:false}`，且是隔离 profile 目录里的真实文件；
4. **杀掉后端进程、另起新进程** + **全新 browser context**（storage 为空，`G2.5` 已断言）；
5. 重启后没有自动打开上次工作库（`409 workspace_not_open`，无回归）；
6. 手动「打开已有」同一工作库 → **落在 Today**，向导为 `null`，`.wizard-backdrop` 计数 0，全页无「第 2 步」标题。

dev（StrictMode）轮同样 51/51。另外，父 SHA 对照轮 `G2` 也全绿——说明本轮改动**没有**回退 repair1 已修好的 P1。

---

## 5. 缺陷 / 观察（最小复现与级别）

### D-6（**P2**，本轮新发现，自动门失败）`web/src/api/generated.ts` 与 `web/openapi.json` 失去同步 → 仓库 CI 门 exit 1

- 级别：**P2**。它是仓库自己 CI 里的一条硬门（`.github/workflows/m41-internal-app.yml` › *Web checks and API types*）：`npm --prefix web run api:types` 之后 `git diff --exit-code -- web/src/api/generated.ts`。本轮该步骤 **exit 1**。运行时类型形状**未变**（差异只是 `FirstUseProgress` 的 JSDoc 注释），因此无运行时影响——但门是失败状态。
- 最小复现（受测 SHA，我的独立 checkout，已还原）：
  ```sh
  cd <checkout>
  npm --prefix web run api:types
  git diff --exit-code -- web/src/api/generated.ts      # → exit 1（父 SHA faa1edd 上为 exit 0）
  git diff --stat                                        # → web/src/api/generated.ts | 5 +++++
  ```
- 实际差异（`logs/06b-openapi-ci-gate.log`、`logs/06-openapi.log`）：
  ```
  @@ -1753,6 +1753,11 @@ export interface components {
            *     rejected instead of having it silently stored on disk.
  +         *
  +         *     ``step`` is a real integer or nothing. ``Literal`` alone would let Pydantic's
  +         *     lax mode normalise an integral JSON float (``3.0``) into ``3``, so an
  +         *     out-of-contract payload would look accepted; the validator below closes that
  +         *     (independent QA finding D-4).
            */
           FirstUseProgress: {
  ```
- 独立对照（证明是本轮引入，不是既存）：
  | | `api:types` | `git diff --exit-code -- web/src/api/generated.ts` |
  |---|---|---|
  | 父 SHA `faa1edd` 独立 worktree | exit 0 | **exit 0**（`logs/06c-openapi-ci-gate-parent.log`） |
  | 受测 SHA `96fdf4d` | exit 0 | **exit 1**（`logs/06b-openapi-ci-gate.log`） |
- 相关字节（我的 checkout，已还原到 tracked）：
  - `web/openapi.json` sha256 `87248b307b51ef1ece6a83664f94c2dce449272ff0640fb201bb9cd69ed6d98b`（重生成后 `cmp` 逐字节相同）
  - `web/src/api/generated.ts` sha256 `396613c3915639dd2c8385818148aa35ddaed065d8e96fd11085030d262fb80d`（**与重生成结果不同**；重生成结果 sha256 `bb4ad789ea4152989e394f06e96a23892dbde5038b6aefcb95ff2eed4c25027b`）
- 注意：`git status` 在**未运行**生成器时是干净的（tracked 与工作区一致）；「运行后 git status 应干净」这句只在跑完 `api:types` 的语境下才有意义，而那个语境下它是**脏**的。
- 收口代价：一条 `npm --prefix web run api:types` + 重新固定 SHA + 再走一轮 fresh QA（或 Sol 明确判定该注释漂移可不阻塞里程碑，但需记录为例外）。

### D-5（P3，新观察）新建工作库后在「向导尚未推进」时 reload/重启，会退出向导落到今日

- 级别：**P3**（不丢数据、不阻塞、可自愈，且有明确指引）。
- 最小复现（生产构建）：新建工作库 → 向导出现第 2 步（**不要**点任何按钮，此时后端无记录）→ `page.reload()`（等价于打包 App 退出后重新打开并 `GET /workspaces/current` 命中的那条路径）。
- 观察：`wizard=null`、落到 Today、出现同一条「还没有首次配置记录」中性提示；后端记录**仍为 404**（不写假进度），设置里仍可手动打开向导并正常走完（`G5d.1–G5d.6`）。
- 判断依据：`App.connect()` 一律按 `mode='open'` 处理（代码注释：「页面重载时工作库已经开着」）。**create 意图没有被持久化**，所以重载后无法区分「刚新建、正在首配」与「打开一个旧版本配好的库」。
- 为什么算观察而不算缺陷：提示文字为真（确实没有记录），Today 完全可用，恢复路径存在。**但它是相对父 SHA 的行为变化**：父 SHA 上同一场景 reload 后会重新出现向导第 2 步（用户留在首配流程里）。也就是说，D-1 的修复把一个「新建后中途退出」的场景从「回到向导」改成「落到今日 + 提示」。
- 建议：若产品希望「首配未完成的新建库」在重启后仍续接向导，需要在创建时持久化一个意图标记（例如把 step 2 立即写盘，或单独记录首次使用意图），否则这是设计取舍而非 bug。

### D-7（INFO）修复提交未同步更新交接文档

- `docs/handoff/NEXT-FRONTEND-D-REPAIR1.md`（`96fdf4d` 处的版本）仍把 D-1 写成「**待用户决议（P3，非回归）**」、把 D-4 写成「**可选小修（INFO）**」，而同一 SHA 的产品代码已经实现了这两项。
- docs 不属于受测产品 SHA，不影响产品判定；但会让「固定 SHA 的自述」与代码不一致，建议下一提交一并纠正。

---

## 6. 真实计数与退出码（全部由我本轮重跑）

| 命令 | 真实结果 | 退出码 | 日志 |
|---|---|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | **692 passed**, 1 warning, 84.17s | **0** | `logs/07-pytest.log` |
| `npm --prefix web test -- --run` | 26 files, **222 passed**, **0 todo / 0 skipped** | **0** | `logs/07-vitest.log` |
| `npm --prefix web run typecheck` | 无输出（clean） | **0** | `logs/07-typecheck.log` |
| `npm --prefix web run lint` | **2 warnings / 0 errors**（`react(set-state-in-effect)`：`App.tsx:124`、`ProjectsView.tsx:62`）。父 SHA 独立复核为同样 2 条、行号 `App.tsx:113` / `ProjectsView.tsx:62` → 仅因本轮新增 11 行而上移，**均为既存、非本轮引入** | **0** | `logs/07-lint.log`、`logs/07-lint-parent-faa1edd.log` |
| `npm --prefix web run build` | 303 modules，`index-CJV7PXqW.js` 591.47 kB，既存 >500 kB 提示 | **0** | `logs/07-web-build.log` |
| `npm --prefix web run test:e2e` | **2 passed**（`first-use.spec.ts`、`viewport.spec.ts`），12.7s | **0** | `logs/07-e2e-default.log` |
| `npm --prefix web run test:e2e:integration` | **1 passed**（`approval-today.spec.ts`），3.6s | **0** | `logs/07-e2e-integration.log` |
| `uv run ruff check src tests` | All checks passed | **0** | `logs/07-ruff-check.log` |
| `uv run ruff format --check src tests` | 100 files already formatted | **0** | `logs/07-ruff-format.log` |
| `uv run mypy src` | Success, **47 source files** | **0** | `logs/07-mypy.log` |
| `uv lock --check` | Resolved 48 packages | **0** | `logs/07-uv-lock.log` |
| `uv sync --locked --group dev` / `npm --prefix web ci` | 成功 | **0 / 0** | `logs/00-uv-sync.log`、`logs/00-npm-ci.log` |
| **OpenAPI 逐字节门** | `openapi.json` **IDENTICAL**；`generated.ts` **DIFFER**（+5 行） | **0 / 1** | `logs/06-openapi.log`、`logs/06b-openapi-ci-gate.log`、对照 `logs/06c-openapi-ci-gate-parent.log` |

**与开发者声称的差异：**

- Python **692 passed** → **一致**（我独立得到 692 / exit 0）。
- Web **222 passed / 0 todo** → **一致**。
- 默认 e2e **2**、集成 e2e **1**、lint **2 warnings / 0 errors** → **全部一致**。
- **未声称但失败的一项**：`generated.ts` 与 `openapi.json` 的一致性（见 D-6）。开发者的提交信息写「OpenAPI 仍是 integer enum，只有随类文档生成的 description 更新」——对 `web/openapi.json` 而言准确，但**遗漏了派生产物 `web/src/api/generated.ts` 没有一起重生成**，而仓库 CI 恰好用 `git diff --exit-code` 卡这一条。

---

## 7. NOT_RUN / UNVERIFIED

**NOT_RUN（不得用本轮结果冒充）**

1. **native WKWebView 同 profile 重启**：NOT_RUN。本轮无新候选 App/DMG，未建包、未启动原生 GUI、未用 CUA。原始 P1 被观察到的 native 路径**没有被重新验证**。
2. 新 macOS 候选 App / DMG / package manifest / frontend 与 dependencies hash / build ID：NOT_RUN（无新产物）。
3. 真实 provider 调用、真实飞书 OAuth/回调、真实 Keychain、真实用户材料、已安装 App、Developer ID 与公证、五日、双机、生产发布：NOT_RUN / 未触碰。
4. 200% 浏览器菜单缩放与原生 `pageZoom`：NOT_RUN。
5. Swift / native 侧检查：NOT_RUN（本轮未改 native，我也未跑 `swift test`）。
6. `frontend-c-flow.spec.ts`、`frontend-c-view.spec.ts`、`first-use-real.spec.ts`：不在默认 e2e `testMatch` 内，NOT_RUN。
7. 全站视口矩阵、876 的「十条变异」：未重跑（属旧 SHA 的旧证据）。
8. **PNG 截图的视觉判读**：NOT_RUN。17 张 prod + 17 张 dev 截图已生成，但本会话模型**不支持图像输入**，我未做也不声称做过视觉确认；我实际读取过的是 prod 轮 17 份 DOM 文本快照（`screenshots-prod/*.txt`）。

**UNVERIFIED**

- 「打包进 DMG 后 WKWebView 的 `nonPersistent` 存储确实丢弃 localStorage、而 `local_profile_dir` 仍持久」——这是整个 repair1 的前提假设。我用「全新 browser context（storage 为空）+ 真实后端新进程 + 磁盘上真实记录」**建模**了它，但**没有**在真实 WKWebView 里直接验证该存储语义。
- 真实 macOS Keychain 可用/不可用两条分支下的向导行为：仅覆盖 `SUMMIT_OFFLINE_GUARD_ACTIVE=1`（密钥后端不可用）分支。
- 并发写只覆盖到 HTTP 单写序列；未做多进程并发写、断电注入等压力验证（沿用上一轮范围，本轮未重跑）。
- 同一工作库多窗口同时改步骤的语义：未测。

---

## 8. 对开发者表述的核对与指正

1. **计数全部成立**：692 / 222 / 0 todo / e2e 2 / 集成 1 / lint 2 warnings 0 errors，均由我独立重跑复现，零差异。
2. **「OpenAPI 只有 description 变化」需要补一句**：`web/openapi.json` 确实只变了 description；但派生的 `web/src/api/generated.ts` **没有一起重生成**，导致仓库 CI 的 `git diff --exit-code -- web/src/api/generated.ts` 在本 SHA 上 exit 1（父 SHA exit 0）。这是 D-6。
3. **「新建工作库仍自动开始向导（首次使用语义不变）」需要限定**：在**点击创建的那一刻**成立；但 create 意图未持久化，`App.connect()` 一律按 `open` 处理，所以「新建后未推进就 reload / 重启」会落到今日 + 提示（D-5）。若这是有意取舍，建议在报告/文档中显式写出；若产品要求续接，则需持久化意图。
4. **D-1 的修复方向与措辞一致**：把意图上抛、无记录时 `open` 不再 modal 遮挡 Today、仍不按凭据推断完成——这三点我都独立证实，且父 SHA 对照证明修复前确实是「向导挡住今日」。
5. **未发现开发者把未测写成已测**：native / DMG / 真实凭据 / 缩放都仍标注为未做，与我独立结论一致。
6. **docs 提交不是受测 SHA**：`96fdf4d` 本身只改 8 个文件（1 个 Python 模块、2 个测试、`web/openapi.json`、4 个前端文件），无 docs；但交接文档在同一个 SHA 上仍写着 D-1「待用户决议」、D-4「可选小修」（D-7）。

---

## 9. 证据索引

`<QA checkout>/.local/qa/frontend-d-repair2/`（另有 `EVIDENCE-MANIFEST.sha256` 逐文件校验）：

- `harness/qa_r2_http.py` — HTTP/socket 黑盒 harness（54 断言，自建）
- `harness/qa_r2_browser.mjs` — Playwright + 进程重启黑盒 harness（51 断言，自建；含 `SUMMIT_QA_ONLY` 子集开关供对照轮）
- `harness/qa_r2_app.py`、`harness/qa_r2_static.mjs` — 自建 ASGI factory 与生产产物静态服务/代理
- `logs/04-http-harness.log` — **主证据**：54/54，exit 0
- `logs/01-03-browser-prod.log` — **主证据**：prod 51/51，exit 0
- `logs/02-browser-dev.log` — dev/StrictMode 51/51，exit 0
- `logs/09-browser-prod-textdumps.log` — prod 51/51（附带 17 份 `screenshots-prod/*.txt` 文本快照）
- `logs/08-parent-faa1edd-control.log` — **非空性对照**：父 SHA D-1 组 5 FAIL / exit 1
- `logs/06-openapi.log`、`logs/06b-openapi-ci-gate.log`、`logs/06c-openapi-ci-gate-parent.log` — 逐字节门与 CI 等价门（含父 SHA 对照）
- `logs/0*-*.failed-raw*.log` — 三次 harness 自身缺陷的**未覆盖原始失败日志**
- `logs/07-*.log` — pytest / vitest / typecheck / lint / build / e2e / e2e-integration / ruff / mypy / uv lock
- `run-prod/results.json`、`run-dev/results.json`、`run-http/results.json` — 逐条断言与 detail
- `screenshots-prod/01..17-*.png`（17 张）+ 同名 `*.txt`（17 份 DOM 文本快照）— 每个关键步骤的截图与可读文本（PNG 未经我视觉判读）
- `screenshots-dev/01..17-*.png`（17 张，dev 语义）— 该轮在我的文本快照补丁之前运行，故**无** `.txt`
- `logs/07-lint-parent-faa1edd.log` — 父 SHA 的 lint 复核（2 warnings / 0 errors，用于证明既存性）
- `tracked-openapi.json.bak`、`tracked-generated.ts.bak`、`tracked-product-bytes.sha256` — 逐字节门运行前后 tracked 字节与还原凭据

## 10. 复现指令（自建 harness）

```sh
QA=/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2/SummitEverything
cd "$QA"
uv sync --locked --group dev
npm --prefix web ci

# A. HTTP / socket 黑盒（54 断言）
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python \
  .local/qa/frontend-d-repair2/harness/qa_r2_http.py

# B. 浏览器 + 真实后端重启（51 断言）
npm --prefix web run build
# harness 通过 harness/node_modules -> web/node_modules 软链解析 playwright（隔离、ignored）
ln -sfn "$QA/web/node_modules" .local/qa/frontend-d-repair2/harness/node_modules
cd web
SUMMIT_QA_MODE=prod node ../.local/qa/frontend-d-repair2/harness/qa_r2_browser.mjs   # 生产构建
node ../.local/qa/frontend-d-repair2/harness/qa_r2_browser.mjs                       # vite dev

# C. 非空性对照（在 faa1edd 的独立 worktree 里，用同一 harness）
P=/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2-parent/SummitEverything
cd "$P/web" && SUMMIT_QA_MODE=prod SUMMIT_QA_ONLY=core,d1 node \
  ../.local/qa/frontend-d-repair2/harness/qa_r2_browser.mjs

# D. OpenAPI / CI 等价门
cd "$QA" && npm --prefix web run api:types && git diff --exit-code -- web/src/api/generated.ts
```

harness 在 8811 / 5211 与 8801 上自管 uvicorn 与前端进程，启动前拒绝复用已占用端口；每次运行使用一次性隔离 profile root（`.local/qa/frontend-d-repair2/run-<mode>/profile`），不触碰真实 `~/Library/Application Support/SummitEverything`。

## 11. 环境与 SHA 核对

- 受测 checkout `HEAD == 96fdf4d7cccfd71bd1719d4318e0e399309e8281` ✔；`git status --porcelain` 空 ✔（含逐字节门运行后的还原）。
- 对照 checkout `HEAD == faa1edd611a74dcdc26bff234de810bdf47761cb` ✔；工作树无 tracked 改动 ✔。
- 分支 `codex/frontend-ux-20261015` 的 tip 在验收全程保持 `96fdf4d` ✔；`git diff --stat 96fdf4d <tip> -- src web tests` 为空。
- 开发者 worktree `/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`：HEAD `96fdf4d`、`git status --porcelain` 空；我只读取，未写入 ✔。
- `uv.lock` / `pyproject.toml` 在 `faa1edd..96fdf4d` 之间无 diff。
- 我创建的两个 worktree（受测、对照）与被测目标均未被删除或移动；未 push / merge。
