# M3 包 2 extra 2 Developer 报告（2026-10-12，待全新独立 QA）

用户在 extra 1 QA FAIL 后明确批准**再一轮且仅此一轮**；历史 repair 1/2、repair 2/2、extra 1 计数不重置。起点 clean SHA `09fd94c6127cdd4bb60827a102446cb352eb32be`，产品源码固定提交 `c41147fe54bf95103c741df192fc76eb9df0f9e7`（分支 `codex/m3-integrated-packages`）。Developer 自测完成，等待 Sol 调度全新独立 QA；这不是 QA 或包级 PASS。此前所有 QA FAIL 报告与证据均保留，extra 1 的 Sol 门与 QA 报告是历史记录，不在本报告修改。

## 行为修复

空引用结果不再固定声称“缓存版本与当前库不一致或资格检查未通过”。QueryService 根据本轮检索事实区分：有相关候选但被当前资格/hash 门拒绝、可读索引中没有与问题相关的证据、以及生成期间引用来源变化。事实、比较和方案分别给出与模式相符的缺资料说明；主文和 `missing_information` 一致。未发现相关候选时不会把库内无关页面的资格问题误说成当前查询故障。页面生成期间无法读取/已消失时报告“页面不可用”，不能把 `Eligibility(False, 'unavailable')` 当作 hash 过期。未检索到引用时不调用答案 provider、不补造事实或数字；诊断不改变 CURRENT/HISTORY、批准和 expected-hash 资格门。

相关回归覆盖 ready 索引中的不相关问句、空索引/not-ready、CURRENT 排除历史/未批准页、真正的旧 hash、provider 生成期间内容变化及页面删除/不可读；fact/comparison/plan 对 no-evidence 主文、missing 内容及 provider 调用次数均有断言。此前 C13/C20 修复、连续指代与切题边界、多材料比较/方案、角色/记忆、请求幂等与其他既有路径未修改。

## 验证结果

README 全量自动矩阵均实际运行，原始日志和 `.exit` 文件位于忽略目录 `.local/dev/m3-package-2-extra-2/raw-logs/`。每项记录的退出码为 0：

| 检查 | 结果 |
| --- | --- |
| `npm --prefix web ci` | PASS；126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | PASS |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS；417 passed，1 条 Starlette/httpx deprecation |
| `uv run ruff check src tests` | PASS |
| `uv run ruff format --check src tests` | PASS；73 files already formatted |
| `uv run mypy src` | PASS；40 source files |
| `uv lock --check` / `uv build` | PASS |
| `npm --prefix web run api:types` | PASS；生成的 OpenAPI 文件无 tracked diff |
| `npm --prefix web test` | PASS；55 tests / 12 files |
| `npm --prefix web run typecheck` | PASS |
| `npm --prefix web run lint` | PASS；保留 TodayView、ProjectsView 两条既有 warning |
| `npm --prefix web run build` | PASS |

定向测试最终为 36 passed（1 warning）。这些结果是 Developer 自测，不替代 QA。

## QA 交接与边界

请在独立 checkout 固定测试产品源码 `c41147fe54bf95103c741df192fc76eb9df0f9e7`，复演 extra 1 QA 的既有范围，并着重核验 C19：ready/stale=0 的 fresh index 遇无关主体时应诚实报告未找到相关依据，不声称缓存/资格异常；空/未就绪库、current 不纳入 history/无批准页面、真实 hash mismatch 应各有准确诊断；生成期间改变或删除/损坏所引页面应丢弃不再可信的回答并报告真实变化/不可用原因；fact/comparison/plan 的正文和 missing-information 一致，零引用时 answer provider 调用数为零。继续检查 earlier C13/C20、连续指代和主体边界、多材料比较/方案、角色/记忆与幂等路径不回退。

真实模型/服务、真实资料、凭据/Keychain、native/DMG、五日/双机及正式 M3 验收/合并均 NOT_RUN；runtime 元数据 UNVERIFIED。包 3 未开始。若该 QA 仍 FAIL，本次 extra 2 额度耗尽，必须停止并交用户决定，不可自行继续修复。
