# 最新实现交接

## 当前前端 UX：B repair1 离线门通过，C 实施中

B repair1 产品固定 SHA `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`（`codex/frontend-ux-20261015`）经独立 QA 与 Sol 核验，适用离线核心及 repair1 两项修复 **PASS**；初始产品 `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` 的首次 QA **FAIL** 原件仍保留。此 gate 只覆盖 B 离线范围，不代表全站、C/D、Stage C 或产品整体 PASS。QA 报告与脱敏 hash 索引见[B QA repair1](../quality/reports/2026-10-15-FRONTEND-B-QA-REPAIR1.md)及[QA evidence](../quality/reports/evidence/2026-10-15-frontend-b-repair1-qa/README.md)；原 DEV 报告和开发 evidence 保留。Web 180 passed / 6 todo；typecheck/lint/build、离线 Playwright 2/2、FastAPI/Fake 1/1、Real frozen scope/focus 1/1 exit 0；Python 661 与 QA mutation 未运行。全站 todo、真实 provider/飞书/OAuth/Keychain、用户材料、DMG/安装/公证、五日和双机仍 NOT_RUN。

当前 C 唯一 writer 在 `codex/frontend-ux-20261015` 实现树，产品基于上述 B 固定 SHA，工作树仅允许串行修改。C 范围为项目列表/独立详情及返回状态、question-first Ask 安全流式 Markdown、Reader 同一渲染器与引用版本边界；不得改内容资格/检索/prompt，也不得以推断补造项目日期或状态。最新范围见[执行路线图](FRONTEND-EXECUTION-PLAN.md)。

当前实现包括五组独立审批加载/空/错/最近成功与重试、只汇总选择且逐类确认、今日会议/任务/条件行动建议/工具/收件箱、来源/稿件/正式正文/索引与外部动作独立确认。Fake FastAPI 闭环覆盖来源原始字节和 origin kind、取消零写、整理到有部分冲突的稿件、暂时未决选择、正式正文确认与索引；自动化记录外部尝试 0。离线浏览器矩阵覆盖 Today、Approval、Import Drawer、Journal Dialog、审批选择汇总五种场景，各 320/390/768/960/1280 × light/dark。

repair1 修复 QA-001 SourceOrganizer 的 Real 来源整理冻结 scope 展示/一致性校验，QA-002 Import Drawer 两个原生文件选择入口的可见键盘焦点；这些行为仍须由 fresh QA 在新固定 SHA 上复验。来源整理 acceptance scope 与 Real 索引 scope 是两条分离流程。当前 Web 套件保留 6 个 todo，归 C/D，不作为 B 全站验收通过。真实 provider/OAuth/Feishu/Keychain/DMG/进程重启/五日/双机均未在 B 执行。

### A 固定离线技术门（适用范围 PASS）

A 初始固定产品 SHA `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad` 经独立 QA 判 **FAIL**，发现 F1 首配缺少密钥时仍可提交、F2 单项成功会使 AI 总卡误报通过、F3 飞书刷新失败丢失最近成功状态。初始 QA 报告与脱敏 harness 已归档到 [初次 QA 证据目录](../quality/reports/2026-10-15-FRONTEND-A-INITIAL/)；原始 QA worktree 未修改。

