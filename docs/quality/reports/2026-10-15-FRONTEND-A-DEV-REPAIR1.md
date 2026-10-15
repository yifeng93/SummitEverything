# 前端 UX 里程碑 A · 修复轮 1 开发报告

当前修复产品提交为 **`9c33a9dde3080fff3e3b3dd8a4193589ef52575f`**，基于 A 初始产品提交 `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`，原始项目基线 `e84e9e5a56475a19f68ca1a684366fba7f9fee83`。这份报告为后续 Fresh QA 交接，**不是开发者自验收，也不是 Sol 的阶段门结论**。修复轮1 Fresh QA 正在独立 checkout 对上述固定 SHA 复验，当前门状态 PENDING。

修复范围只包括初次 QA 的 F1–F3：首配必需密钥的提交前反馈、AI 三项合成连接检查的逐项状态和配置过期、飞书只读状态在刷新失败时保留最近成功值及读取时间。未继续 B、C 或 D。

## 行为修复

首配步骤 2 现在根据选中的能力、当前 password 输入及服务端 `credential_status` 计算是否缺必填密钥。缺失时保存按钮 disabled、`title` 说明具体能力和所需密钥，输入项旁显示字段级指引并通过 `aria-describedby` 关联。服务端已配置凭据时不要求再次录入；输入新密钥但钥匙串不可用时按钮仍禁用，现有提交服务端检查继续作为失败关闭的第二道保护。密钥仍只在组件内存中，不增加浏览器存储或新持久化路径。

设置页改为每个 smoke key 独立记录结果：DeepSeek Chat、Embedding、Rerank。总卡只有三项各自当前配置均通过合成检查时才显示“三项检查通过”；部分结果显示“部分已检查”，任何当前能力失败则显示“有检查失败”。三行各自展示成功、失败或原服务端待确认状态。每项本地结果附带本机配置比较签名 `configStamp`，由相关 provider、model、endpoint、账户、启用标记、运行模式、钥匙串可用性和凭据配置状态生成。设置编辑后只有受影响项签名失配，其旧检查自动回到未检查；这个比较签名只存在于 React 的本地临时状态，没有改动 API、服务端历史或 UI 契约中的业务标识。删除 DeepSeek / Model Studio 凭据也会让对应结果因签名变化失效。

飞书只读状态加载成功时保存 ISO 读取时间。普通刷新若返回 503 或无法解析，状态保留最近一次成功摘要并转为 stale；卡片继续显示摘要，同时用醒目的 alert 写明本次读取失败、缓存可能过时和上次成功时间，并提供重试。首次读取失败仍显示无法读取，不推测授权成功。已确认删除飞书应用密钥会直接把本机连接状态标记为未配置，并取消自动再读，不把旧授权缓存继续显示为“已授权”；只有用户之后主动重新读取且服务器成功返回，才接受新状态。飞书应用配置保存也先使旧状态失效。

## 固定 SHA 与改动范围

产品提交为 `9c33a9dde3080fff3e3b3dd8a4193589ef52575f`（短 SHA `9c33a9d`）。相对初次 QA 产品 SHA `9ed544a` 的产品 diff：6 个文件，158 insertions / 36 deletions。文件为 `web/src/components/FirstUseWizard.tsx`、`web/src/components/SettingsView.tsx`、`web/src/components/settingsBadges.ts`、对应两个测试文件和 `web/src/App.css`。初始 QA 报告、harness 与本报告属于随后单独的 docs-only 提交，不改变产品 SHA。

初次独立 QA 的 **FAIL** 报告和初次 harness 现归档于 [`2026-10-15-FRONTEND-A-INITIAL/`](2026-10-15-FRONTEND-A-INITIAL/)；QA 原始 worktree 没有修改。每个初次原始证据文件的 hash 和大小见其中的 `INITIAL-EVIDENCE-MANIFEST.json`。产品修复的红绿 harness、原始命令日志、截图和隔离环境保留于开发 worktree `.local/dev/frontend-a/repair1/`；命令结果索引已提交在 [`evidence/2026-10-15-frontend-a-repair1/command-results.json`](evidence/2026-10-15-frontend-a-repair1/command-results.json)。

## 观察到的检查结果

下列命令都在修复产品 SHA 的工作树执行，命令原文、退出码、测试计数、日志路径见 command-results JSON。单测和配置/向导状态测试使用合成 fixture；浏览器 route 全部限制在本机地址，真实 Fake 集成配置了独立 profile 根和每次唯一的 Playwright 临时工作库目录，没有 provider smoke POST。

