# 前端 UX 里程碑 D · repair3 · 独立 QA 报告

- 角色：**全新独立 QA**。本会话第一次接触本里程碑；上一轮 QA（repair2）的结论与开发者报告只作为线索，**不作结论依据**。
- 日期：2026-10-15。
- **受测产品源码 SHA：`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（父 `96fdf4d7cccfd71bd1719d4318e0e399309e8281`；分支 `codex/frontend-ux-20261015`；提交标题 *fix: regenerate the browser API types after the step validator change*）。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3/SummitEverything`（detached，`git rev-parse HEAD` 已核对；`git worktree add --detach … e8e1dba…` 新建）。
- 对照 checkout（父 SHA，我自己新建，用于「门非空」对照）：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3-parent/SummitEverything`（detached `96fdf4d`）。
- 证据根目录（git ignored）：`<受测 checkout>/.local/qa/frontend-d-repair3/`（`logs/`、`harness/`、`screenshots-prod/`、`run-prod/`、`run-http/`）。
- 未 push / merge / 删除任何 branch 或 worktree；未写入开发者 worktree；未触碰真实 provider / OAuth / 飞书 / Keychain / 真实材料 / 已安装 App / 生产。
- **本会话模型不支持图像输入**：本报告没有任何「我看了 PNG」的结论。所有断言来自 DOM 级断言、HTTP 响应体、磁盘字节、以及 harness 同步写出的 `.txt` 文本快照。PNG 仅供人工复核。

---

## 0. 判定

**PASS（限定范围）。**

精确适用范围：

| # | 项目 | 判定 |
|---|---|---|
| ① | **D-6 收口**：`npm --prefix web run api:types && git diff --exit-code -- web/src/api/generated.ts` 在 `e8e1dba` exit 0；同一门在父 `96fdf4d` exit 1；CI 工作流里确实就是这一条 | **PASS** |
| ② | **改动面最小性**：`96fdf4d → e8e1dba` 只有 `web/src/api/generated.ts`；`-- src`（Python 后端）为空 | **PASS** |
| ③ | **证据可继承性**：本 SHA 构建的 `web/dist` 指纹、父 SHA 构建的指纹、候选包内 `Resources/web` 指纹三者相同，且逐文件 sha256 全同 | **PASS（继承成立，且我不依赖继承——见下）** |
| ④ | **自动检查回归抽验**（12 条命令，真实退出码） | **PASS**（全部 exit 0，计数与开发者声称一致） |
| ⑤ | **D-1 / D-4 / P1 回归抽验**（新 SHA 上重新取证） | **PASS** |
| ⑥ | **tree / 证据清洁** | **受测 checkout PASS；开发者 worktree FAIL（仅 2 个未跟踪 docs 报告）** |

**唯一未达标项（⑥，轻微 / 过程级）**：开发者 worktree `/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything` 的 `git status --porcelain` **非空**，有 2 个未跟踪的 docs 报告文件（详见 §6）。这不影响受测 SHA、不改变任何 tracked 产品/测试字节、不影响制品，故不构成对固定产品 SHA 的 FAIL，但不符合本轮「开发者 worktree 应为空」的验收前提，作为新发现记录（级别：Nit / 过程）。

- **native WKWebView 同 profile 重启：NOT_RUN（我未独立验证）**。开发者在本机做的人工点击验证我既未被要求、也无能力复现（本会话不驱动 macOS GUI；native 源码与上一受测 SHA 逐字节相同）。我对候选包的核查仅止于**静态制品**（`build-info.json` 与 `Resources/web` 指纹），这**不能**冒充 GUI 运行结论。
- 真实 provider / 飞书 / OAuth / Keychain / 真实材料 / DMG 安装 / 双机：**NOT_RUN**。

---

## 1. 方法与独立性

本轮 harness = **我上一轮自建 harness 的复用**（任务明确允许），仅把证据路径 `frontend-d-repair2` → `frontend-d-repair3`，**断言与业务逻辑一字未改**（这是刻意的：复用同一把尺子，便于与父 SHA 对照，也便于验证「继承」）。逐文件来源哈希：

```
d6b7314674d2f25e05e7cfc22b6568c58a5cccfabac4a0bc08c095aaf8ebce9f  repair2/harness/qa_r2_app.py
612ce1bea630b14c11a2cf1f94d62aca5173b8626d7634587cda65d2f6295de3  repair2/harness/qa_r2_http.py
f86c17c194fbb82c56b432e2280e3b396019c401249391b7719caa3c82933da9  repair2/harness/qa_r2_browser.mjs
8f4b66d2467827cda6ff4d132f7d2d292d709d18572c7b00963e384d7ed35d48  repair2/harness/qa_r2_static.mjs
```

本轮新增（我自己写）：

- `harness/qa_r3_fingerprint.py` — **独立重实现**指纹算法（sorted 相对 posix 路径 + `\0` + 文件 sha256），并与产品 `summit_everything.release.fingerprint_web_dist` 对拍，避免「用产品函数证明产品」。
- `harness/qa_r3_reproduce.sh` — 本轮全部命令与预期退出码的可复现清单。

harness 不 import、不运行开发者任何测试文件（`qa_r2_app.py` 直接调用真实 `create_app()`，隔离 profile root；浏览器 harness 起真实 `uvicorn` 子进程 + 真实 socket；前端跑**生产构建 `web/dist`** 由 QA 自有静态代理 + `/api` 反向代理提供，等价于打包外壳注入 token 的方式）。

**tree 守卫**（证明我没改产品源码）：

```
HEAD                              e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374
HEAD^{tree} 全部取证前            7f3b658d919514144bbebc44cde4d5de7f41e878
HEAD^{tree} 全部取证后            7f3b658d919514144bbebc44cde4d5de7f41e878   ← 相同
git status --porcelain            空（见 logs/10-tree-guard.txt）
tracked 全部文件字节 sha256        aeb2704b00f03370a266743d6e56cbb074396b3620cc61f9a4ada37d48abe5b6
```

证据处理纪律：本轮浏览器 harness 第 1 次运行失败（harness 自身缺 `node_modules` 解析路径），**首次 raw 先另存**为 `logs/08-browser-harness-prod.failed-raw.log` 再修复重跑，未覆盖。

---

## 2. ① D-6 收口（PASS）

**命令与真实退出码**（受测 checkout，`logs/01-d6-gate-e8e1dba.log`、`logs/09-d6-gate-post-harness.log`）：

| 命令 | 退出码 |
|---|---|
| `npm --prefix web run api:types` | 0（`Wrote web/openapi.json`；`openapi.json → src/api/generated.ts`） |
| `git diff --exit-code -- web/src/api/generated.ts`（**CI 原文形式**） | **0** |
| `git diff --exit-code -- web/src/api/generated.ts web/openapi.json`（任务给的更严格形式） | **0** |
| `git status --porcelain`（生成后） | 空 |

即：重导出后 `openapi.json` 与 `generated.ts` **都与 tracked 逐字节一致**——上一轮的 D-6 已被消除。harness 全部跑完后我再跑一遍同一门，仍 exit 0（`logs/09-…`）。

**门非空对照（关键：证明不是我或开发者把门变软）**：同一命令在父 SHA `96fdf4d` 上（我新建的独立对照 checkout，`logs/parent/01-d6-gate-96fdf4d.log`）：

```
api:types                     EXIT=0
git diff --exit-code -- web/src/api/generated.ts           DIFF_GENERATED_EXIT=1
git diff --exit-code -- web/src/api/generated.ts openapi.json  DIFF_BOTH_EXIT=1
原始 diff：@@ -1753,6 +1753,11 @@  +5 行 JSDoc（`step` 为真整数的说明），仅此一处
```

**CI 工作流原文核对**（`git show e8e1dba:.github/workflows/m41-internal-app.yml`，且该文件在 `96fdf4d..e8e1dba` 之间无改动）：

```yaml
      - name: Web checks and API types
        run: |
          npm --prefix web run api:types
          git diff --exit-code -- web/src/api/generated.ts
          npm --prefix web test
          npm --prefix web run typecheck
          npm --prefix web run lint
          npm --prefix web run build
