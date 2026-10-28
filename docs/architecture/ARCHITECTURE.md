# 运行架构与模块责任

状态：v1 工程基准；产品语义以产品规格和工作库契约为准。

## 运行方式

每台 Mac 运行一套应用。DMG 包含薄 macOS 壳、构建后的 WebUI 和打包 Python 服务；使用者不需要装 Python、Node 或 Docker。

React / TypeScript → 受保护的本地 FastAPI → 工作库 / 本地存储 / 外部服务适配器。Swift 只负责窗口、文件选择、钥匙串桥接、服务启停和系统打开操作；不放入知识处理或第二套聊天界面。

后端只监听 127.0.0.1。开发默认端口 8793，WebUI 为 5173；隔离复演可分别通过 `SUMMIT_API_PORT` / `SUMMIT_WEB_PORT` 指定，并将 `SUMMIT_API_TARGET` 指向同一 API。启动器为本次运行分配身份，UI 只连接身份匹配的服务；退出时只终止自己启动的进程组。生产由启动器传递会话 token，通过 Authorization: Bearer 保护 API，限制允许的 origin。token 不进 URL、构建产物或诊断日志。

模型及飞书外部连接由后端执行。前端不持有长期 API 密钥。飞书 OAuth 的 redirect_uri 使用用户配置并与应用注册一致；不能擅自换端口破坏回调。浏览器回调仅通过限时、一次性且绑定本机会话的 state 认证，具体边界见 API 契约；其他业务 API 始终需要 Bearer。

## 源码模块

| 位置 | 责任 |
|---|---|
| src/summit_everything/domain/ | 数据类型、内容指纹、检索资格、状态；无 I/O |
| src/summit_everything/workspace/ | manifest、目录、Markdown、来源、事务、身份锁、恢复 |
| src/summit_everything/intake/ | 输入与批次、整理、完整稿、差异、冲突、批准 |
| src/summit_everything/retrieval/ | 分块、增量索引、混合召回、重排、引用、查询规划 |
| src/summit_everything/integrations/ | LLM / embedding / rerank / Feishu 的协议适配 |
| src/summit_everything/local/ | 本地会话、角色、记忆、索引与凭据抽象 |
| src/summit_everything/api/ | FastAPI DTO、路由、认证、任务与流式事件 |
| web/ | React 界面、生成的 API 类型及真实浏览器测试 |
| native/ | 薄 macOS 壳与生命周期测试 |
| tests/ | 单元、契约、集成和去标识材料 |

内部 DMG 交付目标为 arm64 macOS 应用；构建设置声明 macOS 13 minimum。实际构建与安装验收范围按对应固定 SHA 的报告记录；本文不维护阶段状态。飞书具有 HTTP adapter，Fake provider 仍供默认离线开发与测试使用；真实 provider、OS Keychain、真实服务和用户交付分别受独立授权与验收门约束。当前状态见[进展账本](../implementation/PROGRESS.md)。不要创建无实际用途的空服务。

工作库 context 至少携带 workspace_id、root、local_profile_dir。API 的活动工作库绑定到服务 context，请求不能提交任意绝对路径跳过 root 边界。

## 共用接口

- WorkspaceReader.read_page(page_id) → 当前 PageSnapshot，包括原始解析元数据、正文、content_sha256、可信 storage_area。
- Content.content_sha256(metadata, body) → 内容版本；Content.retrieval_eligibility(metadata, body, area, purpose, expected_content_sha256) → 资格结果。查询传入缓存版本，不能用新批准证明旧片段。
- WorkspaceWriter.apply(operation_id, expected_versions, changes) → MutationResult；必须恢复同一操作，不能生成新操作假装重试。
- IntakeService.prepare(input_ids) → job；只生成来源与稿件，模型无写正式页权限。
- ReviewService.confirm(draft_id, expected_base_sha256, confirmation_id) → 本地 mutation；项目进度和任务 action 单独确认。
- IndexService.plan / run → 范围、费用估计与 job；Provider.embed / rerank 通过独立协议。
- QueryService.stream(request) → 有序事件和最终 Answer / Citation；引用最终使用前重读与复验。
- ExternalActionService.execute(action_id) → pending / succeeded / failed / unknown；未知状态只核实，不再创建。

以上是职责接口；具体 DTO 见 API 契约。FastAPI / Pydantic 模型生成 OpenAPI 和 TypeScript 类型。实现者不能为 API、索引和 UI 各写一份互不一致的 Page 定义。

## 两类存储

工作库：manifest、普通 Markdown、原件、待整理 / 待审业务状态和必要操作结果。普通本地目录可用，OneDrive 是可选存储位置。

本地 profile：macOS Application Support / SummitEverything / workspace_id。SQLite 保存业务状态、索引代指针、会话、角色、记忆、缓存和轮转日志；嵌入式 LanceDB 保存可重建的向量与全文索引。长期凭据存钥匙串，profile 只保存引用。本地 profile 不在工作库里面。

同步区不存运行中的 SQLite / WAL，也不按每次状态变更永久写一份小 JSON。待处理项维护当前状态，完成后按月份汇总；来源记录与外部幂等结果仍可追溯，unknown 项不可清除。

## 模型配置

| 能力 | 默认 |
|---|---|
| 整理、分类、摘要、问答 | deepseek-flash（DeepSeek V4.1 Flash） |
| 嵌入 | qwen3.7-text-embedding，1024 维 |
| 重排 | qwen3.7-text-rerank |

整理、分类和记忆候选抽取关闭思考模式；问答推理预算显式配置，截断要同时检查输出预算耗尽和内容是否为空。失败保留可恢复状态，不伪装成功。

