# M3 包 2 repair 1 QA 证据

受测源码 SHA：`0df323efc26e388d62f234e0471f853b2b54be4d`。QA checkout 文档提交前 HEAD：`d38f546cac8fd923539bea6a8ef9db925e5d959c`；两者产品树相同。本目录是脱敏副本，`sha256-manifest.txt` 的所有路径相对仓库根目录，manifest 不含自身。

`harness/` 包含本轮独立黑盒脚本、合成结果、MockTransport 请求体和输入 fixture；`raw-logs/` 保存各命令实际 stdout/stderr 的脱敏副本，配套 `.exit` 文件记录实际进程退出码。失败的 harness 初试和纠正运行均保留。交互矩阵摘要与 DevTools 限制见 [browser-ax-observations.md](browser-ax-observations.md)。

全部数据仅为本地 QA 合成数据；服务限制 loopback。没有调用真实模型、飞书、凭据、用户材料、Keychain、安装或 DMG，也没有消费 smoke 额度。
