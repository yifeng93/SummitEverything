# Milestone A 独立 QA 报告

- 被测代码 SHA：`9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`
- 比较基线：`e84e9e5a56475a19f68ca1a684366fba7f9fee83`
- QA checkout：`/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything`
- 验收期间固定 HEAD 未变化；最终 `git rev-parse HEAD` 仍为上述 SHA。最终 tracked diff 为空；QA harness、临时环境和证据仅在 `.local/qa/frontend-a-initial/`。
- 结论：**FAIL**。有三项可复现交互/状态缺陷，需修复后对新 SHA 重新验收。

## 范围与边界

按本轮明确决议验收A：暖橙/墨绿及五栏基线；工作库→密钥→检查→飞书→完成的共享首配和设置 step 4 入口；三张业务设置卡；本机密钥内存处理；统一确认对话框；共享 Markdown/StreamingMarkdown；真实 FastAPI + Fake 首配链路；5个视口×light/dark。旧 Today OAuth/审批迁移属于B，Ask/PageReader接入属于C，完整守卫及打包属于D，不按本轮缺陷计算。

只使用合成 profile/workspace 和 Fake。网络隔离配置阻止外网/DNS及Keychain；本轮未触碰真实provider、OAuth、飞书、用户材料、桌面或旧安装数据。浏览器和集成证据的 manifest 显示 `externalAttempts: []`，未发起 provider smoke POST。首配 FastAPI 测试只调用本机 API，包含建立合成工作库、设置读取及本地飞书状态读取。

## 命令与结果

命令均在固定 SHA checkout 执行。成功退出码为 `0`。

| 检查 | 命令 | 结果 |
|---|---|---|
| 依赖安装 | `npm --prefix web ci` | PASS，exit 0，226 packages，0 vulnerabilities |
| 单元测试 | `npm --prefix web test` | PASS，exit 0，24 files；160 passed，8 todo |
| TypeScript | `npm --prefix web run typecheck` | PASS，exit 0 |
| ESLint | `npm --prefix web run lint` | PASS，exit 0；有3条 React set-state-in-effect warnings（App.tsx、ProjectsView.tsx、TodayView.tsx） |
| 生产构建 | `npm --prefix web run build` | PASS，exit 0，Vite build 成功 |
| 离线模拟UI | `SUMMIT_E2E_EVIDENCE_DIR="$PWD/.local/qa/frontend-a-initial/mock-evidence" npm --prefix web run test:e2e -- --config ../.local/qa/frontend-a-initial/playwright.offline.config.ts` | PASS，exit 0，2 passed；包含首配/恢复及 Settings、Today 5视口×两主题布局检查 |
| FastAPI + Fake 首配 | `cd web && env PYTHONPATH="$PWD/../scripts/offline_guard:$PWD/../src" UV_PROJECT_ENVIRONMENT="$PWD/../.local/qa/frontend-a-initial/.venv" UV_OFFLINE=1 SUMMIT_E2E_EVIDENCE_DIR="$PWD/../.local/qa/frontend-a-initial/fastapi-evidence" npx playwright test --config ../.local/qa/frontend-a-initial/playwright.integration.config.ts` | PASS，exit 0，1 passed；localhost真实FastAPI、Fake设置和合成工作库链路 |
| 设置交互黑盒 | `cd web && npx playwright test --config ../.local/qa/frontend-a-initial/playwright.review.config.ts` | PASS，exit 0，2 passed；测试明确断言缺陷的实际行为，因此PASS表示复现成功，不代表相应验收要求通过 |
| 向导边界与视口 | `cd web && npx playwright test --config ../.local/qa/frontend-a-initial/playwright.wizard.config.ts` | PASS，exit 0，12 passed；视口10项、密钥和workspace状态2项。保存按钮问题由断言实际错误状态并留证，故该测试PASS不代表验收要求通过 |

