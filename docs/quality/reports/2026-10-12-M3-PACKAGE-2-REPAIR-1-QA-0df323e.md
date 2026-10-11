# M3 功能包 2 repair 1 独立 QA

**结论：FAIL。** 被测产品源码固定 SHA：`0df323efc26e388d62f234e0471f853b2b54be4d`。独立 QA checkout 固定 HEAD：`d38f546cac8fd923539bea6a8ef9db925e5d959c`；验收起始时产品树与源码 SHA 完全相同。全程未修改产品实现、tracked tests、锁文件、生成 API 或构建配置；本报告和脱敏证据是唯一待提交文件。两个真实用户路径缺陷使包级门 FAIL；Sol 决定最终 gate。

证据目录：[repair 1 evidence](evidence/2026-10-12-m3-package-2-qa-repair-1-0df323e/)，包含实际运行的 QA harness、原始日志及 exit code、浏览器 AX 观察、请求 capture 与 SHA-256 manifest。QA 仅使用当前 checkout 内的合成工作库与本地 loopback 服务，DeepSeek adapter 使用 `httpx.MockTransport` 替身；没有请求真实模型或飞书。

## 验收状态

| 范围 | 状态 | 观察结果 |
|---|---|---|
| C13 current/history 用户选择 | PASS | WebUI 提供“当前有效资料 / 包含历史版本”，历史范围解释可见。当前查询排除旧版本；历史回答显示 invalid / superseded 效力。将 QA 失效页移出后切换并重开历史，引用同时显示“原引用已不可用”和失效效力；其他 current 页仍标记可用。 |
| C14 短追问、用户问题来源和检索边界 | FAIL | “它呢？”单次追问可用前一条用户问题检索青岚；紧接着再问“它什么时候启动？”时错误地同时引用青岚与朱雀，朱雀 12 月排期作为支持证据。assistant/旧证据不是记忆候选来源，但连续指代的主体与检索边界没有保持。 |
| C14 稳定 request ID、事件历史与恢复 | PASS | 同 ID 完成请求重放得到相同语义 SSE events 且 provider 调用数不变；换 answer mode 返回 409。新首问、conversation reopen、同 ID 不同 question / mode 冲突和 conversation delete 的独立集成用例通过。真实 loopback 服务取消返回 202，SSE 以 `cancelled` 错误终止，历史为 cancelled 且无答案。独立 Uvicorn 在 9 字符非空 delta 后 SIGKILL，重启同 profile/workspace 后原文本保留为 interrupted；相同 request ID 只重放已持久事件，不补造 completed/error。 |
| C19 事实 / comparison / plan | FAIL | Fresh index 上直接问“青岚计划的预算上限是多少？”仅引用青岚当前页，失效旧页和朱雀数字均不作为支持证据。comparison 跨青岚、朱雀取材，inferences 分开显示；plan 将 advice 与 missing information 分开显示。但礼貌自然问法“你能告诉我青岚计划的预算上限是多少吗？”及“我想知道青岚计划的预算上限。”都被误判为无已确认对象，明明已有可用青岚证据却不召回。缺陷 1 见下文。 |
| C20 角色、记忆来源、候选门、编辑/删除与预算 | PASS | 本人表达需显式声明才可建候选；assistant 文本、伪造消息 ID、粘贴材料 canary 均拒绝。候选编辑后确认才进入 active memory，active memory 和 role 编辑/删除成功；pending 候选未进入 active provider memory。超预算 UI 显示可读角色预算错误、没有断流文案，也没有新增历史项；API 422 为 `context_budget_exceeded` 且 Mock provider 调用数不增长。长当前问题 8000 字符完整传给 Fake provider，SHA 一致，无静默截断。 |
| C21 workspace / profile 隔离 | PASS | 用不同 workspace UUID 切换前后，角色、记忆、历史隔离并在切回时恢复；同一库由第二 profile 打开时，local profile 路径不同，角色、记忆、历史为独立空状态，索引状态也本地独立。 |
| README 后端 / Web / 类型 / 静态 / 接口 / 构建矩阵 | PASS | guarded pytest 402 项；ruff、format、mypy、lock、uv build、OpenAPI types、Web 52 tests、typecheck、lint 和 build 均退出 0。Web lint 有 2 条 `react(set-state-in-effect)` warning。 |
| Chrome console / Network request body 面板 | NOT_RUN | CUA 可观察并操作真实浏览器界面，但本轮工具未提供 Chrome DevTools console / Network 面板。实际 UI 和本机 API 日志、MockTransport provider capture 可见；不据此声称 DevTools 已通过。 |
| Real/native/DMG/五日/双机/额度 | NOT_RUN | 本轮未触碰真实 provider、飞书、账户、凭据、Keychain、安装包、DMG，也没有消费 smoke 额度。 |
| Runtime 模型元数据 | UNVERIFIED | 只使用 fake provider，未观察实际 runtime 暴露；不能由配置推断。 |

## 两项可复验缺陷

### QA-R1-01：事实问题前置礼貌语使主体解析过度过滤（C19）

在 UI 中创建并确认青岚 18 万元 current 页和朱雀 12 万元 current 页，随后由 UI 执行索引计划；索引显示 4 页 / 4 分块、`summit-fake-embedding-v1`，且 `retrieval-diagnostics.json` 校验页面正文 hash 与索引 hash 一致，旧版 20 万元页因 superseded 不合格。直接问“青岚计划的预算上限是多少？”只引用青岚 current 页，朱雀数字不在最终 citations 或 Fake provider source statements 中。

