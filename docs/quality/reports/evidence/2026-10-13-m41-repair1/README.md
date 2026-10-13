# M4.1 修复轮 1 开发证据

本证据对应产品源码 SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4`。修复目标是 macOS WKWebView 的文件选择导入面板。候选来自该 clean SHA 重建；`.app` 和 DMG 二进制保存在被忽略的 `.local/dev/m41/repair-1/artifacts/`，身份见上级 DEV 报告。

`logs/` 保留本轮命令原始输出与 exit 文件，包括早期临时 harness 的错误尝试；`native-startup.log`、`native-startup-rerun.log`、`manifest-tamper.log` 是失败/无效尝试，未覆盖。成功复验分别在 `native-startup-rerun2.log` 与 `manifest-tamper-rerun.log`。所有合成 profile、复制 bundle 与临时 server 均位于 macOS `DARWIN_USER_TEMP_DIR` 下；测试未读取或修改默认 Internal profile、旧 App、真实凭据或材料。

`harness/` 是本轮隔离启动、前端资源篡改、延迟 readiness 和缺失 backend 的合成 harness。开始时 CUA 返回 Mac 锁屏；该次阻塞保留在 `ui-blocker.txt`。用户解锁后，开发者绑定原先已通过显式测试 profile 启动的 App，实际验证了 NSOpenPanel 打开、取消、TXT/MD 选择、待整理状态、源字节 SHA、Fake 整理/批准、索引和引用查询。详细原生 UI 观察在 `logs/native-ui-observations.txt`。这属于开发者自测，必须由 fresh QA 独立复验；不能以单元测试或 readiness 代替 QA。

检查证据文件完整性：

```sh
shasum -a 256 -c docs/quality/reports/evidence/2026-10-13-m41-repair1/SHA256SUMS
```
