# 独立验收矩阵

本文件定义完整验收标准，不以旧报告状态改写门槛。产品验收需覆盖 C01–C31、UI 十条契约守卫及用户确认的真实门。每份报告的结论只适用于其明确列出的固定 SHA、场景和证据；历史报告与逐轮记录见[历史矩阵](ACCEPTANCE-HISTORY-2026-10-13.md)及[报告索引](reports/README.md)。当前产品状态见 [PROGRESS](../implementation/PROGRESS.md)。

## 验收准备

读取 LATEST-IMPLEMENTATION 的完整代码 SHA，使用独立 checkout。先运行当前可用检查，再运行交接里真实存在的后端 / 前端 / 打包命令。环境与 fixture 都在隔离目录，禁止请求旧运行 App 或使用旧真实 _vault。

执行者自测不能替代本矩阵的独立验收结果。结果只使用 PASS / FAIL / NOT_RUN / BLOCKED，并附固定版本及证据；BLOCKED 必须说明具体环境条件，不代表产品通过；尚未开发或未实际运行的场景记为 NOT_RUN。

Fake provider 只替代外部网络。使用真实 writer、reader、路由、SQLite 和 UI。真实 provider 质量与真实权限另记，必须有用户明确的范围和动作。

## 前端可用性补充（2026-10-16）

以下是固定前端 UX 的补充可观察场景，不替代 C01–C31，也不把本地 Fake 流程冒充真实服务验收：

- 今日 1280×800 合成非空首屏同时显示会议标题与第一条、任务标题与第一条、记录输入及导入入口；4 场会议默认最多 3 场，6 项任务默认最多 5 项，展开后完整结果可达且原分页仍有效。
- 记录保存和多项导入使用返回结果中的精确 `item_id` 接续；同名对象按 ID 定位。来源已处于 processing/reviewing 时只继续现有任务或稿件，不能产生重复 job。
- 审批五组顺序稳定；待处理组默认展开，空组默认收起但可以展开，打开/返回单项专注页后展开状态保留。confirmed 正式页已存在而索引 `not_ready` 时，索引待处理计数为 1 并展开；真实空库仍保持空组。
- 稿件编辑、来源和改动差异分别按需查看；冲突选择未写入 API 时不可称已保存，只在最后确认时生效。侧栏导航、打开正式页、切换工作库和浏览器关闭均保护未保存内容；刷新审批数据不能覆盖正在编辑的正文。
- 逐项验证同名正式页/来源准确定位、多稿仅确认所选一份、确认回执保留实际 `index_update` 与保存 page ID。内部 ID、路径、hash、原始 JSON 不得成为业务可见文案。

截图和几何检查必须使用会议/任务均非空且至少 4/6 条的 fixture；空首页或单条 fixture 不能证明首屏密度与折叠上限。

## Must 场景