期间最初出现的QA harness配置/路径错误已修正；不作为产品失败。最终wizard整套12项复跑exit 0。未重跑 npm ci、unit/typecheck/lint/build 和独立已完成的UI/集成套件；恢复验收后新增的完整边界套件已复跑。

## 验收矩阵

| 项目 | 状态 | 依据 |
|---|---|---|
| 固定SHA、基线和测试期间无移动 | PASS | 初始及最终 `git rev-parse HEAD` 相同；最终 tracked diff为空 |
| 五档 320/390/768/960/1280，设置与今日 light/dark | PASS | 离线Playwright 2项通过；measurements记录所有宽度的document/body/viewport相等，无整页横向滚动 |
| 向导五步骤五档×light/dark | PASS | 独立wizard Playwright 10项通过；无整页横溢 |
| 首配 workspace→设置→恢复，Fake 本机后端链路 | PASS | mock及FastAPI+Fake测试通过；本机manifest记录合成workspace POST与本机设置读取 |
| 设置入口共享向导/step4、步骤恢复/显式关闭/已完成状态 | PASS | mock首配/恢复与设置入口黑盒通过；截图在 mock-evidence |
| 密钥仅password输入、内存、不落storage，退出清空；Keychain不可用失败关闭 | PASS | wizard secret边界测试通过；无凭据写入；浏览器存储和请求体无secret |
| 必填按钮禁用、title、字段级错误 | **FAIL** | 缺陷F-1；必填DeepSeek密钥为空时“保存密钥并继续”仍enabled且无title，点击仅出现通用步骤错误 |
| AI三项独立能力状态、总卡不误报 | **FAIL** | 缺陷F-2；能力行仍各显示“已配置，待本次确认”，但一次局部检查成功会把整张AI卡设为“验证通过” |
| 飞书状态读取失败时保留最近成功值和读取时间 | **FAIL** | 缺陷F-3；成功响应后下一次读取503使状态被替换成“授权状态暂时无法读取”，旧成功值/时间不再展示 |
| 设置三张业务卡/高级信息分层 | PASS（静态与界面抽查） | Settings显示工作库、AI模型、飞书业务卡；高级折叠区承载诊断字段。无独立视觉人工评审 |
| 确认对话框安全交互 | PASS | 删除密钥：role=dialog、aria-modal、焦点落在取消；取消0 DELETE；双击确认只发1 DELETE。合成API拦截，无写真实系统 |
| smoke检查独立范围确认、取消不写、成功单次写、额度展示 | PASS | 黑盒确认取消0 POST、确认1 POST；额度由本地mock/API读取。未调用真实provider；未知结果重发边界未直接模拟，按本项的API额度门为NOT_RUN（见下） |
| MarkdownText/StreamingMarkdown安全及语法 | PASS（组件测试） | 全量Vitest通过；组件测试覆盖GFM、标题/粗体/列表/表格/代码、raw HTML惰性处理、安全外链、wiki链接callback及未完成标记和结束态一致性 |
| Ask/PageReader消费者接入 | NOT_RUN | 明确属于C，不属于A共享组件交付 |
| 真实provider/OAuth/飞书、Keychain落盘成功 | NOT_RUN | 明确禁止真实外部连接/凭据；Fake隔离验证不能代表真实服务 |
| DMG、五日、双机和正式人工验收 | NOT_RUN | 不属于本轮前端A检查范围 |

说明：viewport测量报告里有少数内部子元素边界宽于320，但`.app-frame`、`.main-shell`、`.main-content`、`document`和`body`没有整页溢出；本要求按整页横溢判定通过。

## 缺陷

### F-1（P1）必填密钥缺失时仍允许点击保存

