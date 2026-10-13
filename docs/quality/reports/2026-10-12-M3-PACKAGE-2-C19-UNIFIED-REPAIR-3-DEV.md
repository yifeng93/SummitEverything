# M3 包 2 C19 统一修复 repair 3（DSH 试修）DEV 报告

日期：2026-10-12。本轮由用户指定 Deepseek Harness V4.1 flash（DSH）在独立分支实施；**结论：DEV PASS（仅本执行者自测）**。独立 QA **NOT_RUN**，由 Sol 在另一个 checkout 对固定 SHA 调度全新 QA。历史 FAIL 不改写；本轮不宣告 M3 正式通过、不合并 main、不发布。

## 固定版本与工作边界

| 项 | 值 |
|---|---|
| 主仓库 | `/Users/yifengstudio/Documents/GitHub/SummitEverything`（main 仍为 `5fd91c78930c80b2365957197b8a605757694a91`，未改） |
| 本轮工作树 | `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012` |
| 分支 | `codex/dsh-c19-20261012`（新建，未 push） |
| 起点 | `b3d0dff587c94ee295dfe5379bd67916c98184ec`（`handoff/c19-dsh-2026-10-12` 指向同一提交，未移动） |
| 起点产品源码 | `f79f613a902758da3173a5b27219fa568a912f5e`；已核验 `git diff --quiet f79f613 b3d0dff -- src web native tests scripts pyproject.toml uv.lock` 无差异 |
| 提交链 | `18fe80a`（共享归一化边界修复）→ `6da7c3a`（tracked 回归）→ `80cabed`（首版 DEV 文档与 evidence）→ `0107d58`（D2/D3/D4 修复）→ `9836365`（evidence 更新）→ `be4e72f`（round-2 D5 过度剥离与 D3 措辞终修） |
| **受测固定源码 SHA** | **`be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`**（含三轮修复与 19 项 tracked 回归；其后仅本报告与 evidence 文档提交） |
| 产品树改动 | `src/summit_everything/retrieval/planner.py`、`src/summit_everything/retrieval/query.py`、新增 `tests/integration/test_c19_topic_scope_normalization.py`；其余 `src/web/native/scripts/依赖/锁` 相对 `f79f613` 无差异 |
| M3 保留目录 | `/Users/yifengstudio/.codex/worktrees/m3-integrated-packages/SummitEverything` 仅只读查证；未在其中写源码、装环境或切分支 |
| 数据边界 | 仅 Fake/offline provider、loopback、隔离合成工作库；未调用真实模型、飞书、凭据、Keychain 或真实材料；未消费 smoke；未构建 DMG |

未执行 reset / force-push、未移动冻结标签或基线分支、未删除他人分支或工作树。DSH 子代理预验证在另一个 detached worktree（`/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-PREQA`）只读进行，未改产品与既有 tracked tests。

## 根因

`src/summit_everything/retrieval/planner.py` 把「请求外壳」和「主题内容」放在同一个全局删除集合 `_TOPIC_FILLER` 里，并对其执行 `sub("", …)`；该正则同时包含 `设备|年度|专项|工作` 这类承载信息的名词/限定词。于是

- `玄石展览的访客设备领用办法` 被归一化成 `term:访客领用`，而正式正文原样是 `玄石展览访客设备领用须登记姓名并归还胸牌。`，非连续短语永不匹配：比较只引用预算、把玄石主题报为缺失；单独询问零 citation、零 answer provider 调用。
- 同一集合导致 `年度访客登记` 缩成 `访客登记`（把「有相近但缺限定词的正文」误判为该特定主题已覆盖）。
- `_ENTITY_SUFFIXES` 与 `_entity_mentions` 把 `专项` 当作对象名后缀，使主题短语被识别成伪对象：`玄石展览的专项证章领取` 产出 `的专项`，并额外把页面标题 `专项证章` 提升为对象，造成多余 missing 与错配引用。
- 同一「外壳未剥离」边界还漏掉了 `看看 / 查一下 / 看一下` 等礼貌祈使动词，产生 `看看：缺少预算依据` 这类假缺失；`readable_dimension` 对裸 exact 主题未去 `term:` 前缀，把内部标记泄漏给用户；引用条数上限造成的缺口与真正无资料使用同一措辞。

