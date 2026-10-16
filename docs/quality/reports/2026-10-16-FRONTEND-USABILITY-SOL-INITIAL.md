# 今日与审批可用性：Sol 初验门判断

日期：2026-10-16。受测产品 SHA：`0957df2b871970d626fb2745048a6e79bad4defb`。文档/PR tip：`4b1dc046f719169584b079261eebe91183eea2e2`，与受测产品的实现、测试、依赖树一致。

## 结论：FAIL（质量门）

独立 QA 所执行的前端与交互行为场景 PASS；本轮整体门未通过。`ApprovalView.tsx` 新增两处 `oxlint-disable-next-line react/set-state-in-effect`，绕过了本轮新增实现的检查信号。开发报告只列“新增 warning 已消除”，没有披露禁用。已批准计划明确禁止降低守卫，故 Sol 要求移除禁用并保持行为；不能以另一处禁用、修改 lint 规则或删测试替代。

进入自动修复第 1/2 轮：Developer 串行修复、提交新完整产品 SHA；然后全新的独立 QA 对新 SHA 复验。初验证据保留，不将旧 SHA 的 PASS 自动继承。

## 已核实证据

- QA 开始与结束 HEAD 精确为 `0957df2`，tracked 工作区干净，没有改实现或已有 tracked tests。
- Web 单测 235/235、typecheck、lint、build、API 类型生成、默认浏览器 2/2、真实 FastAPI/Fake 集成 1/1 均 exit 0。lint 两条原有 warning、主 bundle 约 602 KB 提示照实记录；这些命令通过不抵消新增 suppression。
- 独立浏览器验证同名来源精确寻址、首次索引提醒、Markdown、dirty 导航取消与冲突生效时机。修正 QA 回执夹具为真实字符串枚举后复跑通过。
- 真实 FastAPI/Fake 从一份含多个主题的来源生成两份稿件，仅确认一份，另一份仍 pending；正式页只有一份，任务写入为空，项目进度版本仍为 0。
- 混合文件批次成功/失败/未知各发送一次；明确失败项仅在用户重试后再次发送；未知不重发，继续入口只读取本次成功 ID。HTTP 400/503 为故障注入且被 UI 处理，未处理 JS/pageerror 为 0。
- [CI 38911508787](https://github.com/yifeng93/SummitEverything/actions/runs/38911508787) 在 `4b1dc04` 全 13 步 success，含 Python、Web、原生策略和内部 App/DMG 技术构建；不等于用户安装验收。

## 观察与未测边界

早期 QA 工具输出中的三条 `items.filter` 异常没有保存 raw，记 UNVERIFIED。QA 后来发现自己早期夹具将 ActionPage 回成裸数组，修正后 B 与完整浏览器复跑干净；不据此建立产品缺陷，也不补造旧日志。

Chrome DevTools MCP 未配置，使用项目 Playwright/真实 Chromium。真实模型/飞书/凭据/用户材料、Keychain、用户安装、公证、五日和双机 NOT_RUN；runtime metadata UNVERIFIED。原有探测 HTTP 409/404 与后续初始化恢复在 QA 报告单列。

## 持久证据

独立 QA 原报告与 21 份原始报告、日志、harness、manifest、截图按字节复制到 [初验证据目录](evidence/2026-10-16-frontend-usability-initial/REPORT.md)，新 [SHA-256 清单](evidence/2026-10-16-frontend-usability-initial/manifest.json) 可逐项复核。该报告记录对应固定 SHA，不代表修复版本结论。