修复轮 1 产品 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` 经 fresh QA 与 Sol 核验，适用离线技术门 **PASS**；初始 `9ed544a` FAIL，自动修复用 1/2。QA 的 8 项全站 todo 与 3 条 lint warning 保持未关闭，不视为全站通过。真实 provider/OAuth/Feishu/Keychain/DMG/进程重启/五日/双机未在 A 重跑；历史真实链路成功事实不受本次离线验证影响。报告和脱敏 raw evidence 归档于 [A repair1 QA 目录](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/README.md)。Sol 本轮核验结论见该目录报告。

A 行为包括：App 统一宿主持有工作库→模型/密钥→检查→Feishu→完成；无库关闭返回欢迎页、选库后关闭返回来源业务；真实 profile + workspace 身份隔离保存非秘密步骤；仍打开时 page reload 恢复当前步骤，显式关闭不自动弹但设置能手动续接，完成后不自动打扰。设置连接/重新授权入口直达同一向导第 4 步，工作库入口直达第 1 步。设置主区三张纵向卡为工作库 / AI 模型 / 飞书，技术字段进高级区，危险区仅删除选择的密钥。密钥不进浏览器存储；刷新、展开、保存都不自动访问 provider。Mocked 浏览器在五个视口与浅/深主题运行无横向溢出；真实 FastAPI/Fake 只用临时 profile/workspace，记录 external attempts 为 0。

A 的结论只适用于离线技术门；B 当前产品范围为完整审批五组与今日页。具体实现裁定：索引保留产品规格既有自动增量行为，只对 status/manual_required 对应的首次、Real、模型变更或重建计划做明确范围确认；`quick_note` / `file` / `feishu_material` 来源类型由可信路由标记，旧项保持 `unknown`；今日远端成功结果用按 workspace 隔离的 App 会话缓存，切页不外发、换库或授权身份失效时清缓存并丢弃旧异步响应；“检查并应用”只汇总和导航，类别各自独立确认。项目/问答/阅读留给 C。

### 已合入 main 的前端基础（切片 1–2）

设计 tokens、深色模式、5 栏导航、窄屏导航与应用外壳已由 PR #20 合入 main；其当时 web 基线为 **147 passed | 10 todo**，typecheck/lint/build 全 0。指南与逐页规格仍是后续页面顺序、文案和守卫权威；本轮批准的首配/设置对齐补充记录在 [ADR 0011](../decisions/0011-frontend-ux-baseline.md) 与 [产品规格](../product/PRODUCT-SPEC.md)。

## 设置 UX 与内置非秘密默认值（分支 `codex/settings-ux-20261014`，固定产品 SHA `8c4f81c`）

用户在 2026-10-14 要求按 SummitWorkbench 的配置方式重做首次配置，并明确「Base URL、callback、Feishu App ID 这些非秘密值不要再让我填，只输入密钥」。决议与边界见 [ADR 0010](../decisions/0010-first-use-configuration-ux.md)。

- 设置页改为三张卡 + 状态徽章 + 「高级与自定义」；飞书徽章来自真实本地状态接口，只有凭据确实读不出来才显示「需重新授权」。
- 新增 5 步首次配置向导（模型与地址 → 密钥 → 检查连接 → 飞书 → 完成），每步可跳过；密钥只在组件内存，不写任何持久化；向导导航零 provider 请求；连接检查保持「显式点击 + 本次范围确认」，沿用每项 1 次、跨运行累计的合成检查。
- 非秘密接入值由 Git 忽略的 `.local/first-use/defaults.json` 在构建时注入包内 `Resources/first-use-defaults.json`；运行时只认 `SUMMIT_FIRST_USE_DEFAULTS` 与包内资源，无仓库隐式回退；secret 形态键名或未知键一律 fail closed。百炼地址改用官方推荐的业务空间专属域名。
- 保存只记录用户显式覆盖：与注入默认值相同的值不落盘，因此未覆盖过的 profile 会跟随后续构建的默认值；显式改过的值保持固定。

自动检查（Sol 本机执行）：guarded Python **591 passed**（`SUMMIT_FIRST_USE_DEFAULTS` 导出与未导出两种 shell 结果一致）、Web **90 passed**、ruff/format/mypy/lock exit 0、OpenAPI 与 tracked 文件逐字节一致、`npm run build` 成功。打包 `scripts/release-macos.sh` exit 0（DMG CRC VALID），`smoke_packaged_app.py` PASS，包内注入端到端验证 **27/27**（注入生效、保存不固化、换默认值跟随、secret 形态键启动失败、section 级与字段级损坏都不被静默接受）。候选位于 `.local/internal-builds/settings-ux-8c4f81c/`，DMG SHA-256 `966cf3ae278db6ab0d2c6f60629e63d4cc7b3f2bae9f977333e6682e753eaeab`，`dirty=false`。完整证据与未验证边界见 [DEV 报告](../quality/reports/2026-10-14-SETTINGS-UX-DEV.md)。

三轮全新独立 QA 分别在独立 worktree 对固定 SHA 验收，逐字报告归档在 [QA 证据目录](../quality/reports/evidence/2026-10-14-settings-ux-qa/README.md)：第一轮（`e4f15cd`）全项 PASS 但查出 **D1**（section 级损坏被注入掩盖）；第二轮（`6d41d35`）确认 D1 修复并查出 **F1**（字段级同类）与既存 **F2**；第三轮（`8c4f81c`）确认 F1 修复（旧树对照 72 项失败）、其余全项 PASS，并查出 **F3**（测试不固定注入源）。D1/F1 已修复并由后续 QA 复核，F3 由仅测试提交修复（第四轮聚焦复核：导出与未导出两种 shell 下均 591 passed，且修复前对照复现 33 failed / 558 passed）。

**F2 仍开放**：`origin_guard` 中间件读取损坏 profile 时抛错，返回裸 500 而非设计中的 JSON 503，导致 profile 损坏后连用于修复的 PATCH 也 500；该行为在功能前提交 `a6faf7e` 上同样存在，与本功能无关，未在本分支修复。

未测边界：真实 provider/飞书/OAuth/Keychain 生命周期/真实材料/账单与质量/正式安装/公证/Gatekeeper/五日/双机/发布全部 **NOT_RUN**；runtime 模型元数据 **UNVERIFIED**；新界面未做浏览器或真机视觉复核。另有一处已知残留：在本功能之前保存过的旧 profile 里，注入字段可能已被固化为当时的公共端点，需要用户在高级设置清空该字段一次才会跟随新默认值。

## 当前 M4.2 Package A repair1：固定源码适用离线技术场景 PASS，已获离线收口/合入批准

初始 QA 对固定 SHA `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b` 判 FAIL。修复轮 1 最终受测产品源码 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28`；独立 fresh QA 完成，Sol 判适用工作包 A 离线技术场景 **PASS**，未发现新产品缺陷。它不代表 M4.2 全范围、C25、Stage C 或产品最终 PASS。用户于 2026-10-14 批准工作包 A 离线正式收口与合入 main。PR #18 已于 2026-10-14T10:42:19Z 合并，head `0e8fc4633d4b1409fb7da0354d4474a4faeef430`；远端 run [38550700081](https://github.com/yifeng93/SummitEverything/actions/runs/38550700081) 全步骤成功。该 workflow 显示名沿用 M4.1，但本次运行针对 PR #18。当前 main 产品/tests/lock 树与 fixed `419bb86` 相同；本次 closeout 文档提交不改变受测 SHA。完整关系见 [closeout](../quality/reports/2026-10-14-M42-OFFLINE-CLOSEOUT.md)。

