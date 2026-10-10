# 给下一位 Luna：Stage B 阻断修复、剩余实现、证据与独立 QA

你是 SummitEverything 的执行 Luna。继续现有 Stage B，不重新从 Stage A 开始。先处理 Sol 核实的阻断缺陷，再完成剩余 B 实现、离线检查和实际浏览器/原生证据；固定新 SHA，安排独立正式 QA，通过后才决定源码整合。**Sol 本轮只是独立 DEV 候选评估，不能代替正式固定 SHA QA。**

## 1. 实际起点

- 主源码仓库：`/Users/yifengstudio/Documents/GitHub/SummitEverything`。
- 已有工作树：`/Users/yifengstudio/.codex/worktrees/stage-b-real-providers/SummitEverything`；分支 `codex/stage-b-real-providers`。
- 原基线：`ba0d330820d5d98b7e17e86cad5007b5a3a16c1d`。
- Sol 开始时是 dirty tree，46项改动/新文件。用户之后授权核验后提交推送，原样保存实现检查点 **`1fede419a49b76c2f82e392be2803597cedab1f2`**，原开发文档检查点 **`4966a6824bcc98b065e754e2e7a27d3f94a1539c`**。后续评定报告/提示词提交在其后；不要把4966或分支未来HEAD当成QA已通过。
- 第一步自行记录当前完整HEAD、branch、dirty、实际tracked/untracked、远端分支状态、最新报告和在运行服务归属。不要reset/checkout覆盖其他人的修改；复用合适的已有worktree，不在共享main切分支。
- 必读：AGENTS.md → README/PROGRESS → PRODUCT-SPEC → ARCHITECTURE/WORKSPACE-v1/API-v1 → IMPLEMENTER、全v1计划、TESTER、ACCEPTANCE → LATEST-IMPLEMENTATION、原B/C提示词、partial DEV报告、PROVIDER-PROTOCOL-MATRIX、tasks/plan与tasks/todo。
- 核心新增依据：`docs/quality/reports/2026-10-10-STAGE-B-SOL-DEV-REVIEW.md`、同级evidence/`2026-10-10-stage-b-sol-dev-review`。读全部SB-01–13及实际harness/log，不只看摘要。

采用适用的实现、来源核验、增量开发、Git、浏览器验证及完成前验证技能。普通库选择、文件划分自行决定并记录，不反复请用户批准。新鲜代码审查和QA应使用独立上下文；不能自签通过。没有独立能力时交出固定候选与完整QA提示词，保持QA pending。

## 2. 已核实进展与验收边界

现有非秘密settings原子存储/Fake默认、CredentialVault、macOS backend、设置UI、DeepSeek/Model Studio stub adapters、显式操作接线、embedding fingerprint和原子SQLite generation存在；失败model_change保留旧索引。Feishu仍Fake-only：真实OAuth/material/calendar/task HTTP adapters未实现，KeychainCredentialStore独立组件未service-wired，未验证真实user identity和OS生命周期。

Sol在独立文件副本中实跑：后端190通过、前端36通过，ruff/format/mypy/lock/API生成一致/typecheck/lint/Web build/Swift build通过。另有独立后端10失败、前端1失败，不能用原测试全绿掩盖。Python包在并行Swift构建污染临时副本时首跑失败，纯源码顺序构建通过。1条后端弃用与3条既有前端lint warning保留。

B01协议门未完成；B02/B04/B05 readiness FAIL；B03真实adapter NOT_RUN且Fake生命周期有失败；B06整合NOT_RUN。实际browser/native/Keychain故障、真实服务、M3–M5、DMG/五日/双机均未在此轮通过。

保留原产品MUST与C01–C31。原件/稿件/helper不进语料；当前正文批准与版本资格以domain/content.py为唯一规则；模型无批准权；知识批准不改变task/项目进度；unknown不重发、不按同名猜成功；工作库无Git；索引/凭据/历史/日志本机profile隔离。SWB/SK/旧vault/既有应用只读；真实“场地与酒店”仍需专门内容确认，不自动导入、不提交原件到Git。

## 3. 第一优先：修复SB-01–12，记录SB-13

