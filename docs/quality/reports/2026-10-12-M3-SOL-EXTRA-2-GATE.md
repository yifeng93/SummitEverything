# M3 包 2 extra 2：Sol 门判断

日期：2026-10-12。**包 2 FAIL / C19 P1；包 1 保留历史 PASS；包 3 实现 NOT_RUN。** extra 2 用户授权轮次已结束，停止产品修改，等待新决定。

固定产品源码 `c41147fe54bf95103c741df192fc76eb9df0f9e7`；独立 QA 固定 `d2236c243ac28c86b94acd8e8dd139dc865b7b75`。产品与文档提交、QA 报告提交之间 src/tests/web/native/lock/config 无差异。[QA 报告](2026-10-12-M3-PACKAGE-2-EXTRA-2-QA-d2236c2.md)及证据提交 `df659c3b6e99c4c677bfea0897e97446d35391f4` 已整合。Sol 复核 102 项 manifest 文件 SHA-256 无 mismatch；README 矩阵实际 exit 全 0（417 后端、55 Web），QA 服务已停止。

## 已交付修复与剩余问题

无依据原因误报已独立通过：fresh-ready fact/plan 缺资料不报缓存异常、不调用 answer provider；not-ready/empty、真实 hash/批准变化、生成期间内容变化与页面消失分别准确说明。历史确认与知识效力、记忆候选来源门、取消/非空 partial 重启、稳定请求和本机隔离等本轮覆盖回归通过。原 plan 共享计数快照造成的误判已由 QA 单独重跑纠正（14→14），不算产品缺陷。

**比较对象证据归属仍错误。** 索引 ready、6 页、stale_pages=0；没有“风铃工程”或“霜塔项目”的牙刷储存资料。查询“比较风铃工程与霜塔项目的彩色牙刷储存规则。”却引用专项储备 3.6 万元和朱雀预算 12 万元，写入 source_statements，missing_information 为空，并调用 provider（4→5）。Sol 核对原始 HTTP/SSE、引文、counter 与代码后判定实际 C19 P1 FAIL。资料本身是合格 current 内容，但不是问题所指定对象/维度的支持材料；不能以批准资格通过代替相关性正确。

此前为保持跨材料能力，比较/方案未采用 fact 的主体收窄。Sol 对该架构边界的判断不充分。收口应同时检查三类问答的明确对象、缺失对象、缺失维度与跨材料路径，避免只修一个模式的平行问题。不得降低 C19，删除负控或将不相干事实降称“仅作参考”来通过。

## 待批准的具体下一步

原两轮及追加 extra 1、extra 2 全部记录并保留，不重置。请求用户是否允许再增加**最多两轮**统一收口修复：Developer 连续完善三类问答的证据范围，明确比较/方案的对象集合，保留范围内多资料；全部指定对象无依据则明确 missing/无引用/不调用 answer provider，部分缺资料则逐对象/维度说明不足，不用多页数量伪装完整比较；广义未指定对象问题仍允许合理多资料。每轮 Developer 自测并固定新 SHA，全新独立 QA 验整包。通过后直接继续包 3，仍失败或遇高风险门再交用户。授权前不实施。

正式 M3 验收/合并及真实服务/材料/凭据/Keychain、native/DMG、五日、双机门仍未通过。本轮这些场景 NOT_RUN，runtime UNVERIFIED，smoke 未消费。功能分支 `codex/m3-integrated-packages` 完整保留代码和各轮原报告，main 未改。
