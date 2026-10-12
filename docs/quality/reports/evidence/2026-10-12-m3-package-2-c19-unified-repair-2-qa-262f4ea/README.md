# C19 repair 2/2 QA evidence

- 固定 QA HEAD：`262f4eaa418d70f983f3b0b260d3635cd2e28c92`
- 固定产品源码：`f79f613a902758da3173a5b27219fa568a912f5e`
- 最终 verdict：C19 P1 **FAIL**。本轮是最终 repair 2/2，QA 不修改产品代码，也不开始新的返工轮。
- 测试命令、exit 状态见 `commands.tsv`；逐命令原始输出和 `.exit` 见 `raw-logs/`。
- 原 repair-1 QA 两个 harness 的原始副本见 `harness/test_c19_previous_holdout.py` 与 `harness/test_c19_fresh_holdout_original.py`；没有覆盖或改动仓库中旧 evidence。仅本地修正过的9项副本见 `harness/test_c19_fresh_holdout_corrected.py` 和 correction patch；独立扩展矩阵见 `harness/test_c19_r2_expanded_matrix.py`。
- 最小黑盒复现及结构化计划见 `harness/reproduce_device_topic.py`、`raw-logs/device-topic-reproduction.jsonl`。输出观察 `plan term:访客领用`，正文含完整“访客设备领用”短语却未被认作支持；Fact无调用，混合比较仅将预算 passage 发送给 answerer。
- UI AX / API 观察见 `ui-observations.md`；DevTools console/network/PNG未实际取得，为 NOT_RUN。
- 隔离导出 OpenAPI 与生成 TS 见 `openapi.json` / `generated.ts`，只生成到QA evidence，并与 tracked `web/src/api/generated.ts` diff exit 0。
- `final-state.txt` 记录产品树、服务停止后的端口与真实外部门状态。

所有 fixture 均使用合成对象/文本，外部模型、真实 Feishu、凭据、Keychain、真实材料与 smoke 未使用。测试服务均仅监听 loopback，停止后端口不再监听。
