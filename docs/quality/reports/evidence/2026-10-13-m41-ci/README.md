# M4.1 远端离线 CI 证据

两个运行均观察为 completed / success：PR run 38363541676，push run 38363540856。原始 GitHub CLI metadata 和完整日志保留；GitHub 自动遮蔽的 token 仍保持遮蔽，本目录不含账户秘密。

运行记录的分支 head 为 f7ad5e46a18d256483d5d2b89f464b46a4e10793，产品树与固定 QA 源码 3f6eaa408a8860ff5a438be8a874a2c3904733e4 一致。PR checkout 使用 GitHub 的合成 merge ref，push checkout 使用分支提交；该自动构建不是用户交付 DMG，也不能把其身份误作本机固定候选。后续报告 / 交接提交只改文档。

实际 runner 为 macOS 14.8.9 arm64 / Python 3.14.7；499 后端、56 Web、3 XCTest、静态 / 类型 / 锁 / API types、App / DMG 重建及包内 backend smoke 都通过。无实际 GUI、真实账户或系统 Keychain 测试。macOS 14 自动检查不代替完整现场安装或窗口验收，macOS 13 / Intel 未测。

SHA256SUMS 相对仓库根；从仓库根执行 shasum -a 256 -c docs/quality/reports/evidence/2026-10-13-m41-ci/SHA256SUMS。
