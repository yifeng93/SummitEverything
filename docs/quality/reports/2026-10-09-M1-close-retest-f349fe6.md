# SummitEverything M1 收口独立复验报告

## 身份与范围

- 验收者：独立 QA 子 agent；未修改 `src/`、`web/src/`、`native/Sources/` 的产品实现。仅报告提交写入本 QA 分支。
- **完整受测 SHA：** `f349fe6cb5da86c3fdafff11738e2a55335d8874`。
- 前序固定候选：`34522507f2c5c9856ed859f0593e1967190cae41`；本轮最后 UI 收尾提交为上述 f349 SHA。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/qa-m1-close-r3`，分支 `codex/qa-m1-close-r3`。
- 目录与原件：只在本 checkout 的 `.local/qa-m1-close-r3/` 保存模拟工作库、profile 和证据。Fake embedding/provider；未访问真实业务材料、付费模型、飞书或其他 checkout 的服务。
- 环境：macOS 27.0.1；Python 3.12.13；uv 0.12.3；Node 24.15.0；npm 11.12.1；Swift 6.3.3；Chrome 155.0.8059.39。
- 本轮 Web/API 独立运行在 `127.0.0.1:5202` / `127.0.0.1:8842`。health 返回 `workspace_open=true`、版本 `1.0.0`、本轮 run ID `qa-m1-r3-f349fe6c`。UI 工作库 ID 为 `bef91bd1-5eb3-4d62-8333-a52cafdc9490`。浏览器路径、逐步观察与结果见忽略文件 `.local/qa-m1-close-r3/browser-evidence.md`。
- 固定候选中没有 `docs/quality/reports/REPORT-TEMPLATE.md`；报告沿用旧独立报告的栏目与字段。第一份固定候选的报告保留为旧 QA 提交 `23579b65b50b80fadffcd815ea96b8aee1fc5400`（`codex/qa-m1-close-daf726e`），其中 C03 为 FAIL；本文件是修复后的独立复验，不覆盖旧结论或两份历史报告。

## 结果矩阵

| 案例 | 结果 | 本轮范围和证据 |
|---|---|---|
| C01 Foundation | **PASS** | f349 全量 Python 检查、77 项 pytest 通过；内容 hash / 资格门禁及反例包含在测试集。本项只说明基础门禁。 |
| C02 M1 | **PASS** | f349 在真实 UI 新建隔离库、主线和项目；完整 pytest 覆盖工作区约束、非法路径与结构等。 |
| C03 M1 | **PASS** | f349 真实 UI 创建并重命名主线 / 项目，检查 manifest ID 不变；创建并确认两页，新增相对链接需要显式确认；跨项目移动后已有入站链接被重写；归档知识仍可检索，项目可恢复；非空项目 / 主线删除均拒绝。详情见浏览器证据。 |
| C04 M1 | **PASS** | 上一独立浏览器复演在 `daf726e…` 以模拟 canary 验证原件与待审稿不能进入有效答案；f349 重新跑完整后端测试。`daf` 至 f349 没有后端 `src/` 改动。 |
| C05 M1 | **PASS** | 上一独立 UI 复演验证保存、显式整理、部分确认 / 全部确认、换 operation ID 防重复、已完成后的显式 reprocess；失败重试由 Fake timeout 集成测试覆盖。f349 `uv run pytest -q` 重跑通过 77 项，`TodayView` 未改。 |
| C06 M1 | **PASS** | 上一独立 UI 复演：用户先选单项目，一份双主题来源生成两稿、逐稿确认、来源和项目关联完整；f349 重跑前后端自动检查。 |
| C07 M1 | **PASS** | 上一独立 Fake UI 复演：重要冲突不选时不能确认，标记未决后正文明确保留两个候选且不作确定事实；f349 完整集成测试重跑通过。 |
| C08 M1 | **PASS** | 上一独立浏览器复演：审阅期间外部编辑保留 proof，确认发生版本冲突且稿件不覆盖外部正文；显式按外部版本重整后再确认。f349 全量 pytest 和前端测试通过；本轮 `PageReader` 差异仅新增目录移动 / 链接控件及其提示，没有改审稿冲突逻辑。 |
| C09 M1/M2 | **PASS** | 上一独立 UI 复演从“记入工作日志”直接写入无项目归属日志；f349 全量 pytest 通过。未覆盖 M2 任务联动。 |
| C10 M1 | **PASS** | f349 真实 UI 复演外部改动保留旧 proof：旧数字从检索依据消失、页面标为“需要确认”；显式确认后增量索引显示 2 个新 chunk / 1 个复用，问答引用新数字 314 元，不含旧数字 271 元。 |
| C11 M1 | **PASS** | f349 全量 pytest 77 项通过；覆盖当前版本校验、旧 SQLite chunk 排除和邻页资格复核。 |
| C12 M1 | **PASS** | f349 全量 pytest 77 项通过；覆盖不变 chunk 复用、fingerprint 变化、失败重建保留旧 active index 与过期计划拒绝。 |
| C13 M1/M3 | **PASS（M1 部分）** | f349 UI 查询命中归档项目中的有效预算知识；完整 pytest 覆盖归档检索、current/history 的失效 / 替代规则标记。M3 历史会话 UI 未测。 |
| C14 M1/M3 | **PASS（M1 部分）** | f349 全量 pytest 覆盖 SSE 顺序、唯一终态及取消不伪装完成。M3 断流恢复与旧历史引用 UI 未测。 |
| C15 M2 | **NOT_RUN** | 飞书材料分页与授权门未实现 / 未授权。 |
| C16 M2 | **NOT_RUN** | 未创建真实飞书任务；真实写入、unknown 核实和幂等未测。 |
| C17 M2 | **NOT_RUN** | 飞书完成态与日期编辑未测。 |
| C18 M2 | **NOT_RUN** | 任务建议与项目进展独立确认未测。 |
| C19 M3 | **NOT_RUN** | 完整会话问答、方案与角色 UI 未测。 |
| C20 M3 | **NOT_RUN** | 记忆候选与角色权限未测。 |
| C21 M3 | **NOT_RUN** | 多 profile 的会话 / 角色 / 记忆隔离未测。 |
| C22 M3 | **NOT_RUN** | 跨 profile 接续、月归档与断流恢复未测。 |
| C23 M1/M3 | **PASS（M1 部分）** | f349 全量 pytest 覆盖 M1 原子写中断恢复、外部改动保护及相同意图重放；月归档 / 跨 profile 的 M3 场景未测。 |
| C24 M4 | **NOT_RUN** | M4 安全与打包威胁模型未测。 |
| C25 M4 | **NOT_RUN** | 未测 DMG、干净机器安装；上轮开发壳生命周期不能代表 DMG。 |
| C26 M4 | **NOT_RUN** | 真实“场地与酒店”样板授权门未打开。 |
| C27 M4 | **NOT_RUN** | 未调用真实模型或真实飞书。 |
| C28 M4 | **NOT_RUN** | 无真实现场流程与五个实际工作日证据。 |
| C29 M5 | **NOT_RUN** | 未做 Studio / Air 同步往返。 |
| C30 M5 | **NOT_RUN** | 未做双机首次索引与 profile 隔离。 |
| C31 M5 自动 | **NOT_RUN** | 未做模拟冲突副本、多机半写与 unknown receipt 演练。 |

## 检查命令与结果

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `uv sync --group dev` | 0 | 独立 Python 3.12 环境安装完成。 |
| `cd web && npm ci` | 0 | 126 packages added；0 vulnerabilities。 |
| `uv run pytest -q` | 0 | 77 passed；1 Starlette/httpx deprecation warning。 |
| `uv run ruff check src tests` | 0 | All checks passed。 |
| `uv run ruff format --check src tests` | 0 | 29 files already formatted。 |
| `uv run mypy src` | 0 | 22 source files，无类型错误。 |
| `uv lock --check` | 0 | lock 与项目元数据一致。 |
| `uv build` | 0 | sdist 与 wheel 成功。首次与 Swift 构建并行时因共享临时目录发生竞态；串行重跑通过。 |
| `cd web && npm run api:types` | 0 | OpenAPI 与 TypeScript 类型生成成功。 |
| `cd web && npm test` | 0 | 5 test files、10 tests passed。 |
| `cd web && npm run typecheck` | 0 | 通过。 |
| `cd web && npm run lint` | 0 | 退出 0；3 条既有 `react(set-state-in-effect)` warning（ProjectsView、TodayView、AskView）。 |
| `cd web && npm run build` | 0 | Vite production build 成功；JS fingerprint `index-BH7Wnmq0.js`。 |
| `cd native && swift build` | 0（前序候选） | 在 `34522507f2c5c9856ed859f0593e1967190cae41` 通过；`native/` 在 f349 与该 SHA 间无差异。 |
| Chrome 真实 UI：C03 / C10 | 完成 | 在 f349 专用 run ID、工作库和 profile 上完成；证据文件记录路径、按钮、状态、相对链接和检索值。 |

## 缺陷与严重度

- **P0：0。** 未观察到数据丢失、未确认内容入索引或外部副作用。
- **P1：0。** 首轮 `daf` 的 C03 P1 已在 f349 UI 复验通过并关闭。
- **P2：1 个 UI 文案问题。** 非空项目 / 主线删除按预期拒绝，但 alert 仍为英文（如 `A nonempty project must be archived`），周边目录界面为中文。建议在后续 UI 文案收尾统一本地化；不影响拒绝行为和数据完整性，不阻断 M1。
- 自动检查中保留 1 条 Starlette/httpx 弃用警告和 3 条 React effect lint warning；命令均按原标准退出 0，没有通过删测或降低门槛处理。

## 独立结论

- **M1.1–M1.5 模拟验收通过，P0/P1 为 0。** C03 已在 f349 通过真实界面复验；Foundation 与 M1 自动门禁在该 SHA 全量复跑。C04–C09 的真实业务浏览器路径取自前一独立轮次，f349 的后端测试全量复跑，且受影响的 Review / Today 功能未改；C08 的 PageReader 改动只添加相邻的组织操作。C10 在 f349 再次完成真实 UI 路径。
- 结论只适用于固定 SHA `f349fe6cb5da86c3fdafff11738e2a55335d8874` 上模拟资料和 Fake provider 的 M1 范围。真实模型、飞书、真实样板、DMG、现场五日和双机仍是各自独立门禁，不能据此宣告通过。
- P2 安排：实现者可在后续 UI 文案整理时本地化两条拒绝消息；该项不阻断 M1 合入。
