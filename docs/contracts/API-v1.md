# 本地 API 契约 v1

状态：实施基准；M1.1–M1.3 路由已实现，其余路由按计划分阶段交付。前缀 /api/v1；JSON 使用 snake_case、稳定小写枚举，OpenAPI / TypeScript 从后端类型生成。

## 共用对象与认证

- PageSnapshot：page_id、relative_path、metadata、body、content_sha256、storage_area、approval_state（confirmed / pending / invalid）、validity。用户不能上传 storage_area 来改变判定。
- Draft：draft_id、input_ids、target_page_id、metadata、body、expected_base_sha256、conflicts、resolutions、state（pending / confirmed / rejected）。
- Action：action_id、kind（feishu_task_create / feishu_task_update / feishu_task_complete / project_progress）、payload、payload_sha256、state、confirmation_id、provider_result。
- MutationResult：operation_id、state、changed_paths、page_versions、saved_locally。没有自动 cloud_synced 字段。
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
| POST /journal/{kind} | kind:log/thought，正文、可选关联、confirmation_id；复用 PageWriter，不另写落盘 |
| POST /intake/items | 粘贴内容 / 随手记录、operation_id → item；纯本地，不调用模型（已实现） |
| POST /intake/files | multipart txt/md 文件及同批次标识 → 来源与 item；保存原字节（已实现，20 MB 上限） |
| GET /intake/items | 可见待整理列表，不调用模型（已实现） |
| POST /intake/jobs | 明确选择的 item_ids、operation_id、线 / 项目、可选 reprocess=true → Job；FakeLLM 生成多个稿与 action 候选（已实现）。有未审核稿或正在运行的来源拒绝新作业；完成、失败、取消的来源必须由用户明确选择重新整理，且使用新的 operation_id。相同 operation_id 重试只返回原作业状态，不重复调用 provider。 |
| GET /jobs/{id}；DELETE /jobs/{id} | 查询 / 请求取消（已实现；同步 provider 当前无法中断运行中的调用） |
| GET /drafts；GET /drafts/{id}；PATCH /drafts/{id} | 完整稿、来源、冲突；编辑带稿件版本（已实现） |
| POST /drafts/{id}/confirmations | confirmation_id、expected_version、重要冲突处理结果 → MutationResult（已实现） |
| GET /actions；POST /actions/{id}/executions | 候选只读列表已实现；明确批准的 action / payload hash → Job / receipt 后续阶段 |
| POST /actions | kind、payload、operation_id → proposed Action；供手动任务表单及项目进度建议使用，只保存本地候选，不执行外部写 |
| POST /actions/{id}/reconciliations | 只读核实未知远端结果；没有证据时仍 unknown |
| GET /integrations/feishu/status | 权限 / 登录状态，无 token 值 |
| POST /integrations/feishu/authorizations | 创建 OAuth 登录意图，state 绑定当前本机会话 |
| GET /integrations/feishu/callback | 验证已发起 OAuth state / redirect，存钥匙串 |
| GET /integrations/feishu/materials | 搜索 / 分页的可见材料 metadata；不调模型 |
| POST /integrations/feishu/imports | 用户选择的材料 ID、operation_id → 来源与 item；不隐式整理 |
| GET /integrations/feishu/calendar；GET /integrations/feishu/tasks | 读取日历 / 正式任务；任务写统一走 Action |
| POST /index/plans | mode:initial/incremental/full/model_change → 页面 / 分块范围、费用估计、fingerprint |
| POST /index/jobs；GET /index/status | plan_id、必要的 confirmation_id → Job；自动增量由批准 mutation 发起 |
| POST /queries；DELETE /queries/{request_id} | question、conversation_id?、role_id?、purpose:current/history → SSE / 取消 |
| GET /conversations；GET /conversations/{id}；DELETE /conversations/{id} | 本机历史；不进入工作库语料 |
| GET /roles；POST /roles；PATCH /roles/{id}；DELETE /roles/{id} | 本机角色，不能修改批准 / 工具权限 |
| GET /memory/candidates；POST /memory/candidates | 仅用户明确表达的 message_id / text → 本机待确认候选 |
| POST /memory/candidates/{id}/confirmations | confirmation_id、用户编辑内容 → 活跃本机记忆 |
| GET /memory；PATCH /memory/{id}；DELETE /memory/{id} | 管理活跃本机记忆 |
| GET /settings；PATCH /settings | 模型 / endpoint / fingerprint 等非秘密配置；变更模型不静默重建 |
| PUT /credentials/{provider} | 用户明确输入的秘密交钥匙串；响应只返回 configured 状态 |

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

默认且唯一可配置模式为 `fake`；所有外部行为通过注入 FeishuProvider，默认实现没有网络代码。CredentialStore 隔离 user access/refresh token；本切片使用进程内 MemoryCredentialStore。未实施真实 app-secret / 钥匙串设置入口，不读取现有凭据。

- `GET /integrations/feishu/status` → `{mode, authorized, token_type: user, scopes}`，不返回 token。
- `POST /integrations/feishu/authorizations` → `{authorization_url, expires_in_seconds}`。Fake URL 使用精确配置的 callback 加 OAuth `code/state`；state 由本机会话创建、300 秒到期、一次性并受运行身份限制。
- `GET /integrations/feishu/callback?state&code`（或 `error`）→ 验证成功才返回 authorized。callback scheme / host / port / path 必须与 redirect_uri 一致；Origin 有值时须位于配置 allowlist。浏览器顶层回调可没有 Origin；无状态或非法 / 过期 / 重放 / 另一会话的状态都不能授权。除此以外飞书业务路由均要求 Bearer。
- `GET /integrations/feishu/materials?query&visibility&cursor&limit` → MaterialPage `{items, next_cursor}`；visibility 为 owner/shared 或不传，limit 为 1–30，默认 20；query 最多 500 字符。列表不获取正文。
- `POST /integrations/feishu/imports`：`{material_ids: 非空明确选择集合, operation_id}` → `{operation_id, state: succeeded/partial/failed, outcomes}`；每个 outcome 含 material_id、state、成功时 source_id/item_id、失败时 error_code/message。最多 30 个 ID，ID 与 operation_id 上限 200 字符。同 operation_id / 相同 ID 集合重放既有结果，变更集合返回 409。部分失败不是全成功；明确的新 ID 是新的导入意图。
- 正文为 file bytes，接受 UTF-8 TXT/Markdown，20 MB 上限；接受 text/plain、text/markdown、application/octet-stream（charset 若给出须 UTF-8），拒绝 JSON、非法编码、空文件、NUL 与不安全路径。原字节和 SHA-256 原样保留；SourceRecord.external_identity 记录 provider、material_id、token_type 与 content_type。只生成 source / pending intake，不生成稿件、批准或正式知识。
- `GET /integrations/feishu/calendar?start&end&timezone&cursor&limit` → `{items, next_cursor, timezone}`；必须显式传带时区时间和有效 IANA timezone，start < end，limit 1–30。空列表正常，读取无模型或任务写。
- 安全错误代码：authorization_denied、not_authorized、token_expired、missing_scope、not_found、malformed_response、provider_timeout、provider_unavailable、invalid_state、invalid_redirect、invalid_cursor；内部异常文本不泄露到响应。

已核对的真实协议约束仅作为适配边界：妙记搜索为 POST `/open-apis/minutes/v1/minutes/search`，分页为 page_size/page_token（最大 30），要求 user_access_token；不可把 tenant token 或其 scope 当 user scope。正文接口可返回文件，不能假设 JSON text。参见[官方妙记搜索](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/minutes-v1/minute/search)及 REUSE-MAP；本切片未发真实请求。
