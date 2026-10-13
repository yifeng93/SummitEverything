# Browser observations

受测产品源码 `f79f613a902758da3173a5b27219fa568a912f5e`，固定 HEAD `262f4eaa418d70f983f3b0b260d3635cd2e28c92`。Google Chrome 实际打开 loopback WebUI `http://127.0.0.1:15172/`；API `http://127.0.0.1:18872/`。工作库位于此 checkout 的 `.local/qa/c19-r2/ui-workspace`，profile 使用 Fake/offline 配置和两个合成项目、两页经 UI 明确确认的内容。

- **UI-C19-1 完整混合family+exact反例：FAIL（同自动P1）**。已确认页原文含“枫湾活动预算上限为七万二千元”和“玄石展览访客设备领用须登记姓名并归还胸牌”。查询“比较枫湾活动预算与玄石展览访客设备领用办法”，模式“跨材料比较”。AX显示只引用预算，并错误列出 `玄石展览：缺少term:访客领用依据`。
- **UI-C19-2 完整控制：PASS**。查询“比较枫湾活动预算与玄石展览登记姓名流程”，正文分别支持“预算”和 exact `登记姓名`。AX中两条陈述和两条当前有效引用均可见，没有主题pair缺失；比较口径缺失被单独明确为不可推断。
- **UI-C19-3 partial：PASS**。查询“比较枫湾活动预算与玄石展览活动餐券登记”。只引用预算正文，单列玄石活动餐券登记缺口，并说明材料不足以比较。
- **UI-C19-4 unknown-zero：PASS（可见行为）**。模式“提出工作方案”，查询“枫湾活动活动餐券登记办法怎么安排？”。AX显示没有能确认的资料、无引用，明确列出 exact主题缺失。
- **History reopen：FAIL继承原结果**。从“混合family+exact反例”本机历史点开，原错误缺口、预算引用和已完成状态仍显示。它证明历史重开状态保持，缺陷回答也随记录保持。

Chrome DevTools console/network导出及PNG本轮工具接口无法实际取得，记 **NOT_RUN**。服务日志确认 browser 查询 `POST /api/v1/queries` 与重开 `POST /api/v1/conversations/{id}/reopen` 均返回200；不据HTTP 200判业务通过。测试只用 loopback、Fake provider 与合成内容，无真实服务/材料/凭据。
