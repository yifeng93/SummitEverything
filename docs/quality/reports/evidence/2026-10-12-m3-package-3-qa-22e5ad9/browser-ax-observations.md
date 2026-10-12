# 浏览器 UI 实测记录（合成数据）

运行环境：真实 Codex IAB 浏览器，A=`http://127.0.0.1:15173/`、B=`http://127.0.0.1:15174/`；分别连接独立 profile/API 端口 18793/18794、同一个 `.local/qa/m3-package-3/workspace`。Fake 模型、Fake Feishu、MemorySecretBackend；无真实凭据、外部模型或飞书调用。服务启动配置和日志在 `.local/qa/m3-package-3/server-{a,b}.log`、`server-b-restart.log`（本证据包不含 profile DB/服务本地状态）。

实际 UI 交互与可访问性树/API 观察：

1. A 建立合成 workspace、line/project，录入一份“待审核”原件并生成 draft。B 用另一 profile 打开相同 workspace、刷新后看见同一 item 和 draft；两侧 item 为 `reviewing`，对应 job 为 `completed`，draft 为 `pending`。UI 仍提供独立“确认并写入知识库”操作。
2. A 对含 `Setup` 与 `Schedule` 两个标题的合成文本执行整理，生成两个独立 pending drafts；A 只确认 Setup。B 刷新仍看到 Schedule 待审，item 仍显示“待审核”。这验证了共享稿件与跨 profile 部分批准，以及 item/job/provider 完成态和业务审阅态分开显示。
3. 为浏览器呈现明确 unknown 场景，QA 将一个合成 item/job fixture 置为 `unknown` 后在 B 刷新。可访问性树显示“请求状态未知”；勾选后出现提示：“请求状态未知，不会自动重发。明确重新整理会创建新操作，可能再次调用模型；原件与既有稿件会保留。”只在点击“重新整理所选”后才发起新 operation 并新增 pending draft。dead-worker/no-checkpoint 不自动重发另由 backend 目标回归实测。
4. B 服务重启后，重新打开同一 workspace；待审稿、共享 item 与审核状态仍可见。A/B API 快照保存在 `api/`，profile state tree 记录两组本地数据库/诊断文件分别落在各自 profile 根目录；B 的 roles/memory 为空，A 的合成 role 不出现在 B；两侧 index 均 `not_ready`。workspace 本身扫描没有历史/role/memory/index/凭据/诊断数据库。

浏览器提供者没有导出持久 PNG 的接口，本次没有保存屏幕截图文件；以上为实际交互时的 AX 状态摘录与可复核 API JSON。Chrome DevTools console/network 捕获为 NOT_RUN。

测试工作区含一条由早期错误 API fixture 创建的合成 `paste` failed item；另有 unknown fixture 和多段标题 fixture。它们均为 `.local/qa` 下的去标识测试数据，不是产品文件或真实资料。
