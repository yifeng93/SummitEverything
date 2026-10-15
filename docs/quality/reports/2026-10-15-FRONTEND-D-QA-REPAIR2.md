# 前端 UX 里程碑 D repair2 独立 QA（固定 SHA `96fdf4d`）

- 受测产品源码 SHA：`96fdf4d7cccfd71bd1719d4318e0e399309e8281`（父 `faa1edd611a74dcdc26bff234de810bdf47761cb`，分支 `codex/frontend-ux-20261015`）。
- QA 判定：**FAIL（限定范围）**。两条定点修复与 P1 回归本身都 PASS，全部 12 条自动检查 PASS，但仓库 CI 门 `npm run api:types && git diff --exit-code -- web/src/api/generated.ts` 失败（新缺陷 **D-6**，P2）。
- QA 在独立 worktree（detached `96fdf4d`）取证；对照 checkout 为 `faa1edd`。受测与开发者 worktree 的 tracked 状态全程为空，分支 tip 未移动。

## 逐项结论

| 项 | 判定 | 证据（QA checkout 的 ignored `.local/qa/frontend-d-repair2/`） |
|---|---|---|
| D-1 工作库意图上抛；`open` 且无记录 → Today，`.wizard-backdrop` 不再拦截导航，中性非阻塞提示 | **PASS** | `logs/01-03-browser-prod.log` G1–G5；`screenshots-prod/…` |
| D-4 `step` 严格整数：`3.0/2.0/4.0/5.0/2e0/3e0/5.0e0` 全 422；真整数 2/3/4/5 全 200 且落盘为 JSON 整数 | **PASS** | `logs/04-http-harness.log`（54/54） |
| P1 回归（完成 → 真实后端新进程 + 全新 context → 打开已有 → Today） | **PASS**（本轮重新取证） | 同上 G2.1–G2.10 |
| 全部自动检查（12 条） | **PASS**，与 Developer 声称零差异 | `logs/07-*.log` |
| **OpenAPI 派生类型一致性（CI 门）** | **FAIL — D-6** | `logs/06-openapi.log`、`logs/06b-openapi-ci-gate.log`、父对照 `logs/06c-openapi-ci-gate-parent.log` |

**非空性对照（方法学证据）**：同一份自建 harness 在父 SHA `faa1edd` 上 D-1 组失败——`wizard={"第 2 步 · 模型与密钥", step:2} today=false`、`backdrop=1`、无 toast、`navClickIntercepted=true`（Playwright 原文 `.wizard-backdrop … intercepts pointer events`），`23 checks / 18 passed / exit 1`；而 P1 组在父 SHA 全绿。既证明检查不空转，也独立复现了修复前症状。

## 缺陷

- **D-6（P2，本轮引入）**：`web/openapi.json` 重新导出了，但派生的 `web/src/api/generated.ts` 没有重新生成。`npm --prefix web run api:types && git diff --exit-code -- web/src/api/generated.ts` → **exit 1**；父 `faa1edd` 上同一门 **exit 0**。运行时类型形状未变（只差 JSDoc 注释），但该门正是仓库 CI `.github/workflows/m41-internal-app.yml` 的原始步骤，属失败态。tracked sha256：`openapi.json 87248b30…`、`generated.ts 396613c3…`；重生成后 `bb4ad789…`。→ 已由 repair3 `e8e1dba` 只重生成该文件修复。
- **D-5（P3，观察）**：`create` 意图只存在内存，`App.connect()` 一律按 `open` 处理，因此「新建后一步没走就 reload/重启」会退出向导落到 Today 并给同一条提示（父 SHA 会回到向导第 2 步）。提示为真、不写假进度、设置里可恢复，但属行为变化。**用户已决议接受为记录项，不在 `e8e1dba` 修改。**
- **D-7（INFO）**：repair1 交接文档在 `96fdf4d` 时点仍把 D-1 写成「待用户决议」、D-4 写成「可选小修」，与同一 SHA 的代码不一致（docs 不属受测产品 SHA）。已在后续 docs 提交纠正。

