# SWB / SK 复用地图与来源基线

核对日期：2026-10-09。代码路径按各表的根目录说明解析；行号可能变化，按完整提交和符号查证。

| 项目 | 本机参考目录 | 核对提交 |
|---|---|---|
| SummitWorkbench | /Users/yifengstudio/Documents/GitHub/SummitWorkbench | f9e94392c11c8ff222ef9ad51d9acc07e499659b |
| SummitKnowledge | /Users/yifengstudio/Documents/GitHub/SummitKnowledge | 650ae60d9323ab1209e2fd56973c3a792a517bb3 |
| SummitEverything 初始仓库 | 本仓库 | 25277f7b65e9176ef9f46a101e01e43217250a6d |

上述是本次读取的 HEAD，不能称作旧应用当前安装包或发布源码身份。旧仓库不可写，旧 venv 不用本项目 uv sync。

## 关系

SWB 原来负责写入，SK 原来负责检索，另有工作库规则；新产品把这些边界统一在一个服务和一份工作库契约中。

旧仓库是能力与事故经验来源，不是新产品的规则真源。运行时不通过 sys.path 导入旧目录、不要求旧 App 同时启动、不共享旧数据库。移植小模块和相关行为测试，适配新 DTO、storage context 与统一资格函数后再使用。

## SWB

下表 Python 模块以 src/summit_workbench/ 为根；native 路径以旧仓库根目录为根。

| 参考模块 | 可吸收内容 | 必须改变 / 避免 |
|---|---|---|
| domain/approval.py | 版本批准和 canonical hash 的思路 | 不复制旧 type / status / workstream 白名单、元数据挑选集合或旧项目豁免 |
| repositories/workspace_manifest.py；domain/workspace.py | 库身份、路径不作为身份、本地 profile | 新 manifest namespace 和 schema，避免旧 App 误识别新库 |
| workflows/local_mutation.py；repositories/local_mutation_journal.py | 原子写盘、事务恢复、changed paths | 移除所有 legacy Git / 自动 push 关联 |
| repositories/external_action_outbox.py | 稳定意图、幂等、结果未知处理 | API v1 action 状态；执行与批准分开，跨机 receipt 可追溯 |
| providers/feishu/{auth,session,client,calendar,tasks,meetings,config}.py | OAuth 刷新、日历 / 任务、错误分类、会议内容 | 原会议号发现不能当作完整妙记列表；按官方新接口扩展，验证 scope / 可见性 |
| repositories/thought_notes.py；webapp/routers/journal.py | 日志和思考写入经验 | 不继承固定五区块 / 三必填段或 legacy 页面类型；直接保存也需新证明 |
| repositories/writeback.py | 固定区块插入的空行教训 | 新正文自由；有插入需要时保持空行、幂等和完整路径记录 |
| native/SummitWorkbench/{ServiceSupervisor,PanelWindowController}.swift | 后端生命周期、WKWebView、文件选择 | 新应用身份、凭据桥接、会话认证；不搬入旧功能菜单和自动化守护全套 |

## SK

| 参考模块 / 符号 | 可吸收内容 | 必须改变 / 避免 |
|---|---|---|
| markdown_chunking.py::chunk_work_markdown | Markdown 分块、长块处理 | 不把旧标题结构作为新强制模板；引用用 page_id + version + chunk_id |
| vector_store_sqlite.py::VectorStore | 本地 SQLite / NumPy、索引代切换、文件增量与关键词信息 | source_file 不是业务身份；按 workspace_id、page_id 和 model fingerprint 组织 |
| retriever.py::Retriever | 向量 + 关键词 RRF、候选重排、邻页 | 重写旧项目 / 权威权重与白名单；每条候选、邻页、引用都检查当前证明 |
| reranker.py::rerank_documents | 重排调用、错误传播 | Qwen 3.7 的新协议单独实现，不沿用旧请求 / 响应 |
| citations.py | 来源标识和打开体验 | 路径派生 ID 替换为稳定 ID；引用绑定内容版本，不靠唯一文件名猜测 |
| query_router.py；query_planner.py | 元数据广度、语义深度、多材料查询 | 去掉固定个人 / 工作分类和旧目录词；只做 work profile |
| session_context.py | 上下文预算、长历史压缩 | 本机、每工作库隔离；避免不同 workspace 串话 |
| user_memory.py | 本地记忆存取与 prompt 格式 | 候选 / 确认两层；不能从 assistant 回答直接抽成可信记忆 |
| SummitKnowledgeApp/Sources/SummitKnowledge/{RoleStore,ConversationStore}.swift | 角色、历史与交互经验 | 重做 WebUI；不并行保留 SwiftUI 聊天产品 |

server.py / Flask 整体不迁入新运行时。retrieval_policy.py 的旧目录、type 和 status 判定被新统一信任函数替代。

## 飞书已核实的官方入口

官方 SDK 包含 POST /open-apis/minutes/v1/minutes/search 和 GET /open-apis/minutes/v1/minutes/:minute_token/transcript，支持用户 / 租户 token。逐字稿响应是文件内容，不能假定为 JSON 的 text 字段。

依据：[搜索请求](https://raw.githubusercontent.com/larksuite/oapi-sdk-python/v2_main/lark_oapi/api/minutes/v1/model/search_minute_request.py)、[逐字稿请求](https://raw.githubusercontent.com/larksuite/oapi-sdk-python/v2_main/lark_oapi/api/minutes/v1/model/get_minute_transcript_request.py)、[逐字稿资源实现](https://raw.githubusercontent.com/larksuite/oapi-sdk-python/v2_main/lark_oapi/api/minutes/v1/resource/minute_transcript.py)。

SDK 存在接口不证明本人账号已有权限；M2 在真实授权准备好时验证材料发现、分页和正文读取。用户愿意配置必要权限，缺失时显示具体设置指引，手动文字入口仍可工作。

## 移植记录要求

执行者在任务交接中记录：旧仓库提交、模块 / 符号、吸收的行为、修改的假设、新测试和依赖变化。先读真实代码，不凭旧 README 数字宣布兼容；原测试迁移后要证明检验的是新调用边界。

禁止直接复制真实知识内容、Keychain 值、默认飞书凭据、旧包内密钥或模型 API key 到本仓库。第三方许可和打包清单在 M4 核对，不照抄旧 SBOM 当新产物证据。
