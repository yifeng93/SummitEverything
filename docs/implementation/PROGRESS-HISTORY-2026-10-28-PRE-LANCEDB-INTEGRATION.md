# 实施进展账本

本页是当前产品状态的唯一维护处。固定版本的原始报告见[报告索引](../quality/reports/README.md)，执行入口见[最新交接](../handoff/LATEST-IMPLEMENTATION.md)；旧阶段过程见[历史账本](PROGRESS-HISTORY-2026-10-16.md)。

## 设计探索原型（2026-10-23，未提交）

- 用户要求在新分支制作“外部助手 + Skills + MCP 知识服务 + 审核与搜索界面”的高保真原型，并明确不提交。分支 `codex/mcp-workbench-prototype-20261023`，基线 `67b8169115fe166c819e2a5c410831798809c874`。
- 独立入口为 [助手接入与知识搜索原型](../../prototypes/mcp-workbench/README.md)，复用现有主题；未改生产前后端、依赖或已确认产品规格。五页包含知识搜索、审批、助手接入设置、今日和项目；导航与布局差异在原型说明中列为待评审提案。
- 原型使用虚构内容与浏览器内存状态，刷新即重置。搜索是本地文字匹配；知识确认更新对应示例页，任务选择不执行外部动作。MCP 接入、向量引擎升级、真实保存和外部服务均未实施。
- 首轮独立检查发现搜索清空、确认后检索、任务列表和项目筛选问题；第 1 轮修复后的固定文件快照独立检查 **PASS**：26 项交互/布局检查，以及 25 组默认非空页面布局检查均 exit 0，浏览器异常和外发请求均为 0。五档宽度 320/390/768/960/1280 无整页横向溢出、可见文字字号不低于 12px；浅/深色和移动截图已留存并人工查看。Sol 复核工作树与快照 5/5 文件哈希一致、生产目录 diff 为空、暂存区为空、HEAD 未移动。证据保留于本地 `.local/qa/mcp-prototype-repair1/`；此 PASS 只覆盖原型，不代表正式产品验收。候选以基线 SHA 加原型文件 SHA-256 固定；具体交接见 [LATEST-IMPLEMENTATION](../handoff/LATEST-IMPLEMENTATION.md)。
- 本轮不改变下方正式产品验收结论及任何真实未测门；原型视觉仍待用户评审。

## 本轮修复（2026-10-17，已合入 main）

- PR [#25](https://github.com/yifeng93/SummitEverything/pull/25) 已合入，merge
  `2e76f4c94d1f77e2b7285e93b7ef9ef7526a9bc2`，产品 `c82aecf`；PR
  [#26](https://github.com/yifeng93/SummitEverything/pull/26) 已合入，merge
  `f1b990a156e5757ac619f3202c4aefd82c8be2c3`，产品 `fe78ba4`。当前 main 产品树与
  `fe78ba4` 一致；本地与远端仅保留 `main` 分支。
- 修复：百炼点分隔 API key 被旧白名单误拒；整理提示词与 `kind` schema 冲突；已提交计划
  不可取消时的英文提示与残留对话框；页面标题未参与检索 scope；飞书日历缺少身份/日历 ID
  设置；真实模式暴露了不受支持的可见范围筛选。
- 离线回归：Python **731 passed**、Web **243 passed / 27 files**、Ruff/format/mypy、
  typecheck/lint/build、内部 App/DMG 构建、codesign、hdiutil verify 与 packaged smoke
  通过；两条既有 Oxlint warning、Starlette/httpx 弃用提示和约 605 kB bundle advisory
  保留。
- 真实 `Test2` 工作库：整理 job completed（12 稿，DeepSeek 3137/1408 tokens）；索引
  4 chunk（embedding 299 tokens）；问答“学员28号晚住宿需求自动勾选流程是什么？”
  1 条引用，真实调用 embedding 28 / rerank 85 / DeepSeek 390+588 tokens。飞书 OAuth
  已授权；任务读取正常；`identity=user` 日历读到 3 条日程；妙记查询“会议”返回 20 条
  （空查询 0 条）。任务写回仍禁用，材料导入未验证。
- 最新内部候选 DMG：`.local/internal-builds/fe78ba4-20261017/SummitEverything-Internal-fe78ba4.dmg`
  （source `fe78ba4`，`dirty=false`，SHA-256 `3deb5ddc…c497`）；未公证。
- 已安装 App/公证、五日、双机、发布、整站完整业务和 WCAG AA 审计仍 **NOT_RUN**；
  Keychain 在真实整理/查询/飞书读取中可用，但完整生命周期未单独验收；runtime model
  metadata **UNVERIFIED**。

## 上一轮精简（2026-10-17）

- README 已重构为项目首页；实现、验收和文档入口按职责整理，旧状态不再充当当前指令。
- 文档固定 SHA `f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796` 的独立文档 QA **PASS**。代码固定 SHA `2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`；完整受测候选 `5835faa72b513202e92694f4fa14790afefe1e70` 的独立离线代码与内部包技术门 **PASS**，Sol 已核验原始证据。两次常规 QA，无产品修复轮；后续交接/证据提交不改变受测产品树。见[Sol 最终门判断](../quality/reports/2026-10-17-PONYTAIL-CLEANUP-SOL-GATE.md)。
- 产品源码仅删除无调用的 `job_attempt_hash` 四行定义。归档摘要、版本链校验、全部测试与断言、依赖、界面、API 和生成类型保持；没有证据支持进一步删依赖或合并回归测试。候选与保留理由集中在[DEV 记录](../quality/reports/2026-10-17-PONYTAIL-CLEANUP-DEV.md)。
- 原始历史报告与证据保留；C01–C31、真实门和 UI 守卫未降低。报告索引只提供固定版本导航，不作为第二份当前状态。
- 用户已另行批准本机空间清理：三个历史 worktree 与五个缓存/输出目录已删除，8/8 动作 exit 0，全部分支保留。移除目录原分配占用约 1.77 GiB；约 388 MiB 恢复包及 1,649 项非再生材料/浏览器原件校验后保留，未动主工作目录、依赖环境或 `.local` 原件。见[逐项回执](../quality/reports/evidence/2026-10-17-ponytail-local-cleanup/receipt.json)。

## 当前产品能力与限制

今日宽屏左侧安排、右侧记录与导入，窄屏纵排，会议/任务默认 3/5 条可展开；保存和导入使用真实返回 ID 接续。审批清单进入单项 Markdown 阅读，按需编辑、来源和差异、未保存离开保护、多稿分别确认及首次索引提醒保持。该能力前轮合入与历史失败/修复证据见[今日/审批收口](../quality/reports/2026-10-17-FRONTEND-USABILITY-MERGE-CLOSEOUT.md)。

本轮 Python 731、Web 243、Ruff/format/mypy、typecheck/lint/build 及内部 App/DMG 技术构建与 packaged smoke 均通过；真实 `Test2` 的整理、索引、问答、飞书任务/日历/妙记搜索已调用真实 provider。既有两条 Oxlint warning、Starlette/httpx 弃用提示及约 605 kB bundle advisory 保留。前轮 Playwright artifact ENOENT 的根因仍未确认；本轮未再现，不宣称已修复。

真实飞书材料导入、任务写回、业务材料、已安装 App/公证、五日/双机/发布、整站完整业务和 WCAG AA 审计仍 **NOT_RUN**；runtime model metadata **UNVERIFIED**。本轮 PASS 不代表完整产品或发布通过。
