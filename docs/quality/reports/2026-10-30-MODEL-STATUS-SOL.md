# 模型状态提示修复：Sol 复核

日期：2026-10-30。用户要求已成功调用过的模型不再显示「尚未验证」，同时修正本地模型状态。

## 固定版本与范围

- 输入快照：`f63d0debc7c7f4c5839c575dd6dcee657225495a`，用于隔离当前并行源码，不作为本任务改动。
- 首轮产品：`24305e89fa41db41267fcf7a6363c5578b9a2272`，独立 QA FAIL。
- 最终产品：`1e0347401de170919a526b6027f73e35430396be`；分支 `codex/model-status-evidence-20261030`。DEV 与两次全新 QA 使用独立 worktree；QA 未改源码或 tracked tests。
- 验收时主目录为 `codex/mcp-workbench-prototype-20261023`，本切片通过窄补丁应用。用户随后指定提交并推送到 `hanwenbo-dev-202610`；推送前已核对该分支与远端同步，仅纳入本切片及其验收记录，其他未提交修改保留。未发布安装包。

## 修正后的行为

DeepSeek 状态复用本机账本中匹配当前工作库/profile/配置与凭据代次的成功终态和服务用量记录；保存配置不是成功证明。密钥替换/删除会使旧证据失效。合成连接检查结果也保存在本机，普通状态读取不发起模型请求。最近失败或未知与历史成功分开，账本不可读不阻断其他设置读取。

本地向量化、排序分别核对模型文件、provider 和 enabled。已准备模型进度为 100%；未准备、准备失败、文件不完整、停用均有对应状态。状态回调更新本地能力，不覆盖用户未保存的设置。

## 门与证据

| 门 | 结论 | 证据 |
|---|---|---|
| DEV 修复轮 | PASS：原失败用例+状态+设置接口21项，Ruff/format/mypy | [原始检查](evidence/2026-10-30-model-status-sol/dev-repair1-checks.json) |
| 首轮独立 QA | FAIL：不可用 Keychain 前提前创建代次目录；baseline同测试PASS | [首轮报告](evidence/2026-10-30-model-status-qa1/REPORT.md) |
| 全新最终 QA | PASS：后端26、前端25、typecheck、浏览器三种状态与刷新重开 | [最终报告](evidence/2026-10-30-model-status-qa2/REPORT.md) |
| 主目录组合 | PASS：后端26，生成API类型、typecheck均exit0 | [后端日志](evidence/2026-10-30-model-status-sol/main-backend.log)、[类型日志](evidence/2026-10-30-model-status-sol/main-typecheck.log) |
| 当前页面实测 | PASS：已有真实成功记录、本地ready100%、三行准确；刷新及重开保留；无console error/写请求 | [只读结果](evidence/2026-10-30-model-status-sol/live-result.json) |
| 安装包/真实凭据变更/全量 | NOT_RUN | 本轮没有新模型调用、没有替换真实凭据 |
| Agent运行时模型元数据 | UNVERIFIED | 不从模型配置推断运行时暴露信息 |

首次QA浏览器harness错误将action-intents返回数组，导致页面崩溃并记BLOCKED。最终QA按真实分页schema修正harness后通过；未改产品来迁就测试。此前将Keychain用例称为“原有失败”的判断已由baseline对照纠正，原失败证据保留。

## 实际页面验证

URL `http://127.0.0.1:5173/`，标题「SummitEverything — 本地知识工作台」。Browser plugin not available，使用仓库 Playwright。设置→今日→设置→刷新→设置，均显示「已就绪」「最近调用成功」和两项「本机可用」。桌面1440×1000与窄屏390×844已截图；页面非空、没有框架错误层、console/page error为0。本轮没有写请求，未新增模型调用。截图保留本机 `.local/model-status-evidence/live-model-card.png` 和 `live-model-card-mobile.png`；真实当前页面不随源码提交。

应用时主目录的 TasksPanel 未使用类型已被并行工作删除，与候选相同，因此跳过重复补丁。15个非生成/状态文档文件与候选逐字节一致；OpenAPI与TS类型保留主目录并行内容后重新生成。当前进展唯一来源为 PROGRESS，最新交接仅保留固定候选与本报告指针。
