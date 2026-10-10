# Stage B 独立 DEV 候选评估 — Sol — 2026-10-10

**结论：独立 DEV 候选评估 / 正式固定 SHA QA 尚未开始。阶段 B 不可给 PASS，当前不满足正式 QA 入口。** 现有测试全绿，但独立反例为后端 10 FAIL、前端 1 FAIL；另发现一项验收门缩减。未关闭缺陷：P0=2、P1=10、P2=1。未实施的 Feishu 实现和缺失证据另列，不重复计作缺陷。

## 1. 受评树、权限更新与独立性

- 指定 worktree：`/Users/yifengstudio/.codex/worktrees/stage-b-real-providers/SummitEverything`。
- 开始实测 HEAD：`ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`；分支：`codex/stage-b-real-providers`。tracked modifications 加实际 untracked 文件共 46 项，尚无 B 实现提交。
- 用户在评估中补充授权：核验后提交、推送。据此原样保存实现为 **`1fede419a49b76c2f82e392be2803597cedab1f2`**，原开发文档为 **`4966a6824bcc98b065e754e2e7a27d3f94a1539c`**。未切分支、改产品实现、降低验收期望、创建 PR 或合并 main。文档检查点保留开发者原有声明，包括本报告明确拒绝采纳的 R03 改写。
- 测试前按 Git tracked/untracked 清单复制 390 个文件到源码库外的独立临时副本。测试后、提交后逐文件 SHA-256 核对 **390/390 一致**。没有在实现者目录装依赖、生成 API、构建、格式化或增加产品测试。
- 实测临时目录：`/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/summit-stage-b-sol-review-8nxpo73b`；其 `candidate` 是文件快照，不是正式 QA checkout。Python 使用现成 venv、`--no-sync`，前端依赖复制到副本。
- 使用独立 `sitecustomize.py` 禁止 Python 非 loopback socket connect/connect_ex，禁止 macOS Keychain backend 构造/读/写/删；测试只注入 Memory 或合成 stub。真实 Feishu、模型服务、用户 Keychain、真实业务材料操作次数均 **0**。仅访问公开一手协议文档；源码推送单独记录。
- 本报告和提示词属于新增评定产物。既有开发报告保持历史事实。固定 DEV 检查点不追认本次为正式 QA；后续必须修复并固定新 SHA，由新上下文、独立 checkout 正式 QA。

已读取用户指定的 AGENTS、ACCEPTANCE、LATEST-IMPLEMENTATION、B/C 提示词、partial DEV 报告、协议矩阵、tasks/plan、tasks/todo，并核对 README、PROGRESS、产品规格、架构、工作库/API 契约、IMPLEMENTER/TESTER 和 v1 计划及相关源码/测试。Stage A 历史 PASS 没有被搬成 B PASS。

## 2. B01–B06 独立结论

状态按验收手册使用 PASS / FAIL / NOT_RUN / BLOCKED；“部分实现”只描述进展。下表是 DEV readiness 结果，所有正式 B QA 项仍 NOT_RUN。

| ID | 本次结果与进展 | 核实证据与剩余条件 |
|---|---|---|
| B01 | **NOT_RUN（完整协议门）；部分实现** | 模型映射有矩阵、typed 接口及 MockTransport 测试。本次复核 DeepSeek chat、Model Studio embedding/rerank 官方页；Feishu token 官方页仍无可读正文，SDK 源码可见 token request/response，但不替代数据 endpoint scope/日期/结果核实契约。矩阵自己明确未知能力禁用；Feishu real 未实现。管理员能开 scope，不等于 endpoint mapping 已完成。 |
| B02 | **FAIL；部分实现** | SettingsStore 原子更新/Fake 默认、CredentialVault profile/provider/account 摘要、MacOSKeychainBackend fail-closed、设置 UI 和独立 token store 存在。原单元/API 测试通过，但 SB-05/06/09 复现恢复、隔离与账户保存失败，SB-07/08 涉及凭据生命周期。KeychainCredentialStore 只有 profile/App ID，没有已验证 user account identity，且未 service-wired。OS 拒绝/锁定/重启、原生配置与真实 Keychain 隔离 NOT_RUN。 |
| B03 | **NOT_RUN（real HTTP adapters）；Fake 生命周期 FAIL** | FeishuConfig.mode 只允许 fake；create_app 固定 FakeFeishu + MemoryCredentialStore，未接 KeychainCredentialStore。不存在真实 OAuth/material/calendar/task adapter。scope 当前为 Fake `minutes:read/calendar:read`，不是已映射的真实权限。原 refresh/logout 测试通过，但 SB-07/08 复现 logout 后旧 callback 恢复授权、并发 refresh 丢新 token。真实 task 日期/清空/unknown 只读证据未落实，保持未启用；不能把禁用视为已完成。 |
| B04 | **FAIL；部分实现** | DeepSeekLLM、ModelStudioEmbedding/Reranker 接入显式整理/日志辅助/索引/问答。维度、index、finite、fingerprint、手动 real indexing、失败 model_change 保留旧 generation 的既有测试通过。SB-01/02 是资格与引用 P0；SB-03/04/10/11 是取消、规模、能力状态与响应边界 P1。模型 live 行为/质量/价格/账户支持 NOT_RUN。 |
| B05 | **FAIL（readiness）；正式 QA NOT_RUN** | 原检查矩阵本次复跑通过；独立补充反例失败。原浏览器证据只有 replay.md，没有截图字节、完整 console/network 或 manifest；本轮没有补做实际浏览器或原生 UI。修复、完整 DEV 证据、新 SHA、独立正式 QA 缺一不可。 |
| B06 | **NOT_RUN** | 本轮只固定并推送 DEV 分支检查点；没有修复复验、PR、main 整合、合并后树/manifest 核验。此次 Sol 评估不能替代正式 QA。 |

