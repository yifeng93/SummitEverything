# 最新实现交接

## 2026-10-11 C03 删除拒绝提示本地化跟进（QA 通过；分支候选，未合入 main）

针对历史 M1 C03 P2，非空主线（有项目 / 目录有内容）及非空项目的删除拒绝提示已中文化。源码 SHA：`9c953f095086a95e63edbce2169657dba9e71cd1`；固定 QA 文档提交：`141bd96d15039f1cd29461785fdd91e2ef297476`；QA 原报告提交：`f381d28d077d3d668cc65ae5eb4fe13b4ad94761`，已在本分支以 `ebb99811d289ea821d5a1bfee9fad6a2a1ba04db` 整合。QA 测试时 HEAD 固定在 `141bd96`；之后只有 QA 报告、交接文档和证据提交，产品源码树与 QA 目标一致。分支为 `codex/c03-delete-copy-pilot`，尚未合入 main。

Sol 根据独立 QA 判定本 C03 离线切片通过：首轮 PASS，repair 0/2；包括 37 项定向自动回归与本地 Fake WebUI 实际浏览器操作。源码树在 QA 前后无变化。DEV 报告：[C03 删除文案 DEV](../quality/reports/2026-10-11-C03-DELETE-COPY-DEV.md)；QA 原报告：[C03 独立 QA](../quality/reports/2026-10-11-C03-DELETE-COPY-QA-141bd96.md)；日志和脱敏观察证据：[QA 证据目录](../quality/reports/evidence/2026-10-11-c03-delete-copy-qa-141bd96/README.md)。QA 使用 CUA 观察但没有导出截图；API envelope 由 contract tests 断言。该切片结果不重开完整 M1，也不改变已合并 Stage B 的历史范围。真实 provider、真实材料、OS Keychain、DMG、五日、双机及 M3–M5 仍 NOT_RUN；main 尚未包含本候选。

## 2026-10-11 Stage B 离线源码已合并

2026-10-11：Stage B 离线源码收口候选 `576895f6983ca41cacbbad45a9075b97b9986189` 已由 Luna High 在独立 checkout 复验：后端388项与25项独立失败路径通过，Web45项及类型/构建检查通过；实际浏览器、原生冷启动、重启、5秒Web启动延迟与退出清理已复验。已合入main（PR #10，merge `41207e5bfb81b535c0254fd4ac242df11da40d67`），合并后核验、证据发布更正及归档清理见[收口记录](../quality/reports/2026-10-11-STAGE-B-POSTMERGE.md)。已采纳 DeepSeek R1–R4 中经复核的实现，并修复传输取消/资源所有权/大小边界、未知refresh跨重启重发、严格凭据解析和原生就绪问题。历史FAIL与原始证据保留。此结论仅覆盖离线源码和开发壳；真实账户/协议运行、OS Keychain、模型R03质量、DMG、M3–M5、五日/双机仍NOT_RUN，不能称完整Stage B或v1验收通过。保留既有Starlette弃用及3条React lint warning。

