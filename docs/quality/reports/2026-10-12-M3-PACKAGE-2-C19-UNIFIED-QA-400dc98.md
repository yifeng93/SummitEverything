# M3 包 2 C19 统一候选独立初验

日期：2026-10-12。结论：**FAIL**。固定候选仍存在 P1 证据范围缺陷；本报告只记录 QA 观察，Sol 决定 C19 / 包 2 / 整体离线 M3 门。

## 固定版本与隔离

- 完整受测 HEAD：`400dc98c4b0a555561bb98f6633cf1d22ece8550`。
- 产品源码：`247f6708c68812e8b217b1079a2fe953ebb06960`。
- HEAD 相对源码 SHA 仅有 9 个文档文件差异；`src`、`web`、`native`、`tests` 对应 Git diff 均为空（四次 exit 0）。工作区开始时 clean。执行期间未改产品实现、依赖或 tracked tests；QA harness 在 `.local/qa`，提交文件仅为本报告和 `evidence/`。
- 只使用 Fake embedding/reranker、记录型 answerer、MemorySecretBackend 缺省路径与去标识隔离工作库。无真实模型、飞书、Keychain、工作资料或 smoke 调用。
- 全量 WebUI 在 loopback 实际启动并关闭；停止后 API `18893`、Web `15173` 的 `lsof -sTCP:LISTEN` 均 exit 1（无监听）。

## 实际检查

- `npm --prefix web ci`：PASS，exit 0，126 packages，0 vulnerabilities。
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`：PASS，446 passed，1 条既有 Starlette/httpx deprecation，exit 0。
- `uv run ruff check src tests`、`uv run ruff format --check src tests`、`uv run mypy src`（43 files）、`uv lock --check`、`uv build`：全部 PASS，exit 0。
- `npm --prefix web run api:types`：PASS，exit 0，生成 OpenAPI/TypeScript 后无 tracked diff。
- `npm --prefix web test -- --run`：PASS，56 tests / 12 files；`typecheck`、`lint`、`build` 均 exit 0。Lint 保留既有 TodayView、ProjectsView 两条 effect warning。
- 独立 holdout：`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q .local/qa/c19-unified/harness/test_c19_holdout.py`：**FAIL，7 passed / 5 failed，exit 1**。测试使用真实 PageWriter、SQLite IndexStore、QueryService；高分 reranker 与 `missing_information=[]` 的 answerer 不替产品决定证据范围。

检查命令和真实退出码、holdout harness、provider passage/citation/missing/body JSON 见 [固定证据目录](evidence/2026-10-12-m3-package-2-c19-unified-qa-400dc98/README.md)，其 SHA-256 清单为 `SHA256SUMS`。

## 缺陷

**C19-QA-01 — 已知对象上的未知明确主题回退到对象级证据（P1）。** 最小复现：语料只有“白榆工程预算上限 20 万元、启动时间五月”和另一对象排期页，问“白榆工程的培训签到办法是什么”，模式 `plan`。期望零引用、零 provider call，missing 明确培训签到缺口。实际引用白榆同 chunk 的预算和启动时间，provider 收到不支持主题的 passage 并被调用 1 次；其返回“根据提供的材料回答。”，产品输出 `missing_information=[]` 且有推断/建议。见 `reproductions/h04-unknown-dimension.json`。同根变体“为预算时间专项制定培训签到流程”也将预算/六月排期送给 provider。与接受契约要求的主题证据边界冲突。

**C19-QA-02 — 无对象的未知明确主题回退为宽泛检索（P1）。** 仅有两个项目的预算页和启动时间页时，问“培训签到办法怎么安排”，模式 `plan`。期望识别为明确但未知主题，零引用/零 provider call 并报告缺少培训依据。实际引用两页无关内容，宽松 answerer 被调用并输出泛化回答，missing 为空。高分 reranker 不应扩大显式主题证据范围。见 `reproductions/unknown-topic-and-object-name-dimension.json` 的对应记录及 H11。

**C19-QA-03 — 名称/标题和主题维度交叉污染（P1，subject/topic 混淆）。** 有两种相反失效：项目名“预算时间工作坊”包含预算/时间，但问“预算时间工作坊签到办法是什么”时，正确的“培训签到须现场登记并核验姓名”页零引用，错报缺少预算/排期依据（H09）；另两个对象分别有预算与排期页，页面标题为“排期”，问“比较预算和排期建议”时，planner 把“排期”标题解析成对象 `排期`，导致两页零引用并报告该伪对象缺少两种依据。见 H12、`reproductions/s11-title-alias.json`。这是主题/实体边界错误，不是单页标题补丁问题。H07 的元数据别名“青榆”及无“的”简称正向查询仍通过。

独立 holdout 其余 7 项 PASS：无资料三模式零引用/零调用；已知对象与未知并列对象保留已知部分结果和缺口；A预算+B排期不交叉配对；双对象预算/排期泛方案保留依据；最近未知主题追问不回滚旧对象；元数据 alias 与简称事实问句可引用；未指定对象的预算/排期比较和方案保留。共 12 项，7 PASS / 5 FAIL，均列于 harness 与 pytest 日志。

## 浏览器/API/SSE

真实 Chrome 对本机 WebUI 执行 C19 路径：完整双对象四 pair 比较可见四条来源；只有两个交叉 pair 时，UI 只显示现有两条依据并逐项说明另两个对象×维度缺口；ready-index 的双对象“纸伞保管办法”负控零引用且逐对象列缺失；不指定对象的“比较预算和排期，并汇总现有资料”显示四条相关材料；从本机历史重开后答案、推断和四条引用保持一致。详细观察见 `ui-observations.md`。

本轮 API/SSE 相关自动回归包含在 446 项全量测试中并通过（唯一终态、conversation reopen、角色/记忆上下文与 no-evidence modes）。真实 Chrome 实测覆盖上述结果和 history reopen；DevTools console/network、PNG 导出为 NOT_RUN（本轮没有可用的 DevTools/截图导出接口）。

C13/C14/C20/C21 与包 1、包 3代码保持一致：本次 `src/web/native/tests` 与受测产品 SHA 相同；该等包级既有 QA PASS 证据见[包 1 QA](2026-10-11-M3-PACKAGE-1-REPAIR-1-QA-bc3deab.md)及[包 3 QA](2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md)。本轮全量 446 tests 也重新执行通过，但不把自动测试提升为此前未做的 UI/系统门。

## 其余门

- C19 统一候选、包 2 离线门：**FAIL**，含上述 P1。
- 独立 C19 自动 holdout：**FAIL**；7/12 holdout PASS；完整自动测试、Web 构建/类型、OpenAPI、Ruff、mypy、lock、Python build：PASS。
- Chrome loopback C19 UI：限定场景 PASS；DevTools console/network/PNG：NOT_RUN。
- C13/C14/C20/C21 包 1/3相关既有证据与当前代码树一致；本轮关联自动测试 PASS。
- 真实模型质量、真实 Feishu/材料/凭据、OS Keychain、native/DMG、五日、双机、发布：NOT_RUN；runtime UNVERIFIED；有限 smoke 使用数仍为 0。
- M3 正式总验收与重要里程碑合并：未授权/未执行。

建议将以上两类范围缺陷作为同一轮统一修复输入；保留历史 FAIL 和本轮证据，不更改验收门。Developer 给出新固定源码 SHA 后由全新 QA 再验。
