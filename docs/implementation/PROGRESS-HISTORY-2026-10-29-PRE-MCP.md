# 实施进展账本

本页维护当前产品与实现状态。旧阶段详细内容和本轮任务开始时的完整状态保留于[2026-10-28 索引集成前快照](PROGRESS-HISTORY-2026-10-28-PRE-LANCEDB-INTEGRATION.md)。固定版本的原始报告见[报告索引](../quality/reports/README.md)，当前候选执行入口见[最新交接](../handoff/LATEST-IMPLEMENTATION.md)。

## 当前分支与索引集成候选（2026-10-28）

- 目标为 `codex/mcp-workbench-prototype-20261023`，基线 `67b8169115fe166c819e2a5c410831798809c874`。该分支保留已有未提交的 UI 与静态原型修改；它们不属于本次代码提交或验收结论。
- 当前任务把隔离分支的 LanceDB 检索实现整合到本分支：SQLite 保存本机业务状态与索引 generation 指针，profile 下嵌入式 LanceDB 保存 chunk 正文、向量和中文 n-gram BM25 全文索引。检索保持精确候选扫描，不建立 ANN，不据此推断召回质量。
- 旧 SQLite `vector_json` 只读识别为需重建；status/query/plan 不读旧 chunk、不自动搬运或删除，也不自动调用 embedding。只有用户经现有初始索引预览与执行明确建立新代，才按当前已确认 Markdown 重建。检索时复用页面快照避免重复读取；答案生成完成后仍重新读取磁盘校验引用资格。
- Python 全量离线回归 exit 1：748 passed，1 failed。唯一失败为既有 Stage B deadline 时序用例，十轮中首次冷请求 0.404s 超过 0.25s 门限，后续九轮 0.152–0.156s；同一参数原样重跑 exit 0（1 passed）。索引/资格/并发/检查器回归组 exit 0（107 passed）。Ruff check、format check、mypy 与锁定依赖同步均 exit 0；具体日志及 dirty 文件保护结果见 [LATEST-IMPLEMENTATION](../handoff/LATEST-IMPLEMENTATION.md)。
- 本轮不清理或重建现有 profile/索引，不执行 seed，不调用真实 provider，不构建或重启 App。runtime model metadata **UNVERIFIED**。

## 已有 UI 原型（未提交）

UI 与静态原型改动保留在目标工作树，详情、用户确认状态与原始证据见[索引集成前快照](PROGRESS-HISTORY-2026-10-28-PRE-LANCEDB-INTEGRATION.md)。本轮不将原型交互、局部类型检查或旧版本测试结果视为当前完整产品验收。

## 既有离线与真实门

以对应固定版本报告和上述历史快照为准：以前的 Python/Web 检查与内部包结果不代表本次组合提交通过。真实材料与 provider、飞书导入/任务写回、真实 Keychain 生命周期、已安装 App/公证、五日、双机、发布及 WCAG AA 仍按各自门单独验收；当前不据旧报告推进这些门。
