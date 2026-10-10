# 本地 API 契约 v1

状态：v1 完整实施基准；M1 与 M2.1–M2.3 Fake 路由已实现。当前 Stage B 候选增加 profile 设置、Keychain 边界、stub-tested DeepSeek / Model Studio adapters 及 Fake-only Feishu 生命周期。真实业务模型调用在服务端保持 disabled；另有三个只接受固定合成输入、profile 级每 provider 限一次的模型 smoke 路由。Feishu 真实 OAuth / 数据 adapter 与实际 smoke 尚未实现。Settings 读写不联系 provider；审批后真实 embedding 索引须用户另行确认计划。下表同时包含已实现和计划路由；不得据契约条目声称真实 provider 已验证。前缀 /api/v1；JSON 使用 snake_case、稳定小写枚举，OpenAPI / TypeScript 从后端类型生成。

## 共用对象与认证

- PageSnapshot：page_id、relative_path、metadata、body、content_sha256、storage_area、approval_state（confirmed / pending / invalid）、validity。用户不能上传 storage_area 来改变判定。
- Draft：draft_id、input_ids、target_page_id、metadata、body、expected_base_sha256、conflicts、resolutions、state（pending / confirmed / rejected）。
- Action：action_id、kind（feishu_task_create / feishu_task_update / feishu_task_complete / project_progress）、payload、payload_sha256、state、confirmation_id、provider_result。
- MutationResult：operation_id、state、changed_paths、page_versions、saved_locally；正式页确认入口另返回 index_update（not_enabled / updated / update_failed），区分首次索引、成功自动增量和保存后索引失败。没有自动 cloud_synced 字段。
- Job：job_id、kind、state（queued / running / succeeded / failed / unknown / cancelled）、progress、result、error。进度不虚构百分比，取消不保证远端未计费。
- IntakeItem：item_id、source_id、title、filename、original_relative_path、state（pending / processing / reviewing / completed / failed / cancelled）、latest_job_id。状态反映最新整理作业与其稿件，不由前端猜测。
- Citation：page_id、content_sha256、chunk_id、heading、excerpt、validity；客户端用稳定页面路由打开，不信任任意文件 URL。
- Answer：answer_id、question、text、citations、inferences、missing_information、purpose、index_status。infer / advice 不伪装来源事实。

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
| GET /intake/items | 可见待整理列表，不调用模型（已实现） |
| POST /intake/jobs | 明确选择的 item_ids、operation_id、线 / 项目、可选 reprocess=true → Job；FakeLLM 生成多个稿与 action 候选（已实现）。有未审核稿或正在运行的来源拒绝新作业；完成、失败、取消的来源必须由用户明确选择重新整理，且使用新的 operation_id。相同 operation_id 重试只返回原作业状态，不重复调用 provider。 |
| GET /jobs/{id}；DELETE /jobs/{id} | 查询 / 请求取消（已实现；同步 provider 当前无法中断运行中的调用） |
| GET /drafts；GET /drafts/{id}；PATCH /drafts/{id} | 完整稿、来源、冲突；编辑带稿件版本（已实现） |
| POST /drafts/{id}/confirmations | confirmation_id、expected_version、重要冲突处理结果 → MutationResult（已实现） |
| GET /actions；GET /action-intents；GET /actions/{id} | 旧候选数组兼容；显式 cursor/limit 候选分页；独立 Action 列表 / 回执按 cursor/limit 查询（M2.2 Fake 已实现） |
| PATCH /actions/{id}；POST /actions/{id}/confirmations；POST /actions/{id}/executions | 预期 hash 编辑；最终 payload 独立确认；已确认动作原子认领后执行，进行中重放 202 + Location，其他既有状态原样返回 |
| POST /actions | action_id、kind、payload、可选 candidate_id → proposed Action；保留候选 / 稿件 / 来源关联，仅保存意图，不执行外部写 |
| POST /actions/{id}/reconciliations；POST /actions/{id}/outcomes | 只读核实未知结果；无证据保持 unknown；用户独立确认的 state / evidence / confirmation_id 才能记录明确结果 |
| GET /integrations/feishu/status | 权限 / 登录状态，无 token 值 |
| POST /integrations/feishu/authorizations | 创建 OAuth 登录意图，state 绑定当前本机会话 |
| DELETE /integrations/feishu/authorizations | 登出并清除当前用户授权 |
| GET /integrations/feishu/callback | 验证已发起 OAuth state / redirect；当前 Fake 存内存，B 的真实模式需持久化到钥匙串 |
| GET /integrations/feishu/materials | 搜索 / 分页的可见材料 metadata；不调模型 |
| POST /integrations/feishu/imports | 用户选择的材料 ID、operation_id → 来源与 item；不隐式整理 |
| GET /integrations/feishu/calendar；GET /integrations/feishu/tasks | 读取日历 / 正式任务；任务写统一走 Action |
| POST /index/plans | mode:initial/incremental/full/model_change → 页面 / 分块范围、费用估计、fingerprint |
| POST /index/jobs；GET /index/status | 首次索引或用户请求的 full / model_change 计划仍需显式确认；已有索引时，批准 mutation 自动执行同 fingerprint 的 incremental。状态返回 fingerprint、索引页/分块数、当前页数、stale_pages 与 state（not_ready / ready / stale）；旧版本不得作为当前引用 |
| POST /queries；DELETE /queries/{request_id} | question、conversation_id?、role_id?、purpose:current/history → SSE / 取消 |
| GET /conversations；GET /conversations/{id}；DELETE /conversations/{id} | 本机历史；不进入工作库语料 |
| GET /roles；POST /roles；PATCH /roles/{id}；DELETE /roles/{id} | 本机角色，不能修改批准 / 工具权限 |
| GET /memory/candidates；POST /memory/candidates | 仅用户明确表达的 message_id / text → 本机待确认候选 |
| POST /memory/candidates/{id}/confirmations | confirmation_id、用户编辑内容 → 活跃本机记忆 |
| GET /memory；PATCH /memory/{id}；DELETE /memory/{id} | 管理活跃本机记忆 |
| GET /settings；PATCH /settings | 当前本地 profile 的非秘密配置；Stage B 候选已实现原子本地保存；设置读取 / 保存不联网 |
| PUT /credentials/{provider}；DELETE /credentials/{provider} | Stage B 候选已实现显式 macOS Keychain 和测试注入边界；响应只返回 configured 状态 |
| POST /settings/connections/{provider} | 计划路由；尚未实现。连接检查进入 Stage C 授权门，不能由刷新设置触发 |
| GET /provider-smoke；POST /provider-smoke/deepseek-chat；POST /provider-smoke/model-studio-embedding；POST /provider-smoke/model-studio-rerank | 单独限额的合成连接 smoke；provider 在本机已保存并启用 Real 配置时可调用，固定合成输入、每个 app profile 每 provider 最多一次。尝试在出网前原子记账，失败/超时也占额，无自动重试；普通业务模型路径仍被服务端拒绝。真实 smoke 尚未执行；Feishu OAuth 没有对应 smoke 路由 |

