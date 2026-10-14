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

## 8. 第二轮：把同类的「吞错」在相邻路径收口（`19078de`）

独立 QA 对 `a301b1b` 判 9 项全 PASS，但指出同一缺陷类在其它路径仍有残留。第二轮修复（固定产品 SHA `19078de`）：

| 项 | 问题 | 处理 |
|---|---|---|
| F1 | embedding/rerank 出现「200 但内容不可用」（缺 `data`、空、非 JSON、类型错）时抛裸 `ValueError` → 仍是裸 500 | 这类**provider 响应内容**失败改为类型化 provider 错误（`reason=schema`、可读原因）→ API 502；**本地参数校验仍保持裸 `ValueError`**，不得被误报成 provider 故障 |
| F2 | `/api/v1/journal/assist` 一律换成固定文案 | 类型化失败给具体原因，未知异常保留安全文案，并在本地留证 |
| F3 | rerank 的 provider 详情经 API 不可见 | 三种 provider-smoke 失败响应统一附 `provider{code,message,request_id}` |
| F4 | 非 2xx 丢弃传输层 `x-request-id` | 错误响应也读取（body 内 id 优先） |
| F5 | 增量索引失败原因只在打包包里写不了的日志 | 新增 `index_update_failed` 诊断事件（含状态与受控原因），`index_update` 字段语义不变 |
| F6 | `GroundedAnswer.text` 接受纯空白 | strip 后必须非空 |
| 一致性 | LLM 503 vs embedding/rerank 502 | provider 侧失败统一 **502**；本地校验保持 422 |
| 卫生 | 失败记录直写 `str(exc)` | 写入点统一走 `sanitize_provider_text`（纵深防御） |

**两处分层原则（实现者提出、Sol 认可）**：`queries.error`（本地 DB）保存脱敏后的 `<异常类型>: <message>`；服务端日志与 `diagnostics.log` 只写**受控**原因（类型化 provider 失败写结构化 code/message，其它仅写类型名，因为既有测试断言 sentinel 不得进入日志、且 `event_log` 的契约是只写状态元数据）；客户端响应只显示受控文案。

验证：**649 passed / exit 0**（第二轮新增 26 项），ruff/format/mypy/lock 全 0；打包 exit 0、smoke PASS、包内端到端 29/29。独立 QA 对 `19078de` 的复核结论待补。

**候选身份（第二轮）**：App `.local/internal-builds/internal-19078de/SummitEverything Internal.app`；DMG `SummitEverything-Internal-19078de.dmg`，SHA-256 `cb6af3781bcf948eab496ca208fdb8321368b89f9ae6b5ad89f8bf9a457118d1`；`source_sha=19078dedb62655c4090051ee5e2159068ef5f607`、`dirty=false`、`build_id=20261014T154135Z-0d21a90f194c`。

构建说明：构建时主工作树因**另一并行工作流的未提交文档**（`AGENTS.md`、`README.md`、`docs/decisions/0011`、两份前端规格）而是 dirty，而构建脚本拒绝 dirty 树。为保持候选身份干净（`dirty=false`），本轮改在**该提交的独立干净 worktree** 中构建（`web/node_modules` 以 symlink 复用，`.local/first-use/defaults.json` 复制进该 worktree），未触碰那份在制品。

## 9. 第三轮：诊断事件不再因清洗而被丢弃（`f40bc39`）

独立 QA 对 `19078de` 判 1–10 项全 PASS，但发现同类残留 **D1**：`local/event_log.py` 的 reason 校验器拒绝任何含字面 `sk-` 或超过 200 字符的文本，而调用方 `except (ValueError, OSError): pass` → **整条诊断事件被静默丢弃**（`assistant_failed` / `index_update_failed` 连文件都不生成）。触发条件都是常态：脱敏产物 `sk-***` 仍含 `sk-`；拼出的 reason 常 >200（300 字符 message + code + request_id 上限）。

修复：

- 判据换成「是否仍是**未掩码**凭据形状 `sk-[A-Za-z0-9_-]{8,}`」——已掩码的 `sk-***` 不再被拒；
- `clean_reason()` 由「拒绝」改为「清洗」：折叠单行 → 掩码残存凭据 → **截断到 200**；仅非字符串/清洗后为空被拒；
- 调用方新增 `record_diagnostic()`：reason 构造失败时**回退为最小安全值仍记录事件**，`except ValueError: pass` 彻底移除（仅磁盘 `OSError` 继续容忍）；
- 实现者按 Sol 要求**替换了那条「期望丢弃」的旧测试**（原断言换行/含 `sk-`/超长都必须抛错，其期望本身就是 D1 的成因），新期望是「清洗后仍必须写出事件」，并且新增专门断言「未掩码凭据绝不出现在文件里」，安全约束未放宽。

