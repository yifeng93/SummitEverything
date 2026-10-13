# M3 功能包 2 repair 2 独立 QA

**结论：FAIL。** 被测产品源码固定 SHA：`94854bafc0f6aec4d79e55c851be2640ef436739`；产品树来源 SHA：`b7cfd32e1a1991db6e045f282bc0ab39d48aae15`。QA 起始时产品、tracked tests、web、native、lock tree 与固定源码完全一致；QA 未修改产品实现、tests、快照、依赖或配置。唯一提交为本报告和脱敏证据。repair 1 的两项缺陷本轮均通过；本轮仍发现 C13/C20 两项新缺陷。repair 2 已是最后自动修复轮次，由 Sol 核定门并请用户决定后续。

证据根目录：[repair 2 evidence](evidence/2026-10-12-m3-package-2-qa-repair-2-94854ba/)，包括独立 harness、QA 合成 provider payload、raw logs 与 exit codes、浏览器 AX 记录及相对仓库根的 SHA-256 manifest。临时工作库、profile 和运行时产物保存在忽略目录 `.local/qa/m3-package-2-repair-2/`，没有进入提交。所有检索走本地 loopback 服务；DeepSeek adapter 用 `httpx.MockTransport`，向量由本地 FakeEmbedding 生成。未调用真实模型、飞书、用户资料或凭据。

## 验收状态

| 范围 | 状态 | 观察结果 |
|---|---|---|
| C13 current/history | FAIL | 当前范围仅引用当前青岚 18 万页；明确选择历史范围后会引用 superseded 旧版并显示“已被替代的历史版本，仅限历史参考”。但从有效历史引用打开已批准 superseded 页时，WebUI 把知识效力误显示成内容未经确认，见 QA-R2-01。外部编辑后，旧引用重开显示“原引用版本已更新”；没有用旧 hash 继续支持当前问答。 |
| C14 连续指代与对象边界 | PASS | 青岚 → “它呢？” → “它什么时候启动？”均只引用青岚；明确切换到朱雀后，“它”延续朱雀。先切到未知主体“风铃工程”后再问指代，没有串回旧主体或编数字。 |
| C19 事实检索、正式页名字、comparison / plan | PASS | fresh synthetic index 上，直接问青岚预算、自然礼貌问法“你能告诉我青岚计划的预算上限是多少吗？”与“我想知道青岚计划的预算上限。”均只引用青岚。用别名、仅 title 的正式页、manifest project 名和 line 名查询，引用正文来自真实正文；excerpt 不补名字。Comparison 跨青岚/朱雀且推断单独呈现；plan 分列 source statements、inferences、advice、missing information。 |
| C13/C19 硬性信任边界 | PASS | 合成无批准页、role: source 原件、role: draft 待审稿和 invalid 页在 current purpose 下均未被引用；已批准 invalid 页只在 history purpose 可用并显示 invalid 效力。外部编辑后的过期 index hash 不进入当前或历史新查询；显式重新确认后，新 hash 在历史范围才可引用。 |
| C14 requestID / SSE / 取消与恢复 | PASS | 修改 role/memory 后同 requestID 语义 replay 未重调 provider；同 ID 不同 answer mode 返回 409。取消端点 HTTP 202，SSE 以 cancelled error 终止，conversation 为 cancelled 且答案为空。独立 Uvicorn 输出 34 字符 partial 后 SIGKILL；重启同 profile/workspace 后准确恢复为 interrupted，重放相同已存事件且不自动补发。 |
| C20 角色与记忆 | FAIL | 角色创建、编辑、删除成功；pending candidate、确认后 active、编辑与删除路径实际运行；拒 assistant、伪 ID、未勾选和引用材料 canary。一个清楚的本人偏好句被误判为引用/材料并 HTTP 422，见 QA-R2-02。预算超限返回可读 422、不增加 provider calls；8000 字符长问题完整传给 Fake provider，无静默截断。 |
| C21 双 profile / 双工作库隔离 | PASS | 两个 profile 打开同一 workspace UUID 时角色、记忆、历史与 profile path 独立；同 profile 从工作库 C 切到 A 再切回 C，另一工作库的状态不出现，切回原库后状态恢复。只写 QA 合成状态，没有写正式知识、任务或进度。 |
| README 集成矩阵 | PASS | 实际安装 `npm --prefix web ci` 与 `uv sync --locked --group dev`。Guarded pytest 405 passed / 1 warning；ruff check/format、mypy 40 files、lock check、uv build、OpenAPI types、Web 52 tests、typecheck、lint、build 均退出 0。Web lint 有两条 warning。每条命令原始日志和退出码在证据目录。 |
| 浏览器 DevTools console / Network 面板 | NOT_RUN | CUA 实际操作本地浏览器并读取 AX；当前工具未暴露 DevTools console/network 面板。 |
| Runtime 模型元数据 | UNVERIFIED | 本轮只运行 fake provider；没有观察实际 runtime 元数据，不从 TOML 推断。 |
| 真实服务、凭据、原件、native、DMG、五日、双机、smoke | NOT_RUN | 未调用真实模型 / 飞书，未接触凭据、Keychain、原件或真实工作库，也未构建或验收 DMG，未运行五日 / 双机门，未消费 smoke。 |