直接撰写保存是用户确认入口，不是模型可用工具。对已有页确认前以最新磁盘版本比较基准；写入 API 不能接受模型提交的 approval。

前端任务表单日期由用户指定，不猜开始 / 截止日期；适配层按飞书当前协议发送和验证，已有完成任务重复完成按已完成成功处理。

## 查询 SSE

每事件 JSON 为 request_id、seq、type、data；seq 严格递增。type 为 status、citation、delta、completed、error。completed 携带完整 Answer，error 有统一错误结构；取消 / 断流不写一个“成功完整答案”。

在聚合上下文、邻页扩展和引用阶段读取 PageSnapshot，再用统一 gate 加缓存版本复验。索引未就绪或部分更新时返回 index_status，不能用旧片段补齐缺失证据。

用户角色与记忆只改变问答上下文 / 表达，不允许去掉证据边界、执行写动作或把助手建议写入正式页。

冲突稿必须逐项选择一个已展示的依据或明确标为 unresolved；正式正文会附加“冲突处理结果”，记录选择或说明未决尚未成为确定事实。确认页与已确认稿件保存同一最终正文。

## 对接测试边界

Fake providers 在 integrations 协议边界替代网络，工作库、事务、索引资格、路由和 UI 保持真实。不得把真实受测业务服务整体 mock 掉。

 provider 的 malformed / denied / timeout / unknown 响应各有独立 fixture。实际账户与付费质量验收单列，测试者不因为 mock 通过就填写外部场景 passed。

## M2.1 已实施的飞书 Fake 契约

默认且唯一可配置模式为 `fake`；所有外部行为通过注入 FeishuProvider，默认实现没有网络代码。CredentialStore 分别隔离 AppCredentials（app_id / SecretStr app_secret）与 user access/refresh token；非秘密 FeishuConfig 保存 app_id 和精确 redirect_uri。本切片使用进程内 MemoryCredentialStore，仅注入合成秘密，未实施真实账户适配器、app-secret 设置 UI 或 OS Keychain 权限路径，不读取现有凭据。