## 真实计数与退出码（QA 独立重跑）

`pytest` **692 passed** exit 0；`vitest` **222 passed / 26 files / 0 todo** exit 0；`typecheck` exit 0；`lint` **2 warnings / 0 errors** exit 0（`App.tsx:124`、`ProjectsView.tsx:62`，父 SHA 复核为同样 2 条，仅行号上移 → 既存）；`build` exit 0；`test:e2e` **2 passed** exit 0；`test:e2e:integration` **1 passed** exit 0；`ruff check` / `ruff format --check` / `mypy`（47 files）/ `uv lock --check` / `uv sync` / `npm ci` 全 exit 0。

## 证据处理纪律

本轮有 3 次**harness 自身缺陷**导致的失败运行，QA 均先把首次 raw 另存再修改 harness，未覆盖：`logs/04-http-harness.failed-raw.log`（QA 误把错误信封读成 `detail.code`，实际是 `{"error":{"code":…}}`；被测行为本身正确）、`logs/01-03-browser-prod.failed-raw.log`、`.failed-raw-2.log`（`step`/`created` 被分组块作用域遮蔽）、`.failed-raw-3.log`（期望值差一，产品正确）。全部为 QA 侧 harness 缺陷，逐条对照修正；最终 prod 51/51、dev 51/51、HTTP 54/54、exit 0。

## 关键原件 SHA-256

| 原件（相对 `.local/qa/frontend-d-repair2/`） | SHA-256 |
|---|---|
| `QA-REPORT.md` | `ad218f10692d3e5b5efe5ec87d025121286d4b0ab6b0a1c23645c4132612cad0` |
| `EVIDENCE-MANIFEST.sha256` | `332e99a10e5cf2c32a25caa015864d032a626ab2c0db99cd9df25d6fde19860a` |
| `logs/06b-openapi-ci-gate.log` | `a0beb8a1c33fc2f99638d837e8d03e107c68f2d1d0e4a833900cbd6c752b0563` |
| `logs/06c-openapi-ci-gate-parent.log` | `4954b8f36b756d679f513f86a2cb7f6301f8a956ef5d24b0dc33f9ff9786b75c` |
| `logs/04-http-harness.log` | `e84bd00b11fd24f9d9353e61da19335fbb68585c369b478ff012a0b95210e33f` |
| `logs/01-03-browser-prod.log` | `c6a52d4cbabe5c89bf3ee6282aa667339b1fddf5e074fa599e56c03e7d703692` |
| `logs/08-parent-faa1edd-control.log` | `341ed99b97604d99b36d560c069d756017e190bca46df3c17bb009b4f11d21dc` |

完整原件：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair2/SummitEverything/.local/qa/frontend-d-repair2/`。
此 tracked 摘要不复制 trace、profile、token 或真实数据。

## NOT_RUN / UNVERIFIED（QA 自述）

- **NOT_RUN**：native WKWebView 同 profile 重启（该轮无新候选、未启原生 GUI）；新 App/DMG/manifest/build ID；真实 provider / 飞书 OAuth / Keychain / 真实材料 / 已安装 App / 公证 / 五日 / 双机 / 生产；200% 菜单缩放与原生 `pageZoom`；Swift/native 检查；`frontend-c-flow.spec.ts`、`frontend-c-view.spec.ts`、`first-use-real.spec.ts`（不在默认 e2e `testMatch` 内）；旧 SHA 的视口矩阵与十条变异。
- **诚实边界（QA 明确声明）**：该会话模型**不支持图像输入**，QA **没有**视觉判读任何 PNG；结论全部建立在 DOM 级断言、真实 HTTP 响应、磁盘字节与 17 份 DOM 文本快照上。
- **UNVERIFIED**：WKWebView nonPersistent 存储语义本身（用「空 storage + 真实后端新进程 + 磁盘真实记录」建模）；Keychain 可用分支；并发/断电压力；同库多窗口。
