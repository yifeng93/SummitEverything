# 给 Deepseek Harness V4.1 flash：C19 独立试修

以下正文可整段作为下一次试修的任务提示词。用户指定本次由 DSH 实施；不要求 DSH 冒充 Luna 或伪造独立 QA。此次收尾只准备环境和提示词，没有修复 C19。固定引用在本次文档提交后创建，具体完整 SHA 用 `git rev-parse` 查证并在试修报告中记录。

## 任务与冻结基线

你是 SummitEverything 的 C19 专项修复执行者。请先查证实际 Git 状态、读取下列文档，再在自己新建的分支和独立工作树完成根因修复、离线自测和固定 SHA 交接。不要只提出方案，也不要重复开发已完成的 M3 功能。

- Git 主仓库：`/Users/yifengstudio/Documents/GitHub/SummitEverything`。
- main 冻结在 `5fd91c78930c80b2365957197b8a605757694a91`，尚不包含 M3。**不能从 main 开始修 C19。**
- M3 保留分支：`codex/m3-integrated-packages`；保留目录：`/Users/yifengstudio/.codex/worktrees/m3-integrated-packages/SummitEverything`。仅作为基线读取，不在那里写源码、安装环境或切分支。
- 你的起点是本地固定标签 `handoff/c19-dsh-2026-10-12` 指向的提交，包含完整 M3 候选、历史 QA 证据和本次交接文档。不要追随移动中的 branch HEAD；不要假定这个本地标签已经推送到远端。
- 该基线产品源码、tests、scripts、依赖/配置与 `f79f613a902758da3173a5b27219fa568a912f5e` 相同。收尾前文档 HEAD 为 `23057f9150cde7971de988c8af6d9dfc710a95e6`。
- 最后独立 QA 固定 HEAD：`262f4eaa418d70f983f3b0b260d3635cd2e28c92`，产品源码为上述 f79；QA-only 报告提交 `2061b6260ece1b3887fc1ba34cc3960e61716b2a` 已导入 M3 分支。
- **包 1 / 包 3保持已测离线 PASS；包 2 C19 为 P1 FAIL，M3 正式门未通过，未合并 main。** 450 后端和 56 Web 测试通过不代表 C19 产品行为通过。
- 原 Sol / Luna 统一修复周期的两轮自动返工已用完，用户选择暂不追加。现在用户指定另交 DSH 在隔离环境尝试；这不重置历史轮数或授权正式合并/真实服务。

先读 AGENTS.md、README.md、docs/implementation/PROGRESS.md、docs/handoff/LATEST-IMPLEMENTATION.md，接着读 PRODUCT-SPEC、ARCHITECTURE、WORKSPACE-v1、API-v1、IMPLEMENTER、TESTER、ACCEPTANCE 和全 v1 计划。专项必读：

1. `docs/superpowers/plans/2026-10-12-c19-unified-evidence-scope.md`：完整 S01–S14 修复契约。
2. `docs/quality/reports/2026-10-12-M3-C19-UNIFIED-SOL-GATE.md`：Sol 已核证的最终门判断。
3. `docs/quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md` 及同名 evidence 目录。
4. 初验、repair 1 的 QA / DEV 报告，以及 repair 2 DEV 报告，必要时查对应 diff。
5. `docs/handoff/2026-10-12-M3-CLEANUP.md`：清理、恢复入口和保留环境。

自行建分支，建议步骤如下；先检查目标路径和分支不存在，若已存在则选择新的唯一名称，不覆盖：

```sh
repo=/Users/yifengstudio/Documents/GitHub/SummitEverything
base=$(git -C "$repo" rev-parse 'refs/tags/handoff/c19-dsh-2026-10-12^{commit}')
trial_dir=/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012
git -C "$repo" status --short
git -C "$repo" worktree list
git -C "$repo" worktree add -b codex/dsh-c19-20261012 "$trial_dir" "$base"
cd "$trial_dir"
git rev-parse HEAD
git diff --exit-code f79f613a902758da3173a5b27219fa568a912f5e HEAD -- src web native tests scripts pyproject.toml uv.lock
```

若标签/提交缺失或源码一致性检查失败，记录具体差异并交回，不退回旧 main、不自行重建猜测基线。不要 reset、force-push、清理他人的分支/工作树，或在主目录留下修改。

## C19 的产品问题与最小复现

C19 要求事实问答、跨材料比较和工作方案的证据始终满足用户指定的**对象及该对象局部主题**。排名分数、页面数量、模型自行返回的 missing 列表不能代替证据覆盖判断；无资料不能借其他项目预算填充，有资料也不能误判为缺失。

最新独立 QA 使用已确认、当前版本的合成正文：

- 枫湾活动：`枫湾活动预算上限为七万二千元。`
- 玄石展览：`玄石展览访客设备领用须登记姓名并归还胸牌。`
- 问：`比较枫湾活动预算与玄石展览的访客设备领用办法`。

预期 required pairs 为 `(枫湾活动, budget)` 与 `(玄石展览, term:访客设备领用)`；两组支持均须进入实际引用和 provider passages，missing 为空。