## 3. 缺陷（同一快照 / 实现 SHA 1fede419…）

后端前八项的失败原文见 [counterexamples.log](evidence/2026-10-10-stage-b-sol-dev-review/counterexamples.log)，后两项见 [additional.log](evidence/2026-10-10-stage-b-sol-dev-review/additional.log)，前端见 [frontend-counterexample.log](evidence/2026-10-10-stage-b-sol-dev-review/frontend-counterexample.log)。harness 用真实 reader/writer/SQLite/routes，仅外部 provider 用 Spy/MockTransport；没有执行实际外部调用。以下 P0 表示离线复现的产品风险，不表示真实数据已经外泄。

| ID / 级别 | 位置、最小复现、预期与实际 | 修复边界 |
|---|---|---|
| **SB-01 / P0** | [query.py:206](../../../src/summit_everything/retrieval/query.py#L206)，B04/C04/C10/C11。确认合成 canary 页→索引→外部改正文保留旧 proof→查询。预期旧版本不进入 remote candidates；实际 Spy reranker 收到旧 canary，最终 citations 虽为空，外发已发生。 | 在任何外部 rerank 前用真实 StorageArea、purpose、缓存 content hash 调同一资格门；只对 qualified、限量候选排序；邻页扩展同门。覆盖原件/稿件/helper/失效/重新批准旧缓存。 |
| **SB-02 / P0** | [query.py:280](../../../src/summit_everything/retrieval/query.py#L280)，B04/C10/C11。AnswerProvider 接收合法 passages 后，在返回前外部编辑页面。预期停止/失效该答案；实际返回旧“北馆”正文和 validity=current 引用。 | 模型返回后、发布引用/完整答案前重新读页复核版本与资格。失败时不能只去掉 citation 而继续输出依赖旧依据的可信答案。 |
| **SB-03 / P1** | [app.py:1020](../../../src/summit_everything/api/app.py#L1020)，B04/C14。阻塞 query embedding→DELETE cancellation 返回202→释放 embedding。预期不再开始后续 provider 请求；实际 rerank、answer 均调用，最后才输出 cancelled。 | cancellation 贯穿 query/HTTP 生命周期，阶段间检查；已经发出的调用可能计费，但收到取消后不得新启后续调用。断流与唯一终态另测。 |
| **SB-04 / P1** | [query.py:206](../../../src/summit_everything/retrieval/query.py#L206) 与 [rerank.py:47](../../../src/summit_everything/integrations/rerank.py#L47)，B04。一个合成页101段 heading→索引101 chunks→ModelStudioReranker。预期 bounded retrieval 可答；实际全库传入101候选，adapter在请求前抛 max_documents 错误，问答无法完成。 | 本地召回后选有限 qualified candidates；稳定保持原候选索引/ID，不通过提高上限或分批全库外发掩盖问题。限制总 bytes/费用。 |
| **SB-05 / P1** | [app.py:442](../../../src/summit_everything/api/app.py#L442)、[app.py:580](../../../src/summit_everything/api/app.py#L580)，B02/B03。保存 `http://localhost:8765/callback`→新 app实例重新打开同库。GET settings 为已保存URI，authorize却发默认 `127.0.0.1:5173/api/…`。 | 打开/重开库从当前profile恢复有效配置；不能只有PATCH修改内存config。配置清空、App ID切换与未完成state要一致失效。 |
| **SB-06 / P1** | [app.py:280](../../../src/summit_everything/api/app.py#L280)、[app.py:596](../../../src/summit_everything/api/app.py#L596)，B02/C21隔离边界。库A配置/模拟授权→同app打开全新库B。B设置为空，但status仍已授权并继承A服务config/token。 | provider/credential/OAuth state/capability随profile与account切换；不能沿用进程全局FeishuService。该隔离反例不代表已验完M3。 |
| **SB-07 / P1** | [service.py:94](../../../src/summit_everything/integrations/feishu/service.py#L94)，B02/B03。authorize生成待完成URL→logout204→访问旧URL。预期invalid_state且未授权；实际callback200重新authorized。 | logout作废pending state及在途认证结果；refresh/callback完成不能复活已登出的credential。 |
| **SB-08 / P1** | [service.py:136](../../../src/summit_everything/integrations/feishu/service.py#L136)，B02/B03。同一近过期token并发两个materials请求；refresh1阻塞，refresh2先写新token，随后refresh1返回。预期一次refresh或版本保护；实际两次refresh，最新token2被较旧token1覆盖。 | 每profile/account串行刷新、二次检查与原子版本保护；加入存储失败/登出竞态/重启/最新refresh token负例。不能依赖真实服务恰好拒绝第二次调用。 |
| **SB-09 / P1** | [SettingsView.tsx:92](../../../web/src/components/SettingsView.tsx#L92)，B02。更改“Model Studio账户标识”→保存provider设置。预期PATCH含新account；实际请求缺 `model_studio_account_id`，仍留旧账号。真实凭据可能写在新标签后却无法被运行时选中。 | 保存全部对应typed字段；设置/密钥操作绑定已保存的账户版本，不混用未保存表单与持久化配置。 |
| **SB-10 / P1** | [settings.py:426](../../../src/summit_everything/integrations/settings.py#L426)、[runtime.py:22](../../../src/summit_everything/integrations/runtime.py#L22)，B02/B04。StubKeychain配置real/enabled+合成key；summary宣称available=false、stage_c_authorization_required，journal assist却调用被Spy替代的DeepSeek入口并200。 | 服务端实际可执行状态与API/UI一致。未批准范围真正关闭；已有有限smoke授权走单独有次数/数据范围的入口。无需新增重复确认，不能仅展示“当前不可对外请求”却继续收费调用。 |
| **SB-11 / P1** | [embedding.py:84](../../../src/summit_everything/integrations/embedding.py#L84)，同模式在llm/rerank，B04/C24。MockTransport提供20MB分块响应，adapter声明8MB上限。预期超过上限即停读；实际 `Client.post`先完整读取20MB，再检查len。 | 流式、累计bytes限制、关闭超限响应；区分连接/读取/整体deadline。异常与HTTP client生命周期需脱敏并释放；禁止自动重试。 |
| **SB-12 / P1** | [ACCEPTANCE.md:172](../ACCEPTANCE.md#L172)，验收门。与base `ba0d330`比较，原R03“真实模型质量”行的质量与独立QA要求被替换成“有限合成冒烟已授权/NOT_RUN”。 | 恢复原R03标准，有限smoke另加状态/附注；授权小范围测试不能缩减原MUST。评定者未编辑该文件，提交仅保存原候选；下一执行者须修正此文档缺陷。 |
| **SB-13 / P2** | [PROVIDER-PROTOCOL-MATRIX.md](../../architecture/PROVIDER-PROTOCOL-MATRIX.md)、[API-v1.md](../../contracts/API-v1.md)、tasks账本。矩阵仍称“没有真实app path接adapter”，API设置扩展仍称“业务调用尚未启用”，与runtime调用路径冲突；DEV报告末尾又称所有外部动作未授权，与同文新增授权冲突。 | 下位Luna负责在下一DEV交接前同步最终能力/授权/已固定SHA状态；历史报告加纠正说明，不篡改当时事实。以summary/runtime一致的离线反例复核。 |

SB-01/02 为阻断可信答案的 P0。SB-03 至 SB-12 为 P1。SB-13 不单独阻断，但不得继续误导实现/验收。未实施real Feishu、Keychain service wiring和缺失UI证据是阶段缺项，不能通过只修11个测试就宣称B完成。

## 4. 本次实际运行的检查

全部在独立文件快照或纯源码打包副本中执行；没有将开发报告数字冒充本次结果。`PYTHONPATH=<review>/guard:<review>/candidate/src`用于Python测试/API导出，`UV_OFFLINE=1`禁止uv取网络依赖。

| 命令 / 检查 | 结果 |
|---|---|
| `uv run --no-sync pytest -q -p no:cacheprovider` | exit0，**190 passed**，1条既有Starlette/httpx弃用warning；含loopback启动器测试 |
| `uv run --no-sync ruff check src tests` | exit0 |
| `uv run --no-sync ruff format --check src tests` | exit0，48 files already formatted |
| `uv run --no-sync mypy src --cache-dir /tmp/summit-stage-b-sol-mypy-cache` | exit0，32源文件 |
| `UV_OFFLINE=1 uv lock --check` | exit0，37 packages |
| `UV_OFFLINE=1 uv build --offline` | 首次exit2：Git-free副本并行Swift构建生成的绝对临时symlink进入sdist；另建仅含390个源码文件的package-source顺序重跑，exit0，sdist+wheel。前次失败保留，不将其归因产品功能；安装包仍NOT_RUN |
| `uv run --no-sync python scripts/export_openapi.py` + `web/node_modules/.bin/openapi-typescript web/openapi.json -o web/src/api/generated.ts` | exit0；两份生成文件与候选逐字节cmp相同 |
| `npm test -- --run` | exit0，9文件/36 tests |
| `npm run typecheck` | exit0 |
| `npm run lint` | exit0，3条既有react(set-state-in-effect) warnings（TodayView/ProjectsView/AskView），不是zero warnings |
| `npm run build` | exit0 |
| `swift build` | exit0；只证明编译，不证明原生/Keychain行为 |
| 独立`test_review_regressions.py` | exit1，8 failed；早期logout反例错误地访问testserver被invalid_redirect挡下，修正为精确返回URI后正式归档版本复现callback200；不使用早期结果证明SB-07 |
| 独立`test_review_additional.py` | exit1，2 failed |
| 独立`SettingsView.review.test.tsx` | exit1，1 failed；仅加在临时快照，不在产品测试目录 |
| 原候选 `git diff --check` / 提交前cached check | exit0 |
| 提交前后文件指纹 | 390/390匹配；高置信凭据pattern检查46项改动，0命中。合成fixture声明经阅读核查；不是完整安全认证 |

通过矩阵的stdout见本聊天工具记录，仓库中归档的是观察摘要，不伪造原始检查log。失败反例归档实际stdout（脱敏合成state/临时路径、规范stdout行末空白）、执行harness字节和manifest。见 [证据复演说明](evidence/2026-10-10-stage-b-sol-dev-review/README.md)。

## 5. 未测、smoke边界与QA入口

**NOT_RUN**：真实OAuth/code exchange/refresh；Feishu材料/日历/task GET/POST/PATCH；实际模型、账户支持、用量/费用、输出质量；真实Keychain拒绝/锁定/存储/重启/多account/签名应用身份；本轮实际浏览器console/network与原生设置UI；DMG、安装包、五日、双机；完整M3–M5。既有190项回归不等于C01–C31逐行正式QA通过。旧replay.md不是可重算的UI证据包。

本次没有使用有限smoke授权，后续仍有效：Feishu code exchange≤1，必要refresh≤1；DeepSeek chat、Model Studio embedding、rerank各≤1，全部为短合成输入。次数跨DEV/QA累计，失败或unknown仍计已发请求，不能自动重试；不含身份资料读取、真实材料、日历/task读取、真实内容外发或task写入。Keys只能由用户在本机安全UI录入，不收集到聊天/命令行/明文文件。

CNY5是提示词建议的保守操作上限，**不是用户预算**。未来执行前核对当日官方单价、端点和有界输入/输出估算；不能界定在该上限内时，仅询问费用上限，不重复询问测试意愿。本轮未报价、未扣费；协议文档访问不是smoke请求。

**当前不宜执行smoke**：OAuth real adapter和安全持久化尚未接通；callback日志需先确保不记录code/state（开发uvicorn使用默认access log）；模型路径有资格/取消/状态不一致等缺陷，没有专用次数受限合成测试入口。先修与目标smoke有关的安全阻断和本地入口；已有授权无需重问，未录入凭据时等待本机输入，同时继续其他离线工作。

正式QA入口为：SB-01–12修复并有新DEV证据；补齐B实现或明确未证实能力与B仍不完整；恢复原验收门；浏览器/原生与专用合成Keychain故障证据、可复演harness/manifest完整；固定新的源码SHA，干净工作树；另一个独立上下文与checkout。QA必须保留本次FAIL、复验新SHA并回归Stage A。**本次固定1fede419/4966a682仅消除“无法定位改动”问题，没有达到以上入口。**

## 6. 下一执行者

归档证据manifest已逐条重算：10/10匹配，manifest SHA-256为 `c5d718a0546f5fdc8138aee51b9f717448f913f8a86594264dd66e0ad4eedcdb`。追加评定交接文档后，89项产品/配置/测试文件仍与执行快照及实现检查点1fede419逐字节一致；后续报告提交只含评定文档和证据。

完整可直接转交的提示词：[PROMPT-STAGE-B-LUNA-AFTER-SOL-REVIEW.md](../../handoff/PROMPT-STAGE-B-LUNA-AFTER-SOL-REVIEW.md)。先修阻断，再补B和证据；新SHA正式独立QA通过后，才决定源码整合。Sol此次评估不能代替该QA。