`4c6b0bd` 修复 P1 unknown plan GET 与 P2 planner 完整问句证据，并实现规格已确认的批量文件/文件夹输入及 Journal Assist；`419bb86` 最小修复有效文件与零字节混选静默无反馈，保留严格整批拒绝、为可信 NSOpenPanel 确认选择显示通用说明、主动 Cancel 无提示。自动检查：guarded Python 513、Web 65、Swift 5；静态/type/lock/build/schema检查 exit 0；React lint 仍有 2 条 warnings。`spctl` 对 ad-hoc 包实际 exit 3/rejected，未绕过 Gatekeeper。候选、摘要、Developer 观察见 [DEV 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md)。

QA 独立覆盖 P1/P2，Native 多文件/混合失败提示/取消/目录 FileList，Fake JournalAssist 生命周期，Real ProviderRuntime + MockHTTP API 集成，planner C19、候选身份与包校验。逐项结果见 [QA 报告](../quality/reports/2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)；Sol 范围和限制见 [Sol gate](../quality/reports/2026-10-14-M42-PACKAGE-A-SOL-GATE.md)；61 个原始 QA 文件的可提交副本与路径映射见 [QA evidence archive](../quality/reports/evidence/2026-10-14-m42-package-a-qa-repair1/README.md)。Developer、QA 与 Sol 的 docs/evidence commits 均不能被误称为受测产品 SHA。固定候选交付副本位于主仓库 `.local/internal-builds/m42-419bb86/`：App `/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/m42-419bb86/SummitEverything Internal 419bb86.app`；DMG `/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/m42-419bb86/SummitEverything-Internal-419bb86.dmg`，SHA-256 `2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`。它是未公证的内部候选，不表示正式用户安装通过。

首次配置偏好与只读代码审计见 [M42 readiness](M42-PACKAGE-A-READINESS.md)：初始为 Fake；用户已选择 DeepSeek Flash、Qwen 3.7 embedding 与 Qwen 3.7 rerank，并提供非秘密 WorkspaceId、两个百炼 Base URL 与 Feishu AppID（具体值不写入 tracked 文档）。offline_guard 配置模型验证中，Embedding `/compatible-mode/v1` 与 Rerank `/api/v1` 设置值通过，完整 rerank target 作为 Base URL 被拒绝；adapter 会追加 rerank 服务路径。DeepSeek adapter 固定走 OpenAI-compatible `/chat/completions`，无需 Anthropic URL。1024 embedding dimensions 与 cn region 固定；`default` 只是凭据槽标签。Feishu 保留已登记的旧 callback；native callback `http://127.0.0.1:18793/api/v1/integrations/feishu/callback` 需用户在后台手工新增，本轮未操作后台或保存设置。`5173` 仍是开发示例。聊天中的 `***` 是遮罩，不是真凭据。代码请求 scope 与用户报告后台列表的差异见 readiness；未做 live 权限核验。真实账户可用性、OAuth/scope、token/vault 与 Keychain 生命周期均 **NOT_RUN/UNVERIFIED**；不代表真实 Real 配置已通过，也不假设各 workspace 共享 keys。