这不是「设备」一个词的问题，而是归一化、请求外壳剥离、对象提取、局部主题、缺失措辞和回退分支共用边界的同一类缺陷；本轮按共享边界修复，未加词表白名单或单例例外。

## 改动范围（2 个产品模块 + 1 个新 tracked 测试文件）

`src/summit_everything/retrieval/planner.py`：

1. `_TOPIC_FILLER` 不再删除 `设备/年度/专项/工作`；这些限定词保留在未知主题内并参与正文匹配与缺失判定。
2. 新增 `_PLAN_SHELL`：只有整段都是计划用词（如 `下一步工作`）时才不构成主题，`为…制定下一步工作方案` 仍是 `generic_plan` 且 `dimensions == ()`。
3. `_ENTITY_SUFFIXES` 与 `_entity_mentions` 去掉 `专项`：它同时是普通主题修饰语（专项预算 / 专项证章）。真正以 `……专项` 命名的对象仍通过 project/alias/line 别名解析。
4. 新增 `_is_name_stem`：拒绝单字虚词或含 `的` 的词干，杜绝 `的专项` 这类伪对象。
5. 片段若以已识别对象开头，其余部分只算该对象的局部主题，不再注册为第二个对象、也不再窃取下一个对象的主题跨度（修复 `玄石展览访客设备领用办法与枫湾活动预算` 的倒序形态）。
6. `_trim_topic_after_entity_suffix` 增加「结尾主题词可分离」规则：`枫湾活动预算` → 对象 `枫湾活动` + 主题 `budget`；`预算时间创作坊` 这类中间含主题词的名称保持不变。
7. 抽出共享 `_REQUEST_SHELL`（礼貌、问句外壳与祈使查词）供 `_SUBJECT_REQUEST_PREFIX` 与 `_TOPIC_PREFIX` 复用，并把 `看看/看一下/看下/瞧瞧/瞅瞅/查一查/查一下/查看/告诉我/说明一下` 计入，避免对象候选与主题跨度两处再次漂移。

`src/summit_everything/retrieval/query.py`：

8. `readable_dimension` 对裸 exact 主题同样去掉 `term:` 前缀，用户可见的 missing 只用业务语言（`storage&term:…` 的既有渲染不变）。
9. 引用条数确实因 `limit` 截断且仍有未覆盖 pair 时，不再生成逐对 `缺少…依据`，改用一条点名未覆盖对象/主题的截断说明；未截断时行为不变（`_readable_dimension` 从嵌套函数提升为方法供两处复用）。
10. 请求外壳拆成两层：`_POLITE_SHELL`（礼貌/问句框架）可作用于任何候选；`_LOOKUP_VERBS`（看看/看一下/看下/瞧瞧/瞅瞅/查一查/查一下/查看）与 `_TOPIC_SHELL_ONLY`（告诉我/说明一下/梳理/总结/比较…）只作用于「已识别对象之后的剩余串」或主题跨度，绝不作用于独立对象候选，避免把 `总结报告` 这类真实名字削短。

`tests/integration/test_c19_topic_scope_normalization.py`（新增，19 项）：设备主题三模式正/倒序双对象、单对象、partial、zero；`年度/专项/工作` 限定词保留与「纯计划外壳无主题」；对象跨度与主题跨度分离；礼貌查词不产生伪对象；missing 无内部标记；limit 截断与真实缺资料区分。

未放宽 `domain/content.py` 的批准/当前版本/hash 信任门；角色、记忆、assistant 历史仍不扩大证据范围；未改产品规格、Web、native、依赖或锁文件；未删除、跳过或放宽任何既有测试与门槛。

