# Frontend D 初次独立 QA 报告

## 结论

**总体：FAIL（P1，修复前固定候选）**。被测源码 SHA 为 `876008e1d33420f57fb31772c76e471379e6b98d`。独立 browser mock 与同一隔离 profile 的 native restart 都复现：完成首次配置后，重启并打开同一 workspace 仍会重新进入 workspace gate，随后打开已有 workspace 会再次打开首次配置第 2 步，Today 不出现。此行为违反“完成后不再自动打扰、未完成按原步骤续接”的已确认验收要求。

本报告是固定 SHA 的初次阶段验收，不代表 D 整体或真实服务 PASS。QA 没有改动产品源码、已有 tracked tests、依赖、锁文件或配置。所有自建 harness 与证据都在本目录。

## 固定目标与身份

- 源码 HEAD：`876008e1d33420f57fb31772c76e471379e6b98d`；测试前后相同。
- 候选包路径与身份见 [candidate-identity.json](candidate-identity.json)。DMG SHA-256 与 manifest 预期一致；`hdiutil verify` 为 VALID；`codesign --verify --deep --strict` exit 0。
- 独立测试 checkout：`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything`。最终 `git status --short` 为空；`uv.lock` 与 `web/package-lock.json` 无 diff。
- 阅读了 AGENTS.md、README、TESTER、ACCEPTANCE、FRONTEND-GUIDE、PAGE-SPECS 与 FRONTEND-EXECUTION-PLAN。

## 缺陷：已复现 P1

`web/src/App.tsx:126-135` 的 workspace gate `onOpened` 不检查已完成的首次配置进度，直接设置 `{open:true, step:2}`。进度仅保存在 localStorage；WKWebView 使用 nonPersistent 数据存储时，应用重启不会保留该状态。

独立 browser mock 使用合成 localStorage：`{step:5,completed:true,open:false}`。`GET /workspaces/current` 返回未打开状态后执行 `POST /workspaces`，实际 UI 仍显示首次配置第 2 步，Today 不可见；预期应直接进入 Today。结果在 [reproduction.json](evidence/workspace-gate/reproduction.json)，截图为 [completed-workspace-reopened.png](evidence/workspace-gate/completed-workspace-reopened.png)。

Native 使用固定 candidate、全新严格 canonical NSTemporaryDirectory profile、offline guard 和合成空 workspace。完成配置后 Today 出现；退出并确认本轮 app/backend PID 已退出、18793 端口释放；同 candidate、同 profile 重启，workspace gate 再次出现。打开同一 workspace 后落到首次配置 step 2，未进入 Today。安全摘要：[native-restart-repro.json](evidence/native-restart-repro.json)，identity/preflight：[native-preflight.json](evidence/native-preflight.json)。这是本轮直接 native GUI 观察，不由开发者 GUI 结果代替。未使用真实资料或凭据。

## 命令和观察结果

所有原始输出及退出码见 `logs/`，Playwright 截图和几何测量见 `evidence/`。

- `npm ci`：PASS，使用锁文件安装。
- `npm test -- --run`：PASS，25 个文件、204 tests。
- `npm run typecheck`、`npm run lint`、`npm run build`：均 PASS。Lint 有 2 条既有 set-state-in-effect warnings；build 有 chunk size warning。
- `npm run test:e2e`：PASS，2/2（首配流程与 Today/Approval/Settings viewport）。
- 独立 C 页面 E2E：PASS，1/1；合成数据覆盖 Projects 列表/详情、Reader、Ask，在 320/390/768/960/1280 CSS px、light/dark。截图和 measurements 在 `evidence/c-view/`。
- Python：pytest 661 passed（含 1 条 Starlette deprecation warning）、ruff、ruff format --check、mypy、`uv lock --check` 均 exit 0；Swift tests 5 passed。日志分别为 `python-*.log`、`uv-lock.log`、`swift-tests.log`。
- CSS zoom 诊断：PASS（仅诊断 harness）。对独立页面施加 root/body CSS `zoom:2`，测得目标后代高度约翻倍且焦点仍可见。见 `evidence/zoom/measurements.json`。这是 CSS zoom 诊断，不是浏览器菜单 200% 缩放或 WKWebView 原生 pageZoom 验收，后两项 **NOT_RUN**；640 CSS px 的 reflow 证据也不等同 200% zoom。
- D 的 4 个全站 TODO：页面元数据与用户 code、pending/error 状态、破坏性操作正式确认与取消、StreamingMarkdown 临时补全渲染，现有全量单测和浏览器用例通过的部分均有相应证据；但本轮未对每类破坏性操作和所有页面的 first-error/retry/stale 流程做一套完整独立原生交互链，未覆盖部分记 **NOT_RUN**，不从自动化通过推断全站验收。
- 十条守卫的开发 mutation manifest 及 red/green rawlog 只作开发证据只读核查：十条均有 red exit 1、green exit 0 和日志，红因与预期拒绝现象相符。本 QA 没有独立重跑 mutation，故 QA mutation **NOT_RUN**；其结果没有冒充本轮 QA。

## 门状态

- 固定源码和候选 identity：PASS。
- Web 自动测试、类型、lint、build、Python、Swift：PASS（有上述 warnings）。
- Native 首次配置完成后 restart/open-existing：**FAIL（P1）**。
- 独立 Browser 页面与 CSS zoom 诊断：PASS；browser menu 200% 与 WKWebView 原生缩放：NOT_RUN。
- 本轮 native 完整导入→冲突确认→正式内容→索引→查询→引用→Reader 的跨层链：NOT_RUN。native 其他破坏性类别完整矩阵：NOT_RUN。
- 真实 OAuth/provider/Feishu/Keychain/付费服务、正式安装/公证、五日和双机：NOT_RUN。
- **D 初次阶段门：FAIL**，不能以多数自动检查通过结案。

## 后续

按协调者决议由 Sol 判定本轮 FAIL 并启动 repair 1；Developer 提交新 SHA/candidate 后，应由全新 QA 在该固定目标上重新验收。不要把本报告迁移到新 SHA 作为其 PASS 证据。
