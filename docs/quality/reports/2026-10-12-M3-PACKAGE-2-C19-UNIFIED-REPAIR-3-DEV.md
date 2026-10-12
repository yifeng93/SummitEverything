# M3 包 2 C19 统一修复 repair 3（DSH 试修）DEV 报告

日期：2026-10-12。本轮由用户指定 Deepseek Harness V4.1 flash（DSH）在独立分支实施；**结论：DEV PASS（仅本执行者自测）**。独立 QA **NOT_RUN**，由 Sol 在另一个 checkout 对固定 SHA 调度全新 QA。历史 FAIL 不改写；本轮不宣告 M3 正式通过、不合并 main、不发布。

## 固定版本与工作边界

| 项 | 值 |
|---|---|
| 主仓库 | `/Users/yifengstudio/Documents/GitHub/SummitEverything`（main 仍为 `5fd91c78930c80b2365957197b8a605757694a91`，未改） |
| 本轮工作树 | `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012` |
| 分支 | `codex/dsh-c19-20261012`（新建，未 push） |
| 起点 | `b3d0dff587c94ee295dfe5379bd67916c98184ec`（`handoff/c19-dsh-2026-10-12` 指向同一提交，未移动） |
| 起点产品源码 | `f79f613a902758da3173a5b27219fa568a912f5e`；已核验 `git diff --quiet f79f613 HEAD -- src web native tests scripts pyproject.toml uv.lock` 无差异 |
| 修复提交 | `18fe80a36d5ac0d592a7fbcf7404a7324d639c15` |
| **受测固定源码 SHA** | **`6da7c3a8303ec310d6e87f0981f1abf3b9204f7d`**（含修复与新增 tracked 回归；其后仅本报告与 evidence 文档提交） |
| M3 保留目录 | `/Users/yifengstudio/.codex/worktrees/m3-integrated-packages/SummitEverything` 仅只读查证；未在其中写源码、装环境或切分支 |
| 数据边界 | 仅 Fake/offline provider、loopback、隔离合成工作库；未调用真实模型、飞书、凭据、Keychain 或真实材料；未消费 smoke；未构建 DMG |

未执行 reset / force-push、未移动冻结标签或基线分支、未删除他人分支或工作树。

## 根因

`src/summit_everything/retrieval/planner.py` 把「请求外壳」和「主题内容」放在同一个全局删除集合 `_TOPIC_FILLER` 里，并对其执行 `sub("", …)`；该正则同时包含 `设备|年度|专项|工作` 这类承载信息的名词/限定词。于是

- `玄石展览的访客设备领用办法` 被归一化成 `term:访客领用`，而正式正文原样是 `玄石展览访客设备领用须登记姓名并归还胸牌。`，非连续短语永不匹配：比较只引用预算、把玄石主题报为缺失；单独询问零 citation、零 answer provider 调用。
- 同一集合导致 `年度访客登记` 缩成 `访客登记`（把「有相近但缺限定词的正文」误判为该特定主题已覆盖）。
- `_ENTITY_SUFFIXES` 与 `_entity_mentions` 把 `专项` 当作对象名后缀，使主题短语被识别成伪对象：`玄石展览的专项证章领取` 产出 `的专项`，并额外把页面标题 `专项证章` 提升为对象，造成多余 missing 与错配引用。

这不是「设备」一个词的问题，而是归一化、请求外壳剥离、对象提取、局部主题和回退分支共用边界的同一缺陷；本轮按共享边界修复，未加词表白名单或单例例外。

## 改动范围（仅 1 个产品模块 + 1 个新 tracked 测试文件）

`src/summit_everything/retrieval/planner.py`：

