# 内测候选首次真实使用：真实故障链与修复

分支 `codex/internal-candidate-20261014`，**固定产品 SHA `a301b1b`**。本报告由 Sol 编写，记录用户在本机内测包上首次真实配置与调用过程中出现的四次失败、每次的原始证据、共同缺陷与修复。所有真实调用均由用户本人在应用中确认执行；Sol 的探测调用单独列在第 5 节。

## 1. 真实故障链（按时间）

| # | 现象 | 原始证据 | 根因 |
|---|---|---|---|
| 1 | 保存密钥后向量调用失败，界面只显示 `Request failed: 500` | 保存的 DashScope 值**长 257 字符、含空白/换行、不以 `sk-` 开头**；同值打公共与业务空间端点均 `401 invalid_api_key` | 多行内容被整块粘入；应用只 `trim()` 首尾，无形状校验 |
| 2 | 换 key 后仍失败 | `401 invalid_api_key`（形状已正常，117 字符、`sk-` 开头、无空白） | 该值不是有效的百炼 key |
| 3 | 再换 key 后变为拒绝 | `403 access_denied` / `Model.AccessDenied`「Model access denied」；用 `text-embedding-v4` 与公共端点交叉探测**同样被拒** | 该 key 所属（子）业务空间缺模型调用授权；官方处置：业务空间模型调用授权，或改用主账号 key |
| 4 | 索引成功、提问失败：界面「回答失败 · 尚无回答内容」 | 账本：`model.index state=succeeded`（embedding 279 tokens）；两次 `model.query state=unknown`，usage 含 embedding + rerank + **deepseek 683/817 output tokens**；`queries.error` 只存「查询未能完成，请稍后重试。」 | 见下：模型答对了，但返回的 JSON 形状不满足应用的严格 schema |

第 4 项由 Sol 用**与应用完全相同的请求形状**探测复现：`HTTP 200`、`finish_reason=stop`，模型正确引用了合成页面，但返回键为 `['advice','inferences','missing_information','source_statements','text','type']`，其中 `source_statements` 的每项是对象 `{"source_id","quote"}`（应用要求 `list[str]`），且多出一个 `type` 键（`GroundedAnswer` 为 `extra="forbid"`）→ 校验失败 → 被吞成通用文案。

## 2. 共同缺陷：错误在三处被吞

1. `reject_business_error()` 只抛「provider reported an error response」，**丢弃 provider 的 code/message**；
2. embedding/rerank 的失败再被包成通用 `ValueError`，而应用**只为 LLM 注册了异常处理器** → 裸 500；
3. 问答 SSE 路由用笼统 `except Exception:` 把一切异常替换成一句通用文案，**既不记库也不写日志**。

后果：四次完全不同原因的真实故障，在用户界面与本机记录里完全无法区分。**这是本次排查最大的时间成本来源，也是本轮修复的核心。**

## 3. 修复（本分支 `a301b1b`）

- **解析容错**：`GroundedAnswer` 忽略多余键；`source_statements` 等列表接受字符串或 `{source_id, quote}`（兼容 `text/statement/excerpt/body` 作为正文键）并归一化为单行字符串；不可读项仍拒绝。**引用仍来自应用自己的检索结果，不采信模型自报**，`text` 仍必须非空。
- **提示词**：明确给出目标 JSON 形状与类型，要求不加额外键、数组元素为纯字符串。
- **整理路径**：`_complete` 不再要求键集合恰好等于 `{proposals}`（信封层容忍），但提案内部仍 `extra="forbid"`——既有安全测试要求提案携带 `approval`/`path` 这类信任与路径字段时必须被拒；schema 失败改为**响亮且可定位**（报出字段位置，绝不报值）。
- **provider 错误浮现**：provider 的 code/message/request_id 被保留（单行、≤300 字符、`sk-…` 掩码），embedding/rerank 抛类型化错误（仍继承 `ValueError`，兼容既有断言），API 映射为 **502 + 具体原因**；DeepSeek 的 `LLMProviderError` 同样带上结构化字段；三处 provider-smoke 路由也带上具体原因（用户第一次撞墙就在那里）。
- **问答错误可见**：客户端对**未知**异常仍只显示安全文案（既有 release 测试禁止回显任意异常文本），但**具体原因写进 `queries.error`**；对类型化失败，客户端 message 直接显示原因。
- **密钥形状校验**：写入钥匙串**之前**校验——deepseek/dashscope 必须 `sk-` 开头、无空白、长度合规；飞书 AppSecret 无空白/控制字符且长度合规；失败返回 422 `credential_shape_invalid` 且**不回显提交值**。