| ID | 阶段 | 输入 / 触发 | 可观察的通过标准 |
|---|---|---|---|
| C01 | Foundation | 当前基础命令、独立 hash 样例、关键反例 | 现有门禁行为通过；报告只覆盖骨架，不称应用已完成 |
| C02 | M1 | 新库 / legacy 库 / 重复 ID / 跨界路径 | 新目录可用；legacy 不静默转换；非法结构拒绝且原内容不变 |
| C03 | M1 | 线 / 项目增改、移动、归档、非空删除 | ID 稳定、关联可用、事实不复制；非空删除拒绝，归档知识仍能查询 |
| C04 | M1 | 原件 / draft / helper 冒充正式且带有效形状的 proof | 检索、邻页及 answer context 都没有来源 canary；原始字节和来源 hash 保留 |
| C05 | M1 | 随手记录、列表刷新、取消选择、进行中 / 部分确认 / 完成 / 失败重试 | 来源状态准确反映整理作业与关联稿件；进行中或待审核来源不能用新操作 ID 重复生成稿件；失败或已完成来源只有明确选择重新处理后才能再次生成；保存与刷新不调用外部模型 |
| C06 | M1 | 用户先选定一个项目；一份包含多个主题的输入生成多稿，只接受一份 | 所有稿件均归入用户选定项目；仅选中页变为正式，其他稿仍待审；来源关联完整，未接受 task 未执行。模型不得改变项目归属；跨项目自动分流不属于本项 |
| C07 | M1 | 两项重要数字冲突 | 未处理不能确认；选依据或明确未决可确认，正文不把未决当确定事实 |
| C08 | M1 | 审阅期间目标页被外部改动 | 409 / 明确差异，外部内容不被覆盖，稿件可继续编辑 |
| C09 | M1/M2 | 直接写日志 / 思考，不绑项目或关联线 | 自由正文可保存；单一 writer 与新批准；无隐式模型调用或项目状态变化 |
| C10 | M1 | 修改正式页正文 / 元数据但保留 proof | 立即不作为答案依据，待确认可见；重新确认后当前新内容可用 |
| C11 | M1 | 新版已批准，SQLite 尚存旧 chunk；邻页也过期 | 缓存 version 与当前版本不一致者不进上下文 / 引用，不能只检查新 proof 有效 |
| C12 | M1 | 未变页增量、模型 fingerprint 改变、full 失败 | 不重复嵌入未变输入；无静默全量调用；不同维度不混用，旧代未被失败重建破坏 |
| C13 | M1/M3 | 已完成案例、归档项目、被替代 / 失效规则 | 业务结束不屏蔽有效知识；当前问答不用被替代规则作当前依据，历史询问带效力标记 |
| C14 | M1/M3 | 问答流、取消、断流、旧历史引用 | 事件有序且终态正确；无假完成；引用打开正确页与版本，旧引用提示已更新 |
| C15 | M2 | 飞书材料分页、选择一条、正文文件响应、过期授权 | 正确范围、仅选择材料导入、列表无模型；权限问题具体反馈，不假定 tenant / user scope 通用 |
| C16 | M2 | 未确认 task、重复执行、远端超时、不同 payload | 未确认零写；同意图一次副作用；unknown 不重 POST；不同 payload 拒绝 |
| C17 | M2 | 已完成飞书任务再点完成、任务编辑日期 | 完成态幂等成功；用户日期按协议原样处理；没有第二套本地正式任务状态 |
| C18 | M2 | 批准知识，另有 project_progress action 未确认 | 知识生效，项目进度保持；独立确认后才改变 |
| C19 | M3 | 事实、跨页对比、工作方案、没有相关资料 | 引用对应依据，推断 / 建议独立标明；缺失资料明确，不补造业务数字 |
| C20 | M3 | 用户表达 / 原件语句 / assistant 推断形成记忆 | 仅明确用户表达可候选；未确认不进入活跃 prompt；角色不能解除证据或写权限 |
| C21 | M3 | 不同 workspace / 两本地 profile 读同一库 | 库切换不串话；各机历史、角色、记忆和索引独立；工作库无这些本地状态 |
| C22 | M3 | 中断整理，另一 profile 继续；完成流程按月归档 | 稿件可见且状态准确；未知模型调用不自动重发；receipt 和 unknown 未丢，诊断事件不积在同步区 |
| C23 | M1/M3 | 原子写中断、月归档中断、并发相同意图 | 恢复结果可解释且不丢确认内容；相同意图不重复；未确认内容不因恢复入库 |
| C24 | M4 | 非本机绑定、无 token、恶意 Markdown / 资料命令、秘密错误 | API 不执行未授权副作用，安全渲染，资料不能指挥工具；日志 / API 无凭据值 |
| C25 | M4 | 新构建内部 DMG，启动 / 退出 / 重启、粘贴、多文件和文件夹选择 | 无系统 Python / Node / Docker 也能运行；源代码 / 前端身份匹配；多文件/目录导入仅收 TXT/Markdown 且限 100 项 / 100 MB / 20 MB每文件，不跟随链接或越出用户所选根；不误杀旧服务、不覆盖旧 App |
| C26 | M4 | 真实样板确认并初始化 | 只写最终确认内容，原桌面文件保留；不复制样板原件，不把待审数字当最终值 |
| C27 | M4 | 明确选定真实模型 / 飞书验收场景 | 抽取忠实、真实检索 / 重排 / 引用可用，scope 与任务结果可核实；记录费用范围 |
| C28 | M4 | 全流程现场验收 + 五个实际工作日 | 用户业务闭环通过，无未关闭关键问题；试用日期与结果记录，不能提前勾满五天 |
| C29 | M5 | Studio → Air → Studio 正常往返及待审接续 | 同库 ID、正确版本、无丢失或重复动作；切换前由用户确认 OneDrive 同步 |
| C30 | M5 | 各机首次索引、相同库不同绝对路径 | 每机显式建索引、随后增量；路径不改身份；历史 / 角色 / 记忆不随工作库迁移 |
| C31 | M5 自动 | 隔离模拟冲突副本、重复 ID、半写、unknown receipt | 阻止相关写入，恢复 / 核实前不猜测合并或重复远端写；真实库不制造破坏性异常 |

