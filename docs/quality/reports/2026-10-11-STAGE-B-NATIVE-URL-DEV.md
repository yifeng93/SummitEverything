# 原生 readiness 根 URL 修复 DEV

独立实际 UI 对 fd204238 发现新 P1：API run_id 匹配、Web 200，但 URLSession 把无路径根URL规范化为带 / 的URL；精确 equality 因此失败，30秒后出现未就绪 alert。根把固定本机根URL显式写为 /，保留响应精确匹配、防晚到结果与双服务就绪门。

新固定源码：`576895f6983ca41cacbbad45a9075b97b9986189`；相对fd产品只改native App.swift一行。真实loopback Swift URLSession探针按产品URL模板实测 before exit1/equal=false→after exit0/equal=true；Swift build exit0。探针、原始日志与manifest在[evidence](evidence/2026-10-11-stage-b-native-url-dev/manifest.json)。首次尝试原生QA服务已关闭，探针连接失败，保留setup-already-closed.log；正式before/after改为探针自己持有并清理的本机HTTPServer，不借用QA服务。

此前388/Web45适用backend/web与fd相同的树，不能替代新SHA实际原生复验。Luna High正在新独立checkout验证冷启动/延迟npm/退出，QA pending；没有合并。真实Feishu/模型/Keychain仍未访问，账本0/1、写门disabled。
