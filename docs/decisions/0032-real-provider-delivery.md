# ADR 0032：真实 provider 交付与连接恢复

日期：2026-10-30。状态：用户决定，纳入首版交付。

## 决议

- 正常启动、设置界面和交付应用只使用 DeepSeek（整理与问答）和本地 BGE（向量化与排序）。不提供 Fake、Mock 或测试模式入口，也不自动降级到模拟 provider。
- 新 profile 默认选择 real + DeepSeek/local。缺密钥、Keychain、本地模型或有效索引时显示明确的未就绪原因和恢复入口。旧 Fake 配置映射到 real + DeepSeek/local 准备状态；旧索引不得据此判为 ready。
- 正常 API 构造的生产检索服务必须显式接收所需的真实 provider；metadata/status/预览服务缺 provider 时不能构造 Fake，误入生成操作时必须 fail closed。Fake 类仍保留给自动化测试兼容使用；测试应用必须通过隔离的测试依赖工厂显式注入 Fake，并使用隔离工作库。用户/API/环境配置不提供 Fake/Mock 运行开关。
- 飞书 status 查询只读本机凭据：区分 access token 当前可用、已过期但 refresh token 可用、需要重新授权。status 不刷新 token；用户已授权日历可以在今日自动发起一次只读日历请求，由请求边界续期并保存 token。续期失败需分类为可恢复错误，不扩 scope，不循环重试。
- 今日自动日历读取只在对应身份、有效日历 scope 与可用/可续期凭据都满足时发生。StrictMode 并发请求合并；切库、卸载和迟到响应不得污染当前视图。只读日历不触发任务写入、材料读取/导入或模型请求，任务与材料继续遵守各自确认门。
- 问答页在发问前展示真实 provider 与本地索引就绪状态。未就绪时保留问题并提供设置或索引入口；服务错误与恢复操作使用明确间距，切换到设置再返回不得丢问题。

## 背景

用户准备将当前应用作为真实桌面应用交付。测试 Fake 配置被误留在正常入口中；过期的飞书 access token 让只读 status 返回未授权，阻断了本可由日历请求续期的既有个人授权。问答配置错误首次在发问后才暴露，恢复按钮也贴着错误提示。

## 边界与验收

- 配置、状态页和初始 profile 均不允许正常运行选择 Fake/Mock。自动化测试可用显式测试注入；测试不能接触用户 live profile、Keychain 或真实 provider。
- 对过期但仍有有效日历 scope 和未消费 refresh token 的凭据，status 报告“可续期”并保留 scope；一次真实读取成功后保存新 access/refresh 状态。已消费或无 refresh token 时不能展示为可用，错误需留给用户重试授权。
- 读取 capability 必须由实际凭据与 scope 决定，不能仅凭 App ID 推断可用。
- 问答预检在请求发送前阻止配置缺失；没有 provider 调用，不清空输入，并保留用户可见的下一步。