DeepSeek、Qwen embedding 和 Qwen rerank 是独立 provider。Qwen 3.7 重排与旧 qwen3-rerank 端点及响应不可互换；地区、workspace_id、模型、维度形成配置，不能仅改模型字符串。

官方依据：[DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/)、[Qwen embedding](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)、[Qwen rerank](https://help.aliyun.com/zh/model-studio/text-rerank-api)。实施接入时再核对当前官方协议，验证真实账户支持后才进行明确授权的调用。

索引 fingerprint 包含 provider / 模型 / 维度 / 分块与规范化版本。不同 fingerprint 不混用向量；完整重建先写入新的 LanceDB 代，核对行数、模式、维度并建好中文 n-gram BM25 全文索引，再用 SQLite 事务和代号比较交换活动指针。查询固定读取开始时选定的一代；旧代保留供在途查询。未变的嵌入输入复用当前本机代的向量，不同步向量数据库。LanceDB 只执行本地文件模式，不使用云端数据库、模型自动下载或付费 provider。

旧 SQLite `vector_json` 索引不迁移、不读取、不用于检索；状态接口报告需要重建，问答在索引重建前不调用 embedding。用户预览并显式执行一次完整索引后，系统从当前已确认 Markdown 重新生成向量；旧 SQLite chunk 行原样保留但不再作为缓存使用。识别旧格式只读元数据；首次访问不会修改旧索引文件。新 profile 的 SQLite 不创建旧 `chunks/vector_json` 表。旧 LanceDB 代为在途查询保留；应用退出后，可用 `scripts/prune_local_index.py --index-db <profile>/index.sqlite3 --app-stopped` 清理，保留活动代和最近一个旧代。

## 写入与跨机

事务先保存意图与预期版本，临时文件同目录写入、flush / fsync / replace，更新结果后恢复可重入。多文件操作不是天然原子事务，必须有 journal 与恢复顺序。库身份锁防止同机两个进程写同一库。

跨机的同步客户端不是分布式锁。v1 以用户停写、确认 OneDrive 同步完成、另一机再接管为边界；检测冲突副本、重复 ID 或未恢复事务时停止写入相关对象，继续可用的只读功能。

模型中断后的待处理项可在另一机继续查看；不能自动重发未知模型请求或重复外部动作。用户显式重新处理时展示可能新增的调用。

## 构建与维护

使用 uv.lock、前端 lockfile 和可复现打包。只引入本阶段实际需要的依赖；不为换技术而重写已验证算法，也不为复用而搬入旧架构。

M4 强制构建 WebUI 后打包；包内记录应用版本、build、源码提交 / dirty、前端指纹及必要依赖清单。新 bundle / profile 与旧应用隔离；首次交付内部 DMG，不自动覆盖旧安装或发布更新 feed。

## 飞书集成边界

`integrations/feishu/provider.py` 定义配置、凭据接口与 DTO；`fake.py` 提供无网络合成分页、文件和日程；`service.py` 实现本机会话 state、权限门禁、响应验证及选择导入。API 通过 create_app 参数注入 provider/store/config，默认使用 Fake + MemoryCredentialStore。`http.py` 提供独立 Feishu HTTP adapter；真实调用需满足设置、凭据和一次性确认计划边界。

OAuth state 只在本进程内保存，绑定本次服务会话 token 的身份，超时与消费由锁保护。callback 地址精确匹配配置；不为了开发端口重写用户注册地址。凭据不进入工作库或浏览器。SourceStore 的 optional external_identity 在 source record 与可恢复意图中保留，手写输入继续使用原幂等 hash 规则。

材料导入以规范化 ID 集合 hash 认领 journal；独立导入文件锁串行化同库批次，原件写入仍使用 SourceStore 的库身份锁和原子恢复。已保存 source/item 在恢复时按稳定 ID 复用，不再次拉取正文；每项完成结果随后保存，完成 receipt 重放不依赖授权或网络。工作库保留此业务来源 / 意图证据；token 与 OAuth state 均不同步。

凭据与授权边界：应用秘密和 user token 分开储存在 CredentialStore 接口；AppCredentials 使用 SecretStr 并校验配置 app_id。真实模式使用 fail-closed macOS Keychain adapter；真实账户请求及 OS Keychain 拒绝 / 锁定 / 重启生命周期须独立验收。前端保留注册 callback 绝对目的地，直接以无凭据、禁止重定向请求本机固定 callback；API 只为 allowlist Origin 的 callback 提供读取 header（含错误），不为其余业务降低 Bearer 门。

## M2.3 日志、思考与项目概览

日志 / 思考通过同一 PageWriter 保存，页面 ID 由 workspace identity 与 operation ID 稳定派生，writer journal 负责相同意图重放和 payload 冲突保护。AI 辅助只在用户显式点击后调用 FakeLLM，建议留在独立编辑状态；保存仍须显式确认。项目概览沿用项目创建时预分配的 overview_id，仅确认后写入；更新需匹配当前 content hash。目录读取、概览批准和日志保存均不触发项目进度 action。

## 外部请求边界

外部 HTTP 默认通过请求独立 DeadlineTransport：异步可取消 DNS、连接池和 TCP/TLS stream 每次请求独立持有，同步 facade 返回前等待 runner 结束。provider 业务操作租约防止配置重建关闭在途多请求操作；准入/退役同锁。JSON wire 与 identity 响应有界，非 identity 编码拒绝。设计取舍与依赖见 ADR 0007；真实业务能力仍由服务端门禁控制。