1. `_TOPIC_FILLER` 不再删除 `设备/年度/专项/工作`；这些限定词保留在未知主题内并参与正文匹配与缺失判定。
2. 新增 `_PLAN_SHELL`：只有整段都是计划用词（如 `下一步工作`）时才不构成主题，`为…制定下一步工作方案` 仍是 `generic_plan` 且 `dimensions == ()`。
3. `_ENTITY_SUFFIXES` 与 `_entity_mentions` 去掉 `专项`：它同时是普通主题修饰语（专项预算 / 专项证章）。真正以 `……专项` 命名的对象仍通过 project/alias/line 别名解析。
4. 新增 `_is_name_stem`：拒绝单字虚词或含 `的` 的词干，杜绝 `的专项` 这类伪对象。
5. 片段若以已识别对象开头，其余部分只算该对象的局部主题，不再注册为第二个对象、也不再窃取下一个对象的主题跨度（修复 `玄石展览访客设备领用办法与枫湾活动预算` 的倒序形态）。
6. `_trim_topic_after_entity_suffix` 增加「结尾主题词可分离」规则：`枫湾活动预算` → 对象 `枫湾活动` + 主题 `budget`；`预算时间创作坊` 这类中间含主题词的名称保持不变。

未放宽 `domain/content.py` 的批准/当前版本/hash 信任门；角色、记忆、assistant 历史仍不扩大证据范围；未改产品规格、Web、native、依赖或锁文件；未删除、跳过或放宽任何既有测试与门槛。

`tests/integration/test_c19_topic_scope_normalization.py`（新增，15 项）：设备主题三模式正/倒序双对象、单对象、partial、zero；`年度/专项/工作` 限定词保留与「纯计划外壳无主题」；对象跨度与主题跨度分离。

## RED → GREEN

复演命令与原始日志均在 evidence：

| 阶段 | 命令 | 结果 |
|---|---|---|
| RED 基线 | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q <previous_holdout> <r2_expanded>` | **7 failed, 27 passed**（exit 1）；`plan` 为 `term:访客领用`，单问零引用、provider 0 次 |
| GREEN 修复后 | 同上 | **34 passed**（exit 0） |
| 最小复现脚本 | `reproduce_device_topic.py` | 4/4 两段支持进入引用与 provider passages、missing 空；partial 仅预算且准确报玄石缺失 |
| 新边界脚本 | `reproduce_scope_normalization.py` | 设备/年度/专项/工作 正反控、对象跨度分离、generic plan 全部符合预期 |
| 全量后端 | guarded pytest | 基线 450 passed → 修复后 **465 passed**（+15 新回归），无回归 |

RED 原始输出：`raw-logs/baseline-holdout-34.log`、`raw-logs/baseline-device-topic.log`。GREEN 原始输出：`raw-logs/fix-*.log`、`raw-logs/fix-device-topic.jsonl`、`raw-logs/fix-scope-normalization.jsonl`。

## 验收标准对照（S01–S14 与 ACCEPTANCE 原要求保留）

1. **设备主题不丢词**：三模式、正序、倒序、单对象、双对象下 `required_pairs` 为 `(枫湾活动, budget)` 与 `(玄石展览, term:访客设备领用)`；两段支持同时进入 citations 与真正送入 provider 的 excerpt，`missing_information == []`（tracked 测试与 API 复演双重覆盖）。
2. **缺失准确、零引用不借位**：删掉 B 主题正文（换成开放时间）后只保留枫湾预算并精确报告 `玄石展览：缺少term:访客设备领用依据。`，provider 实收不含开放时间；再把 A 支持也换掉后 citations / source_statements / inferences / advice 全空、answer provider 调用数不增加，缺失按对象/主题逐条列出。
3. **换名称、换陌生主题、限定词**：`年度访客登记` 与 `专项证章领取` 完整正文可答；只有 `访客登记` / `证章领取` 的近似正文不被宣称已覆盖（正反控均入 tracked 测试）；`的专项` 不再成为伪对象，页面标题 `专项证章` 不再被提升为对象。
4. **pair 结构**：A 预算 + B 陌生主题两 pair；A/B 共享预算与排期四 pair 的既有场景保持通过；同对象多主题、无对象并列主题、同页/同 chunk 多对象不跨 pair 错配（既有 tracked 用例 + 本轮回归共同覆盖）。
5. **范围门不可绕过**：全部断言同时核对对象、topic 维度、每条引用正文、provider 实收 passages 与 missing，而不只断言「引用非空」；高分 reranker（`HighestScoreReranker`）与 provider 返回 `missing_information=[]` 均不能突破范围门。
6. **正常问法仍可用**：礼貌双对象比较、预算/排期广义汇总、下一步方案与最近 user 主题接续保持既有 34 项与全量测试通过；未知新对象不回退更早话题；limit 截断仍准确提示（既有用例）。
7. **信任与恢复不退化**：CURRENT/HISTORY、批准/hash 变化、生成中编辑/删除、无关坏页诊断、API/SSE 唯一终态、角色与记忆权限、包 3 恢复归档均未改动；由全量 465 后端与 56 Web 测试守护。

## 检查结果（固定 SHA `6da7c3a`，原始日志与 `.exit` 见 evidence `raw-logs/`）

| 检查 | 命令 | exit | 结果 |
|---|---|---|---|
| guarded 全量 pytest | `env PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | 465 passed，1 条既有 Starlette/httpx deprecation |
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