Sol 复核时补充的一处：实现者原本让「未知异常」的详情**只进 Python 日志**。但打包后端以 `log_config=None` 启动、root logger 无 handler，`_LOGGER.warning` 落到被丢弃的 stderr——**在真实包里查不到**。因此改为：客户端文案不变，`queries.error` **始终**保存脱敏后的 `<异常类型>: <message>`（本地库、单行、有界），并加测试固定。

## 4. 真实使用中已确认可用的部分

- 飞书：用户授权成功，7 个请求 scope 全部授予；**真实任务读取成功**（两条 `feishu.tasks.read` 计划 `succeeded`）。
- 模型（Sol 探测，与用户授权）：embedding `HTTP 200`（1024 维，与应用要求一致）、rerank `HTTP 200`（返回 2 条结果）。
- 索引：`model.index state=succeeded`，embedding 279 tokens。
- DeepSeek：真实返回答案（683/817 output tokens，`finish_reason=stop`），此前失败纯属应用解析过严。

## 5. 费用与边界

- 用户真实调用：飞书读取、索引 279 tokens、两次问答各约 1000 tokens（含 reasoning）。
- Sol 的探测调用：embedding 26 tokens、rerank 174 tokens、DeepSeek 一次 244 in / 1720 out（其中 1597 为 reasoning tokens）；另有若干次 401/403 **未计费**。
- 探测只使用**合成文本**，不含任何真实业务材料；密钥仅在内存中使用，从未打印（脚本内置自检：报告中若出现密钥则拒绝输出）。

## 6. 未验证

真实 provider 的可用性不因本修复而改变结论；macOS Keychain 生命周期、正式安装/公证、五日试用、双机、release 仍 **NOT_RUN**；`Model.AccessDenied` 的最终解决依赖用户在控制台的授权操作（或改用主账号 key），本轮只负责把原因**说清楚**。

## 7. 候选身份与验证（Sol 本机执行）

- App：`.local/internal-builds/internal-a301b1b/SummitEverything Internal.app`
- DMG：`.local/internal-builds/internal-a301b1b/SummitEverything-Internal-a301b1b.dmg`
- DMG SHA-256：`1a03d997b1a33bb79d7ddb5c4fb62ff58a5537623f679113dccc3f1bd6774803`
- `build-info.json`：`source_sha=a301b1b0785fd42d765565324f28b2888467b07e`、`dirty=false`、`build_id=20261014T152000Z-0d21a90f194c`、`frontend_sha256=0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0`

| 检查 | 结果 |
|---|---|
| guarded 全量 pytest | **623 passed**, exit 0（修复前 594，新增 29 项） |
| `ruff check` / `ruff format --check` / `mypy src` / `uv lock --check` | 全部 exit 0 |
| 完整打包 `scripts/release-macos.sh` | exit 0，DMG `hdiutil verify` CRC VALID |
| `scripts/smoke_packaged_app.py` | PASS |
| 包内端到端验证 | **29/29**（含损坏 profile 的设计信封） |
| 独立 QA | 已派出（固定 SHA `a301b1b`），结论待补 |

实现者与 Sol 的自测均未调用真实 provider；真实调用的证据见第 4、5 节。