- `GET /integrations/feishu/status` → `{mode, authorized, token_type: user, scopes}`，不返回 token。
- `POST /integrations/feishu/authorizations` → `{authorization_url, expires_in_seconds}`。Fake URL 使用精确配置的 callback 加 OAuth `code/state`；state 由本机会话创建、300 秒到期、一次性并受运行身份限制。
- `DELETE /integrations/feishu/authorizations` → 204，删除当前进程中的 Fake 用户授权，不清除应用凭据。
- `GET /integrations/feishu/callback?state&code`（或 `error`）→ 验证成功才返回 authorized。callback scheme / host / port / path 必须与 redirect_uri 一致；Origin 有值时须位于配置 allowlist。浏览器顶层回调可没有 Origin；无状态或非法 / 过期 / 重放 / 另一会话的状态都不能授权。除此以外飞书业务路由均要求 Bearer。
- `GET /integrations/feishu/materials?query&visibility&cursor&limit` → MaterialPage `{items, next_cursor}`；visibility 为 owner/shared 或不传，limit 为 1–30，默认 20；query 最多 500 字符。列表不获取正文。
- `POST /integrations/feishu/imports`：`{material_ids: 非空明确选择集合, operation_id}` → `{operation_id, state: succeeded/partial/failed, outcomes}`；每个 outcome 含 material_id、state、成功时 source_id/item_id、失败时 error_code/message。最多 30 个 ID，ID 与 operation_id 上限 200 字符。同 operation_id / 相同 ID 集合重放既有结果，变更集合返回 409。部分失败不是全成功；明确的新 ID 是新的导入意图。
- 正文为 file bytes，接受 UTF-8 TXT/Markdown，20 MB 上限；接受 text/plain、text/markdown、application/octet-stream（charset 若给出须 UTF-8），拒绝 JSON、非法编码、空文件、NUL 与不安全路径。原字节和 SHA-256 原样保留；SourceRecord.external_identity 记录 provider、material_id、token_type 与 content_type。只生成 source / pending intake，不生成稿件、批准或正式知识。
- `GET /integrations/feishu/calendar?start&end&timezone&cursor&limit` → `{items, next_cursor, timezone}`；必须显式传带时区时间和有效 IANA timezone，start < end，limit 1–30。空列表正常，读取无模型或任务写。
- 安全错误代码：authorization_denied、not_authorized、token_expired、missing_scope、not_found、malformed_response、provider_timeout、provider_unavailable、invalid_state、invalid_redirect、invalid_cursor；内部异常文本不泄露到响应。
- 用户资源访问前，如 access token 将于 60 秒内过期，服务先调用 provider 的 refresh 契约；仅验证新 user token 仍有效且保留所需 scope 后，才替换当前 credential。Fake 测试覆盖 refresh token 轮换和失效 refresh token；并发串行化、真实 provider 与持久化 Keychain 生命周期尚未实现。

已核对的真实协议约束仅作为适配边界：妙记搜索为 POST `/open-apis/minutes/v1/minutes/search`，分页为 page_size/page_token（最大 30），要求 user_access_token；不可把 tenant token 或其 scope 当 user scope。正文接口可返回文件，不能假设 JSON text。参见[官方妙记搜索](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/minutes-v1/minute/search)及 REUSE-MAP；本切片未发真实请求。

M2.1 审查补充：前端 callback 使用返回的绝对本机地址，限定 http loopback / 固定 callback path / 单一 OAuth code或error及state 参数；不改 host / port、不携带 cookie/Bearer、不跟随 redirect。callback 仅向配置 Origin 返回 Access-Control-Allow-Origin，错误响应也保留此读取边界，Cache-Control 为 no-store；业务路由认证不变。文本文件名验证共享 SourceStore.safe_source_filename 规则；逐项 capture 验证失败转安全 malformed_response 后继续其余选择。前端保留 API error code，expired/not_authorized 使状态失效并停读，missing_scope 只标记权限不足；不把 scope 缺失误当 token 到期。

## Stage B 设置与凭据扩展（候选实现与剩余门）

Fake/offline 是默认模式；这组路由的读取、保存和页面刷新都不联系 provider。连接测试是另一条显式调用，不通过 `GET/PATCH /settings` 触发。当前分支已实现 GET/PATCH、Keychain PUT/DELETE 和 settings UI；真实 provider 连接与业务调用尚未启用，能力摘要保持 disabled。

### `GET /settings`

返回当前本机 profile 的非秘密配置摘要：

