# M4.1 Internal App/DMG Developer 修复轮 1

## 结果

本轮修复初次独立 QA 在旧产品 SHA `b9321d64c5404feadffebc05964793e9402a07aa` 发现的 M41-QA-001：macOS WKWebView 的 HTML 文件上传入口没有原生面板。实现者提交了新产品源码 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 并从该 clean SHA 重建 App/DMG。开发者随后在用户解锁屏幕后完成了真实原生 UI 复演，文件面板、取消、TXT/MD 选择及 Fake 导入/批准/索引/问答闭环均有观察证据；**这只是开发者自测，Sol 仍需 fresh QA 独立验收，不代表 M4.1/M4 通过。** 初次锁屏阻塞记录保留在 evidence 的 `ui-blocker.txt`。

没有尝试自动解锁、读取系统凭据或调用真实服务。所有 UI 操作只使用本轮创建的隔离 profile、工作库和合成 TXT/MD。

## 变更

Swift `WKUIDelegate` 现实现 `webView(_:runOpenPanelWith:initiatedByFrame:completionHandler:)`。上传面板只允许 TXT/MD 文件，按 `WKOpenPanelParameters.allowsMultipleSelection` 设置选择数量，拒绝目录请求和不符合规则的返回值；取消、未受信 frame 或无效选择向 WebKit 返回 `nil`，completion 只调用一次。共享 frame 策略要求实际委托 WebView、main frame、`http://127.0.0.1:18793` origin、frame request URL 和当前 page URL 都逐项匹配；`localhost`、外部 frame/page、credentials URL、错端口均拒绝。工作库目录桥接器复用此 trusted-main-frame 检查，保留原来的目录选择 UI。来源 Markdown 只作为内容处理，策略不解析或执行其命令。

`native/Tests/NativeUploadPolicyTests` 覆盖允许的 TXT/MD 类型、可信 frame 与 URL、拒绝反例、取消空列表、单选拒绝多文件及多选参数；README 与独立测试手册列出 `swift test --package-path native`，CI 加入该命令。CI checkout 改为完整历史，以保证 CFBundleVersion 使用的 commit count 与本机一致。

## 固定源码与候选身份

