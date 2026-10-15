# 前端体验实施路线图（2026-10-15）

状态：A `9c33a9dde3080fff3e3b3dd8a4193589ef52575f`、B repair1 `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`、C `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` 经 fresh QA 与 Sol 判定各自适用离线范围 PASS。D 初次固定产品 SHA `876008e1d33420f57fb31772c76e471379e6b98d` 经 fresh QA **FAIL / P1**：completed 同 profile/workspace 在 native 重启后仍进入 workspace gate，打开已有库后再次显示向导 step 2。四条全站守卫及十 mutation 的开发证据只属于 876，不抵消初次 FAIL，且**明确不可继承**（前端 bundle 指纹已变）。**D 最终固定产品 SHA `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（链 `876008e` → repair1 `faa1edd` → repair2 `96fdf4d` → repair3 `e8e1dba`）：进度改存本机 profile + workspace 隔离的 typed API，旧 localStorage 只做一次性迁移；`open` 且无记录落到今日不被遮罩；`step` 严格整数；CI 类型门重新生成。最终 SHA pytest 692 / vitest 222 passed / 0 todo / 默认 e2e 2 / 集成 e2e 1 / 静态与 build 全 exit 0；三轮独立 QA 各自自建 harness 并在父 SHA 做非空性对照；native 候选包内 runtime 15/15，实机 WKWebView 三路径机器 OCR 判读通过；全站视口矩阵已在 `e8e1dba` 重跑。**Sol 判 D 门限「离线 + 内部候选」范围 PASS、P1 CLOSED；PR [#21](https://github.com/yifeng93/SummitEverything/pull/21) 已开，合并待用户批准。** A/B/C 报告见 [A](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/README.md)、[B](../quality/reports/2026-10-15-FRONTEND-B-QA-REPAIR1.md)、[C](../quality/reports/2026-10-15-FRONTEND-C-QA.md)。D 初次脱敏摘要见[QA报告](../quality/reports/2026-10-15-FRONTEND-D-QA-INITIAL.md)；最终见 [D 最终 QA](../quality/reports/2026-10-15-FRONTEND-D-QA-FINAL.md)、[Sol 最终门判断](../quality/reports/2026-10-15-FRONTEND-D-SOL-GATE-FINAL.md)与 [DEV 报告](../quality/reports/2026-10-15-FRONTEND-D-DEV-REPAIR2.md)。真实 provider/OAuth/Feishu/Keychain/DMG/安装/公证/生产/长期/双机仍按各自门记为 NOT_RUN。

## 决议优先级与范围

本轮产品负责人明确的执行方案优先于 2026-10-14 前端指南 / ADR 中的冲突项。暖橙与墨绿、五栏「今日 / 审批 / 项目 / 知识问答 / 设置」、中文白话、字号尺度、深浅主题、Markdown 与十条守卫保持。导航继续按用户指定顺序执行：共享准备 → 切片 3 首配合并 → 切片 9 设置对齐 → 切片 4 审批五组 → 切片 5 今日 → 切片 6 项目列表和详情 → 切片 7 问答 Markdown 流式 → 切片 8 阅读渲染 → 切片 10 守卫收口；答案质量为另开切片。

### 与旧规格的冲突登记

| 项目 | 旧记录 | 本轮执行决议 | 同步方式 |
|---|---|---|---|
| 前端执行切片顺序 | ADR 0011 / FRONTEND-GUIDE 先审批、今日、项目、问答、阅读，再设置 | 首配 3 与设置 9 提前连续实现；之后 4、5、6、7、8、10 | 本计划记录全序；每个完成里程碑修正 PROGRESS 与 LATEST 当前正文，不重写历史结论 |
| 今日页简报 | 旧逐页规格可能把简报描述为生成摘要 | 只汇总现有会议、任务、行动建议；不加模型总结能力。刷新须先预览范围并独立确认 | 切片 5 同步 FRONTEND-PAGE-SPECS / GUIDE；不新增后端总结接口 |
| 会议与任务 | 历史页面包含集成入口 | 会议只读；Real 任务写仍禁用；Fake 已有动作复演保留 | 切片 5 / 4 同步规格与验收边界 |
| 批量审批 | 旧文案可能暗示一次批量应用 | 检查并应用只汇总已选事项，按类别分别预览与确认；不混合批准、不新增跨类别事务 | 切片 4 同步逐页规格与验收场景 |
| OAuth 入口 | ADR 0011 表述授权只在首次配置一次 | 设置中的连接 / 重新授权直接进入相同首配第 4 步；切片 5 移除今日旧入口 | 共用 OAuth 模块；A 不移除其他页面功能，B 迁移时清理旧入口 |
| 首配顺序 | ADR 0010 从模型开始，工作库由独立 gate 负责 | 唯一向导为工作库 → 密钥 → 检查连接 → 飞书 → 完成进入今日 | 关闭且未完成工作库时回欢迎 / 连接页，不允许绕过工作库前置条件 |
| 测试证据 | 现有主要为组件测试，无浏览器 harness | 离线浏览器 harness 覆盖 320/390/768/960/1280 与 light/dark；关键业务另用真实 FastAPI + Fake + 隔离库 | 只 mock 外部 provider；记录退出码、截图、测量和真实服务证据 |

## 全局实现与验收规则

- 暖橙 + 墨绿视觉基调、五栏导航、正文 15px / 列表 14px / 次要 13px / 全局不低于 12px；组件使用颜色、字号、间距 token。深色对比和窄屏同时复核。
- 浏览器自动化离线运行，所有网络默认拒绝外发。不得访问真实 OAuth、Keychain、provider 或飞书；使用合成 fixture、临时 profile 与临时 workspace。不得访问用户桌面业务材料、已有安装应用或真实本机配置内容。
- API / Fake 集成使用实际 FastAPI 服务及隔离库；UI 单测 mock 可以用于纯交互，但不能替代关键业务闭环。内容资格 / 索引 / 引用信任门不改动，`content.py` 仍为唯一基准。
- 共享 `ConfirmDialog`：`role=dialog`、`aria-modal=true`、焦点陷阱、Esc 取消、关闭后焦点归还；危险动作默认聚焦左侧取消。正文解释影响与可恢复性。确认前请求数 0，取消请求数 0，确认恰好 1；busy 文案与禁用阻止双击。
- Markdown 组件使用 `react-markdown` + `remark-gfm`，不执行 raw HTML；外链安全，页面内链接由 `onOpenPage` 处理。表格、标题、列表、代码、wikilink 均按语义显示。流式显示需稳定已完成语法、暂存不完整片段，错误不抛出，最终 DOM 与完整渲染一致；代码文本不可误删，增长区域无 `aria-live`。
- 首配状态只持久化 profile 与 workspace 隔离的非秘密步骤信息；秘密只在 password 控件和内存中，成功写入后及退出时清除。已有凭据不重复索要，状态只读服务端。工作库、凭据和连接状态分开表达；connecting / unreachable / no-workspace 不混为一态。非必需步骤可跳过；completed 不再打扰。
- Feishu 授权抽成共享小模块，沿用已有 origin / path / state / callback / identity 校验。真实授权与 Keychain 全部 NOT_RUN。
- 设置主区严格纵向三卡：工作库 / AI 模型 / 飞书。显示中文业务能力名和逐项真实状态；端点、区域、账号、AppID、callback、预算参数等放高级；内部 ID、hash、原 JSON 仅诊断导出。读取失败仅降级对应卡片，保留最近成功值及时间；首次失败不得伪装成持续加载或可用。刷新 / 展开 / 保存不隐式联网；各卡不能因单项检查成功而合并宣称全通过。
- 危险删除 / 断开由共享确认弹层保护，且仅删除明确选中的那一项；文案须与实际存储影响一致，不许承诺不发生钥匙串删除。
- 保持 2026-10-15 起始的 Web 测试计数 `147 passed / 10 todo` 作为真实基线；不通过删测试、降低断言或挪 todo 伪造成功。每个被修改的守卫做隔离变异：故意使断言失败、确认命令非 0，恢复后再通过。里程碑 A 覆盖守卫 ①③④⑤⑥⑦⑧⑨⑩；其他页面尚未实现的守卫继续准确登记为 todo 并归属后续切片。

## 里程碑与逻辑提交

### A — 共享准备 + 切片 3 首配合并 + 切片 9 设置对齐（适用离线技术门 PASS）

固定产品 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` 已交 fresh QA；Sol 核读报告、raw 日志、SHA 与 clean 状态后判适用离线技术门 PASS，自动修复使用 1/2。QA 留下的 8 项全站 todo 和 3 条 lint warning 继续登记；真实 provider/OAuth/Feishu/Keychain/DMG/进程重启/五日/双机未在 A 重跑。完整 gate 及脱敏原始证据见 [A Sol gate](../quality/reports/2026-10-15-FRONTEND-A-SOL-GATE.md) 与 [QA archive](../quality/reports/evidence/2026-10-15-frontend-a-repair1-qa/README.md)。