- 起点文档提交：`0a1db5d72e6ac11184d28e65dea3ba008762ba43`，上一源码 `7dc7114595704f34ba386c96324dffa77d529ba4`；两者产品源码无差异。
- 固定受测源码 SHA `576895f6983ca41cacbbad45a9075b97b9986189`；main已包含受测提交，试验/QA工作树归档后已清理。
- [最终后端复验](../quality/reports/2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md)、[最终实际UI复验](../quality/reports/2026-10-11-STAGE-B-LUNA-UI-RETEST-576895f.md)、[根URL修复DEV](../quality/reports/2026-10-11-STAGE-B-NATIVE-URL-DEV.md)。
- [严格标记DEV](../quality/reports/2026-10-11-STAGE-B-STRICT-MARKER-DEV.md)、[原生双服务readiness DEV](../quality/reports/2026-10-11-STAGE-B-NATIVE-READINESS-DEV.md)、[8b后端复验](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-RETEST-8b6259a.md)、[8b原生FAIL](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-UI-RETEST-8b6259a.md)。
- [刷新重启修复DEV](../quality/reports/2026-10-11-STAGE-B-REFRESH-RESTART-DEV.md)、[首次独立QA FAIL](../quality/reports/2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md)。
- [Sol DEV 收口报告](../quality/reports/2026-10-11-STAGE-B-SOL-CLOSURE-DEV.md)、[ADR 0007](../decisions/0007-request-owned-provider-transport.md)、[协议矩阵](../architecture/PROVIDER-PROTOCOL-MATRIX.md)。
- 独立 QA 使用固定源码 SHA、独立环境、外网/DNS/Keychain guard；允许替代 SecretBackend 与外部 HTTP，保留 route/service/存储/协调器/租约/索引真实实现。
- 需覆盖：资格/发布前复核、取消后不得开始后续调用、完整请求/响应限额、DNS/TCP/TLS/头/正文超时与无后台请求、并发不误伤、logout/callback/refresh/配置重建竞态、scope/格式/分页/截断、凭据拒绝/损坏/重启、真实写门、Fake 回归及实际浏览器/原生。
- 默认 Fake；真实 Feishu 数据读取为显式 `real_data_enabled=false`，真实任务写恒禁用 `result_proof_unavailable`，真实模型业务由服务端拒绝。项目进度仍需本地独立确认。
- 旧真实凭据迁移不在本轮范围：无真实调用/凭据迁入；缺消费标记的旧形状无法追溯历史，未来导入/恢复未知消费历史需先重新授权，不能当作安全未消费。
- user-info `user_identity_verified=false`；OS Keychain、真实 scope/数据/模型质量、DMG、M3–M5、五日和双机均 NOT_RUN。

已有有限 smoke 授权保持：code exchange ≤1、必要 refresh ≤1、DeepSeek chat / embedding / rerank 各 ≤1；实际次数全部 **0/1**。不索取或使用密钥，不读取真实身份/材料/日历/task，不执行真实任务写入，也不因新 profile 重置次数。真实材料另有内容确认门。CNY 5 为旧提示词建议操作上限，不是用户指定预算；真正使用既有授权前须核对官方当前价格。

## 历史交接：M2 阶段 A — 以下 SHA / 检查只对应当时版本

### 恢复路径 UI 补验（2026-10-10）

