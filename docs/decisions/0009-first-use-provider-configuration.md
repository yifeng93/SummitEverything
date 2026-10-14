# ADR 0009：首次配置目标与本机 provider 凭据

日期：2026-10-14。状态：Accepted（记录产品目标与当前实现差距；不授权真实连接）。

## 背景

用户希望正常使用前只进行一次简明初配：选择并配置模型、在飞书完成授权，此后同一工作库的日常使用不应反复填写配置。2026-10-14 对当前设置、配置验证和 Feishu OAuth 实现做了只读代码审计。用户随后提供了所选模型、非秘密 WorkspaceId、两个 Base URL、Feishu AppID，以及遮罩占位 secret（`***`，不是实际凭据）。为保护账户信息，本 ADR 不记录具体 ID 或 URL；遮罩文本未录入或保存。没有读取真实 profile/Keychain或执行真实 provider、OAuth、scope、token 生命周期验收；此前误启动期间是否访问 profile/Keychain 及影响仍 UNVERIFIED。

## 决议

- 当前默认 mode/provider 为 Fake。用户已选择 Real 模型为 DeepSeek Flash、Qwen 3.7 embedding 与 Qwen 3.7 rerank：DeepSeek 一把 key，DashScope 一把 key 供 Qwen 两项共用。embedding 维度 1024、地区 cn 固定，不需用户填写。DeepSeek adapter 固定调用 OpenAI-compatible chat completions (`/chat/completions`) 与 `deepseek-flash`，不需要 Anthropic URL；见[DeepSeek 官方 Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/)与[实现](../../src/summit_everything/integrations/llm.py)。
- 用户已提供非秘密 WorkspaceId 与两个 Base URL，但其实际账户可用性及 live connectivity 仍 UNVERIFIED，具体标识和地址不进入文档。offline_guard 下只实例化设置模型时，Embedding `/compatible-mode/v1` 与 Rerank `/api/v1` Base URL path 通过 validator；完整 rerank target 填入设置字段会被拒绝。Rerank adapter 会在 base 后追加 `/services/rerank/text-rerank/text-rerank`。设置中的 `default` 是凭据槽标签，不是 Workspace ID。参见[配置校验](../../src/summit_everything/integrations/settings.py)、[Embedding](../../src/summit_everything/integrations/embedding.py)、[Rerank](../../src/summit_everything/integrations/rerank.py)、[百炼官方 embedding API](https://help.aliyun.com/en/model-studio/text-embedding-synchronous-api)与[Text Rerank API](https://docs.bailian.console.aliyun.com/en/model-studio/text-rerank-api)。
- Feishu 初配需 AppID 与 AppSecret。用户已提供非秘密 AppID，但本文不记录具体值；聊天中的 `***` 是遮罩文本而非真实 AppSecret。保留当前已登记的旧本机 callback，不由本轮替换；如需原生登录，应由用户在后台手工新增 callback `http://127.0.0.1:18793/api/v1/integrations/feishu/callback`。offline_guard 下只实例化配置模型时 native callback 字段通过校验，配置未保存。设置中的 `http://127.0.0.1:5173` 是开发示例，不能作为用户应用 callback。没有操作飞书后台。用户点击授权后才发起 OAuth 并打开网页登录同意 scope。
- 设计目标是配置 JSON 与 secret vault 在同一 profile / app_id 下保存与复用，refresh 状态先持久化再发 HTTP，以免同一工作库日常重复初配；这不承诺跨 workspace 共享 keys，也不代表真实 token/Keychain/OAuth 生命周期已通过。
- API secrets 只由用户在应用的本机安全设置入口输入，不收集在聊天中、不打入安装包。当前不读取或迁移既有钥匙串凭据。

## 当前未决事项与边界

非秘密 WorkspaceId、两个百炼 Base URL 与 Feishu AppID 已由用户提供，本文及其他 tracked 文档不复述具体值。实际账户可用性、OAuth、scope/grant 兼容性、callback、token refresh、vault 与 macOS Keychain 生命周期均 NOT_RUN/UNVERIFIED。当前 user scope 请求与用户报告的后台列表差异见 [M42 readiness](../handoff/M42-PACKAGE-A-READINESS.md)；尚未 live 核对，tenant grant 不等于 user grant，旧权限名不视为当前 scope 等价。当前仍请求 `task:task:write`，但真实任务写继续禁用；不要盲目添加权限。调整请求 scope 属于需新固定 SHA 与 fresh QA 的产品变更。要进行工作包 B，仍需用户指定四份 Markdown 的完整路径并单独授权只读核对；真实模型动作、发送内容、问题、次数与费用上限、Feishu 搜索词/结果/日期范围均需分别明确。四份材料整体获批前不得初始化正式材料工作库。

本记录源于用户 2026-10-14 配置目标澄清与只读代码审计，不改变产品实现，也不扩大当前真实外部操作授权。实施状态与逐项限制见 [M42 readiness](../handoff/M42-PACKAGE-A-READINESS.md) 和 [offline closeout](../quality/reports/2026-10-14-M42-OFFLINE-CLOSEOUT.md)。
