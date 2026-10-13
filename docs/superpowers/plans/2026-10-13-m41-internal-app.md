# M4.1 内部 macOS 应用集成开发计划

> 执行方式：按用户 2026-10-13 的明确授权，一个 Developer Luna 连续实现、自测和小逻辑提交；整包固定 SHA 后由全新 QA Luna 在独立 checkout 集中验收。普通实现选择由 Sol/Developer 决定，不逐项请求批准。

**Goal:** 交付不依赖目标机 Python、Node 或 Docker 的内部 App/DMG 候选，验证 C24/C25 与离线生命周期。

**Architecture:** 继续使用唯一 FastAPI 和已有 React WebUI；发布模式由同一 loopback 服务提供最新构建的静态资源。薄 Swift 壳仅管理自有后端进程、窗口、目录选择和安全会话交接。后端采用完整内置 Python 运行环境或冻结的单目录分发，选择依据记录官方资料和实际可搬迁验证。

**Spec:** PRODUCT-SPEC、全 v1 计划 M4.1、ACCEPTANCE C24/C25、WORKSPACE-v1、API-v1，加本次用户授权。

## 全局约束

- 基线 e0ce04fe9f5ad933f2e7a4b2229c61fd9f2076af；main 保持不动，开发分支 codex/m41-internal-app-20261013。
- 新内部 bundle 名称、标识和默认 profile 与旧 App 隔离；不安装到 /Applications，不触碰真实 Keychain、账户或工作库。
- token 只在本次进程内传递，不能写 URL、包、日志；业务 Bearer 门保留，不能以本机访问替代认证。
- 只清理自有子进程；禁止按名称、端口或无身份 PID 文件杀进程。服务启动失败和端口占用必须 fail closed。
- 包内记录 SHA、dirty、build、前端指纹和锁文件/依赖信息；每次强制构建前端；实际实例须与包匹配。
- 不改变语料批准、真实调用 opt-in、未知动作禁止重发及工作库本地状态分离规则。
- App/DMG 是内部未公证候选；真实签名、公证、用户现场安装、M4.2、五日与双机单独 NOT_RUN。

## 连续实施步骤

### 1. 运行模式与安全交接

责任文件：src/summit_everything 下发布启动模块、API 静态挂载/身份接口；web/src/api 与 SSE 调用的会话头处理；tests 中对应集成反例。

- [ ] 先用最小集成用例证明：无 Bearer 写入拒绝、恶意 Origin 拒绝、静态文件无 token、非法资源路径拒绝、health 身份匹配。
- [ ] 实现发布入口：只绑定 127.0.0.1、提供静态 WebUI、使用限定 allowlist；Swift 在受信页面加载前交接临时 Bearer，所有 API/SSE 请求统一带头。
- [ ] 对 Markdown/资料命令、合成凭据故障和错误脱敏运行既有反例；新增边界先 red 再 green。

### 2. 原生生命周期与打包

责任文件：native/Sources/SummitEverythingApp/ 生命周期和 WebView；scripts/build-macos-app.sh、release-macos.sh 及必要打包模块；pyproject/uv.lock 仅必要构建依赖；CI；tests 打包/退出反例。

- [ ] 构建独立 SummitEverything Internal.app，内置运行依赖和最新 WebUI，失败不留下成功标记，禁止覆盖已有产物/安装。
- [ ] 原生启动只运行 bundle 后端；校验 readiness 的 run/build/frontend 身份，拒绝错误服务；稳定本机 profile，保留工作库身份隔离。
- [ ] 测试首启、正常退出、关最后窗口、重开、自有服务清理、其他服务存活、端口占用、启动失败、延迟 readiness、SSE 取消/断流、中断恢复。
- [ ] 复现 run_dev Ctrl+C PermissionError，评估并修复相关根因；正式 App 必须单独实测。
- [ ] 将 App 复制到隔离临时目录并清空开发 PATH 实际启动，制作/挂载/只读验证内部 DMG；不修改旧应用。

### 3. 集成自测与交接

责任文件：README、PROGRESS、LATEST-IMPLEMENTATION、TESTER、新 DEV 报告、安装说明、证据 manifest。旧 QA 原件不改。

- [ ] 跑 README guarded pytest、ruff、mypy、lock/build、Web tests/typecheck/lint/build、API types 一致性、Swift build 及本轮实际 App/DMG harness，记录退出码。
- [ ] 用实际 UI 在临时库完成目录选择、粘贴/文件导入、确认、索引、问答；重启复核知识与本地历史状态，工作库不得有 SQLite/凭据/日志。
- [ ] 实现和自测完成后固定源码 SHA；从 clean SHA 重建最终候选；证据提交与受测源码 SHA 分开说明。
- [ ] QA handoff 必须含固定 SHA、实际产物路径/摘要、精确命令、场景覆盖、退出码与 NOT_RUN；不得宣称 DEV 等于独立 PASS。

## 独立 QA 和 Sol 门

全新 custom qa 在固定 SHA 的独立 checkout：复跑回归，独立重建或核对身份并启动可搬迁 App/DMG；实际 UI 与 C24/C25 黑盒反例记录 PASS/FAIL/BLOCKED/NOT_RUN，不修改实现或 tracked tests。首次 FAIL 后最多两轮 Developer 修复+新 SHA+fresh QA。Sol 核验日志、退出码、manifest、diff 和身份，维护当前入口。M4.1 重要里程碑合并与正式收口需用户批准；整个 M4 不得提前 PASS。
