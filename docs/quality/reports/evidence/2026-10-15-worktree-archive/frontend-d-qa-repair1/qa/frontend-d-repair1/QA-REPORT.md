# 前端 UX 里程碑 D 修复轮 1 · 独立 QA 报告

- 角色：全新独立 QA（GPT-6 Luna 等效），**无开发者上下文**，从零取证。
- 日期：2026-10-15。
- 受测产品源码 SHA：`faa1edd611a74dcdc26bff234de810bdf47761cb`（分支 `codex/frontend-ux-20261015`）。
- 对照（初次 QA FAIL/P1 的父 SHA）：`876008e1d33420f57fb31772c76e471379e6b98d`。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1/SummitEverything`（`git rev-parse HEAD` 已核对）。
- 对照 checkout（仅用于「修复前」复现，本报告中所有 876008e 结论都出自这里）：
  `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1-parent/SummitEverything`。
- 全部证据、harness、原始日志：`<QA checkout>/.local/qa/frontend-d-repair1/`（git 忽略目录）。
- 两个 QA checkout 与开发者 worktree 的 `git status --porcelain` 均为空；**产品源码未被修改**（见 §9 核对）。

## 0. 判定

**PASS**，适用范围如下（精确边界）：

- ✅ 初次 P1 的**修复在产品代码层成立**：在**真实 FastAPI + 真实 WebUI（生产构建产物）**上，「完成首次配置 → 后端进程重启 + 浏览器存储清空（同 profile、同一工作库）→ 手动打开已有工作库」直接落到 Today，向导与「第 2 步 · 模型与密钥」都不再出现。
- ✅ **同一份 QA harness 在父 SHA 876008e 上复现 P1（exit 1）**，在受测 SHA 上全绿（exit 0）。这排除了「harness 本身软弱、无论如何都通过」的可能。
- ✅ 首次配置进度的 durable 真源、落点判定、迁移、失败可见、契约与 CI 门（OpenAPI 逐字节）在 API/浏览器层全部独立复验通过。
- ⚠️ **native WKWebView 同 profile 重启 = NOT_RUN**（本轮无新候选 App/DMG，未建包、未启动 GUI）。本轮结论等价于「生产 Web 构建产物 + 真实后端 + 空浏览器存储」，**不能冒充 native 结论**。
- ⚠️ 1 条**残余缺陷级观察**（P3，开发者报告已自我声明）：在 repair1 之前就已配好、且本机没有任何进度记录的工作库，升级后仍会被拉进向导第 2 步一次（关掉即自愈）。见 §6 D-1。

## 1. 独立性与方法

- 自建两套 harness，**没有运行、没有 import 开发者任何测试文件**：
  1. `harness/qa_first_use_harness.py` — 直接驱动真实 `create_app()`（隔离 `profile_root`）走真实 HTTP 面，并检查真实落盘文档。33 条断言。
  2. `harness/qa_p1_restart.mjs` + `harness/qa_app.py` + `harness/qa_static_proxy.mjs` — 自管进程生命周期的 Playwright 黑盒：真实 uvicorn（真实产品 app，隔离 profile root，`SUMMIT_OFFLINE_GUARD_ACTIVE=1`）+ 真实 WebUI；「重启」= **杀掉后端进程并另起一个新进程** + **全新 browser context（存储为空）**。64 条断言。
- `qa_p1_restart.mjs` 支持两种前端形态，两种都跑了：
  - `SUMMIT_QA_MODE=prod`：服务 `web/dist`（`npm run build` 产物）并代理 `/api` —— **最接近打包 App**（生产构建，没有 React StrictMode 的双调用）。
  - `SUMMIT_QA_MODE=dev`：vite dev server（dev 语义，React StrictMode）。
- 未触碰真实 provider / OAuth / 飞书 / Keychain / 用户真实材料 / 已安装 App / 生产。密钥后端由 offline guard 强制为不可用。
- 未 `push` / `merge` / 删除任何既有 branch 或 worktree；未触碰开发者 worktree。

## 2. 最有价值的一条证据：同一 harness 的修复前 / 修复后对照

| | 父 SHA `876008e`（生产构建） | 受测 SHA `faa1edd`（生产构建） |
|---|---|---|
| 同 profile 重启 → 打开已有工作库 | **向导「第 2 步 · 模型与密钥」**，`today=false` | **Today**，向导不出现 |
| 结果 | 20 checks / 12 passed / **8 failed**，**exit 1**（P1 复现后 harness 卡死中止） | 64 checks / **64 passed**，**exit 0** |
| 日志 | `logs/08-parent-876008e-comparison.log` | `logs/01-02-03-05-browser-and-e2e.log` |
| 截图 | `parent-876008e-evidence/P1-reproduced-wizard-step2-after-reopen.png` | `screenshots-prod/05-s1-12-today-after-restart-reopen.png` |

父 SHA 上的关键失败行：

```
[FAIL] S1.12 ***P1 CORE*** reopening an already-configured workspace after restart lands on Today
       :: wizard={"raw":"第 2 步 · 模型与密钥","step":2} today=false