外部 Markdown 自动发现补充：在隔离合成工作库中由外部进程原子新增/替换/删除注册目录 Markdown，1–2 秒轮询后阅读器、项目树和审批待确认数应自动同步；连续写入不能永久延迟。正文区域没有编辑、新增正文或插入链接控件。变更本身不批准、不建索引、不调用 provider；只有显式确认后才沿现有首次索引或增量门更新。无效/删除文件应显示不可用，文件修复后恢复；工作库切换与旧请求迟到不得串库。问答读取仍逐次校验当前文件。

同一场景跨阶段可以先验证已实现部分，但整行 PASS 必须说明覆盖内容。阶段退出只看该阶段应完成的 Must 和已声明真实门；未来场景不当成本阶段失败，但不能删除。

M1 的 C13 覆盖归档项目仍可检索、被替代内容不进入当前问答，以及历史检索引用带效力标记；历史会话浏览和旧引用 UI 属于 M3。M1 的 C14 覆盖 SSE 事件序号、唯一终态与取消；断流恢复和历史引用打开 / 更新提示属于 M3。部分实现的检查结果不得替代整行独立验收结果。

## 真实质量问题与黄金依据

真实样板整组确认后，由用户确认材料建立答案依据。至少验证合同进展与批准的区别、成本分子 / 分母、跨期比较、缺失数据、下一步方案。用实际依据核对，不沿用旧待审数字作为 oracle。

模型质量验收要同时检查原文事实是否被改变、未决是否被写成结论、方案是否混入正文；不能只检查 JSON schema 或 HTTP 200。

## 严重程度与退出

- P0：丢数据、未经确认外部写 / 付费操作、原件或失效内容进入可信答案、秘密泄漏、误写旧库。
- P1：核心流程无法完成、版本覆盖、外部重复、证据错误、安装应用不可用、本地库状态串用。
- P2：不阻断核心行为的交互 / 表达问题，保留记录与明确处理安排。

Must FAIL、未关闭 P0 / P1 阻止相关阶段通过。真实门未测时只能给“模拟门通过 / 实际门待完成”，不得给完整产品 PASS。

## 缺陷与复验

缺陷写：阶段、代码 SHA、案例 ID、严重度、最小材料、复现步骤、预期 / 实际、证据、建议边界。

测试者可增加独立黑盒测试，但不改产品代码，不因为实现现状而改期望。实现者修复并提交新 SHA；新报告标明修复项及受影响回归，旧报告保留。

## M2.1 Fake 复验（C15 与日历）

