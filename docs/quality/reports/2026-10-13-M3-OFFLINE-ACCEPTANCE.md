# M3 离线模拟正式验收与合并授权

2026-10-13。**用户已批准M3离线模拟范围正式验收及合并；离线正式门PASS，已随[PR #13](https://github.com/yifeng93/SummitEverything/pull/13)合入main，merge `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`。** 不等同完整v1、真实服务、模型质量或安装包验收通过。

## 用户批准与固定候选

用户在本聊天对“批准M3离线模拟范围正式验收，并将codex/c19-dsh-sol-gate（受测源码0a1b8dc，文档整合HEAD303cf47）合入main”的询问回答：**“批准离线验收及合并”**。这一批准覆盖该固定产品树及随后文档收口；不授权改变产品规格、生产效果、真实资料、凭据或收费调用。

- 被批准产品源码：`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`。
- 独立QA报告提交：`93bbf45e296abb7d2b234059138cf9f8cad84351`；73个新增文档/evidence文件、无产品diff。
- 用户审阅的整合HEAD：`303cf472cb94f238e4dad99442a385b7d05f7fa9`，与受测产品树diff0。
- 合并前main：`5fd91c78930c80b2365957197b8a605757694a91`；远端main一致，GitHub主分支protected=false、rulesets为空，仓库无CI workflow。仍采用正常PR合并，不使用admin/force或绕过门。
- 保存DSH原工作树/`04a504f`、M3冻结/`b3d0dff`及handoff标签；批准本候选合入main不会移动这些冻结引用。

## 包级证据

| 包 | 离线技术结论 | 固定源码及证据 |
|---|---|---|
| 会话与历史 | PASS | `a9078bd327f73f2cde3bab14a8665885d0f57c1c`，QA固定`bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`；[独立QA](2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) |
| 完整问答、角色与记忆 | PASS，既有包范围加C19集中补验 | 最终源码`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`；[C19独立QA](2026-10-13-M3-PACKAGE-2-C19-DSH-REPAIR-1-QA-0a1b8dc.md)、[Sol门与完整历史链](2026-10-13-M3-C19-DSH-SOL-GATE.md)。85不同C19测试、491后端、56Web及适用静态/构建/隔离生成通过，实际HTTP/SSE、Chrome UI与history重开/重启通过 |
| 连续工作与归档 | PASS | `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`，QA固定`7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`；[独立QA](2026-10-12-M3-PACKAGE-3-REPAIR-1-QA-7fd8a53.md)、[Sol门](2026-10-12-M3-PACKAGE-3-SOL-GATE.md) |

原失败报告和原始证据保持不变；C19设备/信息主题误删、跨对象借证及默认cap掩盖真缺失在新SHA关闭。本次没有重启旧Stage B、逐小功能QA或重新开发包1/3。

## 保留边界与接续

`run_dev.py`停止wrapper的PermissionError/exit1为已记录本机测试脚本风险；该脚本与main无diff，后验无QA服务进程/监听，不冒称清理退出0。继续单独追踪，不作生产根因推断。

真实provider/飞书/业务材料/凭据/Keychain、native/DMG、模型R03质量、五日/双机、发布和M4/M5均没有由本轮验证；相应门NOT_RUN，runtime UNVERIFIED，有限smoke各0/1未消费。后续只按全v1计划与实际授权推进，不能把本批准扩大成真实操作授权。

合并后另建固定merge SHA独立QA checkout，核对受测产品树、祖先/父提交、历史证据、依赖与关联检查，留下postmerge报告；更新交接为真实main状态。若GitHub或新main导致产品树变化，应先停止合并并重新验证该新候选，不能自动沿用本SHA结论。

## 实际合并及合并后核验

PR #13 已于 `2026-10-13T01:02:58Z` 正常merge（未用admin/force），合并SHA `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`，两个父提交为 `5fd91c78930c80b2365957197b8a605757694a91` 与 `696d1dacaba92b090f742b9c9ba5e2d0a0b64ad8`。主checkout已fast-forward且clean，实际产品diff相对独立受测源码0a1b8dc为0。全新QA在另一个独立checkout固定该merge核验，具体结果在完成后追加；不能从候选PASS推断其尚未执行的命令通过。

## 合并后实际结论

固定merge `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2` 由全新QA核验PASS。报告提交 `21ec1edd29d30878c44fba19720f76907b8e8788`，原作者计数更正 `c5db4c935b623f1021f34ddf632d6b121b49e358` 仅改报告措辞。Sol实际读取[合并后QA](2026-10-13-M3-POSTMERGE-QA-47a3971.md)，核对49项证据全匹配，清单SHA-256 `fea86e113d493f454af8ee73ef9d306db79a31e18058628d0f8a02abf9aa8096`。guarded491、Web56及适用静态/类型/lock/build/隔离生成均exit0；父提交、祖先、产品树及既有71项证据保持均PASS。未重测候选UI/HTTP/对抗性矩阵，也未关闭真实或工具未测门。

首次日志包装器误用zsh只读变量status、切入web后相对日志路径错误，QA保留初次输出，修正包装器后复跑取得实际退出码。最终原始日志通过；未将包装器错误判作产品失败或伪装首次全绿。

本轮开发、独立验收、人批准、PR合并及postmerge核验已完成。下一位从实际main新建分支，不重新修C19或重启旧Stage B；未来阶段与真实动作仍须遵守全v1计划及实际授权。收尾提交仅文档/evidence，产品树保持受测merge。
