# 设置 UX / 首次配置注入：第三轮独立 QA 报告

- 受测 worktree：`/Users/yifengstudio/.codex/worktrees/settings-ux-qa-8c4f81c/SummitEverything`
- HEAD：`8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b`（detached，`git status --porcelain` 空）
- 环境：macOS arm64、Python 3.12.13、`uv 0.12.3`、Node v24.15.0 / npm 11.12.1
- 全部 harness 在 `.local/qa/`（Git 忽略），未修改任何产品实现或 tracked tests，未 commit / push
- 付费模型：未调用。真实飞书：未写。真实钥匙串：未写（离线 guard 存在性查询路径亦未触及写接口）
- 本报告结论只覆盖实际执行范围，不构成「整体通过」

## 逐项判定

| # | 项目 | 判定 |
|---|---|---|
| 1 | 身份 | **PASS** |
| 2 | F1 字段级修复（本轮核心） | **PASS**（含旧树对照 72 处失败） |
| 3 | D1 section 级回归 | **PASS** |
| 4 | 注入语义回归 a–f | **PASS** |
| 5 | 全量自动测试 | **PASS**（591 passed / exit 0） |
| 6 | 静态检查 | **PASS** |
| 7 | 前端 | **PASS** |
| 8 | 打包候选 | **PASS** |
| 9 | 冻结端到端 | **PASS** |
| 10 | 新缺陷 / 结论过强处 | 见下（F2 既有确认、F3 新增测试隔离缺口、2 条观察） |

---

## 1. 身份 — PASS

```
$ git rev-parse HEAD
8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b
$ git status --porcelain            # 起始与结束均为空
$ git diff --name-only 8c4f81c..76ca47d
docs/decisions/0010-first-use-configuration-ux.md
$ git diff --stat 8c4f81c..76ca47d
 docs/decisions/0010-first-use-configuration-ux.md | 7 +++++++
$ git merge-base --is-ancestor 8c4f81c 76ca47d    # YES（76ca47d 是 8c4f81c 之后的 docs 提交）
```

结论：HEAD 精确等于指定 SHA；工作树干净；与候选 manifest 的 `source_sha=76ca47d` 之间差异**仅一个 docs 文件（+7 行）**，产品树相同。

## 2. F1 字段级修复 — PASS

harness：`.local/qa/f1_field_level_probe.py`（4 字段 × 6 非字符串值 × {无注入, 四键全注入} × {store read, API GET, 直调 handler}，外加空串语义与 PATCH 抹除检查）

```
$ PYTHONPATH=scripts/offline_guard:src uv run --locked python .local/qa/f1_field_level_probe.py
EXIT=0        # 149 checks, 0 failures
```

覆盖值：`int 123 / list [1,2] / dict {"nested":true} / true / false / null`，四个字段
`feishu.app_id`、`feishu.redirect_uri`、`embedding.base_url`、`rerank.base_url`。

结果（新树）：
- 24 个「无注入」组合：`SettingsError(settings_unavailable)`；
- 24 个「有注入」组合：同样 `SettingsError(settings_unavailable)`（这正是 F1 修复点）；
- 48 个 API `GET /api/v1/settings`：**无一返回 200**（实测全部 500，原因见 F2）；
- 48 次直调路由 handler（绕开中间件）：全部抛 `SettingsError(settings_unavailable)`，即设计中的 503 路径已被触发；
- 空串/纯空白：**仍按「未设置」处理**，注入后四字段全部等于注入值（`status=200`），未误判为缺陷；
- 48 次「损坏后 PATCH」：`provider-settings.json` 字节不变，损坏值未被静默抹掉。

**对照证据（旧树 6d41d35）**：`git archive 6d41d35 src scripts/offline_guard | tar -x -C /tmp/qa-r3/old-6d41d35`，把**同一文件字节**（sha256 `6e4749a9…e0b1`）拷到旧树运行：

```
$ PYTHONPATH=/tmp/qa-r3/old-6d41d35/scripts/offline_guard:/tmp/qa-r3/old-6d41d35/src \
    uv run --locked python /tmp/qa-r3/old-6d41d35/probe.py
# probe source tree: /private/tmp/qa-r3/old-6d41d35/src/summit_everything/__init__.py
EXIT=72       # 149 checks, 72 failures
```

72 = 24(store 有注入) + 24(API 有注入返回 200) + 24(handler 有注入未抛错)，分布严格按字段 6/6/6/6；
无注入项、空串语义项在新旧树结果完全一致。失败原文示例：

