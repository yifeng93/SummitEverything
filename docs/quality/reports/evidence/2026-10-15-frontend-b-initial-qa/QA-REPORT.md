# 前端 UX 里程碑 B 独立 QA 报告

日期：2026-10-15
受测产品 SHA：`613d453ab1a47e2f0bfe78d685fb90817f70f4cc`
QA worktree：`[QA checkout path redacted]`
结论：**FAIL（适用于本报告覆盖的 B 离线技术范围）**。Sol 保留最终 gate 判断。

## 范围与结论

本轮按审批五组、今日页、真实整理范围预览、导入/日志弹窗焦点行为以及真实 FastAPI + Fake 主流程复核。所有浏览器数据为合成内容，FastAPI profile 与 workspace 位于本 QA worktree 的 `.local/qa/frontend-b-initial/`。没有访问真实 provider、OAuth、飞书、Keychain、用户桌面库、付费模型或安装应用。

| 项目 | 结果 | 说明 |
|---|---|---|
| SHA 与固定工作树 | PASS | QA HEAD 全程为 `613d453ab1a47e2f0bfe78d685fb90817f70f4cc`；产品树 tracked status clean。 |
| Web 单测、类型、lint、构建 | PASS | 176 passed、6 todo；lint exit 0，保留 2 条 warning；build exit 0，保留大 chunk 提示。 |
| 离线浏览器与五视口/双主题 | PASS | 2/2；320/390/768/960/1280 × light/dark，页面断言无横向溢出。已人工审阅窄屏浅/深色 Today、Approval、Import、Journal 与桌面深色 Approval 截图。 |
| 独立 FastAPI + Fake 闭环 | PASS | 1/1；原件字节保留，来源→稿件冲突→明确未决→正式内容→首次索引按界面逐步完成；外网尝试 0，动作确认/执行写入 0。 |
| Real SourceOrganizer 可读范围预览 | **FAIL / P1** | 服务端 scope 含待发送原文和选中的项目/主线 ID；预览只显示占位句，不显示原文或人类可读目标。请求上限显示正确。取消后 intake job 写入 0，外部尝试 0。详见 QA-001。 |
| 导入弹窗键盘焦点 | **FAIL / P2** | Tab 会进入被 clip 成 1×1 的文件/目录 input；输入本身有 focus-visible 样式，但 outline 一并被裁掉，截图中看不到焦点。Esc 关闭及焦点归还通过。详见 QA-002。 |
| 当前 UI 的嵌套模态 Esc 行为 | NOT_RUN | 本切片未发现实际嵌套 `useDialogFocus` 模态路径：选择汇总关闭后才跳转，Journal 的辅助预览是页内区块，Import 的飞书计划也是页内确认区。没有人为构造产品里不存在的嵌套流程。 |
| 真实外部、DMG、Keychain、五日、双机 | NOT_RUN | 不属于本轮授权的离线模拟验收；历史联通记录不作为本轮证据。 |

索引和飞书范围同时做了静态人类可读性核对：IndexControls 展示计划页数、计划类型、token 估算、页面标题/版本及确认时请求上限；FeishuPanel 的只读搜索预览展示查询词、可见范围和页数，材料导入预览展示已选材料标题及请求上限。Fake 索引闭环由 FastAPI + Fake 浏览器测试实际完成。真实索引/飞书读取不会在本轮发送，故 Real 模式 UI/服务交互记为 NOT_RUN。

## 缺陷

### QA-001 — Real 整理范围无法核验原文和目标（P1）

位置：`SourceOrganizer.tsx:74` (QA 固定树路径：`web/src/components/SourceOrganizer.tsx:74`)。

复现使用独立 FastAPI/Fake 页面和路由 stub，只替代 `GET /settings` 的 `mode=real` 与 `POST /acceptance-plans` 的响应；stub 的 scope 字段遵循后端 `normalize_organize_scope` 形状，含 `outgoing_inputs[].text`、所选 `item_ids` / `line_id` / `project_id`、`max_output_tokens`，plan 的 `request_limit` 为 1。原文是合成哨兵，不含真实材料。

完成首次配置后创建合成主线、项目和 quick note，在审批中选中该来源并点「整理所选」，展开「查看本次范围」。预览请求里的 line/project ID 与 UI 已选目标相同；界面只显示“范围已在本机生成，确认后才发送。”，来源标题为“快速记录”，看不到原文哨兵或目标名称。请求上限“1 次”显示正常。期望用户在确认前能核对将发送的原件正文、所选目标和预算；实际正文/目标均不可见。点击取消后，测试确认没有 `POST /intake/jobs`，没有任何外部网络尝试。

