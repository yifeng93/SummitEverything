# Stage B 独立离线 QA — 7f3119a（2026-10-11）

**FAIL。未关闭 P0=0、P1=1、P2=0（本报告已执行范围）。** 完整已有检查通过，但新增独立反例复现：刷新响应未知后重启会重发已消费的一次性 refresh token。该提交不能作为 Stage B 离线通过或合并依据。实现者修复必须固定新 SHA，另写复验报告；本 FAIL 和原始日志保留。

## 身份、授权与证据

- 角色：独立 backend/offline 验收者；不是实现者。未修改产品实现、已有测试、依赖、lock 或历史证据；未 commit/push/merge。
- 精确源码/契约提交：`7f3119a511fda6f3d2771af4cf09fd9a9026edb7`，detached HEAD。
- checkout：`/Users/yifengstudio/.codex/worktrees/qa-stage-b-sol-backend/SummitEverything`；独立 `.venv`、`web/node_modules`，临时合成工作库由 pytest 创建。Python 3.12.13 / uv 0.12.3 / Node v24.15.0 / npm 11.12.1，Darwin arm64。
- 阅读：AGENTS、README、PROGRESS、PRODUCT-SPEC、ARCHITECTURE、WORKSPACE/API v1、TESTER、ACCEPTANCE、LATEST、全 v1 计划、tasks/plan 与 todo、Sol 旧评定、R1–R4 DEV、Sol closure DEV 与协议矩阵。固定版本交接部分仍写“准备固定”；受测身份以本报告精确 SHA 和 Git/文件核验为准。后续 docs-only checkpoint 没有切入本 QA。
- 每个测试/运行检查都设置 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`。独立负控制确认非 loopback socket、真实 DNS、OS Keychain 构造被拒绝；实际产品运行 `SUMMIT_OFFLINE_GUARD_ACTIVE=1`。
- 真实 exchange / refresh / chat / embedding / rerank 实际仍各 **0/1**，真实远端任务写 **0**。只使用合成字符串、MemorySecretBackend、MockTransport 和数字 loopback；没有读取用户身份、真实材料、日历、任务或 Keychain。
- [identity-audit.json](evidence/2026-10-11-stage-b-independent-offline-qa/identity-audit.json) 记录完整树 ID、环境、lock 与 API 指纹。`src/web/native/scripts/pyproject.toml/uv.lock` diff 为空，连续 API 类型生成后 `web` 未变化。Sol source-hashes **101/101**；R1/R2/R3/R4/Sol 五份证据 manifest **22/22、22/22、38/38、34/34、32/32** 全匹配，历史 FAIL/原日志未改。

## 实际命令结果

完整 argv、退出码、耗时与 PYTHONPATH 见 [check-results.json](evidence/2026-10-11-stage-b-independent-offline-qa/check-results.json)，可复演 runner 为 [run_checks.py](evidence/2026-10-11-stage-b-independent-offline-qa/harness/run_checks.py)。以下均在上述独立 checkout 执行。

| 检查 | 命令 | 退出 / 结果 |
|---|---|---|
| 独立依赖 | `uv sync --locked --group dev`；`npm --prefix web ci` | 0；lock 未变 |
| 全后端 | `uv run --locked --no-sync pytest -q -p no:cacheprovider` | 0；**383 passed**，57.36 s；1 既有 Starlette warning |
| 静态 | `uv run --locked --no-sync ruff check src tests`；`ruff format --check src tests`；`mypy src` | 均 0 |
| 锁 | `uv lock --check` | 0 |
| package | `uv build` | 0，wheel/sdist 生成；隔离构建环境 sitecustomize 缺 aiodns，见下方纠正 |
| package 修正版 | `uv build --no-build-isolation` | 0，guard 无导入错误，wheel/sdist 生成 |
| API 类型 | `npm --prefix web run api:types`，连续两次 | 均 0；生成文件与 HEAD 一致 |
| Web | `npm --prefix web test -- --run`；`npm --prefix web run typecheck`；`npm --prefix web run lint`；`npm --prefix web run build` | 均 0；10 files / **45 passed**；3 既有 React effect warnings |
| 独立黑盒 | `uv run --locked --no-sync pytest -q -p no:cacheprovider docs/quality/reports/evidence/2026-10-11-stage-b-independent-offline-qa/harness/test_independent_boundaries.py` | **1；8 passed / 1 failed**，重复仍同一 FAIL |
| 固定身份/manifest/guard | `uv run --locked --no-sync python docs/quality/reports/evidence/2026-10-11-stage-b-independent-offline-qa/harness/audit_identity.py` | 0；五 manifests / 101 source hashes 匹配 |

所有原始命令日志位于相邻 evidence。初次 `uv build` 虽设置要求的 PYTHONPATH，uv 临时隔离 build backend 不含 aiodns，使 sitecustomize 导入报错而继续；**不把该次当作 guard 成功加载证据**。只在本 QA venv 安装 hatchling（未改 lock），再用 `--no-build-isolation` 成功重跑，保留两份日志与 tooling-install 日志。模型和业务测试均在同步好的独立 venv 中运行，guard 导入与负控制通过。

## 案例与限度

下列 PASS 是本候选已有测试经独立完整执行、源码审阅及指定补充黑盒的离线范围；不能推成真实 provider、UI 或完整 v1 PASS。

| 案例 | 结果 | 本轮实际覆盖 |
|---|---|---|
| SB-01/02，C04/C10/C11/C13 | PASS（离线） | stale cache 不进入 rerank；answer 返回后重新读页使旧引用与旧答案失效；原件/draft/helper、重新批准旧缓存、邻页扩展均经 canonical eligibility；真实 reader/writer/SQLite。`test_stage_b_regressions.py`、`test_qualified_retrieval.py`、content contract。 |
| SB-03，C14 | PASS（离线） | embedding/rerank/answer 阶段取消抑制后续 dispatch，生成后取消不发布成功；SSE 唯一终态。仍不代表实时外部费用或 M3 历史 UI。 |
| SB-04 | PASS（离线） | 101 chunks 本地召回外发至多20 qualified候选；wire/request限额与排序index保持。 |
| SB-05/06 | PASS（已测离线范围） | 已保存 callback、workspace/App ID 状态隔离；配置重建、状态恢复；真实 vault profile/app槽隔离回归。不是 M3 多机完整验收。 |
| SB-07 | PASS（离线） | logout时阻塞app秘密读取、token request在途、new authorization、旧服务state、one-use callback；R4真实route/service/coordinator/vault/provider，HTTP与SecretBackend替代。 |
| SB-08 / B02/B03 | **FAIL（重启unknown刷新）** | 同进程 single-flight、logout/new login/config竞争与malformed响应通过；独立新增跨重启 no-resend 失败，见 QA-B-01。 |
| SB-09 | PASS（组件/API） | Model Studio account typed保存、凭据绑定已保存account；Web组件与API回归通过。实际浏览器由另一验收者负责。 |
| SB-10 | PASS（离线） | status/实际runtime一致：业务模型路径被服务端拒绝；synthetic smoke固定输入、有限账本、失败消费、并发one-use。测试调用只是合成HTTP。 |
| SB-11 | PASS（离线） | 流式有界响应、business-error、deadline、异常脱敏与client释放；完整JSON转义/envelope计入限額。 |
| SB-12/13 | PASS（契约与范围说明） | R03仍保留真实质量/用户评定/独立QA，有限smoke单列；产品/API/矩阵记业务禁用、任务写门、真实门NOT_RUN。旧DEV历史段仅按其SHA理解，不采用旧pending摘要当当前通过。 |
| R2 / real任务写门 | PASS（离线） | app-first日历/选中正文/detail；搜索/task列表user-only；主日历官方nested形状、invalid/empty/ambiguous拒绝；truncated与cursor拒绝；配置执行路径。独立6项create/update/complete×read on/off，独立确认后重复执行均409 `result_proof_unavailable`，**HTTP calls=0**、action仍confirmed。 |
| R3/R4/Sol取消/资源 | PASS（离线） | numeric pycares bytes不调用系统DNS；DNS取消Future、deadline返回workers0、解除后无HTTP；TLS无握手peer EOF；同client A超时B成功；不安全mount发送前拒绝；压缩在读/解压前拒绝；trickle头/body deadline/FIN/reset收敛；retire准入原子、完整操作租约、new-operation拒绝、close一次。 |
| 凭据corrupt/denied/restart | PASS（指定离线项） | 新增2项真实API重启后app日历成功且user槽读取增量0；corrupt或deny user时搜索401 credential_unreadable、status未授权、app仍configured、无secret泄露。OS Keychain未触达。 |
| Stage A Fake/C09/C15–18/C23 | PASS（自动回归范围） | 全suite含真实路由/files/locks/writer的选择导入、独立确认、unknown/restart/receipt/atomic write、日期与项目进度分离回归。没有把过去UI截图当本候选新证据。 |
| B01 | PASS（离线mapping）；真实NOT_RUN | 当前协议矩阵/adapter shapes与反例核对；不重新消耗账号请求。主日历等官方核对由主验收报告单独记录；不声称本agent另做网页取证。 |
| B02–B04 | **FAIL（适用离线门）** | B02/B03受QA-B-01阻断；B04已测模型/检索路径PASS。所有真实质量/账号门NOT_RUN。 |
| B05 | 部分PASS；GUI/native **NOT_RUN（本agent）** | 后端/Web自动检查及合成credential故障通过；实际浏览器/native由并行独立验收者负责，待其报告。 |
| B06 | **FAIL / 整合NOT_RUN** | 固定SHA独立QA发现P1；未PR/merge。 |

## QA-B-01 — P1：刷新结果未知后重启重发同一单次 token

- 固定 SHA：`7f3119a511fda6f3d2771af4cf09fd9a9026edb7`；关联 SB-08、B02/B03、官方refresh单次轮换/no-resend契约。
- 定位：`src/summit_everything/integrations/feishu/service.py:103` 初始化空 `_consumed`；`:120` 仅内存记录digest；`:326` 检查与`:331`标记；`:332`派发。结果未知未改变持久化user credential，也未持久化消耗状态。
- 最小输入：合成app和MemorySecretBackend；真实OAuth parser接收Bearer、有效scope、expires_in=1和synthetic refresh token；MockTransport在refresh收到请求后抛ReadTimeout。没有真实身份/secret/provider。
- 步骤：真实API新建库→保存Real app/settings/秘密→authorize/callback成功→materials触发refresh→503 provider_timeout，refresh_count=1→再次materials返回401，count仍1→关闭TestClient并创建新app，同profile/后端，open同库→再次materials。
- 预期：未知刷新已消费，跨重启仍不得重发该token，应保持401并要求重授权，计数1。
- 实际：新coordinator `_consumed=[]`，持久化old refresh仍在；再次发送同token，**refresh_count=2**，返回503。重复运行同样8pass/1fail。
- 证据：[test_independent_boundaries.py](evidence/2026-10-11-stage-b-independent-offline-qa/harness/test_independent_boundaries.py)，测试 `test_independent_unknown_refresh_is_not_resent_after_restart`；[正式失败日志](evidence/2026-10-11-stage-b-independent-offline-qa/independent-boundaries.log)、[重复失败日志](evidence/2026-10-11-stage-b-independent-offline-qa/independent-boundaries-repeat.log)。
- 测试仅替换外部HTTP和SecretBackend；未mock route/service/store/coordinator/lease。已有InstrumentedStore/整provider Fake测试用于回归，不是本缺陷判定依据。
- 初次harness误期待504，实际产品契约为503/provider_timeout；原日志保留为 `independent-boundaries-initial-harness-status-mismatch.log`，修正status oracle后才到达并复现真正restart失败。没有改产品或降低no-resend期望。
- 已立即通知实现者。建议在**HTTP dispatch前持久化消费保留**并fail-closed；写保留失败不得HTTP、异常/退出/重启不得重发，成功轮换只能新token恢复；新SHA复验保持旧报告FAIL。

## 未测与下一步

真实OAuth/code exchange/refresh、user-info身份确认、scope权限、真实材料/二进制type、日历/task读取和日期账号规范化、模型维度/可用性/费用/质量与R03全部 **NOT_RUN**；OS Keychain拒绝/锁定/重启 **NOT_RUN**。合成MemorySecretBackend fault不能替代OS验收。DMG/安装包身份/干净机器、M3–M5、五个实际工作日、双机 **NOT_RUN**。源码wheel/sdist不是可安装DMG。

本轮整体Stage B离线结果 **FAIL**，完整真实Stage B/C/产品验收 **NOT_RUN**。实现者提供新精确SHA后，在新的独立checkout/环境复验QA-B-01、写保留失败、rotation/log-out/config/跨进程竞争及受影响回归，再重新判断合并门。本QA不切换HEAD、不修改实现、不回写历史PASS。
