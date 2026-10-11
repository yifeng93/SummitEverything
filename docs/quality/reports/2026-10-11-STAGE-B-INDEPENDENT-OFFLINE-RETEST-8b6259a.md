# Stage B 独立离线复验 — 8b6259a（中间提交，2026-10-11）

原 QA-B-01/P1 重启重发已关闭（本提交离线范围），新增 QA-B-02/P2 存储布尔类型宽松解析待修复。**这是中间提交验收，未签发最终 Stage B 离线通过或整合批准。** 下一提交需新固定 SHA、新独立 checkout 复验；真实接入、质量、OS 与交付门仍 NOT_RUN。

## 固定身份与权限

- 精确源码：`8b6259a9aa6ff2e52b700134abadff24de46dc08`，detached HEAD；checkout `/Users/yifengstudio/.codex/worktrees/qa-stage-b-refresh-final/SummitEverything`。
- 新独立 `.venv` 和 `web/node_modules`，`uv sync --locked --group dev` / `npm ci` 均0；Python3.12.13、uv0.12.3、Node24.15.0、npm11.12.1。
- 每条测试/runtime设置 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`。numeric loopback/MockTransport/MemorySecretBackend合成范围；真实DNS/非loopback/OS Keychain负控制被拒绝。
- 产品实现、已有测试、lock、历史证据未编辑；仅新增报告/harness/evidence，无commit/push/merge。和7f相比产品只改 `feishu/provider.py`、`feishu/service.py`；Web/native/scripts/依赖/lock完全一致。
- 真实OAuth exchange/refresh/chat/embedding/rerank均0/1，真实远端任务写0。合成refresh计数是测试oracle，不消耗真实额度。

## 命令与结果

[check-results.json](evidence/2026-10-11-stage-b-independent-offline-retest/check-results.json) 记录完整argv、退出码、PYTHONPATH与耗时；日志在相邻evidence。runner [run_checks.py](evidence/2026-10-11-stage-b-independent-offline-retest/harness/run_checks.py) 可复演。

| 项 | 实际结果 |
|---|---|
| `uv run --locked --no-sync pytest -q -p no:cacheprovider` | 0；**386 passed**，1既有Starlette warning |
| Ruff check/format、mypy src、uv lock --check | 全0 |
| `uv build --no-build-isolation` | 0；wheel/sdist；仅在独立venv装hatchling，guard正常导入 |
| API types连续两次 | 全0；生成文件与HEAD相同 |
| Web test/typecheck/lint/build | 全0；**45 passed**，3既有React effect warnings |
| 独立原9项+新存储故障12项 | 0；**21 passed**，1warning |
| strict-marker独立反例（后新增） | **1；2 failed**（string `"false"`、integer0），12 deselected |
| source/manifest/guard audit | 0；源码指纹、历史证据逐项匹配，protected diff为空，workers0 |

完整命令统一使用上述guard。原7f报告/evidence已进入本候选并逐项重算保持一致；R1/R2/R3/R4/Sol/restartDEV/原QA七份manifest数量 **22/22、22/22、38/38、34/34、32/32、20/20、27/27**。新current source-hashes完全匹配，环境/tree/lock/API详情见 [identity-audit.json](evidence/2026-10-11-stage-b-independent-offline-retest/identity-audit.json)。未重写任何raw log。

## QA-B-01/P1复验：PASS（离线）

原[7f FAIL报告](2026-10-11-STAGE-B-INDEPENDENT-OFFLINE-QA.md)保持FAIL；本8b通过不回写旧结论。既有真实API→service→coordinator→vault→HTTP适配器链只替代SecretBackend和外部HTTP。

- lost-refresh-response：同进程与重启后均401且同refresh请求只一次；存储预留在dispatch前完成。
- reservation set-then-raises：储存True后抛错，返回503，HTTP0；重启仍401/HTTP0。
- rotation persist before-set失败：原token消费True已持久化，503；重启401，旧refresh只一次。
- rotation set-then-raises：新token实际已持久化False；重启只使用**不同的新token**，不会重发旧token；允许合法新token继续续期。
- legacy JSON缺字段：defaultFalse可首次refresh，观察到外部HTTP进入时存储True；成功新tokenFalse。兼容旧凭据并不假称旧未知调用可被追溯。
- None/2/object/unknown string marker：401 credential_unreadable、HTTP0。True/`"true"`/1/`"1"`：401 token_expired、HTTP0。
- 原real task六项create/update/complete×read gate、corrupt/denied user槽后重启app日历、one-use callback回归继续通过。

全量386包含R2–R4/Sol取消、DNS/TLS/no surviving worker/no laterdispatch、sharedclient独立性、retire租约、JSON/压缩/mount、canonical qualification、Stage A Fake路径。详细原scope矩阵仍按7f报告，各场景本8b执行全suite回归。GUI/native由另一独立验收者负责；本agent GUI/native为NOT_RUN。

## QA-B-02/P2：非JSON布尔值被当作消费标记False

- 8b `UserCredentials.refresh_consumed: bool=False`使用Pydantic默认coercion；产品生成JSONbool，vault损坏成字符串 `"false"`或integer0却被当作有效False。
- 独立步骤：真实API合成授权expires_in1→close→仅SecretBackend边界把存储marker改为 `"false"`/0→重启同profile→materials。预期损坏内部字段401 credential_unreadable/HTTP0；实际refresh已派发，MockTransport返回lost-response导致503。
- 证据：[strict-marker-counterexample.log](evidence/2026-10-11-stage-b-independent-offline-retest/strict-marker-counterexample.log)，[test_independent_refresh_faults.py](evidence/2026-10-11-stage-b-independent-offline-retest/harness/test_independent_refresh_faults.py)，测试 `test_nonboolean_false_marker_is_invalid_stored_state`。
- P2原因：未复现有效boolTrue被绕过；product始终写JSONbool，true-like值均拒绝，修改本地vault的人也能直接改False。是内部存储shape/fail-closed硬化缺口，不能捏造P0/P1付费漏洞。
- 已交执行者采纳strictbool修复。新字段只在本地凭据DTO，未增加公开API。后续严格字段须同时验证真正boolFalse和legacy缺字段可续期、其余类型均credential_unreadable。

## 阶段结论

未关闭P0=0、P1=0、P2=1（中间提交已执行范围）；原P1在8b关闭，新P2待新SHA复验。最终Stage B离线门未签发。真实OAuth/账号权限/材料/calendar/task/模型质量/R03/用量费用、OS Keychain、DMG、M3–M5、五日和双机全部 **NOT_RUN**。固定源码通过也不能推为完整真实Stage B/C或产品验收PASS。
