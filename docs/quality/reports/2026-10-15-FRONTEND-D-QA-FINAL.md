# 前端 UX 里程碑 D 最终独立 QA（固定 SHA `e8e1dba`）

- 受测产品源码 SHA：`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`（父 `96fdf4d7cccfd71bd1719d4318e0e399309e8281`，分支 `codex/frontend-ux-20261015`）。
- QA 判定：**PASS（限定范围）**。范围 = D-6 收口 + 改动面最小性 + 证据可继承性 + 12 条自动检查 + D-1/D-4/P1 黑盒重新取证 + tree 清洁。
- 范围外一律不计入判定：native GUI 人工验证、DMG/安装/发布日期门、真实 provider/飞书/Keychain/材料、真实 CI 运行、PNG 视觉判读。
- 受测 checkout HEAD=`e8e1dba`，`git status --porcelain` 空，`HEAD^{tree}` 取证前后同为 `7f3b658d…`（未改产品/测试）；分支 tip 就是 `e8e1dba`。未 push / merge / 删 branch 或 worktree。
- 证据根：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-repair3/SummitEverything/.local/qa/frontend-d-repair3/`（含 harness、logs、截图为同步 `.txt` 快照、`EVIDENCE-MANIFEST.sha256`，共 114 个文件）。

## 逐项结论

### ① D-6 收口 — PASS

`npm --prefix web run api:types` exit 0；`git diff --exit-code -- web/src/api/generated.ts` **exit 0**；更严格的两文件形式（含 `openapi.json`）也 exit 0；生成后 `git status` 空。

**门非空对照**：QA 在自建父 SHA checkout 上跑同一门 → **exit 1**（原始 diff 只有 `@@ -1753,6 +1753,11 @@` 的 +5 行 JSDoc）。门没有变软。

QA 另核对：`.github/workflows/m41-internal-app.yml` 原文确为 `npm --prefix web run api:types` + `git diff --exit-code -- web/src/api/generated.ts`（该文件在 `96fdf4d..e8e1dba` 无改动）。**信息级提示**：CI 门只 diff `generated.ts`（不含 `openapi.json`）；且该 workflow 的 push 触发分支只有 `codex/m41-internal-app-*`，本分支 push 不自动触发（PR / dispatch 才触发）——所以这是本地精确复现 CI 步骤，不是观测到真实 CI 运行。

### ② 改动面最小性 — PASS

`git diff --stat 96fdf4d e8e1dba` → **只有** `web/src/api/generated.ts`（+5 −0）；`git diff --quiet 96fdf4d e8e1dba -- src` exit 0；`native/`、`tests/`、`scripts/`、`docs/` 逐路径全 EMPTY；+5 行全部是 `FirstUseProgress` 上的 JSDoc 注释。

### ③ 证据可继承性 — 成立，但 QA 明确指出命题边界

QA 在两个 SHA 上**各自独立构建** `web/dist`，并用**自己重实现的指纹算法**（`harness/qa_r3_fingerprint.py`，与产品 helper 对拍一致）算出三处指纹完全相同 = `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`：`e8e1dba` 构建、`96fdf4d` 构建（在跑 `api:types` 之前构建）、开发者候选包 `SummitEverything-D-e8e1dba.app/Contents/Resources/web`。两次构建的 4 个产物文件**逐个 sha256 相同**（不是碰巧同哈希）。候选包 `build-info.json` 实测 `source_sha=e8e1dba`、`dirty=false`、`frontend_sha256=784ae1ee…`。机理核对：`generated.ts` 无任何运行期导出，9 处引用全部 `import type`，vite 未开 sourcemap → 编译期擦除，与实测字节一致。

**QA 的诚实反驳（Sol 认同并采纳）**：把「上一次 PASS 可继承」当作证据链替代品**不严谨**——它依赖「构建可复现 + 继承面完整」这一需要单独验证的强前提；若 vite/版本漂移或打开 sourcemap，结论就翻转。**可继承的是「产物行为结论」，不可继承的是「在该 SHA 上运行过」这一事实。** 因此 QA 的 ④⑤ 全部在**新 SHA 上重新取证**，PASS 独立成立。

### ④ 自动检查 12/12 exit 0

`pytest` **692 passed, 1 warning**；`ruff check` All checks passed；`ruff format --check` 100 files already formatted；`mypy` Success（47 source files）；`uv lock --check` OK；`uv build` OK（QA 额外补了 CI 里的这一步）；`vitest` **26 files / 222 passed**（无 todo/skipped）；`typecheck` OK；`lint` **2 warnings / 0 errors**；`build` OK；`test:e2e` **2 passed**；`test:e2e:integration` **1 passed**。计数与 Developer 声称一致。

### ⑤ D-1 / D-4 / P1 — PASS（在新 SHA 重新取证）

- **HTTP 黑盒 54/54 exit 0**：真实 uvicorn + 真实 socket + 手写 JSON。`3.0/2.0/4.0/5.0/2e0/3e0/5.0e0` 全 422；`3.5/true/"3"/null/6/0/-1/[]/{}` 全 422；真整数 `2/3/4/5` → 200 且落盘为 JSON 整数；extra/secret 字段 422；OpenAPI 仍 `integer enum [2,3,4,5]`。
- **浏览器黑盒 51/51 exit 0**（生产 `web/dist` + 后端新进程 + 全新空 context）：G2.7 P1「重开已配置工作库 → Today，wizard=null」、G2.8「无向导、无 backdrop」、G3.3 D-1「`open` 且无记录 → Today」、G3.4「backdrop=0」、G3.6 中性非阻塞 toast、G3.8/G3.9/G3.11 全 PASS；G1.2 `create` 仍进向导第 2 步（正向对照）。G4 组另验证了「无记录工作库仍可从设置手动走完并向该库写出 `{step:5,completed:true,open:false}`」。
- 明确未做：本轮**未**在父 SHA 上重跑 D-1 修复前症状的非空性对照（上一轮 QA 已做过），本轮只对 D-6 门做了父 SHA 对照。

### ⑥ Tree 清洁 — 受测 checkout PASS；开发者 worktree 有 N-1

## 新发现

- **N-1（Nit / 过程级，非产品缺陷）**：QA 取证期间开发者 worktree 的 `git status --porcelain` 非空（两处未跟踪 docs）。已核实：纯未跟踪文档、无 tracked 改动、HEAD 仍 `e8e1dba`、产品/测试字节不变；候选包 `build-info.json` 的 `dirty=false` 时间（22:47:57）早于这些文档写入，且 `build_macos_app.py` 用 `--untracked-files=all` 判定 dirty，若打包时存在会拒绝构建，因此**不影响候选身份**。QA 的建议（提交或移出）已在本轮随后的 docs 提交中执行。

## 关键原件 SHA-256

| 原件（相对 `.local/qa/frontend-d-repair3/`） | SHA-256 |
|---|---|
| `QA-REPORT.md` | `619893cb7f5dfbb121ce25b29afdfc4f6ac10c99a3fe3fa2ddc467dd210d0c93` |
| `EVIDENCE-MANIFEST.sha256` | `50c6796058971c7f00f52759546ce903a9c01f20dd0d84e14d51395ddfbf10ad` |
| `logs/01-d6-gate-e8e1dba.log` | `a217325000bfade3a35535e1b618967441c259ac832f6cfbcf302ea16f2c505b` |
| `logs/09-d6-gate-post-harness.log` | `9dd2dce836fd163da4b2285b8be7f42dde2491421fd9fe682e980729068ee14d` |
| `logs/07-http-harness.log` | `a0b9192ca3d71e146be9bfe17e6d4ac39e7916d30cefadff64212da1937f2786` |
| `logs/08-browser-harness-prod.log` | `51c6bb23f97ed00c9c8e9f159e41b93ba327bc63e18df4e68aabe72619f8c033` |
| `logs/04-python-suite.log` | `29b72dccc7cda2b99ba6ced548ec19bd5c440b760c0fea4d944d6d28e307265d` |
| `logs/05-web-suite.log` | `431a5859e904769cb377bbd78f95ae02d2200e7b60c20afc911caea8710497fe` |
| `logs/parent/01-d6-gate-96fdf4d.log` | 父 SHA 非空性对照（同门 exit 1） |
| `harness/qa_r3_fingerprint.py` | `ffb98e5f08e90c1760e009d036442005c2421fc9d90529f597dff6bdbb6ae2a3` |

QA 也按纪律保留了自身 harness 首次失败的 raw：`logs/08-browser-harness-prod.failed-raw.log`（第一次因缺 `playwright` 包 `ERR_MODULE_NOT_FOUND` 崩溃，随后修正环境重跑，未覆盖原始失败日志）。
此 tracked 摘要不复制 trace、profile、token 或真实数据。

## NOT_RUN / UNVERIFIED（QA 自述）

- **NOT_RUN**：native WKWebView 同 profile 重启与开发者人工点击验证（QA 无 GUI 能力，**未独立验证**；QA 对候选包只做静态制品核查：`build-info.json` + `Resources/web` 指纹）；`.app`/`.dmg` 启动、`smoke_packaged_app.py`、`swift test`、`release-macos.sh`/DMG 构建与 codesign/hdiutil（不在该轮范围）；**PNG 视觉判读**（模型不支持图像输入，未视读任何 PNG；结论全部基于 DOM 断言、HTTP 响应、磁盘字节与同步 `.txt` 快照）；父 SHA 的 D-1 修复前行为对照（本轮未重跑）；真实 provider / 飞书 OAuth / Keychain / 真实材料 / 双机 / 五日；**真实 CI 运行**（本分支 push 不触发该 workflow）。
- **UNVERIFIED**：历史「PASS 可继承」作为结论替代品的严谨性（QA 已给出反例条件并改用新 SHA 重新取证）。
