# QA-B-01 重启刷新防重发 DEV修复（2026-10-11）

独立QA固定7f3119a发现P1；旧FAIL保留。本次为实现者修复与DEV，不替代新SHA独立QA；未合并。

真实API→service/coordinator/vault→合成HTTP反例：未知refresh后同进程不重发、重启却发送第二次。新增测试先2FAIL/1PASS（重启与保存失败零请求），修后定向49PASS。UserCredentials增加本地refresh_consumed（旧JSON缺字段默认false）；同vault槽在HTTP前保存true。失败/中断/重启继续拒绝旧token；保存标记失败不发送HTTP；合法新token返回后保存false。授权代次、共享锁与logout门仍保留；不修改官方token DTO或声称身份验证。

最后产品修改后完整检查：后端386/Web45；ruff/format/mypy36/lock/package/API/type/lint/webbuild/Swift/diff均exit0。首次ruff有复制harness残留unused uuid import，已修复，原失败日志保留。普通uv build的隔离backend缺aiodns导致sitecustomize未加载，只有构建exit0，不作为guard覆盖证据；另在本venv安装hatchling（lock未修改）后uv build --no-build-isolation在guard下通过，日志同时保留。源代码运行与测试guard负控制另由独立QA验证。

已有真实exchange/refresh/chat/embedding/rerank仍0/1；无真实凭据、OS Keychain、身份/材料/日历/task访问或任务写入。R03、DMG、五日、双机和M3–M5仍NOT_RUN。新源码SHA提交后交独立checkout复验，只有PASS才整合。
