# 前端 UX 里程碑 A：开发交接

产品固定提交：`9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`（产品代码与测试）。基线：`e84e9e5a56475a19f68ca1a684366fba7f9fee83`。报告和证据索引是 docs-only，不改变产品 SHA。该提交尚未经过独立 QA，以下均为开发者自测观察，不构成阶段通过。

## 交付行为

- 设置页连接工作库、AI 模型、Feishu 统一调用应用级首次配置流程。无库时先做第 1 步；打开工作库后在同一向导原地进入第 2 步。工作库入口进入第 1 步，设置连接/重新授权 Feishu 直达同一向导第 4 步。
- 非秘密进度按服务端返回的真实 profile + workspace 身份隔离保存。向导仍打开时页面重载会恢复当前步；用户显式关闭后不自动弹出，但设置入口可以手动续接；完成后重载不自动打扰。密钥只在字段/内存短暂存在，不写入 localStorage、sessionStorage 或工作库。
- 设置主区是纵向「工作库 / AI 模型 / 飞书」三卡。能力用业务中文逐项列出，密钥、模型标识、端点、账户、callback、预算与诊断收在默认折叠的高级区；危险区位于其底部，确认仅删除所选密钥。正文明确区分工作库正文和本机 profile 的索引、历史、凭据与诊断。
- 共享 ConfirmDialog 提供 `role=dialog` / `aria-modal=true`、焦点陷阱、Escape 取消、关闭还焦点、取消先于确认；streaming markdown 仅展示稳定前缀，静态与流式共用 `react-markdown` + `remark-gfm`，禁用 raw HTML，并保留安全外链与内部页面回调。
- `test:e2e` 是只访问 loopback 的 mocked 浏览器测试；真实集成单独运行本机 FastAPI + 合成 Fake，并使用运行期新建的隔离 profile/workspace。未调用真实模型、Feishu、Keychain 或真实用户目录。

## 验证结果

以下为产品提交后的最终命令；真实退出码与完整输出保存在 `.local/dev/frontend-a/current/`，同样的精简清单见[命令结果 JSON](evidence/2026-10-15-frontend-a-dev/command-results.json)。

| 命令 | 结果 |
|---|---|
| `cd web && npm ci` | PASS，exit 0；226 packages，0 vulnerabilities |
| `cd web && npm test -- --run` | PASS，exit 0；24 files，160 passed，8 todo |
| `cd web && npm run typecheck` | PASS，exit 0；正式 `tsc -b` |
| `cd web && npm run lint` | PASS，exit 0；3 条 React effect warnings（App / Projects / Today） |
| `cd web && npm run build` | PASS，exit 0；Vite 生产构建成功 |
| `cd web && SUMMIT_E2E_EVIDENCE_DIR=../.local/dev/frontend-a/current npm run test:e2e` | PASS，exit 0；2 tests，五档 320/390/768/960/1280 × 浅/深主题。今日与设置横向溢出最大值均为 0 |
| `cd web && npm run test:e2e:integration` | PASS，exit 0；本机 FastAPI + isolated Fake，1 test |

本轮起始基线记录为 `147 passed | 10 todo`；本次新测试与完成本地设置/视口断言后为 `160 passed | 8 todo`。保留的 8 个 `todo` 是未完成全应用断言，不按通过计算：① 全应用内部标识位置、② 项目中文优先、④ 今日/审批/项目/问答加载空分离、⑤ 全应用危险动作、⑥ 页面全面 Markdown/流式接入、⑧ 今日区块及退役内容、⑨ 各列表零模型请求。相应后续归属以 `ui-contract*.test.tsx` 中的 todo 文案为准；A 未提前收口 B/C/D 页面守卫。

A 范围变异结果：①③④⑤⑥⑦⑧⑨⑩ 九条各自应用了单点故障，指定测试均 exit 1；每次在 `finally` 精确恢复原文件。随后 `npm ci` 后再次跑全套单测、正式 typecheck、lint、build、mocked E2E 和真实集成，全部 exit 0。逐条失败输出在 `.local/dev/frontend-a/current/mutations/`，摘要在 `.local/dev/frontend-a/current/mutations/summary.txt`。

