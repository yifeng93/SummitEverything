# 设置 UX 与内置非秘密默认值：DEV 报告

分支 `codex/settings-ux-20261014`。固定产品源码 SHA `e4f15cdfe54be2e8b2b426d9b440eecf2b5ff7e9`（`build: allow opting out of the SwiftPM manifest sandbox`）。本报告由 Sol 编写并执行，不是独立 QA 结论；独立验收见后续 QA 报告。

## 范围与决议

用户 2026-10-14 要求按旧项目 SummitWorkbench 的配置方式重做首次配置，并「不要再让我填 Base URL、callback、App ID，只输入密钥」。决议记录于 [ADR 0010](../../decisions/0010-first-use-configuration-ux.md)，产品范围同步进 [PRODUCT-SPEC](../../product/PRODUCT-SPEC.md)。未改变：默认 Fake、真实调用需一次性范围预览与独立确认、飞书任务写禁用、密钥不打入安装包或仓库。

## 产品改动

- 设置页改为三张卡（工作库 / AI 模型 / 飞书）+ 状态徽章；技术字段收进「高级与自定义」。飞书徽章来自真实本地状态接口 `GET /api/v1/integrations/feishu/status`，只有 `credential_error=credential_unreadable` 才显示「需重新授权」；读取失败不假设已授权，且不计入检查额度。
- 新增 5 步首次配置向导（模型与地址 → 录入密钥 → 检查连接 → 飞书 → 完成），每步可跳过；密钥只存在于组件内存，提交后清空，不写任何持久化；向导打开、切步、退出不产生 provider 请求。
- 连接检查保持显式确认：确认面板写明固定短合成 payload、不发送工作库材料、本次占用 1 次、累计已用 x/1 且跨运行不重置、失败超时同样计数且不自动重发。
- 非秘密接入值（`feishu_app_id`、`feishu_redirect_uri`、`embedding_base_url`、`rerank_base_url`）改由本机忽略文件在构建时注入包内 `Resources/first-use-defaults.json`；运行时只认 `SUMMIT_FIRST_USE_DEFAULTS` 显式路径与包内资源，**没有仓库隐式回退**（避免测试结果依赖开发机上的文件）。开发预览由 `scripts/run_dev.py` 显式 opt-in。
- 注入加载 fail closed：显式路径不可读、secret 形态键名、未知键、值不合法都报错且错误文本不含值；校验沿用原 validators。
- 保存语义：profile 只记录**用户显式覆盖**；提交值等于当前注入默认值时删除该键而不是写 `""`（写 `""` 会被 base URL validator 拒绝）。换构建/换注入后，未覆盖过的 profile 跟随新默认值。
- 百炼地址采用官方推荐的业务空间专属域名，依据阿里云百炼[地域及接入域名](https://help.aliyun.com/zh/model-studio/beijing-access-information)；`dashscope.aliyuncs.com` 仅作为无注入时的回退默认。

## 真实命令与退出码（本机 arm64、macOS 27.0.1）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `PYTHONPATH=...offline_guard:src uv run pytest -q` | 0 | **558 passed**, 1 warning |
| `uv run ruff check src tests` | 0 | All checks passed |
| `uv run ruff format --check src tests` | 0 | 91 files already formatted |
| `uv run mypy src` | 0 | no issues in 46 source files |
| `uv lock --check` | 0 | — |
| `scripts/export_openapi.py` + `git status web/openapi.json web/src/api/generated.ts` | 0 | 逐字节一致，契约未变 |
| `npm test`（web） | 0 | 14 files / **90 passed** |
| `npm run typecheck` | 0 | — |
| `npm run lint` | 0 | 2 warnings（既有 `ProjectsView.tsx:40`、`TodayView.tsx:80`），0 errors |
| `npm run build` | 0 | 34.77 kB CSS / 365.68 kB JS |
| `scripts/release-macos.sh <app> <dmg>` | 0 | 完整打包成功，DMG `hdiutil verify` CRC VALID |
| `scripts/smoke_packaged_app.py` | 0 | PASS（身份、静态 UI、未授权读写、端口冲突、父进程管道清理） |
| `.local/verify-packaged-defaults.py` | 0 | **23/23 checks passed** |

`SUMMIT_FIRST_USE_DEFAULTS` 注入的「有/无本机文件」两次全量对比各为 558 passed / exit 0，证明无隐式依赖。A/B 由 Developer 执行、Sol 复核；其余均为 Sol 本机执行。

打包时的环境适配（不改默认行为）：`SUMMIT_SWIFT_DISABLE_SANDBOX=1` 让 SwiftPM 在内层沙箱环境下跳过 manifest 沙箱（默认与 CI 不变，已单独提交 `e4f15cd`）；`PYINSTALLER_CONFIG_DIR` 与 `UV_CACHE_DIR` 指向工作区内目录以避开外层沙箱限制。

## 包内注入端到端验证（23/23）

针对冻结后的包（不是源码树）：① 包内 `Resources/first-use-defaults.json` 存在且与本机来源文件等值；② 打包后端启动后 `GET /settings` 返回四个注入值；③ 提交这四个值保存后，profile 的 `provider-settings.json` 中四个键**不存在**（不固化）；④ 同一 profile 换一个注入文件重启后，四个字段跟随新默认值；⑤ 注入文件含 `deepseek_api_key` 时打包后端**拒绝启动**（非零退出）。DMG 挂载后包内同样带有该文件，`build-info.json` 的 `source_sha` 与受测 SHA 一致。

## 候选身份

- App：`.local/internal-builds/settings-ux-e4f15cd/SummitEverything Internal.app`（157 个文件）
- DMG：`.local/internal-builds/settings-ux-e4f15cd/SummitEverything-Internal-e4f15cd.dmg`
- DMG SHA-256：`ce79a8c355c89e420606e3882b918b6dd9c993009b3df633bc25c52df5a0d68c`
- `build-info.json`：`source_sha=e4f15cd…`、`dirty=false`、`build_id=20261014T132453Z-0d21a90f194c`、`app_version=0.1.0`、`frontend_sha256=0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0`、`dependencies_sha256=2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`

后续 docs-only 提交不改变受测产品 SHA；候选为 ad-hoc 本地签名、未公证。

## 未验证 / 边界

- 真实 provider、真实飞书账户与 OAuth/scope、真实业务材料、真实账单与答案质量、正式用户安装/覆盖、Developer ID 与公证、Gatekeeper 接受、五日试用、双机（M5）与发布：**NOT_RUN**。runtime 模型元数据 **UNVERIFIED**。
- macOS Keychain 生命周期仍 **NOT_RUN**。包内验证中的 `GET /settings` 会做只读的凭据存在性查询，本机未保存过该命名空间下的凭据；本轮没有写入钥匙串、没有使用任何真实密钥，这不构成 Keychain 验收。
- 新界面/向导**未做浏览器或真机视觉复核**：只有组件测试与构建产物证据，没有人工或真实浏览器会话观察。
- 旧 profile 迁移残留：若某 profile 在本功能之前保存过，其落盘值可能是当时的内置公共端点；`read()` 视非空存储值为显式选择，因此不会自动跟随新的注入默认值，需要用户在高级设置里清空该字段一次。首次真实配置若新建工作库则不受影响。
- `spctl` 结论沿用历史：ad-hoc 包 exit 3 / rejected，未绕过系统安全设置。

## 相关文件

- [ADR 0010](../../decisions/0010-first-use-configuration-ux.md)、[PRODUCT-SPEC](../../product/PRODUCT-SPEC.md)、[M42 readiness](../../handoff/M42-PACKAGE-A-READINESS.md)
- 实现：`web/src/components/{SettingsView,FirstUseWizard,SmokeCheckConfirm,settingsBadges}.tsx|ts`、`src/summit_everything/integrations/first_use_defaults.py`、`settings.py`、`scripts/{build_macos_app,run_dev}.py`
- 提交：`a6faf7e`（docs）、`4c27238`（web）、`ff4d8aa`（config 注入）、`e4f15cd`（构建沙箱 opt-in）
