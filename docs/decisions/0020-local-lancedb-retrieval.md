# ADR 0020：本机 LanceDB 检索存储

- 状态：已采纳（来源 LanceDB 分支原编号 0013；本仓库 0013 保留给当日 UI 决议）
- 日期：2026-10-23
- 决策范围：本机检索索引实现，不改变 Markdown 权威源、用户确认门或回答资格语义。

## 背景

原索引把向量作为 JSON 保存在 SQLite，并在每次问答时把全部向量读入 Python 做全局排序。需要原生向量检索与全文检索，同时保持本机独立运行、可重建和现有的版本 / 资格门。

## 决策

- FastAPI 继续使用 SQLite 管理索引指针和其他本地业务状态；chunk 正文、float32 向量与 BM25 全文索引保存在 profile 内的嵌入式 LanceDB（`index.sqlite3` 对应独立 `index.lancedb` 目录）。依赖锁定为经本机 API 验证的稳定发行版。
- 中文全文检索使用固定 n-gram tokenizer，不安装词典、不下载语言模型。召回保留向量与 BM25 候选并合并，之后仍只调用一次既有 provider reranker；推理与 embedding provider 继续按原设置独立控制。
- 每次构建写入新表；核验 schema、行数、维度和全文索引后，SQLite 以 `BEGIN IMMEDIATE` 比较上一活动代并原子切换指针。失败不改活动指针；并发过期构建拒绝发布。查询在开始时固定一代，代表不在查询中途更换。
- 每次检索仍调用统一的 `domain/content.py` 规则，并在 citation 前重读 Markdown。候选选择遍历原生引擎的精确排序结果以保留 planner、主题、comparison 覆盖与邻页语义；不把未完成资格筛选的 top-k 当最终结果。暂不建 ANN 索引，不声明近似召回质量。
- （已被 ADR 0019 取代）既有 SQLite 向量数据第一次访问时本机迁移至 LanceDB；当时决定保留旧行作为恢复副本。
- LanceDB 位于本机 profile，SQLite 继续作为 control plane；不引入 Docker、云端数据库或工作库数据同步。

## 后果

向量不再进入正常查询的 Python 反序列化路径，中文关键词可参与本机 BM25 召回。精确候选扫描保留完整 scope / coverage 行为，但语料增大时延迟和返回元数据成本仍要用合成基准量化；以后只有取得检索质量与过滤行为证据，才可考虑 ANN。

每个 profile 的 `.lock` 文件以系统文件锁协调跨进程操作：查询和代构建持共享租约，清理要求非阻塞独占租约并在锁内同时删除表及更新历史；有操作占用时清理会明确失败。用户仍须先退出应用，避免后续新进程在维护窗口开始。清理保留活动代及最近一个旧代。索引是缓存，若清理工具未运行会继续占据本机空间。

## 依据

- [LanceDB Quickstart](https://docs.lancedb.com/quickstart)
- [LanceDB FTS Index](https://docs.lancedb.com/indexing/fts-index)
- [LanceDB Table Updates](https://docs.lancedb.com/tables/update)
- [LanceDB Vector Indexes](https://docs.lancedb.com/indexing/vector-index)