```
FAIL | store F1 feishu.app_id=int with-injection raises | {"embedding": {...valid injection...}}
FAIL | api F1 feishu.app_id=int with-injection not 200 | status=200 {...}
```

→ F1 修复有效，且判别器只指向修复点；仓库本身未被改动。

## 3. D1 section 级回归 — PASS

harness：`.local/qa/d1_section_level_probe.py`（`feishu`/`embedding`/`rerank` × `str/list/int/null/bool/含列表的映射` × 有/无注入；另加「section 合法但另一字段损坏」；另加 24 个 API 组合）

```
$ PYTHONPATH=scripts/offline_guard:src uv run --locked python .local/qa/d1_section_level_probe.py
EXIT=0        # 66 checks, 0 failures   （API 24 组全部 status=500，非 200）
$ （同一文件在旧树 6d41d35）EXIT=0  # 66 checks, 0 failures
```

section 级非映射在有/无注入下都抛 `SettingsError`；`{}` 之外的损坏未被注入「修好」；section 合法但 `identity/dimensions/provider` 非法时仍拒绝。

## 4. 注入语义回归 a–f — PASS（38/38）

harness：`.local/qa/injection_semantics_probe.py`（走真实 `SUMMIT_FIRST_USE_DEFAULTS` → `load_first_use_defaults` → `create_app` 路径）

```
$ PYTHONPATH=scripts/offline_guard:src uv run --locked python .local/qa/injection_semantics_probe.py
EXIT=0        # 38 checks, 0 failures
```

- **a** GET 返回四个注入值（与注入文件逐字段相等），且 `mode/llm/embedding/rerank` 全为 `fake`；
- **b** 原样回填 PATCH 后 profile 中四键**均不存在**，文件全文不含四个注入值的任何明文；
- **c** 同一 profile 换注入文件（store 级与「重启后重新打开同一 workspace」两条路径）均跟随新值；
- **d** 显式非默认值落盘且不被后续注入覆盖；PATCH 空串后回落注入默认；
- **e** secret 形态键（`feishu_app_secret`/`app_token`）、未知键、非法 JSON、非映射 JSON、非字符串值、显式路径缺失：全部 `FirstUseDefaultsError` 失败关闭；错误文本与捕获日志中**无值明文**（非字符串值那条例外消息精确等于
  `first_use_defaults_invalid source=<path> fields=feishu_app_id`）；成功加载的 INFO 日志只含字段名不含值；
- **f** 非法 URL（外部域名、http 而非 https、callback 非回环、embedding 用了 `/api/v1` 路径、app_id 超长）全部被**原 validator** 拒绝（`first_use_defaults_value_invalid`，只报字段位置不回显值）；显式非法 base_url 不会被注入「修好」；API PATCH 非法 URL → 422 且不落盘。

另有 `.local/qa/f1_edge_probe.py`（21/21 PASS）覆盖：`0 / 0.0` 不被修好；注入不会「补齐」因其它原因非法的 section；显式 `"0"`、带空格字符串一律原样保留不被注入顶替；空 section 被补齐。

## 5. 全量自动测试 — PASS

```
$ export UV_CACHE_DIR=$PWD/.local/uv-cache
$ uv sync --locked --group dev          # EXIT=0
$ PYTHONPATH=$PWD/scripts/offline_guard:$PWD/src uv run pytest -q
591 passed, 1 warning in 77.94s (0:01:17)
PYTEST_EXIT=0
```

与实现者自述的 591 一致（唯一 warning 为 starlette TestClient 的 httpx 弃用提示，非本功能引入）。

**附加 A/B（本报告新增，不是验收项要求）**：把环境变量指向本机真实忽略文件再跑全量 → 见第 10 节 **F3**。

## 6. 静态检查 — PASS

| 命令 | 退出码 | 结果 |
|---|---|---|
| `uv run --locked ruff check src tests` | 0 | All checks passed! |
| `uv run --locked ruff format --check src tests` | 0 | 91 files already formatted |
| `uv run --locked mypy src` | 0 | Success: no issues found in 46 source files |
| `uv lock --check` | 0 | Resolved 48 packages |

## 7. 前端 — PASS

