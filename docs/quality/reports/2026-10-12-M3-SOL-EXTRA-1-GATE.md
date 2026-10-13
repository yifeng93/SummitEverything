# M3 包 2 extra 1：Sol 门判断与接续

日期：2026-10-12。用户明确授权的额外一轮修复与独立 QA 已完成。**包 2 仍 FAIL；包 1 保留历史 PASS；包 3 实现 NOT_RUN。** 未合并 main，未进行正式 M3 验收。

## 实际目标与核证

- 固定产品源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`；独立 QA 固定 checkout `507cc1f197ce3af3b22aa53c98148e4ca45ff935`。文档提交与产品源码的 src/tests/web/native/lock/config 树无差异。
- [独立 QA 报告](2026-10-12-M3-PACKAGE-2-EXTRA-1-QA-507cc1f.md)及证据提交 `b8eb2457c600414ff3b8c83d9fe2d1e5c125e114` 已整合至功能分支。QA 未修改产品或已有测试。
- Sol 读取实际 index status、HTTP 200/SSE 完成字段、空引用与 provider 调用计数，以及对应 QueryService 的无引用分支；确认缺陷不是索引未重建或夹具错误。
- 证据 `manifest.json` 使用 evidence 根目录相对路径；45 项文件实际 bytes/SHA-256 校验无 mismatch。11 个最终自动检查 exit 均 0，guarded pytest 407 passed、Web 55 passed；类型、静态、锁、生成接口及构建均通过。QA 服务已停止、工作树干净。

## 通过与未通过范围

额外授权所针对的两项缺陷均独立通过：已批准 superseded/invalid 页面正确显示确认状态与历史效力，hash 真实变化仍待确认；正常本人偏好可创建 pending、编辑并单独确认后进入 active prompt，原消息材料引文/裸引号/blockquote 子串及伪造来源仍被拒。原 FAIL 证据保留，不改写历史。

**C19 新缺陷为 P2 提示误导：** 新鲜索引 `ready`、7 页、`stale_pages=0`，查询“为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。”时没有相关依据。主文正确说明缺依据，引用、来源陈述、推断、建议皆空，provider 调用数 19→19；但 `missing_information` 固定返回“已缓存的资料版本与当前工作库不一致，或当前资格检查未通过。”无依据不等于缓存损坏或资格异常，提示可能误导用户重新索引/确认资料。没有证据泄漏或编造数字，但不能隐瞒该问题、降低 C19 门或据自动检查判整包 PASS。

## 后续需要的授权

原两轮自动返工及用户追加的唯一 extra 1 均已使用。停止产品修改，等待用户是否授权额外一轮针对该诊断问题的修复及全新独立 QA。包 3 需包 2 通过后再实施，先前只读准备保留在[历史接续记录](2026-10-12-M3-SOL-GATE.md)。

如获授权，修复应区分相关性未召回、版本/资格拒绝和生成期间内容变化，不凭空声称缓存故障；覆盖 fact/comparison/plan 的无依据结果和真实 stale/hash 反例，保留不自动调用 provider、信任门及缺资料不造数。Developer 连续修复、自测并固定新 SHA，全新 QA 验完整功能包。正式验收与合并仍需用户批准。

真实服务/材料/凭据/Keychain、native/DMG、五日、双机与发布门 NOT_RUN，runtime UNVERIFIED；本轮未消费 smoke。功能源码与全部证据留在 `codex/m3-integrated-packages`，主 checkout main 未改。