## RED → GREEN

复演命令与原始日志均在 evidence：

| 阶段 | 命令 | 结果 |
|---|---|---|
| RED 基线 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q <previous_holdout> <r2_expanded>` | **7 failed, 27 passed**（exit 1）；`plan` 为 `term:访客领用`，单问零引用、provider 0 次 |
| GREEN 修复后 | 同上 | **34 passed**（exit 0） |
| 新增 tracked 回归 | `uv run pytest -q tests/integration/test_c19_topic_scope_normalization.py` | **19 passed**（exit 0） |
| 最小复现脚本 | `reproduce_device_topic.py` | 4/4 两段支持进入引用与 provider passages、missing 空；partial 仅预算且准确报玄石缺失 |
| 新边界脚本 | `reproduce_scope_normalization.py` | 设备/年度/专项/工作 正反控、对象跨度分离、generic plan 全部符合预期 |
| 预验证反例脚本 | `reproduce_preqa_findings.py` | D2/D3/D4/D5 已修；D1 作为契约待定项保留原始观测 |
| 全量后端 | guarded pytest | 基线 450 passed → 修复后 **469 passed**（+19 新回归），无回归 |

RED 原始输出：`raw-logs/baseline-holdout-34.log`、`raw-logs/baseline-device-topic.log`。GREEN 原始输出：`raw-logs/fix-*.log`、`raw-logs/fix-device-topic.jsonl`、`raw-logs/fix-scope-normalization.jsonl`、`raw-logs/fix-preqa-findings.jsonl`。

## DSH 子代理对抗性预验证与反例处置

按用户选择，DEV 固定后由全新 context 的 DSH 子代理在独立 detached checkout 自建 harness 做两轮对抗性黑盒预验证。**它是 DSH 子代理验证，不是官方独立 QA，不代表 M3 签核。**

- 第 1 轮（`…-DSH-C19-PREQA`，固定 `80cabed`）：冻结 34 项、当轮 tracked 15 项与全量 465 项全绿（exit 0），验收区 1/2/3/4/7 PASS，发现 D1–D4 四项反例。
- 第 2 轮（`…-DSH-C19-PREQA2`，固定 `9836365` / 产品源 `0107d58`）：冻结 34、tracked 18、全量 468 与 loopback 均 PASS；D2/D4 确认修复，D3 判「部分修复」，并新发现 D5——上一轮共享 `_REQUEST_SHELL` 把**未注册**对象名开头的 `总结/梳理/查看/看看/查一下` 等一起剥掉，65 个「前缀 × 词根」探针中 60 个行为改变，可把 `总结报告` 变成对象 `报告`（并引用无关页）或把 `总结方案` 静默丢弃后仍称完整。

本轮对全部反例逐一处置：

| 编号 | 发现 | 处置 |
|---|---|---|
| D2 过严 | `麻烦帮我看看…`、`帮我查一下…`、`看看…` 把祈使动词当伪对象，产生 `看看/查一下：缺少预算依据` 假缺失 | **已修**（改动 7），并加 tracked 正控；复现脚本显示四种礼貌问法 subjects 均为 `枫湾活动`、missing 为空 |
| D3 过严 | HTTP API 默认 `limit=5`，6 pair 时被截断的 pair 与真实缺资料使用同一措辞 | **已修**（改动 9），并加 tracked 对照（limit=5 出现截断说明、limit=12 无截断且 6 页齐全） |
| D4 轻微 | 用户可见文本泄漏内部标记 `缺少term:访客设备领用依据` | **已修**（改动 8），并在 tracked 回归中断言 `term:` 不出现 |
| D1 过宽 | 页面归属项目 A、但标题/别名是 B 的对象名且正文不含 B 名时，该页会被当作 B 的证据引用 | **保留并上报，不改**（见下） |
| D5 过宽/名损（第 2 轮，本轮引入） | 共享 `_REQUEST_SHELL` 也用于清理**独立**对象候选，未注册名 `总结报告/梳理工程/查看细则` 被改写成 `报告/工程/细则`，`总结方案` 被静默丢弃却仍称完整 | **已修**（改动见下），并加 tracked 正控 |
| D3 措辞（第 2 轮复核判定未真正修好） | 截断提示虽已追加，但逐对 `缺少…依据` 条目仍在，答案依然断言已知资料缺失 | **终修**：截断时不再输出任何 `缺少…依据` 条目，只输出一条点名未覆盖对象/主题的截断说明 |

第 3 轮（`…-DSH-C19-PREQA3`，固定 `7e772ea` / 产品源 `be4e72f`）复验结果：产品树一致；冻结 34、tracked 19、全量 469、子代理自建 round-3 harness 27 项与 loopback 全部 PASS；**D5 PASS**；**D3 PASS**；D2/D4 仍修复；D1 仍为唯一 FAIL（已声明为契约问题）。关键独立证据：子代理把原始基线 `f79f613` 用 `git archive` 解出做 A/B，13 前缀 × 5 词根的 65 个未注册对象名矩阵在新 SHA 与基线之间**逐字节一致（0/65 行为改变）**，且每行 `citations=1`、无无关页被拉入；`比较总结报告与松墨展会的预算` 端到端只引用 `松墨展会预算上限为七万元。` 并把 `总结报告` 报告为缺失。截断场景在 limit=1/5 三模式下**不再出现任何逐对 `缺少…依据`**，只有点名未覆盖对象/主题的上限说明；未截断场景不变。原始 harness 与矩阵日志见 `evidence/2026-10-12-m3-package-2-c19-unified-repair-3-dsh-be4e72f/subagent-preqa/`（`matrix_r3_base.log` 与 `matrix_r3_new.log` 逐字节相同）。

子代理同时列出**与基线逐字一致的既有语言边界**（非本轮引入、未恶化）：lookup 动词后接**未注册**对象时动词并入对象名（`看看云岬营地`）；`…，另外看看…` 产生伪对象 `另外看看`；对象名为 `查看明细项目` 时多出伪兄弟 `明细项目`；主题跨度以 总结/查看/梳理 开头时缩成 `term:报告`/`term:记录`。这些属于同一类边界，建议在后续轮次或 QA 观察中单独定级。

D1 判定说明：计划的确定边界写明「项目/页元数据可确定归属」，且既有 tracked 用例（`青榆` 作为 `aliases` 元数据、正文与项目名都不含该词）要求 alias 必须能建立对象归属；本轮把标题/别名视为同级归属信号与该设计一致，改成不绑定会破坏既有已接受行为。三轮子代理预验证均确认该反例未变；反例原文与最小 fixture 已存入 `raw-logs/fix-preqa-findings.jsonl`（`D1-title-alias-binding`：正文 `预算上限为九万元。` 被作为「枫湾活动的预算」引用）。是否收紧为「只有 project/line/aliases 绑定、裸 title 不绑定」属于产品契约决定，交 Sol/QA；本轮不擅自改。

## 验收标准对照（S01–S14 与 ACCEPTANCE 原要求保留）

1. **设备主题不丢词**：三模式、正序、倒序、单对象、双对象下 `required_pairs` 为 `(枫湾活动, budget)` 与 `(玄石展览, term:访客设备领用)`；两段支持同时进入 citations 与真正送入 provider 的 excerpt，`missing_information == []`（tracked 测试与 API 复演双重覆盖；子代理独立复核同样 PASS）。
2. **缺失准确、零引用不借位**：删掉 B 主题正文（换成开放时间）后只保留枫湾预算并精确报告 `玄石展览：缺少访客设备领用依据。`，provider 实收不含开放时间；再把 A 支持也换掉后 citations / source_statements / inferences / advice 全空、answer provider 调用数不增加，第三对象不补位（子代理独立复核 PASS）。
3. **换名称、换陌生主题、限定词**：`年度访客登记` 与 `专项证章领取` 完整正文可答；只有 `访客登记` / `证章领取` 的近似正文不被宣称已覆盖；`的专项` 不再成为伪对象，页面标题 `专项证章` 不再被提升为对象（正反控均入 tracked 测试）。
4. **pair 结构**：A 预算 + B 陌生主题两 pair；A/B 共享预算与排期四 pair；同对象多主题、无对象并列主题、同页/同 chunk 多对象不跨 pair 错配（既有 tracked 用例 + 本轮回归；子代理新增 fixture 复核 PASS）。
5. **范围门不可绕过**：断言同时核对对象、topic 维度、每条引用正文、provider 实收 passages 与 missing；高分 reranker、无关邻页、`related_page_ids`、provider 返回 `missing_information=[]` 均不能突破（子代理独立复核这些攻击面 PASS）。**唯一未闭合项是 D1 的标题/别名归属契约问题**，已单列上报。
6. **正常问法仍可用**：礼貌双对象比较、预算/排期广义汇总、下一步方案、最近 user 主题接续保持通过；礼貌祈使查词（看看/查一下）已修复；未知新对象不回退更早话题（子代理复核 PASS）；limit 截断现在只输出截断说明、不再断言资料缺失；名字以请求词开头的未注册对象也不再被削短。
7. **信任与恢复不退化**：CURRENT/HISTORY、批准/hash 变化、生成中编辑/删除、无关坏页诊断、API/SSE 唯一终态、角色与记忆权限、包 3 恢复归档均未改动；由全量 469 后端与 56 Web 测试守护（子代理复核 CURRENT/HISTORY、生成期编辑作废与无资料诊断 PASS）。

## 检查结果（固定 SHA `be4e72f`，原始日志与 `.exit` 见 evidence `raw-logs/`）

| 检查 | 命令 | exit | 结果 |
|---|---|---|---|
| guarded 全量 pytest | `env PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | 469 passed，1 条既有 Starlette/httpx deprecation，无 skip/xfail |
| ruff check | `uv run ruff check src tests` | 0 | All checks passed! |
| ruff format | `uv run ruff format --check src tests` | 0 | 79 files already formatted |
| mypy | `uv run mypy src` | 0 | Success: no issues found in 43 source files |
| lock check | `uv lock --check` | 0 | — |
| uv build | `uv build` | 0 | sdist + wheel 构建成功 |
| Web api:types | `npm --prefix web run api:types` | 0 | `web/src/api/generated.ts` 无 diff（API 契约未变） |
| Web tests | `npm --prefix web test -- --run` | 0 | 56 passed / 12 files |
| Web typecheck | `npm --prefix web run typecheck` | 0 | — |
| Web lint | `npm --prefix web run lint` | 0 | 保留既有 warning，未新增 |
| Web build | `npm --prefix web run build` | 0 | production build 成功 |
| git diff --check | `git diff --check` | 0 | — |