- 产品源码 SHA：`3f6eaa408a8860ff5a438be8a874a2c3904733e4`，提交 `Fix Internal app file upload picker`。其后文档/证据提交不改变产品源码树；候选 build manifest 的 `dirty` 为 `false`。
- 架构与宿主：仅 arm64；本机 macOS 27.0.1。包声明最低 macOS 13.0，但 Intel 和更低系统实际兼容性均 NOT_RUN。
- `.app`：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app`。
- `.app` 目录摘要（排序相对路径 + NUL + 文件内容 SHA-256）：`1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb`，156 个文件；主 executable SHA-256：`b23fa16046cfe39c1aa8885f08b6bbbfe1b90e0d9744919f91f950e42f60cc64`。
- DMG：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything-Internal-fix1-3f6eaa4.dmg`；SHA-256：`554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8`。
- manifest：`app_version=0.1.0`，`build_id=20261013T060945Z-577f0cc805f2`，`source_sha=3f6eaa408a8860ff5a438be8a874a2c3904733e4`，`dirty=false`，frontend SHA-256 `577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`，dependencies SHA-256 `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。
- bundle：`com.summiteverything.internal`；签名只用于本地 adhoc 完整性验证，未使用 Developer ID 或公证。

新候选由 `scripts/release-macos.sh` 强制重建前端、onedir 后端和 Swift 壳。命令完整输出、逐命令 exit、artifact identity、隔离 harness 与失败尝试见[修复轮 1 evidence](evidence/2026-10-13-m41-repair1/README.md)。候选二进制不会提交到 Git。

## 开发自测结果

| 检查 | 结果 |
|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q` | PASS，499 passed，1 个 Starlette/httpx 弃用警告，exit 0 |
| `npm --prefix web test` | PASS，56 tests，exit 0 |
| `swift test --package-path native` | PASS，3 tests，0 failures，exit 0 |
| `swift build -c release --package-path native` | PASS，exit 0 |
| `uv run --locked ruff check src tests`、`ruff format --check`、`mypy src`、`uv lock --check` | PASS，各 exit 0 |
| M4.1 `scripts/release-macos.sh <new .app> <new .dmg>` | PASS，clean SHA 强制重建，exit 0 |
| `codesign --verify --deep --strict <new .app>`、`hdiutil verify <new .dmg>`、`lipo -archs` | PASS，各 exit 0；arm64 |
| `SUMMIT_APP=<new .app> uv run --locked python scripts/smoke_packaged_app.py` | PASS，空 PATH 下内置 onedir、身份、静态入口、匿名读写拒绝、端口冲突和 pipe EOF 清理，exit 0；此项是 backend smoke，不是 UI 复演 |
| 隔离 native App 实际启动/readiness/父中断 | PASS：复制候选至 `DARWIN_USER_TEMP_DIR`，设置独立 `SUMMIT_INTERNAL_TEST_PROFILE_ROOT`，health 的源码/dirty/build/frontend/dependency 与候选 manifest 相符；仅终止本测试父进程后，自有 backend child 与 18793 listener 清理，exit 0 |
| 隔离 copied bundle 前端资源篡改 | PASS：复制包的 Web `index.html` 增加合成字节后，实际内置 backend 以 exit 1 fail closed；最终候选未改，exit 0 |
| native 延迟 readiness | PASS（合成 backend）：临时 bundle 副本中的 fake backend 延迟监听 4 秒，再返回本次 run ID 与候选 identity；App 先检查 health，之后才请求 `/`，exit 0。该场景不替代真实 backend 延迟和 UI 观察 |
| native missing-backend | 部分 PASS：临时复制包缺失 backend 时 18793 没有 readiness 服务；启动错误 modal 因锁屏未观察，故 UI 提示 `NOT_RUN`。测试过程只以 SIGTERM 结束自有 App，exit 0 |
| live HTTP SSE 取消 / 客户端断流 / reopen 与敏感错误回显回归 | PASS，`tests/integration/test_http_sse_lifecycle.py` 与 `test_release_app.py` 共 6 tests，exit 0；保留真实 FastAPI/QueryService/IndexStore/SQLite/TCP，只有 AnswerProvider 合成。credential-sentinel 响应检查及 loop exception handler 均未泄漏/报错 |
| native 文件面板实际 UI、取消、TXT/MD 逐字节核对与 Fake 导入/确认/索引/问答 | PASS（开发者实际 UI 观察，非独立验收）：取消后收件箱 0；TXT 67 bytes、MD 124 bytes 均进入待整理，原件 SHA 与输入一致；Fake 整理和逐条批准后建 2 页索引，两条查询均显示可用引用。完整观察见 evidence `logs/native-ui-observations.txt` |
| Cmd+Q 快捷退出 | NOT_RUN/PASS 边界：快捷键尝试未退出；改用 App 菜单 Quit 正常退出，shell 确认两个自有 PID 与 18793 listener 消失 |
| valid Bearer 的完整 API、诊断与运行日志脱敏矩阵 | NOT_RUN；本轮只复跑 tracked 合成 API/SSE 错误回显与 access log sanitizer tests |
| 远端 GitHub Actions | NOT_RUN；本地改了 workflow 但未触发远端 runner |
| 真实模型、Feishu、真实材料、系统 Keychain、用户安装、旧 App 覆盖、Developer ID/公证、Intel、macOS 13、M4.2、五日、双机、发布 | NOT_RUN / 本轮范围外；runtime 模型配置元数据仍 UNVERIFIED |

本轮隔离测试使用的临时目录都位于本机 `DARWIN_USER_TEMP_DIR`。不读取或写入默认 Internal profile、旧 App 或真实业务资料；不调用真实外部服务，不触碰 Keychain，不安装至 `/Applications`。最后检查没有本轮 App/backend 进程或 18793 listener 留存。

## QA 有界交接

请 fresh QA 对固定源码 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 建立独立 checkout，核对上列绝对产物路径、摘要和 tracked evidence manifest。独立复验：真实 NSOpenPanel 的 cancel 与 TXT/MD 选择、字节对照及 pending 状态；恶意 frame/page 与单选约束；Fake 整理确认、逐条批准、索引及引用；并完成验收手册要求的剩余离线生命周期/API/SSE矩阵。使用自己的隔离临时 profile 与合成材料。开发者观察和启动 harness 仅作辅助证据，不替代 QA。

Sol 为本轮 gate owner。旧 SHA `b9321d6` 的 M41-QA-001 仍为对应旧候选的历史 FAIL；新 SHA 的修复仅有开发者 UI 自测，待 fresh QA 实际判断。复修轮数按 Sol 调度；本报告不批准 merge，也不对产品门作最终 PASS 判断。
