# Stage B / C 当前工作计划

2026-10-11。产品 v1 MUST 和全 v1 计划不缩减；本次只收口 Stage B 离线源码，不等于可安装产品或真实账户验收。

当前：1–3已完成；受测源码 `576895f6983ca41cacbbad45a9075b97b9986189`。4–5整合、核验与归档清理进行中；6不在本轮执行。

1. 采纳并修复 DEV：协议矩阵、统一凭据槽、应用身份优先、授权代次、刷新单次消费、配置生命周期、数据/写门、模型与检索资格、请求独立取消和大小边界。
2. 完整 DEV 检查与合成 UI / 原生证据，固定新源码 SHA；历史 FAIL 与 R1–R4 manifest 保持原样。
3. 独立上下文在源码库外 checkout 精确 SHA，离线正式 QA（真实 route/service/存储/协调器/租约；只替代 SecretBackend 与外部 HTTP）。覆盖 SB-01–13、R2–R4、Sol 新反例、Stage A 回归和实际 UI；缺陷修复后换新 SHA 复验。
4. QA PASS 后 PR / merge（保留受测提交），核对 main 源码树和 evidence manifest，合并后冒烟。
5. 为闲置 worktree/分支制作可恢复归档，确认无活跃使用后清理；main 与 origin/main 干净一致。历史报告和真实门保留。
6. C：使用原授权范围，不重新申请或扩大；当前不执行。账号 scope、callback 注册、user-info、transcript content-type、全天日期规范化、模型维度/质量与 OS Keychain 仍需各自后续证据。task 写因无独立结果证明继续 disabled。

真实次数：code exchange/refresh/chat/embedding/rerank 全部 0/1。不录入任何真实凭据；不访问真实身份、材料、日历、task；不执行真实任务写入。CNY 5 是旧提示词建议上限，不是用户预算。M3–M5、DMG、五日、双机在全 v1 后续门中。
