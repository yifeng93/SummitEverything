# Fresh QA 修复轮 1 证据

固定产品 SHA `d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`。本目录按字节复制 QA 原报告、状态、harness、原始日志、manifest与代表截图；[SHA-256 清单](manifest.json)覆盖45份复制文件（本说明为Sol新增，未包含在raw清单）。完整视口图片仍留原QA工作树，合成workspace/profile/db未提交。

[原始QA报告](REPORT.md)、[退出码](check-status.json)、[最终SHA/clean](final-check.json)、[Sol最终门判断](../../2026-10-16-FRONTEND-USABILITY-SOL-FINAL.md)。脚本保留原QA路径，复验时需要在隔离checkout中适配根路径/端口，不使用真实材料或服务。默认E2E首次artifact ENOENT失败与成功重跑日志均保留，根因未确认。
