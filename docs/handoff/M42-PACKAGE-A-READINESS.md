# M4.2 真实验收准备卡

本页用于 Developer / 独立 QA 与后续 opt-in 真实验收交接。工作包 A fixed `419bb86` 已经 fresh QA 并合入 main；PR #18 的离线 CI run 38550700081 全步骤成功。内部候选交付于 `/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/m42-419bb86/`：`SummitEverything Internal 419bb86.app` 与 `SummitEverything-Internal-419bb86.dmg`，DMG SHA-256 `2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`。候选仅供已授权的内部验证，不表示用户安装、公证或全产品验收通过。合并/CI范围与保留状态见[离线收口记录](../quality/reports/2026-10-14-M42-OFFLINE-CLOSEOUT.md)。准备就绪不表示真实业务调用已发生，也不替代用户对材料、发送范围、服务、次数与费用的单独确认。

## 离线开发的已知范围

- 真实模型整理、索引、问答和 Feishu 只读/导入使用本机一次性计划：先展示当前发送范围，由用户独立确认，再执行一次。计划过期、被取消或与配置/来源/页面版本/授权代次不一致时拒绝外发。
- 请求数是有限 HTTP 请求上限，不是金额上限或“模型操作”数量。一次问答上限为 embedding、rerank、answer 各一次；索引上限按每批最多 20 个文本段计算；整理最多一次；飞书导入按保守失败回退上限计算。预留后遇到超时或进程中断保留为 unknown，不能自动重发。
- Provider usage 仅记录响应实际给出的安全 request id 与 token 计数。缺失字段为未知/null；不从调用数推算 token 或用户账单。账单需在 provider 控制台核对。
- 批量导入已实现为单文件接口的顺序复用：选择多个文件或明确选择一个/多个文件夹，最多 100 项 / 100 MB、单个不超过 20 MB，仅 TXT/Markdown；取消选择不写入。失败项单独显示并保留同一 operation_id 重试。隐藏路径、package 内容和 symlink 不作为来源；native 目录遍历上限 2,000 项，无法完整读取时整批拒绝。Developer 在旧 `bc5018d` 候选实际观察过 WKWebView 目录 FileList；固定 `419bb86` 候选新增验证了混选有效/零字节文件时的提示、取消和有效多选导入。Fixed `419bb86` 已由 fresh QA 独立复验本项所列场景；失败项同 operation_id 的真实 UI retry 仍 NOT_RUN。
- Real 模式日志 AI 辅助已接入一次性 plan：正文及输出上限在预览中可读，确认后只组织一次，正文/设置变化、取消、超时和 ledger 状态阻止重发。建议仍为编辑态；写入正式日志仍由独立保存确认触发。Fake 流程保持直接建议。
- 本轮受测的自动/API/Mock 与 corrected packaged UI 场景使用合成文本和隔离 profile/workspace；Real provider 只连 MockHTTP。启动隔离限制见 [Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)：较早 UI run 未前置检查，late CUA 启动在输入前被发现 guard/profile 不符并终止。相关 Keychain 查询次数及 profile 回退 **UNVERIFIED**，不能说整个本轮零查询或全程隔离。不得把离线 adapter 成功写成真实服务验证。

## 工作包 B 授权准备卡

下一步只在用户明确指定 **4 份 Markdown 的完整路径**，并单独授权对这些指定文件做只读事实核对 / grillme 后开始。读取不等于用户批准，不等于初始化正式工作库，也不授权入库或对外发送；只有整组材料得到用户明确批准后，才可初始化正式材料工作库。本轮未读取四份真实业务 Markdown；未主动进行真实 profile 或 Keychain 验收，误启动期间是否访问及影响仍 **UNVERIFIED**。

