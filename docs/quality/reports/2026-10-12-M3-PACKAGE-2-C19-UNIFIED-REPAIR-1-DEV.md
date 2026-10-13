# M3 包 2 C19 统一范围 repair 1 Developer 报告

日期：2026-10-12。产品源码固定提交 `df1aac288a002e86a24132a9954fbe0b18d41d1f`，基于 QA 报告整合后的 `21d5add03c934c627ec93e746ceb481f36a679ca`。本轮是用户重新授权 C19 统一修复后的第 1/2 次自动返工；旧 repair、extra 轮次计数及 QA 结论均不重置。包 3不在本轮改动范围。

## 行为变化

原候选在 exact topic 未命中已知预算、排期、存储、负责人维度时，把它误当成泛化检索；同一解析器也会从完整自然问句中误读对象名称里的维度词，并可能把 `工作` 等请求词当主题。结果是明确的访客登记、培训签到、资产借还问题可能退化成广域检索，或无法匹配本来就有资料的主题。

`RetrievalPlan` 现在用内部 `scope_kind` 区分明确主题、泛化方案、开放问题和无法解析的范围。对象先从识别到的正式对象名/alias 中解析，再从剩余主题片段识别已知维度或保留 exact term；未识别的具体主题默认仍是明确范围。常见礼貌/请求包装只作为外壳剥除，不把它们当实体；对象名称中完整出现的“预算”“时间”等词先屏蔽，因此“预算时间工作坊的培训签到办法是什么”会检索培训签到，而不是误判成预算/时间范围。泛化的“A 与 B 制定下一步工作方案”仍走多材料方案路径。

显式范围进入现有范围筛选和覆盖检查。无匹配主题资料时保留缺资料提示、零引用和零 answer-provider 调用；有正式资料的未知主题可正常引用。仅标题等于“排期”的页不会被误认作项目实体，元数据短 alias“青榆”仍能匹配问句“青榆访客登记办法是什么”。事实、比较、方案均走同一 parser；未修改 content eligibility/hash 信任门、公开 API、OpenAPI 或生成的 TypeScript。

## 回归和矩阵

新增/扩展测试在 `tests/integration/test_qualified_retrieval.py`：

- `test_c19_scopes_every_answer_mode_to_named_objects_and_requested_dimensions`：原 QA 高分无关页反例、两个未知对象、无“的”并列对象、对象×维度缺口与空 provider missing 正控/负控。
- `test_c19_same_chunk_does_not_cross_assign_subjects_to_other_dimensions`：同一段落中 A 预算/B 排期不能交叉归属。
- `test_c19_neighbor_expansion_reuses_scope_and_keeps_valid_same_topic_neighbor`：无关邻页不扩大范围，合法同主题邻页仍保留。
- `test_c19_general_comparison_keeps_multiple_material_path_without_object_gate`：未指定对象的通用比较仍可跨资料回答。
- `test_c19_unknown_exact_topics_are_separated_from_object_names_and_keep_positive_matches`：预算词嵌入复合对象名、访客登记/培训签到/资产借还 exact topic、未知主题有资料正控、自然前缀和无“的”语法、短 metadata alias。
- `test_c19_unknown_exact_topic_without_evidence_is_fail_closed_in_all_modes`：新合成主题无资料时三模式均无引用、无答案调用且缺失可见；裸“访客登记”“培训签到”仍按明确主题处理。
- `test_c19_broad_dimensions_ignore_page_title_as_subject_but_keep_schedule_evidence`：标题恰为“排期”不污染通用“比较预算和排期建议”。
- `test_c19_limit_truncation_reports_uncovered_comparison_subject`：limit 截断不能伪称比较完整。