安全观察需按真实时序理解：corrected UI run 开始前已核 native/backend guard 与 profile 并通过；更早的一段 UI 运行没有前置核验，恢复上下文后误启动的 late CUA copied app 在任何 UI 输入之前被观察到 guard=false/profile 不匹配并停止。Keychain 查询次数与默认 profile 回退均 **UNVERIFIED**；不能称本轮零查询/全程隔离。P1一条初始错误 assertion raw 完整保留，另一条失败 raw 被成功运行覆盖并在 QA 报告披露。CUA 是观察转录，不是 AX dump 或 screenshot。

当前剩余的授权边界：部分成功后失败项同 operation ID 的真实 UI retry、Real JournalAssist packaged UI、真实 provider/Feishu/Tasks、四份真实材料、Keychain 生命周期、账单/答案质量、正式用户安装/覆盖、公证、五日、双机、M5与发布均 **NOT_RUN**；runtime model metadata **UNVERIFIED**。下一步的具体授权准备见 [M42 readiness](M42-PACKAGE-A-READINESS.md)。用户未指定四份材料的完整路径，也未授权只读核对；本轮未读取四份真实业务 Markdown，未主动进行真实 profile 或 Keychain 验收，误启动期间是否访问及影响仍 **UNVERIFIED**。

## M4.1 固定候选与技术门（历史 SHA）

用户 2026-10-13 授权本分支 `codex/m41-internal-app-20261013` 连续实现和自测离线 M4.1 Internal App/DMG。初始产品 SHA `b9321d64c5404feadffebc05964793e9402a07aa` 的独立 QA 发现 M41-QA-001：WKWebView HTML 文件导入没有原生面板；该 SHA 的 FAIL 记录保留在[初次 QA 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-b9321d6.md)。修复轮 1 固定产品源码 SHA：`3f6eaa408a8860ff5a438be8a874a2c3904733e4`（后续只提交 docs/evidence）。