启动与完整检查命令见 README 的 M2.1 节；使用空的隔离工作库。点击模拟授权，搜索并筛选 owner/shared，换页选定材料、取消选择；确认列表不产生 intake/job/draft/page。再只导入所选，读取 sources API 并核对原字节、SHA-256 与 external_identity；检查队列为 pending、仍无稿件 / 页面。重放 operation_id 不重复原件，换 payload 必须 409。日历明确指定 2026-10-09 至 2026-10-10 与 Asia/Shanghai，检查日程 / 空态 / 分页。

`tests/integration/test_feishu.py` 使用真实 API / SourceStore / 隔离库，外部边界 Fake：多页、空页、visibility、只取选择正文、失败逐项、denied/expired/scope/404/malformed/timeout/unavailable、UTF-8 / 类型 / 安全文件名 / 大小、state 重放 / 到期 / 跨运行 / callback 地址 / Origin、授权 Bearer 门、refresh token 轮换与失效、logout、重启幂等及原件写后中断恢复。`FeishuPanel.test.tsx` 覆盖真实组件的失败授权、退出授权、分页选择、部分结果、取消与日历空 / 错误态。

实现者自测不填写独立 QA 通过。真实 Feishu 用户权限、账户登录、真实材料与钥匙串持久化均未测；任务写属于 M2.2。

M2.1 审查回归：用不同的 API/Web 端口注册 callback，确认前端请求实际注册目的地且不跟随 redirect / 携带凭据；检查 callback allowlist CORS / no-store、非法外部地址拒绝。导入合法材料与“ .txt”等被来源 writer 拒绝的名称，必须逐项失败且其余继续。模拟 token_expired / not_authorized 后查看界面状态并确认读取按钮关闭，missing_scope 显示权限不足且没有虚构成功；检查合成 AppCredentials 与 user token 隔离、配置无秘密、状态 / 错误 / 授权 URL 无秘密。

## M2.3 Fake 复验（C09 / C18）

使用合成库分别直接保存日志与思考，验证无关联、仅关联主线、主线加项目；列表刷新零模型调用。显式 AI 辅助后编辑 / 取消建议，确认 suggestion 不写页面；保存成功后从日志列表重开。重复相同 operation_id / confirmation_id / payload（含并发）只写一页，重试响应相同；改变 payload 需 409。用失效主线或不属于该主线的项目验证拒绝。

新建项目不生成概览页；从项目目录明确创建，重开；更新必须带当前内容版本，旧版本409且原正文保留。概览可以相对链接权威事实页。创建 / 更新 / 直接确认日志与思考后，核对 project progress 版本与值均未变；再通过 M2.2 独立 progress action 确认能单独改变。此处 DEV 测试不是独立 QA 结论。

已有索引时，日志、思考、项目概览、稿件批准、直接页面确认和外部编辑重新确认都应自动对同一 fingerprint 增量更新；首次索引仍需用户确认。检查 MutationResult 的 index_update 与 `/index/status` 的 state，覆盖未启用、成功、失败 / 中断。增量不得重嵌未变内容或触发 full / model_change。失败后索引 state 应为 stale，旧 SQLite chunk 经版本资格门不得成为当前引用；C04/C10/C11/C12/C13/C23 保持独立验收。


## M2.2 Fake 复验（C16–C18）

此节列 M2.2 Fake 复演期望。阶段 A 当前独立 QA 与合并后复验见[报告索引](reports/README.md)，该历史通过不替代本次新维护 SHA 的验收。命令：`uv run pytest -q tests/integration/test_actions.py`；`npm --prefix web test -- TasksPanel.test.tsx`；M1 / M2.1 回归沿用 README 全量命令。

