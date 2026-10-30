# ADR 0031：已连接后的飞书日历直接只读

日期：2026-10-29。状态：用户决定，纳入 v1。

## 背景

今日页的日历刷新会先生成一次性范围计划，再要求用户二次确认。日历已经是只读能力，额外点击让日常查看更繁琐；用户明确决定连接授权后点击刷新/分页即可读取。本决议只调整日历读取，不推及材料导入、任务写入或付费模型。

## 决策

- 今日 Web 和本机 Agent 的 `list_calendar` 共用当前 API 的直读路径。日历按钮点击后立即请求，不显示“本次范围预览”或“确认并执行本次读取”，不创建、确认或消费 acceptance-plan。
- 继续使用已配置的应用或用户身份。服务端检查活动 profile/workspace、Real 配置、凭据、实际 scope、有效 IANA 时区、带时区的起止时间、页大小和 cursor。Real 配置缺 app_id 时必须拒绝，不能因 provider 装配回落到 Fake 而返回合成成功。
- 保留 `calendar:calendar.event:read`，并兼容已存的 `calendar:calendar:readonly` 用户 scope；不扩大新 OAuth 请求范围。应用主日历不代表用户个人日历，返回资源归属不明确时仍须如实说明。
- 显式真实时间范围继续单页；provider 需要时最多进行 token/refresh、primary calendar 和 events 三步，单次响应受现有 4 MiB 上限与 HTTP deadline 约束。失败不自动重试，旧结果和错误态分开呈现。Fake 分页保持现状。
- 材料与任务列表/读取、材料导入仍按原计划预览和独立确认；真实任务写仍禁用；不改变用户知识批准、模型付费或资料导入边界。

## 验收

- Web 和 Agent 日历读取不发 acceptance-plan 请求，服务端两路由使用同一 service；Agent 仍绑定当前工作库。
- mock 验证有授权/权限时成功，无用户授权/缺 scope/Real 缺 app_id 时拒绝；primary + events 最多三次 HTTP 请求，超时不重发。
- Web 保留忙碌、错误、空结果、截断和 Fake 分页状态；没有真实飞书、付费模型或 Keychain 读取。
