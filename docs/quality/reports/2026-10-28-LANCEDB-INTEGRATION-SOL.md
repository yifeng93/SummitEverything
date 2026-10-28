# LanceDB 整合到主开发分支：Sol 复核

日期：2026-10-28。目标目录 `/Users/hanwenbo/ai/SummitEverything`，目标分支 `codex/mcp-workbench-prototype-20261023`。固定代码提交 `193aa35a33c667a41a9fe125db4f0caf50d62545`，后续收口提交仅更新文档与证据。来源为隔离分支 `596ddab6b6c1b82ad43f283990f4a1076694fa9a` 的索引实现，按本次范围整合，不引入其旧 UI/native 修改。

## 实际结果

LanceDB 索引代码、锁定依赖、旧 SQLite 向量不迁移策略、并发发布保护、相关脚本与契约已在目标分支提交。目标 `.venv` Python 3.13.2 arm64 实际 import 验证 `lancedb 0.40.0`，安装位置在主目录，未把依赖只留在隔离 checkout。SQLite 继续记录活动代和业务状态；正文、向量与中文全文索引在 profile 的 `index.lancedb`。旧 SQLite 索引需要用户显式重建，本任务没有执行真实重建。

独立 QA 的固定提交检查 **109 passed**，固定提交加主工作树三个 Python/测试文件的哈希快照 **110 passed**，均 exit 0。组合包括现有检索性能优化及 API 状态扩展；资格门、生成后实时引用复验、显式重建、发布失败/并发、已有 LanceDB 读取与检查器只读测试通过。完整新 UI 不在本次 QA 范围。

DEV 相关回归 **107 passed**，Ruff check/format、mypy、lock 校验与目标环境同步均 exit 0。全量 Python 首跑是 **748 passed / 1 failed，exit 1**：R4 deadline 用例首轮 0.404s 超过 0.25s 阈值；同一用例不改阈值重跑 **1 passed，exit 0**。因此不能称全量一次通过，也未证明时序偶发根因。Sol 执行当前 UI TypeScript 检查 exit 0，仅代表当时类型检查。

QA 发现交接文档仍写候选 SHA 待填写；收口已补齐完整 SHA，并核对后续修改只涉及文档证据，产品代码未变。原始 QA 报告保持不改。

## 原有改动与交付边界

固定提交没有 `web/`、`native/` 或 `prototypes/` 文件。原有 query 性能优化与对应测试保留在主工作树未提交，已按哈希组合验收；索引查看脚本及其测试属于本次适配，一并提交。暂存区在代码提交后为空。

初始记录是 54 个文件与 2 个目录条目；43 文件字节保持，8 个共享文件为本次集成修改，另有 3 个非本任务编辑的 UI 文件在任务期间字节变化并原样保留。2 个目录没有初始递归哈希，不声称全工作树逐字节不变。详见 [保留记录](evidence/2026-10-28-lancedb-integration/preservation.json)。没有删除原有文件，也没有回滚非本任务修改。

未推送、未合并 main、未重新打包、未重启开发服务或已安装 App。没有调用真实 provider/材料/飞书/Keychain、seed 或重建既有 profile。App/DMG、真实模型质量、五日、双机、公证与发布仍 NOT_RUN；runtime model metadata UNVERIFIED。

## 证据

- [独立 QA 原报告](evidence/2026-10-28-lancedb-integration/qa/REPORT.md)
- [检查结果与退出码](evidence/2026-10-28-lancedb-integration/verification.json)
- [固定与组合快照输入](evidence/2026-10-28-lancedb-integration/qa-input.json)
- [原始日志与文件哈希](evidence/2026-10-28-lancedb-integration/SHA256SUMS.json)