1. 未确认、模型建议或知识批准均零任务写 / 零进度变化。手动标题、显式无日期 / 全天 / 带偏移时间后审阅 exact 值，确认仍不执行，另点执行才调用 Fake。确认后编辑使原确认失效，必须新 ID 重新确认。
2. 同 ID/hash 多次执行、双击和并发只一次副作用；进行中202 + Location。改变 hash409，两个有效 action 可同标题。已完成任务再完成直接成功，无第二次 PATCH；只选 due 时标题 / 描述不变。
   创建 / 编辑响应须与明确请求字段一致，容许 timestamp int/string 的合法归一化；明确清空描述 / 日期按返回对象验证。同 GUID 旧对象、未生效字段或 completed_at=0 均不能记 succeeded，转 unknown 后不重发。
3. 注入远端已写后 Timeout、响应损坏、真实子进程退出；重启保留 Fake remote 文件，running→unknown，无证据不重发，不按标题猜成功。只读核实确切 Fake 证据 / 用户独立明确 outcome，可终结并保留 evidence；同核实 ID重放，变更依据409。迟到响应不得覆盖明确终态。
   Fake `task_result` 只有在 client_token、动作类型、目标和返回字段均匹配当前动作时才构成证据；普通 FeishuTask、无关任务或冲突结果保持 unknown。此 Fake 契约不表示真实 Feishu 有按 client_token 查询端点。
4. 完成回执跨月摘要后重启可查 / 防重；unknown/running 不压掉。摘要写后删 active 中断允许相同副本，损坏hash或冲突副本必须409。
5. 候选转换保留 draft/source，旧 GET /actions 数组兼容；新列表cursor/limit分页。进度动作锁 + expected_version + write_intent，只独立确认后改进度，旧版本失败不覆盖；模拟写后丢回执可读本地 writer evidence。

实际账号权限、真实 GET/POST/PATCH、真实全天日期提取 / 时间 normalization、真实 token 查询能力、凭据 / OS Keychain、DMG、真实材料和模型质量均 NOT_RUN。全天 Fake 午夜约定不是真实协议验收。2026-10-10 最终 UI 树复演：独立临时 workspace/profile，创建（显式无日期）→确认→执行→refresh，完成→确认→执行→refresh 已完成；控制台warn/error为0。异常 / 并发 / 子进程路径由真实服务和文件测试覆盖，未声称浏览器全部复演。

> 以下阶段记录中的历史通过/失败只适用于其注明的受测版本。真实质量和 M4/M5 要求仍有效；当前状态见 PROGRESS。

## 阶段 B / C 追加门（历史复演范围与仍适用的真实验收标准）

本节记录 Stage B 固定源码的历史复验，不替换 C01–C31、不降低原 MUST。B03/B04 的服务端门控只适用于其标明的历史 SHA，不能作为当前 HEAD 的行为说明。表格中的历史结果仅帮助追溯；当前实现状态以 PROGRESS 为准，当前任务验收范围以 LATEST-IMPLEMENTATION 为准。