[FAIL] S1.13 ***P1 CORE*** the wizard is NOT shown on open :: wizard={"raw":"第 2 步 · 模型与密钥","step":2}
[FAIL] S1.7  backend holds the completed record :: status=404 body={"detail":"Not Found"}
[FAIL] S2.4  restart + reopen of an explicitly-closed workspace shows Today with no wizard
       :: today=false wizard={"raw":"第 2 步 · 模型与密钥","step":2}
```

受测 SHA 上的对应通过行（prod）：

```
[PASS] S1.12 ***P1 CORE*** reopening an already-configured workspace after restart lands on Today
       :: wizard=null today=true
[PASS] S1.13 ***P1 CORE*** the wizard is NOT shown on open :: wizard=null
[PASS] S1.14 no "第 2 步 · 模型与密钥" heading exists anywhere after reopening
[PASS] S1.7  backend holds the completed record {step:5,completed:true,open:false}
```

## 3. 逐项判定

| 项 | 判定 | 证据 |
|---|---|---|
| ① 重演 P1 并确认已修复（真实后端 + 生产 Web 构建） | **PASS** | `logs/01-02-03-05-browser-and-e2e.log`（S1.1–S1.15）；`screenshots-prod/01..05`；对照 `logs/08-…` |
| ② 未完成 `open` 恢复原 step；明确关闭重启不弹、设置手动续接；飞书直达第 4 步；无记录从第 2 步 | **PASS** | 同上（S2.1–S2.5、S3.1–S3.2、S4.1、S5.1） |
| ③ 旧 localStorage 一次性迁移、迁移后删除、无长期双写、非法形状不迁移 | **PASS** | 同上（S6.1–S6.5、S7.1–S7.3、S8.1–S8.3）；`src` 中已无 `localStorage.setItem`（仅主题键 `sx:theme-preference`） |
| ④ store：profile/workspace 隔离、白名单、拒绝非法与密钥字段且不落盘、原子写、并发不损坏、损坏失败关闭、新进程重读 | **PASS** | `logs/04-05-06-http-harness.log`（A5–A13、B1–B6、C1–C2、D1–D5、E1–E5、F1；33/33）；新进程重读另由浏览器 harness 的真实 uvicorn 重启（S1.9–S1.13、C 组）覆盖 |
| ⑤ durable write 失败停在原步骤、失败可见、可重试、不显示完成/关闭成功；读失败留在今日、不误报完成、设置仍可手动开向导 | **PASS** | 浏览器 harness S9.2–S9.12、S10.1–S10.6；截图 `14..19` |
| ⑥ 契约：无 token 401 / 无活动工作库 409；状态码与错误码；OpenAPI 与 generated.ts 与 `export_openapi.py` 逐字节一致 | **PASS** | `logs/04-05-06-http-harness.log` A1–A4；`logs/06-openapi.log`；sha256 见 §4 |
| ⑦ 独立重跑全部自动检查并记录真实退出码 | **PASS** | `logs/07-*.log`、`logs/01-02-03-05-browser-and-e2e.log`；真实数字见 §4 |
| ⑧ 主动证伪 | **PASS（有 3 条残余观察）** | S1.9、S8.1、S10.1–S10.3、S11.1–S11.2、S12.1–S12.7、A13、S7.3；残余见 §6 |

### ③ 的机制级补充
`loadFirstUseProgress` 把 404 `first_use_progress_absent` 映射为「无记录」，其他失败抛出；后端已有记录时**根本不读**浏览器副本（S8.1/S8.3 证明后端记录胜出且旧副本原样保留）；迁移写入成功后才 `removeItem`（S6.4）。生产构建下迁移**恰好一次 PUT**（trace `["-> GET","<- 404","-> PUT","<- 200"]`）。

### ⑤ 的机制级补充
写失败注入方式：在真实后端上把该工作库的 `local_profile_dir` `chmod 0500`，让真实 store 抛 `OSError` → 真实 503 `progress_unavailable`。结果：向导停在原步骤、`role="alert"` 显示「这一步还没有保存到本机…」、「重试保存」出现、`p.settings-notice` 计数为 0（**没有成功提示**）、后端文件不存在；恢复权限后重试前进到第 3 步。关闭路径同样：失败时不关闭、不写 `open:false`、不到 Today。读失败注入方式：往真实记录文件写半截 JSON，重启后重新打开 → 留在 Today、`role="alert"` 提示、**不声称已完成**、设置里仍能手动打开向导。

## 4. 真实计数与退出码（全部由我本轮重跑）

命令与日志：`logs/07-pytest.log`、`logs/07-vitest.log`、`logs/07-web-static-build.log`、`logs/07-python-static.log`、`logs/01-02-03-05-browser-and-e2e.log`。

| 命令 | 真实结果 | 退出码 |
|---|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | **686 passed**, 1 warning, 82.83s | **0** |
| `npm --prefix web test -- --run` | 26 files, **220 passed**, **0 todo / 0 skipped** | **0** |
| `npm --prefix web run typecheck` | 无输出（clean） | **0** |
| `npm --prefix web run lint` | **2 warnings / 0 errors**（均 `react(set-state-in-effect)`：`App.tsx:113`、`ProjectsView.tsx:62`） | **0** |
| `npm --prefix web run build` | 303 modules，`index-9bp8hJZU.js` 591.23 kB，既存 >500 kB 提示 | **0** |
| `npm --prefix web run test:e2e` | **2 passed**（`first-use.spec.ts`、`viewport.spec.ts`），12.5s | **0** |
| `uv run ruff check src tests` | All checks passed | **0** |
| `uv run ruff format --check src tests` | 100 files already formatted | **0** |
| `uv run mypy src` | Success, **47 source files** | **0** |
| `uv lock --check` | Resolved 48 packages | **0** |

**与开发者声称的差异：无。** 开发者声称 Web **220 passed / 0 todo**、Python **686 passed**，我独立重跑得到完全相同的数字与 exit 0。lint 的 2 条 warning 我也在父 SHA `876008e` 上重跑 `npm --prefix web run lint` 确认同样存在（`Found 2 warnings and 0 errors`），即**确为既存、非本 SHA 新增**。

### OpenAPI CI 门（逐字节）
```
web/openapi.json            sha256 6b4a0e95dcea557abfc346530e8c70714ab770c4ad0293ae3b2aba1ab9b0c5e4
web/src/api/generated.ts    sha256 396613c3915639dd2c8385818148aa35ddaed065d8e96fd11085030d262fb80d
uv run python scripts/export_openapi.py   → EXIT=0（Wrote web/openapi.json）
cmp 重生成后的 openapi.json 与 tracked → IDENTICAL bytes
npx openapi-typescript openapi.json -o <tmp>  与 tracked generated.ts → IDENTICAL bytes
运行后 git status --porcelain → 空
```
另外独立核对 diff 形状：`web/openapi.json` **+131/−0**、`web/src/api/generated.ts` **+103/−0**；新增 1 个 path（`/api/v1/first-use/progress`）、1 个 schema（`FirstUseProgress`），**无删除、无既有 path/schema 改动**。开发者报告写的「+234 行、0 删除」成立。
（我是在自己的隔离 checkout 里先备份 tracked 字节、跑完再还原的；事后 `git diff` 为空、sha256 与 `HEAD` 中的字节一致。）

## 5. 关键原始证据索引

`<QA checkout>/.local/qa/frontend-d-repair1/`：

- `harness/qa_first_use_harness.py` — HTTP/store 黑盒 harness（自建）
- `harness/qa_p1_restart.mjs` — 浏览器 + 进程重启黑盒 harness（自建）
- `harness/qa_app.py` — 自建 ASGI factory（真实 app，隔离 profile root）
- `harness/qa_static_proxy.mjs` — 生产产物静态服务 + `/api` 代理（自建）
- `logs/01-02-03-05-browser-and-e2e.log` — **主证据**：prod 64/64 → dev 64/64 → repo e2e 2/2，全部 exit 0
- `logs/04-05-06-http-harness.log` — HTTP/store harness 33/33，exit 0
- `logs/06-openapi.log` — OpenAPI / 浏览器类型逐字节一致
- `logs/07-*.log` — pytest / vitest / typecheck / lint / build / ruff / mypy / uv lock
- `logs/08-parent-876008e-comparison.log` — 父 SHA P1 复现，exit 1
- `screenshots-prod/01..23-*.png` — 受测 SHA 每步截图（prod 构建）
- `screenshots-dev/01..23-*.png` — 同上（dev server）
- `parent-876008e-evidence/` — 父 SHA 的 P1 复现截图与 `results.json`
- `run-prod/results.json`、`run-dev/results.json` — 逐条断言与 detail（含请求 trace）
- `logs/archive-harness-iteration-superseded.log` — harness 自身修正过程中的中间运行，**不作为结论证据**

## 6. 缺陷 / 残余风险（含最小复现与级别）

### D-1（P3，残余，开发者报告已声明）升级前已配好的工作库会再看到一次向导，且这一步挡住 Today
- 级别：P3（一次性、无数据损失、可自愈）。不是修复引入的回归：父 SHA 上同样如此，且父 SHA 连「关闭后不再弹」都做不到。
- 最小复现（受测 SHA，prod 构建）：
  1. 新建工作库 → 向导第 2 步；不要点任何按钮（**不要**按「关闭向导」，否则会写入 `open:false`）。
  2. 重启后端进程 + 用全新 browser context 打开该已有工作库。
  3. 观察：向导自动出现在「第 2 步 · 模型与密钥」，`today=false`。
  4. 尝试点左侧「今日」导航：被 `.wizard-backdrop` 拦截（`navClickIntercepted=true`），**不关向导就到不了 Today**。
  5. 点「关闭向导」→ Today，后端写入 `{step:2,completed:false,open:false}`；此后再重启 + 打开 → 直接 Today（自愈，不再复现）。
- 证据：`screenshots-prod/20-s12-4-*.png`、`21-s12-5-*.png`、`22-s12-6-*.png`、`23-s12-7-*.png`；`logs/…` S12.1–S12.7。
- 说明：这与「不按『有凭据』猜测首配完成」的既定约束一致，属于设计取舍。但**用户可见后果比开发者报告写得更重**：报告只说「会展示一次向导」，没有说明这一步在关闭前**挡住 Today**（模态遮罩覆盖主导航）。如果 Sol 的门要求「老工作库不得被再次 onboarding」，这就是 P2 级 follow-up。

### D-2（P3，dev 语义专属）React StrictMode 下旧 localStorage 迁移会发两次相同 PUT
- 级别：P3 / 环境专属，**不影响打包产物**。
- 最小复现：vite dev server（React StrictMode）下，给一个无后端记录的工作库预置合法旧 localStorage 记录后刷新页面。
- 观察到的请求 trace：`["-> GET","<- 404","-> PUT","<- 404","-> PUT","<- 200","<- 200"]`（**2 次 PUT，载荷逐字节相同**）。
- 生产构建（`web/dist`）同一场景：`["-> GET","<- 404","-> PUT","<- 200"]`，**恰好 1 次 PUT**。
- 影响：载荷相同且写入幂等，不产生错误状态、不损坏文档；但严格意义上「只迁移一次」在 dev 语义下不成立。开发者报告的「一次性迁移」表述需要限定在生产构建语义下。
- 证据：`logs/…` prod S6.3 vs dev S6.3。

### D-3（INFO）OpenAPI 未描述 401 / 404 / 503 响应
新端点只在文档里声明 `200` 与 `422`；实际存在的 `401 unauthenticated`、`404 first_use_progress_absent`、`503 progress_unavailable` 只体现在行为与报告文字里。功能正确，但契约文档不完整。证据：`logs/06-openapi.log` 中打印的新 path 片段；行为证据 A1–A5、D1、D4。

### D-4（INFO）整数型 JSON 浮点 `3.0` 被 Literal 强制转换接受
`PUT {"step":3.0,...}` 返回 200 并在**落盘前归一化为 JSON 整数 3**（`"step": 3`）；`1/0/6/"3"/2.5/null/true/-1/4.5` 均 422。产品面不可达（前端只发 2/3/4/5），不构成实际风险，仅记录契约边界。
证据：`logs/04-05-06-http-harness.log` A9 / A9b。

## 7. NOT_RUN（不得用本轮结果冒充）

1. **native WKWebView 同 profile 重启**：NOT_RUN。本轮无新候选 App/DMG，未建包、未启动原生 GUI。原始 P1 被观察到的那条 native 路径**没有被重新验证**；本轮只证明「生产 Web 构建产物 + 真实后端 + 空浏览器存储」成立。
2. 新 macOS 候选 App / DMG / package manifest / frontend 与 dependencies hash / build ID：NOT_RUN（本轮无新产物）。
3. 真实 provider 调用、真实飞书 OAuth/回调、真实 Keychain、真实用户材料、已安装 App、Developer ID 与公证、五日、双机、生产发布：NOT_RUN / 未触碰。
4. 200% 浏览器菜单缩放与原生 `pageZoom`：NOT_RUN（与 876 相同，未变化）。
5. Swift 相关检查：NOT_RUN（本轮未改 native）。
6. 876008e 的全站视口矩阵与开发者自述的「十条变异」：未重跑（属旧 SHA 的旧证据）。

## 8. UNVERIFIED

- 「打包进 DMG 后 WKWebView 的 `nonPersistent` 存储确实丢弃 localStorage，而 `local_profile_dir` 仍然持久」——这是整个修复的前提假设。我用「全新 browser context（storage 为空）+ 真实后端新进程 + 磁盘上真实记录」**建模**了它，并验证落点正确；但**没有**在真实 WKWebView 里直接验证该存储语义。
- 真实 macOS Keychain 不可用/可用两条分支下的向导行为：仅验证了 `SUMMIT_OFFLINE_GUARD_ACTIVE=1`（密钥后端不可用）分支。
- 并发写只验证到「8 线程 × 60 次直接 store 写 + 3 个读线程」与「6 个并发 HTTP 写」规模；未做大压力/断电注入。
- 多窗口（同一工作库两个窗口同时改步骤）的语义未测。

## 9. 对开发者证据的核对与指正

- **计数与退出码：一致。** Web 220 passed / 0 todo、Python 686 passed、静态检查与 build 全 0、e2e 2/2 均由我独立重跑复现，无差异。
- **「lint 仍有 2 条既存 warning」：成立。** 我在父 SHA 876008e 上重跑得到同样 2 条。
- **「OpenAPI diff +234/−0、未改既有 schema」：成立。** 数字与形状均已独立核对。
- **表述需要收紧（1）：**「旧 localStorage 副本只做一次性迁移」在 **dev / React StrictMode** 语义下会发出 2 次相同 PUT（见 D-2）；只有在**生产构建**下才严格是一次。建议报告显式限定。
- **表述需要收紧（2）：** 未验证项里写「pre-repair1 已配好的工作库会再看到一次向导」，但没有说明**关闭前 Today 不可达**（模态遮罩覆盖主导航）。实测后果更重，建议补上（见 D-1）。
- **表述需要收紧（3）：** 报告写「离线 Playwright（含首配闭环与五档/深浅基线）PASS 2/2」，但仓库 `playwright.config.ts` 的 `testMatch` 只包含 `viewport.spec.ts` 与 `first-use.spec.ts`；`frontend-c-flow.spec.ts`、`frontend-c-view.spec.ts`、`approval-today.spec.ts`、`first-use-real.spec.ts` **不在默认 e2e 门内**。这不影响本轮判定（首配闭环确实在门内），但「e2e PASS」的覆盖范围不宜被读成全部 spec。
- **表述需要收紧（4）：** 开发者在自述里明确写了「本机记录必须来自 GET/PUT 端点而不是浏览器存储」，这点我完全同意——我的 harness 正是用**真实后端 + 真实端点**复验，而不是 mock。
- **未发现开发者有「把未测写成已测」的地方。** native / DMG / 真实凭据 / 缩放都被如实标为 NOT_RUN，与我独立结论一致。

## 10. 复现指令（自建 harness）

```sh
QA=/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1/SummitEverything
cd "$QA"
uv sync --locked --group dev
npm --prefix web ci

