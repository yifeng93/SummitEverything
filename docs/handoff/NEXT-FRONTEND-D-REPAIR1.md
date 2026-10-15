# 下一步：前端 D repair1 执行交接

## 当前固定状态

- 当前产品工作树：`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`，分支 `codex/frontend-ux-20261015`。
- 本次收尾前的 docs 基线：`95d582e67d0b5c922e133c55f94d57a44a787d3a`；本次 docs-only commit 后的当前 HEAD 以 git history 为准。唯一产品源码 SHA 保持 `876008e1d33420f57fb31772c76e471379e6b98d`。Sol 最近确认 product tree clean、18793 无 listener。
- 里程碑 A `9c33a9dde3080fff3e3b3dd8a4193589ef52575f`、B repair1 `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`、C `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` 均仅适用离线范围 PASS。
- D 初次 SHA `876008e1d33420f57fb31772c76e471379e6b98d` 经 fresh QA 判 **FAIL / P1**，报告见[初次 QA 归档](../quality/reports/2026-10-15-FRONTEND-D-QA-INITIAL.md)。repair1 已获授权；当前用户要求暂停实现，仅收尾文档。因此**产品代码尚未开始 repair1**，下一执行者从 repair1（修复轮 1/2）开始，不能误报为 repair2。

Sol 负责计划、调度、gate 判断；代码实现交给 custom Developer GPT-6 Luna，修复完成并固定 SHA 后再交给全新的 custom QA GPT-6 Luna 独立验收。串行修改，fresh QA 不修改实现和 tracked tests。最多两轮自动修复；每轮新 SHA、新候选、新 fresh QA。重要里程碑 merge 仍需用户批准。

## D 初次 P1 与原始 QA 证据

`web/src/App.tsx` 的 WorkspaceGate `onOpened` 无条件开启 step 2；进度只有 localStorage，而生产 WKWebView 使用 nonPersistent 数据存储，重启会丢失进度。独立 browser mock 用 `{step:5,completed:true,open:false}`，同隔离 profile/workspace 的 native app 也复现：已完成首配后重启，workspace gate 再出现；打开已有 workspace 后进入模型与密钥 step 2，不进入 Today。

原始 QA checkout 与原件保持不动：

- `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything/.local/qa/frontend-d-initial/QA-REPORT.md`
- `evidence/workspace-gate/reproduction.json`
- `evidence/native-preflight.json`
- `evidence/native-restart-repro.json`
- 其余日志、manifest、截图及 profile 都留在同一 ignored `.local/qa/frontend-d-initial/`；不得复制 trace、profile、token 或真实数据到 tracked 文档。

最小脱敏报告与关键 JSON SHA-256 索引见[初次 QA 报告](../quality/reports/2026-10-15-FRONTEND-D-QA-INITIAL.md)。QA 原始结论是 D 总体 FAIL；Web 204/204、type/lint/build、Python 661、Swift 5 等其余初次 QA gates 通过，不抵消 P1。10 个 mutations 是 876 Developer 证据，不是本轮 QA 独立重跑。

## 修复边界与用户决议

Sol 已批准的最小设计：新增本机 backend profile + workspace 身份隔离的非秘密向导进度存储，持久化仅允许 `step`、`completed`、`open`；通过 typed API contract（Pydantic/OpenAPI/TypeScript 同步）读写。后端使用 profile store 的原子操作/适配方式；拒绝非法 step、未知或秘密字段，写入失败必须可见并可重试。localStorage 可受限地一次迁移兼容旧 `{step,completed,open}`，迁移成功后 backend 为唯一真源，不能长期双写。

必须保持 WKWebView nonPersistent 隔离，不按“有凭据”猜测首配完成、不持久化秘密、不自动打开真实上次工作库：

- completed + 同工作库：开库后直接进入 Today，不自动打扰。
- 未完成且 open：同 profile/workspace 恢复原 step。
- 已明确关闭的向导：重启不自动出现；设置仍可手动续接原 step。
- 设置显式要求 Feishu 连接：step 4 优先于普通 resume。
- step 变化、完成、关闭必须等 durable write 成功再收 UI；失败显示和提供重试，不能假装保存。
- 设置、密钥内存/Keychain、能力检查、Feishu status、审批 B、C 引用资格等行为不退化。workspace lifecycle 仅验证用户手动重新打开原库后的恢复，不加自动打开上次库功能。

