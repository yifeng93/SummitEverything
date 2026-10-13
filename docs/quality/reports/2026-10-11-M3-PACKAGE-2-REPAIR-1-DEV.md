# M3 功能包 2 repair 1 Developer 报告

日期：2026-10-11

状态：Developer 已完成 repair 1/2 和本机自动检查；固定 SHA 的整包独立 QA 等待 Sol 调度。本报告不是 QA PASS。

分支：`codex/m3-integrated-packages`

首轮失败受测源码：`082744738f300525e57dfd6655245adb98e13628`

修复源码 SHA：`0df323efc26e388d62f234e0471f853b2b54be4d`

## 修复范围

首轮 QA 原报告及证据保留在[报告](2026-10-11-M3-PACKAGE-2-QA-0827447.md)和相邻 evidence 目录。QA 将事实问答的 cross-project citation 精度列为缺陷；原报告已明确撤回早期 stale-index 夹具假阳性，本修复只针对正确重建索引后的真实问题。

- AskView 增加“当前有效资料 / 包含历史版本”的显式范围选择，发送 `purpose` 并在历史范围说明其效力。引用卡片分别显示原引用版本可用性与 `current` / `superseded` / `invalid` 效力；当版本已更新且已失效时两种状态同时可见。
- 新增确定性检索规划：清晰的短指代追问可将最近一条真实用户问题作为检索提示；完整历史和 assistant 答案不作为检索依据。原始本轮问题仍传给 answer provider，每次新问答都重新调用当前资格复核。问句明确提到主体时，fact 候选要求标题或正文中包含其显式主体；comparison 与 plan 路径保持多材料能力。没有引入实体词表、固定合成实体或人工分数阈值。
- AskView 将非成功 HTTP 响应显示为可读回答错误。HTTP 422 的预算拒绝不再写成断流/连接中断，且本地历史列表不会因未受理请求而产生记录。
- 新增集成回归：短追问经真实本地 API 保留当前用户消息及引用、只把最近用户问题用于检索提示、切换主题不带入旧问题；主体精度 / 缺失主体、比较模式保留两方；预算拒绝不创建历史。UI 回归覆盖历史范围提交、superseded/invalid 标记、效力与引用可用性同时显示及 422 状态。

API schema 无变化；`api:types` 已重新生成并核对。没有新增依赖或修改 lock。

## Developer 自测结果

原始 stdout 与真实退出码位于 ignored `.local/dev/m3-package-2-repair-1/`。全量命令最后一次均在修复源码上运行；Web lint 保留 TodayView 和 ProjectsView 两条既有 effect warnings，pytest 保留一条既有 Starlette/httpx TestClient deprecation。

| 命令 | 结果 |
|---|---|
| `npm --prefix web ci` | PASS，exit 0；126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | PASS，exit 0 |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，402 passed，1 条既有 deprecation，exit 0 |
| `uv run ruff check src tests` | PASS，exit 0 |
| `uv run ruff format --check src tests` | PASS，73 files already formatted，exit 0 |
| `uv run mypy src` | PASS，40 source files，exit 0 |
| `uv lock --check` | PASS，exit 0 |
| `uv build` | PASS，sdist 与 wheel 成功构建，exit 0 |
| `npm --prefix web run api:types` | PASS，OpenAPI 类型生成成功，exit 0 |
| `npm --prefix web test -- --run` | PASS，52 tests / 12 files，exit 0 |
| `npm --prefix web run typecheck` | PASS，exit 0 |
| `npm --prefix web run lint` | PASS，exit 0；保留上述 2 条 warnings |
| `npm --prefix web run build` | PASS，exit 0 |
| `git diff --check` | PASS，exit 0 |

最终自动矩阵前另运行后端定向测试 `uv run pytest -q tests/integration/test_qualified_retrieval.py tests/integration/test_answer_context.py`：14 passed，1 条既有 deprecation。UI 新增的复合状态断言先在旧展示逻辑上失败（只显示“原引用版本已更新”而漏掉 invalid）；新增独立可用性/效力标签逻辑后，最终 52 项 Web 测试通过。

## 独立 QA 交接

请全新 QA 在独立 checkout 固定 `0df323efc26e388d62f234e0471f853b2b54be4d`，完整执行首轮报告范围，重点重验 QA-1 至 QA-4。复演材料位于 `docs/quality/reports/evidence/2026-10-11-m3-package-2-qa-082744738/harness/`；先复制到新 SHA checkout 的 `.local/qa/m3-package-2-qa/harness/`，并遵循原[QA 报告](2026-10-11-M3-PACKAGE-2-QA-0827447.md)的隔离 workspace、profile、本地端口和脚本步骤。优先检查：

1. UI 可明确选择 history；history 查询实际发送 `purpose=history`，superseded 与 invalid 都标为仅限历史参考；availability 与 validity 同时异常时两者都显示。current 查询仍排除历史版本。
2. 新一轮“它呢？”仅使用最近一条历史用户问题作为 retrieval hint，不发送旧 assistant answer；当前资格门每轮重取。切换到明确新主题后，不把旧主题问题混入检索。确认比较模式针对多主体仍可返回双方资料。
3. context / role budget 返回 HTTP 422 后，界面说明输入/预算未受理，不显示连接中断，不创建假历史。
4. 在正确重建索引的合成库中复演首轮青岚预算问题：fact 不应引用朱雀页；明确对象无合格页时返回无依据；comparison 跨两对象保留两边。不得复用旧 stale-index 夹具结论。

QA checkout 不得在共享开发 checkout 改动产品实现或已有 tracked tests。所有真实服务、真实模型、业务材料、凭据、Keychain、native、DMG、五日、双机均不在本轮范围；未观测 runtime 元数据应标 UNVERIFIED。M3 包级状态仍由 Sol 判定；包 3 不在本报告范围内。