# A. HTTP / store 黑盒（33 条断言）
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python \
  .local/qa/frontend-d-repair1/harness/qa_first_use_harness.py

# B. 浏览器 + 真实后端 + 真实重启（64 条断言，两种前端形态）
npm --prefix web run build
cd web
SUMMIT_QA_MODE=prod node ../.local/qa/frontend-d-repair1/harness/qa_p1_restart.mjs   # 生产构建
node ../.local/qa/frontend-d-repair1/harness/qa_p1_restart.mjs                       # vite dev
```

harness 会在 8799/5199 上自管 uvicorn 与前端进程，并在启动前拒绝复用已被占用的端口；每次运行使用一次性隔离 profile root（`.local/qa/frontend-d-repair1/run-<mode>/profile`），不会触碰真实 `~/Library/Application Support/SummitEverything`。

## 11. 环境与 SHA 核对

- 受测 checkout：`HEAD == faa1edd611a74dcdc26bff234de810bdf47761cb` ✔；`git status --porcelain` 为空 ✔。
- 对照 checkout：`HEAD == 876008e1d33420f57fb31772c76e471379e6b98d` ✔；工作树无 tracked 改动 ✔。
- 开发者 worktree `/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`：我只读取，未写入；`git status --porcelain` 为空 ✔。
- 分支 `codex/frontend-ux-20261015` 的 tip 现在是 `834695e`（在我开始验收后由开发者追加）。
  我核对：`git merge-base --is-ancestor faa1edd <tip>` = YES，且 `faa1edd..tip` 的 diff **只涉及 README 与 `docs/**`（6 个文件，无源码）**，所以受测产品树没有变。
- `uv.lock` / `pyproject.toml` 在 `876008e..faa1edd` 之间**完全无 diff**（这也是我用同一 venv 跑父 SHA 源码对照的前提）。