## Repair1 首先建立红测

在产品源码上先复现失败再实现，至少覆盖：

1. backend store：profile/workspace 相互隔离；schema 只含白名单字段；非法 step 和额外 secret/unknown 字段拒绝；原子写入、并发写不丢、损坏文件错误和原子失败可见；重启重读正确。
2. browser/UI：completed 同一 workspace 开库进入 Today；open incomplete 回原 step；closed 重启不自动弹；设置手动 resume；显式 Settings Feishu step 4 优先；旧 localStorage `{step:5,completed:true,open:false}` 的受限迁移；read/write 失败可见和 retry；durable write 失败时不显示完成/关闭成功。
3. Native WKWebView 同 candidate、同 canonical temp profile：完成 → quit → same profile restart → 手动 open existing → 直接 Today；未完成 step 3/4 → restart → open existing → 原 step；明确 close → restart → 不弹，Settings 手动续接。使用合成 workspace 与 Fake，不碰真实 Keychain/服务。

API/store focused tests 先红绿。随后完整 Web test/typecheck/lint/build、受影响 E2E、Python guarded suite + ruff/format/mypy + uv lock/schema、Swift（若未改仍记录实际核验结果）。新增的 ①④⑤⑨ 持久化相关变异只对相关守卫按需红绿；旧 876 的 204 tests、Python 661、Swift 5、十 mutation 是旧 SHA 证据，不得冒充新 SHA。本轮不重跑没有变化的全站视口矩阵/全部十变异；对可继承的 876 证据注明 fixed tree unchanged。

## 新 SHA 与全新候选闭环

源码与文档分开提交；产品 tree clean 后记录新产品 SHA。用 Codex native `create_worktree` 创建 exact SHA 的新 managed build worktree，不能 shell git 绕注册；只将主 repo `.local/first-use/defaults.json` LOCAL COPY 到隔离 worktree 对应 ignored 路径，不 cat/print/提交/外传内容。QA 用空/合成 defaults。

构建唯一新的 app/DMG 输出目录，强制 frontend rebuild；记录 source SHA、dirty=false、build ID、frontend/dependencies hash、DMG SHA。保留旧物件，不覆盖或删除：

- D 初次候选 App：`/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.app`
- D 初次候选 DMG：`/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.dmg`
- build ID：`20261015T132109Z-8a0917f72e08`；frontend SHA-256：`8a0917f72e0833727fa90a4f827e70be8835db6711eb9e24b167df16087fab62`；dependencies SHA-256：`cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7`；DMG SHA-256：`8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9`。
- 更早的 `.local/internal-builds/main-bce8843` 及本轮所有 876 candidates/tree/raw artifacts 均保留原样。

新候选启动前重新 `lsof` 检查固定端口 18793；若被占用，识别占用者、不连接、不 kill，记录 BLOCKED。native/backend 必须在严格 canonical `NSTemporaryDirectory()` child profile 中启动，`SUMMIT_INTERNAL_TEST_PROFILE_ROOT` / `SUMMIT_PROFILE_ROOT` 与 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 均由真实进程 allowlist 检查；实际 PID、候选路径、manifest health identity、static root 200 核验通过后才能用 CUA 选 exact app。ps env 原文/token 不得打印或保存。通过 LaunchServices `open -n --env ...` 启动；不能直接执行二进制。完成 GUI 后只退出本轮启动 PID 并确认端口释放。

Native same-profile 生命周期及 Fake 导入→审批→索引→问答→引用→Reader/目录闭环必须在 repair1 新候选实际执行；backend smoke 不能代替 WKWebView。200% 浏览器 native/menu zoom 和 WKWebView 原生 `pageZoom` 暂为 **NOT_RUN**；640 CSS viewport 仅 reflow，独立 CSS zoom 2× harness 仅 simulation，不得写成真实页面缩放通过。截图只存 build `.local`，若无法安全保存 native screen evidence 如实说明。

真实 provider/OAuth/Feishu/Keychain、用户资料、真实 App Support、Desktop/test、已安装 App、付费、production、push、merge、删 branch/worktree 一律不触碰。QA 固定新 product SHA 与新 candidate 独立验收后停止修改；未取得用户批准不得做重要里程碑合并。