用户已选定 DeepSeek Flash、Qwen 3.7 embedding 与 Qwen 3.7 rerank。设置中 DeepSeek 使用一把 key；DashScope key 供 Qwen embedding/rerank 共用。当前设置标签为 `DeepSeek API Key`、`阿里云 Model Studio API Key` 与 `飞书应用密钥`。用户已提供非秘密 WorkspaceId、两个百炼 Base URL 与 Feishu AppID；为避免把账户标识和地址写入仓库，此处不记录具体值。本机忽略文件 `.local/first-use/SETUP.md` 保存了供本机恢复使用的配置指引，不纳入 Git，也不含 API key 或 AppSecret。非秘密接入值的注入来源是同目录的 `.local/first-use/defaults.json`，只允许 `feishu_app_id`、`feishu_redirect_uri`、`embedding_base_url`、`rerank_base_url` 四个键；出现 secret 形态键名（`/secret|key|token|password|credential/i`）或未知键时加载 fail closed。此前提供的 API key 仅为 `***` 遮罩占位，不是真实凭据，未录入或保存。提供非秘密字段不授权连接、付费调用或发送资料。实际调用仍须先核对历史 smoke 累计（不随新 profile/workspace 重置）、执行日官方价格与用量边界，并逐次明确材料/问题、请求次数和费用上限。真实 Keychain 生命周期另需明确授权新命名空间，不读取或迁移旧钥匙串。

