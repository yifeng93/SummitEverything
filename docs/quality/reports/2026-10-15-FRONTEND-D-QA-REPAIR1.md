# 前端 UX 里程碑 D repair1 独立 QA（固定 SHA `faa1edd`）

- 受测产品源码 SHA：`faa1edd611a74dcdc26bff234de810bdf47761cb`（父产品 SHA `876008e1d33420f57fb31772c76e471379e6b98d`，分支 `codex/frontend-ux-20261015`）。
- 门判定（QA 自判，限定范围）：**PASS**。初次 P1 在产品代码层**已修复**，且 QA 用**同一份自建 harness 做了修复前/后对照**，排除「harness 太软」的可能。
- 适用边界：真实 FastAPI + 真实 WebUI（含 `web/dist` 生产构建）+ 全新 browser context（空存储）+ **真实后端进程重启**（杀进程另起新 uvicorn）+ 隔离 profile/工作库，offline guard 开启。
- **native WKWebView 同 profile 重启 = NOT_RUN**（本轮未建包、未启 GUI），不得用浏览器结果冒充。因此这**不是** D 里程碑整个门的 PASS。
- QA 独立重跑的数字与 Developer 声称**零差异**：Python 686 passed、Web 220 passed / 0 todo（26 files、0 skipped）、默认 e2e 2 passed；typecheck / lint（2 warnings / 0 errors，父 SHA 重跑确认为既存）/ build / ruff check / ruff format / mypy(47 files) / uv lock 全 exit 0。
- QA 未复用开发者任何测试文件，自行编写 3 个 harness（HTTP 级 store/契约、浏览器端到端、静态服务）。**产品源码零修改**；两个 QA checkout 与开发者 worktree 的 `git status` 均为空；未 push / merge / 删 branch 或 worktree。

## 最强证据：同一 harness 的修复前 / 后对照

| | 父 `876008e`（生产构建） | 受测 `faa1edd`（生产构建） |
|---|---|---|
| 重启 → 打开已有工作库 | 向导「第 2 步 · 模型与密钥」，today=false | **Today，无向导** |
| 结果 | 20 checks / 12 passed / **8 failed**，exit **1** | 64 checks / **64 passed**，exit **0** |
| 日志 | `logs/08-parent-876008e-comparison.log` | `logs/01-02-03-05-browser-and-e2e.log` |

父 SHA 的 8 条失败包含 QA 标注为 `***P1 CORE***` 的 S1.12 / S1.13 / S1.14，以及关闭后重启仍弹向导、后端 404 无记录等；这正是初次 QA 的 P1，说明 harness 具备真实判别力。

## ①–⑧ 逐项

| 项 | 判定 | 证据（均在 QA checkout 的 ignored `.local/qa/frontend-d-repair1/`） |
|---|---|---|
| ① 重演 P1 并确认修复（真实后端 + 生产 Web） | PASS | `logs/01-02-03-05-browser-and-e2e.log`（S1.1–S1.15）、`screenshots-prod/01–05` |
| ② 未完成 open 恢复原 step／明确关闭不自动弹且设置手动续接／飞书直达第 4 步／无记录从第 2 步 | PASS | 同上 S2.1–S2.5、S3.1–S3.2、S4.1、S5.1 |
| ③ 旧 localStorage 一次性迁移、迁移后删除、无长期双写、非法形状不迁移 | PASS | 同上 S6.1–S6.5、S7.1–S7.3、S8.1–S8.3；`src` 内首配路径已无 `localStorage.setItem` |
| ④ store 隔离／白名单／拒绝密钥字段且不落盘／原子／并发不损坏／损坏失败关闭／新进程重读 | PASS | `logs/04-05-06-http-harness.log`（33/33，exit 0）；新进程重读另由浏览器 harness 的真实 uvicorn 重启覆盖 |
| ⑤ 写失败停原步骤 + 可见 + 可重试 + 无假成功；读失败留 Today + 不误报完成 + 设置仍可开向导 | PASS | 浏览器 harness S9.2–S9.12、S10.1–S10.6；截图 14–19 |
| ⑥ 401/409/404/503 契约；OpenAPI 逐字节一致 | PASS | HTTP harness A1–A5、D1、D4；`logs/06-openapi.log` |
| ⑦ 独立重跑全部自动检查 | PASS | `logs/07-*.log`、`logs/01-02-03-05-browser-and-e2e.log` |
| ⑧ 主动证伪 | PASS（附观察） | S1.9、S8.1、S10.1–S10.3、S11.1–S11.2、S12.1–S12.7、A13、S7.3 |

OpenAPI 门复验：`scripts/export_openapi.py` 重生成后与 tracked `web/openapi.json` **bytes IDENTICAL**；`openapi-typescript` 重生成与 `web/src/api/generated.ts` **IDENTICAL**；运行后 `git status` 为空；diff 形状 +131/−0 与 +103/−0，新增 1 path + 1 schema，**无删除、无既有 schema 改动**。

## 缺陷与观察

### D-1（P3，残余；非回归）pre-repair1 已配好、本机无记录的工作库会被再拉进向导一次，且关闭前 Today 不可达

