# 独立 QA 报告 — SummitEverything 固定 SHA `a301b1b0785fd42d765565324f28b2888467b07e`

- worktree：`/Users/yifengstudio/.codex/worktrees/settings-ux-qa-a301b1b/SummitEverything`（detached HEAD）
- 被测主张：主仓库 `docs/quality/reports/2026-10-14-REAL-FIRST-USE-FINDINGS.md`（待证伪）
- 边界：未修改产品实现 / 已有 tracked tests，未 commit、未 push；未调用真实 provider、未使用真实 key、未写真实钥匙串；全部网络路径用 `httpx.MockTransport` 或打包后端在本机 loopback。
- 环境：`UV_CACHE_DIR=<worktree>/.local/uv-cache`；guarded 命令 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q`。
- 为让 `tests/integration/test_dev_runner.py` 全绿，把主仓库 `web/node_modules` symlink 到 worktree 的 `web/node_modules`（该路径在 `.gitignore`，`git status` 仍为空）。

## 判定汇总

| # | 项目 | 判定 |
|---|---|---|
| 1 | 身份与范围 | PASS（含一处范围澄清） |
| 2 | 真实 payload 容错 + 引用来源证伪 | PASS |
| 3 | 提示词形状 | PASS |
| 4 | provider 错误浮现 | PASS（embedding 路径完全符合；rerank 有一处结构性偏差，见 F3） |
| 5 | 问答错误可见 | PASS |
| 6 | 密钥形状校验 | PASS |
| 7 | 未回归（pytest/ruff/format/mypy/lock） | PASS |
| 8 | 打包候选 | PASS（另加 2 项自建验证） |
| 9 | 诚实性检查 | PASS |
| 10 | 新缺陷清单 | 5 项新发现 + 3 项观察（见下） |

**本报告只覆盖实际执行过的检查；未覆盖 macOS 钥匙串真实生命周期、正式公证安装、五日、双机、真实 provider 可用性。**

---

## 1. 身份与范围 — PASS

```
$ git rev-parse HEAD
a301b1b0785fd42d765565324f28b2888467b07e
$ git status --porcelain        # 起、止各一次，均为空
(空)
$ git diff --name-status bb80b40..a301b1b | wc -l
62
```

- HEAD 与要求的固定 SHA 一致；起止 `git status --porcelain` 均为空。
- `git diff --name-status bb80b40..a301b1b` 共 62 个文件（原始输出见 `evidence/identity-and-scope.txt`）。
- **范围澄清（web/\*\*）：** `bb80b40..a301b1b` 这个**区间**确实包含 10 个 `web/**` 改动（`git diff --name-only bb80b40..a301b1b -- web/`），全部来自区间内的提交 `4c27238 feat(web): card-based settings with a first-use configuration wizard`。**本次修复提交 `a301b1b` 自身没有改任何 `web/**` 文件**：
  ```
  $ git diff --name-status a301b1b^..a301b1b
  M src/summit_everything/api/app.py
  M src/summit_everything/integrations/embedding.py
  M src/summit_everything/integrations/http_boundary.py
  M src/summit_everything/integrations/llm.py
  M src/summit_everything/integrations/rerank.py
  A tests/integration/test_provider_failure_visibility.py
  M tests/integration/test_provider_settings_api.py
  A tests/unit/test_llm_schema_tolerance.py
  A tests/unit/test_provider_error_reporting.py
  ```
  在主仓库报告 `2026-10-14-REAL-FIRST-USE-FINDINGS.md` 中**没有**「未改前端」的表述，故不存在需要证伪的声明；若把范围限定为「本次修复提交」，则「未改前端」成立。

## 2. 真实 payload 容错 — PASS

Harness：`.local/qa/test_qa_payload_tolerance.py`（13 项，exit 0）。全部走真实 `DeepSeekLLM` + `httpx.MockTransport`（`client=` 注入），无网络。

- 真实形状 `source_statements=[{"source_id","quote","type","confidence"}]` + 顶层多余 `type` 键 → **接受**，且归一化为纯字符串：
  `answer.source_statements == ["x: 合成事实：演示地点是北馆。"]`、`answer.text` 非空、`"type" not in answer.model_dump()`。
- 不可读内容全部被**拒绝**（`LLMProviderError`, `reason == "schema"`）：`[{"foo":1}]`、`[1,2]`、嵌套 list、`{"quote":""}`、`text=""`、缺 `text`、`advice=[{"foo":1}]`。
- **引用来源证伪（重点）**：让 mock 返回 `source_statements=[{"source_id":"MODEL-CLAIMED-SOURCE-ID","quote":"模型自称引用自某个并不存在的来源。"}]`，跑真实 `QueryService.query()`（索引为应用自建）：
  - `answer.citations` 非空且 `page_id == 1111…1111`（应用自己检索到的页）；
  - `answer.source_statements` 由 `retrieval/query.py:601` 从**应用自己的 passages** 重建，模型自报 id 与自报 quote **均未出现**在 `source_statements` / `text` 中。
  - 结论：模型自报 `source_id` 不构成引用，引用不可被模型「采信」。
- 附带证伪：模型正文仍被使用（`test_answer_text_from_the_model_is_still_used`），说明容错不是「解析后被丢弃」的假通过。
- 观察（非拒绝项）：`source_statements` 传单个字符串会被包成单元素列表（`normalize_notes` 的既有设计），不是静默丢弃。

## 3. 提示词 — PASS

从**实际发出的请求体**取出 `messages[0]["content"]`（不是读源码），断言存在以下片段：

```
"no additional keys"
'{"text": string, "source_statements": [string], "inferences": [string], "advice": [string], "missing_information": [string]}'
"plain string" / "never an object" / "do not add extra keys such as type or confidence"
```

并确认 `text must be non-empty`，问题与 passages 作为 user 数据传递（`untrusted` 措辞存在）。

## 4. provider 错误浮现 — PASS（含 1 处结构性偏差）

Harness：`.local/qa/test_qa_provider_errors.py`（10 项，exit 0）。真实 adapter + 真实路由，`create_http_client` 注入 `MockTransport`，凭据用哨兵 `sk-abcdefghijklmnop`。

- `{"error":{"message":"Invalid API-key provided. key=sk-…","code":"invalid_api_key"}}`（HTTP 401）经 `POST /api/v1/index/jobs` →
  **502**，`error.code == "provider_error"`，`message` 含 `invalid_api_key` 与 `Invalid API-key provided.`，`error.provider.code/message` 存在，`error.request_id` 存在。
  响应体与日志中**均无**哨兵，出现 `sk-***`（`caplog` 全级别扫描）。
- `{"code":"Model.AccessDenied","message":"Model access denied.","request_id":"req-403-synthetic"}`（HTTP 403）→ 502 + `provider.code/message/request_id == "req-403-synthetic"`。
- **200-带-error** 两种形态都被保留：DashScope 顶层 `code` 与 OpenAI 嵌套 `error` 均 → 502 + `provider_error` + 结构化 details。
- 偏差 F3：`RerankProviderError` 的 502/`provider_error` 处理器**在真实产品路由中不可达**（见第 10 节）。可达的 rerank 路径只有：
  - `POST /api/v1/provider-smoke/model-studio-rerank` → 502 但 `error.code == "provider_smoke_failed"`，**没有** `provider` 结构化对象（`message` 里含 code/message/request id 文本）；
  - `POST /api/v1/queries`（SSE）→ error 事件的 `message` 含 `Model.AccessDenied — Model access denied.（request req-403-synthetic）`。
  我另加一条 harness-only 路由直接触发产品自己的处理器，证明处理器本身形状正确（502 + `provider_error` + `provider.request_id`）。

## 5. 问答错误可见 — PASS

Harness：`.local/qa/test_qa_query_visibility.py`（6 项，exit 0）。用假 query service 注入，读真实 `conversations.sqlite3`。

原始样本（含哨兵 `sk-abcdefghijklmnop`）：

```
--- typed (EmbeddingProviderError) ---
queries.error = 'EmbeddingProviderError: 向量服务返回错误：invalid_api_key — Invalid API-key provided. sk-***'
sse error     = {"code":"query_error","message":"向量服务返回错误：invalid_api_key — Invalid API-key provided. sk-***（request request-77）", ...}
--- unknown (RuntimeError("sentinel sk-… /private/qa-profile")) ---
queries.error = 'RuntimeError: sentinel sk-*** /private/qa-profile'
sse error     = {"code":"query_error","message":"查询未能完成，请稍后重试。", ...}
```

- 类型化：客户端文本含具体原因（`invalid_api_key` / `Invalid API-key provided.` / `request-77`）；`queries.error` 含 `<类型>: <脱敏 message>`。
- 未知异常：客户端仍只显示安全文案 `查询未能完成，请稍后重试。`，**不含** sentinel、路径、`RuntimeError`；但 `queries.error` **两种情况都**写入 `<异常类型>: <message>`（`RuntimeError: sentinel sk-*** /private/qa-profile`），单行、长度 ≤300。
- 任何 `sk-…` 在响应与本地记录中都被打码为 `sk-***`。
- 前端消费确认：`web/src/components/AskView.tsx:396` 用 `String(message.data.message ?? '问答未能完成。')` 原样显示 SSE `message`，与后端一致。

## 6. 密钥形状校验 — PASS

Harness：`.local/qa/test_qa_credential_shape.py`（29 项，exit 0）。`PUT /api/v1/credentials/{provider}`。

- deepseek/dashscope：`sk-`+16 位合法 → 200；`sk-`+15 → 422 `credential_shape_invalid`；总长 512 → 200、513 → 422；含换行/内嵌换行/空格/前导空格/制表符/非 `sk-` 前缀/大写 `SK-`/`pk-` → 422；空串 → 422（由请求模型 `min_length=1` 拒绝，code 为 `validation_error`，早于形状门禁——已如实记录）。
- 飞书 AppSecret：恰好 8 与恰好 512 → 200；7 / 513 → 422；换行、尾换行、空格、制表符、`\r`、NUL 控制字符 → 422。
- **任何拒绝响应都不回显提交值**（逐例断言），且被拒值未落入 profile 目录任何文件。
- 已接受的形状不会出现在 `GET /api/v1/settings` 响应中。

## 7. 未回归 — PASS

```
$ PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q
623 passed, 1 warning in 78.77s
EXIT=0

$ uv run --locked ruff check src tests        → All checks passed!            EXIT=0
$ uv run --locked ruff format --check src tests → 96 files already formatted   EXIT=0
$ uv run --locked mypy src                    → Success: no issues found in 46 source files  EXIT=0
$ uv run --locked uv lock --check             → EXIT=0
```

与主仓库报告自述的「623 passed」一致。注：本次全量运行在 symlink 了 `web/node_modules` 的 worktree 下进行。

## 8. 打包候选 — PASS

- DMG SHA-256 **自算一致**：
  `1a03d997b1a33bb79d7ddb5c4fb62ff58a5537623f679113dccc3f1bd6774803  SummitEverything-Internal-a301b1b.dmg`
- `hdiutil verify` → `checksum … is VALID`，EXIT=0。
- 包内 `Contents/Resources/first-use-defaults.json` 与主仓库本机来源 `.local/first-use/defaults.json` **字典等值**（4 个非密钥键）。
- `Contents/Resources/build-info.json`：`source_sha=a301b1b0785fd42d765565324f28b2888467b07e`、`dirty=false`、`build_id=20261014T152000Z-0d21a90f194c`。
- **额外验证（自建）**：包内 `Resources/web` 的 `fingerprint_web_dist()` 与 `build-info.frontend_sha256` 一致（`0d21a90f…21f0`）；`verify_dependency_manifest()` OK。
- `SUMMIT_APP="…/SummitEverything Internal.app" uv run --locked python scripts/smoke_packaged_app.py` →
  `PASS: onedir backend starts with empty PATH; identity, static UI, unauthorized reads/writes, port conflicts, and parent-pipe cleanup verified`，EXIT=0。
- **额外验证（自建）**：`.local/qa/qa_packaged_probe.py`（`.local/qa/evidence/packaged-probe.log`）——把 bundle 复制到临时目录后启动打包后端（loopback，`SUMMIT_OFFLINE_GUARD_ACTIVE=1` 关闭钥匙串）：
  ```
  PASS health.source_sha: a301b1b0785fd42d765565324f28b2888467b07e
  PASS workspace.create: 201
  PASS credential.shape_invalid: 422 credential_shape_invalid
  PASS credential.no_echo
  PASS credential.valid_shape_passes_the_gate: 503 credential_store_unavailable
  PASS credential.valid_no_echo
  ```
  即**归档候选确实包含本次修复**，且本探测**没有写入真实钥匙串**（只用形状非法值，拒绝发生在钥匙串写入之前）。

## 9. 诚实性检查 — PASS

- `DraftProposal` 仍 `extra="forbid"`（`llm.py:53-61`）：逐项断言 `{"approval":…}`、`{"path":"/outside/workspace.md"}`、`{"confirmation_id":"model-issued"}`、`{"published":true}` 均 `ValidationError`，**且经真实 adapter** 也同样 `LLMProviderError(reason="schema")`。
- 只有信封层容忍：`{"proposals":[…],"type":…,"extra":1}` 被接受；而 `{"type":…}`（缺 proposals）、`{"proposals":[]}`、`{"proposals":"not-a-list"}`、缺必填字段的提案全部被拒——**没有把静默接受当通过**。
- schema 失败信息只报字段位置（`proposals schema mismatch: …`），不含字段值，长度受限。
- 未知异常不回显任意文本：第 5 节已断言客户端文本无 sentinel/路径/类型名，本地记录才保存脱敏原因。

## 10. 新缺陷与残留观察

复现命令统一为：
`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q .local/qa/test_qa_swallow_paths.py`（F1–F2、F5 的 characterization 断言在此文件中，绿即代表缺陷可复现）。

**F1（新，中）内容层 embedding/rerank 失败仍是裸 500。**
200 但内容不可读（`{"data":[]}`、缺 `model`、非 JSON 体）时，`embedding.py:159` / `rerank.py:129` 仍抛裸 `ValueError`（`… provider failed validation`），**没有任何异常处理器**，客户端得到匿名 500。这正是本轮报告所述「失败被包成通用 ValueError → 裸 500」的**同类缺陷在原代码路径上的残留**；本次修复只覆盖了「provider 明确报错」的分支。
证据：`test_finding_content_level_embedding_failure_is_a_bare_500`、`test_finding_non_json_200_embedding_body_is_a_bare_500`（断言 `status_code == 500`）。

**F2（新，中）`POST /api/v1/journal/assist` 仍吞掉类型化原因。**
`app.py:2148-2156` 与 `2178-2181` 把 `LLMProviderError` 一律换成固定文案「AI 辅助暂时不可用；记录仍留在编辑区，未保存。」，无 code/message/request id。对比：query SSE、provider-smoke、organize（`/api/v1/intake/jobs` → 503 `provider_error` + 结构化 message）都已带原因。用户第一次撞墙的正是「模型调用」，journal assist 是另一个用户可见模型路径。
证据：`test_finding_journal_assist_swallows_the_provider_reason`。

**F3（新，中低）rerank 的结构化 `provider` 字段在任何可达路由上都拿不到。**
`RerankProviderError` 的 502/`provider_error` 处理器（`app.py:1863-1874`）不可达：provider-smoke 抢先 catch 成 `provider_smoke_failed`（message 里才有 code/message/request id，无 `provider` 对象）；query SSE 走 `query_failure_message`。因此第 4 项对 rerank 的字面要求（`error.code=="provider_error"` 且 `provider.request_id` 存在）**无法经 API 满足**。
证据：`test_rerank_smoke_surfaces_provider_detail`、`test_rerank_provider_error_handler_shape_is_correct_but_unreachable`。

**F4（新，低）非 2xx 错误响应丢弃传输层 `x-request-id`。**
`bounded_json_post` 只在 2xx 时读响应头；非 2xx 走 `provider_failure(status, body)`，仅从 body 取 request id。provider 只把 request id 放在响应头时，用户/支持拿不到。
证据：`test_non_2xx_drops_the_transport_request_id_header`。

**F5（新，低）`index_after_approval` 只回 `update_failed`，原因不入任何可见面。**
`app.py:1769-1775` 捕获全部异常后仅 `_LOGGER.error(type(exc).__name__)`（打包后端无日志 handler），响应只有 `index_update: "update_failed"`。页面/日志/项目概览确认后的增量索引失败因此不可诊断（与 2026-10-14 报告第 2 节同一类问题）。
证据：`test_finding_index_after_approval_hides_the_failure_reason`。

**F6（轻）`GroundedAnswer.text` 接受纯空白。**
`text: str = Field(min_length=1)` 对 `"   "` 通过（提示词却要求 `text must be non-empty`），模型返回空白正文时会以「成功」结束并流出空回答。
证据：`test_whitespace_only_text_observation`（断言当前行为）。

**F7（观察）失败整理任务的本地记录直接写 `str(exc)[:500]`。**
`intake/review.py:~402` 未做脱敏。当前**不构成泄漏**，因为 `LLMProviderError` 的 message 是由已脱敏字段拼出的（实测记录里是 `sk-***`），但这种安全性依赖上游消息恰好被脱敏，而非该写入点自己的保证。

**F8（观察）`normalize_statement` 把模型自报的 `source_id` 拼进归一化字符串。**
`{"source_id":"x","quote":"…"}` → `"x: …"`。今天不构成引用风险（第 2 节已证明 `query.py` 丢弃模型自报的 `source_statements` 并用自家 passages 重建），但 adapter 层输出仍是一个由模型控制的标识符字符串；若未来有路径直接展示 `GroundedAnswer.source_statements`，该 id 会被显示。

**F9（nit）模型异常的状态码不一致。**
`LLMProviderError` → 503，`EmbeddingProviderError`/`RerankProviderError` → 502。功能上可接受，但同一类「provider 报错」在客户端有两个状态码。

## 未测 / 受阻

- 未调用任何真实 provider（无真实 key、无外网）；`Model.AccessDenied`/`401` 均为合成响应体。
- 未打开/写入真实 macOS Keychain；打包探测已用 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 关闭。
- 未重新打包、未验证 DMG 内 .app 与目录外 .app 一致（只核 DMG 校验和与 .app 内容）。
- 未复现主仓库自述的「包内端到端 29/29」全量脚本；只做了第 8 节列出的自建包内探测。
- 未覆盖 macOS 安装/公证、五日、双机、release 门；前端未做浏览器级 E2E（仅静态确认 `AskView.tsx` 原样显示 SSE message）。

## 新增文件（均在 `.local/qa/`，被 `.gitignore` 忽略，未 commit）

```
.local/qa/conftest.py
.local/qa/qa_helpers.py
.local/qa/test_qa_payload_tolerance.py       (13)
.local/qa/test_qa_provider_errors.py         (10)
.local/qa/test_qa_query_visibility.py        ( 6)
.local/qa/test_qa_credential_shape.py        (29)
.local/qa/test_qa_honesty.py                 ( 7)
.local/qa/test_qa_swallow_paths.py           ( 5)
.local/qa/qa_packaged_probe.py
.local/qa/evidence/qa-harness-run.log
.local/qa/evidence/identity-and-scope.txt
.local/qa/evidence/packaging-and-status.txt
.local/qa/evidence/packaged-probe.log
.local/qa/REPORT-a301b1b.md
```

harness 全量：`70 passed, exit 0`。