```
$ cd web && npm ci      # EXIT=0, added 126 packages, 0 vulnerabilities
$ npm test              # EXIT=0  14 test files passed / 90 tests passed (1.68s)
$ npm run typecheck     # EXIT=0  (tsc -b)
$ npm run lint          # EXIT=0  2 warnings, 0 errors  (oxlint, 33 files)
$ npm run build         # EXIT=0  dist: index.html 0.62kB / CSS 34.77kB / JS 365.68kB
```

`lint` 的 2 条 warning 位于 `ProjectsView.tsx:40`、`TodayView.tsx:80`（react `set-state-in-effect`）：
`git diff --name-only a6faf7e..8c4f81c` **未触及这两个文件**；并在导出到 `/tmp/qa-r3/web-old/web` 的
**功能前源码树（a6faf7e）**上直接跑同一 `oxlint`（28 files）→ **同为 2 warnings / 0 errors**。
判定：**既有 warning，非本功能引入**。

## 8. 打包候选 — PASS

DMG：`/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/settings-ux-8c4f81c/SummitEverything-Internal-8c4f81c.dmg`

```
$ shasum -a 256 ...SummitEverything-Internal-8c4f81c.dmg
966cf3ae278db6ab0d2c6f60629e63d4cc7b3f2bae9f977333e6682e753eaeab   # 与声称值逐字符一致
$ hdiutil verify <dmg>   → CRC VALID (exit 0)
```

包内 `build-info.json`（App 目录与挂载后的 DMG **完全一致**）：

```json
{"app_version":"0.1.0","build_id":"20261014T134528Z-0d21a90f194c","dirty":false,
 "source_sha":"76ca47d40f42d232f3d50b480b92961b507fb646",
 "frontend_sha256":"0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0",
 "dependencies_sha256":"2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f"}
```

- 自算 `fingerprint_web_dist(Resources/web)` = `0d21a90f…21f0` = manifest → **匹配**；`build_id` 含其前 12 位；
- 自算 `dependencies.json` sha256 = `2aa53e0c…fe5f` = manifest；`verify_dependency_manifest` OK；
- **`first-use-defaults.json` 三方等值**（`shasum -a 256` 全部为 `23f3b3f95e633b16f6d36e718052a0924916df67d8c9368d0ce758c4c0e004e1`）：
  App 目录内 / **挂载后的 DMG 内** / 本机来源 `/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/first-use/defaults.json`；
  键集合恰为四个允许键（值长度 20/58/75/63，报告中不转录明文）；挂载后已干净 `detach`。

```
$ SUMMIT_APP="<App>" uv run --locked python scripts/smoke_packaged_app.py
PASS: onedir backend starts with empty PATH; identity, static UI, unauthorized reads/writes,
      port conflicts, and parent-pipe cleanup verified
SMOKE_EXIT=0
```

## 9. 冻结端到端 — PASS（85/85）

harness：`.local/qa/frozen_e2e.py`（包内后端二进制**原地**运行；隔离 `HOME`/`TMPDIR`/`SUMMIT_PROFILE_ROOT`；`PATH=""`；`SUMMIT_OFFLINE_GUARD_ACTIVE=1`；`SUMMIT_FIRST_USE_DEFAULTS` 显式 unset，唯一注入来源为包内资源）

```
$ SUMMIT_APP="<App>" PYTHONPATH=scripts/offline_guard:src uv run --locked python .local/qa/frozen_e2e.py
EXIT=0        # 85 checks, 0 failures
```

- health 身份（`source_sha`/`build_id`/`frontend_sha256`/`run_id`）与 build-info 一致；静态 UI 200；
- **包内 `first-use-defaults.json` 生效**（无环境变量、非开发机文件），`mode/llm/embedding/rerank` 全 fake；离线 guard 下 `keychain_available=false`；
- 原样回填 PATCH 后 profile：四键不存在、无值明文（622 字节）；
- **字段级损坏 20 组（4 字段 × int/list/dict/bool/null）→ 状态直方图 `{500: 20}`，无一 200**；每组 read 与 PATCH 后 profile 字节均不变；
- **section 级损坏 12 组（3 section × str/list/int/null）→ `{500: 12}`**；
- 非注入字段损坏（`llm.account_id=123`）→ 同样 500 且响应体为裸 `Internal Server Error`（F2 基线，见第 10 节）。

