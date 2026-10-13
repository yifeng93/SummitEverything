# 本地 API 契约 v1

状态：v1 API 契约与实现边界。M3 离线实现与正式模拟验收已通过并合入 main；当前验收证据见 [PROGRESS](../implementation/PROGRESS.md) 和 [报告索引](../quality/reports/README.md)。本表包含已实现与计划路由；契约定义不表示真实 provider 已验收。Settings 读写不联系 provider；真实 embedding 索引须用户另行确认计划。前缀 `/api/v1`；JSON 使用 snake_case、稳定小写枚举，OpenAPI / TypeScript 从后端类型生成。

## 共用对象与认证

- PageSnapshot：page_id、relative_path、metadata、body、content_sha256、storage_area、approval_state（confirmed / pending / invalid）、validity。用户不能上传 storage_area 来改变判定。
- Draft：draft_id、input_ids、target_page_id、metadata、body、expected_base_sha256、conflicts、resolutions、state（pending / confirmed / rejected）。
- Action：action_id、kind（feishu_task_create / feishu_task_update / feishu_task_complete / project_progress）、payload、payload_sha256、state、confirmation_id、provider_result。
- MutationResult：operation_id、state、changed_paths、page_versions、saved_locally；正式页确认入口另返回 index_update（not_enabled / updated / update_failed），区分首次索引、成功自动增量和保存后索引失败。没有自动 cloud_synced 字段。
- Job：job_id、kind、state（queued / running / succeeded / failed / unknown / cancelled）、progress、result、error。进度不虚构百分比，取消不保证远端未计费。
- IntakeItem：item_id、source_id、title、filename、original_relative_path、state（pending / processing / reviewing / completed / failed / cancelled / unknown）、latest_job_id；新增可选兼容字段 `attempt_no`、`revision`、`previous_attempt_sha256`、`finished_at`。`unknown` 不自动重发；显式 reprocess 要求新 operation_id。
- IntakeJob：job_id、item_ids、request_hash、state（running / provider_calling / completed / failed / cancelled / unknown）、draft_ids、created_at；可选 `finished_at`、`attempt_id`、`revision`、`checkpoint_sha256`。`completed` 表示 provider 输出已保存为本地稿件/候选，不表示稿件已批准。Draft 新增可选 `job_id` 以关联恢复与完成作业。
- Citation：page_id、content_sha256、chunk_id、heading、excerpt、validity；客户端用稳定页面路由打开，不信任任意文件 URL。
- Answer：answer_id、question、text、citations、answer_mode、source_statements、inferences、advice、missing_information、purpose、index_status。来源陈述、推断、建议和缺失资料分别展示，不能互相伪装。

服务 context 决定活动工作库和本地 profile。除工作库打开外，请求不接受任意 root / 绝对路径。业务 API 使用启动器传递的 Bearer token；allowlist origin，拒绝非本机绑定和无 token 的状态修改。浏览器 OAuth 回调无法携带此 Bearer，是唯一认证例外：必须验证本机先前发起、绑定会话、限时且一次性的 state，再处理授权结果；回调不能访问其他业务功能。

完整 frontmatter、输入文本、文件名、外部响应和配置在边界验证。保存格式须符合工作库契约，不能丢弃未知合法元数据。

## 错误、分页与意图

错误统一为 {error: {code, message, request_id, details?}}；message 面向用户，details 不含秘密 / 内部栈。

| HTTP | code 示例 | 行为 |
|---|---|---|
| 401 / 403 | unauthenticated / forbidden | 不执行副作用，提示重新授权或配置 |
| 404 | not_found | 不猜测另一个同名页 |
| 409 | version_conflict / intent_conflict / action_unknown | 保留原内容 / receipt，给可恢复路径 |
| 422 | validation_error | 返回明确字段问题 |
| 502 / 503 / 504 | provider_error / unavailable / timeout | 不伪装完成，不自动重复外部写 |

列表输入 cursor、limit，默认 50，范围 1–100；输出 items、next_cursor。可选查询按 line_id、project_id、kind、state / 时间过滤。

所有写意图携带 operation_id（或对象自带 action_id / confirmation_id）。同意图重试保留 ID；意图 payload hash 不一致返回 409。进行中重试返回 202 和状态位置。单次点击不生成多个独立意图。

## 路由与主要输入 / 输出

### 一次性真实验收计划（M4.2 包 A 实现）

`POST /acceptance-plans` 只在本机生成 10 分钟有效的单次计划，不调用 provider。输入 `operation` 和具体 `scope`；响应同时返回可读范围与 `plan`（范围/配置 SHA-256、有限 `request_limit`、状态和时间）。客户端必须展示该范围并由用户显式调用 `POST /acceptance-plans/{plan_id}/confirm`，提交预览时返回的 `scope_sha256` 和 `scope`。设置、模型内容和页面数据不能自行确认。

真实整理、索引、问答、飞书只读与导入执行路由要求相应已确认 `acceptance_plan_id`，并在外发前重核同一内容/页面版本、profile/workspace、配置与飞书授权代次。执行预留有限 HTTP request 数；索引上界按最多 20 条输入一批，问答最多 embedding/rerank/answer 各一次，整理最多一次，飞书导入按保守最坏上界计算。超时或进程中断的预留不可释放、不可重发；状态 `unknown` 表示结果未知而非明确失败。相同 Feishu operation_id 与 query request_id 的本地 replay 不重复 provider 调用或消耗新的计划。