可复现命令：

```sh
cd web
npx playwright test --config .local/qa/frontend-b-initial/integration.config.ts --grep 'Real source preview'
```

退出码 1 是预期验收失败，原始输出见 [`source-scope-final.log`](logs/source-scope-final.log)。服务端返回 scope 与预览请求见 [`source-scope-request.json`](evidence/source-scope-request.json)，界面文本见 [`source-scope-dialog.txt`](evidence/source-scope-dialog.txt)，截图见 [`source-scope-dialog.png`](evidence/source-scope-dialog.png)，Playwright trace 在 `integration-results/source-scope-Real-source-p-7a110-pe-before-any-organize-call/trace.zip`。

### QA-002 — 键盘焦点进入被完全裁剪的文件输入（P2）

位置：`useDialogFocus.ts:3` (QA 固定树路径：`web/src/components/useDialogFocus.ts:3`)、`App.css:126` (QA 固定树路径：`web/src/App.css:126`)。

在今日页打开「导入会议」，从弹窗初始焦点连续 Tab。焦点依序到两个 `input[type=file]`，其 computed `clip` 为 `rect(0px, 0px, 0px, 0px)`、布局大小为 1×1；focus-visible outline 也处在被裁剪输入上，截图看不到当前焦点。随后 Tab 仍留在弹窗；Escape 关闭弹窗并把焦点还给「导入会议」按钮，行为通过。

可复现命令同 QA-001。Tab 观测见 [`import-focus-walk.json`](evidence/import-focus-walk.json)，不可见焦点截图见 [`import-first-file-focus.png`](evidence/import-first-file-focus.png)。

## 运行记录

完整命令、退出码和输出索引见 [`command-results.json`](command-results.json)。主要独立结果：

- `npm ci`：0，226 packages，audit 0 vulnerabilities；lock 未变化。
- `npm test -- --run`：0，24 files、176 passed、6 todo。
- `npm run typecheck`：0。
- `npm run lint`：0，2 warnings（`App.tsx`、`ProjectsView.tsx` 的既存 effect state 更新警告）。
- `npm run build`：0，JS chunk 568.70 kB，构建工具提示超过 500 kB 建议值。
- `SUMMIT_E2E_EVIDENCE_DIR=../.local/qa/frontend-b-initial/evidence/viewport npm run test:e2e -- --output=../.local/qa/frontend-b-initial/e2e-results-redirected`：0，2/2；最终截图和浏览器测试输出均重定向到 QA 隔离目录。
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`：0，661 passed，1 条 Starlette deprecation warning。
- `npx playwright test --config .local/qa/frontend-b-initial/integration.config.ts --grep 'isolated FastAPI Fake flow'`：0，1/1。
- QA-001 指定的真实范围 UI 断言命令：1，原文与目标可见性断言失败；预算可见、选择 ID 对应、取消零写及零外网断言均先通过。
- `git diff --check`：0；QA worktree `git status --short --untracked-files=all` 为空。

曾将两个集成用例置于同一 FastAPI profile 的 harness 运行 exit 1：首个用例留存的 workspace 状态影响后一个用例首配。该结果是 harness 隔离失误；修正为每个 Playwright 进程使用独立 profile、逐例运行后，FastAPI/Fake 流程 PASS，QA-001 按预期稳定 FAIL。该原始日志留在 `logs/integration-suite.log`，没有用它作为产品缺陷证据。

离线 `viewport.spec.ts` 第一次运行因其默认路径写入本 QA worktree 的 `.local/dev`，没有触及开发 worktree；我确认它由本轮测试新建，随后用 `SUMMIT_E2E_EVIDENCE_DIR` 在 QA 路径重跑成功，并清除本 worktree 仅由该首次测试生成的 `.local/dev`。最终截图只保存在 QA evidence 目录；没有 tracked 或 lockfile 变化。

## 风险与下一步

SourceOrganizer 在真实模式下要求用户确认，但 UI 没有展示 API 计算出的原件正文及人类可读目标，当前无法完成“确认确切外发范围”这道用户门。QA-002 影响键盘用户在文件选择入口中定位焦点。请 Developer 在新的产品 SHA 修复后，由全新 QA 对新 SHA 复验；本报告只验证固定 `613d453`。

本报告不判断 Stage C、真实 provider/OAuth/飞书权限、真实材料、Keychain、DMG、公证、正式安装、五日试用、双机或发布状态。
