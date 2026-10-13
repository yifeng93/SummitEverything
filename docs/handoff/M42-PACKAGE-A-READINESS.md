# M4.2 真实验收准备卡

本页用于 Developer / 独立 QA 与后续 opt-in 真实验收交接。准备就绪不表示真实业务调用已发生，也不替代用户对材料、发送范围、服务、次数与费用的单独确认。

## 离线开发的已知范围

- 真实模型整理、索引、问答和 Feishu 只读/导入使用本机一次性计划：先展示当前发送范围，由用户独立确认，再执行一次。计划过期、被取消或与配置/来源/页面版本/授权代次不一致时拒绝外发。
- 请求数是有限 HTTP 请求上限，不是金额上限或“模型操作”数量。一次问答上限为 embedding、rerank、answer 各一次；索引上限按每批最多 20 个文本段计算；整理最多一次；飞书导入按保守失败回退上限计算。预留后遇到超时或进程中断保留为 unknown，不能自动重发。
- Provider usage 仅记录响应实际给出的安全 request id 与 token 计数。缺失字段为未知/null；不从调用数推算 token 或用户账单。账单需在 provider 控制台核对。
- 本轮实现及测试仅使用合成文本、隔离 profile/workspace、Fake/Mock HTTP。不得把离线 adapter 成功写成真实服务验证。

## 真实使用前需逐项独立准备

1. 确认选定资料已由用户批准，并在专用、隔离的工作库中是当前正式版本。待审稿、原件、收件箱状态不进入索引依据。
2. 设置当前服务端 Real 配置及用户明确选择的模型，然后保存 secret 到系统 Keychain。打开设置页和状态页本身不发出 provider 请求。M4.2 候选的 offline guard 会禁用 Keychain；不得用合成凭据或 DEV 参数替代真实用户授权。
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

Model Studio workspace endpoint 应由用户显式配置。Qwen embedding 使用 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`；rerank 使用 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`。不从账户名自动猜测或覆盖 workspace endpoint。

## 当前已知产品差距

- Today 原生选择器一次只选一个文件；已确认的批量文件/文件夹导入需求仍待实现，不得宣称包 A 支持。
- 真实模式 journal assist 尚无一次性计划及相应发送/费用回执闭环；本轮不把它描述为已受控的真实模型动作。
- 真实 Feishu OAuth / 账号 scope、provider 质量与账单、系统 Keychain 生命周期、实际用户安装、五日体验、双机、公证与发布均 NOT_RUN。Runtime 实际模型元数据 UNVERIFIED。

## 五个实际工作日记录

只能在完整真实闭环获准后填写；目前有意保持为空。C28 模板位于[验收矩阵](../quality/ACCEPTANCE.md#c28-五个实际工作日记录模板)。

| 实际日期 | 使用场景/范围 | 已知缺陷及级别 | 用户观察/决定 | 证据链接 |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