按影响与依赖分切片，每个切片先复现反例，再实现，再运行该反例与受影响回归。把必要反例纳入正常测试；保留Sol FAIL的harness/log，不改期望来变绿。

1. **SB-01 P0外发资格**：QueryService当前把所有缓存chunk传remote rerank后才验页面。将资格筛选前移到任何模型正文外发之前，真实路径给StorageArea、purpose与缓存hash；仅confirmed且当前缓存版本qualified候选可发。邻页扩展同门。覆盖原件/稿件/helper、role冒充、invalid/superseded、外部编辑、重新批准后旧缓存。合成canary不得进入任何不应收到它的provider请求。不能只检查最终citations为空。
2. **SB-02 P0引用时序**：模型调用期间页面可变。模型返回后、发布引用/完整回答前重读复核版本和资格；若依据过期，不继续把依赖旧依据的生成正文作为可信回答发布。设计明确的失效/重查行为，不自动付费重试。
3. **SB-03 P1取消**：cancel signal贯穿召回/embedding/rerank/LLM，阶段间检查；DELETE202后不启动后续调用。已发请求可能已计费要准确说明。覆盖取消在不同阶段、超时、断流、唯一SSE终态；provider不自动重发。
4. **SB-04 P1规模**：本地召回后对有限qualified候选做remote rerank，保持ID/index映射；101+chunk库可查询，不能全库外发/提高adapter上限掩盖。设候选数量、bytes、token/成本边界。
5. **SB-05/06 P1配置恢复与隔离**：打开/重开/切库从当前profile恢复有效Feishu配置；消除进程全局service/config/token跨库残留。清空callback/App ID变更应同步失效待处理state。profile/app/provider/user-account隔离可测，类型不可靠model_copy绕过校验。
6. **SB-07/08 P1注销与refresh**：logout失效pending state、在途callback/refresh；不得删除后又写回旧授权。按profile/account串行refresh，锁内二次检查和原子版本保护，保留最新refresh token。覆盖存储失败、拒绝/锁定、重启、scope丢失、expired、并发、logout竞态。真实user identity缺项与refresh expiry字段按官方证据补齐，不能沿用仅App ID覆盖用户的存储。
7. **SB-09 P1Model Studio账户**：SettingsView PATCH必须保存model_studio_account_id；密钥保存/删除绑定已保存账户/配置版本，避免未保存表单选择与运行时账号错配。覆盖切换、reload、重启与错误恢复。
8. **SB-10 P1状态一致**：available/configured/disabled_reason与服务端执行路径一致。不能UI说“当前不可对外请求/需授权”却调用remote。已有有限smoke走单独限定合成payload/次数的入口；不新增重复授权流程，不把所有真实业务按钮普遍解锁。
9. **SB-11 P1HTTP边界**：三类model adapters当前完整下载再检查大小。改为有界stream读取、及时关闭超限响应、有限连接/读取/整体时间，并释放operation-scoped client。严格解析HTTP/JSON/业务错误、finish_reason/截断、索引/维度/finite/usage。超时和未知不自动重发，异常不能包含原始body/header/key/prompt。
10. **SB-12 P1恢复验收门**：与ba0d330比对，ACCEPTANCE R03原真实模型质量要求被有限smoke替换。恢复原R03质量/独立QA标准，有限smoke仅作附注或额外行；不能缩减MUST。Sol没有修此文件，检查点保存的是待修候选，不能沿用改低后的标准。
11. **SB-13 P2交接一致**：在新DEV交接前同步协议矩阵、API契约、tasks账本、真实/合成状态、费用估计、未测与固定SHA。历史报告追加纠正说明，不改当时原FAIL/未测事实。责任为本执行Luna，期限为下一固定候选交接前。

## 4. 完成B01–B04剩余实现

先核对官方当前协议并维护matrix：来源URL/核对日期、endpoint/headers/request/response、user/tenant token、精确scope、分页/大小/时间范围、错误/幂等/结果核实、价格与未知项。可查官方SDK具体源码，注明版本与能证明的边界；动态页面不可读时寻找可读一手来源，不把SDK DTO或Fake约定当完整协议。用户是Feishu自建应用管理员，可开scope；scope可授予不是未实现的理由，也不等于接口语义已经确认。