当前 planner 把“设备”当 filler 全局移除，变成 `term:访客领用`；完整正文不能匹配这个非连续短语，最终只引用预算、误报玄石主题缺失。fact / comparison / plan 三模式及倒序都复现；单问“玄石展览的访客设备领用办法是什么？”也零引用、零 answer provider 调用。真实 Chrome UI 与 history reopen 复现了错误结果。

最后独立有限矩阵是 **22 案例：15 PASS / 7 FAIL**，七项为同一根因。原 12 项 holdout 和最初纠正后的 9 项 holdout 已通过。最后保存的 corrected harness 后来追加了 r2 测试，内容与 expanded 文件相同，直接跑全文件是 22 项；用 `-k test_fresh` 才是原 9 项，不要双计数量。

Sol 另做过只读 parser 检查：

- `玄石展览的年度访客登记办法是什么` 被缩成“访客登记”，丢掉“年度”。
- `玄石展览的专项证章领取办法是什么` 可能识别出伪对象“的专项”。

这两项是风险观察，尚未独立黑盒 QA 定级。你应先加正反控查证，不能把它们记成已独立验收的缺陷或已通过项。

## 前几轮做过什么

1. 包 2 前期修复了历史批准状态、本人偏好记忆误拒，以及“没有相关资料”误显示缓存/资格异常。其后仍有比较无资料对象时借用其他项目预算的 P1。
2. Sol 研究后统一三模式对象/主题、候选/邻页/引用/provider passages 和缺失提示。统一初验候选源码 `247f6708c68812e8b217b1079a2fe953ebb06960`、QA `400dc98c4b0a555561bb98f6633cf1d22ece8550`：原 12 项中 7 PASS / 5 FAIL，陌生主题回退、未知并列对象遗漏及名称/主题污染仍存在。
3. repair 1 源码 `df1aac288a002e86a24132a9954fbe0b18d41d1f`、QA `04a0239012068598123966ab31340127a6f8ff76`：加强 exact/bare 未知主题、对象跨度、source-aware aliases，原 12 项通过。新混合问法把 A 的 budget 和 B 的 exact topic 合成联合维度，已有两段正文仍无法匹配；新 QA 5 PASS / 3 FAIL。
4. repair 2 源码 f79、QA 262：改为先解析每个对象的局部 required pairs，再汇总 dimensions；处理显式不同主题、共享后缀、同对象多主题、无对象并列主题，以及按 pair 计算 partial/zero。原 12、纠正 9 项通过，但新设备主题暴露全局删词，仍 FAIL。

历史证据不改写。repair 1 的旧 harness 曾要求完整 fixture 中已有证章资料的赤陶仍 missing，Sol 确认这一条预期错误。repair 2 只在独立副本改为完整两组引用/provider 支持，并增加删除赤陶正文的 partial 对照。原文件、报告、hash 保留；纠错并没有取消 repair 1 的其他真实混合主题失败。使用最新 corrected 副本，不靠修改历史断言消除红灯。

## 修复方向与范围

重点检查 `src/summit_everything/retrieval/planner.py` 的 `plan_retrieval`、`_extract_explicit_subjects`、`query_scope`、`_local_subject_topics`、`_topic_dimensions`、`_single_topic_dimension`、`_topic_phrase`、`_entity_mentions`、`_TOPIC_FILLER`，以及 `retrieval/query.py` 中 required_pairs、候选/邻页/引用/provider 文本与 missing 的使用。以实际文件为准，不凭函数名字猜调用关系。

先建立可解释的边界，再实现：仅在语法位置明确时剥离“请、比较、是什么、办法”等请求外壳；保留未知主题内部有意义的名词和限定词。对象跨度、连接符和主题跨度应分清，不能因为主题里出现“专项/项目”等后缀就猜新对象。审计所有归一化、提取和回退分支，避免只移除一个设备 stopword 后又在其他函数丢词。

保持现有本地匹配能力与最小实现。不使用案例名称/主题白名单，不做庞大 NLP 框架，不添加远端意图识别或真实模型调用；不要为通过测试统一拒答，或改 Fake reranker 掩盖范围门问题。完整未知主题与已测常见主题同义表达都要保留。

`domain/content.py` 是批准/版本/hash 的统一信任门，不能放宽。角色、记忆、assistant 历史不能扩大证据范围，资料和模型输出不能授权操作。M3 包 1/包 3和其他阶段只做必要回归；不改变规格、确认/权限、恢复和归档行为，不开展无关重构。

## 必须满足的验收标准

S01–S14 和 ACCEPTANCE 原要求全部保留，重点增加下列结构性正反控，三种模式共享同一范围规则：