补测失败关闭（`.local/qa/failclosed_startup_probe.py`，16/16 PASS）：
- 进程内 `create_app` 对缺失显式路径 / secret 形态键抛 `FirstUseDefaultsError`，**不降级为空默认**；
- 冻结二进制遇 secret 形态键 / 非法 JSON / 未知键 / 缺失路径 → **均非零退出（exit=1）**，输出中**无值明文**（同名 grep 命中 0）；stderr 原文含
  `FirstUseDefaultsError: first_use_defaults_secret_key source=<path> fields=deepseek_api_key`；
- 有效显式文件可正常启动并覆盖包内值；**部分键的显式文件不会与包内文件合并**（first-candidate-wins，见观察 O2）。

---

## 10. 新缺陷、既有行为确认与结论过强处

### F2（既有、非本轮引入）— 确认存在，且用户影响明确
`origin_guard` 中间件在 workspace 打开后每次请求都直接 `SettingsStore(...).read()`，**无 try/except**。
profile 损坏时 `SettingsError` 在中间件层抛出，Starlette 的 exception handler 覆盖不到 → **裸 500 `Internal Server Error`**，而非设计中的 JSON 503。

- 本轮实测：本树 48/48 损坏请求、冻结包 32/32 损坏请求全部为 500；
- **既有性证据**：`git show a6faf7e:src/summit_everything/api/app.py`（功能前提交）第 497-500 行同样是无保护的
  ```python
  if workspace is not None:
      settings = SettingsStore(Path(workspace.local_profile_dir) / "provider-settings.json").read()
  ```
  → 与本功能无关，未被误判为本轮引入；
- 非注入字段（`llm.account_id`）损坏给出同样的裸 500，证明与注入逻辑无关；
- **实际影响**：profile 一旦损坏，**经 API 无法修复**（任何请求都 500，包括用于修复的 PATCH），用户只能手改文件。判定沿用第二轮：**F2 不在本轮修复范围，仅确认既有行为**。

### F3（本轮新增：测试隔离缺口 / 结论过强）— 测试套件非环境无关
`.local/qa/` 之外的 A/B 复现：

```
$ SUMMIT_FIRST_USE_DEFAULTS=/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/first-use/defaults.json \
  PYTHONPATH=$PWD/scripts/offline_guard:$PWD/src uv run pytest -q
33 failed, 558 passed, 1 warning in 77.68s          # exit 1
$ ... 同上，但环境变量未设置
591 passed, 1 warning                                # exit 0
```

- 33 个失败分布：`tests/integration/test_feishu.py` 32 个 + `tests/integration/test_feishu_real_gate.py` 1 个；
- 根因：`tests/` 下**没有任何测试**固定注入来源（`grep -rn "first_use_defaults=\|FirstUseDefaults.empty()" tests` 无命中），23 个调用 `create_app()` 的测试文件全部继承环境变量；
- 机制最小复现：
  ```
  $ printf '{"feishu_app_id": "cli_synth_id"}' > /tmp/appid-only.json
  $ SUMMIT_FIRST_USE_DEFAULTS=/tmp/appid-only.json ... uv run pytest -q \
      tests/integration/test_feishu_real_gate.py::test_real_mode_without_an_app_id_is_reported_as_unconfigured
  1 failed   # AssertionError: assert 'acceptance_plan_required' == 'provider_not_configured'
  $ printf '{"embedding_base_url": "https://ws-synth0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"}' > /tmp/embed-only.json
  $ SUMMIT_FIRST_USE_DEFAULTS=/tmp/embed-only.json ... （同一批测试）
  2 passed
  ```
  即失败由注入的**飞书值**（`app_id`/`redirect_uri`）改变「已配置」状态与假 OAuth 回调端口引起，与 embedding/rerank 注入无关。
- 定性：**不是产品缺陷**——默认（环境变量未设置）门禁全绿 591 passed，冻结包行为正确；这是**测试套件未隔离注入源**的缺口，且实现者自述「两次全量对比各为 558 passed / exit 0，证明无隐式依赖」在 `8c4f81c` 上**不可复现**。风险是验证卫生：任何 shell/CI 导出了该变量都会看到 33 个伪失败；也可能掩盖真实的「注入后行为」断言。

### O1（观察，既有、非本功能）— LLM 模型字段的校验宽松
手写 profile `{"llm": {"provider": "deepseek"}}`（**缺 `model` 键**）会被接受为 `provider=deepseek, model=None`：
pydantic 对**未出现的键**不运行 field validator（`LLMSettings.model_matches_provider`），而 `EmbeddingSettings`/`RerankSettings` 用的是 `mode="after"` 的 model validator，故同样形状被拒。
证据：`{"llm":{"provider":"deepseek","model":null}}` → 拒绝；`a6faf7e`（功能前）同样接受 → **既有行为**。
**经 API 不可达**：`PATCH {"llm":{"provider":"deepseek"}}` → 422（merge 后 `model` 键存在为 null）。判定：低危、需手工改 profile，非本轮引入。

