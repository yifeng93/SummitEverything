# M4.2 Package A repair1 QA evidence archive

本目录是 QA docs-only 报告 commit `e3983569dbbb7093107c63fca1986e29cfcfd867` 的报告与 raw evidence 的可提交副本；受测产品源码 SHA 固定为 `419bb865b334389d1efd0f4a1a855cd0d5324d28`。Developer docs handoff `be1924856488263585f9f6a5e68d95b7e73af28e` 与 QA 报告提交不属于受测产品 SHA。

`original-qa/` 下含 manifest 所列 61 个文件的逐字节副本以及原清单 `evidence-sha256.txt`。原始清单中 QA-root 相对路径以 `.local/qa/m42-a-repair1/` 开头；归档时只移除此固定前缀，文件名和剩余目录结构保留在 `original-qa/` 下。原清单字节未改，其 SHA-256 为 `0d19e759d319a93653018dacb1411633fa9b5390f892a50ae8fbb273d639f572`。新归档清单 `SHA256SUMS.txt` 使用相对此 evidence 包根目录的路径，对本 README、逐字节副本、原清单及 QA command ledger 独立校验。

固定产品测试结果与门范围见 [QA 报告](../../2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) 和 [Sol gate](../../2026-10-14-M42-PACKAGE-A-SOL-GATE.md)；逐命令索引是从 QA docs commit 导入的原始 `command-exit-ledger.md`，未改写。QA 报告/source command index 的 Git 字节与源 commit 一致。

## 证据限制和启动时序

- QA 报告保留原始限定：较早一段 UI 执行未在启动前核验 guard/profile，不能计入 Corrected-run PASS，Keychain 查询次数和 profile 回退 **UNVERIFIED**。
- 正确前置检查后的 packaged UI run 中，native/backend guard 和隔离 profile 匹配；late CUA resume 误启动的 copied app/backend 在任何 UI 输入前被查到 guard=false/profile 不匹配，QA 只停止了这两个 QA 自有 PID。旧 M41 PID 未触碰。不得声称本轮全程零 Keychain 查询或全程隔离。
- P1 初始一条错误 assertion 的完整 raw 保留；第二条临时 assertion 失败的 raw 被后续成功运行覆盖。原报告仅保留 tool-output 摘录并披露丢失，本归档不补造输出。
- CUA UI 内容是 QA 的观察转录，不是原始 AX dump 或 screenshot。不得将转录称为截图。
- 本次 archive manifest 的 61 项全部从源清单逐个复核，源/副本 SHA 一致；源 QA checkout 仅读取，未删除、改写或移动。

## Sol 的适用门判断

适用工作包 A 固定 SHA 的离线技术场景 **PASS**，不代表全 M4.2、C25、Stage C 或整个产品最终 PASS。正式离线收口/合并尚待用户批准。所有真实 provider、Feishu/task、真实材料、Keychain、用户安装/公证、五日/双机、M5/release 仍按报告为 **NOT_RUN**；runtime model metadata **UNVERIFIED**。
