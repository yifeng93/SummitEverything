# 设置 UX 与内置非秘密默认值：DEV 报告

分支 `codex/settings-ux-20261014`。**固定产品源码 SHA `8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b`**（`fix(config): never repair a corrupted settings field by injection`）；其后另有仅测试的 `ea90828`（测试隔离）与 docs 提交，均不改变产品树。本报告由 Sol 编写并执行；独立验收由三轮全新 QA 完成，见下文「独立 QA 复核」。

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
| `PYTHONPATH=...offline_guard:src uv run pytest -q` | 0 | **591 passed**, 1 warning（两侧一致，见下） |
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

测试隔离：全量在 `SUMMIT_FIRST_USE_DEFAULTS` **已导出**（指向本机注入文件）与**未导出**两种 shell 下均为 591 passed / exit 0。这一对 A/B 是有意义的，因为 QA 的 F3 证明过：修隔离之前，导出该变量会让 33 个无关 Feishu 测试失败。**更正**：本报告早先版本曾用「有/无本机文件两次各 558 passed」声称证明无隐式依赖——那次对比从未设置该变量，因此覆盖不到这个情形，该结论已作废。开发期的 A/B 由 Developer 执行、Sol 复核；上表其余命令与下节包内验证均由 Sol 在本机执行。

打包时的环境适配（不改默认行为）：`SUMMIT_SWIFT_DISABLE_SANDBOX=1` 让 SwiftPM 在内层沙箱环境下跳过 manifest 沙箱（默认与 CI 不变，已单独提交 `e4f15cd`）；`PYINSTALLER_CONFIG_DIR` 与 `UV_CACHE_DIR` 指向工作区内目录以避开外层沙箱限制。

## 包内注入端到端验证（27/27）

针对冻结后的包（不是源码树）：① 包内 `Resources/first-use-defaults.json` 存在且与本机来源文件等值；② 打包后端启动后 `GET /settings` 返回四个注入值；③ 提交这四个值保存后，profile 的 `provider-settings.json` 中四个键**不存在**（不固化）；④ 同一 profile 换一个注入文件重启后，四个字段跟随新默认值；⑤ 注入文件含 `deepseek_api_key` 时打包后端**拒绝启动**（非零退出）；⑥ **section 级**（`embedding` 写成字符串）与**字段级**（`embedding.base_url` 写成数字）两种损坏 profile 都不被静默接受（非 200）。DMG 挂载后包内同样带有该文件，`build-info.json` 的 `source_sha` 与构建时 HEAD 一致。

## 独立 QA 复核

三轮全新 QA 分别在独立 worktree 对固定 SHA 验收，报告逐字归档在 [证据目录](evidence/2026-10-14-settings-ux-qa/README.md)：

- **第一轮（`e4f15cd`）**：身份、全量 558、静态检查、前端 90、契约未变、注入语义黑盒 26 项、前端证伪 7 项、候选哈希与冻结端到端全部 PASS；「向导导航零 provider 请求」「取消不发请求」「密钥不进任何持久化」三条主张未被证伪。发现 **D1**（section 级损坏被注入掩盖，有注入时比无注入宽松）。
- **第二轮（`6d41d35`）**：D1 确认修复（同一 harness 在只读导出的旧源码树上 56 failed / 36 passed 作为对照），其余全项 PASS（全量 561、前端 90、包内 defaults 逐字节一致、DMG 挂载复核、冻结端到端 19/19）。发现 **F1**（字段级同类不对称）与既有 **F2**；并指出「逐项 PASS」不能推广为「注入永不比无注入宽松」。
- **第三轮（`8c4f81c`）**：F1 确认修复（自建 149 项全绿；同一字节 harness 在旧树 `6d41d35` 上 72 项失败，恰为「有注入」的 store/API/handler 三类），D1 回归 66/66，注入语义 38/38 与边界 21/21，全量 591，前端 90（lint 2 条 warning 经功能前树复现判为既有），候选 DMG 哈希、包内三方等值与 manifest 指纹、smoke 全部 PASS，冻结端到端 85/85（字段级损坏 20 组与 section 级 12 组均为 500、无一 200）。发现 **F3**（测试不固定注入源）。

- **第四轮（`ea90828`，仅测试提交）**：聚焦复核 F3 修复。导出注入源与未导出两种 shell 下**均 591 passed / exit 0**；同一 worktree 内对 `8c4f81c` 全树副本做的修复前对照为 `33 failed / 558 passed`（导出）与 591 passed（未导出），与第三轮数字一致，证明隔离 fixture 正是消除差异的原因。产品树在该提交区间零变化，候选 DMG 不受影响。该轮指出实现者两处表述不准（区间含一个未申报的 docs-only 提交；引用 `create_app` 的测试模块实测 22 个而非 23 个），并指出 fixture 作用域为目录级——Sol 裁决保持现状并记录：`testpaths` 已完整覆盖，上移根级会扩大到被忽略的临时 harness。

