M4.1 将开发环境依赖的原生壳改为自包含的内部 macOS App：内置 Python/FastAPI 和每次强制重建的 React 静态前端，生成可核对源码、前端和依赖身份的 App/DMG。原生壳按实例管理服务、校验 readiness、限制可信 WebView 与文件面板；退出、最后窗口关闭及父进程中断均清理自有服务。

固定产品源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 已经全新独立 QA 和 Sol 证据核验，适用离线技术门 PASS。实际原生 TXT/MD 选择、取消、原字节保存、明确批准、索引/引用问答及重启恢复通过；499 后端、56 Web、3 Swift XCTest、16 定向 API/release/SSE 及静态/类型/锁/构建通过。初验文件面板 P1 经一次修复关闭，历史 FAIL 和所有 raw evidence 保留。当前 PR 后续提交仅文档/证据，产品树与固定受测 SHA 一致。

内部候选仅实测 arm64 macOS 27.0.1，ad-hoc 签名；系统应用评估返回拒绝，Developer ID、公证、Gatekeeper 接受、真实用户安装、真实模型/飞书/Keychain/业务材料、M4.2、五日、双机和发布仍 NOT_RUN。内部 DMG 留在本机隔离产物目录，未发布二进制或覆盖旧应用。

验收证据：`docs/quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md`、`2026-10-13-M41-SOL-GATE.md`；安装和下一步：`docs/handoff/M41-INTERNAL-INSTALL.md`。本 PR 保持 draft，等待用户批准 M4.1 离线正式收口和合并 main；该批准不扩展真实操作范围。

远端 CI 补充：PR run 38363541676 与 push run 38363540856 均 success，记录 head 为 f7ad5e46a18d256483d5d2b89f464b46a4e10793，产品树与受测 3f6eaa4 一致。macOS 14.8.9 arm64 / Python 3.14.7 自动测试及 App/DMG 构建、backend smoke 通过。最终 52d0f34 仅保存这两次运行原始证据和交付位置，未改变产品；PR 同步自动触发最终文档 HEAD 的第三次 CI（run 38364423576），已完成且 success，受检 HEAD 为 52d0f3419bf10ad9cb719efed0580256bd059022；该次不修改产品或本机候选。