验收点：

1. 每条导航只挂载一个目的页；A 统一设置与向导入口，今日旧授权入口迁移归 B；向导完成直达今日、可中断恢复，workspace 前置条件不可绕过。connecting / unreachable / no-workspace 区分。
2. 页面导航、设置读取和刷新不调用 provider；确认弹窗取消无请求、确认恰好一个请求、双击只一请求；危险确认默认取消。
3. 向导的工作库 → 密钥 → 检查 → 飞书 → 今日完整链可使用真实 FastAPI + Fake 和新建临时库执行；关闭 / 重启恢复非秘密步骤，完成后不重复展示。所有秘密测试值为合成值。
4. 设置三卡纵向、读失败局部降级，准确呈现工作库 / AI / 飞书状态；危险动作的取消零写、确认仅写对应对象。AI 能力不因单项成功而泛绿。
5. Markdown 普通完整文本和流式末尾部分语法的结构化渲染、HTML 转义、外链策略、页内导航、代码内容、最终态一致均有断言。
6. 浏览器截图与布局测量覆盖 320、390、768、960、1280 像素及 light/dark；0 横向溢出，正文最小字号规则通过。

覆盖守卫及变异：①内部标识 / 路径 / JSON 不出主界面；③字号下限与三类尺度；④加载、空、错误分离；⑤危险确认 / 外部操作单飞；⑥ Markdown 安全与流式稳定；⑦浅深色对比；⑧已完成页面的区块契约不回退；⑨列表 / 读取刷新 provider 调用数为零；⑩五档无横向溢出。每条变异记原命令、破坏方式、红色退出码、恢复补丁与绿色退出码。

