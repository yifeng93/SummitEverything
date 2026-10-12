# M3 包 2 extra 2 独立 QA 报告

## 判定

**FAIL（包级门）**。C19 fresh-ready 无依据的 comparison 请求仍召回无关页面、生成不相关引用并调用答案 provider，属于证据错误（P1）。其余本轮实际覆盖的核心诊断和回归未发现新增阻断缺陷。Extra 2 是用户明确批准的最后一轮；按约定停止，不在 QA 修改产品，也不继续自动修复。

- 固定测试 checkout HEAD：`d2236c243ac28c86b94acd8e8dd139dc865b7b75`
- 产品源码 SHA：`c41147fe54bf95103c741df192fc76eb9df0f9e7`
- 两者产品树一致；`git diff --quiet c41147fe54bf95103c741df192fc76eb9df0f9e7 HEAD -- src web native tests` exit 0。
- 本报告的 harness、日志和证据目录：[`evidence/2026-10-12-m3-package-2-qa-extra-2-d2236c2`](evidence/2026-10-12-m3-package-2-qa-extra-2-d2236c2)。`manifest.json` 逐文件记录相对此根目录的 SHA-256。

## 缺陷：C19 fresh-ready comparison 对无关主题返回错误证据

合成 workspace 当前索引状态为 `ready`，6 pages / 6 chunks，`stale_pages=0`。没有任何已确认材料涉及“风铃工程”或“霜塔项目”的彩色牙刷储存规则。提交：

```text
POST /api/v1/queries
question = 比较风铃工程与霜塔项目的彩色牙刷储存规则。
answer_mode = comparison
purpose = current
```

实际 HTTP 200，返回了两个无关引用：page `00000000-0000-0000-0000-0000000003ed`（专项储备上限 3.6 万元）和 page `00000000-0000-0000-0000-0000000003ea`（朱雀项目设备预算上限 12 万元），并把它们写入 `source_statements`；答案 provider 调用计数从 4 增至 5。输出没有说明对比主体/指标缺失，`missing_information=[]`。预期是无引用、明确缺少相关依据、provider 调用数不变。可复现请求、完整响应、counter 和 SHA 存于 `harness/extra2-c19-results.json` 与 `harness/deepseek-payloads.jsonl`；原始运行输出及 exit 在 `raw-logs/c19-final.*`。

这不是之前已修复的 stale 诊断问题，也不是计数串联造成的假失败：真实 stale unrelated-page 对照不会污染 plan 诊断；此次 comparison 响应自身已带无关引文。按 ACCEPTANCE.md，证据错误为 P1，阻止 M3 包级通过。

## 本轮实际结果

- **PASS — C19 fresh-ready fact 与 plan 无相关依据。** fact 无引用/来源/推断/建议，missing 与主文一致，无 provider 调用。plan 由独立请求重新测量，HTTP 200、`ready`、无引用/来源/推断/建议、missing 清楚说明缺少方案依据，provider 计数 14→14。原 `c19-final` 中 plan 计数沿用 comparison 前快照，不能作为 plan 调用次数结论；保留原始日志，并以 `extra2-plan-counter-result.json` 独立实测为准。
- **PASS — C19 not-ready 与空索引。** not-ready 的 fact/comparison/plan 均返回 `not_ready`、无引用、明确提示先建索引，provider 不调用；empty-index 三模式同样无引用、提供缺失提示且不调用。
- **PASS — C19 无关 stale 与实际 hash 不匹配区分。** 真实 stale 页面与查询主题无关时，plan 不报缓存/资格异常且不调用 provider。实际正文 hash 从 `d2d264…cef4ab` 变为 `a92cb…7831aa` 时，系统说明正文和确认记录不一致，无引用且不调用 provider。
- **PASS — C19 provider 生成期间来源变动。** fake provider 生成期间分别修改内容、把页标成 superseded、删除被引页，答案均被作废、清除引用/来源/推断/建议并报告版本变化或页面不可用；没有泄露原引用内容。见 `generation-races-results.json`。
- **PASS — C13 浏览器历史资格。** 真实浏览器交互中，当前范围排除 superseded；历史范围的已确认 superseded 和 invalid 引用可打开，分别显示“已确认 · 已被替代”和“已确认 · 已失效”及历史效力提示。外部编辑 hash 后，页面变待确认、旧引用显示不可用提示。细节在 `harness/browser-ax-observations.md`。
- **PASS — C20 浏览器记忆确认和 API provenance。** 用户本人偏好先成为 pending，只有单独确认后成为 active；fake provider 的 `body.user_memories` pending 时为空、确认后含该偏好。历史真实用户问题继续位于有界 `previous_user_questions_for_reference_only`，按会话来源与记忆候选区分。引文、blockquote、材料内第一人称归属、assistant 答案、伪 request ID、未声明/false attestation 均拒绝；明确本人表达正控进入 pending。见 `extra2-memory-provenance-results.json` 与 `extra2-memory-prompt-results.json`。
- **PASS — C20/C14 budget 和请求状态。** 8,000 字符问题完整进入 provider payload；7,174-byte active-memory 超预算返回可读 HTTP 422 且 provider 不调用。角色指令超预算也返回可读 422、无 provider 调用。cancel 返回 202，SSE 唯一终态是 cancelled/error，历史无答案。partial SSE 后 SIGKILL/restart 保持 `interrupted` 与原 partial，不自动重发；稳定 ID 回放同一事件、不同 payload 返回 409（blackbox evidence）。
- **PASS — C21 profile 隔离。** 本机两个 profile 对同一 synthetic workspace 的历史/角色/记忆/索引相互隔离（blackbox evidence）。
- **PASS — README 自动矩阵。** `npm --prefix web ci`、`uv sync --locked --group dev`、带 offline guard 的 `pytest`（417 passed）、ruff check/format、mypy（40 files）、`uv lock --check`、`uv build`、OpenAPI types、web tests（55/12 files）、typecheck、lint、build 均实际 exit 0。保留既有 lint 两条 warnings 与 pytest 一条 Starlette/httpx deprecation。

context-boundary harness 的 8k 与 memory budget 断言通过，随后删除了本轮创建的两条大记忆（HTTP 204）。脚本的 cleanup 总结因 profile 中另有两条此前创建的 synthetic baseline memories 而显示 FAIL；不是删除失败或产品数据丢失。原始日志保留，未将该 fixture 清理误报为产品缺陷。

## 未运行与限制

- **NOT_RUN** — DevTools console/network（本次浏览器辅助界面未暴露这些面板）、真实模型/飞书、真实材料/凭据/Keychain、native/DMG、五日真实使用、双机。
- **UNVERIFIED** — runtime/model 元数据未实际暴露；不以配置推断。
- 自动测试和 fake boundary 不等同真实集成或安装包验收。真实外部 smoke 未执行。

## 清理和复验命令

自动矩阵命令及真实退出码在 `raw-logs/`；额外独立 API harness 命令可从同名 `.py` 文件和 `raw-logs/*.log` 复演。所有服务已停止；QA 未改产品源码、原 tracked tests、依赖/lock/config。最终应由 Sol 评定 gate；本报告证据支持 C19 P1 FAIL。