检查前后 `git rev-parse HEAD` 均为 `be4e72f`，工作树 clean。未增加 suppressions、未降低阈值、未删除或跳过测试。

## 实际 API/SSE 与 history reopen 复演（隔离 loopback）

`harness/api_c19_replay.py` 在隔离 `SUMMIT_PROFILE_ROOT` 上启动真实 uvicorn（127.0.0.1 随机端口，Fake/offline provider），用合成工作库经 `POST /api/v1/workspaces` 打开、就地建索引后走 `POST /api/v1/queries` SSE，读取 completed 终态与 conversation id：

- 13/13 观测 PASS：设备三模式正/倒序、单对象、partial、zero、`年度`/`专项` 目标正文与限定词不匹配的零引用、history reopen 与 history list。
- 完整比较在 API 层同时引用两段正文且无主题 pair 缺失；partial 只引用预算并单列 `玄石展览：缺少访客设备领用依据。`；限定词不匹配时零引用并准确报缺口；截断场景出现明确截断说明。
- `POST /api/v1/conversations/{id}/reopen` 返回 200，消息状态 `completed`，两条 citation 与文本原样保留（历史重开保持正确结果）。
- 复演结束后回连端口失败（无 listener），测试服务已停止。

浏览器 Chrome/AX、DevTools console/network 与 PNG 本轮无可用工具接口，记 **NOT_RUN**；不以 API 200 冒充浏览器验收。