`GET /acceptance-plans/{plan_id}` 仅返回本地状态；成功后 `provider_usage` 只包含 provider 明确回报的 request id 与 token 计数，未回报的字段为 null / `usage_reported=false`。字段缺失不当作 0，亦不表示实际账单；真实账单需另在 provider 侧核对。损坏/容量用尽时本地拒绝继续授权。`DELETE /acceptance-plans/{plan_id}` 撤销尚未执行计划，不影响已经预留的调用。全程只接受本机 Bearer / allowlisted Origin。

下表是 v1 完整能力面，按阶段实现。尚未实现的路由不能返回空成功伪装功能存在。

| 路由 | 主要契约 |
|---|---|
| GET /health | App / service / frontend 身份和 readiness，无密钥 |
| POST /workspaces | root、mode:create/open、operation_id → WorkspaceContext 摘要；校验所选目录 |
| GET /workspaces/current | manifest、只读 / 写入状态、本地保存说明 |
| GET /lines；POST /lines；PATCH /lines/{id}；DELETE /lines/{id} | 线 CRUD，写带 operation_id；非空删除拒绝 |
| GET /projects；POST /projects；PATCH /projects/{id}；DELETE /projects/{id} | 主线归属、名称、归档；业务进度另走 Action |
| GET /pages；GET /pages/{id} | PageSnapshot；引用打开可附 expected_content_sha256，旧版本返回内容已更新 |
| POST /pages | 明确直接撰写并确认的 metadata / body、confirmation_id → MutationResult；新增基准为空 |
| POST /pages/{id}/confirmations | 外部编辑或直接修改后的 metadata / body、expected_base_sha256、confirmation_id → MutationResult |
| POST /pages/{id}/moves | destination_relative_path、operation_id、跨项目时的 structure_confirmation_id → MutationResult；移动原子维护标准 Markdown 相对链接，结构确认更新单一主归属 |
| POST /journal/{kind} | kind:log/thought，正文、可选关联、confirmation_id、operation_id；页面 ID 稳定派生于工作库与操作意图，复用 PageWriter，重试同结果、异正文 409 |
| POST /journal/assist | 用户明确请求后返回分离的可编辑建议；不保存、不批准；失败不影响已保存页面 |
| POST /projects/{id}/overview/confirmations | 显式确认新建或更新稳定 overview_id 页面；更新必须提交当前 expected_content_sha256，过期版本 409；独立于项目进度 Action |
| POST /intake/items | 粘贴内容 / 随手记录、operation_id → item；纯本地，不调用模型（已实现） |
| POST /intake/files | multipart txt/md 文件及同批次标识 → 来源与 item；保存原字节（已实现，20 MB 上限） |
| GET /intake/items | 从 active 与完成摘要读取状态；无活跃 lease 且无可恢复 checkpoint 的旧 running attempt 标 unknown，不触发 provider 重发。 |
| POST /intake/jobs | 明确选择的 item_ids、operation_id、线 / 项目、可选 reprocess=true → IntakeJob；FakeLLM 生成稿与 action 候选（已实现）。处理中/待审拒绝新作业；completed/failed/cancelled/unknown 均要求用户明确 reprocess，且用新的 operation_id。相同 operation_id / 相同请求体返回现有 job，不重复调用 provider；进行中的同一意图返回 HTTP 202 和指向该 job 的 Location。unknown 的显式 reprocess 是新意图，可能再次调用模型。 |
| GET /jobs/{id}；DELETE /jobs/{id} | 查询 / 请求取消。成功 checkpoint 只恢复本地稿件/候选，CAS 防止迟到输出覆盖 cancelled/unknown/终态；同步 provider 调用不能被本地强制中断。 |
| GET /drafts；GET /drafts/{id}；PATCH /drafts/{id} | 完整稿、来源、冲突；编辑带稿件版本（已实现） |
| POST /drafts/{id}/confirmations | confirmation_id、expected_version、重要冲突处理结果 → MutationResult（已实现） |
| GET /actions；GET /action-intents；GET /actions/{id} | 旧候选数组兼容；显式 cursor/limit 候选分页；独立 Action 列表 / 回执按 cursor/limit 查询（M2.2 Fake 已实现） |
| PATCH /actions/{id}；POST /actions/{id}/confirmations；POST /actions/{id}/executions | 预期 hash 编辑；最终 payload 独立确认；已确认动作原子认领后执行，进行中重放 202 + Location，其他既有状态原样返回 |
| POST /actions | action_id、kind、payload、可选 candidate_id → proposed Action；保留候选 / 稿件 / 来源关联，仅保存意图，不执行外部写 |
| POST /actions/{id}/reconciliations；POST /actions/{id}/outcomes | 只读核实未知结果；无证据保持 unknown；用户独立确认的 state / evidence / confirmation_id 才能记录明确结果 |
| GET /integrations/feishu/status | 权限 / 登录状态，无 token 值 |
| POST /integrations/feishu/authorizations | 创建 OAuth 登录意图，state 绑定当前本机会话 |
| DELETE /integrations/feishu/authorizations | 登出并清除当前用户授权 |
| GET /integrations/feishu/callback | 验证已发起 OAuth state / redirect；Fake 存进程内，Real 模式写入当前 profile 的统一 Keychain 凭据槽 |
| GET /integrations/feishu/materials | 搜索 / 分页的可见材料 metadata；不调模型 |
| POST /integrations/feishu/imports | 用户选择的材料 ID、operation_id → 来源与 item；不隐式整理 |
| GET /integrations/feishu/calendar；GET /integrations/feishu/tasks | 读取日历 / 正式任务；任务写统一走 Action |
| POST /acceptance-plans；POST /acceptance-plans/{id}/confirm；GET /acceptance-plans/{id}；DELETE /acceptance-plans/{id} | 真实模型/Feishu 单次动作的本机预览、独立确认、状态/安全用量读取和未执行计划取消；计划绑定 profile、workspace、执行配置与确切 scope digest，有 10 分钟 TTL 和有限 HTTP request 上限。详情不保存 prompt/正文；unknown 消耗额度且无重发接口 |
| POST /index/plans | mode:initial/incremental/full/model_change → 页面 / 分块范围、费用估计、fingerprint |
| POST /index/jobs；GET /index/status | 首次索引或用户请求的 full / model_change 计划仍需显式确认；已有索引时，批准 mutation 自动执行同 fingerprint 的 incremental。状态返回 fingerprint、索引页/分块数、当前页数、stale_pages 与 state（not_ready / ready / stale）；旧版本不得作为当前引用 |
| POST /queries；DELETE /queries/{request_id} | question（最多 8000 字）、conversation_id?、role_id?、answer_mode:fact/comparison/plan、purpose:current/history → SSE / 取消；服务器从当前合格版本重新检索，不把历史 assistant 回答当 passage。意图 hash 包含模式、角色与上下文版本；稳定 ID 重放使用已保存事件，不重发 provider。角色偏好与用户记忆不得改变证据、工具或批准边界。 |
| GET /conversations?cursor&limit；GET /conversations/{id}；POST /conversations/{id}/reopen；DELETE /conversations/{id} | 按本地 profile 与当前 workspace 隔离的问答历史；列表默认 20、limit 1–100；历史只读重开可接续提问或删除；不进入工作库语料 |
| GET /roles；POST /roles；PATCH /roles/{id}；DELETE /roles/{id} | 本机 profile+workspace 角色 CRUD；instructions 最多 4000 字符，角色上下文预算 0–6000 字节且每次查询会校验实际长度。角色只影响表达，不修改批准 / 工具权限 |
| GET /memory/candidates；POST /memory/candidates | 用户必须明确勾选 `user_expression=true`，`message_id` 必须是当前 profile/workspace 历史中的真实用户问题，`text` 必须与问题原文相符且表达本人偏好 / 习惯 / 事实；引用、来源、转述、粘贴及来源 canary 文本拒绝；服务端核验消息来源，不信任 UI 标签；响应是本机 pending 候选，不能直接进入上下文 |
| POST /memory/candidates/{id}/confirmations | confirmation_id、用户编辑后的正文 → 活跃本机记忆；保留来源 message_id 与确认意图，重放同意图幂等，改内容冲突 |
| GET /memory；PATCH /memory/{id}；DELETE /memory/{id} | 查看、编辑、删除活跃本机记忆；按 profile 与 workspace 隔离，不写工作库 |
| GET /settings；PATCH /settings | 当前本地 profile 的非秘密配置；已实现原子本地保存；设置读取 / 保存不联网 |
| PUT /credentials/{provider}；DELETE /credentials/{provider} | 已实现显式 macOS Keychain adapter 与测试注入边界；响应只返回 configured 状态。真实 OS Keychain 拒绝 / 锁定 / 重启生命周期仍 NOT_RUN |
| POST /settings/connections/{provider} | 计划路由；尚未实现。连接检查进入 Stage C 授权门，不能由刷新设置触发 |
| GET /provider-smoke；POST /provider-smoke/deepseek-chat；POST /provider-smoke/model-studio-embedding；POST /provider-smoke/model-studio-rerank | 单独限额的合成连接 smoke；provider 在本机已保存并启用 Real 配置时可调用，固定合成输入、每个 app profile 每 provider 最多一次。尝试在出网前原子记账，失败/超时也占额，无自动重试；普通业务模型路径仍被服务端拒绝。真实 smoke 尚未执行；Feishu OAuth 没有对应 smoke 路由 |