最小复现：新建工作库到向导第 2 步（**不要**点关闭）→ 重启后端进程 + 全新 browser context → 打开该已有工作库 → 向导自动出现在第 2 步、today=false；点左侧「今日」导航被 `.wizard-backdrop` 拦截；点「关闭向导」后到达 Today 并写入 `{step:2,completed:false,open:false}`，此后不再复现（自愈）。
证据：`screenshots-prod/20–23`、日志 S12.1–S12.7。
影响：父 SHA 在同场景下更差（完全进不去 Today），所以**不是回归**；且与「不按『有凭据』猜测首配完成」的既定约束一致，属设计取舍。开发者的未验证项原文只写「会再看到一次向导」，**低估了后果**（未说明会挡住 Today）。若门要求「老工作库不得被再次 onboarding」，这是 follow-up（QA 建议 P2）。

### D-2（P3，dev 专属）React StrictMode 下旧 localStorage 迁移会发 2 次相同 PUT

dev trace：`["-> GET","<-404","-> PUT","<-404","-> PUT","<-200","<-200"]`，两次载荷逐字节相同；**生产构建同一场景恰好 1 次 PUT**。幂等、不损坏、不影响打包产物；但「只做一次性迁移」的表述需限定为生产构建语义。

### D-3（INFO）OpenAPI 只声明 200/422，未描述实际存在的 401/404/503

前端依赖 404 `first_use_progress_absent` 做控制流，但该状态未进入契约描述。

### D-4（INFO）`{"step": 3.0}` 被 `Literal` 归一化接受

返回 200 并在落盘前归一化为 JSON 整数 `3`（磁盘上不会出现浮点）；`1/0/6/"3"/2.5/null/true/-1/4.5` 均 422。前端只发 `2/3/4/5`，产品面不可达。证据：HTTP harness A9 / A9b。

## 证据处理说明（Sol 已核对）

- QA 的最初一版 HTTP harness 把 `3.0` 列入「必须 422」并因此 exit 1。QA 随后判定这是**期望写错**（JSON Schema 的 integer 允许零小数部分的数字），于是把该用例改写为**更强的观察断言 A9b**（断言 200、归一化为整数 3、磁盘无浮点），同时把 `bad_steps` 由 8 项扩为 9 项（新增 `-1`、`4.5`），总数 32→33 且全绿。
- Sol 核对：这是**修正错误期望并加强断言**，不是删测试或降低验收门；A9b 断言的实际行为比原先的错误期望更具体。`bad_steps` 仍覆盖 `1/0/6/"3"/2.5/null/true/-1/4.5`。
- 一处**证据处理瑕疵**：HTTP harness 那条最初失败的 raw 日志被 33/33 的运行**覆盖**，未像浏览器 harness 那样留档（浏览器 harness 的中间失败运行已留档为 `logs/archive-harness-iteration-superseded.log`）。该发现本身仍被 D-4 记录并以 A9b 固定，因此不改变判定；但原始失败 raw 未保留，后续应避免覆盖。
- 证据内**无 token、无真实数据**（Sol 已做凭据形状扫描，无命中）。

## 关键原件 SHA-256

| 原件（相对 `.local/qa/frontend-d-repair1/`） | SHA-256 |
|---|---|
| `QA-REPORT.md` | `ddbf22f0dfdff040ecb4720310e774e814d0368120d716d82298b11dab0e6c29` |
| `run-prod/results.json` | `0f715b484e9250d4c7935332c4561c0faaf90d81d14bd99dc9aaf9b9c0b7c671` |
| `run-dev/results.json` | `ccfc504c4bd231d2ee3e85c9fb173bef4bfc533cfb3c4939e04a4ae6c4806b4a` |
| `logs/04-05-06-http-harness.log` | `08650d38d9831fb97fd25c34f2a991e05e64682472fd79a4934237ea759aa88c` |
| `logs/01-02-03-05-browser-and-e2e.log` | `6c133302cedec5f94a80eb21941d491bd55e88e9923ff9e95205ca87fdadbdf8` |
| `logs/08-parent-876008e-comparison.log` | `d5df10dfa5b23b543cba0969e5e92138332557d9ba51b4b19603d3874ce86e0b` |
| `logs/06-openapi.log` | `0c2727fbacf844e90c3ed93e778078cee4b4d04902015b0824f288bc076ccd8d` |
| `logs/archive-harness-iteration-superseded.log` | `1a04fa258f8b9e467750682d2ce775a37e70f0522d9bea30a49fbadad96eaa8c` |

完整原件、harness、逐条日志与截图在：
`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1/SummitEverything/.local/qa/frontend-d-repair1/`
对照（父 SHA）checkout：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair1-parent/SummitEverything`（HEAD `876008e`）。二者均保留，未被删除或改写。此 tracked 摘要不复制 trace、profile、token 或真实数据。

## NOT_RUN / UNVERIFIED

- **NOT_RUN**：native WKWebView 同 profile 重启（无新候选 App/DMG）；新 macOS 候选 / DMG / manifest / hash / build ID；真实 provider / 飞书 OAuth / Keychain / 真实材料 / 已安装 App / Developer ID / 公证 / 五日 / 双机 / 生产；200% 菜单缩放与原生 `pageZoom`；Swift；876 的旧视口全矩阵与「十条变异」。
- **UNVERIFIED**：「打包后 WKWebView 丢弃 localStorage、而 `local_profile_dir` 持久」这一前提假设——QA 用「空存储 context + 后端新进程 + 磁盘真实记录」建模验证了落点，但未在真实 WKWebView 内直接验证该存储语义；Keychain 可用分支；大规模压力与断电注入；同库多窗口并发改步骤。
