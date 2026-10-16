# 下一阶段起点（2026-10-16）

本文件是 2026-10-15 PR #21 合并前清理收口后的**当前起点页**。它取代
[NEXT-AFTER-FRONTEND-D.md](history/2026-10-15-NEXT-AFTER-FRONTEND-D.md) 的「下一步」职能：
该文件已于 2026-10-16（PR #21 合入 main 之后）**移入 `docs/handoff/history/`**，不再是当前页；
该归档动作就是 §2 第 3 条的收尾（已执行完毕）。

## 1 · 干净基线

| 项 | 实测值 |
|---|---|
| 分支 | `codex/frontend-ux-20261015`（worktree clean） |
| 清理提交链（按时间序） | `8973b5a`（C0 计划）→ `9a9aba8`（C1 文档收敛）→ `9d6e097`（C3 孤儿）→ `207b8f9`（C2 归档）→ `32aa10c`（C4+C5 清退）→ `af65f04`（C6 显示名）→ `68c3639`（C6 CI 证据）→ `ebb6b6f0`（C6 更正）→ `412e0fd`（C7 交接与清理报告）→ `7a448c3`（C7b 链接与索引修正）→ `904a38d`（QA 独立验收报告） |
| **受测产品 SHA** | **`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（D 最终候选；本轮清理**未改动产品面**，冻结面 pathspec → exit 0 空 diff） |
| 独立验收 | 全新 QA 在独立 checkout `qa-cleanup-verify` 对受测 SHA `7a448c39092b81d0afcb15ce4dc57d91faaa7e5e` 全项 PASS（A–H），报告见 [QA 报告](../quality/reports/2026-10-15-PRE-PR21-CLEANUP-QA.md) |
| `main` | `e84e9e5a56475a19f68ca1a684366fba7f9fee83`（主仓库 `/Users/yifengstudio/Documents/GitHub/SummitEverything`） |
| 合并 | **`main` 现为 merge commit `12280ec1893f8f526b9b73a84b98416545254f42`**（2026-10-16T01:27:08Z；真 merge 非 squash，父 `e84e9e5` + `8ded0d9`） |
| 远端分支 | 只剩 `refs/heads/codex/frontend-ux-20261015` 与 `refs/heads/main`（`git ls-remote --heads origin`，exit 0） |
| worktree | **只剩 2 个**：主仓库（`main`）+ `frontend-ux-20261015`（`git worktree list \| wc -l` = 2） |
| worktree 目录 | `/Users/yifengstudio/.codex/worktrees` = **1 条 / 804 M**（唯一保留 `frontend-ux-20261015`） |
| 真实 CI | run [`38831085564`](https://github.com/yifeng93/SummitEverything/actions/runs/38831085564)（`headSha=af65f049…`，清理后 tip）**completed / success，4m45s**；run [`38831643643`](https://github.com/yifeng93/SummitEverything/actions/runs/38831643643)（`headSha=68c36399…`）**completed / success，4m08s**。两次四步骤全 success。**边界**：run `38831085564` 的 headSha 是 `af65f04`；受测 SHA `7a448c3` 当时尚未 push，因此该 SHA 上还没有 CI run——最终 tip push 后会补跑并回填。 |
| PR #21 | **已合入 main**：merge commit `12280ec1893f8f526b9b73a84b98416545254f42`（2026-10-16T01:27:08Z，真 merge 非 squash），head `codex/frontend-ux-20261015` → base `main`，被合并 tip `8ded0d9`；分支将删除 |
| 前端指纹 | `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`（清理前后不变） |
| Sol 最终门判断 | **本轮清理限「仓库整理」范围 PASS，可随 PR #21 一起合入**；PR #21 已于 2026-10-16 按用户批准合入（见上「合并」行）；见 [Sol 最终门判断](../quality/reports/2026-10-16-PRE-PR21-CLEANUP-SOL-GATE.md) |

本页之后仅新增 Sol 最终门判断（`docs/quality/reports/2026-10-16-PRE-PR21-CLEANUP-SOL-GATE.md`）
与其在交付回报中给出的最终 CI run；精确 tip 以 `git log --oneline codex/frontend-ux-20261015` 为准。

清理结论、逐项证据与退出码见
[2026-10-15-PRE-PR21-CLEANUP-DEV.md](../quality/reports/2026-10-15-PRE-PR21-CLEANUP-DEV.md)，
分片计划见 [2026-10-15-PRE-PR21-CLEANUP-PLAN.md](2026-10-15-PRE-PR21-CLEANUP-PLAN.md)。

## 2 · 合并后收尾（2026-10-16 已执行）

1. **核对产品树未被合并改变**：合并后对 `main` 重跑冻结面比对——`main` 的
   `src/`、`web/src/`（排除 `*.test.ts(x)`）、`web/package.json`、`web/package-lock.json`、
   `pyproject.toml`、`uv.lock`、`native/` 必须与 **`e8e1dba`** 一致（`git diff e8e1dba <merge-commit> -- …` → exit 0，空 diff）。
   同时 `python -c "from summit_everything.release import fingerprint_web_dist; …"` 应为 `784ae1ee…`。
   **结果（2026-10-16）：** ✅ 产品树等价性实测通过——`git diff --stat e8e1dba 12280ec -- src tests web/src web/package.json web/package-lock.json pyproject.toml uv.lock native` **输出为空（空 diff / exit 0）**。
2. **记录合并事实，并区分两个 SHA**：
   - 记录 merge commit SHA、其触发的真实 CI run id 与 conclusion；
   - 明确写出 **「PR head ≠ 受测产品 SHA」**：受测产品 SHA 是 `e8e1dba`，而 PR head 是清理后的
     docs/cleanup tip（`ebb6b6f0` 及其后的文档提交）。清理提交只动 `docs/**` 与 workflow 显示名，
     **不改变产品树**，因此 `e8e1dba` 的离线门结论仍然适用，但**不能**把「PR head 绿」当作产品面新证据。
   - 在 [PROGRESS](../implementation/PROGRESS.md) / `docs/handoff/LATEST-IMPLEMENTATION.md` /
     `README.md` 的**当前正文**里直接纠正合入事实（按 AGENTS：不在顶部叠加互相覆盖的状态段）。
   **结果（2026-10-16）：** ✅ merge commit `12280ec1893f8f526b9b73a84b98416545254f42` 与 CI run [`38834559855`](https://github.com/yifeng93/SummitEverything/actions/runs/38834559855)（`headSha=8ded0d9`，success，3m25s）已记录于 [LATEST-IMPLEMENTATION.md](LATEST-IMPLEMENTATION.md) 新节，并同步更正 [README](../../README.md) 与 [PROGRESS](../implementation/PROGRESS.md) 的当前正文；**「PR head ≠ 受测产品 SHA」**已写明（受测产品 `e8e1dba`、清理 QA 受测 `7a448c3`、被合并 tip `8ded0d9`）；`main` 的 merge commit 本身未触发新 run。
3. **把被取代的当前页移入历史**：`NEXT-AFTER-FRONTEND-D.md` 移入
   `docs/handoff/history/` 并加历史归档声明（正文保留原样），随后由本文件接续「下一步」入口。
   **本文件落盘时不要执行这个移动**——它现在仍是当前页。
   `FRONTEND-EXECUTION-PLAN.md` 已在顶部加状态块指向本文件，正文保留为历史执行序，**同样不移动**。
   **结果（2026-10-16）：** ✅ 已执行——`NEXT-AFTER-FRONTEND-D.md` 已 `git mv` 为
   [history/2026-10-15-NEXT-AFTER-FRONTEND-D.md](history/2026-10-15-NEXT-AFTER-FRONTEND-D.md)，
   顶部已加历史归档声明（正文原样保留），「下一步」入口由本文件接续。
4. 合并后如再改产品，必须重跑真实 CI；CI 已实测「本 PR 上任何 push 都会触发该 workflow」，
   合并后该行为可能改变，需重新观察而不是沿用假设。

## 3 · 下一个阶段的候选方向（按依赖排序）

### 3.1 D-3 契约补全（最小、无阻塞，建议第一个做）

- **目标**：让 `GET/PUT /api/v1/first-use/progress` 的 OpenAPI 描述**实际存在**的应答状态：
  `401 unauthenticated`、`404 first_use_progress_absent`、`503 progress_unavailable`
  （现状只声明 `200`/`422`）。
- **理由**：前端已经**依赖** 404 做控制流（无记录 → 落到今日并不遮罩），但契约未声明它；
  这是「行为正确、文档不完整」的 INFO 级缺口，也是唯一一个纯契约、无产品行为变化的项。
- **允许面**：`src/summit_everything/api/app.py` 的路由声明与
  `web/src/api/generated.ts`（`npm --prefix web run api:types` 重新生成）；
  文档同步 `docs/contracts/API-v1.md` 与 `docs/implementation/PROGRESS.md`。
- **验证**：`uv run pytest`（不得低于 692 passed）；`npm --prefix web run api:types` 后
  `git diff --exit-code -- web/src/api/generated.ts` → 0；`ruff check`/`ruff format --check`/`mypy` exit 0；
  导出 OpenAPI 后断言三个状态码出现在该 path 上；前端 vitest 222 不降；build exit 0。
- **风险**：改路由装饰器可能被误读为「行为变化」——**只加文档/声明**，不改状态码与载荷；
  契约一旦声明 404，就要有对应测试固定它，避免以后被静默改掉。

### 3.2 前端剩余守卫与页面切片

- **目标**：对照 [FRONTEND-GUIDE.md](../product/FRONTEND-GUIDE.md) 与
  [FRONTEND-PAGE-SPECS.md](../product/FRONTEND-PAGE-SPECS.md) 清点尚未落地的守卫与逐页区块顺序，
  按依赖排成小切片（每片一个可复验提交）。
- **允许面**：`web/src/**`（含测试）、`docs/product/**`、`docs/implementation/PROGRESS.md`；
  后端仅在契约需要时按 3.1 的规则改。
- **验证**：vitest（≥222 passed / 0 todo）、`test:e2e`（≥2）、`test:e2e:integration`（≥1）、
  typecheck / lint / build 全 exit 0；跨视口矩阵按既有 harness 重跑并留截图证据；
  **10 条 UI 契约守卫不得静默改动**，区块顺序是规格，改了必须同文件同步。
- **风险**：规格与实现漂移（历史报告里已出现过「旧表述与新决议并存」）；照旧 `web/src/api/generated.ts`
  由 `api:types` 生成，禁止手改；字号 <12px、主界面出现英文 ID / 路径 / 原始 JSON、空态被画成加载态
  都是硬违规。

### 3.3 工作包 B/C 真实模型与飞书的授权准备

- **目标**：把真实 provider / 飞书 OAuth / 真实业务材料从 NOT_RUN 推进到**可执行的授权准备卡**
  （精确到资料路径、动作、范围与回滚），而不是直接调用。
- **允许面**：准备卡与验收矩阵文档（`docs/handoff/M42-PACKAGE-A-READINESS.md` 同类）、
  `docs/quality/ACCEPTANCE.md` 的未测项登记；**真实凭据与真实材料不入库**。
- **验证**：准备卡本身要求「用户逐项选定材料 / 范围 / 动作」；任何真实调用必须由用户单独授权，
  并在授权后单独留证（真实 run 的 id、日志、结论）。
- **风险**：授权面写成宽泛的「打开真实连接」会越权；默认自动测试不得调用付费模型或创建真实飞书任务；
  真实「场地与酒店」仍有专门内容确认门。

### 3.4 native GUI 独立复现的授权

- **目标**：让 **QA 或第三方**独立复现 D 门的三条 native 路径（已完成→今日；未完成 open→恢复原 step；
  设置里手动续接原 step），而不是只依赖 Sol 实机的本机 Vision OCR 判读。
- **允许面**：隔离 checkout 中的 QA harness 与 `docs/quality/reports/evidence/**`；
  **不改产品实现、不改已有 tracked 测试**。
- **验证**：需要 macOS 辅助功能权限或人工点击配合；候选包按 `e8e1dba` 重建
  （`.app`/`.dmg` 已随本轮清理删除，**不可再取**，只能用 SHA-256 与 `build-info.json` 核对重建结果）。
- **风险**：无 GUI 能力的执行者无法完成，必须提前确认权限与人工配合；重建出的候选若与
  `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b`（DMG）不一致，
  说明源码或构建环境已漂移，**不得**沿用旧的 native 结论。

## 4 · 仍未关闭项

- **D-3（INFO）**：`GET/PUT /api/v1/first-use/progress` 的 OpenAPI 只声明 200/422，未声明实际存在的
  401/404/503；前端依赖 404 `first_use_progress_absent` 做控制流。小切片。
- **D-5（P3，用户已决议接受）**：新建工作库后未推进就 reload/重启会落到今日并给非阻塞提示
  （`create` 意图只在内存）。
- **D-2（P3，dev 专属）**：React StrictMode 下旧 localStorage 迁移会发两次载荷相同的 PUT；
  生产构建恰好一次。
- **200% 浏览器菜单缩放与原生 `pageZoom`**：**NOT_RUN**（640 CSS px 只是 reflow，root CSS zoom 只是 simulation）。
- **native GUI 的独立复现**：D 门的三条 native 路径由 Sol 实机以本机 Vision OCR 判读通过；
  QA 无 GUI 能力、**未独立复现**。
- **真实门**：真实 provider / 飞书 OAuth / Keychain 生命周期 / 真实业务材料 / 已安装 App /
  Developer ID 与公证 / 五日 / 双机 / 生产与发布，全部 **NOT_RUN**，各自需用户按准备卡单独授权。
- **合并本身**：**已关闭**——PR #21 已于 2026-10-16T01:27:08Z 按用户明确批准合入，merge commit `12280ec`；Sol 未自行 merge，「Sol 不 merge」原则保持。
- **原「本片上报的待裁决残留」（见 DEV 报告 §11）已全部收口**：`DELETIONS.md` 内 2 条
  `../DELETED-PATHS-INDEX.md` 相对路径错字**已由 `7a448c3` 修为 `../../`**；
  `docs/quality/reports/README.md` 索引缺口 **0/121**（QA 报告入库后 121/0）；
  范围外删除条数以**实测 36** 为准。
  细节见 [QA 报告](../quality/reports/2026-10-15-PRE-PR21-CLEANUP-QA.md) 与
  [DEV 报告](../quality/reports/2026-10-15-PRE-PR21-CLEANUP-DEV.md) §11 的收口记录。

## 5 · 边界

- 任何**真实门**（真实服务 / 凭据 / 飞书 / Keychain / 真实材料 / 已安装 App / 公证 / 发布 /
  五日 / 双机）都要**用户单独授权**，按准备卡逐项指定资料路径、动作与范围；未授权时记为 NOT_RUN，
  继续其他离线开发。
- **不得删测试或降低验收门**；失败不得靠删测试或降低期望结果收口。
- `src/summit_everything/domain/content.py` 仍是内容指纹与检索资格的唯一基准；
  Python / TypeScript 类型与 OpenAPI 是 API 真源，界面不复制可信资格算法。
- 新工作库不初始化 Git、不 commit、不 push；真实业务原件、`.venv`、`node_modules`、构建产物不入库。
- 执行者与验收者分离：执行者实现并自测、固定 SHA；验收者在**独立 checkout** 对固定 SHA 验收并留证，
  不修改产品实现或已有 tracked 测试。