同一 fresh index 上的用户问法“你能告诉我青岚计划的预算上限是多少吗？”和“我想知道青岚计划的预算上限。”却都显示“没有找到能确认该对象的已确认资料。”没有 source statements/citations。准确而自然的礼貌前缀令主体提取失败，排除掉了本来合格的当前主体证据。期望礼貌问句能识别同一青岚主体，继续应用 current qualification；实际无证据返回。对照与原始 harness 结果见 `browser-ax-observations.md` 和 `harness/`。

### QA-R1-02：连续短指代检索跨入另一主体（C14/C19）

真实 UI 同一对话依次提问：

1. `青岚计划的预算上限是多少？` → 只引用青岚 current 页；
2. `它呢？` → 可用上一条用户问题检索，支持仍只有青岚；
3. `它什么时候启动？` → 支持引用同时出现青岚 11 月排期和朱雀 12 月排期。

第三轮的问题主体应承接本轮上下文所指的青岚；朱雀数字不是青岚事实的支持材料。第三轮返回的跨主体 citation / provider source statements 构成实际缺陷，单轮追问成功不能证明连续追问边界正确。该测试使用本轮新建的 fresh index；没有复用或绕过资格门的 stale-hash 夹具。

## 支持结果与实现边界

- C13 UI 范围控件、历史效力和引用可用性/失效性在切换范围与 reopen 路径实际可见。重开旧问答时，原页面已移出工作库，UI 同时标明 `原引用已不可用` 与 `已失效版本，仅限历史参考`。current 查询不允许失效 / superseded 页支持事实回答。
- C19 对比与方案跨材料通过，来源陈述、推断、建议、缺失信息各自分区；普通直接事实问题不出现无关主体数字。C19 总项因 QA-R1-01 仍为 FAIL。
- C20 本人表述 provenance、引用/assistant 拒绝、候选确认后才活跃、角色记忆隔离、budget 422 与 provider 调用未增加通过。API capture 记录 pending 候选不在 `user_memories`，previous-question context 来自用户问题；browser DevTools request body 未观察到。
- C21 在干净 workspace UUID 与 profile fixture 下通过。同库工作空间、profile 的纯本机状态分别观察；没有把被早期 harness 初试污染的历史误判成产品串库缺陷。
- SSE `same_sse=false` 是 JSON object key 顺序不同；解析后事件对象与类型均相同（`same_events=true`），provider 调用数不增长。以语义事件相同判 replay PASS，保留原始字段作为证据。

## 自动检查与原始退出码

下列命令在固定源码树实际执行，原始 stdout/stderr 和对应 `.exit` 文件见 evidence `raw-logs/`。`npm ci` 按 README 在 repo 根首次试跑因根目录没有 package lock 返回 1；随后按 README 正确的 WebUI 指令 `npm --prefix web ci` 成功退出 0。两次日志都保留，前次是 QA 命令定位错误而非产品缺陷。

| 命令 | exit | 结果 |
|---|---:|---|
| `npm --prefix web ci` | 0 | 安装 126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | 0 | dev 环境就绪 |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | 402 passed；1 条 Starlette/httpx TestClient deprecation warning |
| `uv run ruff check src tests` | 0 | 通过 |
| `uv run ruff format --check src tests` | 0 | 73 files 已格式化 |
| `uv run mypy src` | 0 | 40 source files 通过 |
| `uv lock --check` | 0 | 锁文件一致 |
| `uv build` | 0 | sdist / wheel 构建通过 |
| `npm --prefix web run api:types` | 0 | OpenAPI 类型生成通过，生成树无 diff |
| `npm --prefix web test -- --run` | 0 | 52 tests / 12 files 通过 |
| `npm --prefix web run typecheck` | 0 | 通过 |
| `npm --prefix web run lint` | 0 | 通过；2 条既有 React effect warnings |
| `npm --prefix web run build` | 0 | Vite build 通过 |
| 定向 query cancel + 2 cancellation regressions | 0 | 3 passed |
| 非空 partial interrupted-state recovery regression | 0 | 1 passed |
| conversation 首问 / reopen / replay / conflict / delete integration | 0 | 1 passed |
| local API live cancellation harness | 0 | `202`，SSE `status,error(cancelled)`，history cancelled / 空答案 |
| 独立 Uvicorn 首个非空 delta 后 SIGKILL / restart / replay | 0 | 9 字符 partial 保留；interrupted 状态和相同事件 replay |
| C20 / C13 / C14 blackbox、workspace/profile isolation | 0 | 最终修订 fixture 通过；详细逐项 JSON 见 evidence `harness/` |

Harness 初试与修正按原始日志保留：根目录 `npm ci` 位置错误后切到 `web`；C21 第一版 clone 保留 workspace UUID，未能区分两个库，随后改用不同 UUID 的 QA workspace；C21 第二次因 profile B 未先 open workspace 而返回 409，被修正为同库独立 profile 后重跑通过。失败均是 QA harness/setup 误差，非产品证据。另有单次关于真实事实检索的早期 QA stale-hash 夹具错误；本报告不复用该结论，fresh index 与两份 SHA 当前一致，纠正记录和旧日志均保留。

测试结束时固定 HEAD 仍为 `d38f546cac8fd923539bea6a8ef9db925e5d959c`；产品与 tracked tests 相对固定源码无变化。QA 启动的 API、Vite 和 partial-recovery 服务均已停止；监听端口 `15172/15173/18793/18795/18796` 已核验无 listener。证据 manifest 相对 repo 根记录并覆盖脱敏 raw logs 与实际执行 harness。