- 位置：[FirstUseWizard.tsx](/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/FirstUseWizard.tsx:301)，保存按钮在304行仅受`busy`控制。
- 复现：`.local/qa/frontend-a-initial/specs/wizard-viewport.spec.cjs`中`required credentials expose an enabled save action without field guidance`；启动离线向导，在step2选择“整理与问答”，保持DeepSeek Key为空。按钮可用、没有`title`；点击后只能看到通用 `role=alert`，没有对应字段错误。
- 预期：必填项未填时按钮disabled并有解释title/字段错误；不可进入下一步。
- 实际：按钮enabled；提交后才显示泛化错误，用户不清楚哪个输入项阻止继续。
- 证据：wizard Playwright结果目录 `.local/qa/frontend-a-initial/playwright-wizard-results/`；规格文件记录断言及行为。

### F-2（P1）单项检查成功把AI总卡误报为整体验证通过

- 位置：[SettingsView.tsx](/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/SettingsView.tsx:46)以单一`lastCheck`维护全卡检查结果；[settingsBadges.ts](/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/settingsBadges.ts:195)在`lastCheck === 'succeeded'`时直接输出“验证通过”。
- 复现：`.local/qa/frontend-a-initial/specs/settings-review.spec.cjs`的capability/status场景；以局部provider smoke失败后再成功的响应驱动界面。成功后总卡徽章变“验证通过”，但三条能力行分别仍是“已配置，待本次确认”。
- 预期：AI总卡及每条能力状态须反映逐项真实结果；单次单能力成功不可让未检查/失败能力整体泛绿。
- 实际：AI总卡表达范围大于已完成检查范围。**能力行本身没有同时误报**：三行都保持各自“待本次确认”，错误仅在总卡徽章（没有一行被改成可用）。这仍会在主要卡片层面造成错误的整体成功信号。
- 证据：设置黑盒规格和运行结果；源码定位如上。

### F-3（P1）飞书状态读取失败覆盖最后成功值且未保留读取时间

- 位置：[SettingsView.tsx](/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/SettingsView.tsx:80)的`loadFeishuStatus`仅保存当前状态；84–86行在不可解析/异常时直接替换为`unreadable`。飞书状态没有对应的`lastSuccess`与读取时间状态。
- 复现：`.local/qa/frontend-a-initial/specs/settings-review.spec.cjs`的Feishu场景；第一次本机状态读取返回已授权及测试账户，点击“重新读取授权状态”后令请求返回503。
- 预期：展示最近一次成功授权状态及其读取时间，同时提示本次读取失败/可能已过期。
- 实际：整卡被“授权状态暂时无法读取”替换，之前成功值不再展示，成功读取时间也没有保留或显示。
- 证据：设置黑盒规格和运行结果；源码定位如上。

## 五轴代码质量判断

- **正确性 / 规格一致性：FAIL。** F-1至F-3均由真实UI交互（网络仅在浏览器/API mock）复现；其余核心新流程与边界覆盖见上表。
- **安全性：PASS（已测边界）。** 密钥为password控件；成功提交/退出清空；没有进入local/session storage或模拟请求体；Keychain不可用路径拒绝写入；删除密钥依赖危险确认；off-line guard记录无外连尝试。真实Keychain与provider未测。
- **可读性：PASS / 有改进空间。** 前端类型检查通过；新增业务组件职责可定位。局部状态有单值代表多能力检查结果（F-2的根本语义风险），React lint仍有3条effect更新warning。
- **架构：PASS（A范围）。** 首配集中于共享向导、设置状态以业务能力呈现，真实后端链路经过FastAPI+Fake；C范围旧消费者未接入不判失败。需修复统一卡状态的数据模型以避免跨能力混淆。
- **性能 / 响应式：PASS（有限范围）。** 五档尺寸、两主题和关键向导/设置状态均通过整页溢出检查；未做压力、慢网或大型数据性能测试，记为NOT_RUN。

## 风险、工作树与下一步

A门当前FAIL，三项缺陷均建议修复后重新提交SHA并由新一轮QA验收。单元/构建通过不能覆盖这三项交互错误；真实连接、Keychain保存、安装包及多设备/长期验收仍未验证。QA未修改tracked文件或产品代码；`git status --short`为空，HEAD保持固定SHA。所有报告、harness和证据在`.local/qa/frontend-a-initial/`，未提交。