## 语言边界与剩余风险（未独立定级）

- **D1 未闭合（最需要 Sol/QA 决策）**：标题/别名元数据 vs 项目归属，是否允许只凭标题把页面绑定到另一对象名。现有实现对 project/line/aliases/title 一视同仁；收紧会与既有 `青榆` alias 用例冲突。反例 fixture 与原始输出见 `raw-logs/fix-preqa-findings.jsonl`。
- **D3 的深层公平性未变**：截断时被丢弃的可能是任一对象/主题（本轮复现里 limit=5 丢的是枫湾预算）。本轮只把原因说清楚并停止误报缺失，未改变候选公平策略；若要求「截断不得使固定一方被淹没」，属 S12 的另一选项，需要单独设计与验证。注意本轮修复会让 exact 主题保留更多 pair，从而更容易触发 `limit=5`。
- **名字以请求词开头**：`总结报告`、`梳理工程`、`查看细则` 等独立候选现在保留完整；但 `总结方案` 仍会被既有的主题词归一化削成 `总结`（`方案` 属于 `_TOPIC_FILLER` 的请求/主题用词），此时按未知对象 `总结` 报缺失，不再静默丢弃。同名歧义（语料里真的存在对象 `报告`）时仍优先采用已注册对象，属既有权重设计。
- 无「的」的紧凑倒序且对象**完全未知**（库中无该对象任何页面）时，`枫湾活动访客设备领用办法` 这类「名称+复合主题」连续串无法可靠切分，会作为一个未知对象整体处理；有「的」或在语料中可解析对象时边界明确。
- 目标与正文只差限定词时按不覆盖处理（`季度访客登记` 对 `年度访客登记` 正文 zero），这是本轮有意收紧的方向，可能与「同义改写」期望存在张力，需 QA 独立判断。
- `……专项` 若只出现在问题中且从未作为任何 project/alias/line 出现，不再仅凭后缀提升为对象（按主题处理并报告缺失）；以该名命名的真实对象仍可解析。
- 本轮只做离线/合成范围；真实 provider、飞书、凭据、Keychain、DMG、五日、双机、发布均 **NOT_RUN**，runtime **UNVERIFIED**，有限 smoke 保持 **0/1 未消费**。

## 交接与下一步

- 分支/工作树：`codex/dsh-c19-20261012` / `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012`；受测固定源码 `be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`；工作树 clean、测试服务已停止。
- 子代理三轮预验的 harness 与原始日志副本见 `evidence/2026-10-12-m3-package-2-c19-unified-repair-3-dsh-be4e72f/subagent-preqa/`（明确标注为 DSH 子代理材料，非官方 QA）。
- 本报告的结论仅为 **DEV PASS**。独立 QA 需在另一个 checkout 固定同一 SHA，复跑 34 项 holdout、19 项新回归、README 适用全量检查，并独立复演 API/UI 的完整、partial、zero 与 history reopen；**QA NOT_RUN**，由 Sol 调度。子代理预验证不得作为官方 QA 结论引用。
- 建议 QA 优先独立判定 D1（标题/别名归属）与 D3 深层公平性，这两项是本轮明确保留的未闭合边界。
- 即使独立 QA 通过 C19，包 2 门、M3 正式验收与合并 main 仍需用户批准；历史 FAIL 继续有效。
