# M4.1 Internal App / DMG Developer 交接

## 固定目标与状态

- 受测产品源码 SHA：`b9321d64c5404feadffebc05964793e9402a07aa`，分支 `codex/m41-internal-app-20261013`，当时 `dirty=false`。实现提交是 `feat: build internal macOS app candidate`；此报告后续单独提交，不改变受测产品 SHA。
- 本报告仅记录 Developer 实测，不是独立 QA 结论或 M4.1 阶段通过判定。Sol 的 fresh QA：`NOT_RUN`。
- 主机：arm64 macOS 27.0.1。候选构建设置为 arm64、macOS 13 minimum；Intel、macOS 13–26 未实测。
- 构建使用 PyInstaller `--onedir`（官方模式说明：[PyInstaller operating modes](https://pyinstaller.org/en/stable/operating-mode.html)）。只使用 ad-hoc 签名。未安装到 `/Applications`，未做 Developer ID、真实签名账户或公证；DMG 只做只读挂载检查，不代表实际用户安装。

## 固定产物身份

- App：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app`
- App 目录摘要（相对路径 + NUL + 文件内容 SHA-256 的排序摘要）：`96face5e21c4d237018bc86e8ab89d74651ac4bad5caaea653580a93475def73`，156 个文件。
- DMG：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/artifacts/SummitEverything-Internal-M4.1-b9321d6.dmg`
- DMG SHA-256：`1822e655836d591dcc612f6de4dfeda095dc16bd8e194e87e33cf5b5894c72fd`。
- manifest：`source_sha=b9321d64c5404feadffebc05964793e9402a07aa`，`dirty=false`，`app_version=0.1.0`，`build_id=20261013T052105Z-577f0cc805f2`，`frontend_sha256=577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`，`dependencies_sha256=2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。
- 包内前端重新计算指纹与 manifest 完全一致；`CFBundleIdentifier=com.summiteverything.internal`、`CFBundleVersion=227.0.0`、架构 `arm64`、`SummitBuildID` 与 manifest 一致。
- 确切 clean-SHA 构建命令（在仓库根目录）：`scripts/release-macos.sh "$PWD/.local/dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app" "$PWD/.local/dev/m41/artifacts/SummitEverything-Internal-M4.1-b9321d6.dmg"`，exit 0。构建强制重建前端，在 staging 中完成 app 签名校验、DMG 创建/验证/只读挂载校验后才产出目标文件。

## 实测结果

| 检查 | 结果 | 证据与说明 |
|---|---|---|
| clean-SHA App + DMG 构建 | PASS，exit 0 | `.local/dev/m41/raw-logs/build-final-b9321d6.log`；输出仅在被忽略的 `.local` 下 |
| 最终 App 签名结构校验 | PASS，exit 0 | `codesign --verify --deep --strict "/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app"`；仅 ad-hoc |
| DMG 校验 | PASS，exit 0 | `hdiutil verify "/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/artifacts/SummitEverything-Internal-M4.1-b9321d6.dmg"`，内含只读挂载、App 存在与签名检查；未执行安装 |
| 可搬迁后端 smoke | PASS，exit 0 | `SUMMIT_APP="/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app" uv run --locked python scripts/smoke_packaged_app.py`；复制 bundle、空开发 `PATH`，验证服务身份、静态资源、未授权请求拒绝、固定端口冲突 fail-closed、父 pipe EOF 仅清理自有服务。日志区分此项为 backend smoke，不冒充 UI：`.local/dev/m41/raw-logs/packaged-backend-smoke-final.log` |
| 最终包真实原生窗口 / 前端 | PASS（有限 UI 路径） | 把上述 App 复制到真实 `DARWIN_USER_TEMP_DIR` 下，再以空开发 `PATH` 启动。SwiftUI 窗口内真实 WKWebView 打开 loopback 页面；创建隔离工作库；保存一条含 `echo SYNTHETIC_TEST_ONLY` 的合成文本为待整理，UI 显示计数 1 和“资料命令不会执行”；Cmd+Q 后自有 App/backend 和端口消失；同 profile 重开后连接既有库且待整理计数仍为 1；关闭最后窗口后进程与 listener 消失。详细观察、临时目录、PID 与命令结果见 `.local/dev/m41/raw-logs/native-ui-final-observations.txt`。未复演文件选择、审核稿确认、完整索引和问答 UI。 |
| 固定 profile / workspace 本地内容检查 | PASS（此隔离副本） | 根路径均在 `DARWIN_USER_TEMP_DIR`。库仅有 Markdown、manifest、sources 索引、事务记录和锁；无 SQLite、凭据或诊断日志。profile 的日志仅写一条合成 `intake_saved` 事件；不包含 token。 |
| guarded 后端完整测试 | PASS，499 passed，1 warning，exit 0 | `env PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked pytest -q`；`.local/dev/m41/raw-logs/guarded-pytest-final.log`。warning 是 Starlette `TestClient` 关于 httpx 的弃用提醒。 |
| 其它本地门 | PASS，exit 0 | `.local/dev/m41/raw-logs/gates-full.log`：Web 56 tests、Web typecheck/lint/build、OpenAPI types 生成后无 diff、`uv build`、Swift release build；`.local/dev/m41/raw-logs/final-static.log`：ruff、format、mypy、`uv lock --check`、`git diff --check`；`.local/dev/m41/raw-logs/swift-build-final.log`：`MACOSX_DEPLOYMENT_TARGET=13.0 swift build -c release --package-path native`。Web lint 有两条 `set-state-in-effect` warning，命令 exit 0。 |
| 真实 HTTP SSE cancel / disconnect / reopen 与异常消费 | PASS，修复后 focused test exit 0 | `uv run --locked pytest -q tests/integration/test_http_sse_lifecycle.py`；使用真实 QueryService、IndexStore / SQLite、真实 route/server 和合成可取消 AnswerProvider。旧实现失败并由 loop exception handler 捕获 `Task exception was never retrieved`；原始 red 与修复后 green 留存于 `sse-real-query-exception-red.log` / `sse-real-query-exception-green.log`。cancel 终态、断流恢复/重开、task exception 消费均由 tracked `tests/integration/test_http_sse_lifecycle.py` 覆盖。 |
| 开发 runner 启动期 Ctrl+C | PASS（回归实现） | 从基线 `2c4e479:scripts/run_dev.py` 复现启动中断，shell exit 241；没有复现历史 `PermissionError`。修复后 tracked runner 测试 4 passed、exit 0，受控子进程路径退出为 0。两份证据：`dev-runner-ctrl-c-baseline.log`、`dev-runner-ctrl-c-green.log`。不声称已证实历史 PermissionError 根因。 |
| 远端 CI | NOT_RUN | workflow 已加入，但本轮没有 GitHub Actions 运行结果。 |

完整构建 / 输出验收摘要在 `.local/dev/m41/raw-logs/final-artifact-verification.log`。早期完整 gate 曾发现 5 个已知 workspace/conflict 错误信息在安全脱敏时被泛化；实现改为固定安全消息映射后最终 499 测试通过。初始失败日志保存在 `.local/dev/m41/raw-logs/gates-full.log`，没有删除或放宽测试。

## 安全与边界记录

- 服务绑定 loopback；Bearer 认证仍在。发布资源由唯一 FastAPI 提供；Swift 只在 readiness 身份和资源校验后向精确本机 trusted main frame 注入每次启动的新 token。WKWebView 使用非持久数据存储，导航和目录桥接有来源限制；Ask SSE 复用 API session headers。token 未记录或写入 URL / build manifest。
- 只替换本地合成 AnswerProvider；没有读取真实账户、真实 Feishu、业务材料、OS Keychain 或付费模型。C24/C25 对 Markdown 安全、未授权写拒绝、命令文本不执行、日志凭据脱敏有自动化回归，但整项独立黑盒验收仍交 QA；不据此声称 C24/C25 全部 PASS。
- 首轮 CUA 尝试曾在新的 `SummitEverything Internal` 默认 Application Support profile 保存合成 UI 状态；它与旧 app 使用不同 bundle/profile。本轮没有读取旧 App、旧凭据、真实材料或真实 Keychain，已生成的合成状态原样保留。之后最终固定候选的 UI 测试严格使用 `DARWIN_USER_TEMP_DIR` 下的 profile/workspace。此边界偏离记录供 QA/Sol审查。
- runtime 模型配置元数据没有实际暴露：`UNVERIFIED`。真实 Feishu OAuth/callback、真实 provider / 模型质量、OS Keychain、Intel 与低版本 macOS、真实用户安装、签名身份、公证、五日、双机、M4.2 与发布全部 `NOT_RUN`。

## QA handoff

QA 请固定在产品 SHA `b9321d64c5404feadffebc05964793e9402a07aa` 独立 checkout 复验，不把本报告或 Developer 自测当作 QA 结论。优先核验：包内身份/静态指纹 tamper fail-closed；首次启动、正常退出、最后窗口退出、重开、强制父进程中断、服务失败/延迟 readiness、固定端口冲突不影响他服务；真实 SSE cancel/disconnect/reopen 与 task exception capture；WKWebView 来源与目录桥接；C24/C25 的 loopback、Bearer、Markdown/命令与日志脱敏；迁移副本 UI 保存/重开和 profile 隔离。实际 UI 文件选择、整理确认、索引问答，本轮 `NOT_RUN`。外部 OAuth、真实材料、OS Keychain、正式安装/签名/公证、低版本/Intel、CI 和 M4.2 按上表继续 `NOT_RUN`。