S01–S14 对照：S01–S04 由三模式统一范围、分对象/维度缺口及无资料零调用覆盖；S05 由邻页范围回归覆盖；S06 由同段落交叉归属、最终 passage/ excerpt 支持点及对象名屏蔽覆盖；S07 保留原记录型 provider 空 missing 与高分 reranker 反例；S08 保留真实 user 历史的主题边界与短追问回归；S09 由礼貌事实问法、同义维度和项目/页/title/metadata 主体识别回归；S10 由多对象下一步方案回归；S11 由未指定对象广义比较及不同 exact topic 负控覆盖；S12 由 limit 截断缺失回归；S13 保留 CURRENT/HISTORY、hash 更新和生成时变化资格回归；S14 保留 API/SSE/history、角色/记忆与 replay 回归。fresh QA 应使用不同实体、礼貌表达及主题结构进行 holdout，不把开发样例当验收输入。

具体语言边界：此为有界中文请求外壳和 topic/对象解析，不是通用 NLP。能识别的自然维度受现有 `_TOPIC_CLASSES` 同义集合限制；信息性未识别主题按 exact term 收窄，无法可靠建立对象/主题约束时 fail closed。清楚的开放属性问句（例如有语料支持的“地址在哪里”“什么时候启动”）与不指定对象的通用方案保留开放路径。含混句法可能返回缺资料而不是推测用户意图；不承诺任意长句、口语变体或跨语言语义解析。

## Developer 检查结果

固定源码后重新执行的定向检查：

- `uv run pytest -q tests/integration/test_qualified_retrieval.py`：27 passed，exit 0；日志 `.local/dev/c19-unified/r1-final-qualified.log`。
- `uv run pytest -q .local/dev/c19-unified/r1-holdout/test_c19_holdout.py`：12 passed，exit 0；日志 `.local/dev/c19-unified/r1-final-holdout.log`。此为此前 QA holdout harness 的只读副本，未修改原 QA 报告/证据。
- 预期失败的新增反例 RED 记录在 `.local/dev/c19-unified/r1-red.log` 和 `red-scope-matrix.log`；早期 `r1-green-probe.log` 是中途迭代输出且仍含失败，不能作为通过证据。

README 全量矩阵（固定源码树）：`uv sync --locked --group dev`、`npm --prefix web ci`、OpenAPI/TS 生成、guarded 全量 pytest、Ruff check/format、mypy、lock check、uv build、Web tests/typecheck/lint/build 均 exit 0。guarded pytest 449 passed、1 条既有 Starlette/httpx deprecation；Web 56 passed / 12 files；mypy 43 source files；lint exit 0，保留 TodayView 与 ProjectsView 两条既有 React effect warnings。各原始日志位于 `.local/dev/c19-unified/r1-matrix/`，命令实际退出码附在日志末尾。生成接口无 diff；Web 源码未改。

## QA 状态和限制

这是 Developer 自测，不是 QA PASS。C19 统一候选初验独立 QA 固定 `400dc98c4b0a555561bb98f6633cf1d22ece8550`（产品源码 `247f6708c68812e8b217b1079a2fe953ebb06960`）判 FAIL，Sol 结论与原报告保持不变；其报告及 evidence 不改写。`d2236c2` 属于更早的包 2 extra 2 QA。当前源码 `df1aac288a002e86a24132a9954fbe0b18d41d1f` 等待全新独立 QA。M3 包 2 / M3 正式门未通过；包 3既有离线 PASS 不受影响。真实 provider、真实材料/服务/凭据、Keychain、native/DMG、五日、双机和发布 NOT_RUN；runtime UNVERIFIED；有限 smoke 未消费。

QA 交接：在独立 checkout 固定本报告所列产品源码 SHA。重跑完整包 2/C19验收与原 QA 通过的 7 项正控；特别 holdout 新的自然礼貌前缀、对象名称含维度词、没有“的”的并列主题、短 alias + 未知主题、裸 exact topic 负控、已有主题正文正控、精确“排期”标题的通用比较、地点/时间开放属性和工作方案正控。跨 fact/comparison/plan 断言最终 citations/passages 与所问对象/主题一致、partial missing 完整、无依据时零 provider 调用，资格/hash 与 SSE/session replay 不退化。Sol 独立判断门状态。