验证：**656 passed / exit 0**（第三轮净增 7 项），ruff/format/mypy/lock 全 0；打包 exit 0、smoke PASS、包内端到端 29/29。独立 QA 对 `f40bc39` 的复核结论待补。

**候选身份（第三轮）**：App `.local/internal-builds/internal-f40bc39/SummitEverything Internal.app`；DMG `SummitEverything-Internal-f40bc39.dmg`，SHA-256 `a856a2eb70607f30078197946f4aba67c9a7ad367d639c187c101230172370ce`；`source_sha=f40bc39445258d954166143e094156c788be36e1`、`dirty=false`、`build_id=20261014T155526Z-0d21a90f194c`。

## 10. 三个候选的关系（供选择安装）

| SHA | 内容 | DMG SHA-256 |
|---|---|---|
| `a301b1b` | 首轮：payload 容错、provider 错误浮现（embedding/rerank 502）、问答原因可见、密钥形状校验 | `1a03d997…4803` |
| `19078de` | 第二轮：内容层 200-不可用 → 502、assist/索引失败可见、request-id、空白答案、状态码统一 | `cb6af378…18d1` |
| `f40bc39` | 第三轮：诊断事件不再因清洗被丢弃 | `a856a2eb…70ce` |

三轮都基于同一分支依次叠加；**最新最全的是 `f40bc39`**。三者对「用户提问能否得到回答」这条主路径等价（第一轮已修好），差别在相邻路径与留证完整度。

## 11. 第三轮独立 QA 结论（`f40bc39`）：9 项全 PASS

| 项 | 判定 | 关键证据 |
|---|---|---|
| 1 身份与范围 | PASS | 起止 `git status --porcelain` 均空；`19078de..f40bc39` 改 5 文件，`web/**` 0 |
| 2 D1 触发 A | PASS | assist 与索引**两条真实端点路径**：`Your api key: sk-*** is invalid` → 事件确实写入，reason 含 `sk-***`，无未掩码凭据 |
| 3 D1 触发 B | PASS | 258/278 字符 message → 两条路径事件均写出、`0 < len(reason) <= 200` |
| 4 安全未放松 | PASS | 未掩码 `sk-abcdefghijklmnop` 落盘后无原串；掩码先于截断；换行折叠；空/非字符串经回退仍记事件 |
| 5 无静默丢弃 | PASS | 全 src 仅剩 5 处 `except: pass`（异常类体、state 清理、CancelledError），无 `contextlib.suppress` |
| 6 契约未回归 | PASS | lifecycle sentinel + 白名单/轮转 + 凭据不落盘等 53 passed |
| 7 全量与静态 | PASS | guarded **656 passed**；ruff/format/mypy/lock 全 exit 0 |
| 8 打包候选 | PASS | DMG 哈希逐位一致；DMG 挂载后 `diff -r` 与磁盘 .app 完全一致；**包内 PYZ 的 `event_log`/`api.app` code object 与源码 `compile()` 结果 `marshal.dumps` 逐字节相同** → 包内确含本轮修复 |
| 9 残留（如实记录，非「整体通过」） | — | 见下 |

### 第 9 项列出的残留边界

- **控制字符（低，本轮唯一防御纵深下降点）**：旧校验器拒绝一切 `ord<32`；新 `clean_reason` 只折叠 `str.split()` 认定的空白，故 `\x00`/`\x07`/`\x1b`(ANSI)/`\x7f` 会原样落盘。JSON 仍是合法单行，危害限于终端转义注入，**不是凭据泄漏**。属可在一行内收紧的后续小改。
- **logging 层吞异常（既有，非本轮引入）**：handler 流损坏时 `logging.Handler.handleError` 会吞掉写错、`profile_event` 正常返回，事件静默丢失（实测 stderr 出现 `--- Logging error ---`）。本轮未修、也未声称修。
- **掩码形状边界（既有）**：大写 `SK-`、7 字符 `sk-abcdefg`、零宽/双向控制符切断形状不被掩码——但与既有 `http_boundary` 的输出**逐个一致**，本轮既未引入也未加重。
- **文档小错**：tracked test 里 `# 258 characters` 的字符串实测 278 字符（非产品缺陷）。

未测：打包应用内**行为级** D1 复现需要真实凭据或对外网络（两者被禁止），故以「PYZ 字节码逐字节等价 + 常量存在性」替代——强于单次行为观测，但确非端到端行为证据。
