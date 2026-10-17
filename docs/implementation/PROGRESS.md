# 实施进展账本

本页是当前产品状态的唯一维护处。固定版本的原始报告见[报告索引](../quality/reports/README.md)，执行入口见[最新交接](../handoff/LATEST-IMPLEMENTATION.md)；旧阶段过程见[历史账本](PROGRESS-HISTORY-2026-10-16.md)。

## 本轮修复（2026-10-17，已合入 main）

- PR [#25](https://github.com/yifeng93/SummitEverything/pull/25) 已按正常 merge commit
  合入，merge `2e76f4c94d1f77e2b7285e93b7ef9ef7526a9bc2`；产品修复提交
  `c82aecf09b195ddcbae40e3b5c5db31d959aea6e`，基线 `e1bbcee`。合并后 main 产品树与
  `c82aecf` 完全一致。
- 修复四组用户可见问题：百炼点分隔 API key 被旧白名单误拒；整理提示词与 `kind` schema
  冲突导致真实整理失败；已提交计划不可取消时对话框仍提供取消并显示英文；页面标题未参与
  检索 scope 导致已确认页面 0 引用。详见[检索修复与真实验证](../quality/reports/2026-10-17-RETRIEVAL-TITLE-SCOPE-DEV.md)、[整理 DEV](../quality/reports/2026-10-17-ORGANIZE-KIND-FIX-DEV.md)、[独立 QA](../quality/reports/2026-10-17-ORGANIZE-KIND-FIX-QA.md)。
- 离线回归：Python **731 passed**、Web **241 passed / 26 files**、Ruff/format/mypy、
  typecheck/lint/build、内部 App/DMG 构建、codesign、hdiutil verify 与 packaged smoke
  通过；两条既有 Oxlint warning、Starlette/httpx 弃用提示和 603.86 kB bundle advisory
  保留。
- 真实 `Test2` 工作库验证：整理 job `8c79b00d-…` completed，12 份稿，DeepSeek
  3137 输入 / 1408 输出 tokens；索引 4 chunk，百炼 embedding 299 tokens；问答
  “学员28号晚住宿需求自动勾选流程是什么？”得到 **1 条引用**，真实调用 embedding
  28 / rerank 85 / DeepSeek 390+588 tokens，回答忠实于已确认页面。
- 内部候选 DMG：`.local/internal-builds/c82aecf-20261017/SummitEverything-Internal-c82aecf.dmg`
  （source `c82aecf`，`dirty=false`，SHA-256 `775d147b…f6c5`）；未公证。
- 真实飞书 OAuth/读取、已安装 App/公证、五日、双机、发布、整站完整业务和 WCAG AA
  审计仍 **NOT_RUN**；Keychain 在真实整理/查询中可用，但完整生命周期未单独验收；
  runtime model metadata **UNVERIFIED**。

## 上一轮精简（2026-10-17）

- README 已重构为项目首页；实现、验收和文档入口按职责整理，旧状态不再充当当前指令。
- 文档固定 SHA `f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796` 的独立文档 QA **PASS**。代码固定 SHA `2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`；完整受测候选 `5835faa72b513202e92694f4fa14790afefe1e70` 的独立离线代码与内部包技术门 **PASS**，Sol 已核验原始证据。两次常规 QA，无产品修复轮；后续交接/证据提交不改变受测产品树。见[Sol 最终门判断](../quality/reports/2026-10-17-PONYTAIL-CLEANUP-SOL-GATE.md)。
- 产品源码仅删除无调用的 `job_attempt_hash` 四行定义。归档摘要、版本链校验、全部测试与断言、依赖、界面、API 和生成类型保持；没有证据支持进一步删依赖或合并回归测试。候选与保留理由集中在[DEV 记录](../quality/reports/2026-10-17-PONYTAIL-CLEANUP-DEV.md)。
- 原始历史报告与证据保留；C01–C31、真实门和 UI 守卫未降低。报告索引只提供固定版本导航，不作为第二份当前状态。
- 用户已另行批准本机空间清理：三个历史 worktree 与五个缓存/输出目录已删除，8/8 动作 exit 0，全部分支保留。移除目录原分配占用约 1.77 GiB；约 388 MiB 恢复包及 1,649 项非再生材料/浏览器原件校验后保留，未动主工作目录、依赖环境或 `.local` 原件。见[逐项回执](../quality/reports/evidence/2026-10-17-ponytail-local-cleanup/receipt.json)。

## 当前产品能力与限制

今日宽屏左侧安排、右侧记录与导入，窄屏纵排，会议/任务默认 3/5 条可展开；保存和导入使用真实返回 ID 接续。审批清单进入单项 Markdown 阅读，按需编辑、来源和差异、未保存离开保护、多稿分别确认及首次索引提醒保持。该能力前轮合入与历史失败/修复证据见[今日/审批收口](../quality/reports/2026-10-17-FRONTEND-USABILITY-MERGE-CLOSEOUT.md)。

本轮 Python 731、Web 241、Ruff/format/mypy、typecheck/lint/build 及内部 App/DMG 技术构建与 packaged smoke 均通过；真实 `Test2` 的整理、索引与问答已调用真实 provider 并得到正确引用。既有两条 Oxlint warning、Starlette/httpx 弃用提示及 603.86 kB bundle advisory 保留。前轮 Playwright artifact ENOENT 的根因仍未确认；本轮未再现，不宣称已修复。

真实飞书、业务材料、已安装 App/公证、五日/双机/发布、整站完整业务和 WCAG AA 审计仍 **NOT_RUN**；runtime model metadata **UNVERIFIED**。本轮 PASS 不代表完整产品或发布通过。