- **固定基线与修复代码：** 补验从当时 `main` 固定 SHA `409b90704046c623184846c09c873cec053e946d` 开始；该 SHA 在 C18 local-writer receipt 恢复后出现同一动作同时显示成功和“仍为未知”的 P2 UI 矛盾。执行者单独提交修复 `30903c4cdf73855af71a201e3edea6c535ee8199`，只涉及 TasksPanel 状态文案和组件回归测试。
- **独立报告链：** 固定 409b 的补验初报 `6eaf71d6c4e0ddf74b8c532d652296cb6a35b8d0` 保留 C18 UI FAIL。后续脱敏 / 证据清理提交依次为 `eae0f22dce4c7f15d97bd7d5cc1e17f7d7b148f4`、`1d62e24`、`1f0639a`；初报的当前证据树 manifest SHA-256 为 `64f77d13a0bcc0f9b1a4089641df056937647e5b375c3ab3925dab49349f8c10`。独立验收者将新 SHA 的复验报告提交为 `2d6254c4c2717857fda8ccaa97c210b41e0c695e`，再将其以 cherry-pick 方式串接进同一 QA 分支，分支报告树提交 `998b4d2fa1165cecb71c9baf8ff6610a516d3df0`。309 证据 manifest SHA-256 为 `599190944efaf82861b5d571b2364524ec1a06829d5055b1cadd0f0b6453e66f`。报告及可复演 harness 位于 `docs/quality/reports/` 与相邻 `evidence/` 目录。
- **补验结论：** 固定 409b 的 C16 崩溃后 unknown→只读核实成功、确认状态、双击及真实重叠请求 UI 过渡均 PASS；C23 manifest replace 前原子写中断后 unknown/no-resend PASS。固定 309 的 C18 receipt-loss→restart unknown→只读核实 succeeded→同 ID replay PASS：UI 只显示成功，本地 manifest / progress_version 重放前后不变。固定 309 的 C23 no-proof 负对照仍为 unknown。自动测试未在独立复验中重跑，状态为 NOT_RUN；实现者对 309 修复提交的组件与指定集成测试自测见其提交记录。该补验不改变原固定 409b 初报的 FAIL 事实，只表示缺陷在新 SHA 已整改并复验。
- **证据限制与范围：** 两轮均为隔离浏览器、合成工作库与 Fake providers；最终 309 复演全程仅观察到 loopback sockets。409b 初次候选 Chrome曾连接本机代理 `127.0.0.1:7890`，无法证明代理是否转发，故初报保留该限制。没有有意调用真实飞书、模型、业务材料或凭据；本轮没有真实业务外部操作。独立 UI console/network、请求响应、磁盘指纹、同一 action_id 与撤回重复截图说明见报告。该补验不重跑原生壳或整体 Stage A 自动矩阵。
- **合并后核验：** PR #7 以 merge commit `c655eb48f5ce7448edac77c0250f9ed9d2ac8e33` 合入 main；SSH 读取的远端 `main` 在本次核验时为该 SHA。独立 detached checkout 固定于该 merge commit，确认 `30903c4cdf73855af71a201e3edea6c535ee8199` 为祖先，且 `src/tests/web/native` 与受测修复 SHA 完全一致；两份补验报告均存在，47 项和 26 项 manifest 均逐项匹配。之后仅文档 ledger 更新不改变受测源码树。阶段 B/C 与 M3–M5 未开始。