D1、F1、F3 均已修复并经后续独立 QA 复核。**F2 未修复**，见下节。

## 已知开放问题

- **F2（既有，未修）**：`origin_guard` 中间件直接读取 profile 设置且无异常处理（[app.py:508-516](../../../src/summit_everything/api/app.py#L508-L516)），profile 损坏时抛出裸 500，绕过已注册的 `SettingsError` 处理器（本应返回 JSON 503）。实际影响是 profile 一旦损坏，**连用于修复的 PATCH 也返回 500**，只能手改文件。该形态在功能前提交 `a6faf7e` 上同样存在，与本功能无关；现有测试没有任何一条断言该 500，因此修复面小，但属于中间件行为、应作为独立切片实施与验证。
- **O1（既有，低危）**：手写 `{"llm":{"provider":"deepseek"}}`（缺 `model` 键）被接受为 `model=None`；`embedding`/`rerank` 因使用 after-validator 而拒绝。经 PATCH 不可达。
- **O2（设计取舍）**：显式注入文件整体替换包内文件，不做按字段合并；只给部分键时其余字段退回内置默认值。
- **O3（已知呈现）**：启动期失败关闭表现为 PyInstaller 原始 traceback（exit 1，不泄露值）。

## 候选身份

- App：`.local/internal-builds/settings-ux-8c4f81c/SummitEverything Internal.app`（157 个文件）
- DMG：`.local/internal-builds/settings-ux-8c4f81c/SummitEverything-Internal-8c4f81c.dmg`
- DMG SHA-256：`966cf3ae278db6ab0d2c6f60629e63d4cc7b3f2bae9f977333e6682e753eaeab`
- `build-info.json`：`source_sha=76ca47d4…`（构建时的 docs 提交；`git diff --name-only 8c4f81c..76ca47d` 仅 ADR 一个文件，产品树与固定产品 SHA 相同）、`dirty=false`、`build_id=20261014T134528Z-0d21a90f194c`、`app_version=0.1.0`、`frontend_sha256=0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0`、`dependencies_sha256=2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`

前三轮候选（`e4f15cd`、`6d41d35` 与本节）为不同 SHA 的独立构建，旧候选仅作历史追溯。后续仅测试与 docs 的提交不改变本候选对应的产品树；候选为 ad-hoc 本地签名、未公证。

## 未验证 / 边界

- 真实 provider、真实飞书账户与 OAuth/scope、真实业务材料、真实账单与答案质量、正式用户安装/覆盖、Developer ID 与公证、Gatekeeper 接受、五日试用、双机（M5）与发布：**NOT_RUN**。runtime 模型元数据 **UNVERIFIED**。
- macOS Keychain 生命周期仍 **NOT_RUN**。包内验证中的 `GET /settings` 会做只读的凭据存在性查询，本机未保存过该命名空间下的凭据；本轮没有写入钥匙串、没有使用任何真实密钥，这不构成 Keychain 验收。
- 新界面/向导**未做浏览器或真机视觉复核**：只有组件测试与构建产物证据，没有人工或真实浏览器会话观察。
- 旧 profile 迁移残留：若某 profile 在本功能之前保存过，其落盘值可能是当时的内置公共端点；`read()` 视非空存储值为显式选择，因此不会自动跟随新的注入默认值，需要用户在高级设置里清空该字段一次。首次真实配置若新建工作库则不受影响。
- `spctl` 结论沿用历史：ad-hoc 包 exit 3 / rejected，未绕过系统安全设置。

## 相关文件

- [ADR 0010](../../decisions/0010-first-use-configuration-ux.md)、[PRODUCT-SPEC](../../product/PRODUCT-SPEC.md)、[M42 readiness](../../handoff/M42-PACKAGE-A-READINESS.md)
- 实现：`web/src/components/{SettingsView,FirstUseWizard,SmokeCheckConfirm,settingsBadges}.tsx|ts`、`src/summit_everything/integrations/first_use_defaults.py`、`settings.py`、`scripts/{build_macos_app,run_dev}.py`
- 提交：`a6faf7e`（docs）、`4c27238`（web 卡片+向导）、`ff4d8aa`（config 注入）、`e4f15cd`（构建沙箱 opt-in）、`6d41d35`（D1 修复）、`8c4f81c`（F1 修复，固定产品 SHA）、`76ca47d`（ADR 补充）、`ea90828`（测试隔离 F3，仅测试）
- 本报告早先版本以 `e4f15cd` 为固定 SHA 且包含一条已被推翻的「无隐式依赖」结论，正文已就地更正并保留更正说明。
