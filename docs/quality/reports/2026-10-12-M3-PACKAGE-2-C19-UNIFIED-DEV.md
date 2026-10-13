# M3 包 2 C19 统一证据范围修复（Developer 交接）

日期：2026-10-12。用户在 extra 2 独立 QA / Sol 门判 C19 P1 FAIL 后，明确重新授权一次统一收口。Developer 固定产品源码 `247f6708c68812e8b217b1079a2fe953ebb06960`，提交 `fix(retrieval): enforce shared evidence scope`。这是 DEV 自测记录；fresh QA 对该 SHA 尚未运行（NOT_RUN）。extra 2 的 QA FAIL、原始报告与证据保持原样；M3 整体尚未正式验收或合并。

## 交付行为

`RetrievalPlan` 在现有 planner/query 内携带显式对象、维度、未识别对象和所需对象×维度组合。fact、comparison、plan 共用候选、排序后材料、相关邻页、provider passage 与 citation 的范围约束。语料页/项目/线名称可辅助识别归属，不能替代正文对所问维度的支持；同一 chunk 或页面不能以笛卡尔积方式证明多个对象×维度均有依据。高分 rerank 仅用于排序，不构成范围资格证明。

无资料时不调用 answer provider、不产生引用，missing 由服务端确定；部分资料只回答已支持的对象×维度，并明确指出其余缺口。provider 返回空 missing 列表不能清除已知缺失，主文也不能声称完整。无指定对象的广义比较/方案仍可使用多个相关材料；匹配规则保留已测礼貌表达、常用维度同义表达、无“的”对象句式、连续追问及正常多材料建议。CURRENT/HISTORY、批准/hash、生成后版本复核和内容资格门未放宽。没有 OpenAPI/TypeScript/API 字段变化。

规则是本地、有界、可解释的语料和语义主题匹配，不是通用 NLP。陌生描述可在已识别维度上细化主题；未识别主题按范围不足处理，不因中文 bigram 分数或对象名命中而引用无关事实。未覆盖的自然语言结构可能保守少召回，需在 QA 报告具体记录；真实模型质量未测。

## S01–S14 开发证据

以下是固定源码上的回归映射和开发观察，不替代独立 QA。测试位于 `tests/integration/test_qualified_retrieval.py`、`tests/integration/test_answer_context.py`、`tests/integration/test_conversations.py`。

| ID | 测试 / 观察 |
|---|---|
| S01 | `test_c19_scopes_every_answer_mode_to_named_objects_and_requested_dimensions`：风铃工程/霜塔项目无彩色牙刷储存依据时，fact、comparison、plan 不引用无关储备/预算，也不将其诊断为缓存问题。 |
| S02 | 同一参数化矩阵覆盖 A 有预算、B 未知以及第三对象有预算：只保留 A 的预算依据并逐对象报告缺口；未知并列主体不被已识别 alias 提前吞掉。 |
| S03 | 同一参数化矩阵覆盖已知对象有预算但仅问陌生的储存规则：对象名及正 rerank 分数不能代替主题证据，三模式均不补造该维度。 |
| S04 | 同一矩阵覆盖 A 预算有依据、A 排期缺失而 B 有排期：只回答明确请求的 A-预算 pair，不把 B 的排期迁入 A，也不额外制造反向 pair 的 missing。 |
| S05 | `test_c19_neighbor_expansion_reuses_scope_and_keeps_valid_same_topic_neighbor`：跨页邻接仍使用主体/维度范围；不相关邻页拒绝，同主体同维度邻页保留并受资格复核。 |
| S06 | `test_c19_same_chunk_does_not_cross_assign_subjects_to_other_dimensions`：同 chunk 的 A 预算/B 排期在中文分号、中文逗号、英文逗号和连接结构中不会交叉配对；无“的”查询保持指定 pairs。 |
| S07 | S01–S04 通过 high-score reranker 与返回 `missing_information=[]` 的记录型 answerer 验证：评分不穿透范围门，provider 不得擦除服务端计算的缺口。 |
| S08 | `test_multi_turn_followup_skips_intermediate_pronouns_but_stops_at_new_topic` 与既有 conversations 回归：只沿最近有效 user 主题接续，明确新对象/未知对象及完整新问题建立边界；assistant 文本不成为检索证据。 |
| S09 | `test_fact_subject_is_found_inside_a_polite_request_without_filtering_the_prefix`、`test_fact_subject_matching_uses_qualified_page_and_workspace_names`：礼貌问句不当作 phantom subject；已资格核验的正文、title/alias 与 project/line 归属支持主体识别。 |
| S10 | S01–S04 的 plan 正控及 `test_c19_scopes_every_answer_mode_to_named_objects_and_requested_dimensions`：已知 A/B 的方案保留跨材料依据，不因“方案”未写在材料中而整体拒答；建议仍是未批准内容。 |
| S11 | `test_c19_general_comparison_keeps_multiple_material_path_without_object_gate`：未点名对象的广义预算/排期比较保留多材料路径；主题/描述限定仍要求材料支持。 |
| S12 | `test_c19_limit_truncation_reports_uncovered_comparison_subject`：排序/limit 截断不能把多页误计为多个对象已覆盖，未送入 provider 的对象仍列为缺口。 |
| S13 | `test_rejected_stale_hash_is_reported_as_version_change`、`test_unrelated_stale_page_does_not_pollute_scoped_query_diagnostics`、`test_current_and_history_queries_label_superseded_knowledge` 与既有生成期间版本变更测试：当前/历史资格与 hash 门维持；无关坏页不污染诊断，生成期间变化仍阻止旧依据。 |
| S14 | `test_api_no_evidence_modes_are_ready_and_never_call_provider`、`test_role_memory_and_followup_context_are_verified_and_profile_local` 及 conversations 集成：API 三模式无证据时零 provider calls；角色/记忆、history/replay 不授予扩大范围的权限。API/OpenAPI/TS 生成无 diff。 |

