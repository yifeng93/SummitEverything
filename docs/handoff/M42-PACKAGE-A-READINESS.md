# M4.2 真实验收准备卡

本页用于 Developer / 独立 QA 与后续 opt-in 真实验收交接。准备就绪不表示真实业务调用已发生，也不替代用户对材料、发送范围、服务、次数与费用的单独确认。

## 离线开发的已知范围

- 真实模型整理、索引、问答和 Feishu 只读/导入使用本机一次性计划：先展示当前发送范围，由用户独立确认，再执行一次。计划过期、被取消或与配置/来源/页面版本/授权代次不一致时拒绝外发。
- 请求数是有限 HTTP 请求上限，不是金额上限或“模型操作”数量。一次问答上限为 embedding、rerank、answer 各一次；索引上限按每批最多 20 个文本段计算；整理最多一次；飞书导入按保守失败回退上限计算。预留后遇到超时或进程中断保留为 unknown，不能自动重发。
- Provider usage 仅记录响应实际给出的安全 request id 与 token 计数。缺失字段为未知/null；不从调用数推算 token 或用户账单。账单需在 provider 控制台核对。
- 批量导入已实现为单文件接口的顺序复用：选择多个文件或明确选择一个/多个文件夹，最多 100 项 / 100 MB、单个不超过 20 MB，仅 TXT/Markdown；取消选择不写入。失败项单独显示并保留同一 operation_id 重试。隐藏路径、package 内容和 symlink 不作为来源；native 目录遍历上限 2,000 项，无法完整读取时整批拒绝。Developer 在旧 `bc5018d` 候选实际观察过 WKWebView 目录 FileList；固定 `419bb86` 候选新增验证了混选有效/零字节文件时的提示、取消和有效多选导入。Fixed `419bb86` 已由 fresh QA 独立复验本项所列场景；失败项同 operation_id 的真实 UI retry 仍 NOT_RUN。
- Real 模式日志 AI 辅助已接入一次性 plan：正文及输出上限在预览中可读，确认后只组织一次，正文/设置变化、取消、超时和 ledger 状态阻止重发。建议仍为编辑态；写入正式日志仍由独立保存确认触发。Fake 流程保持直接建议。
- 本轮受测的自动/API/Mock 与 corrected packaged UI 场景使用合成文本和隔离 profile/workspace；Real provider 只连 MockHTTP。启动隔离限制见 [Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)：较早 UI run 未前置检查，late CUA 启动在输入前被发现 guard/profile 不符并终止。相关 Keychain 查询次数及 profile 回退 **UNVERIFIED**，不能说整个本轮零查询或全程隔离。不得把离线 adapter 成功写成真实服务验证。

## 工作包 B 授权准备卡

下一步只在用户明确指定 **4 份 Markdown 的完整路径**，并单独授权对这些指定文件做只读事实核对 / grillme 后开始。读取不等于用户批准，不等于初始化正式工作库，也不授权入库或对外发送；只有整组材料得到用户明确批准后，才可初始化正式材料工作库。本轮未读取四份真实业务 Markdown；未主动进行真实 profile 或 Keychain 验收，误启动期间是否访问及影响仍 **UNVERIFIED**。

模型候选为 DeepSeek Flash 与 Qwen 3.7 embedding/rerank，仍需用户选择。任何真实模型动作前，用户需指定模型、实际材料与问题、请求次数上限及费用上限。先核对历史有限 smoke 累计，不随新 profile/workspace 重置；实际执行日重新查官方价格与 usage/账单边界。API key 只能从应用 Settings 的本机安全密钥入口录入，不在聊天中提供。真实 Keychain 生命周期须另行明确授权新命名空间，不读取或迁移旧钥匙串。

首次日常使用的产品预期是：在本机首次配置模型 API key 并点击飞书授权；普通使用不应每次重新填写。2026-10-14 Explorer 对当前设置 UI、验证器和授权实现作了只读审计：启动 mode/provider 默认为 Fake；Real 模型选择为 DeepSeek Flash + Qwen 3.7 embedding/rerank，共两个 key（DeepSeek key 与 DashScope key，后者供 Qwen embedding/rerank 共用）。Embedding 维度 1024、地区 cn 固定，不需要用户填写。现有通用 DashScope endpoints 是否适配该真实账户/Workspace **UNVERIFIED**；应提供本人的 WorkspaceId 或完整 endpoint URLs。UI 中 account label `default` 仅为凭据槽标记，不表示 Workspace。

Feishu 初次配置需要 App ID 与 AppSecret；只在本机安全设置录入 secret。应在飞书应用注册原生有效回调 `http://127.0.0.1:18793/api/v1/integrations/feishu/callback`；界面文案中 `http://127.0.0.1:5173` 只是开发示例，不可用于用户应用注册。点击 OAuth 会发起授权并打开网页登录同意相应 scope。已实现的设计是 token 按同一 profile / app_id 存入本地 vault 并复用；refresh 先持久化 consumed 状态，再发送 HTTP。此描述来自只读代码审计，不是实际 OAuth、账户 scope、OS Keychain 或 refresh 生命周期的验收结果；这些仍 **NOT_RUN**，此前启动隔离观察仍按上文标记 **UNVERIFIED**。

同一工作库的本机 JSON 配置与 Keychain secret 槽旨在避免日常重复配置，但不能保证 Real 模式已经通过，也不能假设所有 workspace 共用 keys。Sol 已单独向用户询问非秘密的 WorkspaceId 或完整 endpoint URLs 与 Feishu AppID；secret 绝不通过聊天收集或打进安装包。当前没有真实授权 scope、连接账户或读取/迁移旧凭据。

Feishu 只读前须由用户确认精确搜索词、选中结果、日期范围及时区，并将读取范围限定为任务第一页。任务写继续 disabled，任何未来启用或写操作都需独立批准。完成产品规定的 12 步，并由用户明确确认开始五个实际工作日验收后，才能启动现场阶段。当前均未获授权。

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
