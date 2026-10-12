# M3 C19 统一修复周期：Sol 最终门判断

2026-10-12。**C19 / 包 2 FAIL（P1），M3 正式门未通过。** 包 1、包 3保留各自已测离线 PASS。本次用户重新授权的统一修复已经完成初验、自动返工 1/2、自动返工 2/2及每轮全新独立 QA；额度中断没有重置次数。依据 AGENTS.md 第62行，两次返工后仍失败，停止自动源码修改并交用户决定。

## 固定版本和实际核证

- 最终产品源码：`f79f613a902758da3173a5b27219fa568a912f5e`；全新 QA 固定交接 HEAD：`262f4eaa418d70f983f3b0b260d3635cd2e28c92`。交接仅7份文档。
- [repair 2 独立 QA](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-QA-262f4ea.md) 提交：`2061b6260ece1b3887fc1ba34cc3960e61716b2a`，已导入功能分支。Sol 实际读取报告、原始退出码、主题复现、浏览器及服务停止记录，核对 [57 项证据清单](evidence/2026-10-12-m3-package-2-c19-unified-repair-2-qa-262f4ea/SHA256SUMS) 全部匹配。清单 SHA-256：`485c08400d007c71e71af1d1786f1f66ff9ea0233f6499e057354f846057b35a`。
- QA 报告提交与被测 HEAD 的产品、测试、脚本、依赖/配置树 diff 为0；QA checkout clean，自己的 API/Web 服务停止，端口无监听。没有在 QA 期间移动受测源码。
- [统一初验](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-QA-400dc98.md) 47项证据及 [repair 1](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-1-QA-04a0239.md) 23项证据均已核对，原 FAIL 与哈希保留。初验47项清单 SHA-256为 `2ab9b4a9a04b5bd5f9a2423a62f0730d5a67bebd2d36bf94706cbd25548d08d1`；repair 1清单为 `aca1528564e9bd7b5cbeec6b53ba3fa3de6704208921aa71bc2ab8593c718ecd`。

## 已交付与未关闭

对象、局部主题和覆盖 pair 统一驱动三类问答、邻页、引用、provider passages与缺失信息。原无对象资料误引预算、部分对象缺失、联合维度误配、陌生主题回退、名称/主题污染等已测反例已关闭；正确证据不能靠页数、高重排分或 provider 的空 missing 列表伪装完整。旧12项及纠正后的9项独立 holdout全部 PASS。

**仍有P1：信息性主题词被全局剥除。** 问“比较枫湾活动预算与玄石展览的访客设备领用办法”，已确认正文确有两组支持。planner 却把 `访客设备领用`改成 `term:访客领用`，导致正文匹配失败。三模式及倒序只引用预算、错误报告设备主题缺失；单独问设备主题也零引用。Chrome 实际 UI 和历史重开复现，有限结构矩阵15 PASS / 7 FAIL，7项为同一根因。完整自动检查通过不能抵销这个产品失败。

Sol 额外只读检查发现同一清理规则也会把“年度访客登记”改成“访客登记”；“专项证章领取”还可能生成伪对象“的专项”。这是解析风险观察，不冒充独立 QA 场景通过/失败。下一次若获授权，应修复主题归一化和对象识别的共同边界，不为每个词追加例外。

## 门与证据限度

| 门 | Sol 判断 |
|---|---|
| C19 / 包2 | FAIL，未关闭上述P1 |
| 原12及纠正后9项 holdout | PASS，当前固定源码独立复跑 |
| 新有限结构矩阵 | 15 PASS / 7 FAIL，同根因 |
| 自动检查 | PASS：guarded 后端450、Web56、Ruff/format、mypy43、lock/build、Web类型/lint/build |
| 隔离 OpenAPI→TypeScript稳定性 | PASS，输出在 `.local/qa`，生成TS与tracked一致，未改产品文件 |
| 浏览器完整控制、真正partial、无依据 | PASS，限定合成场景 |
| 浏览器设备主题及history reopen | FAIL，实际复现P1 |
| 包1/包3 | 保留既有报告的离线PASS；未改对应模块，关联自动回归通过，不扩展为未测门通过 |
| M3正式验收/合并 | 未通过；没有合并main、没有发布 |
| 真实服务/provider/材料/凭据/Keychain、native/DMG、五日、双机、release | NOT_RUN，smoke未消费 |
| DevTools console/network/PNG | NOT_RUN |
| runtime元数据 | UNVERIFIED |

旧 repair 1 harness 中完整两pair却要求赤陶 missing 的一条断言，经 Sol 对规格和fixture核对确认为遗留错误。本轮 QA 仅更正独立副本，强化两组引用/provider支持断言，并加删除赤陶正文的partial对照；原QA文件/报告/哈希未改。纠错不取消 repair 1真实的混合主题P1，不构成降低验收门。

## 待用户决定的具体下一步

建议额外授权一轮，由 Sol 直接收口剩余归一化/对象识别根因，再由全新 QA 验收：仅剥离位置明确的请求外壳，保留主题中“设备、年度、专项”等信息性词；禁止在已划为主题的片段内仅因实体后缀就猜新对象。审计所有清理与回退分支、加内容保持的结构性正反控，保留旧12/9与本次完整/partial/zero矩阵；固定新SHA独立QA，不改词汇白名单或默认拒答。不做真实服务、正式合并或发布。

此提议尚未获批，源码保持上述固定版本。若用户暂不追加，完整代码和证据保留在 `codex/m3-integrated-packages`，供后续接续；不得以“自动检查全绿”标记M3通过。
