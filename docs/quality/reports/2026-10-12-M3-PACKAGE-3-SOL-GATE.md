# M3 包 3 Sol 门判断

日期：2026-10-12。包 3 离线集成 **PASS**；包 2 的 C19 P1 仍 **FAIL**，M3 正式验收与重要里程碑合并尚未通过。

## 固定版本及独立核证

- 产品源码：`ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`。
- 全新 QA 的固定交接 HEAD：`7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`；与产品源码之间仅文档变更。
- [repair 1 独立 QA](2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md) 的报告提交：`a251c6cb3bad8b99fdac8abb5b9f16dc7090092b`，已导入功能分支。
- Sol 实际读取报告、故障日志和测试结果，逐项核对 [53 项证据清单](evidence/2026-10-12-m3-package-3-repair-1-qa-7fd8a53/SHA256SUMS)，全部匹配。清单 SHA-256：`bd2b23e9609f264ec143490fc78425cd0e31825a96e3638e6104be9723b97898`。
- QA 报告提交对受测 HEAD 的产品、测试、脚本、配置和依赖树 diff 为 0；QA 工作树 clean。服务停止记录显示四个测试端口均无 LISTEN。
- [首次 QA FAIL](2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md) 和 65 项原证据保留，初验清单 SHA-256 为 `3077fdcc56d2bb35c3e0f207dfc05e1c43cf79890af6ac4953764180a99ce856`，Sol 也已逐项核对。包 3 使用一次自动返工，计 repair 1/2；未重置包 2 返工额度。

## 门判断

| 范围 | 判断 | 依据与限度 |
|---|---|---|
| C22 整理接续与未知结果 | PASS，离线范围 | 两 profile 可见同库待审稿；活 owner 不误判 unknown，死 owner 不自动重发；checkpoint 仅恢复本地待审内容，取消与迟到结果、并发同意图和版本 CAS 回归通过。 |
| C22 初验 lease 异常清理 | PASS，修复已关闭 | 独立注入首次 running receipt 写失败和 jobs 目录创建失败，保留异常 traceback 时 lease 已删除且不活跃，receipt/item 保持 confirmed/pending，provider 为 0。同意图重试仅产生一次 Fake 副作用。初验的 FAIL 不改写。 |
| C23 月归档与故障恢复 | PASS，离线范围 | 摘要写失败、同副本、冲突/损坏/非法月及意外副本回归，进度 proof 已归档后的只读核实及 Fake Feishu 重放通过；原件、完整稿件和确认内容保留。 |
| C21 本地状态边界 | PASS，本机两 profile 范围 | 初验隔离证据加本轮真实浏览器短复演；诊断轮转与 allowlist 回归。此结论不扩展到真实双机或同步并发。 |
| C13/C14/C20 关联回归 | PASS，已测离线范围 | 本轮 440 全套、99 核心及 37 资格/变更检查，结合未变模块的固定初验证据；没有把关联回归冒充整体 M3 通过。 |
| 包 2 C19 对象与证据范围 | FAIL，已知 P1 | 初验再次复现无资料比较引用无关预算。本轮未改 retrieval/planner/query，不能关闭该缺陷；用户此前暂停该修复并明确先执行包 3。 |
| M3 正式验收/合并 | 未通过 | 包 1、包 3 离线集成 PASS，包 2 FAIL。重要里程碑正式验收与合并仍需用户批准，当前不具备请求通过的条件。 |
| 真实服务、材料、凭据/Keychain、native/DMG、五日、双机、发布 | NOT_RUN | 本轮仅合成内容与 Fake providers；没有消费真实操作授权或重置 smoke 次数。 |
| DevTools console/network、PNG 文件 | NOT_RUN | 实际浏览器操作留有 AX/API 证据；没有对应导出证据。 |
| runtime 元数据 | UNVERIFIED | 不从配置推断实际运行模型或推理参数。 |

## 实际检查及保留边界

独立后端 440 passed；核心 99、资格/变更 37、Web 56 passed，静态/类型/lock/build/OpenAPI 等适用检查均 exit 0。Fresh checkout 首次未安装 Web 依赖导致 439 passed / 1 runner 环境失败，日志未删；按 README 执行 npm ci 后重跑全套 exit 0。保留既有 1 条 Starlette 弃用和 2 条 React lint warning。Sol 核对原始结果，不重复 Developer/QA 常规检查。

120 个 Fake 流程跨四个业务月，item/job 各 120、transactions 366、月摘要 13；重放后 provider 仍为 120，原件/完整稿各 120，完成流程没有 active item/job、checkpoint 或 lease。unknown item/job 各 1，另有 legacy undated item 1 保留 active，不伪造完成月份。4 条合成 Feishu receipt 只证明归档读取，实际 Fake 导入—重启重放由独立集成测试证明。没有文件系统性能基准或跨机并发写结论；本机 flock 不能作为分布式同步锁。

## 接续

包 3 已完成实现、一次返工、全新独立 QA 和 Sol 核证，继续保留在 `codex/m3-integrated-packages`，没有合并 main。后续若恢复包 2 C19 修复，需要用户重新授权已暂停的追加返工；其通过后再提出 M3 正式验收与重要里程碑合并请求。Stage C、M4/M5 和真实门按原计划另行处理。