检查点提交：A0 计划文档；A1 离线 harness 与基线证据；A2 共享组件；A3 首配；A4 设置。每个检查点运行本片测试后提交。最终开发证据写 `.local` 原始日志/截图并以脱敏索引引用；摘要在 `docs/quality/reports/2026-10-15-FRONTEND-A-DEV.md`。

回滚面：提交各自独立；A1 可单独撤回 harness / lock；组件、向导、设置按 A2/A3/A4 逻辑提交回退。不得为回滚改变后端内容信任门或删除守卫。

### B — 切片 4 审批完整五组 + 切片 5 今日

审批按待整理来源 → 待复核稿件 → 待确认正式内容 → 待确认索引 → 待确认外部动作五组展示，每组独立加载/空/错和业务回执。主操作只对用户已选项做总览，再逐类别分别范围预览与确认；不做类别间合并确认，不新增跨类别事务。今日按会议、待办、行动建议、工具顺序呈现；简报仅汇总现有数据，不新增模型总结。会议只读，Real task 写保持禁用，Fake 既有动作复演保留。

父产品 `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` 已由初次独立 QA 判 **FAIL**，发现 QA-001 SourceOrganizer Real 来源整理未展示被冻结的 `outgoing_inputs` 正文与可读目标，以及 QA-002 Import Drawer 隐藏文件 input 焦点不可见。repair1 产品固定 SHA：`a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`；Developer 检查 180 passed / 6 todo、typecheck/lint/build exit 0、离线 Playwright 2/2、FastAPI/Fake 冲突闭环 1/1、同范围真实冻结 scope 取消 1/1；Python 在 repair1 未重跑（后端未改）。Import Drawer 焦点捕获为 5 个宽度 × light/dark 共 10 张；退出码、原失败/重跑和文件哈希见 [repair1 DEV/evidence](../quality/reports/2026-10-15-FRONTEND-B-DEV-REPAIR1.md)。

repair1 QA 已对固定产品 SHA 独立复验，Sol 判适用 B 离线核心及修复 PASS。结果为 180 passed / 6 todo、typecheck/lint/build exit 0、离线 E2E 2/2、Real scope/focus 1/1、Fake FastAPI 1/1。Python 661、QA mutation 未运行；真实 provider/OAuth/Feishu/Keychain/DMG/进程重启/五日/双机仍未测。不得把初始 FAIL 合并写成 PASS；6 项 todo 留给 C/D。

回滚：ApprovalView 与 TodayView 分离提交。入口迁移时去掉今日旧授权按钮；共享 OAuth 行为继续由首配第 4 步承载。

### C — 切片 6 项目列表和详情 + 切片 7 问答流式 + 切片 8 阅读渲染

项目先列表后详情并保留返回搜索/筛选/滚动；问答使用共享 Markdown 流式渲染，完整输出、取消和终态明确；阅读页复用相同安全渲染器、引用版本边界不变。