检查前后 `git rev-parse HEAD` 均为 `6da7c3a`，工作树 clean。未增加 suppressions、未降低阈值、未删除或跳过测试。

## 实际 API/SSE 与 history reopen 复演（隔离 loopback）

`harness/api_c19_replay.py` 在隔离 `SUMMIT_PROFILE_ROOT` 上启动真实 uvicorn（127.0.0.1 随机端口，Fake/offline provider），用合成工作库经 `POST /api/v1/workspaces` 打开、就地建索引后走 `POST /api/v1/queries` SSE，读取 completed 终态与 conversation id：

- 13/13 观测 PASS：设备三模式正/倒序、单对象、partial、zero、`年度`/`专项` 目标正文与限定词不匹配的零引用、history reopen 与 history list。
- 完整比较在 API 层同时引用两段正文且无主题 pair 缺失；partial 只引用预算并单列 `玄石展览：缺少term:访客设备领用依据。`；两周限定词不匹配时零引用并准确报 `缺少term:…依据`。
- `POST /api/v1/conversations/{id}/reopen` 返回 200，消息状态 `completed`，两条 citation 与文本原样保留（历史重开保持正确结果）。
- 复演结束后回连端口失败（无 listener），测试服务已停止。

浏览器 Chrome/AX、DevTools console/network 与 PNG 本轮无可用工具接口，记 **NOT_RUN**；不以 API 200 冒充浏览器验收。

## 语言边界与剩余风险（未独立定级）

- 无「的」的紧凑倒序且对象**完全未知**（库中无该对象任何页面）时，`枫湾活动访客设备领用办法` 这类「名称+复合主题」连续串无法可靠切分，会作为一个未知对象整体处理；有「的」或在语料中可解析对象时边界明确。已作为实测边界记录，未用白名单或词典猜补。
- 目标与正文只差限定词时按不覆盖处理（`季度访客登记` 对 `年度访客登记` 正文 zero），这是本轮有意收紧的方向，可能与「同义改写」期望存在张力，需 QA 独立判断。
- `……专项` 若只出现在问题中且从未作为任何 project/alias/line 出现，不再仅凭后缀提升为对象（按主题处理并报告缺失）；以该名命名的真实对象仍可解析。
- 本轮只做离线/合成范围；真实 provider、飞书、凭据、Keychain、DMG、五日、双机、发布均 **NOT_RUN**，runtime **UNVERIFIED**，有限 smoke 保持 **0/1 未消费**。

## 交接与下一步

- 分支/工作树：`codex/dsh-c19-20261012` / `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012`；受测固定源码 `6da7c3a8303ec310d6e87f0981f1abf3b9204f7d`；工作树 clean、测试服务已停止。
- 本报告的结论仅为 **DEV PASS**。独立 QA 需在另一个 checkout 固定同一 SHA，复跑 34 项 holdout、新增 15 项回归、README 适用全量检查，并独立复演 API/UI 的完整、partial、zero 与 history reopen；QA **NOT_RUN**，由 Sol 调度。
- 即使独立 QA 通过 C19，包 2 门、M3 正式验收与合并 main 仍需用户批准；历史 FAIL 继续有效。
