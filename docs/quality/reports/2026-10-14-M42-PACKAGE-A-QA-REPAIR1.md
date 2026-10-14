# M4.2 Package A 独立验收：修复轮 1

验收者：fresh custom QA。固定受测产品源码 SHA：419bb865b334389d1efd0f4a1a855cd0d5324d28。Checkout：/Users/yifengstudio/.codex/worktrees/m42-package-a-qa-repair1/SummitEverything。测试开始时 HEAD 为 detached、工作树 clean；所有产品检查均针对该 SHA。报告提交只新增本报告与 QA evidence index，不能作为受测源码 SHA。

这次结论只涉及 M4.2 Package A 修复轮 1。QA 没有修改应用源码、tracked tests、依赖、lockfile 或产品配置。Developer 的文档交接 commit be1924856488263585f9f6a5e68d95b7e73af28e 在另一 checkout 只读审阅；没有切换、合并或 cherry-pick 到受测 checkout。

## 独立结果

| 场景 | 结果 | 证据与边界 |
|---|---|---|
| M42-QA-001：已预留 Feishu read 计划中断后 GET | **PASS** | 独立合成 API harness：confirmed plan 执行 run、预留 2 次；另一个应用实例打开同库后首次 GET 200、状态 unknown、有合法 finished_at，重复 GET 仍 200/unknown/finished_at 有值；重放 read 请求 409；reservation 保持 2、run ID 保持，GET 前后 ledger 字节相同。p1-repair1-probe-final.log 3 passed；tracked test_feishu_real_gate.py 活跃 owner 与 restart 两个用例 2 passed。活跃 owner 在同一 run 下仍为 executing。没有真实 Feishu 请求。 |
| M42-QA-002：visitor 共享 planner | **PASS** | 最终 419 包的正确 guard/profile corrected-run 中，以规定的正文逐页批准后，UI 实际提交两条原始问题“访客离开时，前台应记录什么？”和“访客离场后要补充记录哪些信息？”。每条的 AX 回答及引用都包含完整断言“访客离开时，前台补记离开时间。”；正文没有自包含问句。独立 tracked 检索测试覆盖相同原问句、未知对象/未知 topic 不发给 answerer、缺字段仅给 evidence-supported partial、跨对象 comma clause 不进入证据。 |
| Native 文件多选 | **PASS** | corrected-run 中，alpha + beta 两项在显式导入前作为待导入出现，确认后各自显示已导入、inbox 增加；alpha + 0-byte 文件显示“文件未导入”操作提示且 inbox 计数不变；主动 Cancel 不显示警报且计数不变。 |
| Native 文件夹选择 / WK FileList | **PASS** | 原生目录面板选中 synthetic folder 后，WebKit 待导入列表同时显示 root 文件和 nested 文件；点击导入后两项分别成功并写入收件箱。隐藏文件 fixture 未进入待导入。目录 2000 项上限、不可读整批拒绝等另见 native unit tests 和 tracked full suite，不声称 UI 覆盖这些故障。 |
| Fake JournalAssist UI | **PASS** | corrected-run 实际生成可编辑模拟建议，取消一次；第二次采用建议后单独点击“确认并保存在本机”，UI 显示本机索引更新，重开同一隔离工作库后可见已保存 Markdown 正文。 |
| Real JournalAssist Runtime + MockHTTP | **PASS（API/集成测试）** | tracked test_real_model_approval_flow.py 2 passed。覆盖真实 ProviderRuntime 在 MockHTTP 边界运行、正文/output/config scope 绑定、正文或配置变化拒绝且不出站、取消不出站、确认只执行一次、timeout 后 unknown 不重发、usage ledger 异常时关闭 client。Real-mode packaged UI 本轮 **NOT_RUN**；没有访问真实 provider、Keychain 或真实账户。 |
| Shared planner 反例 | **PASS（自动测试）** | test_c19_topic_scope_normalization.py 41 passed，另有 test_qualified_retrieval.py 4 个定向用例通过。覆盖复合 budget + schedule 保留两 topic、不同对象/逗号 clause 不串证据、unknown object/topic fail-closed、保守的限定语和 partial 缺项。完整 513 项 guarded Python suite 也通过。 |
| 全套本地自动检查 | **PASS** | Guarded Python 513 passed；Web 12 个测试文件 / 65 tests passed；Native 5 tests passed；ruff、format、mypy、uv lock/build、API types、TS typecheck、lint、Web build、git diff --check 均 exit 0。保留 Starlette deprecation 与 2 条既有 React lint warnings。OpenAPI 生成未产生 tracked diff。 |
| 最终候选包身份和内容 | **PASS** | 独立读取 copied app build-info：source SHA 精确匹配、dirty=false、build ID 20261014T050331Z-788b29e2f3bb、frontend SHA 788b29e2f3bb8b95736179ed07af6fa0d02eea17b3e881f92a8d79f2e70cb2ec、dependencies SHA 2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f。156-path app manifest 的实际字节 SHA-256 是 9bb4d2c6e511e47812db8cca6e1af56d4dd248e1ca177a92525e1f7271c8c7f0；DMG SHA-256 是 2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a。只读挂载后的 app、独立临时 copy 均逐项匹配 manifest，hdiutil verify 与 strict codesign verify exit 0。 |
| Gatekeeper assessment | **观察到拒绝** | spctl --assess --type execute --verbose=2 exit 3 / rejected（ad-hoc signature）。未绕过 Gatekeeper、未清除 quarantine、未改安全设置。经 LaunchServices 启动的隔离 copy 在 corrected-run 可交互；这不替代正式签名 / 公证安装门。 |
| 失败项 retry / fault injection UI | **NOT_RUN** | 多文件部分成功后仅重试失败 operation 的真实 UI fault retry 未执行；不能由普通多选成功、API/前端反例或代码推为 PASS。 |
| Keychain 生命周期、真实模型/Feishu/Tasks、真实业务资料、账单/质量、用户安装/覆盖、公证发布、五日、双机及 M5 | **NOT_RUN** | 按本轮授权边界未触碰真实资料、密钥或远程服务。 |
| Runtime model 信息 | **UNVERIFIED** | UI / runtime 未提供可验证的本轮实际 model 元数据；不从配置推断。 |

