# M3 包 2 / C19 DSH 修复独立验收

日期：2026-10-13。独立 QA 固定验收产品源码 `be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`。QA worktree 起始 HEAD 与固定 SHA 完全一致；黑盒执行期间没有移动 HEAD。测试后产品源码目录相对该 SHA 无差异。QA 结论为 **FAIL**，具体缺陷交 Sol 判门；本报告不签发包 2 或 M3 正式验收。

## 结论与缺陷

**C19 主题词保留：FAIL，P1。** 独立新增“信息”结构对照复现了同类全局删词根因，故旧设备修复仍未达到 C19 的主题/证据边界要求。测试材料均为已确认的合成页面；信息词与 D3 矩阵通过后端服务 harness 执行，使用记录型 Fake answerer 观察 provider 调用次数及传入 passages，不调用真实外部 provider，期望观察引用与缺失边界：

| 模式 | 问题 | 正控材料 / 期望 | 实际结果 |
|---|---|---|---|
| 事实 | `白萤会展的年度访客信息登记办法是什么？` | 正文 `白萤会展年度访客信息登记须核验身份。` 应引用并保留“信息”限定 | 无引用、provider 0 次，误报缺少“年度访客登记” |
| 比较 | `比较白萤会展的年度访客信息登记办法` | 同上，应引用 | 无引用、provider 0 次，误报缺少“年度访客登记” |
| 方案 | `为白萤会展制定年度访客信息登记工作方案` | 同上，应引用 | 无引用、provider 0 次，误报缺少“年度访客登记工作” |
| 事实 | `白萤会展的年度访客信息登记办法是什么？` | 近似负控正文 `白萤会展年度访客登记须核验身份。`（少“信息”）应拒引并如实说明缺失 | 错误引用近似正文，provider 1 次，未报告缺失 |
| 比较 | `比较白萤会展的年度访客信息登记办法` | 同上，应拒引 | 错误引用近似正文，provider 1 次，未报告缺失 |
| 方案 | `为白萤会展制定年度访客信息登记工作方案` | 同上，应拒引 | 无引用，符合缺失边界 |

以上 6 项为 **5 failed / 1 passed**，原始断言、输出与退出码在 evidence 的 `harness/test_c19_information_qualifier.py` 和 `raw-logs/information-qualifier.log`。这不是单纯措辞差异：完整主题正文被漏掉，而少限定词材料在事实/比较模式被当作证据。它与“设备”等信息性限定词在主题归一化时全局剥除属于同类问题；建议 Developer 统一审计请求外壳与主题位置处理，而非逐词添加例外。

**D3 limit 与真实缺失混淆：FAIL，P2。** 独立 fixture 在默认 `limit=5` 下放入云岬营地 6 份有效预算材料；汀屿计划存在但只有访客登记资料，没有排期。事实、比较、方案三模式各查询 `比较云岬营地预算与汀屿计划的排期`，均引用 5 份预算材料，却把汀屿真实缺失替换成“引用条数已达上限、范围尚未覆盖，可缩小问题范围后重试”。`limit=20` 对照会准确报告汀屿缺少排期。期望是可以同时报告截断和已确认的真缺失，或明确指出尚未覆盖而不遮蔽已知缺失。默认配置的三模式均失败；结果及可直接复跑的 harness 在 `harness/test_c19_d3_limit_true_absence.py`、`raw-logs/d3-default-limit.log`。风险在于用户可能误以为已有材料只是被截断而重复缩小提问，无法得知资料实际不存在。

**D1 元数据归属：PASS（本次受测边界内未证实缺陷）。** 独立 probe 观察到：页标题或别名可将匿名预算正文绑定到问题对象；正文明确写了另一对象时，不借给元数据标题对象，且没有调用 provider；同时存在同名项目时两条都可引出，因此仍需产品 UX 明确歧义呈现，但当前证据不足以按契约判为缺陷。C19 计划允许项目/页面元数据建立归属，不能仅从页面位于其他项目目录推断正文归属错误。另，既有 `青榆` tracked 用例的正文明确写有“青榆”，不能作为“匿名正文仅凭 alias 绑定”的证据；DSH DEV 对该用例的概述不准确。本次独立匿名 alias fixture 单独支持实际观察到的绑定行为。原始 JSON 在 `raw-logs/probe-d1-d3-recheck.json`。

## 其他验收门

- 历史 C19/holdout 回归：**PASS**。原 previous12、expanded22、tracked19 共 75 次执行，其中 corrected/expanded 为相同 22 项重复；共 53 个不同用例，全部通过。日志明确记录重复，不按 75 个独立用例计算。
- 后端完整测试：**PASS**，469 passed，1 条现有 Starlette/httpx 弃用提示。
- Python 静态检查：**PASS**，ruff check、ruff format（79 files）、mypy（43 files）、lock check、`uv build` 全部退出 0。
- Web：**PASS**，56 tests / 12 files；typecheck、lint、build 均退出 0。Lint 有 2 条既有 warning。
- API 类型：**PASS**。项目 `api:types` 退出 0，执行后 tracked 生成文件字节无变化。另将 OpenAPI 与生成类型隔离输出到 `.local` 并比较，退出 0、无 diff。
- 本地 API/UI 合成流程：**PASS（仅实际观察到的流程）**。使用 Fake provider 在真实本地进程中操作隔离工作库，完成导入、确认、索引、设备事实查询、双对象比较、历史打开、引用重开；修改合成正文后旧历史保留快照并显示旧引用失效状态；服务重启后重开工作库与历史，篡改后的正文被确认记录校验拒绝。完整观察见 evidence `ui-observations.md` 与本地服务日志。信息限定词矩阵和 D3 holdout 是后端服务 harness，不是浏览器端到端复验；完整 / partial / zero 范围的专门 HTTP API/UI 验收本轮未执行（NOT_RUN），不据此记 PASS。
- 浏览器 DevTools console/network/PNG：**NOT_RUN**，当前环境没有可用采集接口；不以 HTTP 200 代替 UI 观察。
- 真实 provider、飞书、凭据、Keychain、真实业务材料、DMG、五日、双机及发布：**NOT_RUN**；runtime **UNVERIFIED**；有限 smoke **0/1 未消费**。

## 固定源码与证据

测试开始和结束时产品 SHA 均为 `be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`；`src web native tests scripts pyproject.toml uv.lock` 相对该 SHA 的产品 diff 为 0。服务已停止，API 18873 与 Web 15179 均无监听。测试期间未修改产品源码、tracked tests、依赖配置或 lockfile。测试结束时尚未生成本报告的原始源码工作树干净；以下 QA commit 只包含此报告与唯一命名的 evidence 目录，固定受测源码仍为 be4e72f。

证据目录：[2026-10-13-m3-package-2-c19-dsh-qa-be4e72f](evidence/2026-10-13-m3-package-2-c19-dsh-qa-be4e72f/)，入口为 `README.md`；原始命令、退出码、probe、harness、合成 UI workspace 和服务日志均在其中。完整文件 SHA-256 清单为 `SHA256SUMS`，可在仓库根目录运行：

```sh
shasum -a 256 -c docs/quality/reports/evidence/2026-10-13-m3-package-2-c19-dsh-qa-be4e72f/SHA256SUMS
```

**建议下一步：** Developer 对全局主题剥壳边界和引用上限/证据覆盖原因分别做统一修复，保留并运行两份 holdout；完成后提交新固定 SHA，由全新 QA 再验。本报告仅提供独立证据，不自行启动修复，也不改变包 2/M3 门状态。