```

结论：任务描述的「原始步骤确实就是这一条」**成立**——注意 CI 门只 diff `generated.ts`（不含 `openapi.json`）；我额外跑了更严格的两文件形式，也是 exit 0。

**观察（非缺陷，信息级）**：该 workflow 的 `on.push.branches` 只有 `codex/m41-internal-app-*`，因此 `codex/frontend-ux-20261015` 的 push **不会自动触发**这个 job（`pull_request` 触碰 `web/**` 等路径会触发，也可 `workflow_dispatch`）。所以本轮是「在本地精确复现仓库 CI 的那一步」，不是「观察了一次真实 CI 运行」。

---

## 3. ② 改动面最小性（PASS）

`logs/01-…` 外的独立命令输出：

```
$ git diff --stat 96fdf4d e8e1dba
 web/src/api/generated.ts | 5 +++++
 1 file changed, 5 insertions(+)

$ git diff --name-status 96fdf4d e8e1dba
M	web/src/api/generated.ts

$ git diff --quiet 96fdf4d e8e1dba -- src ; echo $?
0
```

逐路径核对（`native / tests / scripts / src / docs` 全部 EMPTY，只有 `web` 变了那一个文件）：

| 路径 | `git diff 96fdf4d e8e1dba -- <path>` |
|---|---|
| `src`（Python 后端） | **EMPTY** |
| `tests` | EMPTY |
| `native` | EMPTY |
| `scripts` | EMPTY |
| `docs` | EMPTY |
| `web` | `web/src/api/generated.ts`（+5 −0） |

`+5` 行的内容我逐行看过：全部是 `FirstUseProgress` 上的 **JSDoc 注释**（描述 `step` 必须是真整数、Pydantic lax mode 会把 `3.0` 规范化成 `3`），没有任何类型签名、枚举或运行期结构变化。

---

## 4. ③ 证据可继承性（PASS；并且我没有把它当作结论来源）

### 4.1 我做的三件事

1. **在两个 SHA 上各自独立构建** `web/dist`（同一 checkout 环境、同一 `npm ci` 锁文件）：
   - `e8e1dba`：`npm --prefix web run build` exit 0（`logs/02-build-e8e1dba.log`）
   - `96fdf4d`：`npm --prefix web run build` exit 0（`logs/parent/02-build-96fdf4d.log`），**在跑 api:types 之前构建**，保证是「已提交的 96fdf4d」
2. **独立重实现指纹算法**并与产品 helper 对拍（`logs/11-fingerprint-independent.txt`）：

| dist | QA 重实现 | 产品 helper | 文件数 |
|---|---|---|---|
| 受测 checkout `e8e1dba/web/dist` | `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0` | 同 | 4 |
| 对照 `96fdf4d/web/dist` | `784ae1ee…dbf0` | 同 | 4 |
| 开发者候选包 `SummitEverything-D-e8e1dba.app/Contents/Resources/web` | `784ae1ee…dbf0` | 同 | 4 |

3. **逐文件 sha256 比对**：两次构建的 `assets/index-CJV7PXqW.js`、`assets/index-lgEUmbbh.css`、`favicon.svg`、`index.html` **哈希完全相同**（`diff` 两个 manifest 输出 `DIST_MANIFEST_IDENTICAL=yes`）。也就是说这里不是「sha256 碰巧一致」，而是**产物逐个文件逐字节相同**。

### 4.2 `frontend_sha256` 两次构建是否相同

**相同**。`scripts/build_macos_app.py:134` 定义 `frontend_sha = fingerprint_web_dist(web/dist)`，两次构建的该值都是 `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`；开发者候选包 `build-info.json` 里记录的也是这个值（我直接读了文件）：

```json
{"app_version":"0.1.0","build_id":"20261015T144744Z-784ae1ee176a",
 "dependencies_sha256":"cab27471…28c7d7","dirty":false,
 "frontend_sha256":"784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0",
 "source_sha":"e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374"}
```

### 4.3 为什么「types-only、构建时被擦除」在这里是真的（而不只是开发者说的）

- `web/src/api/generated.ts` **没有任何运行期导出**（`grep -E "^export (const|function|class|enum|default)"` 无命中）；它只导出 `components`/`paths`/`operations` 等**类型**。
- 全部 9 处引用者都是 `import type { components } from '../api/generated'`（`grep -v "import type"` 无命中），TypeScript/`tsc -b` 与 vite/esbuild 在编译期把这些 import **完全擦除**；`vite.config.ts` 未开启 sourcemap，因此连原始注释文本都不会进入产物。
- 经验证据与上面一致：**产物逐字节相同**（4/4 文件 sha256 相同）。

### 4.4 我对「继承」的立场（诚实说明）

- 对**制品级性质**（前端 bundle 的字节、后端 Python 字节、测试字节），继承是**可证且已证**的：`src` diff 为空、`tests` diff 为空、`dist` 逐字节相同、9 处 import 全是 type-only。上一轮 QA 在 `web/dist` 上做的浏览器结论，覆盖的确实是同一个 bundle（候选包内 `Resources/web` 指纹相同）。
- 但「上一次 PASS 可以继承」作为**证据链的替代品**是不严谨的：它成立的前提是「两次构建可复现且继承面完整」，而这是需要单独验证的强前提（我这次恰好验证成功；若 vite 版本漂移或开了 sourcemap，结论就会翻转）。**我没有把它当结论来源**：⑤ 的三条核心场景我在新 SHA 上重新取证，④ 的 12 条命令我也全部重跑。因此即使有人不接受继承论证，本报告的 PASS 仍然独立成立；继承只用于解释「为什么新 SHA 的结果与父 SHA 一致是合理的」。
- 另外要说清：可继承的是**产物的行为结论**，不可继承的是「在这个 SHA 上运行过」这一事实本身（证据的 SHA 归属）。这也是我坚持全部重跑的原因。

---

## 5. ④ 自动检查回归抽验（12/12 exit 0）

全部在受测 checkout 实跑，真实退出码（`logs/04-python-suite.log`、`logs/05-web-suite.log`）：

| # | 命令 | 真实结果 | exit |
|---|---|---|---|
| 1 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | **692 passed, 1 warning in 82.15s** | 0 |
| 2 | `uv run ruff check src tests` | `All checks passed!` | 0 |
| 3 | `uv run ruff format --check src tests` | `100 files already formatted` | 0 |
| 4 | `uv run mypy src` | `Success: no issues found in 47 source files` | 0 |
| 5 | `uv lock --check` | 无输出 | 0 |
| 6 | `uv build` | sdist + wheel 构建成功 | 0 |
| 7 | `npm --prefix web test -- --run` | **Test Files 26 passed (26) / Tests 222 passed (222)**，无 todo/skipped 行 | 0 |
| 8 | `npm --prefix web run typecheck` | 无错误 | 0 |
| 9 | `npm --prefix web run lint` | **Found 2 warnings and 0 errors**（74 files / 116 rules） | 0 |
| 10 | `npm --prefix web run build` | vite build 成功（4 个产物文件） | 0 |
| 11 | `npm --prefix web run test:e2e` | **2 passed (12.9s)** | 0 |
| 12 | `npm --prefix web run test:e2e:integration` | **1 passed (3.6s)** | 0 |

与开发者声称一致：692 / 222（0 todo）/ 2 warnings 0 errors / e2e 2 / integration 1。CI 里另有 `swift test --package-path native` 与 `scripts/release-macos.sh` + DMG + `smoke_packaged_app.py`：**本轮 NOT_RUN**（不在本轮要求范围；native 源码逐字节未变）。`uv build` 我额外跑了（CI 有这一步），exit 0。

---

## 6. ⑤ D-1 / D-4 / P1 新 SHA 重取证（PASS）

### 6.1 HTTP 黑盒 harness（`logs/07-http-harness.log`）

```
QA R2 HTTP HARNESS TOTAL: 54 checks, 54 passed, 0 failed      HTTP_HARNESS_EXIT=0
```

真实 `uvicorn` 子进程 + 真实 TCP socket + **手写 JSON 字符串**（保证 `3.0` 真的以 `3.0` 上线），隔离 profile root。

**D-4（`step` 严格整数）关键行**：

```
[PASS] B3 step=3.0 -> 422   :: {"error":{"code":"validation_error",...}}
[PASS] B3 step=2.0 / 4.0 / 5.0 / 2e0 / 3e0 / 5.0e0 -> 422
[PASS] B4 step=3.5 / 2.5 / 4.5 / -4.0 / true / false / "3" / "3.0" / null
       / 6 / 1 / 0 / -1 / [] / {} -> 422
[PASS] B7 extra/secret field rejected -> 422
```

以及真整数 2/3/4/5 → 200 并落盘为 JSON 整数、OpenAPI 仍为 `integer enum [2,3,4,5]`（其余 54 条中的正向断言）。

**D-1（HTTP 半边）**：`open` 一个已配置但本机无记录的工作库 → 后端**不伪造**记录（`/first-use/progress` 仍 404）、不从凭据/设置推断「首次配置已完成」、不创建记录文件；多工作库记录互不泄漏。

### 6.2 浏览器黑盒 harness（`logs/08-browser-harness-prod.log`）

```
QA R2 BROWSER HARNESS (prod) TOTAL: 51 checks, 51 passed, 0 failed   BROWSER_HARNESS_EXIT=0
```

跑的是**生产构建 `web/dist`**（无 React StrictMode），后端为真实 `uvicorn`；「重启」= 杀掉后端进程 + **另起新进程** + **全新 browser context（storage 为空）**（最接近 nonPersistent WKWebView 的可用模型，但**不是** native）。任务点名的三条：

```
[PASS] G2.7 ***P1 CORE*** reopening the already-configured workspace lands on Today :: landing=today wizard=null today=true
[PASS] G2.8 ***P1 CORE*** no wizard and no wizard backdrop after the reopen :: wizard=null backdrop=0
[PASS] G2.9 no "第 2 步 · 模型与密钥" heading exists anywhere
[PASS] G3.3 ***D-1 CORE*** "open" with no local record lands on Today, not the wizard :: wizard=null today=true
[PASS] G3.4 ***D-1 CORE*** no .wizard-backdrop covers Today :: backdrop=0
[PASS] G3.5 the app does NOT claim first use is already completed (no inference from credentials)
[PASS] G3.6 a non-blocking pointer is shown (neutral toast, role=status, not an error)
             :: [{"text":"这个工作库在本机还没有首次配置记录。…可从设置里打开连接向导。 ✕","cls":"toast toast-neutral","role":"status"}]
[PASS] G3.8 主导航不被提示拦截；G3.9 可自由回今日；G3.11 打开没有创建记录文件
[PASS] G1.2 create 意图仍进向导第 2 步（D-1 正向对照，未被修坏）
```

P1 路径完整复现了任务要求的形式：**完成首配 → 真实后端新进程 + 全新 context → 手动打开已有 → Today 且无向导/无遮罩**（G2.7/G2.8，并含 G2.4「重启后无自动打开」、G2.5「新 context storage 确实为空」）。D-4 与 D-1 的修复前症状我本轮**没有**在父 SHA 上重跑对照（上一轮已做过，且父 SHA 的 `src` 与 `web/src` 除该注释文件外与本 SHA 相同）；这一点明确记为「本轮未重跑父 SHA 行为对照」。

文本快照（供人工复核，PNG 我未视读）：`screenshots-prod/*.txt`。

---

## 7. ⑥ tree / 证据清洁

| 对象 | 结果 |
|---|---|
| 受测 checkout `frontend-d-qa-repair3` | `git status --porcelain` **空**；`HEAD^{tree}` 取证前后相同；未改任何 tracked 文件 |
| 我新建的父 SHA 对照 checkout `frontend-d-qa-repair3-parent` | 为跑门把 `generated.ts` 变成 dirty（这是门的必然结果），**已 `git checkout --` 还原**，现为空 |
| 开发者 worktree `frontend-ux-20261015` | `git status --porcelain` **非空**：`?? docs/quality/reports/2026-10-15-FRONTEND-D-DEV-REPAIR2.md`、`?? docs/quality/reports/2026-10-15-FRONTEND-D-QA-REPAIR2.md`（**新发现 N-1**） |
| 开发者构建 worktree `frontend-d-build-repair3` | **空**，HEAD = `e8e1dba` |
| 分支 tip | `codex/frontend-ux-20261015` tip **就是** `e8e1dba`（`git log e8e1dba..tip` 为空，`git diff --stat e8e1dba tip` 为空）→ 不存在「tip 落后/超前」问题，任务里「e8e1dba..tip 只含 docs」在当前状态下 vacuously 成立 |

**N-1（新发现，Nit / 过程级，非产品缺陷）**

- 现象：开发者 worktree 有 2 个未跟踪的 docs 报告（dev 报告 + 一份 QA 报告副本），违反本轮「开发者 worktree 应为空」的验收前提。
- 最小复现：`git -C /Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything status --porcelain`
- 影响评估（我实际核过，不是推测）：
  - 两个文件都是 `??`（未跟踪），**没有任何 tracked 文件被修改**，`HEAD` 仍为 `e8e1dba`；受测产品 SHA 与全部 tracked 测试/源码字节不受影响。
  - mtime `22:56:08` / `22:59:23`，而候选包 `build-info.json` mtime 为 `22:47:57` 且 `dirty:false`——即这两个文件**晚于**候选打包产生（`build_macos_app.py:115` 用 `git status --porcelain --untracked-files=all` 判 dirty，若打包时存在这些文件会直接拒绝构建，与 `dirty:false` 矛盾）。第二个文件甚至是在我本轮取证期间（约 22:59）写入的，说明该 worktree 在我验收过程中仍被并行写入（仅 docs）。
  - 结论：不影响 PASS 的适用范围；但「docs 报告未提交、且工作树不干净」应记入交接（若流程要求 worktree 清洁，请提交或移出 `.local`）。

---

## 8. NOT_RUN / UNVERIFIED 清单

| 项 | 状态 | 原因 |
|---|---|---|
| native WKWebView 同 profile 重启、开发者人工点击验证 | **NOT_RUN（我未独立验证）** | 本会话无法驱动 macOS GUI；我只有静态制品核查（`build-info.json` + `Resources/web` 指纹），不构成 GUI 运行证据。开发者的 native 结论**未经我确认**，请勿计入本轮 QA 结论 |
| 候选 `.app` / `.dmg` 的实际启动、`scripts/smoke_packaged_app.py` | NOT_RUN | 不在本轮要求范围；仅静态读取了构建 worktree 的制品 |
| `swift test --package-path native` | NOT_RUN | 不在本轮要求范围（native 源码 `96fdf4d..e8e1dba` 无变化，但我未实跑，不作继承） |
| `scripts/release-macos.sh` / DMG 构建 / `hdiutil verify` / `codesign --verify` | NOT_RUN | 同上 |
| PNG 截图的视觉判读 | **UNVERIFIED / 不可能** | 当前模型不支持图像输入；我未视读任何 PNG，只用同步 `.txt` 文本快照 |
| 父 SHA 上 D-1 修复前症状的行为对照（非空性对照） | NOT_RUN（本轮） | 上一轮做过；本轮只对 D-6 门做了父 SHA 的 exit 1 对照 |
| 真实 provider / 飞书 OAuth / Keychain / 真实材料 / 双机 / 五日 | NOT_RUN | 需用户显式选材与授权，本轮无凭据 |
| 真实 CI（GitHub Actions）运行 | NOT_RUN | 无网络侧 CI 证据；我只是在本地精确复现 workflow 里的那一步（且该 workflow 的 push 触发分支不含本分支） |

---

## 9. 证据索引（`<受测 checkout>/.local/qa/frontend-d-repair3/`）

| 文件 | 内容 |
|---|---|
| `logs/00-install.log` | `uv sync --locked --group dev && npm --prefix web ci`（exit 0） |
| `logs/01-d6-gate-e8e1dba.log` | 受测 SHA：api:types + 两种 diff 形式 + status（exit 0/0/0） |
| `logs/01-before-hashes.txt`, `logs/01-before-status.txt` | 门之前 `openapi.json`/`generated.ts` 的 sha1 与 status |
| `logs/02-build-e8e1dba.log`, `logs/03-fingerprint-e8e1dba.txt`, `logs/03-dist-manifest-e8e1dba.txt` | 受测 SHA 构建与指纹 |
| `logs/parent/01-d6-gate-96fdf4d.log` | **父 SHA 门 exit 1 的原始输出**（含 5 行 diff） |
| `logs/parent/02-build-96fdf4d.log`, `logs/parent/03-fingerprint-96fdf4d.txt`, `logs/parent/03-dist-manifest-96fdf4d.txt` | 父 SHA 构建与指纹 |
| `logs/04-python-suite.log` | pytest 692 / ruff check / ruff format / mypy / uv lock / uv build |
| `logs/05-web-suite.log` | vitest 222 / typecheck / lint / build / e2e 2 / e2e:integration 1 |
| `logs/06-pre-harness-tree.log`, `logs/10-tree-guard.txt`, `logs/10-tracked-product-bytes.sha256` | tree 守卫（前/后 tree 哈希相同、status 空） |
| `logs/07-http-harness.log` + `run-http/results.json` | HTTP 黑盒 54/54，exit 0（D-4 + D-1 HTTP 半边） |
| `logs/08-browser-harness-prod.log` + `run-prod/results.json` + `run-prod/env.json` | 浏览器黑盒 51/51，exit 0（D-1 / P1，生产 bundle） |
| `logs/08-browser-harness-prod.failed-raw.log` | **harness 自身缺陷的首次原始日志**（未覆盖，未修改产品） |
| `logs/09-d6-gate-post-harness.log` | 全部取证完成后重跑门，仍 exit 0 |
| `logs/11-fingerprint-independent.txt` | 三处 dist 的独立重实现指纹 vs 产品 helper（全部 `784ae1ee…`） |
| `harness/qa_r2_{app,http,browser,static}.*` | 复用的 QA harness（仅改证据路径） |
| `harness/qa_r3_fingerprint.py`, `harness/qa_r3_reproduce.sh` | 本轮新增的独立指纹脚本与可复现清单 |
| `screenshots-prod/*.png`, `*.txt` | 浏览器 harness 截图 + 文本快照（PNG 我未视读） |
| `EVIDENCE-MANIFEST.sha256` | 以上全部证据文件的 sha256 |

---

## 10. 一句话结论

`e8e1dba` 上的 5 行 JSDoc 重新生成把上一轮唯一的 FAIL（D-6）闭掉了，且**没有**动任何 Python/测试/native 字节，构建产物与父 SHA **逐字节相同**；12 条自动检查与 D-1 / D-4 / P1 黑盒场景在本 SHA 上重新取证全部通过。**本轮判定 PASS（限定范围）**；范围之外（native GUI 人工验证、DMG 安装、真实外部门、PNG 视觉判读）我没有独立验证，不计入。
