export function buildFeishuAgentSetupPrompt(origin: string): string {
  let safeOrigin = ''
  try {
    const parsed = new URL(origin)
    safeOrigin = parsed.origin
  } catch {
    safeOrigin = '当前 SummitEverything 页面'
  }

  return `请在本机为 SummitEverything 自动检查并完成可安全完成的飞书接入配置。当前应用网页 origin：${safeOrigin}

先阅读并遵循本机项目中的 docs/handoff/FEISHU-AGENT-SETUP.md、docs/contracts/MCP-v1.md、docs/contracts/API-v1.md、README.md 中 Agent 接入说明，以及相关飞书接入文档和现有技能。使用本机上下文定位当前 SummitEverything 项目、服务和工作库；工作库身份如能安全取得可用于核对，但不得复制或输出 token、密钥、凭据内容、授权码或带敏感参数的 URL。凭据只可经受支持的本机安全通道提交到应用正式凭据接口。

执行顺序：
1. 发现当前助手宿主实际支持的 MCP 配置、飞书工具/连接器和本机 CLI/技能；检查现有 SummitEverything MCP 配置和状态，并优先复用已经存在的飞书授权与配置。不要覆盖无关配置，不要重复授权。
2. 核对 SummitEverything MCP 契约、服务器可用性和工作库身份。MCP 工具可读性与飞书外部连接是不同验证门；逐项说明已有证据和缺口。
3. 当前 SummitEverything MCP 只提供 14 个工具，没有设置飞书凭据的工具，也没有飞书 CLI bridge。MCP 之外，核实 API-v1 的 GET/PATCH /settings 与 PUT /credentials/{provider}、当前服务适配及宿主安全凭据来源；有受支持且获准的安全路径时继续配置，不得因 MCP 缺少工具就直接停止。不要把 CLI 可运行、配置文件存在或工具列表出现说成 SummitEverything 已连通。
4. 只从现有钥匙串/宿主秘密管理取得凭据，并经受支持的本机安全通道提交到正式凭据接口；不得把秘密输出到对话、终端、日志、提示词、仓库或普通配置。不要求用户把密钥复制到聊天；不得猜测路径或生成/覆盖 token 文件。若确实缺少安全凭据来源或支持接口，报告缺口和最小下一步。
5. 若官方授权必须由用户扫码/确认，先完成其余安全配置，再只要求用户完成该最小动作；已有有效的一次性计划可按其绑定范围继续，不额外要求重复确认。分别验证外部飞书连接，以及 SummitEverything 应用确实通过其受支持集成读到指定的无敏感信息。不要创建任务、导入或确认正式知识。

本提示词只授权检查和配置接入，不授权真实飞书任务写入、正式知识确认、付费模型调用、超出已有一次性计划的真实请求或绕过项目中既有授权门。任何外部读请求先核实现有计划/授权要求。收尾报告：实际配置了什么、复用了什么、分别通过了哪些验证、哪些仍未验证、需要用户做的最小动作；不输出任何秘密。`
}