S10 和 S02/S04 同时覆盖明确 “A 和 B 制定方案/预算” 与无“的”主体表达；S06 覆盖同句标点边界；S11 覆盖“橙色雨伞保管规则”一类广义主题描述，不依赖 QA 实体词表。未对任意自由自然语言作完整解析保证。

## 实际检查

- 定向：`PYTHONPATH="$PWD/src" uv run pytest -q tests/integration/test_qualified_retrieval.py tests/integration/test_answer_context.py tests/integration/test_conversations.py` — **PASS**, 36 passed，1 条既有 Starlette deprecation warning。
- 全量 guarded：`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` — **PASS**, 446 passed，1 条 Starlette/httpx deprecation warning，exit 0；日志 `.local/dev/c19-unified/guarded-pytest.log`。
- `uv run ruff check src tests` — **PASS**, exit 0。
- `uv run ruff format --check src tests` — **PASS**, exit 0。
- `uv run mypy src` — **PASS**, 43 source files，exit 0。
- `uv lock --check` — **PASS**, exit 0。
- `uv build` — **PASS**, sdist 与 wheel 均构建成功，exit 0。
- `cd web && npm run api:types` — **PASS**；生成的 OpenAPI / TS 文件无 diff。
- `npm ci` — **PASS**, 126 packages，0 vulnerabilities。
- `npm test && npm run typecheck && npm run lint && npm run build`（`web/`）— **PASS**, 56 tests / 12 files、typecheck、lint、production build 均 exit 0；保留 2 条已有 React effect lint warnings。日志 `.local/dev/c19-unified/web-checks.log`。
- `git diff --check` — **PASS**, exit 0（源码提交前）。

以上自测不构成 QA PASS。Sol 已另行核对 guarded pytest 446、Web checks 0、mypy 43；本交接未重复这些常规检查。未启动真实服务或浏览器 QA，fresh QA 为 NOT_RUN。

## QA 固定交接与限制

受测源码必须固定为 `247f6708c68812e8b217b1079a2fe953ebb06960`。重点在独立 checkout 按 S01–S14 与现有包 2/包 1/包 3相关范围执行 holdout：更换主体名、对象顺序、维度词和句式；使用 high-score reranker、稀疏与密集语料；直接观察 provider passages/excerpts、citations、missing、主文与调用次数；复核 hash/批准门及 API/SSE/history。QA 不应将当前开发测试视为独立证据，也不应修改产品源码或旧 tracked tests。

Package 2 extra 2 原 QA 与 Sol C19 P1 FAIL 仍保留；仅 Sol 可判本候选是否关闭该门。包 1、包 3先前离线 PASS 不改变。M3 整体未正式验收、未合并。真实模型/服务、真实材料/凭据、OS Keychain、native/DMG、五日、双机与发布未测，runtime UNVERIFIED，smoke 未消费。
