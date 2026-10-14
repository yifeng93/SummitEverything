# M4.2 Package A Sol gate

## 固定范围与结论

Sol 对固定产品源码 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28` 的独立 fresh QA 证据完成审阅。本轮 M4.2 Package A **适用离线技术场景 PASS**，修复轮数 1/2；QA 未发现新的产品缺陷。此判断只覆盖报告中实际执行的离线/API/Mock/packaged UI 场景，不是 M4.2 全范围、C25、Stage C 或整款产品最终 PASS。

固定受测产品树以 `419bb865b334389d1efd0f4a1a855cd0d5324d28` 为准。QA checkout 在受测时 detached、clean；Sol 已核 `src/`、`web/`、native、tracked tests、依赖/lock 等产品树与固定 SHA 一致。Developer handoff docs commit `be1924856488263585f9f6a5e68d95b7e73af28e` 与 QA evidence commit `e3983569dbbb7093107c63fca1986e29cfcfd867` 只记录文档/证据，**不能作为受测产品 SHA**。本 worktree 的合并 QA 文档提交也不移动 fixed-source 身份。QA 报告：[固定 SHA 独立验收](2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)；QA 原始 evidence 副本与独立 manifest：[evidence README](evidence/2026-10-14-m42-package-a-qa-repair1/README.md)。初始 QA FAIL 报告和原始字节副本保持原样。

| 验收范围 | Sol 判定 | 证据范围 |
|---|---|---|
| M42-QA-001 重启后的预留计划 GET | PASS | 终态 unknown GET 200、合法 observation `finished_at`；reservation/run/ledger 持久语义核对；活 owner 仍 executing；read 重放 409；没有真实 Feishu 请求 |
| M42-QA-002 访客共享 planner | PASS | 最终候选的 corrected-run 使用无自包含问句的批准正文，实际提交两条初始 QA 原问句，AX 答案与引用包含完整断言“访客离开时，前台补记离开时间。”；自动反例验证未知 topic/object 与跨对象边界 |
| 文件/目录导入 Native UI | PASS | corrected-run 多文件、有效+零字节混合的明确拒绝提示、主动取消无提示、合成目录的 root/nested TXT/MD FileList 和收件箱导入；隐藏项未进入待导入 |
| Fake JournalAssist UI | PASS | 建议取消、再次建议采用到编辑区、单独保存、同一隔离工作库重开可见已保存内容 |
| Real JournalAssist Runtime + MockHTTP | PASS（仅 API/集成） | tracked Runtime/MockHTTP 验证配置与正文 scope、拒绝外发、取消、单次执行、timeout unknown 不重发、usage 异常关闭 client；Real-mode packaged UI NOT_RUN |
| shared planner C19 反例及自动检查 | PASS | C19 topic 41 与检索 4 个定向用例；Python 513、Web 65、Swift 5；lint/type/static/schema/lock/build exits 0，2 条既有 React lint warnings 保留 |
| 最终候选包身份 | PASS（包校验） | source SHA 匹配、dirty=false；156-file App manifest SHA `9bb4d2c6e511e47812db8cca6e1af56d4dd248e1ca177a92525e1f7271c8c7f0`；DMG SHA `2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`；复制/只读挂载 hash、codesign strict 和 `hdiutil verify` exit 0 |
| Gatekeeper assessment | 观察到拒绝 | `spctl --assess --type execute --verbose=2` exit 3 / ad-hoc rejected；没有绕过安全设置。Corrected-run LaunchServices 可交互不等于正式签名、公证或用户安装 |
| M4.2 远端离线 CI | NOT_RUN | M4.2 未 push、未执行远端 CI；PROGRESS 所列两次 success 仅为 M4.1 历史 |

## 证据限定

Corrected packaged UI run 开始前，native/backend guard 与 canonical profile root 均实际匹配。更早的一段 UI 运行未在启动前核验，保持 **UNVERIFIED**。上下文恢复后的 late CUA `getApp` 误启动 copied bundle，在任何 UI 输入前 checker 观察到 guard=false/profile 不匹配；QA 只停止了两个对应 QA 自有进程，旧 M41 PID 51339 未触碰。早期与 late 启动的 Keychain 查询次数、默认 profile 回退均 **UNVERIFIED**，不可表述为本轮零 Keychain 查询或全程隔离。

P1 一个错误 assertion 的完整 raw 留存；另一个临时 assertion 失败输出被之后成功运行覆盖，QA 只留 tool-output 摘录并显式披露。QA CUA UI 为观察转录，没有保存 AX raw dump 或截图。详情见原样 [QA 报告](2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md) 与 evidence README，不推断缺失 raw。

以下项目仍 **NOT_RUN**：多文件部分成功后的失败项原 operation ID 真实 UI retry；Real JournalAssist packaged UI；真实 provider/Feishu/OAuth/tasks、真实材料、账单与答案质量、真实 Keychain 生命周期、正式用户安装/覆盖、公证与发布、五日/双机和 M5。Runtime model metadata **UNVERIFIED**。工作包 B 只能在用户指定确切资料、动作和授权后开始；本次未读取四份真实业务 Markdown，未主动进行真实 profile 或 Keychain 验收；误启动期间是否访问及影响仍 **UNVERIFIED**。

## 当前决议和下一步授权边界

当前用户尚未批准 M4.2 Package A 重要离线正式收口/合并，因此此分支不创建 PR、不 push、不 merge，main 基线保持原样。Sol 可在用户批准后再完成该重要里程碑的整合。

后续工作包 B 先等待用户逐一指定四份 Markdown 的**完整路径**，并单独明确授权只读事实核对/grillme；读取不等于批准、入库或对外发送。只有四份材料整体得到用户明确批准后，才可初始化正式材料工作库。

模型选择仍待用户确认。DeepSeek Flash 与 Qwen 3.7 embedding/rerank 只是候选；实际模型动作前要由用户选定模型、实际材料/问题、请求次数上限与费用上限；先核对既有有限 smoke 次数累计，不因新 profile/workspace 清零；执行当日再次核实官方单价、usage 和费用范围。API key 只可通过应用 Settings 本机安全密钥入口录入，绝不在聊天中提供。真实 Keychain 生命周期需另行明确授权新的命名空间；不得迁移或读取旧钥匙串项。

Feishu 只读准备必须先由用户确认搜索词、选中结果、日期区间和时区，以及只查看任务第一页的范围；真实任务写仍保持 disabled，任何未来动作都需单独批准。用户尚需完成产品规定的 12 步并明确批准五个实际工作日验收之后，才能开始该现场阶段。

这些是下一步授权边界说明，不代表当前已获相关材料、模型、Keychain、Feishu、费用或正式收口授权。本次未读取四份真实业务 Markdown；未主动进行真实 profile 或 Keychain 验收，误启动期间是否访问及影响仍 **UNVERIFIED**。