- `mode`: `fake` 或 `real`，缺失配置时默认为 `fake`。
- `feishu`: 当前只实现 `app_id` 与 loopback `redirect_uri`；授权状态、用户 scope、账号标签尚未实现。不返回 app secret 或 token。
- `llm`, `embedding`, `rerank`: 当前只实现 provider、allowlisted model、能力开关和受限地区；LLM 有本机账户标识，Model Studio embedding / rerank 共用 `model_studio_account_id`，候选只允许中国大陆 endpoint。embedding 另返回 dimension 与 fingerprint。真实调用状态仍 disabled。
- `capabilities`: 按能力列出 `available/configured/disabled_reason`。协议未证实的 Feishu task create/edit/complete 可单独 disabled，不能因为读取可用而标成可写。
- `credential_status`: 各 provider 是否已设置、Keychain 是否可用。不得返回 Keychain item 名、secret 长度或 secret 值。

### `PATCH /settings`

只接受非秘密字段的 typed partial update。未知字段拒绝，范围、地区和模型标识按 provider allowlist 校验，写入当前本地 profile 并原子替换。更改 provider/model/dimension 不调用 provider、不重建索引、不估计实际账单；返回新配置与提示用户显式查看/确认索引计划。endpoint 使用固定 provider mapping 派生，禁止任意 URL。当前未实现 workspace endpoint / 多地区选择。

### `PUT /credentials/{provider}` 与 `DELETE /credentials/{provider}`

- `provider` 为 allowlist key，例如 `feishu_app`, `deepseek`, `dashscope`。
- `PUT` 的 secret 只在 request body 内传输到 loopback FastAPI，再交给 Keychain；response 只含 `{provider, configured: true}`。错误不回显 body、值、长度或底层 Keychain 错误文本。设置变更不测试连接。
- `PUT` / `DELETE` 的 JSON body 带非秘密 `account_id`。Keychain item 按 app/profile/provider/账户标识的摘要隔离；切换账户标识后只显示并操作当前账户项。Feishu 应用凭据使用当前 `app_id` 作为账户标识；真实 OAuth user token 持久化仍未实现。`DELETE` 只删除当前 provider/account key，不扫描或删除用户其他 Keychain 项。
- Keychain 拒绝、锁定、不可用或删除失败采用一致的 `credential_store_unavailable` / `credential_access_denied` 错误。真实模式始终 fail closed，不回退内存或文件。
- 专用测试可传入合成 CredentialStore。合成 Keychain item 使用独立测试命名空间，测试结尾只清理本次创建的条目。

### 连接测试与 OAuth

连接测试必须是单独的用户动作并返回明确将要联系的 provider；不属于设置保存、预览或状态刷新。真实连接测试进入 Stage C 授权表。OAuth state 一次性、限时并绑定当前本机会话；callback 使用原样注册 URI，避免日志记录 code/state/token，结果 `Cache-Control: no-store`。真实 refresh 必须串行化并以原子替换保留新 token；并发失败不能覆盖更新过的新 refresh token。登出删除当前 profile/account 的 user credential，不删除应用秘密或其他账号项。

### 持久化与数据边界

非秘密配置位于 local profile；workspace 只保留可迁移业务内容，不能保存 secrets、OAuth state、provider response、聊天历史或索引。Keychain 账户 key 使用 profile、provider 与账户标识摘要；当前 Feishu user-token refresh/logout 只在 Fake 进程内实现，真实 OAuth、持久化和请求仍未完成。连接和模型请求应仅由服务端发出，日志只记录安全错误码、request id 和必要计数。


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

真实协议只核对公开文档 / 官方 SDK，不发真实请求。Task v2 REST GET/POST `/open-apis/task/v2/tasks`、GET/PATCH `/:task_guid`、PATCH task/update_fields；provider 分页 page_size/page_token 和 items/has_more/page_token。[官方 Task 概述](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/overview)、[官方 Python 请求模型](https://github.com/larksuite/oapi-sdk-python/tree/v2_main/lark_oapi/api/task/v2/model)、[官方 Go SDK 注释](https://pkg.go.dev/github.com/larksuite/oapi-sdk-go/v3/service/task/v2)。client_token 从 workspace UUID + action UUID 派生稳定 UUID，仅创建传给 provider；官方成功幂等窗口5分钟，不能代替本地永久禁止未知重发。PATCH 的 token 参数仅供 Fake 留执行证据，不是额外 REST 字段。

**未验证的真实语义：**官方概述提示全天时间有特殊规则，可访问资料未确证其日期提取时区。当前全天午夜 timestamp 是明确的 Fake 约定，原始日期 + IANA 永久保留；真实 adapter 必须先核证并验收。Fake 精度 / 全天返回只是模拟，不代表真实 normalization。`task_result(token)` 仅为 Fake 合成证据查询；无已核实真实查询能力时必须返回无证据或安全错误并保留 unknown，不能按标题 / 列表猜成功。当前候选只实现 Fake provider，不把该证据契约描述成真实 Feishu 端点。
