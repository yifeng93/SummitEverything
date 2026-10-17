# 最新实现交接

## 当前候选：API key + 整理 kind + 检索标题 scope（真实问答 PASS，待合并批准）

- 分支：`codex/retrieval-title-scope-20261017`；基线 `e1bbcee0f9e3e71e077e813db360cb3b802b57c3`。
- API key 修复提交：`f1f0982be75aadd9a74021a7ee5641317ddc2113`；整理修复产品提交：
  `c59d7a7016b0effa86d9073d7e8aca19f5cce9a9`；检索修复产品提交：
  `c82aecf09b195ddcbae40e3b5c5db31d959aea6e`。
- 已修复：百炼点分隔 key 被旧白名单误拒；整理提示词把 fact/idea 当 `kind` 导致
  `proposals schema mismatch: kind`；已提交计划不可取消时界面仍留取消按钮并显示英文；
  整理失败后来源状态与结果文案不准确；页面标题未参与检索 scope 导致已确认页面 0 引用。
- 自测：Python 731 passed；Web 241 passed；Ruff/format/mypy、typecheck/build 通过；
  内部 App/DMG 构建、strict codesign、hdiutil verify、packaged smoke 通过。
- DMG：`.local/internal-builds/c82aecf-20261017/SummitEverything-Internal-c82aecf.dmg`；
  SHA-256 `775d147bab3f4c6ce9c669b95e1a97464f15b9691952885550da29aa9de6f6c5`。
- 离线 QA：固定 `ad60394`（`c59d7a7` 产品树）A–E PASS；检索修复后全量 731 / 241、静态检查、DMG 身份与 smoke 通过。见 [key/整理 QA](../quality/reports/2026-10-17-ORGANIZE-KIND-FIX-QA.md) 与 [检索 DEV+真实验证](../quality/reports/2026-10-17-RETRIEVAL-TITLE-SCOPE-DEV.md)。
- 真实验证：`Test2` 整理 job completed（12 稿）、索引 4 chunk、问答 1 引用并真实调用 embedding/rerank/DeepSeek。
- 边界：已离线 QA + 目标真实查询验证，但**未合并、未推送**；真实飞书 / 安装与公证 /
  五日 / 双机 / 发布仍为 NOT_RUN。
- 恢复：旧 `model.organize` 计划为 `unknown` 终态，无法取消且会在 10 分钟后过期；来源为
  `failed`，在审批来源中选中后点“明确重新整理”即可创建新计划，旧失败请求不会自动重发。
- 合并：离线 QA + 真实问答建议合并；需用户批准后推送、跑 CI、按正常 PR 合并。真实
  DeepSeek / 百炼 embedding+rerank 已用 `Test2` 验证；飞书、安装/公证、五日/双机/发布
  仍是独立未测门。

## 已合入基线

Ponytail 精简已合入 `main`（`e1bbcee`）；当前产品状态唯一来源为
[PROGRESS](../implementation/PROGRESS.md)，其历史证据和 Sol 门见
[报告索引](../quality/reports/README.md)。
