# M3 包 2 repair 2 浏览器观察

固定产品 SHA：`94854bafc0f6aec4d79e55c851be2640ef436739`。浏览器为 CUA 控制的本地 Chrome/IAB 页面，WebUI `127.0.0.1:15173`，API 为 loopback；使用本地合成工作库与 MockTransport provider。

| 路径 | 实际操作与可见结果 | 状态 |
|---|---|---|
| 自然事实问法 | Fresh synthetic index 上直接问“青岚计划的预算上限是多少？”及礼貌问法“你能告诉我青岚计划的预算上限是多少吗？”、“我想知道青岚计划的预算上限。”；两种礼貌问法只返回青岚合格页，未带朱雀。 | PASS |
| 连续主体承接 | 同一会话问青岚预算 → “它呢？” → “它什么时候启动？”，来源保持青岚，无朱雀；转问“那朱雀项目的预算上限呢？”后再问“它”，来源转为朱雀；切到未知“风铃工程”后续指代无旧主体 citation 或数字。 | PASS |
| 正式页自然命名 | 通过别名青岚计划、仅正式页标题“霁川预算核定”、manifest 项目“潮汐运营项目”及主线“澄川协作线”分别检索；找到合格正式页的真实正文，摘录没有补入标题/别名/线项目名。 | PASS |
| comparison 与 plan | 新会话比较青岚与朱雀时两份资料均被引用，推断单独呈现；plan 同时跨资料并将 source statements、inferences、advice、missing information 分开。 | PASS |
| current/history 和历史引用 | 当前范围只引用青岚当前版 18 万；包含历史版可引用 superseded 旧版并明确标“已被替代的历史版本，仅限历史参考”。点击历史引用打开 PageReader。hash 匹配时 PageReader 错显示“待确认”“此页面自上次确认后已有变化”；详见 QA-R2-01。外部改正文后重开旧回答，citation 显示“原引用版本已更新”，PageReader 显示新正文且标不可替代旧依据。 | FAIL（历史页状态语义） |
| first-person memory candidate | 浏览器新对话直接输入“我偏好用简短中文回答，并明确标出资料没有提供的数字。”，没有粘贴或从 clipboard 读取。用户真实消息出现后勾选本人表达，按钮启用；点击显示引用/材料拒绝提示，API 对同 message ID、user_expression=true 返回 422。短句正控创建 pending 候选为 201；引用材料 canary 为 422。 | FAIL（误拒自然本人偏好） |
| Console / Network 面板 | 浏览器 CUA 能读取页面 AX，但本轮没有实际暴露 DevTools console/network 面板。 | NOT_RUN |

浏览器 AX 用户输入设置为 DOM `setValue`，没有剪贴板材料来源。合成资料、问题和 provider 内容均为 QA 构造；没有真实外部请求。