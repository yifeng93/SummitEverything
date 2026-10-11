# Stage B / C 当前检查单

- [x] B1.1–1.3 协议/契约与已有非秘密用户配置；账号侧真实行为未测。
- [x] B2.1–2.2 设置与 fail-closed 统一 vault；合成拒绝/损坏/重启回归。OS Keychain NOT_RUN。
- [x] B2.3 候选浏览器 / 原生开发壳 DEV；合成安全故障界面，不访问真实 Keychain。
- [x] B3.1–3.2 OAuth/读取 adapter 离线贯通；应用与用户身份按操作区分。
- [ ] B3.3 真实 task 写保持 disabled；缺丢失写结果独立证明，不能以禁用标成真实通过。
- [x] B4.1–4.3 模型/检索离线实现、取消/资格/大小/错误与资源生命周期。
- [x] B5.1 完整 DEV 检查：后端388/Web45及静态/类型/锁/构建。
- [x] B5.2 浏览器/原生 DEV 证据；安装包及 OS Keychain 仍 NOT_RUN。
- [x] B5.3 独立 DEV 代码复核并修复发现；不替代正式 QA。
- [x] B5.4 固定精确源码 SHA `576895f6983ca41cacbbad45a9075b97b9986189`，干净候选。
- [ ] B6.1 独立 checkout 固定 SHA 离线 QA。
- [ ] B6.2 QA-B-01、严格标记P2和原生startup P1修复固定fd204238，fd独立原生URL比较P1已修复，新源码576895f复验中。
- [ ] B6.3 PR/main/合并后树与 manifest 核验、闲置工作区归档清理。
- [ ] C0 既有有限 smoke（仍 0/1；本轮不执行）。
- [ ] C1/C2/C3 真实数据/模型质量/task写各自授权与验收门。
- [ ] C4 后续代码修复重新固定 SHA 并独立 QA。

当前权威状态见 README、PROGRESS 与 LATEST-IMPLEMENTATION；R1–R4 为历史 DEV。Stage B 离线源码门与真实接入/OS/交付门分别判断。