## 可复验缺陷

### QA-R2-01：历史页把“仅限历史”显示成“待确认 / 正文已变化”（C13）

合成页 `青岚旧预算规则.md` 的 `validity` 为 `superseded`。初始 `content_sha256` 与 frontmatter `approval.content_sha256` 完全相同（`eab770…7fcd9fb`），但 `GET /api/v1/pages` 返回 `approval_state=invalid`。CURRENT 问答只引用 18 万元当前页；显式 history 问答引用旧版 20 万元，并把引用标为“已被替代的历史版本，仅限历史参考”，符合效力规则。

实际在 WebUI 打开这条 history citation，PageReader 显示“待确认”，以及“此页面自上次确认后已有变化，目前不会用于知识问答。请核对当前正文；只有点击确认后，新版本才会恢复检索资格。”这与当前页面 hash 和批准 hash 相等矛盾，并把效力状态误述为尚未确认。随后只在 QA 合成工作库外部编辑正文为 21 万元，旧 hash 的 current/history 候选均被拒绝，旧历史 citation reopen 返回 409；再显式 POST 页面确认得到 HTTP 200，新的 content/approval hash 同为 `a69253…54ac73693`。CURRENT 仍只引用 18 万元页，history 才引用已批准的 superseded 21 万元页，但 `approval_state` 仍返回 `invalid`，WebUI 仍显示上述“待确认 / 自上次确认后已有变化”。因此问题是历史效力与确认状态在 UI 状态映射中混淆；它没有导致旧正文绕过 stale-hash 门进入新检索。原始页面状态、重确认结果、CURRENT/HISTORY citations、409 及浏览器 reopen AX 分别见证据 `harness/history-page-hash-results.json`、`stale-hash-r2-results.json`、`reapproval-r2-results.json`、`browser-ax-observations.md`。

### QA-R2-02：本人偏好自然句被误判成引用材料（C20）

在实际浏览器新对话中直接键入“我偏好用简短中文回答，并明确标出资料没有提供的数字。”（未 paste；来自本轮 QA 输入），回答完成后勾选“这是我本人表达的偏好或事实”。AX 显示 checkbox 为 1，创建候选按钮启用；点击后 UI 提示“这段内容看起来是引用或材料描述，不能作为本人记忆候选。”随后以真实历史 user message ID `ea44a3d1-70de-4545-bac1-fdcc16ecd613` 与 `user_expression=true` 调用 candidate API，得到 HTTP 422 和同一错误。它是本人主动陈述的表达偏好，不含材料引用或转述。

对照真实用户消息“我偏好用简短中文表达。”得到 HTTP 201，候选进入 pending；明确标注“引用材料原文……这是粘贴内容，不代表我的偏好”的 canary 正确返回 422。没有 assistant 消息作为来源，也没有伪造 message ID 或剪贴板内容。结果表保存 provenance / message ID / response，见 `harness/memory-provenance-r2-results.json`。拒绝的真实自然偏好句因此无法经正常 UI 流程进入用户可确认的候选。

## 自动检查与服务清理

`npm --prefix web ci`、`uv sync --locked --group dev`、guarded pytest、ruff、format、mypy、`uv lock --check`、`uv build`、`npm --prefix web run api:types`、Web tests、typecheck、lint、build 的实际命令输出及 `.exit` 见证据 `raw-logs/`。最终集成重跑另见 `blackbox-r2-final`、`workspace-switch-r2`、`cancel-service-r2`、`partial-recovery-r2`、`context-boundaries-r2`、`trust-boundary-r2`、`memory-provenance-r2`、`stale-hash-r2` 和 `reapprove-history-r2`。

测试结束后已停止 Vite、profile A/B fake API 和 partial recovery API；核验监听端口 `15173/18793/18795/18796` 均无 listener。固定产品 HEAD 仍为 `94854bafc0f6aec4d79e55c851be2640ef436739`，`git diff -- src tests web native uv.lock` 为空。除本报告和对应 evidence 外，没有其他 tracked working-tree 变化。
