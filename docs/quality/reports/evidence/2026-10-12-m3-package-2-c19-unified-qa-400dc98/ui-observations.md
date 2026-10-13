# C19 WebUI AX 观察记录

固定源码 `247f6708c68812e8b217b1079a2fe953ebb06960`，文档交接 HEAD `400dc98c4b0a555561bb98f6633cf1d22ece8550`。在真实 Chrome 访问本地开发 WebUI `http://127.0.0.1:15173/`，API 为 loopback `127.0.0.1:18893`；工作库 `.local/qa/c19-unified/ui-workspace`，Fake embedding，4 页合成已确认知识。查询和答案留在隔离 profile。没有真实模型/Feishu 请求。

1. 通过 WebUI 新建“C19 QA 模拟库”，再以 API/真实 PageWriter 写入青砾工程预算 14 万、琥珀项目预算 9 万、青砾启动时间五月、琥珀启动时间九月四页，并通过 API Fake index plan/job 建索引。初始只有每对象一项时，UI 的“跨材料比较”结果引用青砾预算和琥珀排期，明确列出青砾排期、琥珀预算缺失；没有将两组错误配对当完整比较。
2. 增加剩余两项并增量索引后，UI 比较“青砾工程和琥珀项目的预算和排期”，显示四条匹配的已确认来源、无对象/维度缺口，仅提醒没有共同的比较口径；没有推断优劣或因果。历史列表显示“已完成”。
3. UI 对已知两项目询问“纸伞保管办法”时返回零引用，并逐对象说明缺少保管规则依据。
4. UI 无对象广义询问“比较预算和排期，并汇总现有资料。”时，显示四条预算/启动时间材料及“共同的比较口径或指标”缺失，保留跨材料比较路径。
5. 刷新页面后通过本机历史重开双对象完整比较，原答案、四条事实、推断和四条引用重新显示。

UI scope覆盖：fresh ready-index negative、complete two-object positive、partial missing、unknown-topic negative、general comparison positive、history reopen。浏览器DevTools console/network及PNG：NOT_RUN（本轮没有相应DevTools/截图导出接口）。
