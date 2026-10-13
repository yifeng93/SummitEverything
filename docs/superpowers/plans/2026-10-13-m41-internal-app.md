# M4.1 内部 macOS 应用集成开发计划

> 执行方式：按用户 2026-10-13 的明确授权，一个 Developer Luna 连续实现、自测和小逻辑提交；整包固定 SHA 后由全新 QA Luna 在独立 checkout 集中验收。普通实现选择由 Sol/Developer 决定，不逐项请求批准。

**Goal:** 交付不依赖目标机 Python、Node 或 Docker 的内部 App/DMG 候选，验证 C24/C25 与离线生命周期。

**Architecture:** 继续使用唯一 FastAPI 和已有 React WebUI；发布模式由同一 loopback 服务提供最新构建的静态资源。薄 Swift 壳仅管理自有后端进程、窗口、目录选择和安全会话交接。后端采用 PyInstaller `--onedir`，其应用目录包含 Python interpreter 和依赖；官方操作模式说明 onedir 可作为应用目录分发（https://pyinstaller.org/en/stable/operating-mode.html），本轮以无开发 PATH 的搬迁复演验证。

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

- [x] 用受保护 API / manifest / 资源测试证明：无 Bearer 写入拒绝、非法资源路径拒绝、health 身份匹配、静态资源与实际指纹一致；既有 Origin 限制回归仍须由 QA 对固定包黑盒复验。
- [x] 实现发布入口：只绑定 127.0.0.1、同服务提供静态 WebUI；Swift 校验健康身份和资源后才向受信主 frame 注入每次新 token，Ask 的 fetch SSE 与其它 API 共用 session headers。
- [x] 跑全量 Markdown / 资料处理 / 错误脱敏既有回归，并新增合成敏感哨兵、真实 HTTP SSE 任务异常捕获 red/green 测试；外部服务只替换为合成 provider。

### 2. 原生生命周期与打包

责任文件：native/Sources/SummitEverythingApp/ 生命周期和 WebView；scripts/build-macos-app.sh、release-macos.sh 及必要打包模块；pyproject/uv.lock 仅必要构建依赖；CI；tests 打包/退出反例。

- [x] 构建独立 SummitEverything Internal.app，内置 PyInstaller onedir 和强制重建 WebUI；staging 完成签名验证及可选 DMG 校验后才发布新输出，并拒绝覆盖。
- [x] 原生启动只运行 bundle 后端；校验 readiness 的 run/build/frontend/dependency 身份、响应类型和直达 URL；每 profile 加实例锁，自有 pipe EOF 清理后端。
- [x] 测试首启、正常退出、关最后窗口、重开、自有服务清理、其他服务存活、端口占用、启动失败、延迟 readiness、SSE 取消/断流、中断恢复。
- [x] 以基线 `2c4e479` 实测启动中 Ctrl+C 返回 shell exit 241；本轮没有复现历史 PermissionError。增加启动期间与服务 ready 后 Ctrl+C 子进程回归，runner 改为正确等待自有子进程退出；另单独复演正式 App 窗口退出。
- [x] 将最终 clean-SHA App 复制到隔离临时目录并以空开发 PATH 启动原生 UI；制作 / 挂载 / 只读验证内部 DMG。Dev 版 backend smoke 已独立跑通；最终包结果在 clean-SHA 产物和 QA handoff 补录。

### 3. 集成自测与交接

责任文件：README、PROGRESS、LATEST-IMPLEMENTATION、TESTER、新 DEV 报告、安装说明、证据 manifest。旧 QA 原件不改。

- [x] 在固定源码 SHA `b9321d64c5404feadffebc05964793e9402a07aa` 跑 guarded pytest、ruff、mypy、lock/build、Web tests/typecheck/lint/build、API types 一致性、Swift build 与最终 App/DMG harness，记录退出码；完整命令和 NOT_RUN 见 DEV 报告。
- [x] 用实际 UI 在临时库完成目录选择、粘贴/文件导入、确认、索引、问答；重启复核知识与本地历史状态，工作库不得有 SQLite/凭据/日志。
- [x] 实现和自测后固定源码 SHA；从 clean SHA 重建最终候选；证据提交与受测源码 SHA 分开说明。
- [x] QA handoff 含固定 SHA、实际产物路径/摘要、精确命令、场景覆盖、退出码与 NOT_RUN；独立 QA 尚未运行，不宣称 DEV 等于独立 PASS。

本轮实际复制候选并启动原生 WKWebView，在真实 `DARWIN_USER_TEMP_DIR` 隔离 profile/workspace 中创建库、保存合成收件项、正常退出、重开并确认收件状态恢复、关闭最后窗口并确认自有服务退出。文件选择、审核稿确认、完整索引与问答 UI 未由 Developer 本轮复演，留 QA 覆盖或明确记 NOT_RUN。端口冲突、父 pipe EOF、真实 TCP SSE cancel/disconnect/reopen、任务异常消费与开发 runner Ctrl+C 的具体证据见 [M4.1 DEV 报告](../../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)。

## 独立 QA 和 Sol 门

全新 custom qa 在固定 SHA 的独立 checkout：复跑回归，独立重建或核对身份并启动可搬迁 App/DMG；实际 UI 与 C24/C25 黑盒反例记录 PASS/FAIL/BLOCKED/NOT_RUN，不修改实现或 tracked tests。首次 FAIL 后最多两轮 Developer 修复+新 SHA+fresh QA。Sol 核验日志、退出码、manifest、diff 和身份，维护当前入口。M4.1 重要里程碑合并与正式收口需用户批准；整个 M4 不得提前 PASS。


## 当前执行结果

固定源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 的 fresh QA 和 Sol 适用离线技术门 PASS；初验文件面板 P1 经自动修复 1/2 轮关闭。原始 FAIL 与全部证据保留。正式里程碑收口 / 合并等待用户批准；真实安装、签名公证、OS Keychain、M4.2、五日、双机和发布未测。见 [Sol 门](../../quality/reports/2026-10-13-M41-SOL-GATE.md)。