### A 验收矩阵（开发自测）

| 需求 | 状态 | 证据 / 限定 |
|---|---|---|
| 五档、浅/深截图和测量 | PASS | `.local/dev/frontend-a/current/{today,settings}-{320,390,768,960,1280}-{light,dark}.png`；measurements.json 显示横向溢出 0 |
| 统一首配流程、step1→2、错误态、可跳步骤 | PASS | Playwright `first-use.spec.ts`；逐步截图 `onboarding-step-2/3/4/5.png` 与 `onboarding-workspace-error.png` |
| 第 3 步仍打开时 page reload 自动恢复 | PASS | `onboarding-step-3-reloaded-open.png` |
| 显式关闭后不自动弹、设置手动 resume step3 | PASS | `onboarding-step-3-manual-resume.png`；关闭状态与重载独立验证 |
| 完成后不自动弹；设置 Feishu 按钮直达 step4 | PASS | Playwright + `onboarding-reauthorize-step-4.png` |
| profile/workspace 身份隔离、storage 失败、旧格式关闭 | PASS | `firstUseProgress.test.ts` |
| Settings 3 卡、能力状态、隐私分级、初次读失败降级、无成功假态 | PASS | `SettingsView.cards.test.tsx`；synthetic IDs/hash 不出现在主卡；只读失败各卡有“暂时无法读取”及重试 |
| ConfirmDialog a11y 与取消零写 | PASS | ConfirmDialog/Settings 回归；未确认与取消路径 API 写入数为 0 |
| 密钥保存/Settings refresh 无自动 provider 请求 | PASS | 组件测试：密钥字段清空且不入浏览器存储、provider smoke POST 为 0；连接检查仍需独立范围确认 |
| Markdown 安全与稳定流前缀 | PASS | `MarkdownText.test.tsx`；GFM、raw HTML 不执行、内部链接回调、完整代码围栏与未闭合语法 |
| 真实 FastAPI + Fake 首配 | PASS | `fastapi-onboarding-complete.png`、`fastapi-request-manifest.json`；`externalAttempts=[]`。这不是真实 provider/OAuth 验收 |
| 守卫 ①③④⑤⑥⑦⑧⑨⑩ 对 A 相关断言的变异 | PASS | 九个故障变体均 exit 1 后恢复；全应用语义未实现项仍 todo |
| 守卫 ② 与全站剩余守卫 | NOT_RUN | 后续页面切片/里程碑 D；不把 8 个 todo 计作通过 |
| 真实 OAuth、OS Keychain、真实 provider、进程级重启、Internal App/DMG | NOT_RUN | 本轮只做离线浏览器与临时 FastAPI/Fake；页面 reload 覆盖不等于进程重启 |
| 独立 QA | PENDING | Sol 已启动 fresh QA，目标固定产品 SHA `9ed544a`；开发者不判阶段 PASS |

截图和原始日志只在本机隔离路径 `.local/dev/frontend-a/`，不纳入 Git。FastAPI 请求清单只含合成请求路径；未写入任何秘密或真实业务材料。

## 限制与 QA 复验

- `npm test` 只跑 Vitest，Playwright mock 与真实 API 集成必须分别运行，不能由 Vitest 通过代替。
- 仅页面 reload 自动恢复与设置手动续接已测试；应用进程重启属于 D 包/安装验证，本轮 NOT_RUN。
- 真实 OAuth、Keychain 生命周期、Real provider 和 Feishu 外部请求均 NOT_RUN。今日既有授权入口迁移在 B，审批/今日/项目/问答页面实现与全应用守卫由后续切片完成。
- Fresh QA 可在干净依赖下复现：`npm ci`；`npm test -- --run`；`npm run typecheck`；`npm run lint`；`npm run build`；`npm run test:e2e`；随后 `npm run test:e2e:integration`。若需要重新生成截图，设置 `SUMMIT_E2E_EVIDENCE_DIR=../.local/dev/frontend-a/current` 后运行 `npm run test:e2e`。这些命令在 `web/` 内运行。
