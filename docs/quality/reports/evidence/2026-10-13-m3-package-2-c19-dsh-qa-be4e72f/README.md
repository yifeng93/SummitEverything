# C19 DSH 固定 SHA 独立验收证据

- 固定产品源码 SHA：`be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`
- QA 执行 checkout：独立 worktree；测试开始时 HEAD 等于固定 SHA。测试过程中未移动 HEAD。
- 原始命令输出与退出码：`raw-logs/`
- 只读黑盒 harness：`harness/`（源工作区中的运行副本位于 `.local/qa/c19-dsh-be4e72f/harness/`）
- 实际 UI/API 观测：`ui-observations.md`，服务日志在 `raw-logs/run-dev-ui.log`
- 临时隔离 UI 工作库：`ui-workspace/`，仅合成内容。
- 测试产物中的应用源码、tracked tests、依赖定义、锁文件均未修改。API 类型检查首次使用项目命令时输出目标为 tracked 文件，但随后确认无字节变化；另独立导出到 `.local` 并比较，通过。

哈希清单：`SHA256SUMS`；逐项校验命令见报告。
