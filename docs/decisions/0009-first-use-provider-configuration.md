# ADR 0009：首次配置目标与本机 provider 凭据

日期：2026-10-14。状态：Accepted（记录产品目标与当前实现差距；不授权真实连接）。

## 背景

用户希望正常使用前只进行一次简明初配：选择并配置模型、在飞书完成授权，此后同一工作库的日常使用不应反复填写配置。2026-10-14 对当前设置、配置验证和 Feishu OAuth 实现做了只读代码审计，以明确真实账户首次使用前还需要哪些非秘密信息。此次审计没有读取真实 profile 或 Keychain，也没有执行真实 provider、OAuth、scope 或 token 生命周期验收；此前误启动期间是否访问 profile/Keychain 及影响仍 UNVERIFIED。

## 决议

- 当前默认 mode/provider 为 Fake。用户设定的 Real 模型目标是 DeepSeek Flash 与 Qwen 3.7 embedding/rerank：DeepSeek 一把 key，DashScope 一把 key 供 Qwen embedding 和 rerank 共用。embedding 维度 1024、地区 cn 固定，不需用户填写。
- DashScope 通用 endpoints 是否适用于实际账户仍 UNVERIFIED。首次真实配置需用户自己的 WorkspaceId 或确认完整 embedding/rerank endpoint URLs；设置中的 `default` 是凭据槽标签，不是 Workspace ID。
- Feishu 初配需 AppID 与 AppSecret，在飞书应用中注册 native callback `http://127.0.0.1:18793/api/v1/integrations/feishu/callback`。设置中的 `http://127.0.0.1:5173` 是开发示例，不能作为用户应用 callback。用户点击授权后才发起 OAuth 并打开网页登录同意 scope。
- 设计目标是配置 JSON 与 secret vault 在同一 profile / app_id 下保存与复用，refresh 状态先持久化再发 HTTP，以免同一工作库日常重复初配；这不承诺跨 workspace 共享 keys，也不代表真实 token/Keychain/OAuth 生命周期已通过。
- API secrets 只由用户在应用的本机安全设置入口输入，不收集在聊天中、不打入安装包。当前不读取或迁移既有钥匙串凭据。

## 当前未决事项与边界

用户尚未提供非秘密的实际 WorkspaceId 或完整 endpoints、Feishu AppID；实际账户可用性、OAuth、scope、callback、token refresh、vault 与 macOS Keychain 生命周期均 NOT_RUN/UNVERIFIED。要进行工作包 B，仍需用户指定四份 Markdown 的完整路径并单独授权只读核对；真实模型动作、发送内容、问题、次数与费用上限、Feishu 搜索词/结果/日期范围均需分别明确。四份材料整体获批前不得初始化正式材料工作库。

本记录源于用户 2026-10-14 配置目标澄清与只读代码审计，不改变产品实现，也不扩大当前真实外部操作授权。实施状态与逐项限制见 [M42 readiness](../handoff/M42-PACKAGE-A-READINESS.md) 和 [offline closeout](../quality/reports/2026-10-14-M42-OFFLINE-CLOSEOUT.md)。
