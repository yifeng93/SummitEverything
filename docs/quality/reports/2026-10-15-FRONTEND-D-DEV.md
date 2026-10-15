# 前端 UX 里程碑 D 开发自测与候选交接

- 产品源码固定 SHA：`876008e1d33420f57fb31772c76e471379e6b98d`，分支 `codex/frontend-ux-20261015`，产品 checkout 在冻结时 clean。
- 本报告是 Developer 自测和证据索引，不是独立 QA 或 Sol gate；D 全站及打包候选验收仍待 fresh QA。
- C 固定 SHA `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` 的适用离线场景已由 Sol 判 PASS；范围和初次/重试 harness 失败与最终通过见 [C QA 报告](2026-10-15-FRONTEND-C-QA.md)及[脱敏原始证据索引](evidence/2026-10-15-frontend-c-qa/README.md)。

## D 变更与原 TODO 对照

四条全站守卫均替换为真实断言，没有删减既有用例：

| 原守卫 | 本轮断言与主要用例 | 状态 |
|---|---|---|
| ① 普通页面正文、标题、details、aria 不泄内部标识；用户代码正文保真 | `ui-contract.render.test.tsx` metadata canary 覆盖 Today、Approval、Settings、Onboarding、Projects、Reader、Ask 等运行时普通 DOM；`pre code` 中内部样式字串作为用户正文对照保留 | Developer 自测通过，待独立 QA |
| ④ 未加载不能画成空态，成功空态、错误和 stale 最近成功值分开 | `TodayView.test.tsx`、`ApprovalView.test.tsx`、`AskView.test.tsx` 对 pending→loaded-empty/error 与 stale 路径断言 | Developer 自测通过，待独立 QA |
| ⑤ 删除、断开、覆盖、移动按类别确认；取消零写入、确认仅一次、busy 不重复执行 | `AskView.test.tsx`、`FeishuPanel.test.tsx`、`Reader`/`Projects` 页面用例和危险设置项用例覆盖各自确认流程；focused confirmation suite 覆盖取消与单飞 | Developer 自测通过，待独立 QA |
| ⑥ 流式 Markdown 中间态不裸露未闭合语法，代码与转义正文保真，终态和静态相同 | `MarkdownText.test.tsx` 逐 chunk golden 覆盖 bold、inline code、fence、表格、wiki/link pending 与完成；`AskView.test.tsx` 覆盖取消 partial；原始 source 不修改，终态用原文渲染 | Developer 自测通过，待独立 QA |

十条守卫各有一条受控 mutation：`.local/dev/frontend-d/mutation/01-metadata` 至 `10-viewport` 的 red exit 均为 1、恢复后的 green exit 均为 0。theme 对比度既有测试保持（两主题共 10 组文字配色对，均达到 4.5:1；3 组边界线对单独判读），D 未以此报告新增缺口。

## 自动检查与矩阵

Developer 记录的本轮最终退出码：Web 单测 204/204，TypeScript、lint、生产构建均 0；lint 保留 2 条 React effect warning，Vite bundle warning 保留。Focused confirm/stream/metadata 及运行时 metadata canary 分别通过；全套 shell E2E 2/2，C 浏览器矩阵 1/1。Python guarded suite 661 tests passed；`ruff check src tests`、`ruff format --check src tests`、`mypy src`、uv lock/schema gate 均 exit 0；Swift `swift test --package-path native` 为 5/5。受影响文件仅做过 Ruff 格式整理，未改后端语义，`content.py` 不变。

浏览器界面矩阵覆盖 Today、Approval、Projects 列表/详情、Reader、Ask、Settings、Import Drawer 与关键确认/Journal 对话框；320/390/768/960/1280 CSS viewport × light/dark，并检查 reduced motion、焦点、disabled、title、Escape 和横向溢出。640 CSS px 只作为 reflow 检查，不当作 200% 页面缩放。另有独立离线浏览器 harness 将 `document.documentElement` 的 CSS `zoom` 设为 2 并实测文字/按钮高度 2×、focus 可达、根滚动区无横溢；这只是 CSS zoom simulation，不代表 Chrome 菜单缩放或 WKWebView 原生 pageZoom。