| 检查 | 开发结果 | 证据 |
|---|---|---|
| `npm --prefix web test` | **PASS**，24 files；164 passed，8 todo | `command-logs/final-npm-test.log` |
| `npm --prefix web run typecheck` | **PASS**，exit 0 | `command-logs/final-typecheck.log` |
| `npm --prefix web run lint` | **PASS**，exit 0；有 3 条既有 App/Projects/Today React effect warnings | `command-logs/final2-lint.log` |
| `npm --prefix web run build` | **PASS**，exit 0；Vite 生产构建完成 | `command-logs/final2-build.log` |
| 离线 UI Playwright | **PASS**，2/2；首配/恢复及设置/今日 5 视口 × 2 主题 | `command-logs/final-mock-e2e.log`；`mock-evidence/` |
| 真实 FastAPI + Fake 隔离集成 | **PASS**，1/1；合成工作库，Fake，`externalAttempts=[]`，无 smoke POST | `command-logs/final-fastapi-fake.log`；`fastapi-evidence/fastapi-request-manifest.json` |
| F1–F3 设置黑盒回归 | **PASS**，3/3；包括密钥移除后缓存失效 | `command-logs/final-review-e2e.log` |
| 首配向导边界/视口 | **PASS**，12/12；必填指引、Keychain 失败关闭、5宽×双主题 | `command-logs/wizard-e2e.log` |
| 三项守卫隔离变异 | **PASS（测试能拦截突变）**；F1/F2/F3 每项故意破坏相应行为后测试 exit 1，恢复 byte-for-byte；之后全量单测及 typecheck exit 0 | `command-logs/mutation-f1.log` 至 `mutation-f3.log`，对应 `.exit` 文件，`post-mutation-npm-test.log` 和 `post-mutation-typecheck.log` |

修复前，校正后的 F1 正确预期在初始产品上重现按钮 enabled（1 项失败）；校正后的 F2/F3 正确预期在初始产品上均失败（2 项失败）。旧 SHA 红灯的完整原始日志位于 `.local/dev/frontend-a/repair1/logs/red-wizard.log` 和 `red-review.log`。首轮 Playwright harness 曾因 `testDir` 路径错误收集 0 项；修正后红灯确实落在产品断言，不以该配置错误作为红证据。测试与修复后的页面截图位于 `.local/dev/frontend-a/repair1/mock-evidence/`，包括：

- `onboarding-missing-key-guidance.png`：F1 字段提示、disabled 保存按钮和原因 title。
- `settings-ai-per-capability.png`：F2 一项成功、一项失败、一项未检查时的逐行状态及总卡提示。
- `settings-feishu-stale-read.png`：F3 保留最近授权摘要、读取时间、过期提示和重试入口。

## 修复矩阵和边界

| 缺陷 | 初次独立 QA | 修复轮1开发回归 | Fresh QA 修复轮1 |
|---|---|---|---|
| F1 缺密钥时按钮未禁用/无字段指引 | FAIL，`9ed544a` | PASS：Vitest + Playwright；已配服务端凭据不重复索要；Keychain 不可用禁用并失败关闭 | PENDING，目标 `9c33a9d` |
| F2 单项检查可将 AI 总卡标为通过 | FAIL，`9ed544a` | PASS：每项独立状态，错误不被别项成功覆盖，相关配置变化使局部状态过期；F2 变异可被测试拦截 | PENDING，目标 `9c33a9d` |
| F3 飞书刷新失败丢失最近成功状态/时间 | FAIL，`9ed544a` | PASS：stale 保留成功摘要及时间，告警/重试；首次失败仍 unreadable；删除密钥使缓存失效 | PENDING，目标 `9c33a9d` |
| A 中其余既有工作（首配、共享基础、三张设置卡等） | 初始 QA 对 `9ed544a` 有报告所列结果 | 这轮未改动；全量 unit、mock E2E 与 FastAPI/Fake 已对当前产品重跑 | 整体门仍等 Fresh QA，不把初始 SHA 的结论转记到当前 SHA |

真实 provider、真实飞书 OAuth、实际 macOS Keychain 访问/写入、真实用户工作库、Internal App/DMG、进程级重启、五日/双机与人工验收仍 **NOT_RUN**。本轮没有访问真实凭据、用户材料、外部服务或旧安装数据。十条全应用守卫中未属于 F1–F3 或此前 A 切片的项仍按路线图留给后续 D；本轮没有通过删测试、变更门槛或重置 todo 来收口。

Sol 已启动 Fresh QA worktree `frontend-a-qa-repair1`，仅对固定产品 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` 复验。本工作树从产品提交后保持源码、测试与 lock 冻结；下一步只接受 Sol 协调的 Fresh QA 结论和必要的 docs-only 状态同步。
