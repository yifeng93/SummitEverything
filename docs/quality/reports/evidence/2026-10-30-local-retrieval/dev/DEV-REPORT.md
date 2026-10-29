# 本地检索 + DeepSeek 开发交接

## 目标与实现

- 基于 `b737a4c1a2c14c6641347353414f1a0cf7631e6f`，把真实 embedding、召回与排序切换为本机固定版本的 BAAI/bge-small-zh-v1.5（512 维）；DeepSeek 仅整理与生成回答。
- 新增 profile 内本地模型准备、固定下载源/版本/文件哈希校验、原子安装、进度/失败状态、超时、并发锁与显式重试。真实推理设置 `local_files_only` 与指定模型目录，不自动联网回退；Fake 保持独立离线实现。
- 保留 LanceDB、正式内容资格和索引计划的显式确认门。新模型指纹变化需要 `model_change` 计划；本地索引费用为零，不建立云端 acceptance plan。切换模型后未重建前，新确认内容留在旧索引代次并返回 `manual_required`。
- Legacy DashScope 设置可读取；运行时不调用退役云向量化/排序。设置页提供明确本地迁移入口，不展示/删除旧凭据。AskView 的 local provider 不再要求 DashScope key，模型未准备和服务器配置错码回设置且保留问题。
- 同步产品、架构、API、首次配置与界面规格，新增 ADR 0031；更新 API/OpenAPI/TS 类型及 macOS 构建 Python 版本选择（依赖锁支持 Python 3.12/3.13 的 macOS 13 兼容 ORT wheel，>=3.14 使用新 ORT 条件依赖）。

## 固定候选

- 分支：`codex/local-retrieval-deepseek-20261029`
- 基线：`b737a4c1a2c14c6641347353414f1a0cf7631e6f`
- 固定源码 SHA：`a67e12bf580bcf01be611578f1e8c163a66a63f0`
- 当前工作仅在 `/Users/hanwenbo/.codex/worktrees/offline-ask-schema/SummitEverything`；主目录及并行改动未编辑。

## 检查结果

| 检查 | 结果 |
|---|---|
| Python 全量离线，无模型目录 | PASS: 808 passed, 6 skipped；skip 为需显式真实模型路径的用例。日志 `pytest-fixed-no-model-rerun.log` |
| 固定本地模型真实检索与 MockDeepSeek 整理/问答审批流 | PASS: 7 passed，网络 socket 被测试拦截；日志命令见开发执行日志 |
| 前端全量 Vitest | PASS: 33 files / 295 tests，`npm test -- --maxWorkers=4` |
| 前端 TypeScript | PASS: `npm run typecheck` |
| 前端生产构建 | PASS；主 JS 约 809 kB，有 >500 kB 分包建议警告 |
| Oxlint | PASS，exit 0；保留仓库既有 React warning，LocalModelSetup 本任务新增 warning 已消除 |
| Ruff | PASS: check；format --check 为 114 files already formatted |
| mypy | PASS: 49 source files |
| uv lock | PASS: `uv lock --check` |
| diff whitespace | PASS: `git diff --check` |
| API 合成真实闭环 | PASS: 原件导入 → MockDeepSeek 整理 → 用户确认正式稿 → 真本机索引 → 一个 DeepSeek 计划 → SSE 引用及当前 hash 复核；2 mock calls、0 socket、0 云 embedding/rerank。证据 `http-flow-final.log` |
| Fake64 → local512 migration 合成闭环 | PASS: 切换后先批准页面仍 `manual_required`，显式 model_change 重建 2 页后问答引用通过；2 mock calls、0 socket。证据 `http-flow-migration-final.log` |

完整套件首轮出现两个失败：新 deadline 测试的 5 ms 超时受线程调度影响，已改为 50 ms 总限时和 80 ms mock 下载；既有 Stage B loopback 套件在整套并发运行时访问已关闭 socket。两测试隔离复跑 4/4 通过，最终无模型全套 808/6 skip 通过；Stage B 测试未改。较高默认 Vitest 并发下出现旧 5 秒用例超时，`--maxWorkers=4` 整套通过，未改 App 超时。

## 未测门与限制

- 未调用真实 DeepSeek 服务或读取/写入用户凭据；上述完整整理/问答闭环使用 MockTransport。真实 provider / Keychain 生命周期未测。
- 官方模型文件由既有隔离 probe 获取；本候选的下载生命周期以 synthetic downloader、hash/atomicity/timeout/retry 测试覆盖，未从本产品执行真实 95 MB 下载。
- 未构建/安装 DMG 或 app，未做公证、五日、双机或发布验收。Python ORT 平台条件已静态构建/lock 验证，但安装包仍是独立门。
- 独立 QA 尚未开始；等待 root 对固定 SHA 派发全新 QA。真实模型元数据未作为产品 runtime user-facing 证据，不宣称真实广泛检索质量。
