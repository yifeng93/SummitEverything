# 整理 kind 解析与失败取消修复 — Developer 记录

日期：2026-10-17
分支：`codex/organize-kind-fix-20261017`
基线：`c5379848808ea0cbde030d9d61ad230bb7bdfe12`（含 API key 形状修复的文档提交）
产品修复提交：`c59d7a7016b0effa86d9073d7e8aca19f5cce9a9`
后续测试提交：`9f265da`

## 现象（用户真实试用）

用户用一份测试逐字稿在 `Test2` 工作库发起“整理所选材料”，界面报：

> 模型服务不可用：返回内容不符合应用要求的字段。

随后点“取消”，界面报：

> an executing or completed plan cannot be cancelled

诊断与工作库状态：

- 整理作业 `9f1d8732-…` 状态 `failed`，错误 `proposals schema mismatch: kind`。
- 来源 `37b1337d-…` 状态 `failed`；没有生成稿件，没有写入正式知识。
- `acceptance-plans.json` 中 `model.organize` 计划状态 `unknown`，已记录 DeepSeek 返回
  `input_tokens=3114`、`output_tokens=1523`、`total_tokens=4637`，请求已真实发出并计费。
- `unknown` 是终态；按状态机不能再取消，所以取消报错本身符合后端规则，但界面不应在
  作业提交失败后继续提供取消按钮，也不应把英文状态机文案显示给用户。

## 根因

1. **提示词与 schema 冲突**：`DeepSeekLLM.organize` 的系统提示说
   “Preserve facts, ideas, suggestions, and unresolved items as distinct kinds”，
   但 `DraftProposal.kind` 只接受 `object / case / topic / decision`。模型按提示词返回了
   `fact` 等值，Pydantic 严格校验拒绝整批 proposals，作业失败。
2. **取消路径没有区分“预览”与“已提交”**：`SourceOrganizer.confirm` 在 job 请求失败后
   保留确认对话框；用户再点取消，DELETE 一个已 `unknown` 的计划，必然失败。
3. **英文状态机文案直接透出**：`PlanConflict` 的英文 message 经 API detail 原样显示。

## 修改

- 提示词明确：`kind` 只能是 `object / case / topic / decision`；事实、想法、建议、未决
  要区分在 `body` 中，不再称为“kinds”。
- `DraftProposal` 增加 `kind` 归一化：常见同义词（fact/idea/suggestion/unresolved/note/
  page/knowledge 与中文词）映射到 `topic`；未知字符串也回退 `topic`；只有非字符串值
  仍会校验失败。`kind` 只是待审稿的分类提示，不承担信任门禁。
- 计划状态机冲突统一翻译为中文；取消已提交/已结束计划时显示
  “这次操作已经提交或结束，不能再取消；请查看本次结果。”
- `SourceOrganizer` 记录 job 请求是否已发出：已发出后失败则关闭对话框，不再提供取消；
  取消冲突时显示中文并关闭。
- 整理失败后刷新来源列表，来源会显示“整理失败”，按既有 C05 规则用“明确重新整理”
  发起新 operation。
- 审批页对 `failed / cancelled / unknown` 整理结果分别显示业务语言，不再把 failed 写成
  “正在处理中”。

## 验证

| 检查 | 结果 |
|---|---|
| 定向 Python（真实模型适配、schema tolerance、计划账本、失败可见性） | 70 passed |
| 全量 pytest | 730 passed，1 条既有 Starlette/httpx 弃用 warning |
| 端到端真实适配器测试（模型返回 `kind=fact`） | 2 passed；稿件落为合法 `topic` |
| 全量 Web Vitest | 241 passed / 26 files |
| Web typecheck / lint / build | typecheck、build exit 0；2 条既有 Oxlint warning；主包 603.86 kB advisory |
| Ruff check / format / mypy | exit 0 |
| 内部 App/DMG 构建 | release、strict codesign、hdiutil verify 均 exit 0 |
| packaged smoke | PASS |

构建身份：

- `source_sha=c59d7a7016b0effa86d9073d7e8aca19f5cce9a9`
- `dirty=false`
- DMG：`.local/internal-builds/c59d7a7-20261017/SummitEverything-Internal-c59d7a7.dmg`
- DMG SHA-256：`9f14c726a0007d24da56b7c52753aee23452e74ba52aa4a1f9e1a82d67bcd540`

## 当前工作库的恢复方式

- 旧整理计划已是 `unknown` 终态，不需要也无法取消；它会在 10 分钟后过期，不阻塞新计划。
- 来源已是 `failed`，不会自动重发。打开 `Test2` 的审批 → 来源，选中该来源，指定主线/
  项目后点“明确重新整理”，会创建新的 operation 与新的 acceptance plan。
- 新计划确认后会重新调用一次 DeepSeek，可能再次产生少量 token 费用；旧失败请求已消耗
  3114 输入 / 1523 输出 tokens，不会自动重发。
- 没有生成稿件，也没有写入正式知识。

## 边界

- 本轮测试使用合成 HTTP 边界，没有再次调用真实 DeepSeek；真实 key 的 retry 由用户在应用内
  执行。真实 provider / 飞书 / Keychain / 安装与公证 / 五日 / 双机 / 发布仍为 NOT_RUN。
- 未执行独立 QA，未合并、未推送。
- 用户真实逐字稿内容、key 和 provider 原文未写入报告或仓库；只记录计数与字段名。