- **该轮代码 SHA：** `32da67e9c0280e3dae18fd374e30c925565b0b82`，分支 `codex/m2-stage-a-closeout`，基线为原 M2 交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。
- **原候选：** `09398fcae597b2478001d40aedf580ea91322c11`。原候选 QA 测试与报告提交 `f64c565b7c5105867e0c19e7e1e716dc726f8ff7`；A-01 P0、A-02–A-04 P1、A-05 P2 复现结果见 [原候选定向 QA](../quality/reports/2026-10-10-M2-stage-a-original-qa.md)。报告结论保持原样。
- **该轮状态：** Fake-only M2.1–M2.3 阶段 A 已由独立 QA 在固定代码 SHA `32da67e9c0280e3dae18fd374e30c925565b0b82` 复验通过；最终报告提交 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`。原候选缺陷初验及后续各轮复验报告均保留，结论与受测 SHA 对应。
- **初始文档 checkpoint：** M2 核心规格 checkpoint `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`；执行交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。该轮文档已在修复代码后提交；最新基线见本文顶部。
- **自测摘要：** Python 142 passed；Web 8 files / 32 tests；Ruff、format、mypy、lock、uv build、OpenAPI 类型生成、typecheck、lint、web build 与 Swift build 退出 0。保留 1 条既有 Starlette/httpx 弃用警告和 3 条既有 React effect lint 警告。以上不是独立 QA 结论。
- **独立验收摘要：** A-01–A-05 与阶段 A Fake-only MUST 场景通过；未关闭 P0/P1/P2=0。浏览器 Fake 流程和 console、原生开发壳归属 / 窗口 / Quit / 退出清理均有独立报告和证据。API 没有 OAuth cancel UI 控件的变体记 NOT_RUN，API denial 已覆盖。
- **合并与合并后核验：** PR #4 以 merge commit `0789f9ebfee4a0352e2818510055a252ba374daf` 合入 main。独立 checkout 固定于该 SHA，自动检查全绿；Python 142 passed、Web 32 passed，另有关键路径 8 项冒烟通过。合并树 `src/tests/web/native` 与 QA 固定源码树一致。详细命令和结果见[合并后核验记录](../quality/reports/2026-10-10-M2-stage-a-postmerge.md)。
- **阶段状态：** Stage A 的 Fake-only 模拟范围 QA、PR 合并和合并后核验已完成；真实 provider、材料和发布门仍 NOT_RUN，不包含在本阶段结论内。
- **真实门：** 当前只有 Fake providers；本轮未访问真实 Feishu、付费模型、真实业务材料或 Keychain，未执行 DMG、五日或双机验证。用户备好的真实资源未被消费；真实门继续 NOT_RUN。
- **阶段边界：** 未启动 M3–M5；该轮结束时等待技术评定；现已收口，B/C 入口见顶部。

以下 `M1` 区域为历史交接记录。

下文保留 M1 独立 QA 历史。

## 固定候选

- **阶段：** M1.1–M1.5 DEV、独立模拟验收及 main 合并后检查均通过。
- **首次 QA 固定代码 SHA：** `73ec81a06f2557c006f98ff88fa81b08d14ef315`。
- **当前修复候选代码 SHA：** `f349fe6cb5da86c3fdafff11738e2a55335d8874`。
- **合并提交：** `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`（PR #1，merge commit；远端 `main` 已包含受测代码）。
- **分支：** `codex/m1-close`。
- **材料边界：** 只用隔离模拟工作库与 Fake providers；没有导入真实“场地与酒店”材料、付费模型或真实飞书。
- **DEV 自测记录：** [2026-10-09-M1-close-DEV.md](../quality/reports/2026-10-09-M1-close-DEV.md)（已提交，不是独立 QA 报告）。详细隔离运行记录另保存在 ignored `.local/m1-close/evidence/dev-self-check.md`。
- **独立 QA：** 首轮发现 C03 P1，已由执行者修复；同一 QA 在新 checkout 的 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 上复验通过。报告：[首次失败记录](../quality/reports/2026-10-09-M1-close-73ec81a.md)、[最终复验报告](../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。M1 模拟范围 P0/P1=0；报告记录 1 个 P2 英文删除拒绝提示及后续本地化安排。
- **合并后验证：** 在远端 `main` merge commit 的独立 checkout 上，后端 77 项、前端 10 项、OpenAPI 类型生成、类型 / lint / 构建、lock、uv build 与 Swift build 全通过；远端 `main` 包含受测 SHA 与两份 QA 报告。

## 修复摘要

- 修复 C05：来源状态由最新整理作业和关联稿件派生并持久化，覆盖 pending、processing、reviewing、completed、failed、cancelled；正在整理或仍有待审稿的来源不能用新 operation ID 另起作业。失败、取消或全部处理完成后，只有显式 `reprocess=true` 才能重新整理；相同 operation ID 按原意图幂等重试。
- C06：用户先选一个项目，一份多主题来源可生成多份稿件，逐份确认并保持完整来源关联；不进行自动跨项目分流。
- C07：未决或选择结果会写入最终正文，未决内容明确标为未确定；稿件编辑区预览结果。
- C08/C10：真实 UI 显示外部版本差异、阻止覆盖；保留稿件、显式比较基准、重新确认后，索引重建并恢复最新正文检索。
- C03/C13/C14 的 M1 部分：既有测试覆盖归档知识检索、非空删除保护、失效 / 被替代内容区分、SSE 顺序 / 唯一终态 / 取消不伪装完成。
- C03 初次 QA 暴露的界面缺口已修复：稳定 ID 重命名、归档项目查看 / 恢复、仅空目录可删除、页面移动及新增相对链接后明确确认。新增 ProjectsView / PageReader 界面回归；QA 已在真实浏览器复验移动、引用修复和链接确认。
- C11/C12/C23 的 M1 部分：旧版本资格门、邻页复核、索引 fingerprint 变化与失败重建保护、原子写恢复和同意图重试由自动测试覆盖；QA 已对固定候选完成 M1 范围复验。
- 本地开发壳：API / Web 端口与 profile 可隔离；run identity 防止误连其它 checkout 服务；runner 只清理自己启动的进程组。正常 Quit、最后窗口关闭、`swift run` Ctrl+C 均以本轮独立端口复演并确认无监听残留。

## 启动与检查

```sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
```

默认 API `127.0.0.1:8793`、Web `127.0.0.1:5173`。并发隔离可设 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT`、`SUMMIT_API_TARGET`、`SUMMIT_PROFILE_ROOT`。访问 `http://127.0.0.1:5173`。原生开发壳：`cd native && swift run`。