1. 上述设备主题：正序、倒序、单独询问、混合两对象均有正文时，主题词不丢失，引用及真正送入 provider 的 excerpt 都包含对应支持点，missing 为空。
2. 移除玄石主题正文、改成该对象的开放时间或预算正文：只保留枫湾预算，准确报告玄石所问主题缺失；再移除预算正文则零引用、source statements / inferences / advice 为空、answer provider 0 次，不能捡第三对象资料。
3. 新名称、新陌生主题和“设备、年度、专项”等限定词；正文确有完整主题的正控须可答，只有相似但缺限定词的正文不能伪装该特定主题已覆盖。“的专项”不得成为伪对象。记录实测支持的语言边界。
4. A 的预算 + B 的 exact topic 是两 pair；A/B 共享预算及排期是四 pair；同对象两个主题、无对象两个明确主题、同页/同 chunk 不同对象都保留正确归属，不能用全页关键词串联错配。
5. 名称含预算/时间词、只有 project/title/alias 命中、无关邻页、高分 reranker、provider 返回 missing=[] 都不能突破范围门；正文的主题支持和对象归属需同时成立。
6. 礼貌/同义预算、正常双对象比较、广义预算/排期、多材料下一步方案、最近 user 主题代词接续仍可用。未知新对象不能回退更早话题；limit/前20/文本预算导致未覆盖时明确提示，不能虚称完整。
7. CURRENT/HISTORY、引用前后 hash/批准变化、生成中编辑/删除继续正确处理。无相关资料与缓存/资格故障分清，无关坏页不污染诊断。API/SSE 唯一终态、history reopen、角色/记忆权限及包 3恢复归档不得退化。

不要仅断言“引用非空”或“调用了一次”。至少核对 scope/required pairs、每条引用的对象/版本/支持文本、provider 实收 passages、missing 内容，以及 zero/partial/complete 三组对照。

## 复演与自测

仅在新工作树安装本项目依赖。先 `npm --prefix web ci` 与 `uv sync --locked --group dev`，全 pytest 的 dev runner 需要 Web 依赖。

旧 `.local/qa` 已清理，使用 tracked evidence 副本重建自己的 harness；原 evidence 不编辑：

```sh
evidence=docs/quality/reports/evidence/2026-10-12-m3-package-2-c19-unified-repair-2-qa-262f4ea
harness=.local/dsh/c19/harness
mkdir -p "$harness"
cp "$evidence/harness/test_c19_previous_holdout.py" "$harness/"
cp "$evidence/harness/test_c19_r2_expanded_matrix.py" "$harness/test_c19_fresh_holdout.py"
cp "$evidence/harness/reproduce_device_topic.py" "$harness/"
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src:$PWD/$harness" uv run python "$harness/reproduce_device_topic.py"
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q "$harness/test_c19_previous_holdout.py" "$harness/test_c19_fresh_holdout.py"
```

基线第二条测试命令预期 27 PASS / 7 FAIL（12+22），先保留 RED 和实际 exit。复现脚本只打印观察，其 exit 0 不能判产品通过。修复后 34 项均须通过，再补本次限定词/新主题/对象结构正反控，不把公开旧用例全绿当充分验收。

按 README 运行并记录实际命令、退出码和原始日志：

```sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
npm --prefix web run api:types
npm --prefix web test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
git diff --check
```

API 未变化时，生成的 OpenAPI / TypeScript 应稳定；有合理变化则说明契约及生成物 diff。执行者可以在自己的分支更新合法生成物，独立 QA 只做隔离导出和比对。至少用隔离 profile/合成库复演实际 API/SSE 与浏览器的完整、partial、zero、历史重开，记录页面实际观察；工具不可用如实记 NOT_RUN，不伪造截图/console/network。

不删除、跳过或放宽已有测试，不降低阈值、不增加 suppressions 绕过检查。既有 warning 记录保留。只使用 Fake/offline、loopback、隔离合成材料；本次应用真实 provider/飞书/凭据/Keychain/真实材料、安装 DMG、发布、五日/双机均无新增授权。历史有限 smoke 仍为 0/1，本次不消费、不重置。

## 交付与最终门

可以连续开发并做多个逻辑提交；整项完成后固定完整源码 SHA，停止写入，留 clean checkout 和已停止的测试服务。提交 DEV 报告、新测试/矩阵、原始日志与 hash 清单，更新该试修分支的 PROGRESS / LATEST。报告说明起点完整 SHA、根因、历次尝试区别、改动范围、RED→GREEN、所有检查的实际 exit、语言边界及未测门。

你自己的测试结果只能记 DEV PASS。由全新的独立 QA 在另一个 checkout 对你的固定 SHA 复验，至少跑上述 34 项、新结构 holdout、适用全量检查和实际 API/UI 对照；QA 不修改产品/已有 tracked tests，不验移动的目标。若你的 Harness 无法提供独立 QA，就交回固定 SHA 和证据，由 Sol 调度，明确 `QA NOT_RUN`，不要自行签发独立 PASS。

独立 QA 失败后按 AGENTS 最多两轮自动返工，每轮新 SHA / 全新 QA，未解决交用户决定。历史 FAIL 仍保留，只在新 SHA 通过后关闭对应缺陷。即便 C19 独立 QA 通过，也由 Sol 判断包 2门；重要 M3 正式验收和合并须用户批准。不要自行合并 main、移动冻结标签/基线分支、推送正式版本或发布。最后只交付：分支/工作树、固定 SHA、已修行为、DEV/QA 结果与证据、剩余风险和准确下一步。