- B02：将统一安全credential边界接线至实际OAuth/runtime，App secret与user token分项；避免设置UI与token store存在两套不互通slot。Keychain unavailable fail closed，不能退回明文或内存。非秘密配置/GET/PATCH/reload/preview零provider请求；实时secret仅在安全本机表单短暂内存，结束清空、禁止前端持久化。
- B03 OAuth：真正浏览器授权、精确已注册callback（用户已提供localhost:8765/callback，仍从安全本地配置读取）、session/profile/account-bound一次性state、code exchange、user token/scopes、refresh轮换、logout与安全错误。callback/default uvicorn access log必须屏蔽code/state/query/body/headers；浏览器与原生都验证，不复制Fake fetch callback到真实流程。
- B03读取：metadata分页、明确选择后内容下载并保留原字节/hash/source身份、部分失败；日历显式起止/结束不含/IANA时区与分页；task读取。仅HTTP stubs/合成数据开发，无真实业务读。unsupported类型具体阻断；不假冒PDF/Word/OCR完整支持。
- B03写入：仅官方已证实的task create/edit/complete字段/日期/offset/清空映射，保留独立确认/journal/receipt/unknown/no-resend。查证只读核实如何绑定操作、目标与实际结果；不存在依据就维持相关能力disabled，报告B仍不完整，不能编造task_result端点或按标题猜成功。实现离线写adapter不授权真实写入。
- B04：显式整理、日志辅助、index execute、query的selected provider正确；模型无法改变用户选定项目/签发approval；严格结构、冲突与建议分离。fingerprint包含已核实provider/model/endpoint/dimension/protocol；设置变更无静默全量调用，审批real embedding需另行显式计划；失败/维度不符/中途退出不破坏旧generation。索引建完再次核对变动页面并准确提示stale。成本未知不显示¥0。

关键协议无法证实时保持能力禁用，写清具体未知、证据来源与后续验证方法，继续其他独立任务。不能把disabled能力当B完成；任何缩减已确认功能需用户产品决定，不能为收口省略。

## 5. 完整离线与实际DEV证据

只使用隔离模拟工作库、profile、Fake/MockTransport及专用合成Keychain项；不碰用户既有项。默认测试强制不访问真实模型/Feishu。运行README实际命令并逐条留退出码与warning：

```sh
uv run pytest -q
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
swift build --package-path native
git diff --check
```

API/生成TS必须一致，依赖改变更新lock；不要把uv build和Swift build在同一污染目录并行。已有warning保留，失败不能删测试或改门。对新增组件/adapter、取消/拒绝/锁定/恢复/并发覆盖实质行为；现有190/36不构成完整B oracle。

实际浏览器与原生开发壳离线复演：确认候选代码/前端/run identity/workspace/profile/window归属，保存设置/账户切换/Fake授权与注销/reload/重启/Keychain故障以及显式模型动作的stub行为。Keychain测试只创建命名明确的合成测试项，读写和清理只限本轮创建项，不扫描用户凭据。不能用Memory tests或Swift build证明OS行为。

从操作开始记录console/network；截图与实际状态/操作ID对应。留实际执行harness字节、SHA-256、脱敏API/磁盘断言、screenshots、console/network摘要、manifest；每条重算匹配。录入secret/OAuth时停敏感捕获或过滤header/body/query，不能把密钥/tokens/code/state存入HAR/截图/log/Git。原生窗口无法确认归属时NOT_RUN，继续其他工作，不制造证据。保留本次失败链与旧Stage A撤回/纠正链。

## 6. 有限真实smoke授权（精确保留，先安全准备）

用户于**2026-10-10**已授权以下有限smoke，Sol本轮未使用，次数仍0：

| 服务 | 累计最多 | 数据与目的 |
|---|---|---|
| Feishu OAuth | code exchange 1次；必要refresh 1次 | 用户自行完成浏览器授权，仅验证token接入；不读取身份资料/材料/日历/task |
| DeepSeek chat | 1个已发请求 | 短小纯合成输入，协议/连通性 |
| Model Studio embedding | 1个已发请求 | 短小纯合成输入，有界维度 |
| Model Studio rerank | 1个已发请求 | 短合成query+少量合成候选 |

