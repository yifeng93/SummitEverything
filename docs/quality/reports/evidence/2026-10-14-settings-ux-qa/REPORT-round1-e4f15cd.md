# QA 独立复核报告 — `e4f15cdfe54be2e8b2b426d9b440eecf2b5ff7e9`

独立 QA（非实现者）。未修改产品实现或已有 tracked tests，未 commit/push。
worktree：`/Users/yifengstudio/.codex/worktrees/settings-ux-qa-e4f15cd/SummitEverything`

## 1. 身份核对 — PASS

| 检查 | 命令 | 结果 |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `e4f15cdfe54be2e8b2b426d9b440eecf2b5ff7e9` ✅ |
| 起始工作树 | `git status --porcelain` | 空 ✅ |
| 分支 tip | `git rev-parse codex/settings-ux-20261014` | `0747133d0869ed6a229f19e60c7e7029c68d0e21` |
| 差异范围 | `git diff --name-status e4f15cd..codex/settings-ux-20261014` | `M README.md`、`M docs/handoff/LATEST-IMPLEMENTATION.md`、`M docs/implementation/PROGRESS.md`、`A docs/quality/reports/2026-10-14-SETTINGS-UX-DEV.md`；84 insertions |

结论：产品/测试/lock/web/pyproject 树与该 SHA 完全一致，多出的两个提交是纯文档（含根目录 README.md）。

## 2. 全量自动测试 — PASS