固定修复候选 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 与合并后的 main 树均完整复跑：后端 77 passed；前端 5 个测试文件 / 10 项测试；OpenAPI 类型生成、typecheck、lint、production build、ruff check / format、mypy、lock check、uv build、Swift build 均退出 0。保留 1 条 Starlette/httpx 弃用提示及 3 条既有 React effect lint 警告。

## 真实 UI 复演

完整隔离路径和步骤见 DEV 自测证据。真实浏览器复演覆盖 C06 的单项目多稿、部分与全部确认；C10 外部编辑、旧证据失效、重新确认及增量索引恢复；C08 目标外部变化的冲突保护、稿件保存 / 重新确认及最新正文检索。材料全部是本地合成文本。

## 尚未完成或未测

- M1 独立模拟验收已通过，详情按案例见最终复验报告。受测实现固定 SHA 为 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；执行者后续提交均为文档和 QA 报告导入。
- C13 历史会话 UI、C14 断流恢复 / 历史引用 UI 属 M3；C25 DMG、干净机器安装和发版身份属 M4；均不得记作 M1 PASS。
- 真实“场地与酒店”材料确认、真实模型质量、真实飞书权限 / 写入、五个实际工作日、双机往返未测且需要各自授权门。
- 1 条 Starlette/httpx 弃用提示和 3 条前端 effect lint 警告保留；未通过隐藏警告或降低期望获得绿灯。

## 合并后检查记录

- PR：[SummitEverything M1 closeout](https://github.com/yifeng93/SummitEverything/pull/1)，以 merge commit 合并至 `main`。
- 合并提交 SHA：`4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`；已确认该树包含受测代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 和 QA 报告提交 `0fd0102ad8a22fae336339e7fd635acc15438224` / `49ce008446339c723b83ee39cfe3e2ae029b4437`。
- 在该 main 树复跑：后端 77 passed，ruff check / format、mypy、`uv lock --check`、`uv build`、OpenAPI 类型生成、前端 10 tests、typecheck、lint、production build、Swift build 均退出码 0。保留 Starlette/httpx deprecation 和 3 条既有 React effect lint 警告。
- 合并后服务端口和 UI 服务均未启动；真实材料、模型、飞书、DMG 与多设备门仍未测。

## QA 交接

独立验收在源码仓库外的 `/Users/yifengstudio/.codex/worktrees/qa-m1-close-r3` 固定到 `f349fe6cb5da86c3fdafff11738e2a55335d8874`。报告与隔离模拟 UI 证据已保存；不修改产品实现。M2/M3/M4/M5 场景和真实外部门按最终复验报告保持 NOT_RUN。

## 下一阶段

此处保留阶段 A 开始前的历史交接状态：当时 M2.1–M2.3 等待固定 SHA 独立 QA，原代码 SHA 为 `09398fcae597b2478001d40aedf580ea91322c11`，核心文档 checkpoint 为 `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`。最新阶段状态见本文件顶部；真实资源的边界与 M3–M5 暂缓决议仍有效。