这是跨执行/审查/QA共用次数，不是每个人各一套。失败、超时、unknown、重定向等已发请求也占用，关闭SDK/HTTP自动retry。禁止通过业务Ask/完整索引/整理整库绕过单次计数；smoke不得联动材料读取、模型链追加或任务写。

API keys/App secret仅由用户在本机安全UI/Keychain录入；不得要求贴聊天，不猜遮蔽值，不用CLI参数、shell history、环境变量或明文配置作回退。尚未录入可请用户完成安全本地输入，继续无需秘密的开发，不重复问是否愿意测试。账户/地区/模型/URI等非秘密只问确实缺失项，已给事实沿用并验证。

smoke前先处理相关安全阻断与日志脱敏，离线验证payload与计数。逐条记录endpoint、精确合成payload、账号非秘密标识、次数、当日官方价格/计费单位、输入/输出上限、单次及合计保守估计和停止条件。**CNY5为提示词建议保守操作上限，不是用户指定预算。** 能可靠控制在范围内就依已有授权进行；不能可靠界定则暂停付费调用，只问费用上限，不重复问是否愿意测试。非付费/离线轨道继续。实际费用无账单只能估计/待核，不能写0元。

授权**不包括**真实业务材料、Feishu材料/日历/task读取、身份资料读取、真实内容外发、任何task创建/修改/完成/清理，不包括扩大请求次数、账号或模型范围。这些需单独逐项授权，且较广C轨道在B正式QA后再安排。有限smoke可在其安全前提通过后先行，但结果只证明受限连接/协议，不等于模型质量、B/C完成。若发现P0/P1/secret泄漏/错误账号/unknown立即停对应真实轨道；修代码后回B新SHA独立QA，已用次数不可自动恢复。

## 7. 固定新SHA、独立正式QA、再整合

1. 每个可复验切片提交小逻辑commit；README/PROGRESS/LATEST-IMPLEMENTATION/tasks更新实际状态与未测。无secret/真实材料/.venv/node_modules/构建产物进入Git。已有DEV检查点不重写历史、不force push。
2. 修复SB-01–12、完成B实现/证据后，固定新的完整源码SHA，再提交交接文档与证据；区分源码SHA、DEV证据/报告SHA、QA报告SHA。干净tree+SHA只是入口之一，不等于通过。
3. 安排独立验收者使用新上下文和源码库外独立checkout，**精确ref=new SHA**，不得默认main或使用作者工作树。QA只改测试/报告，不改产品/验收；B01–B06、适用C01–C31、Stage A unknown/no-resend、知识/进度独立确认、原子恢复、当前引用资格和全部SB反例要复核。正式QA默认离线；有限smoke已有结果可作为单独证据，不能QA重跑突破次数。
4. QA FAIL由执行者单独修复提交新SHA，QA重新固定复验并保留旧FAIL；未关闭P0/P1禁止阶段通过。缺独立环境/上下文就交出完整QA提示词并保持pending，不自验合并。
5. 正式QA通过后再创建PR，保留受测SHA可追溯（不squash丢掉身份），附件含检查、DEV/QA/真实门区分和未测项。合并后独立checkout核对受测源码树一致、报告/manifest逐项匹配及适当冒烟；再决定进入更广C。未完成真实门不宣称整个产品或C通过。
6. 仅清理本轮有归属且无需保留的服务PID/端口、专用合成Keychain项；保存未解决候选和证据。不动用户已有应用/库/凭据，不误杀其他服务。

最后给用户：当前源码/报告/证据SHA，B01–B06具体结论，P0/P1/P2未关闭数与修复链，自动检查/实际浏览器/原生/真实smoke分别结果，次数/费用/账号范围/未测项，独立QA是否开始/通过，PR/merge/main/tree核验（仅实际发生项）。M3–M5、DMG、五日、双机继续独立列账。把固定证据交回技术评定者；不能只说“全部通过”。