新 clean-SHA 候选 App：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app`，目录 SHA-256 `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb`；DMG：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything-Internal-fix1-3f6eaa4.dmg`，SHA-256 `554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8`。manifest `dirty=false`、App 版本 `0.1.0`、build `20261013T060945Z-577f0cc805f2`、frontend `577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`、dependencies `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。完整命令 exit、UI 观察和隔离测试见[修复轮 1 DEV 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV-REPAIR1.md)及[tracked evidence](../quality/reports/evidence/2026-10-13-m41-repair1/README.md)。

fresh QA 已在独立 checkout 验收上述固定 SHA；[QA 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md)及 QA-only 原提交 `2437f9c771ff7da3aaf2b39a387903654fde5b9d` 的 47 项 evidence 全部由 Sol 核验，清单摘要 `b6c646435be20866c1c82a56b338801c3c1568ec841a0d2261b41c6af1917211`，29 条命令结果摘要 `979b9acc1f0adb9ae3879a5ae5b0216d1bdd2654c4e6c43ca74773c2f82d46bc`。Sol 判适用离线技术门 PASS，自动修复轮数 1/2；用户已于 2026-10-13 批准离线正式收口，PR #17 已合入 main。新 QA 独立确认了文件面板取消 / TXT / MD 字节、Fake 整理和逐条批准、索引引用问答、重启持久性、菜单 / Cmd+Q / 最后窗口退出、父 SIGKILL 清理、端口 / 错误身份 / 延迟 readiness、缺失后端告警、资源篡改拒绝、合成凭据故障和真实 TCP SSE。Developer 先前 Cmd+Q 的疑问已在新 QA 复验为 PASS。详情与局限见[Sol 门判断](../quality/reports/2026-10-13-M41-SOL-GATE.md)。

主机仅 arm64 macOS 27.0.1；macOS 13 是构建声明，Intel 和其他系统未测。包为 ad-hoc 本地签名，`spctl` 观察为拒绝，Developer ID / 公证及 Gatekeeper 接受仍 NOT_RUN，未绕过系统安全设置。用户测试见[简短说明](M41-INTERNAL-INSTALL.md)；它不会授权覆盖安装或真实业务初始化。

真实 provider / Feishu、真实业务材料、OS Keychain、正式用户安装、Developer ID / 公证、M4.2 真实业务与最终产品验收、五日、双机与发布仍 NOT_RUN；runtime 模型配置元数据 UNVERIFIED。

交付副本：`/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/3f6eaa4/SummitEverything-Internal.dmg`，摘要与候选相同。用户明确回复“批准，并合入”；[PR #17](https://github.com/yifeng93/SummitEverything/pull/17) 已于 2026-10-13 合并，合并点 `c995034f2a7c8acbb8f7ffaa2e0094382af0e3a5`。本机 main 已 fast-forward，产品树与固定受测 SHA 一致；分支、原候选和 QA 工作树保留。远端两个离线 CI 运行在分支 `f7ad5e4` 均 success；该产品树与固定 QA SHA 一致，详见 [CI 原始证据](../quality/reports/evidence/2026-10-13-m41-ci/README.md)。最终 PR HEAD `52d0f3419bf10ad9cb719efed0580256bd059022` 的 [CI run 38364423576](https://github.com/yifeng93/SummitEverything/actions/runs/38364423576) 也已 success。后续仅文档变化不能被写成新的安装包验收。

## 已合入并验收的产品基线

- 本轮清理前 main 基线：`879c82464903a7aed91b30955d7355064fa85088`。这是本轮维护的起点，不代表本轮维护代码 SHA 或后续合并后的 main HEAD。
- M3 离线产品合并：`47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`；C19 固定源码：`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`。
- 三个 M3 离线功能包通过；M3 离线模拟正式验收获用户批准并合入 main。全新 QA 在固定合并点复跑 guarded 后端 491、Web 56 与适用检查通过，49 项合并证据匹配。
- 详情：[M3 验收记录](../quality/reports/2026-10-13-M3-OFFLINE-ACCEPTANCE.md)、[合并后 QA](../quality/reports/2026-10-13-M3-POSTMERGE-QA-47a3971.md)、[完整报告索引](../quality/reports/README.md)。

## 清理维护交接（历史固定 SHA）

Developer 已在 `codex/maintenance-cleanup-20261013` 基于清理前 main `879c824` 完成入口文档整理、旧工作树和冗余本地分支清理，并移除经调用关系审计确认未使用的私有薄封装 `_load_items` 及其变为未用的 import。产品行为、tracked tests 和验收条款保持不变。受测产品源码 SHA `6a33259224097167cfdde689da93258fe925964e` 已通过独立离线 QA，并由 PR #15 合入，合并点为 `2238f1b47d4c7ee073e1d420dc86b23d7e75ffb6`；该合并点产品树与固定 QA SHA 一致。QA-only 报告 / evidence commit 为 `da76f56b765308a365eafd0927c84e88caec492e`，37 项 manifest SHA-256 `88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3` 已由 Sol 核验。详见[DEV 报告](../quality/reports/2026-10-13-PRE-NEXT-STAGE-CLEANUP-DEV.md)和[QA 报告](../quality/reports/2026-10-13-PRE-NEXT-STAGE-CLEANUP-QA-6a33259.md)。Git 与远端最终状态以工作结束时实际查询及本机私有回执为准。

## 清理维护时记录的问题（仅该历史 SHA）

当时记录的 `scripts/run_dev.py` Ctrl+C / `PermissionError` 只对应该维护 SHA；M4.1 分支本轮另行复现后修正，具体结果见 M4.1 DEV 报告。历史报告及证据不改写。

## 后续工作规则

新任务先核对真实 main HEAD 与 AGENTS 指令，再读 [PROGRESS](../implementation/PROGRESS.md)、[IMPLEMENTER](IMPLEMENTER.md) 或 [TESTER](TESTER.md) 及 [ACCEPTANCE](../quality/ACCEPTANCE.md)。固定 SHA 缺失时先联系 Sol 补全交接；不回退到 Foundation/M1 起点。C19/DSH旧材料仅作历史追溯，见[历史索引](history/2026-10-13-m3-offline-closeout.md)。

[清理前的完整交接历史](LATEST-IMPLEMENTATION-HISTORY-2026-10-13.md)。