### Intake 作业恢复与回执归档

`IntakeItem.state` 支持 `pending`、`processing`、`reviewing`、`completed`、`failed`、`cancelled`、`unknown`；`IntakeJob.state` 支持 `running`、`provider_calling`、`completed`、`failed`、`cancelled`、`unknown`。扩展字段为可选，以兼容旧工作库。`unknown` 表示无法证明 provider 是否完成；读取或恢复不得隐式重新调用。用户显式 reprocess 必须创建新的 `operation_id`，UI 明示可能新增 provider 调用。完成 job 表示稿件 / 候选已保存到本地，不等于其全部得到确认。

进行中的相同 operation 重放返回 HTTP 202，并以 `Location: /api/v1/jobs/{job_id}` 指向状态资源；completed 或其他终态的相同 operation / payload 重放旧结果，不再次调用 provider。相同 operation ID 携带不同意图返回 409。成功 checkpoint 可恢复本地稿件 / action 候选，但不能批准知识；attempt / revision CAS 阻止迟到结果覆盖 cancelled、unknown 或其他终态。

实现中的回执扫描以 active 文件及 `.summit-everything/archives/{intake-items,intake-jobs,transactions}/{YYYY-MM|undated}/summary.json` 为真源，按 operation、source、稳定 receipt ID 做查重 / replay；摘要结构、冲突恢复及旧无时间记录边界见[工作库契约第 1 节](WORKSPACE-v1.md#1-工作库布局与状态)。`undated` 仅兼容历史无 `finished_at` 的记录，不代表虚构月份。运行中的 owner lease 与本机诊断日志都留在本地 profile；API 不暴露 lease / 日志文件，且不同机器须在同步完成后轮流写，不提供分布式锁。

直接撰写保存是用户确认入口，不是模型可用工具。对已有页确认前以最新磁盘版本比较基准；写入 API 不能接受模型提交的 approval。

前端任务表单日期由用户指定，不猜开始 / 截止日期；适配层按飞书当前协议发送和验证，已有完成任务重复完成按已完成成功处理。

## 查询 SSE

每事件 JSON 为 request_id、seq、type、data；seq 严格递增。type 为 status、citation、delta、completed、error。completed 携带完整 Answer，error 有统一错误结构；同 workspace/profile 内稳定 request_id 和相同输入只重放既有事件，不重复调用查询，改输入返回 409。取消与断流分别保留真实 partial 和准确状态；不可发送终态的断流不伪造 completed。每次查询事件、partial 和原引用快照保存在本地 profile SQLite，不进入工作库目录或正式知识语料。历史引用保留原 content hash / excerpt；读取时依据统一检索资格门返回 available / updated / unavailable，不能以当前页内容替换原回答引用。打开旧版本时仍传 expected_content_sha256；版本变化后 UI 明示差异并可查看当前页。

在聚合上下文、邻页扩展和引用阶段读取 PageSnapshot，再用统一 gate 加缓存版本复验。索引未就绪或部分更新时返回 index_status，不能用旧片段补齐缺失证据。

用户角色与记忆只改变问答上下文 / 表达，不允许去掉证据边界、执行写动作或把助手建议写入正式页。

冲突稿必须逐项选择一个已展示的依据或明确标为 unresolved；正式正文会附加“冲突处理结果”，记录选择或说明未决尚未成为确定事实。确认页与已确认稿件保存同一最终正文。

## 对接测试边界

Fake providers 在 integrations 协议边界替代网络，工作库、事务、索引资格、路由和 UI 保持真实。不得把真实受测业务服务整体 mock 掉。

 provider 的 malformed / denied / timeout / unknown 响应各有独立 fixture。实际账户与付费质量验收单列，测试者不因为 mock 通过就填写外部场景 passed。

## M2.1 已实施的飞书 Fake 契约

默认且唯一可配置模式为 `fake`；所有外部行为通过注入 FeishuProvider，默认实现没有网络代码。CredentialStore 分别隔离 AppCredentials（app_id / SecretStr app_secret）与 user access/refresh token；非秘密 FeishuConfig 保存 app_id 和精确 redirect_uri。Fake 切片使用进程内 MemoryCredentialStore。真实模式另有 `FeishuHttpProvider`（见下节），它只通过统一凭据槽读取 app secret 与 user token。

### 真实 Feishu HTTP adapter（2026-10-10，离线 stub 已覆盖）

应用身份优先：日历日程、妙记逐字稿/产物、task 详情/创建/编辑都接受 `tenant_access_token`，因此优先用应用身份（`identity=app` 且已存 app secret 时**完全不读取用户凭据槽**，不刷新、不要求 user token；身份先按配置决定，再读对应凭据）。仅妙记搜索与任务列表按官方要求只接受 `user_access_token`，这两项需要一次性用户授权。缺 app 密钥 → `credential_missing`；无 user token → `not_authorized`；用户槽损坏/拒绝 → `credential_unreadable`（可读 401，不泄露内部异常）；scope 不足 → `missing_scope`；权限错误不得自动换身份扩大访问。官方来源与逐字段证据见[协议矩阵](../architecture/PROVIDER-PROTOCOL-MATRIX.md)；本节只记契约。

- `authorization_url` = `https://accounts.feishu.cn/open-apis/authen/v1/authorize?client_id&response_type=code&redirect_uri&scope&state`；`scope` 为空格分隔的用户权限，含 `offline_access` 才返回 refresh token。
- `exchange` / `refresh` 使用官方 JSON OAuth 端点（v2 `https://open.feishu.cn/open-apis/authen/v2/oauth/token`；v3 迁移目标 `https://accounts.feishu.cn/oauth/v3/token`）。响应解析严格：`token_type` 必须为 `Bearer`、`expires_in` 必须为正有限整数、`scope` 必须存在且以本次响应为准；refresh 必须返回**新的** `refresh_token`（缺失或仍是已消费旧值即拒绝），损坏响应不写入凭据。refresh token 单次使用并轮换，已消费的 token 绝不重发。
- 应用身份 token：`POST /open-apis/auth/v3/tenant_access_token/internal`，内部缓存到过期前 60 秒。
- 妙记搜索：`POST /open-apis/minutes/v1/minutes/search`，`page_size` 上限 30，user token，scope `minutes:minutes.search:read`。该 endpoint **没有 visibility 过滤参数**；请求带 `visibility` 时返回 `unsupported_capability`，不静默返回全部。
- 逐字稿：`GET /open-apis/minutes/v1/minutes/:token/transcript?file_format=txt` 返回二进制；scope `minutes:minutes.transcript:export`；`missing_scope` 时回退 `GET .../artifacts`（scope `minutes:minutes.artifacts:read`，正文在 `data.transcript`）。仅接受 UTF-8 TXT/Markdown，不声称 PDF/Word/OCR。
- 日历：`GET /open-apis/calendar/v4/calendars/:calendar_id/events`，`start_time`/`end_time` 为 **Unix 秒字符串**且不能与 `page_token`/`sync_token`/`anchor_time` 同时使用；显式区间是单页、不自动扩大范围也不补发请求，携带 cursor 时返回 `invalid_cursor`。上游 `page_size = max(50, limit)`；响应先逐项验证，再最多返回调用方 `limit` 条；超过 limit、达到上游 page_size 或上游 `has_more` 时 `CalendarPage.truncated=true`，真实区间 `next_cursor=null`（不提供无法执行的下一页）。`start_time`/`end_time` 的 `timestamp`（秒）或全天 `date` 归一为 UTC aware datetime。主日历按官方 `data.calendars[].calendar.calendar_id` 解析；显式配置 `calendar_id` 时跳过查询；空 → `no_primary_calendar`、歧义 → `ambiguous_calendar`、损坏 → `malformed_response`。
- 任务读：`GET /open-apis/task/v2/tasks`（user token，scope `task:task:read`/`task:task:write`）与 `GET /open-apis/task/v2/tasks/:task_guid`。`due.timestamp`（毫秒字符串）/`completed_at` 归一为 int。
- 任务写：`POST /open-apis/task/v2/tasks` 与 `PATCH /open-apis/task/v2/tasks/:task_guid`（`update_fields` 必填；列字段不赋值表示清空；`completed_at="0"` 恢复未完成）。adapter 已实现，但**能力仍 disabled，且由独立服务端门强制**：`FeishuService.require_task_write()` 在 real 模式对 create/update/complete 一律返回 `409 result_proof_unavailable`，`ActionService` 在写入 running 回执前检查、`FeishuTasks.execute` 再检查一次；provider 写调用次数为 0。`real_data_enabled` 只控制读取，不解除写禁用；本地 `project_progress` 不受该读取门影响。没有官方 endpoint 能按 `client_token` 证明丢失回执后的写结果，`task_result()` 返回无证据，unknown 不重发、不按标题猜成功。
- 生命周期与 deadline：一个完整业务操作（主日历→events、refresh→读取、正文回退、多项导入）持有**按调用线程归属**的租约；配置变更后新操作立即使用新配置，已开始的操作（含嵌套步骤与后续 HTTP）按旧配置快照完成，退役 provider 拒绝无关新操作与无租约的直接 adapter 调用，只在最后一个租约结束后关闭自有 client 一次。HTTP 边界使用可取消的整体 deadline：到期关闭底层传输连接并等待 worker 收敛后才返回，覆盖连接/响应头/正文/结束（响应头未完成时同样生效），注入 client 也不能绕过无重定向与大小上限。
- 授权代次：同一 profile/app 共享授权代次；logout、重新授权与凭据替换都会使在途 refresh 结果作废，不清除随后建立的新授权。
- 错误映射：按 HTTP 状态与官方业务码映射到 `token_expired` / `missing_scope` / `not_found` / `provider_timeout` / `provider_unavailable` / `malformed_response`；响应体、header、token、prompt 不出现在错误文本。
- 历史服务端门：旧 Stage B 固定 SHA 曾使用 `feishu.real_data_enabled` 作为数据读取开关。当前真实读取 / 导入与模型 organize/index/query 必须有绑定当前范围的本机一次性计划和独立确认；该旧 bool 即使为 true 也不能单独授权。未配置 Real / provider 时返回具体配置错误；计划不会调用 provider。真实 task 写仍由独立门返回 `result_proof_unavailable`。

- `GET /integrations/feishu/status` → `{mode, authorized, app_configured, identity, token_type: user, scopes, user_identity_verified, credential_error}`，不返回 token。`credential_error=credential_unreadable` 表示本机用户凭据无法解析（此时 `authorized=false`）。`mode` 反映实际配置（real 不会返回 fake）；`authorized` 只表示存在可用 **user** token；`app_configured` 只表示已保存应用密钥，不伪装成用户已授权；`user_identity_verified` 在本轮保持 false（未执行真实 user-info）。
- `POST /integrations/feishu/authorizations` → `{authorization_url, expires_in_seconds}`。Fake URL 使用精确配置的 callback 加 OAuth `code/state`；state 由本机会话创建、300 秒到期、一次性并受运行身份限制。
- `DELETE /integrations/feishu/authorizations` → 204，删除当前进程中的 Fake 用户授权，不清除应用凭据。
- `GET /integrations/feishu/callback?state&code`（或 `error`）→ 验证成功才返回 authorized。callback scheme / host / port / path 必须与 redirect_uri 一致；Origin 有值时须位于配置 allowlist。浏览器顶层回调可没有 Origin；无状态或非法 / 过期 / 重放 / 另一会话的状态都不能授权。除此以外飞书业务路由均要求 Bearer。
- `GET /integrations/feishu/materials?query&visibility&cursor&limit` → MaterialPage `{items, next_cursor}`；visibility 为 owner/shared 或不传，limit 为 1–30，默认 20；query 最多 500 字符。列表不获取正文。
- `POST /integrations/feishu/imports`：`{material_ids: 非空明确选择集合, operation_id}` → `{operation_id, state: succeeded/partial/failed, outcomes}`；每个 outcome 含 material_id、state、成功时 source_id/item_id、失败时 error_code/message。最多 30 个 ID，ID 与 operation_id 上限 200 字符。同 operation_id / 相同 ID 集合重放既有结果，变更集合返回 409。部分失败不是全成功；明确的新 ID 是新的导入意图。
- 正文为 file bytes，接受 UTF-8 TXT/Markdown，20 MB 上限；接受 text/plain、text/markdown、application/octet-stream（charset 若给出须 UTF-8），拒绝 JSON、非法编码、空文件、NUL 与不安全路径。原字节和 SHA-256 原样保留；SourceRecord.external_identity 记录 provider、material_id、token_type 与 content_type。只生成 source / pending intake，不生成稿件、批准或正式知识。
- `GET /integrations/feishu/calendar?start&end&timezone&cursor&limit` → `{items, next_cursor, timezone}`；必须显式传带时区时间和有效 IANA timezone，start < end，limit 1–30。空列表正常，读取无模型或任务写。
- 安全错误代码：authorization_denied、not_authorized、token_expired、missing_scope、not_found、malformed_response、provider_timeout、provider_unavailable、invalid_state、invalid_redirect、invalid_cursor、credential_missing、credential_unreadable、unsupported_capability、result_proof_unavailable、no_primary_calendar、ambiguous_calendar；内部异常文本不泄露到响应。
- 用户资源访问前，如 access token 将于 60 秒内过期，服务先调用 provider 的 refresh 契约；仅验证新 user token 仍有效且保留所需 scope 后，才替换当前 credential。refresh 在 lifecycle 锁内串行执行并二次检查，因此同一 profile/account 的并发读者只消耗一次 refresh token 并保留最新 token（离线并发回归覆盖）；真实 Keychain 拒绝/锁定/重启生命周期仍未验收。

已核对的真实协议约束仅作为适配边界：妙记搜索为 POST `/open-apis/minutes/v1/minutes/search`，分页为 page_size/page_token（最大 30），要求 user_access_token；不可把 tenant token 或其 scope 当 user scope。正文接口可返回文件，不能假设 JSON text。参见[官方妙记搜索](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/minutes-v1/minute/search)及 REUSE-MAP；本切片未发真实请求。

M2.1 审查补充：前端 callback 使用返回的绝对本机地址，限定 http loopback / 固定 callback path / 单一 OAuth code或error及state 参数；不改 host / port、不携带 cookie/Bearer、不跟随 redirect。callback 仅向配置 Origin 返回 Access-Control-Allow-Origin，错误响应也保留此读取边界，Cache-Control 为 no-store；业务路由认证不变。文本文件名验证共享 SourceStore.safe_source_filename 规则；逐项 capture 验证失败转安全 malformed_response 后继续其余选择。前端保留 API error code，expired/not_authorized 使状态失效并停读，missing_scope 只标记权限不足；不把 scope 缺失误当 token 到期。

## Stage B 设置与凭据扩展（候选实现与剩余门）

Fake/offline 是默认模式；这组路由的读取、保存和页面刷新都不联系 provider。连接测试是另一条显式调用，不通过 `GET/PATCH /settings` 触发。当前分支已实现 GET/PATCH、Keychain PUT/DELETE 和 settings UI。M4.2 包 A 为真实 Feishu 只读/导入及模型 organize/index/query 增加单次授权计划；`real_data_enabled` 兼容字段本身不授权真实外发。真实 task 写仍保持独立禁用。

### `GET /settings`

返回当前本机 profile 的非秘密配置摘要：

- `mode`: `fake` 或 `real`，缺失配置时默认为 `fake`。
- `feishu`: `app_id`、loopback `redirect_uri`、`identity`（app/user，默认 app）、`calendar_id`、`material_content`（transcript/artifacts）与 `real_data_enabled`（默认 false）。不返回 app secret 或 token；授权状态由 `GET /integrations/feishu/status` 单独返回。
- `llm`, `embedding`, `rerank`: 当前只实现 provider、allowlisted model、能力开关和受限地区；LLM 有本机账户标识，Model Studio embedding / rerank 共用 `model_studio_account_id`；Model Studio `base_url` 是**逐账户受限可配置**（allowlist：阿里云 HTTPS host + `/api/v1` 或 `/compatible-mode/v1` 路径），不再是完全固定派生。embedding 另返回 dimension 与 fingerprint。真实业务调用状态仍 disabled。
- `capabilities`: 按能力列出 `available/configured/disabled_reason`。该静态摘要不签发动作计划或确认；Feishu 实际调用还需提交已确认的精确计划。task create/edit/complete 因缺少可核实结果证明单独保持 unavailable（`result_proof_unavailable`）。不能因为读取可用而标成可写。
- `credential_status`: 各 provider 是否已设置、Keychain 是否可用。不得返回 Keychain item 名、secret 长度或 secret 值。

### `PATCH /settings`

只接受非秘密字段的 typed partial update。未知字段拒绝，范围、地区和模型标识按 provider allowlist 校验，写入当前本地 profile 并原子替换。更改 provider/model/dimension 不调用 provider、不重建索引、不估计实际账单；返回新配置与提示用户显式查看/确认索引计划。Model Studio endpoint 允许逐账户受限 base URL：必须是阿里云 HTTPS host 且路径为 `/api/v1` 或 `/compatible-mode/v1`，其他任意 URL 一律拒绝（有离线反例覆盖）。当前未实现多地区选择。

### `PUT /credentials/{provider}` 与 `DELETE /credentials/{provider}`

- `provider` 为 allowlist key：`feishu_app`、`feishu_user`、`deepseek`、`dashscope`。`feishu_user` 由 OAuth 流程写入，设置 UI 只展示 `feishu_app`/`deepseek`/`dashscope` 的配置状态。
- `PUT` 的 secret 只在 request body 内传输到 loopback FastAPI，再交给 Keychain；response 只含 `{provider, configured: true}`。错误不回显 body、值、长度或底层 Keychain 错误文本。设置变更不测试连接。
- `PUT` / `DELETE` 的 JSON body 带非秘密 `account_id`。Keychain item 按 app/profile/provider/账户标识的摘要隔离；切换账户标识后只显示并操作当前账户项。Feishu 应用凭据与 user token 使用**同一个 vault 命名空间**，账户标识均为当前 `app_id`：app secret 占 `feishu_app:<hash>`，user token 占 `feishu_user:<hash>`，因此设置 UI 写入的 app secret 就是 adapter 读取的槽，不存在两套互不通的 Keychain slot。`DELETE` 只删除当前 provider/account key，不扫描或删除用户其他 Keychain 项。
- Keychain 拒绝、锁定、不可用或删除失败采用一致的 `credential_store_unavailable` / `credential_access_denied` 错误。真实模式始终 fail closed，不回退内存或文件。
- 专用测试可传入合成 CredentialStore。合成 Keychain item 使用独立测试命名空间，测试结尾只清理本次创建的条目。

### 连接测试与 OAuth

连接测试必须是单独的用户动作并返回明确将要联系的 provider；不属于设置保存、预览或状态刷新。真实连接测试进入 Stage C 授权表。OAuth state 一次性、限时并绑定当前本机会话**与发起时的授权代次**；callback 在可能阻塞的应用凭据读取之前与之后、token 请求前以及凭据回写前复核该代次，logout 或更新的授权会使旧 callback 失效并返回 `invalid_state`（不写凭据、不恢复 `authorized`、不覆盖新授权）；重复 callback 只 exchange 一次。callback 使用原样注册 URI，避免日志记录 code/state/token，结果 `Cache-Control: no-store`。真实 refresh 必须串行化并以原子替换保留新 token；并发失败不能覆盖更新过的新 refresh token。登出删除当前 profile/account 的 user credential，不删除应用秘密或其他账号项。

### 持久化与数据边界

非秘密配置位于 local profile；workspace 只保留可迁移业务内容，不能保存 secrets、OAuth state、provider response、聊天历史或索引。Keychain 账户 key 使用 profile、provider 与账户标识摘要；真实模式使用同一个 vault 命名空间保存 app secret 与 user token，OS Keychain 拒绝/锁定/重启的实际生命周期仍未验收，真实 OAuth 与数据请求次数为 0。连接和模型请求应仅由服务端发出，日志只记录安全错误码、request id 和必要计数。


## M2.2 已实施的独立动作与任务 Fake 契约

- `POST /actions` 输入 `{action_id: UUID, kind, payload, candidate_id?}`。payload 原样保存；JSON UTF-8、ensure_ascii=false、sort_keys=true、紧凑 separators、allow_nan=false 得到 SHA-256。kind / candidate_id 独立比对。同 ID / 同值返回既有对象（201），不同值 409。不同合法 ID 允许同标题。
- `GET /action-intents?cursor&limit` → `{items, next_cursor}`，默认20、1–100；按 action UUID 排序、跨月汇总查找。`GET /actions` 无参数保留 M1 ActionCandidate 数组；显式 cursor/limit 返回候选页。`GET /actions/{id}` 返回保存的 intent / receipt。
- `PATCH /actions/{id}` 输入 `{expected_payload_sha256, payload}`；只允许 proposed/confirmed，改动清除确认，旧 confirmation_id 保留失效证据且不能复用。`POST /confirmations` 和 `/executions` 输入 `{payload_sha256, confirmation_id}`，hash 必须匹配、确认 ID 非空。确认不执行；执行先在库锁内保存 running 与确认，再调用 provider。进行中相同请求 202 + Location，unknown/terminal 200 返回原状态，无重写。
- `/reconciliations` 输入 `{}`，不发送任务写。Fake 执行证据必须含与当前动作匹配的稳定 client_token、动作类型、目标 GUID（适用时）及返回任务；业务层还校验目标和请求字段结果。普通任务对象、同名/无关任务或 token / 结果不匹配都不能证明成功，仍为 unknown。Project progress 仅接受本地 writer 凭据。`/outcomes` 输入 `{payload_sha256, confirmation_id, state: succeeded/failed, evidence}`；只接受 unknown 的独立明确结果；同核实 ID / 同值可重放，不同值409。核实证据保留；迟到响应不能覆盖已明确终态。
- TaskCreate `{summary, description?, due}`：due 必须显式给 null 或 `{value, is_all_day: 严格bool, timezone: IANA}`；标题不能空白。全天 value 是 ISO 日期；具体时间须带与 IANA 时区一致的偏移。原文和时区保留在 intent，具体时间映射为毫秒 timestamp **字符串**，不向 provider 猜发 timezone 字段。
- TaskUpdate `{task_guid, task: {选定字段}, update_fields}`：仅 summary / description / due；update_fields 必须与给出的字段完全一致，不能重复。due:null 明确清空日期；description:"" 明确清空描述。未选字段不发送。TaskComplete `{task_guid}`：先读 provider 完成态，已完成直接成功；否则 PATCH completed_at 毫秒字符串，update_fields=[completed_at]。
- 创建、编辑和完成的成功回执须以 GUID、实际请求字段及归一化日期语义验证；不匹配、字段未生效或完成仍为 completed_at=0 时按 unknown 保存，不重发未知动作。
- `GET /integrations/feishu/tasks?cursor&limit`（默认20、1–100）与 `/{task_guid}` 只读 provider；TaskPage items/next_cursor。API 的 FeishuTask 为只读投影，due.timestamp / completed_at 归一为 int。读取要求 user 的 task:task:read 或 task:task:write，写要求 task:task:write；复用 M2.1 session / CredentialStore。没有本地任务状态修改入口。
- ProjectProgress `{project_id: UUID, expected_version: 非负严格int, progress}`：独立 action 写 project manifest 的 progress / progress_version / progress_confirmation_id；锁 + 预期版本 + 既有 write_intent 事务，知识批准不调用它。

真实协议已从官方 `.md` 页面逐字段确证（2026-10-10）：Task v2 REST GET/POST `/open-apis/task/v2/tasks`、GET/PATCH `/:task_guid`、PATCH `task`+`update_fields`；列表 `page_size` 1–100 默认 50、`type=my_tasks`、仅接受 user token，`items/has_more/page_token`。[列取任务列表](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/list)、[创建任务](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/create)、[更新任务](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/patch)。client_token 从 workspace UUID + action UUID 派生稳定 UUID，仅创建传给 provider；官方仅说明其触发后端幂等行为，不能代替本地永久禁止未知重发。PATCH 的 token 参数仅供 Fake 留执行证据，不是额外 REST 字段。真实请求仍未执行。

**真实 task 协议现状（2026-10-10 起可从官方 `.md` 页面确证）：**官方 create/patch 文档明确 `due.timestamp` 与 `completed_at` 为距 1970-01-01 UTC 的**毫秒字符串**，`is_all_day=true` 时只解析并存储日期部分；PATCH 的 `update_fields` 必填，列字段不赋值表示清空，`completed_at="0"` 恢复未完成，已完成任务不能再次完成。真实 adapter 已按此映射实现。仍未确证的是账号侧实际 normalization、以及**丢失回执后按 `client_token` 独立证明写结果**的能力：没有任何官方 endpoint 提供该查询，因此 `task_result()` 返回无证据，任务写能力保持 disabled，unknown 不重发、不按标题或普通列表猜成功。全天午夜 conversion 不再只是 Fake 约定，但真实账号行为仍需 Stage C 复验。当前 Feishu adapter 已实现；真实请求次数为 0。

## 2026-10-11 Stage B 离线收口补充

Provider HTTP 使用请求独立传输（ADR 0007）；调用返回前解析/传输 worker 已结束，限额包括完整 JSON wire，identity 以外响应编码拒绝。应用身份操作不读取用户凭据槽；OAuth 结果须匹配发起代次，登出/新授权/配置切换后旧结果不得写回。租约准入与退役原子协调。

今日任务区由 API 的 mode 区分 Fake/Real；模式尚未确定时远端写控件禁用。Real 创建/编辑/完成与旧 confirmed 的执行入口禁用，项目进度保持本地独立确认。服务端三层任务写门仍返回 409 `result_proof_unavailable`，不能仅凭 UI 禁用获得安全结论。

浏览器/原生的合成凭据故障证据不等于 OS Keychain、真实身份或账户验收。阶段状态与源码/QA SHA 见最新交接。

真实 OAuth UI 只展示已校验的官方 HTTPS 授权链接，由用户在独立浏览器完成后刷新本机 `/status`；不 fetch 外部authorize URL、不模拟 code、不自动轮询旧authorized值宣称本轮成功。原生target=_blank仅允许用户点击官方authorize链接交系统浏览器；Fake窄callback helper保持不变。实际外部打开、callback端口注册及真实身份验证仍为C证据门。应用身份日历不要求用户OAuth；mode/identity来自API。

2026-10-11刷新重启防重发：user凭据vault同槽新增本地refresh_consumed标记（旧凭据缺字段默认为false）。发送单次refresh之前必须成功保存true；超时、响应损坏或进程中断后重启仍拒绝旧token，重新授权恢复。合法轮换的新token保存false；失败保存不发送HTTP。此字段不是HTTP响应DTO或已验证身份，不泄露凭据。

迁移边界：本轮真实 OAuth/token 调用始终为 0，真实 adapter 尚未发布，也未迁移 SWB/SK 或外部凭据。缺少 refresh_consumed 的兼容形状只经合成历史 fixture 验证；它不能证明旧 token 未被消费。未来若导入或恢复消费历史未知的旧真实凭据，必须先重新授权，不得据默认 false 宣称跨旧版本的 no-resend 保证。本轮保证从本实现成功保存消费预留后开始，既有单次调用账本不重置。
