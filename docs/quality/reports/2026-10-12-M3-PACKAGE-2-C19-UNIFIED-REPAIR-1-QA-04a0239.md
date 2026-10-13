# M3 包 2 C19 unified repair 1/2 独立 QA

日期：2026-10-12。独立 QA 结论：**FAIL（P1）**。Sol 负责包 2、整体离线 M3 和正式阶段门的最终判断。

## 固定版本与隔离

- 被测产品源码 SHA：`df1aac288a002e86a24132a9954fbe0b18d41d1f`。
- 本 QA checkout 固定 HEAD：`04a0239012068598123966ab31340127a6f8ff76`。
- HEAD 的 parent 为 `0cfd92c067ea7e1c8b0a76af2f0f3cb893731ccf`；产品源树与源码 SHA 相同，HEAD 相对产品 SHA 只有交接文档差异。开始验收时 checkout clean。没有移动被测提交。
- fixture、profile、前端与 Python 依赖和临时日志均在此隔离 checkout；自动检查及 UI 只使用 Fake/offline provider 和合成内容。未使用真实模型、飞书、材料、凭据、Keychain、任务或 smoke。
- QA 未改 `src`、`web`、`native`、已有 tracked tests、依赖、lockfile 或产品配置。最终源码 diff 仍为 0；运行的 API 与 Web 服务已停止，两端口无 listener。

## 自动检查

- `npm --prefix web ci` 与 `uv sync --locked --group dev` 均 exit 0；安装数量和结果见 evidence。
- 固定候选全量 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`：**449 passed**，一条既有 Starlette/httpx deprecation，exit 0。
- `uv run ruff check src tests`、`uv run ruff format --check src tests`、`uv run mypy src`、`uv lock --check`、`uv build`、Web tests（56 tests / 12 files）、typecheck、lint 与 build 全部 exit 0。逐条实际退出码及原始日志见 [evidence](evidence/2026-10-12-m3-package-2-c19-unified-repair-1-qa-04a0239/README.md)。
- 原 C19 QA 12 项 holdout 独立复跑 **12/12 PASS**。
- 新增有限 holdout 8 项中 **5 PASS、3 FAIL**。三个失败断言属于同一混合主题范围问题，详见 C19-QA-R1-01；通过项包括未知主题无依据时三模式零引用/零调用、未知 exact topic 有正文时可回答、metadata 短 alias 不得补足另一个主题、标题“排期”不污染广义比较、开放地址问题、泛化下一步方案，以及 A/B 预算与排期 shared-dimension 完整正控。原始 harness 与实际输出保存在 evidence。

## 缺陷：C19-QA-R1-01（P1，FAIL）

**对象×异质主题证据被合并，已存在的匹配依据一并丢弃。** 独立临时库包含两页：白鹭工程的正式页正文是“白鹭工程预算上限为十八万元。”；赤陶项目的正式页正文是“赤陶项目活动证章领取须出示邀请函。”。用真实 `PageWriter`、SQLite `IndexStore`、`QueryService`、Fake embedding、对所有候选给高分的 reranker 和会返回空 `missing_information` 的记录型 answerer 查询：

`比较白鹭工程预算与赤陶项目的活动证章领取办法`

预期应将查询保留为两个不同请求 pair：`(白鹭工程, 预算)` 和 `(赤陶项目, 活动证章领取)`；两段正文分别支持各自部分。完整资料下应引用两项、不报告缺失，并向 answer provider 传递包含支持点的 excerpts。若只提供其中一段，产品应返回对应部分并指出另一 pair 缺失。

实际 `fact`、`comparison`、`plan` 三种模式均无 citation、无 answer-provider 调用，错误报告两个对象都缺少 `预算（活动证章领取）`。将主题/对象顺序换为“比较赤陶项目的活动证章领取办法与白鹭工程预算”后仍零 citation，且把尾部“白鹭工程”吞入主题缺失描述。另一个同根变体在有额外排期/财务页时也拒绝白鹭预算。可复演日志显示三模式 missing/body/provider-call 结果；浏览器 UI 产生相同错误，并在从历史重开后保留错误结果。

Sol 根据固定 planner 观察到，planner 先把完整问句整理成一个联合 family+exact 维度，之后无法正确将不同主题分配给各自对象。上述反例无需更改语料词汇，也不依赖模型判断；这是 C19 核心证据范围缺陷。修复后应按对象保留局部主题映射，在同一对象跨主题共享表达、对象与主题倒序、部分覆盖/未知 exact、完整 shared A/B budget+schedule 正控上分别验证；不能通过全局放宽范围或默认拒答关闭它。

复现命令：

~~~sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q -s .local/qa/c19-unified-r1/harness/test_c19_fresh_holdout.py
~~~

旧 12 项通过与本轮 P1 FAIL 均各自保持事实。开发自测 PASS 不抵销此失败；这是用户批准 repair 1/2 的独立 QA 结论，可交 Developer 在下一固定 SHA 修复，随后由全新 QA 复验。

## 浏览器与其余门

实际 Chrome Incognito loopback 复演通过了新隔离库、项目、合成来源、Fake 整理稿经 UI 明确确认、首次 Fake 索引计划/执行、问题查询和历史重开流程。查询 UI 可访问树显示无引用及两个错误缺口；本地 `/api/v1/queries` 和 conversation `/reopen` 均返回 200。无知识或任务副作用跟随问答。详见 [UI observations](evidence/2026-10-12-m3-package-2-c19-unified-repair-1-qa-04a0239/ui-observations.md)。Chrome console/network 导出与 PNG 未从 CUA 提供的接口中实际获得，状态 **NOT_RUN**。

API/OpenAPI 类型生成 **NOT_RUN**：README 脚本会写入 `web/openapi.json` 与 `web/src/api/generated.ts`，QA 规则禁止写产品文件；本轮未生成或覆盖它们。Stage C 真实 provider、真实材料/服务/凭据、OS Keychain、runtime 暴露验证、native/DMG、五日、双机与发布均 **NOT_RUN**；runtime **UNVERIFIED**；smoke **0**。本报告不构成 M3 正式验收或合并批准。

## 证据与提交

原始命令输出、holdout harness、UI 观察与 SHA-256 manifest 位于 [本轮证据目录](evidence/2026-10-12-m3-package-2-c19-unified-repair-1-qa-04a0239/README.md)。QA commit 只包含本报告与 QA harness/evidence，不含产品源码或已有 tracked tests。
