# 原生开发壳双服务就绪修复 DEV（2026-10-11）

旧8b独立UI复验发现QA-UI-B-01/P1：测试wrapper仅延迟npm启动5秒，API先ready时原生立即加载未启动Web，之后API/Web都ready仍白屏。原8bFAIL、截图和wrapper/状态证据原样保留。

修复原生readiness：API须ready且run_id匹配，再检查本机WebGET200并且响应URL等于配置webURL；同一时间只发一组检查，失败继续轮询，30秒期限仍给readiness错误；回主线程核验timer有效后才加载Web。无任意网络重试、权限扩大或旧服务接管。Swift build0。新增严格bool标记修复同批固定，既有API/凭据协议不变。

全部产品修改后后端388/Web45、ruff/format/mypy36/lock/package无隔离guard构建/API/type/lint/webbuild/Swift/diff全0（见相邻evidence）。当前仅DEV：新固定SHA须独立上下文/checkout重演正常与延迟Web启动、原生身份/目录/退出，并做后端完整与新反例复验，未满足不得合并。真实调用0/1、OS Keychain/DMG/真实质量与全v1后续门NOT_RUN保持。
