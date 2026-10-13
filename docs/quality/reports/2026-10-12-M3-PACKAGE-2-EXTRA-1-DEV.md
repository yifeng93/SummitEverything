# M3 包 2 extra 1 Developer 报告

日期：2026-10-12。用户在 repair 2/2 QA FAIL 后明确批准**仅一轮额外修复**。这是包 2 的 extra 1，不重置原 repair 1/2 与 repair 2/2 计数；不是 QA 报告或阶段结论。

## 固定代码与范围

- 起点：`36a0cc32757f761bd1c31abcddde07f1a2a426c6`。
- 固定源码 SHA：`bb997a42ed1d218e10527e3e07e6c587fc9929f6`，由提交 `6bc2f4f5a9c5bd2193e6eaaff39c9af868366ff6` 加后续来源引文边界提交组成。
- 文档-only 交接提交：固定 SHA 会在交接消息中提供；此提交只含 durable handoff 文档。
- 修复 Sol 门报告所确认的 QA-R2-01（批准证明与知识效力混淆）和 QA-R2-02（本人表达因普通词语误判材料）。保留首轮、repair 1/2 和 repair 2/2 的 FAIL 报告及证据；没有改写 QA 期望或降低资格门。

## 行为变化

`reader._approval_state` 继续调用统一的 `retrieval_eligibility`，但以 `HISTORY` 目的校验批准证明、页面资格和实际内容 hash。它把“这份当前正文是否曾被用户确认”与 metadata 的 `current / superseded / invalid` 知识效力分开。hash 相同且 proof 有效的 superseded/invalid 页面呈现为已确认的历史内容；PageReader 明示“已被替代”或“已失效，仅供历史参考”，不会把它提升为 current。invalid 页的显式确认仍保留 invalid 效力；真正外部改正文导致 proof hash mismatch 时仍为 `approval_state=invalid`，页面保持待确认及正文变化警告。CURRENT/HISTORY 查询和 citation 资格路径未更改。

记忆候选仍须来自实际保存的历史 user message、候选正文为该消息中的精确子串、请求明确 `user_expression=true`，且存在清楚的本人表达；候选保持 pending，只有单独用户确认后才成为 active。服务端现在检查候选在原 user message 中的语境：正文提到“资料没有提供”“引用来源”等不再自动当材料；被材料归属语句引出的片段、裸引号或 Markdown blockquote 中的第一人称偏好仍拒绝。先前另一段材料引文不会污染消息里后续独立的本人偏好；本人偏好中引用一个普通术语（如“资料不足”）可作为 pending 候选。assistant 来源、伪 message ID、无本人声明、转述/粘贴材料仍被拒绝。

## 回归与自动检查

新增 API / reader 回归覆盖：approved superseded 与 invalid 页的批准状态；对 invalid 效力重新确认后不晋升状态；正文外部改动时 hash 不匹配仍无效；CURRENT/HISTORY 的资格边界保留。新增候选来源测试覆盖自然偏好提及“资料”“引用来源”、材料引文后另起的本人偏好、从材料引文中截取内部第一人称、裸引号与 Markdown 引文（整段及子串）、本人句中加引号的术语。AskView 和 PageReader 组件回归覆盖记忆确认、approved historical status 展示及真实 hash mismatch 时仍显示 reconfirm warning。

README 全量检查按依赖安装顺序运行：

| 命令 | 结果 |
|---|---|
| `npm --prefix web ci` | PASS，126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | PASS |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，407 passed，1 条既有 Starlette/httpx deprecation |
| `uv run ruff check src tests` / `uv run ruff format --check src tests` | PASS |
| `uv run mypy src` | PASS，40 source files |
| `uv lock --check` / `uv build` | PASS |
| `npm --prefix web run api:types` | PASS；生成后 `web/openapi.json` 与 `web/src/api/generated.ts` 无 diff |
| `npm --prefix web test` / `npm --prefix web run typecheck` | PASS，55 tests / 12 files；typecheck exit 0 |
| `npm --prefix web run lint` / `npm --prefix web run build` | PASS；保留 TodayView 与 ProjectsView 两条既有 lint warnings |

所有上述自动命令的原始 stdout/stderr 与真实 exit code 均保存在忽略目录 `.local/dev/m3-package-2-extra-1/raw-logs/`；最终矩阵每项 exit 为 0。此前新增回归经历预期 RED 后 GREEN；Developer 检查不能替代全新 QA。

## QA 交接

请在独立 checkout 固定产品源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，复验完整包 2，而非只跑新单测。重跑三份历史 package-2 QA 的适用范围、C13/C14/C19/C20/C21 和实际 WebUI 路径，重点覆盖：批准且 hash 一致的 superseded / invalid 页展示及 CURRENT/HISTORY 行为；外部编辑 hash mismatch 与重新确认仍显示内容变化；本人自然表达含资料、引用、来源时可创建 pending 并仅在显式确认后 active；从真实 user message 的材料引文中抽出的第一人称片段、裸引文、Markdown quote、assistant / 伪 ID / 转述 / 粘贴必须拒绝；history attribution 后续独立偏好不误拒。保留 comparison/plan 多材料、此前主体识别、指代、当前资格、角色/预算/replay 回归。

Developer 未运行独立 QA、未操作真实模型/服务/材料/凭据/Keychain、未启动包 3 或合并。真实/native/DMG/五日/双机及发布门仍 NOT_RUN，runtime 元数据 UNVERIFIED。若本轮 QA 仍 FAIL，用户授权的额外自动修复额度耗尽，应停止并请用户决定后续。
