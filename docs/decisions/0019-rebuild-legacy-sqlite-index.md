# ADR 0019：旧 SQLite 向量索引需显式重建

- 状态：已采纳
- 日期：2026-10-28
- 决策范围：本机向量索引的旧格式处理，不改变 Markdown 权威源、用户确认门、索引范围确认或检索资格语义。

## 背景

旧版把向量放在 profile 的 SQLite `chunks.vector_json` 中。后来改用 LanceDB 后曾保留自动本机迁移，以避免重新嵌入。实际用户数据规模很小，兼容迁移没有足够收益，反而保留了双格式读取、迁移失败与重试路径。

## 决策

- SQLite 只保存 LanceDB 活动代指针和 generation history。新 profile 不创建旧 `chunks/vector_json` 表。
- 对旧 SQLite-only 索引只读检查活动指针的结构与存在状态。status 报告 `legacy_vectors_require_rebuild`；query 不使用旧文本/向量且不触发 embedding；initial plan 可正常预览当前已确认 Markdown。
- 批准页面的自动增量只对可读的活动 LanceDB generation 执行。旧格式 index 视为没有当前可用代，页面批准不会顺带开始索引。
- 用户通过已有索引预览与执行路径明确重建后，从当前已确认 Markdown 重新生成向量。该构建遵循 provider 配置及真实调用的一次性计划门。SQLite 控制列和 history table 的初始化与新 generation 指针发布在同一 SQLite 事务内；先完成并验证 LanceDB table，失败时不改旧控制状态，未发布的新代仍清理。
- 旧 SQLite `chunks/vector_json` 行与文件不自动删除、不搬运、不反序列化，供用户自行保留或后续处理。没有提供“清空所有数据”入口。
- 已存在的正常 LanceDB generation 继续原样读取、增量复用和原子替换；跨进程 lease、CAS、历史代保留、索引失败不发布及资格过滤均保持不变。

## 后果

旧索引在应用中不能直接查询，用户需要按当前确认内容重新建索引；若使用真实 embedding provider，建立索引会进入既有的显式预览和授权流程。旧向量不会自动转换，也不会被误认为当前可用索引。status/query/plan 不写旧 SQLite schema 或旧 chunks；SQLite-only profile 在真正发布新索引前也不创建 LanceDB 数据目录。

## 验收要点

- 新 profile 创建 SQLite generation control schema，不创建 `chunks` / `vector_json`。
- 用旧 SQLite-only schema 验证 constructor、status、query、plan 前后文件 hash 和 schema 不变；旧向量行不被消费，API 在 Real 设置下不自动启动索引；注入的计数测试 provider 调用数为 0。
- 页面确认不顺带重建；initial plan 可用，只有显式 index job 才嵌入并发布 LanceDB generation。
- 显式重建失败保留旧 pointer/schema/chunk 行；成功后只写新 LanceDB generation，旧行仍未消费。
- 既有 LanceDB 代的读取、增量复用、失败不发布与并发 generation 冲突继续通过相关测试。