- `UV_CACHE_DIR=<wt>/.local/uv-cache uv sync --locked --group dev` → exit 0，Installed 40 packages。
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` → **558 passed, 1 warning, exit 0**（78.55s）。
- 隐式依赖核对：验收开始时 `.local/first-use/defaults.json` **不存在**（`ls` exit 1），无法做「改名后重跑」。改为更强的正反验证：
  1. 在 `.local/first-use/defaults.json` 写入四个键的诱饵文件（sha256 `923952f72e37…dac4`）后重跑全量 → **558 passed, exit 0**；
  2. 删除诱饵，确认路径再次不存在。
  另有一条 tracked 测试固定 `REPO_DEFAULTS_RELATIVE_PATH` 不是查询源。结论：不存在对本机忽略文件的隐式依赖。

## 3. 静态检查 — PASS

| 命令 | exit | 结果 |
|---|---|---|
| `uv run ruff check src tests` | 0 | All checks passed! |
| `uv run ruff format --check src tests` | 0 | 91 files already formatted |
| `uv run mypy src` | 0 | no issues in 46 source files |
| `uv lock --check` | 0 | — |

## 4. 前端 — PASS

| 命令 | exit | 结果 |
|---|---|---|
| `npm ci` | 0 | added 126 packages, 0 vulnerabilities |
| `npm test` | 0 | 14 files / **90 tests**（交付树基线） |
| `npm run typecheck` | 0 | — |
| `npm run lint` | 0 | 2 warnings, 0 errors |
| `npm run build` | 0 | CSS 34.77 kB / JS 365.68 kB |

lint 的两条 warning 均为既有文件、与本次提交无关：`ProjectsView.tsx:40`（最后改动 `7e3ed60`）、`TodayView.tsx:80`（最后改动 `4c6b0bd`）；`4c27238` 未触碰这两个文件。
加入我的 QA 文件后重跑：15 files / **97 tests**，typecheck exit 0，lint 仍 2 warnings / 0 errors（34 files）。

## 5. 契约未变 — PASS

`uv run python scripts/export_openapi.py` → exit 0；`git status web/` 空、`git diff --stat web/openapi.json` 空；再 `openapi-typescript openapi.json -o src/api/generated.ts` → 仍无 diff；随后从 git 复原，确认无残留改动 → 契约逐字节未变。

## 6. 注入语义黑盒（自建 harness）— PASS

Harness：`.local/qa/test_qa_first_use_injection.py`（26 tests，全部 PASS；`uv run pytest -q .local/qa/test_qa_first_use_injection.py` exit 0）。

- (a) 注入文件在时 `GET /api/v1/settings` 返回四个注入值，`mode=fake`、三个 provider 仍 `fake`，且尚未落盘。✅
- (b) 原样 `PATCH` 这四个值后，profile `provider-settings.json` 中 `feishu.app_id` / `feishu.redirect_uri` / `embedding.base_url` / `rerank.base_url` 四键**均不存在**。✅
- (c) 用同一 profile_root、换注入文件重建 app 后（`mode:"open"` 重开工作库），读到新值；`mode` 仍 fake。✅
- (d) 显式提交非默认值后落盘并固定，换注入文件仍是用户值，未覆盖的字段跟随新默认值。✅
- (e) `deepseek_api_key` / `dashscope_secret` / `feishu_app_token` / `feishu_app_password` / `some_credential_blob` 使 `create_app` 抛 `first_use_defaults_secret_key`；未知键抛 `first_use_defaults_unknown_key`；非法 JSON 抛 `first_use_defaults_invalid`；`str/repr(exc)`、`caplog`（DEBUG）均**不含值明文**，`__cause__ is None`。显式 `SUMMIT_FIRST_USE_DEFAULTS` 指向缺失路径即使 bundle 存在也致命失败。✅
- (f) http、非 aliyuncs HTTPS 主机、错误 path、带 query、带 port、飞书 callback 非 loopback/错 path 全部被拒（`first_use_defaults_value_invalid`），且同一值用 `ProviderSettings.model_validate` 直接校验同样 `ValidationError` —— 证明复用原 validator、无旁路，错误文本不含值。✅

## 7. 证伪两条主张 — 未证伪（在已测范围内成立）

自建文件：`web/src/components/QaIndependent.test.tsx`（7 tests，全部 PASS），挂载真实 `SettingsView`/`FirstUseWizard` 并记录全部 fetch。

- a) 向导挂载（含自动打开）、前进/后退/跳过（1→2→1→2→3→2→3→4→3→4→5→4→5）、关闭、重新打开再走一遍：**无非 GET 请求**，且只有 3 个本地 GET（`/settings`、`/provider-smoke`、`/integrations/feishu/status`）各 1 次，无 `/provider-smoke/*`。✅
- b) 三个检查逐个「点按钮→弹确认面板→取消」全程 0 次 POST；确认 Rerank 后恰好 1 条 `POST /provider-smoke/model-studio-rerank`，再确认 DeepSeek 后恰好 1 条对应路径，全程无 embedding POST；设置页卡片同样需确认、取消不发。保存密钥（向导 step2 与设置页卡片两条路径）后 0 次 provider-smoke POST。✅
- c) 向导与卡片两条路径：`Storage.prototype.setItem` 未被调用，`localStorage/sessionStorage` 长度 0，`document.cookie`、`window.name` 不变，秘密值不出现在任何 URL/`outerHTML`；提交后密码输入框清空；正对照：秘密值仅出现在 PUT body。✅

## 8. 打包候选 — PASS

- DMG SHA-256 自算：`ce79a8c355c89e420606e3882b918b6dd9c993009b3df633bc25c52df5a0d68c`，与声称**逐字节一致**。✅
- `SUMMIT_APP="…/SummitEverything Internal.app" uv run --locked python scripts/smoke_packaged_app.py` → exit 0，`PASS: onedir backend starts with empty PATH; identity, static UI, unauthorized reads/writes, port conflicts, and parent-pipe cleanup verified`。✅
- 包内 `Contents/Resources/first-use-defaults.json` 与主仓库来源 `.local/first-use/defaults.json` 等值：sha256 均为 `23f3b3f95e633b16f6d36e718052a0924916df67d8c9368d0ce758c4c0e004e1`，`cmp` exit 0，各 324 字节，仅含四个允许键。✅
- `build-info.json`：`source_sha=e4f15cdfe54be2e8b2b426d9b440eecf2b5ff7e9`、`dirty=false`、`build_id=20261014T132453Z-0d21a90f194c`、`app_version=0.1.0`、`frontend_sha256=0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0`、`dependencies_sha256=2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。✅
- 额外自建冻结端到端：`.local/qa/qa_packaged_injection.py` → **6/6 PASS**：冻结二进制经 `sys.frozen` 真实解析包内资源并返回四个注入值；保存后 profile 无四键；含 `deepseek_api_key` 的注入文件使后端启动失败（rc=1）且 **stderr 不含明文**。全程 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 强制 `UnavailableSecretBackend`，未读写真实钥匙串。

## 9. 缺陷与风险

- **D1（真实存在，低危，未被实现者记录）**：注入默认值会**掩盖损坏 profile 的失败关闭**。当 defaults 存在且某可注入 section 落盘为「非 dict」时，`FirstUseDefaults.apply` 用 `{}` 替换再验证，`SettingsStore.read()` 不再抛 `SettingsError`。复现见 `.local/qa/test_qa_first_use_injection.py::test_qa_risk4_a_corrupted_section_can_be_masked_by_an_injection`（无注入 `SettingsError`；有注入静默成功）。影响范围限于 `feishu`/`embedding`/`rerank` 被写成非对象；不涉及网络或密钥。
- **R1（已披露）**：本功能之前保存过的 profile 落盘旧公共端点会被当作显式选择，不跟随新注入（`test_qa_risk1…` 证实）。
- **R2（表述偏强）**：「profile 只记录用户显式覆盖」略强于实现：显式提交的值若**恰好等于当前注入默认值**会被删键、不固定（`test_qa_risk2…` 证实）；用户无法把当前注入值「钉住」。
- **R3（低危）**：密钥保存顺序为先 `PATCH /settings`（落盘 Real + 启用所选能力）后 `PUT /credentials`；若钥匙串写入失败，profile 已切 Real 且能力启用但无密钥。此时 `smokeCheckDisabled` 因凭据缺失保持按钮禁用，不会外呼；界面留在第 2 步并报错。
- **R4（范围）**：实现者声称的包内 23/23 未用其脚本复跑；我以 6 项自建端到端复核核心语义，结论一致。
- **R5（已披露）**：新界面/向导无浏览器或真机视觉复核，我也未做。

## 未测 / 受阻

- 真实 provider、真实飞书账户/OAuth/scope、真实材料与账单、正式安装/覆盖、Developer ID/公证、Gatekeeper、五日、双机：NOT_RUN（超出授权）。
- macOS Keychain 生命周期：NOT_RUN；本轮以 guard 强制不可用后端，未读写真实钥匙串。
- `.local/first-use/defaults.json` 的「改名后 sha256 不变」检查：N/A（开始时不存在）。
- 未挂载 DMG 做安装级验证；仅校验 DMG 哈希与归档 App 内容。
- runtime 模型元数据：UNVERIFIED（未测）。

## 新增文件（未提交）

- `.local/qa/test_qa_first_use_injection.py`（ignored）
- `.local/qa/qa_packaged_injection.py`（ignored）
- `web/src/components/QaIndependent.test.tsx`（untracked）

最终 `git status --porcelain` 仅一行 `?? web/src/components/QaIndependent.test.tsx`；`git diff` 为空；HEAD 仍为 `e4f15cd…`。
