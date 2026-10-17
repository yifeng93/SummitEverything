# 文档入口精简批次一 — 独立 QA 报告

日期：2026-10-17

受测 SHA：`f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796`

对比基线：`6f8fe80558d6e51481f6a3dd203c7e53e6faad89`

范围：仅文档入口精简批次一；不运行产品测试或构建。

## 判定

- **文档专项：PASS**。README、状态来源、当前交接、链接与保护范围检查符合本批验收要求。
- **产品/应用门：NOT_RUN**。本轮验收范围不包括 C01–C31 的产品行为复演、UI、构建包、真实服务、凭据或多机/多日门；不得据此推断产品整体通过。
- **runtime metadata：UNVERIFIED**。本轮未启动应用或读取运行时元数据。

Sol 负责最终 gate 判定。

## 实际检查

| 检查 | 实际命令/方法 | 结果 |
|---|---|---|
| 固定目标与起始状态 | native worktree 从完整 SHA 创建；`git rev-parse HEAD`；创建 QA evidence 前 `git status --short` | PASS；HEAD 与受测 SHA 相等，初始无工作区改动 |
| 当前入口及 Markdown 链接 | `python3 docs/quality/reports/evidence/2026-10-17-ponytail-docs-qa/check_docs.py` | PASS，exit 0；18 份入口/契约文档，271 个本地链接与锚点检查，0 错误 |
| 源码与配置树 | checker 的 base→target changed paths；并运行 `git diff --quiet BASE TARGET -- src tests web native scripts .github/workflows pyproject.toml uv.lock package.json package-lock.json` | PASS，exit 0；产品、测试、Web/native、脚本、workflow、依赖树均未变 |
| 产品规格 | 三个受保护规格的 BASE/TARGET Git blob ID 对比 | PASS；PRODUCT-SPEC、FRONTEND-GUIDE、FRONTEND-PAGE-SPECS 均逐字节不变 |
| 验收标准 | BASE/TARGET 的 ACCEPTANCE C01–C31 与 R01–R05 行逐行比较 | PASS；31 个 C 行及 5 个真实门行均逐字节相同。前端守卫所在两份前端规格 blob 未变；AGENTS 与 TESTER 中独立 QA 和最多两轮 repair 规则仍在 |
| 历史报告与证据 | 用 `git ls-tree -rz` 获取 BASE/TARGET 路径及 blob ID，checker 逐项比较 `docs/quality/reports/**` 所有 BASE 既存文件，跳过允许更新的 reports/README.md | PASS；检查 3,348 个既有文件，删除 0、内容变化 0。检查包含原始 DEV/QA、日志、manifest、签名与 evidence 内容，不是依赖 DEV 摘要 |
| 空白与补丁格式 | `git diff --check BASE..TARGET` | PASS，exit 0 |
| README 命令入口 | checker 检查能力/开发/检查/导航区块、`web/package.json` 中 test/typecheck/lint/build 脚本及 runner、lockfile、Swift package 路径存在 | PASS。命令本身未执行；产品检查不在本批范围 |

详细可复验脚本和原始检查输出位于 [本轮 evidence](evidence/2026-10-17-ponytail-docs-qa/README.md)。

## 观察与限制

README 已承担项目首页用途、能力说明、隔离开发启动、常用检查及文档导航；详细步骤链接到实现/测试手册。AGENTS、docs 索引和各当前入口把产品状态指向 PROGRESS；LATEST 当前内容限于本次文档任务、固定产品代码基线、QA 指令和 PROGRESS 链接。当前入口中没有要求重启旧 Stage B/M1 等阶段的启动指令；完整 v1 计划按计划与历史用途标示，旧报告索引内容属于明确历史记录。

所有对比基于固定 BASE→TARGET Git tree。目标提交期间 HEAD 未变化。QA 期间只新增本报告与其 evidence 目录；最终状态见 evidence 目录 README 所指的本报告/后续证据提交记录。仓库其他历史文件中既有旧引用不属于本批改写范围；本次验证聚焦当前入口，不把全仓历史引用清理作为门槛。

## 缺陷

未发现本批范围内的缺陷。产品行为与外部/发布门保持 NOT_RUN。