首次日常使用的产品预期是：在本机首次配置模型 API key 并点击飞书授权；普通使用不应每次重新填写。2026-10-14 Explorer 对当前设置 UI、验证器和授权实现作了只读审计：启动 mode/provider 默认为 Fake；用户选择 DeepSeek Flash、Qwen 3.7 embedding、Qwen 3.7 rerank，共两个模型服务 key（DeepSeek key 与 DashScope key，后者供 Qwen 两项共用）。Embedding 维度 1024、地区 cn 固定，不需要用户填写。用户已提供非秘密 WorkspaceId 与两项 Base URL；具体值不进入仓库。UI 中 account label `default` 仅为凭据槽标记，不表示 Workspace，且不能用于推断 Workspace。offline_guard 下只实例化配置模型时，Embedding Base URL path `/compatible-mode/v1` 与 Rerank API Base URL path `/api/v1` 均通过 validator；完整 rerank URL 填入 Base URL 会触发 `ValidationError`。设置框应分别填写 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` 与 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1`；这条手填要求在 `codex/settings-ux-20261014` 分支被 [ADR 0010](../decisions/0010-first-use-configuration-ux.md) 取代：非秘密接入值由 Git 忽略的本机文件 `.local/first-use/defaults.json` 在构建时注入 App bundle 的 `Resources/first-use-defaults.json`，设置页只在「高级与自定义」保留覆盖入口，采用官方推荐的业务空间专属域名（依据[百炼地域及接入域名](https://help.aliyun.com/zh/model-studio/beijing-access-information)）；该注入路径的打包级验证在分支收口时单独记录，未验证前不得当作已通过。实现会在 rerank base 后追加 `/services/rerank/text-rerank/text-rerank`，完整 endpoint 不能直接粘贴进设置框。参考[配置校验](../../src/summit_everything/integrations/settings.py)、[embedding adapter](../../src/summit_everything/integrations/embedding.py)及[rerank adapter](../../src/summit_everything/integrations/rerank.py)，[百炼官方 embedding API](https://help.aliyun.com/en/model-studio/text-embedding-synchronous-api)与[Text Rerank API](https://docs.bailian.console.aliyun.com/en/model-studio/text-rerank-api)。DeepSeek adapter 固定使用 OpenAI 兼容的 chat completions endpoint 与 `deepseek-flash`，不需要 Anthropic URL；见[实现](../../src/summit_everything/integrations/llm.py)和[DeepSeek 官方 API](https://api-docs.deepseek.com/api/create-chat-completion/)。这些核对不证明真实账户可用或已连接。

Feishu 初次配置需要 App ID 与 AppSecret；只在本机安全设置录入真实 secret。用户报告已提供非秘密 AppID，遮罩文本 `***` 不是真实 AppSecret。保留当前已登记的旧本机 callback，不在本轮替换；另一个应由用户在飞书应用后台手工新增的原生 callback 是 `http://127.0.0.1:18793/api/v1/integrations/feishu/callback`。offline_guard 下只实例化配置模型时，native callback 配置字段通过校验；未保存该配置。设置文案中的 `http://127.0.0.1:5173` 是开发示例，不用于原生应用注册。没有操作飞书后台。点击 OAuth 才会发起授权并打开网页登录同意所请求的 scope。已实现的设计是 token 按同一 profile / app_id 存入本地 vault 并复用；refresh 先持久化 consumed 状态，再发送 HTTP。此描述来自只读代码审计，不是实际 OAuth、账户 scope、OS Keychain 或 refresh 生命周期的验收结果；这些仍 **NOT_RUN**，此前启动隔离观察仍按上文标记 **UNVERIFIED**。

同一工作库的本机 JSON 配置与 Keychain secret 槽旨在避免日常重复配置，但不能保证 Real 模式已经通过，也不能假设所有 workspace 共用 keys。用户已提供非秘密 WorkspaceId、两个百炼 Base URL 与 Feishu AppID；具体值不进入 tracked 文档。真实 API secrets 仍只允许用户通过本机安全入口录入，聊天中的 `***` 是遮罩占位，不是真密钥。当前未做 live scope/grant 核验、未连接账户，也未读取或迁移旧凭据。

Feishu 只读前须由用户确认精确搜索词、选中结果、日期范围及时区，并将读取范围限定为任务第一页。任务写继续 disabled，任何未来启用或写操作都需独立批准。完成产品规定的 12 步，并由用户明确确认开始五个实际工作日验收后，才能启动现场阶段。当前均未获授权。

## Feishu scope 与用户报告的权限

当前代码的 `FeishuConfig.user_scopes` 发起用户 OAuth 时请求：`offline_access`、`minutes:minutes.search:read`、`minutes:minutes.transcript:export`、`minutes:minutes.artifacts:read`、`calendar:calendar.event:read`、`task:task:read`、`task:task:write`。这是代码请求列表，不是已获授权的 grant。用户报告管理后台 tenant 范围显示分钟细粒度、calendar event read 与 task read/write，而 user scope 列表显示较早的粗粒度 minutes、calendar readonly、task:task/offline_access 等权限；该描述只是用户提供的控制台信息，本轮没有登录或读取权限页面，不能当作 live 证据。代码当前请求的六个细粒度 scope 名未出现在用户提供的 user-scope 列表中；这只描述名称差异，不判定权限不足、无效或等价。Tenant 权限不自动覆盖 user grant；旧粗粒度权限与当前细粒度 scope 的兼容关系尚未核验，管理员侧配置也不证明用户已同意授权。当前配置仍请求 task write，但真实 Feishu 任务写继续禁用。不要为排障盲目增加权限；若后续要收窄 OAuth scope，应作为独立产品改动固定新 SHA 并 fresh QA。Feishu 官方权限页本轮未取得可核实内容，因此不对权限映射作官方结论。

## 真实使用前需逐项独立准备

1. 确认选定资料已由用户批准，并在专用、隔离的工作库中是当前正式版本。待审稿、原件、收件箱状态不进入索引依据。
2. 仅在上述单独授权后，使用当前服务端 Real 配置和用户选定模型；secret 通过应用 Settings 本机安全入口保存。打开设置页和状态页本身不发出 provider 请求。offline guard 下 Keychain 被禁用；不得用合成凭据或 DEV 参数替代真实用户授权。
3. 每次动作预览中检查：实际问题与完整上下文（历史用户问题、角色、已确认记忆）、合格页面标题/版本、待整理来源全文、或 Feishu 精确筛选与选中项。只确认本次范围；发生修改须创建新计划。
4. 确认后查看本地状态和 provider 账单；unknown 不重试。Feishu 任务创建/编辑/完成因缺少独立结果证明能力仍禁用。
5. 质量验收必须由用户对实际资料与答案评定。以下是合成 golden 场景模板，不是正式事实或真实样例；用户应按实际页面填写事实依据并裁定答案：

| 场景 | 黄金问题 | 可接受事实依据 | 禁止的结论 | 用户裁定 |
|---|---|---|---|---|
| 报价与合同 | 测试会场 A 的报价、签约和批准状态分别是什么？ | 分开引用报价、签约状态与批准状态的当前页面/版本 | 把报价说成已签约或已批准 | 真实验收时填写 |
| 未决间夜 | 当前住宿总价是多少，哪些费用还未确定？ | 区分已定价格、未确认的间夜/费用及其对应范围 | 把未决间夜当成零元或并入确定总价 | 真实验收时填写 |
| 指定范围平均值 | 已确认的 6000 与 9000 两项在 30 晚范围内平均每晚是多少？ | 明确这两项各自范围和公式 `(6000+9000)/30=500` | 把 500 扩展到范围外晚数或当作全程最终价 | 真实验收时填写 |
| 单晚价格比较 | 每晚单价从 200 降到 180，变化比例是多少？ | 比较同一“每晚单价”口径：下降 10% | 推断总住宿成本也下降 10%，或忽略晚数/其他费用 | 真实验收时填写 |
| 方案与任务 | 这份工作方案已批准并成为正式任务了吗？ | 查方案状态与独立任务事实/批准记录 | 把模型建议或方案正文说成已批准任务 | 真实验收时填写 |

## 费用核对参考（官方页面，2026-10-13）

当日公开价用于测试前估算，不构成消费预算。DeepSeek Flash 每百万未命中输入 token 高峰 ¥2、闲时 ¥1，输出 token 高峰 ¥8、闲时 ¥4；Qwen embedding 与 rerank 各为每百万输入 token ¥0.5。真实执行日须再次核对官方价格、缓存/时段规则和账单。估算应分别按 provider 的实际 token usage、输入/输出类别与当日单价计算；没有 token usage 时显示未知，不填零。真实账单金额未知，必须在 provider 侧核对。

- [DeepSeek 官方中文价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)
- [阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing)
- [阿里云百炼文本 embedding API](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)

Model Studio workspace endpoint 应由用户显式配置。用户可以给出自己的 WorkspaceId，或直接确认完整 endpoint URLs：Qwen embedding 使用 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`；rerank 使用 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`。不得把 account label `default` 当 WorkspaceId，也不得推断其真实账户可用；不从账户名自动猜测或覆盖 workspace endpoint。

## 当前已知产品差距

- fixed `419bb86` corrected packaged UI 与独立 QA 已实际验证多选、混选拒绝提示、取消、目录 FileList 和 Fake Journal 生命周期。部分成功后失败项的真实 UI 同 operation ID retry，以及 Real JournalAssist packaged UI 仍 NOT_RUN；Runtime + MockHTTP 的 API 集成已验，不代表真实 provider。
- Provider 真实内容质量、端到端账单，Feishu OAuth / 账号 scope、OS Keychain 生命周期、正式用户安装/覆盖、五日体验、双机、公证与发布仍 NOT_RUN。Runtime 实际模型元数据 UNVERIFIED；启动隔离与 Keychain 查询次数限制见上文及 Sol gate。

## 五个实际工作日记录

只能在完整真实闭环获准后填写；目前有意保持为空。C28 模板位于[验收矩阵](../quality/ACCEPTANCE.md#c28-五个实际工作日记录模板)。

| 实际日期 | 使用场景/范围 | 已知缺陷及级别 | 用户观察/决定 | 证据链接 |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
