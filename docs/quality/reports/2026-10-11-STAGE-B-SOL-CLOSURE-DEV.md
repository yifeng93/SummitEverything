# Stage B Sol 收口 DEV（2026-10-11）

状态：DEV 修复与独立代码复核完成，源码候选已固定 `7f3119a511fda6f3d2771af4cf09fd9a9026edb7`；正式 QA pending，main 未合并。本报告不是 QA。

起点 `0a1db5d72e6ac11184d28e65dea3ba008762ba43`，源码前候选 `7dc7114595704f34ba386c96324dffa77d529ba4`，两者仅文档差异。采纳 DeepSeek R1–R4 的协议映射、统一 vault、身份隔离、OAuth 代次与刷新防重发、日历截断、任务写门、检索资格和业务服务门。历史报告和证据不改写。

| 新发现 | 修复与证据 |
|---|---|
| DNS 暂停超 deadline 返回后仍发请求 | 请求独立 async resolver/pool，取消覆盖 DNS；非 daemon runner 返回前 join。before 与 after integration 实测，远端未收到 HTTP、Future cancelled、workers=0 |
| 超时取消共享池误伤另一合法请求 | 每请求独立连接池；同 client A trickle 超时、B 正常成功 |
| retire 检查与租约登记之间关闭 client | 检查/登记在同生命周期锁中；调度暂停反例保留真实租约实现，最后操作结束后 client 只关一次 |
| TLS 握手未交接时 TCP 所有权丢失 | backend 从 TCP 建立即持有 stream，退出关闭；真实握手暂停测试观察 peer EOF |
| pycares bytes IP 解析成字符串 repr | ASCII 解码、IP 验证；真实 pycares numeric result → loopback，禁止系统 DNS fallback |
| HTTPX mounts 绕过安全 transport | 检查 URL 实际选中 transport；不安全 mount 发送前拒绝 |
| 只检查 user/text 字节，没有 JSON envelope/转义 | HTTPX 相同 wire 编码检查 1MB；超限 LLM/rerank 请求次数0 |
| 解压先于限额导致无界内存 | Accept-Encoding identity；其他编码在读正文前拒绝；独立复核 gzip 16MiB 反例峰值增量由47.7MB降至约0.30MB |
| 应用日历依赖用户OAuth、真实OAuth误走Fake helper | 日历按API身份判定；Real显示官方浏览器链接+本机状态刷新，Fake窄回调保持。native只允许用户点击官方HTTPS授权链接离开WebUI；真实OAuth/系统外部页面未运行 |
| Real 任务区仍宣称Fake且开放写控件 | 从真实 status mode 共享到任务面板；未知/Real 禁止创建/编辑/完成/执行远端任务，保留本地项目进度；真实原生 UI + 组件反例 |

完整 guard 检查：后端383 passed；ruff/format/mypy(36)/lock/uv build/API类型幂等/Web45/typecheck/lint/build/Swift/diff均exit0。最终完整检查在全部产品修改后执行，日志已归档于 evidence/checks。保留既有Starlette warning1与React lint warning3。无测试期望删除或降门。

独立只读 reviewer 对新增传输/边界复核62 passed；这属于DEV代码审查，不是固定SHA QA。R4组合测试原“服务端 write 成功次数立即不变”存在TCP缓冲观测竞态，保留失败日志并增加服务端FIN/reset观察，随后断言字节收敛和worker=0；不改变取消安全标准。

DEV UI：API18893/Web15173，隔离 `.local/sol-closure/profile` 与合成 workspace。IAB创建库/设置/Real配置保存与Keychain不可用禁用状态，console warning/error=[]。原生开发壳同端口/独立run_id，目录选择合成路径、Real task写控件禁用、设置不可用与最后窗口退出清理（无端口残留）。首次测试bundle PATH遗漏uv/npm，显示启动失败；补齐测试wrapper PATH后正常，失败截图保留；不是修改产品代码。截图/AX见 evidence/ui。完整浏览器网络/磁盘断言交独立QA补足；本DEV不声称HAR或安装包验收。

历史 manifests R1/R2/R3/R4 22/22、22/22、38/38、34/34重算匹配，历史FAIL保持。R4未提交起点已归档到 `/Users/yifengstudio/.codex/archives/summit-stage-b-20261011/deepseek-r4-dirty-source.tar.gz` 与二进制diff。

真实 Feishu/模型调用仍全部0/1；未录入任何凭据，未访问用户身份、真实材料、日历/task或OS Keychain。真实写/业务模型/未授权读取保持服务端禁用。R03、OS、scope、user-info、DMG、M3–M5、五日/双机NOT_RUN。独立QA必须精确SHA、独立checkout并留自己的报告；PASS后才整合。

证据纠正：初次 reviewer-boundaries 日志的 rerank 输入实际 wire 长度900114，未达到1MB，不能作为有效超限失败反例。保留该原始日志；改用350000组转义字符（wire1050114），从归档R4源码重放得到LLM/rerank两项FAIL，见 before/full-wire-r4-corrected-input.log。overlay仅加入新测试导入所需transport模块，受测旧model/boundary文件保持R4原件；当前两项PASS并断言HTTP调用0。

归档格式说明：首次git staged diff --check观察到原始失败/lint日志中的尾随空白；未改写日志，避免破坏历史manifest。新增gitattributes仅豁免 evidence 下.log文件的行尾/文件尾空白；源码、测试、契约和常规文档仍执行原有空白检查。此前工作树diff check未覆盖未跟踪日志，不能据此声称该批原始日志无尾随空白。
