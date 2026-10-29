# 本地检索 + DeepSeek：桌面 Web 复核

用户明确选择不再依赖百炼，向量化、召回和排序由本机完成，DeepSeek 仅整理与回答。2026-10-30 用户进一步限定本轮只验桌面 Web，不开展移动端兼容工作。

## 固定源码与落地

- 产品源码：`a67e12bf580bcf01be611578f1e8c163a66a63f0`；分支 `codex/local-retrieval-deepseek-20261029`；基线 `b737a4c1a2c14c6641347353414f1a0cf7631e6f`。固定候选经全新 QA 在独立 checkout 验收，未修改被测源码。
- 54 个任务文件增量已应用 `/Users/hanwenbo/ai/SummitEverything`，主目录分支仍为 `codex/mcp-workbench-prototype-20261023`。保留其他任务改动；API 契约保留并行飞书日历只读规则，AskView 保留并行对话缓存，UI allowlist 仅调整本轮计数。
- 主目录前后文件哈希和三处合并说明见 [应用清单](evidence/2026-10-30-local-retrieval/sol/applied-manifest.json)、[合并清单](evidence/2026-10-30-local-retrieval/sol/merge-manifest.json)。开发服务 5173 已提供新的问答模块，8793 OpenAPI 已包含模型准备接口。未推送、未发布或修改已安装 App。

## 用户可见行为

- 设置中明确准备约 95 MB 的本地中文模型，固定文件与版本、校验后原子安装，失败可重试；业务推理不自动下载或回退云端。
- 正式检索使用 512 维本地模型和现有 LanceDB。长文本按模型窗口拆分并保留原文引用；同义问句、错误数字前提、跨项目隔离、无关问题和长文尾部有有界实测。
- Fake 预览仍可不下载模型运行。旧索引与新模型指纹不匹配时必须明确重建；切换后先确认正文仍保存成功，并提示手动准备索引，不把新向量写入旧代。
- 本地索引不申请云端调用额度；问答只为 DeepSeek 回答申请一次性授权。问答页不再要求百炼密钥，缺模型或旧配置迁移提示可进入设置并保留原问题。
- 旧百炼配置兼容读取，运行时拒绝调用云端向量化与排序；迁移不自动删除旧凭据。正式正文仍需用户确认。

## 验收结果

| 检查 | 结果与边界 |
|---|---|
| 独立固定 SHA 后端全套 | PASS，808 passed / 6 skipped；跳过项需显式本地模型目录 |
| 独立真实本地模型专项 | PASS，7/7；小型合成资料，Python socket 拦截，不推断普遍检索质量或操作系统级断网 |
| 独立前端与静态检查 | PASS，295/295（4 workers），typecheck/build/lint、Ruff/format/mypy/lock |
| 独立桌面浏览器 | PASS，1440×900 下 4/4：无百炼密钥的问答确认和单次发送、当前引用打开正文、缺模型恢复、设置准备失败重试/迁移、本地索引确认；浏览器 API 为合成路由 |
| 实际 FastAPI + 本地模型闭环 | PASS，导入→MockDeepSeek 整理→明确批准→本地索引→问答计划→SSE→当前正文 hash；普通与模型迁移流程均通过。回答使用 MockTransport，未真实调用 DeepSeek |
| 产品模型下载适配器 | PASS，固定 SHA 下载公开 95,330,972 字节，本机约 19.187 秒就绪；固定 size/hash 全通过。仅隔离测试目录，使用 90 秒整体测试期限 |
| 主目录组合后端 | PASS，814 passed / 6 skipped，退出码 0；包含现有并行改动 |
| 主目录组合前端 | PASS，298/298（2 workers），退出码 0；首次 4 workers 为 297/298，来源选择用例未及时出现提示。原测试未改，单 worker 专项 33/33 后全套复跑通过 |
| 主目录组合桌面与 API | PASS，桌面 4/4、typecheck、真实本地模型+MockDeepSeek 迁移闭环；旧代保护、当前引用和凭据读取边界均通过 |

独立 QA 首次在前端依赖未安装时有 3 个开发启动器失败；补齐 npm 依赖后专项 4/4、完整后端 808/6 skipped 通过。历史大范围 Ruff 扫描包含既有证据文件而失败，正式 source/tests 范围通过。DEV 原始失败及修复过程、QA harness 初期数据问题均保留，不能把首次失败记作通过。

## 仍需单独确认或验收

- 当前用户开发库的配置、凭据与索引未自动切换；真实凭据保存和对现有已确认正文建索引，等待用户明确选择。代码接入完成不等于该工作库已经启用。
- 本次未追加真实 DeepSeek 调用：此前 100 次和追加 5 次预算均已用完；真实整理/回答质量的旧证据与当前完整模拟链路分开。
- Keychain 生命周期、真实业务资料、实际 MCP 客户端完整调用、安装 App/DMG、macOS 13 实机、签名公证、双机、五日及发布 NOT_RUN；runtime 元数据门 UNVERIFIED。
- 移动端不在用户本次要求范围，不做手机样式兼容结论。

## 可复验证据

- [独立 QA 报告与命令退出码](evidence/2026-10-30-local-retrieval/qa/REPORT.md)
- [DEV 原始交接](evidence/2026-10-30-local-retrieval/dev/DEV-REPORT.md)
- [主目录后端](evidence/2026-10-30-local-retrieval/sol/main-backend.log)、[前端最终](evidence/2026-10-30-local-retrieval/sol/main-frontend-rerun.log)、[桌面浏览器](evidence/2026-10-30-local-retrieval/sol/main-desktop-browser.log)、[API 闭环](evidence/2026-10-30-local-retrieval/sol/main-http-flow.log)
- [公开模型下载与校验](evidence/2026-10-30-local-retrieval/sol/product-model-download.log)、[全部证据哈希](evidence/2026-10-30-local-retrieval/manifest.json)

证据不含模型权重、真实凭据或业务原件。测试启动的隔离 Vite 服务均已停止，现有开发服务保留。