### Scope 与安全前置的时序说明

正确的 packaged UI corrected-run 开始前，native PID 52780 与其 child backend PID 52782 的 offline guard 和 canonical profile root 均实际核验为匹配；backend 监听端口 18793 与 CUA WebView URL 相符。PID 到 copied candidate executable 路径的关联保存在 QA raw logs。此前某一更早的 UI 运行发生在 guard/profile checker 之前，该段不计入 corrected-run PASS，保持 **UNVERIFIED**。

上下文恢复后一次新的 cua.getApp 绑定意外拉起相同 copied bundle 的 PID 66827/66829。任何产品 UI 输入之前，安全 checker 发现两进程 guard=false 且 profile root 不匹配。通过 image path 确认是 QA 临时 copy 后，只对这两个 QA 自有进程发 SIGTERM；旧进程 PID 51339 的路径属于 M41 安装，未触碰。late launch 不进入 PASS 证据；Keychain 查询次数及默认 profile 回退都保持 **UNVERIFIED**。没有在此之后继续 CUA 操作。

### 缺陷及验收风险

本轮没有观察到新的产品缺陷，也没有把初验的两项 defect 降级为 partial PASS。P1/P2 的本轮目标均有独立修复轮 1 证据。QA focused harness 调试中曾出现两条错误预期：一条要求 GET 的 finished_at 跨两次 observation 固定不变；另一条要求 durable ledger 在 GET 后改成 unknown。API 契约是每次 status GET 返回有校验的 ephemeral unknown / observation timestamp，同时持久 ledger 继续 executing，reservation 与 run ID 不写。纠正后的 harness 检查 API status、ledger 原字节与 reservation/run，3 项通过。第一条失败的完整 raw 保留；第二条失败原输出曾被后续成功运行覆盖，因此只保留 tool-output 摘录并明确披露，不将其伪装成 raw。详见 probe-assertion-correction-history.txt。

QA 的“PASS”仅指表中实际执行且有证据的固定 SHA 场景；它不代表 M4.2、C25 或全产品最终门通过。Sol 负责最终门判定。跨平台/Intel 不在本机验证范围；本机是 arm64 macOS 27.0.1。

## 命令和证据

完整命令退出码账本见 evidence/2026-10-14-m42-package-a-qa-repair1/command-exit-ledger.md。本机原始 harness、输出、exit、隔离 app 过程和 CUA 观察记录位于 /Users/yifengstudio/.codex/worktrees/m42-package-a-qa-repair1/SummitEverything/.local/qa/m42-a-repair1/。其中：

- Guarded full Python output：full-guarded-pytest.log。
- Focused P1、Journal、planner 与 retrieval raw log 各有配对 .exit 文件。
- Corrected process precheck、image path 与 window-port association：native-backend-guard-profile-corrected-launch.log、corrected-process-image-paths.log、cua-window-port-match.log。
- UI observations 是对本会话 CUA AX tool outputs 的 QA 转录说明，不是截图或原始 AX 文件：ui-corrected-run-observations.txt。Late launch 经 sanitize 的 tool transcript 与两条初始错误预期见各自说明文件。
- 所有 local evidence 文件 hash 清单：evidence-sha256.txt（manifest SHA-256 0d19e759d319a93653018dacb1411633fa9b5390f892a50ae8fbb273d639f572；61 entries）。候选 app 原始 156 行 manifest 在 Developer evidence candidate-419bb86-app-SHA256SUMS.txt；本轮独立读取并验证 copied app 与只读挂载 app。

QA 报告源码父 commit 为固定受测 SHA；新增 QA 文档 commit 单独记录，不能当作受测产品源码 SHA。最终门仍由 Sol 判定。

