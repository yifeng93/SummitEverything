# ADR 0010：首次配置界面形态与非秘密接入信息内置

日期：2026-10-14。状态：Accepted（记录用户在本分支确认的界面与打包决议；不授权真实连接、不改变 Fake 默认）。

## 背景

用户以旧项目 SummitWorkbench 的配置页为目标形态：设置主区只有少量卡片、每张卡带状态徽章、能少填就少填、保存后立刻给出连接结论、并提供可续的分步向导。参考实现位于本机只读 checkout `/Users/yifengstudio/Documents/GitHub/SummitWorkbench`（`f9e9439`）：`web/src/features/settings/render.ts` 的三卡布局与保存后验证、`src/summit_workbench/webapp/onboarding_view.py` 的可续向导（凭据明确不进草稿）。

用户同时要求：Base URL、飞书 callback、Feishu App ID 这类**非秘密**接入信息不要在设置界面里让用户手填，应提前封装；配置时只需输入保密密钥。用户曾提出把 Feishu AppSecret 也封装进安装包，经说明「DMG 内的任何内容都可被持有该文件的人提取」后，用户选择 AppSecret 首次录入一次、之后由 Keychain 复用。

## 决议

1. **设置页改为卡片式主区**：工作库 / AI 模型 / 飞书三张卡；Base URL、区域、维度、账户标识、callback、问答预算、模型参数、能力状态与诊断入口收进「高级与自定义」折叠区。
2. **每张卡显示状态徽章**：未配置 / 已配置（尚未验证）/ 验证通过 / 验证失败 / 需重新授权。技术原因码映射为业务语言，并给出下一步动作。
3. **首次配置为分步向导**，步骤从「选模型」开始（工作库仍由既有 WorkspaceGate 负责），每步可跳过、可中断续接；设置页提供「重新打开连接向导」。向导状态只保存非秘密步骤信息，**密钥永不写入任何草稿、sessionStorage、localStorage 或工作库**。
4. **非秘密接入信息在构建时从本机忽略文件注入**，不进入源码仓库；代码保留官方公共端点作为无注入时的回退默认值。百炼地址采用官方推荐的**业务空间专属域名** `{WorkspaceId}.cn-beijing.maas.aliyuncs.com`（OpenAI 兼容 `/compatible-mode/v1`、DashScope `/api/v1`），依据阿里云百炼官方[地域及接入域名](https://help.aliyun.com/zh/model-studio/beijing-access-information)中「业务空间专属域名（推荐）」与迁移映射；`dashscope.aliyuncs.com` 作为存量回退默认保留。注入文件只允许非秘密字段，实现必须拒绝 secret 形态的键名。
5. **连接检查保持显式确认**：点击「检查连接」先展示本次范围（固定短合成 payload、不发送工作库材料、占用次数与累计剩余），确认后才发；沿用现有受限合成 smoke 额度（每项 1 次、跨运行累计、失败/超时/未知同样计数、不自动重发）。**不做保存后自动联网验证**。
6. **Feishu App ID 属非秘密值**，可随注入文件预填（高级可覆盖）；**App ID 不写入 tracked 文档**。
7. **密钥边界不变**：DeepSeek key、DashScope key、Feishu AppSecret 只由用户在本机设置入口录入一次并存入 macOS Keychain，不打入安装包、不写入仓库、不通过聊天传递。Keychain 不可用时失败关闭。
8. **飞书任务写继续禁用**，能力文案不得声称可以写回飞书任务。

## 与既有决议的关系

- 本 ADR 细化 [ADR 0009](0009-first-use-provider-configuration.md)：非秘密字段由「用户在设置中填写」改为「构建时注入的默认值，高级可覆盖」。
- 不改变 PRODUCT-SPEC 中「密钥不打包、不通过聊天传递」「默认 Fake」「真实调用需一次性范围预览与独立确认」「正式任务事实由飞书管理」等条款。
- 真实账户可用性、OAuth/scope、Keychain 生命周期、账单与答案质量仍为 NOT_RUN/UNVERIFIED；本 ADR 不因界面改动而改变这些门的结论。

## 影响与待同步

- 需要同步更新：产品规格首次配置段落、[M42 readiness](../handoff/M42-PACKAGE-A-READINESS.md) 准备卡、README 的设置界面描述。
- 注入机制不得把真实业务原件、密钥或个人标识写入仓库；注入文件位于 Git 忽略目录，并由实现校验只含允许的非秘密字段。