交付：项目、问答、阅读分别逻辑提交并带 focused tests，之后固定里程碑提交与 DEV 证据；fresh QA 固定 SHA。重点守卫①②④⑤⑥⑧⑨与真实 FastAPI/Fake 检索引用链。回滚以页面级提交为边界；不改 `content.py` 与引用资格门。

### D — 切片 10 守卫收口及最终候选

初次 D 固定 SHA `876008e1d33420f57fb31772c76e471379e6b98d` 已完成 ①④⑤⑥、十条守卫开发变异、browser matrix 和 ad-hoc candidate，但 fresh QA 发现完成首配后同 profile/workspace 重启又弹 workspace gate / setup step 2，D gate **FAIL / P1**。候选 App/DMG 与 package manifest 不覆盖不删；旧 main candidate `.local/internal-builds/main-bce8843` 也不动。

D 的修复分三步落地：repair1 `faa1edd` 把仅含 `step/completed/open` 的 profile+workspace 隔离首配进度持久化到本机 backend（Pydantic/OpenAPI/TS typed API，保留 WKWebView nonPersistent），fresh focused 用例覆盖 completed→Today、open incomplete 原 step、closed 不弹、设置手动续接与 step4 优先、失败可见/可 retry、profile/workspace 隔离、原子性与密钥字段拒绝；repair2 `96fdf4d` 让工作库 gate 上抛 create/open 意图（`open` 且无记录落到今日、不再被 `.wizard-backdrop` 挡住）并把 `step` 收紧为严格整数；repair3 `e8e1dba` 重新生成 `web/src/api/generated.ts` 修复 CI 类型门。三条 repair1 变异 + 两条 repair2 变异全部先红后恢复。见 [D repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-D-DEV-REPAIR1.md)与 [D repair2/3 DEV 报告](../quality/reports/2026-10-15-FRONTEND-D-DEV-REPAIR2.md)。

**D 已按固定产品 SHA `e8e1dba` 收口**：native managed build worktree 与全新候选已建（`SummitEverything-D-e8e1dba`，DMG SHA-256 `5f9805eb…`，`dirty=false`）；包内 runtime 自建 harness 15/15（含杀 backend 另起新进程后记录仍读回）；实机 WKWebView 三条路径以本机 Vision OCR 机器判读通过（已完成→今日、未完成 open→恢复原 step、设置手动续接原 step）；全站视口矩阵已在 `e8e1dba` 重跑。Sol 判 **D 门限「离线 + 内部候选」范围 PASS、P1 CLOSED**。876 的十条变异**不可继承**（前端指纹已变），由本轮 5 条定向变异替代。未覆盖：D-3（OpenAPI 未声明 401/404/503，INFO）、D-5（用户决议接受）、`swift test`（`native/` 未改）、CSS 640 仅 reflow、root CSS zoom 仅 simulation、browser menu 200% 与 native `pageZoom` **NOT_RUN**；真实服务、Keychain、用户资料、安装 App、公证与发布都不碰。**PR [#21](https://github.com/yifeng93/SummitEverything/pull/21) 已开（含 A→D 整条线），重要里程碑 merge 仍需用户批准。**

## 新鲜 QA 里程碑

| QA | 固定产品范围 | 固定目标 |
|---|---|---|
| A | 共享组件 + 切片 3 首配 + 切片 9 设置 | 固定 A 产品 SHA；复验首配/设置业务与 UI，离线浏览器矩阵及变异证据 |
| B | 切片 4 审批 + 切片 5 今日 | 固定 B 产品 SHA；五组独立确认与今日简报范围 |
| C | 切片 6/7/8 项目、问答、阅读 | 固定 C 产品 SHA；页面导航与 Markdown / 引用闭环 |
| D | 切片 10 + 新候选 | 固定 D 源码和构建身份；十守卫、WKWebView / DMG 隔离候选 |

QA 不与开发同时修改共享 checkout；每次报告绑定精确产品 SHA。失败最多按协作约定修复两轮，每轮出新 SHA 并 fresh QA。Sol 保留最终门判职责。

## 本轮明确不进入范围

里程碑 B 执行审批五组与今日，不进入答案质量切片、项目/问答/阅读页面、生产发布、push、merge 或分支/worktree 清理。真实 provider、OAuth、飞书、Keychain 与用户业务材料继续按实际授权和本轮证据记录；不得覆盖既有 `a81f3f1` / 用户历史联通成功事实。正式安装、公证、五日/双机仍是各自独立门。