### O2（观察，已文档化）— 显式注入文件整体替换包内文件，不做合并
`load_first_use_defaults` 是 first-existing-candidate-wins：设置 `SUMMIT_FIRST_USE_DEFAULTS` 且文件存在时，**包内 `Resources/first-use-defaults.json` 不再被读取**。
冻结包实测：显式文件只含 `feishu_app_id` 时，`embedding.base_url` 回落为模型内置默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`，**不是**包内的业务空间地址（已在 `.local/qa/failclosed_startup_probe.py` 断言并输出）。
模块 docstring 已声明该优先级，且该路径仅由开发者/QA 显式 opt-in（`scripts/run_dev.py` 只在文件存在时 setdefault）。判定：**已文档化的设计取舍，非缺陷**；若未来把它当作生产覆盖手段，需注意「部分键 = 其余键退回内置默认」。

### O3（观察）— 失败关闭的呈现是原始 traceback
被拒绝的注入源在冻结包中表现为 PyInstaller 的 `Failed to execute script 'packaged_server' due to unhandled exception!` + Python traceback（exit 1）。失败关闭与「不回显值」都满足，仅是运维呈现粗糙；与 build-info 缺失等其它启动异常同形，非本功能特有。

### 对实现者自述的核对
- 「注入只在字段缺失或字符串去空白后为空时填充」——**证实**（第 2、4 节）；
- 「显式非空值一律保留交给原 validator」——**证实**（含 `"0"`、带空格字符串、`0`/`0.0`/null 等边界）；
- 「空串视为未设置」——**证实**（空串与纯空白均补注入值）；
- 「无仓库隐式回退」——**证实**（`git ls-files` 无任何 defaults 文件被跟踪；运行时只认 env 与包内资源；`run_dev.py` 为显式 opt-in）；
- 「DMG SHA-256 `966cf3ae…`、`source_sha=76ca47d`、`dirty=false`」——**证实**；
- 「`SUMMIT_FIRST_USE_DEFAULTS` 有/无两次全量各 558 passed」——**证伪**（F3：本机真实文件在场时 33 failed / 558 passed）；
- 报告中的 558 与当前 591 的差异可由后续新增测试解释，不视为矛盾。

## 新增文件（均未 commit；`.local/` 已被 `.gitignore:19` 忽略）

- `.local/qa/f1_field_level_probe.py` — F1 字段级矩阵 + 旧树对照（149 checks）
- `.local/qa/d1_section_level_probe.py` — D1 section 级（66 checks）
- `.local/qa/injection_semantics_probe.py` — 注入语义 a–f（38 checks）
- `.local/qa/f1_edge_probe.py` — 边界正/负例（21 checks）
- `.local/qa/failclosed_startup_probe.py` — 进程内 + 冻结启动失败关闭（16 checks）
- `.local/qa/frozen_e2e.py` — 冻结端到端（85 checks）
- `.local/qa/REPORT-round3.md` — 本报告
- 临时对照树（仓库外）：`/tmp/qa-r3/old-6d41d35/`、`/tmp/qa-r3/old-a6faf7e/`、`/tmp/qa-r3/web-old/`

## 未测 / 受阻项（NOT_RUN）

- 真实 provider / 真实飞书账户与 OAuth scope / 真实业务材料 / 账单与答案质量：**NOT_RUN**（无授权与凭据，且本轮禁止）；
- macOS 钥匙串生命周期（写入/删除/首次授权弹窗）：**NOT_RUN**（本轮不写真实钥匙串）；冻结包仅覆盖 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 下的不可用分支；
- 浏览器/真机视觉复核与人工向导走查：**NOT_RUN**（只有组件测试与构建产物；与 DEV 报告自述边界一致）；
- 正式安装/覆盖、Gatekeeper/`spctl`、公证、五日试用、双机（M5）：**NOT_RUN**（沿用历史结论，本轮未重新执行）；
- runtime 模型元数据：**UNVERIFIED**；
- 打包脚本本身未重跑（使用已归档候选；仅复核 SHA、包内文件、manifest 与 smoke）。