## 全新 macOS 候选身份与 runtime

Native Codex `create_worktree` 创建的干净 build worktree 固定在产品 SHA 876008e。仅将主 checkout `.local/first-use/defaults.json` 复制到 ignored build worktree 同路径，未读取、打印、提交或外传值；build script validator 已验证。`scripts/release-macos.sh` 强制前端重建，exit 0。候选仅为 ad-hoc、未公证内部验证包，不能据此宣称发布 PASS。

| 字段 | 候选值 |
|---|---|
| App | `/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.app` |
| DMG | `/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.dmg` |
| Source / dirty | `876008e1d33420f57fb31772c76e471379e6b98d` / `false` |
| Bundle / build ID | `com.summiteverything.internal` / `20261015T132109Z-8a0917f72e08` |
| Frontend SHA-256 | `8a0917f72e0833727fa90a4f827e70be8835db6711eb9e24b167df16087fab62` |
| Dependencies SHA-256 | `cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7` |
| DMG SHA-256 | `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9` |

构建、初次启动与重启的安全 preflight 均核对唯一候选 native/backend PID、仅 allowlist 的 profile/guard 字段、18793 listener、health manifest identity 和静态 root 200；raw process environment/token 不落盘。profile 是 `NSTemporaryDirectory()` 的 canonical child，native/backend runtime offline guard 均为 1。启动前无 18793 listener；GUI 结束后本轮启动 PID 6917/6919 退出且端口释放。完整 manifest 与 logs 留在 build worktree 的 `.local/dev/frontend-d-final/`。

同一候选/隔离 profile 的实际 Fake WKWebView 流程：合成 quick note 与两份 synthetic 文件导入；创建 line/project；对来源先取消整理再显式确认；对合成稿件复核并确认正式版本；Fake 索引纳入 2 页；查询返回可读 citation 并打开 Reader。重启候选后，临时 workspace 内容和来源状态仍在；通过“打开已有”重新连接隔离 workspace 后可见原资料。

### 未验证项与风险

- **restart onboarding 疑点：UNVERIFIED。** 同 profile 重启显示首次配置向导第 2 步；手动打开已有隔离 workspace 后恢复了业务数据，但没有验证已完成首配不再打扰。`App.onOpened`/向导进度持久化路径由 Sol 交 fresh QA 独立核对。本轮保持源码和候选冻结，不自行修复；如 QA 确认缺陷，应新 SHA、新候选再验。
- **原生 WKWebView `pageZoom=2`：NOT_RUN。** 内部候选 View 菜单没有页面缩放项，Cmd+Plus 快捷键无可见变化；窗口放大不等于页面缩放。
- **Native GUI screenshot artifact：NOT_RUN。** CUA 无障碍树中观察到的候选页面状态留在本任务记录；未将含内置非秘密默认项的 screen capture 写入 tracked docs 或原始 QA evidence。
- 真实 provider、OAuth、Feishu、Keychain、真实用户资料、已安装 App/真实 Application Support、用户 Desktop/test、Developer ID/公证、长期五日/双机和生产操作均未触碰/未测。

## 复核入口

- 脱敏 evidence index 与文件摘要：[D DEV evidence](evidence/2026-10-15-frontend-d-dev/README.md)。
- 产品提交 SHA 和完整源变更：本报告记录的 `876008e1d33420f57fb31772c76e471379e6b98d`；下一步由 fresh QA 在独立 worktree 固定复验。
- 命令、exit sidecars、浏览器截图/测量、10 mutation 日志：产品 checkout 忽略目录 `.local/dev/frontend-d/`。
- 包 manifest、build、profile、native preflight、restart preflight、CSS zoom simulation 和 DMG：managed build worktree 忽略目录 `.local/dev/frontend-d-final/`。
- 实际 UI 流程只使用此 App/DMG 候选和隔离 Fake profile；QA 应对精确 App 重新建立自己的 temp profile，不要使用本轮 temporary profile。

D 开发自测不能代替独立 QA。Sol 对 restart onboarding 疑点、候选身份及完整 gate 最终判定；本报告不授予 merge、公开发布、公证或真实服务操作。
