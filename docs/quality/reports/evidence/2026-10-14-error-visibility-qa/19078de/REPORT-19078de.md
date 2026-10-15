# QA 验收报告 — 固定 SHA `19078dedb62655c4090051ee5e2159068ef5f607`

独立 worktree：`/Users/yifengstudio/.codex/worktrees/qa-19078de/SummitEverything`（detached HEAD）
环境：`UV_CACHE_DIR=<worktree>/.local/uv-cache`；guarded 命令 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`
约束遵守：未修改产品实现与 tracked tests，未 commit/push，未联网、未调用真实 provider、未写真实钥匙串。

## 1. 身份与范围 — PASS

| 检查 | 命令 | 结果 |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `19078dedb62655c4090051ee5e2159068ef5f607` |
| 起止工作树干净 | `git status --porcelain` | 空（起、止均为空） |
| 改动清单 | `git diff --name-status a301b1b..19078de` | 13 个文件（6 src + 6 tests + 1 doc） |
| 未改前端 | `git diff --name-only a301b1b..19078de -- web/` | 0 个文件 |

改动：`api/app.py`、`intake/review.py`、`integrations/{embedding,http_boundary,llm,rerank}.py`、`local/event_log.py`；
测试：`test_assist_and_index_failure_records.py`(A)、`test_provider_failure_visibility.py`、`test_llm_schema_tolerance.py`、`test_profile_event_log.py`、`test_provider_error_reporting.py`。

## 2. F1 — 200 但内容不可用 → 类型化 provider 错误 + API 502 — PASS

harness：`.local/qa/test_f1_unusable_200.py`（30 passed）

- 类型化：embedding 9 种坏形态 + 4 种非 JSON；rerank 7 种坏形态 + 2 种非 JSON；全部 `EmbeddingProviderError`/`RerankProviderError`，`reason=="schema"`，`details()=={}`，`str()` 含「无法解析」，哨兵不出现。
- API 502：真实 adapter + MockTransport 经 `/api/v1/index/jobs` 逃逸到异常处理器 →
  `502` + `error.code=provider_error` + `message="向量服务不可用：返回内容不符合应用要求的字段。"`（可读、无 `sk-`、无哨兵）。
- 反向边界：embedding（空批、超批、空白、超长）与 rerank（空候选、超量、空 query、空候选文本、超长请求体）
  均为**裸 `ValueError`**（`type(exc) is ValueError`，非 `ProviderError`），且**不发起任何 HTTP**（handler 抛断言即失败）；
  API 层本地校验仍 `422 validation_error`。

## 3. F2 — `/api/v1/journal/assist` 原因可见且本地留证 — PASS（含 1 处残留，见 §11 D1）

harness：`.local/qa/test_f2_f6_and_hygiene.py`（36 passed）

- 类型化失败：`502` + `error.code=assistant_unavailable` + 消息含 `InsufficientBalance`/`request-5`/「已保存内容未更改。」；
  `diagnostics.log` 末条 `assistant_failed`、`state=failed`、`reason` 含 provider code。
- transport/deadline/schema/bare ProviderError 四种类型化失败均保留具体分类，不使用固定文案「AI 辅助暂时不可用」。
- 未知异常：客户端仍是安全文案，无哨兵、无本地路径；`reason=="RuntimeError"`（仅类型名）。
- 未运行分支：real 模式的 acceptance-plan assist 分支仅代码审阅（需 real 模式 + 真实 provider），它调用同一 `assistant_failure`/`record_assistant_failure`。

## 4. F3 — provider-smoke 三响应带 `error.provider{code,message,request_id}` — PASS

真实 adapter + MockTransport 400/403/500/402：

- embedding → `provider={code:"invalid_api_key",message:"Invalid API-key provided.",request_id:"body-request-7"}`；`code=provider_smoke_failed`；无 key 泄漏。
- **rerank（上一轮缺失的那条）** → 结构完全一致（PASS）。
- LLM → `InsufficientBalance` + `llm-req-3`。
- 仅传输层 `x-request-id`（body 无）时 embedding/rerank 都取到 `hdr-9`。

## 5. F4 — request-id 采用与优先级 — PASS

`bounded_json_post` 直测：非 2xx 只带 header → 采用；body 优先于 header；两者都无 → `None`；
非法形状 header（`bad id!`/超长/空/含空格）→ `None`；2xx 仍读 header（`ok-request-1`）；
`request-id`、`x-dashscope-request-id`、body 顶层 `id` 均生效；经 smoke API 到达 `error.provider.request_id`。

## 6. F5 — 索引失败落在 `diagnostics.log` — PASS（含残留，见 §11 D1）

- 增量索引失败：`index_update == "update_failed"`（字段语义不变），`diagnostics.log` 出现 `index_update_failed`/`state=failed`；
  成功写入仍为 `updated`；哨兵文本与本地路径**不进**该文件。
- 类型化失败：记录洗过的 provider 详情（`invalid_api_key` + `req-11`）。
- **例外**：reason 含掩码凭据（`sk-***`）或超 200 字符时事件被静默丢弃（§11 D1）。

## 7. F6 — `GroundedAnswer.text` 空白判失败 — PASS

`""`、`"   "`、`"\n\t"`、`"\u3000\u00a0"`、`" \n \t "` 全部 `ValidationError`；正常文本被 `strip` 但内容不丢；
经 `DeepSeekLLM.answer`（MockTransport 返回 `{"text":"   "}`）→ `LLMProviderError(reason="schema")` →
smoke `502` + 「返回内容不符合应用要求的字段」；非空文本仍 `200 succeeded`。

## 8. 一致性与卫生 — PASS

- provider 侧统一 **502**：`LLMProviderError`/`ProviderError`/`EmbeddingProviderError`/`RerankProviderError`
  四个已注册处理器实测均 `502` + `provider_error`（LLM 上一轮的 503 已改为 502）。
- 本地校验保持 **422**：`credential_shape_invalid`、`validation_error`。
- 失败记录脱敏写入点：assist/索引诊断、查询 DB 记录、`review.py` intake job 的 `error` 字段、
  `profile_event` 的 `_validated_reason`（原始 `sk-`/多行/空/超长直接 `ValueError`）。
  实测：含 `sk-…` 的异常文本落库/落日志时被打码为 `sk-***`，原始串不出现；intake job 端到端返回 `sk-***`。

## 9. 未回归 — PASS

| 检查 | 退出码 | 关键输出 |
|---|---|---|
| `uv run pytest -q`（guarded 全量） | 0 | `649 passed, 1 warning in 78.46s` |
| `uv run ruff check src tests` | 0 | `All checks passed!` |
| `uv run ruff format --check src tests` | 0 | `97 files already formatted` |
| `uv run mypy src` | 0 | `Success: no issues found in 46 source files` |
| `uv lock --check` | 0 | `Resolved 48 packages in 3ms` |

## 10. 打包候选 — PASS

- DMG 自算：`cb6af3781bcf948eab496ca208fdb8321368b89f9ae6b5ad89f8bf9a457118d1` → **与声称一致**。
- `Resources/first-use-defaults.json` 与 `.local/first-use/defaults.json`：SHA-256 相同（`23f3b3f9…`）+ 语义深比较相等。
- `build-info.json`：`source_sha=19078dedb6…`、`dirty=false`、`build_id=20261014T154135Z-0d21a90f194c`。
- `SUMMIT_APP=… uv run python scripts/smoke_packaged_app.py` → `PASS: onedir backend starts with empty PATH; …`，exit 0。
- 自建只读探测 `.local/qa/probe_packaged_backend.py`（隔离 HOME/profile，`SUMMIT_OFFLINE_GUARD_ACTIVE=1`，只发非法形状凭据，**不写真实钥匙串**）exit 0：
  - 包内压缩模块字符串 7/7 命中本轮新增文案（含「向量/排序服务返回了无法解析的响应」「index_update_failed」「assistant_failed」「assistant_unavailable」「answer text must not be blank」「credential_shape_invalid」）；
  - `health.source_sha=19078de…`、`dirty=false`；未授权读 `401`；建库 `201`；
  - 坏密钥形状 `422 credential_shape_invalid`；超长形值 `422` 且不回显。

## 11. 继续找残留 — 发现 1 处同类吞错（D1）

### D1（FAIL）诊断事件在 reason 含掩码凭据或超 200 字符时被静默丢弃

位置：`src/summit_everything/local/event_log.py:66 _validated_reason`（拒绝含 `sk-`、拒绝 `len>200`）
配合 `src/summit_everything/api/app.py` 的 `record_assistant_failure`（`:530`）与索引失败块（`:1834`），
两处都 `except (ValueError, OSError): pass`。

两条独立触发路径：

1. **掩码后仍含 `sk-`**：`sanitize_provider_text` 把凭据掩成 `sk-***`，而 `sk-***` 仍含子串 `sk-` → 守卫拒绝。
   实测（真实边界 + 真实错误构造）：
   ```
   provider_message -> 'Authentication Fails, Your api key: sk-*** is invalid'
   assist diagnostics reason -> '模型服务返回错误：invalid_api_key — Authentication Fails, Your api key: sk-*** is invalid'
   contains 'sk-': True | length: 80
   event -> DROPPED: invalid diagnostic reason | file exists: False
   ```
   这正是最常见的 `invalid_api_key`（provider 常回显 key）场景。
2. **超 200 字符**：`provider_message` 上限 300、`code` 上限 100、`request_id` 上限 200，
   渲染后的 reason 极易 >200。实测 `provider_message="m"*258` → reason 长 301 → 事件丢弃。

影响：`assistant_failed` 与 `index_update_failed` **完全不存在**（`diagnostics.log` 都不生成）。
客户端面仍正确（502 + 洗过的文案），所以既有 tracked tests 全绿；索引路径仍有一行
`logging.getLogger(__name__).error(...)` 带完整 reason，但按本轮前提「打包后无 handler、stderr 被丢弃」，它不构成可检索留证。
这属于本轮目标（F2「两种情况都在本地留证」、F5「出现可检索的失败事件」）在相邻路径的残留。

证据测试（我新增、故意断言期望行为，故 FAIL）：`.local/qa/test_residuals.py` R1–R4、
`.local/qa/test_sweep_entry_points.py::test_sweep_typed_assist_error_that_sanitizes_to_sk_star_star_star`。

修复方向（QA 不实现）：掩码产物不要命中自身守卫（如 `***`）、`_validated_reason` 对已掩码值改为截断而非抛错、
调用方在守卫拒绝时回退到异常类型名而非丢弃整条事件。

### 已实际检查的入口（逐项实测结论）

| 入口 | 结论 |
|---|---|
| provider-smoke（LLM/embedding/rerank） | PASS：结构化 `error.provider{code,message,request_id}` |
| `journal/assist`（fake 分支） | PASS：类型化原因可见 + 留证；未知异常安全文案 + 类型名留证 |
| `journal/assist`（real/acceptance-plan 分支） | **NOT_RUN**：仅代码审阅（需 real 模式 + 真实 provider），复用同一 helper |
| `index/plans`、`index/jobs`、批准后增量索引 | PASS：类型化 502；失败 `update_failed` + 诊断事件（D1 例外） |
| `queries`（SSE）+ conversations DB 记录 | PASS：类型化原因进 `message` 与 DB `error` 字段，未知异常保留 `RuntimeError` |
| settings / credentials | PASS：`422 credential_shape_invalid`、`422 validation_error`、`503 credential_store_unavailable`/`credential_missing`（不吞原因） |
| 飞书 status/materials/calendar | PASS：`FeishuError` 非 `ValueError`，因此 `imports`/`calendar` 的 `except ValueError → 422` 不会吞掉 provider 原因；未授权/无效参数返回设计好的 code+message |
| intake items/jobs + job `error` 字段 | PASS：端到端 `502 provider_error`，持久化 `error` 为 `sk-***`（原始 secret 不入文件/响应），且经 `GET /api/v1/jobs/{id}` 可见 |
| memory candidates / roles | PASS：`422 validation_error` |
| conversations 列表/读取 | PASS：编码化 404/422；POST 非路由（405） |
| 未检查 | 真实飞书网络调用、真实钥匙串后端路径、answer_context、actions、导出/备份 — 未实测，不做结论 |

## 12. 我在 `.local/qa/` 新增的文件（未 commit，`.local/` 已被 `.gitignore:19` 忽略）

- `qa_common.py`（共享 fixture/helper）
- `conftest.py`（把本目录加入 `sys.path`）
- `test_f1_unusable_200.py`（30 用例，F1）
- `test_f2_f6_and_hygiene.py`（37 用例，F2–F6 + 卫生）
- `test_residuals.py`（R1–R4，故意 FAIL 的残留证据）
- `test_sweep_entry_points.py`（入口扫描；1 条故意 FAIL）
- `probe_packaged_backend.py`（打包后端只读探测，exit 0）
- `REPORT-19078de.md`（本报告）

## 13. 未测 / 受阻项

- 上述 real 模式 assist 分支、真实飞书、v1 计划中真实 provider/材料/凭据/钥匙串/DMG 安装/五日/双机等门：**未测**。
- 结论仅限定在本文实际执行的范围；不构成「整体通过」。
