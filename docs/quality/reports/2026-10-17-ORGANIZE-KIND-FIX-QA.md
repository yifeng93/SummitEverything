# API key / 整理 kind / 失败取消 — 独立 QA 与 Sol 门

日期：2026-10-17
候选分支：`codex/organize-kind-fix-20261017`
候选 tip：`ad603942563c53312b4b1ff0cb96ae5d634d87fc`
产品修复提交：`c59d7a7016b0effa86d9073d7e8aca19f5cce9a9`（DMG 的 source_sha）
基线：`e1bbcee0f9e3e71e077e813db360cb3b802b57c3`

## 结论

**PASS（离线 / Mock 范围），建议合并。** 未发现阻断缺陷；真实 DeepSeek retry
（需要用户 key）以及真实百炼/飞书/Keychain/安装/公证/五日/双机/发布仍为
**NOT_RUN**，本轮结论不能替代它们。

## 独立验收对象

- 独立 checkout：`.local/qa/organize-fix-qa-20261017`，HEAD 精确为 `ad60394`，
  验收期间未移动；产品源码与 tracked tests 未改。
- 原始 QA 报告（忽略目录，不随仓库分发）：
  `.local/qa/organize-fix-qa-20261017/QA.md`。
- DMG：`.local/internal-builds/c59d7a7-20261017/SummitEverything-Internal-c59d7a7.dmg`
  SHA-256 `9f14c726a0007d24da56b7c52753aee23452e74ba52aa4a1f9e1a82d67bcd540`；
  `source_sha=c59d7a7…`、`dirty=false`。
- 产品树等价：`c59d7a7..ad60394` 与 `9f265da..ad60394` 对
  `src web native scripts pyproject.toml uv.lock` 的 diff 均为空；tip 后只有测试和文档。

## 逐项结果

| 项 | 结果 | 实际证据 |
|---|---|---|
| A 产品树与 DMG 身份 | PASS | 两条产品树 diff 为空；DMG SHA-256 匹配；codesign strict、hdiutil verify、packaged smoke 均 exit 0；build-info 身份正确 |
| B 点分隔 API key | PASS | 117 位、`sk-` 开头、3 个点的合成 key → 200 且 `credential_status.dashscope=true`、不回显；同长度含空格/换行/零宽 U+200B/内部引号 → 422 `credential_shape_invalid` 且不泄 key；含 `+/=.:` → 200 |
| C 整理 kind | PASS | mock `kind=fact` 的 plan→confirm→job→draft 全链路 job 201、draft kind=`topic`；`unresolved`/`summary` 同样 201/`topic`；同义词/未知值/中文值归一化通过，非字符串仍拒绝；system prompt 已明确四种 kind 且不含 `as distinct kinds` |
| D 失败后取消与状态 | PASS | `unknown` 计划 DELETE → 409 `acceptance_plan_conflict`，message「这次操作已经提交或结束，不能再取消；请查看本次结果。」无英文；SourceOrganizer 6 项（job 失败关框、不再调用取消、冲突中文并关闭）；ApprovalView 20 项；QA 渲染 4 项（failed/cancelled/unknown 中文文案 + failed 来源仍可“明确重新整理”） |
| E 全量回归 | PASS | Python 730 passed；ruff check/format、mypy exit 0；Web 241 passed / 26 files；typecheck/lint（2 条既有 warning、0 error）/build exit 0 |

Sol 复核额外执行：

- 重新运行 QA 三个 Python harness：9 passed；QA-only 渲染 harness：4 passed。
- 在 QA checkout 重跑全量 Python：730 passed；全量 Web：241 passed / 26 files。
- 复核独立 checkout、产品树 diff、DMG 哈希与 build-info，结果与 QA 报告一致。
- QA checkout 最终只多出 `QA.md`（未 tracked）；产品源码与 tracked tests 无改动。

## 非阻断观察（不计为缺陷）

1. 原始 QA 的 smoke 默认端口 18793 被一个既有 `summit-backend` 进程占用；QA 改用
   18893 后通过，未触碰该进程。
2. 未设置工作区 `UV_CACHE_DIR` 时，沙箱拒绝 `~/.cache/uv`（exit 2）；设置后全部通过。
   这是环境限制，不是候选失败。
3. `organizeResult` 结果面板位于来源专注视图，属于既有布局；本轮未改这一信息架构。
4. 失败的 `model.organize` 计划仍按既有状态机保持 `unknown` 终态，不能取消；新计划可用。
   旧计划不自动重发，这是预期行为。

## 未测与边界

- 真实 DeepSeek retry（用户 key、真实计费）：**NOT_RUN**；本轮只证明形状门禁、提示词、
  kind 归一化和完整 Mock 链路。
- 真实阿里云百炼 / 飞书 / Keychain / 用户工作库 / 已安装 App：**NOT_RUN**。
- 五日、双机、安装、公证、发布：**NOT_RUN**。
- 未使用或写入任何用户 key、真实材料、provider 原文；用户真实工作库未触碰。

## 合并建议

**建议合并。** 理由：A–E 全部 PASS，两个用户可见缺陷（点分隔 key 被误拒、整理 kind
导致 job 失败/取消英文提示）均有端到端覆盖；产品树自 `c59d7a7` 后未变，DMG 身份
与全量回归一致；未扩大产品范围或降低验收门。

合并前置 / 边界：

1. 先按正常 PR 流程推送候选、跑远端 CI；CI 成功、无冲突后合并。
2. DMG 的 `source_sha` 为 `c59d7a7`，tip 为 `ad60394`；已用产品树等价证明，不把 tip
   当成新的产品源码。
3. 真实 DeepSeek retry 仍是独立未测门；建议合并后在已安装候选上由用户重试一次
   `Test2` 的失败来源，确认真实 provider 行为。若真实 retry 失败，应停止扩大范围并
   按新证据修复，不能把离线 PASS 当作真实 provider PASS。
4. 合并属常规可复验变更，仍需用户明确批准；本 QA 未删除分支/worktree，也未移动固定 SHA。
