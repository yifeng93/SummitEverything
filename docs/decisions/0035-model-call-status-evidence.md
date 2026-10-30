# ADR 0035：设置页模型状态使用持久调用证据

- 日期：2026-10-30
- 状态：已采纳

## 背景

设置页原先只在当前 React 生命周期保存 smoke 检查结果，刷新或重新打开后丢失；成功业务调用也没有进入徽章判断。本地 BGE 的可用状态还与三项云端 smoke 混在一起。

## 决定

- DeepSeek 最近调用状态由本机 acceptance ledger 的成功终态与实际 DeepSeek 用量记录派生；只看已配置、预留请求数或没有用量的终态不算成功。
- 现有 ledger 记录在读取时只作为「当前配置有历史成功记录」复用。后续 DeepSeek 密钥替换或删除会递增本机非秘密凭据代次，设置和计划绑定该代次，旧记录不沿用。
- DeepSeek smoke 的有限结果写入本机 smoke ledger，并绑定请求发出前的 profile、workspace、设置摘要和凭据代次。结果未知保留为未知。普通设置读取不联网。
- 本地向量化与排序分别核对 BGE 文件 ready、provider 选择和 enabled 开关。它们使用「本机可用」状态，无需云端 smoke。准备中的状态变化同步刷新两行能力。
- 最近失败 / 未知与历史成功并列保留；读取证据账本失败只降低调用状态，不阻断其他设置读取。

## 影响

设置摘要含 `model_call_status`。每次真实业务调用的预览确认、费用和用量门禁保持独立，不由此状态代替。详见 [API v1](../contracts/API-v1.md) 与[设置页规格](../product/FRONTEND-PAGE-SPECS.md#8-设置-componentssettingsviewtsx)。
