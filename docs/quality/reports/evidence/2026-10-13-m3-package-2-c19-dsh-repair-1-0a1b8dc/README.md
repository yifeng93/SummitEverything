# C19 候选统一返工 1/2 Developer evidence

固定产品源码 SHA：`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`。起点：`4010c54c36f197748f0e0f71c79f6a38c978af66`。分支：`codex/c19-dsh-sol-gate`。本证据目录只记录 Developer 自测，不是独立 QA 结论。

`commands.tsv` 记录命令与真实退出状态。`raw/` 保留两组初验 RED、固定 C19 holdout 和全量后端的最终日志、静态/Web 构建日志及 loopback smoke 脚本/输出。初验两份 22 项 expanded / corrected matrix 是字节相同副本；矩阵合并命令实际执行 107 项，按不同测试 ID 去掉该重复路径后为 85 项。

`loopback_smoke.py` 使用随机本机端口、临时合成工作库和 Fake provider，分别走完整、partial、zero 问答 SSE 及 conversation reopen。原始输出 `loopback-final.log` 为四项 PASS。该服务已在脚本 `finally` 中停止；进程核查未发现本轮 Uvicorn 残留。此验证不声称浏览器 DevTools 或真实 WebUI 通过。

受测源码 SHA 与后续文档整合 HEAD 分开：**源码验收目标始终为上述 `0a1b8dc...`**；之后只增加 DEV 报告、evidence 与状态入口文档。QA 应在独立 checkout 固定该源码 SHA，并在审阅前核对产品文件树未变。

真实 provider、飞书、凭据 / Keychain、真实材料、native / DMG、五日 / 双机、发布 NOT_RUN；runtime UNVERIFIED。源码树和本目录文件的 SHA256 manifest 随此目录提供。
