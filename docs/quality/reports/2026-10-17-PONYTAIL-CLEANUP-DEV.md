# 文档入口精简批次一 — Developer 记录

日期：2026-10-17
基线：`6f8fe80558d6e51481f6a3dd203c7e53e6faad89`
分支：`codex/ponytail-cleanup-20261017`
范围：仅仓库文档；不处理本机磁盘清理。

## 交付

- README 改为项目首页，保留能力、隔离开发启动、常用检查和文档入口；历史 DEV/QA 过程与 SHA 不再放在首页。
- PROGRESS 是唯一产品状态来源；LATEST 只记录当前文档任务、产品代码基线、QA 指令及状态链接。
- 同步 AGENTS、ADR 0008、实现/测试手册、对应提示词、文档与报告索引，以及完整 v1 计划入口说明。
- 修正架构中“不存在真实 Feishu HTTP adapter”的旧描述；API 文档不再把候选实现与旧阶段状态作为当前说明；ACCEPTANCE 不再声明当前 main 等同 M4.2 的旧 SHA。C01–C31、UI 十条守卫、产品范围、真实验收门均保留。
- 新增本批次唯一计划 `docs/superpowers/plans/2026-10-17-ponytail-cleanup.md`。既有报告/evidence 原件不修改、不删除。

## 文档处置理由

README 原有大量历史里程碑细节、旧固定 SHA、逐轮 QA 和面向已完成阶段的操作提示，混淆了首页与状态账本的职责；重写为精简项目入口。PROGRESS 保留产品基线与未测范围，并仅增补文档批次状态。LATEST 原来复制多轮报告内容，改为可执行交接。手册与 prompt 移除旧阶段开场、候选与历史操作指令，统一链接权威状态和验收标准。ARCHITECTURE/API/ACCEPTANCE 的实现性旁注改为当前契约或明确历史注记，不改产品规格迁就源码。

## 检查

实现前 HEAD/分支/工作区检查：`pwd && git status --short --branch && git rev-parse HEAD && git branch --show-current` — **PASS / exit 0**；初始工作区 clean，HEAD 与分支符合任务指定值。

以下检查在修改后执行并填入实际退出码：

| 检查 | 结果 |
|---|---|
| 本地 Markdown 链接与锚点（20 份当前文档） | PASS / exit 0；检查 265 个本地链接、0 个错误。BASE 有 1 个原有失效锚点，已修正为实际标题 `#1-库与身份` |
| 当前入口失效指令/旧状态扫描 | PASS / exit 0；无旧阶段提示作为当前入口，无旧三处状态维护口径 |
| 受保护历史报告/evidence base→worktree | PASS / exit 0；`git diff --name-status BASE -- docs/quality/reports` 仅显示允许更新的索引 README；新增本 DEV 报告为本轮文件，其他历史报告与 evidence 未变 |
| `src tests web native scripts` 与依赖树未变 | PASS / exit 0；`git diff --quiet BASE -- src tests web native scripts pyproject.toml uv.lock web/package.json web/package-lock.json` |
| `git diff --check` | PASS / exit 0 |

未运行产品全量测试、浏览器、DMG 构建或真实服务：本批仅改文档，任务要求使用文档专项 QA。真实 provider/Feishu、业务材料、OS Keychain、用户安装/公证、五日/双机/发布等仍按 PROGRESS 标为未测；本轮没有采集 runtime 模型元数据。

一次正则化链接扫描器将 FRONTEND-GUIDE 的正文误读为路径并报错；该次未形成文档检查结果。随后使用过滤空格目标、校验文件与锚点的检查器重跑，结果见表格。

对整个 `docs/**/*.md` 的探索性扫描检查了 382 份文档和 1,153 个链接，发现 28 个历史报告/evidence 内的旧绝对路径、归档 harness 参考或报告行号锚点。该扫描不是验收门；涉及的历史原件均未改动，当前入口与本轮相关文档的 265 个链接已单独通过检查。

Developer 自测不代表 fresh QA 或 Sol gate 通过。QA 应按 [LATEST-IMPLEMENTATION](../../handoff/LATEST-IMPLEMENTATION.md) 在独立 checkout 验收其指定的完整固定 SHA。