| ID | 阶段 / 历史记录 | 可观察、可复验的退出标准 |
|---|---|---|
| B01 | 离线QA PASS；真实证据 NOT_RUN | 官方飞书文档可以 `.md` 后缀读取原始 Markdown，authorize、OAuth v2/v3 token 与 refresh 轮换、tenant token、用户身份、妙记搜索/逐字稿/产物、日历日程、task 读/建/改的 endpoint、token 类型、scope、分页、时间与错误码已逐条写入[协议矩阵](../architecture/PROVIDER-PROTOCOL-MATRIX.md)（核对日期 2026-10-10）。仍未知并明确阻断：账号侧 scope 可用性、逐字稿二进制 content-type、按 client_token 证明丢失写结果的 endpoint。DeepSeek / Model Studio 映射与价格同表记录 |
| B02 | 离线QA PASS；真实证据 NOT_RUN | profile 设置、原子更新与 Web 设置 UI 有实现。Feishu app secret 与 user token 现在共用同一 vault 命名空间并以 app_id 为账户标识（`VaultCredentialStore`），设置 UI 写入的槽就是 adapter 读取的槽；离线测试覆盖轮换、登出、profile/app 隔离、损坏值与同命名空间。此轮未录入任何真实密钥；合成凭据故障/隔离profile离线PASS；OS Keychain 拒绝/锁定/重启及真实多profile仍 NOT_RUN |
| B03（历史） | 旧 SHA 的离线QA PASS；真实证据 NOT_RUN；真实请求 0 | 固定旧 SHA 的 `FeishuHttpProvider` 协议反例。当时 real data 由 `feishu.real_data_enabled` 门控（默认 409 `stage_c_authorization_required`）。当前包 A 行为见本表后的说明。task 写仍因没有独立结果证明能力而 disabled。真实 OAuth 与读取仍 NOT_RUN |
| B04（历史） | 旧 SHA 的离线QA PASS；真实证据 NOT_RUN | 固定旧 SHA 的 stub-tested adapters 与有限 smoke；当时真实模型业务由服务端拒绝。当前包 A 行为见本表后的说明。真实维度、服务质量、账单和 R03 用户评定仍 NOT_RUN |
| B05 | 独立离线QA PASS | 最终受测源码576895f；独立388+25/Web45，实际合成浏览器/原生冷启动/重启/5秒延迟启动和退出清理PASS；见最终独立复验报告。历史R1–R4证据原样保留；OS Keychain和DMG未运行 |
| B06（历史） | 对固定 SHA 的离线 QA PASS / 历史合并点 | Luna High 独立 checkout 固定 576895f；与执行者环境分离，离线完整检查、新增失败路径和实际 UI 复验。PR #10 当时已合并，merge `41207e5` 的产品树与受测 SHA 一致并通过合并后核验。真实门另行验收 |
| R01 | 部分授权 / 冒烟未执行 | 用户于 2026-10-10 授权有限合成冒烟：一次 Feishu OAuth code exchange、必要时一次 refresh；DeepSeek chat / Model Studio embedding / rerank 各最多一次合成请求。执行前核对官方价格和端点；提示词建议 CNY 5 为保守操作上限（非用户指定预算）。秘密只经安全本地入口。真实材料、日历/task读取、真实内容外发和任务写入仍需逐项授权 |
| R02 | 真实只读 / NOT_RUN（冒烟例外不含业务读取） | 固定 B 受测 SHA；真实 OAuth / scope / refresh / Keychain、连接后的有界日历 UI 与 MCP 直读、选中材料和 task 读取实际协议 / UI 完整且资源范围准确；无隐式正文批准或模型发送。日历直读按服务端身份/scope校验，材料与任务读取仍使用逐次确认计划 |
| R03 | 真实模型质量 / NOT_RUN | 真实 LLM / embedding / rerank 各自可核对配置、实际调用、用量 / 费用；预定质量样例、用户评定、资格 / stale / 注入反例和独立 QA 通过 |
| R04 | 真实任务 / NOT_RUN | 独立确认创建 / 编辑 / 完成；各日期语义与清空、目标 / 字段和 GET 回读证实；journal 核实 / unknown 不重发；遗留测试资源及处理责任明确 |
| R05 | C 整合 / NOT_RUN | 固定代码 / 文档 / 独立 QA / manifest / PR / main 关系清楚；所有适用必需真实项通过，否则为部分完成或 BLOCKED；代码变更后对应门重新复验 |

### 一次性授权计划验收标准

真实模型 organize/index/query 和 Feishu 材料/任务 read/import 必须先预览确切内容范围、显式确认，再在原业务路由提交 plan id。飞书日历 read 是只读例外：授权连接后 UI 与 MCP 直接调用日历接口，服务端仍校验配置身份、凭据与 scope，并限制单次响应、请求数和时间；失败不自动重试。取消、过期、配置/来源/页面/Feishu 授权代次变化、异 workspace/profile 或未确认均不得外发。计划保护的请求先有限预留；中断状态保留为 unknown 且不能释放/重放。日历直读按 adapter 的有限调用链、单次响应大小与单个请求 deadline 约束，不自动重试。provider usage 只保存响应报告的 request id/token 数；缺字段保持未知，真实账单需在服务商侧人工核对。本要求不替代整行 MUST 验收。



### 日历直读专项验收

Real 已授权连接后，今日页刷新和 MCP `list_calendar` 不调用或消费 acceptance-plan；API 与 agent API 都直接经过同一 `FeishuService.calendar`，并保留 profile/workspace、应用或用户凭据、scope、IANA 时区、start < end、limit 1–30 与 cursor 校验。Real 缺 app_id 必须返回配置错误，不能降级为 Fake 成功；用户身份无 token 或缺 calendar readonly scope 时请求被拒绝。provider 对显式区间最多进行 tenant-token/refresh + primary lookup + events 的有界链路（最多 3 次 HTTP 请求），DeadlineTransport、4 MiB 响应上限与无重试规则继续生效；真实区间仍单页并以截断提示说明，Fake 分页保持。超时/错误保留原日历与错误态，不显示空列表。合成 API 测试核对 agent workspace 不匹配拒绝；HTTP Mock 统计实际调用数，禁止真实飞书/模型/Keychain。

### C28 五个实际工作日记录模板

本表保持空白，必须在完整真实闭环获准后按实际工作日填写。不得预填日期或将模拟结果记作真实体验。

| 实际日期 | 使用场景/范围 | 已知缺陷及级别 | 用户观察/决定 | 证据链接 |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

范围外的 DMG、五日、双机及 M3–M5 依原矩阵单独判断。资源已准备不是授权或 PASS；没有执行或未获授权的项保留 NOT_RUN / BLOCKED。P0/P1 与阻断 MUST 的缺陷不能带入下一阶段，P2 不得隐瞒或自行降级。

R03 之外的有限合成连接 smoke 已由用户于 2026-10-10 另行授权：一次 Feishu OAuth code exchange、必要时一次 refresh，以及 DeepSeek chat / Model Studio embedding / rerank 各最多一次短合成请求。它只记录受限连接、协议、用量与实际费用，不能替代本行真实模型质量、预定样例、用户评定或独立 QA。执行前查当日官方价格；CNY 5 是提示词建议的保守操作上限，不是用户指定预算，超出可可靠界定范围时暂停付费调用并只询问额度。

### 2026-10-11 历史收口范围说明

2026-10-11 的用户选择为离线源码修复、固定 SHA 独立 QA 后整合；真实 provider、OS Keychain、DMG 和真实质量不进入当轮 PASS。B01–B04 按离线协议/实现验证，B05 包含实际浏览器/原生开发壳与合成 credential 故障，B06 为独立 checkout 对精确 SHA 的离线 QA 与整合。原 C01–C31、R03 真实模型质量及全 v1 MUST 均保持；不把那些未测项降为可省略。

额外必验失败路径：DNS 暂停取消后不得继续发 HTTP；TLS 握手未完成也关闭 TCP；同 client 请求 A 超时不取消 B；退役准入原子；真实 pycares bytes 地址不重新进入系统 DNS；不安全 HTTPX mount 发出请求前拒绝；完整 JSON wire 计入上限；压缩响应在解压前拒绝；Real 任务写 UI 与后端拒绝一致。测试保留真实内部实现，外部边界只用 HTTP 合成远端和 MemorySecretBackend。原归档 harness 的构造死锁/原因字符串差异与历史 FAIL 保留，修正版不能覆盖原件。

UI附加反例：Real app_configured/identity=app/authorized=false时日历可请求本机API（数据授权门由服务端继续把守），搜索仍要求user；真实authorize URL不得交Fake callback helper，必须显示官方安全链接和本机状态刷新，不能通过刷新旧authorized状态宣称本轮授权成功。原生开发壳编译/窗口与外部系统浏览器实际连接分开，后者NOT_RUN。
