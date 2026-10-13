# M3 包 2 C19 DSH repair-1 独立 QA

## 结论

**C19 候选在本次离线合成验收范围内 PASS。** 受测产品源码 SHA 为 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07`。本报告仅给出本候选的独立技术验收结果，不代表 Sol 已签发包 2 / M3 正式通过，也不代表未执行的真实服务或发布门通过。

固定源码复核：QA checkout HEAD 与指定 SHA 完全一致；源码路径集合 `src web native tests scripts pyproject.toml uv.lock` 相对固定 SHA 的 diff 为 0。QA 新增内容仅限本报告与同名 evidence 目录；临时 harness 位于被忽略的 `.local/qa`。

## 验收结果

- C19 distinct 回归集：85 项通过。构成为初验 holdout 12、expanded matrix 22、tracked topic-scope 41、information qualifier 6、D3 true absence 4。corrected22 与 expanded22 文件字节相同，只计一次。完整后端套件已覆盖 tracked 回归，命令结果为 491 passed。
- 信息性限定词独立复现：完整“年度访客信息登记”正文在 fact、comparison、plan 三类均可由当前批准正文支持；少“信息”的近似正文不引用、不进入 Fake answerer 上下文，并明确报告缺失。6/6 通过。
- 限额与真实缺失：default limit=5 下，A 的预算引用和 B 的排期真缺失同时呈现；limit=20 时仍准确保留真缺失。纯 cap 不转成“缺少依据”。独立 D3 harness 的 4/4 是 default=5 的 fact/comparison/plan 三模式加 limit=20 一控。候选前 20、旧 hash、尾部不合格候选由 tracked topic-scope 41 项中的既有测试覆盖；不要求本轮重构公平排名算法。
- D1 归属：独立有限探针覆盖批准标题单独绑定匿名正文、alias 单独绑定匿名正文、正文明确属于另一个对象时不得继承，以及相同对象跨目录的正例。title-only / alias-only 按当前规格能建立归属，两正例各调用 Fake answerer 一次生成答案；显式其他对象正文未借用证据且 provider_calls=0；同名对象跨目录正例引用两项材料。探针退出码 0。
- 结构反控：由独立复跑的 tracked topic-scope 41 项、独立 previous holdout 12 项和 expanded matrix 22 项覆盖，没有额外新增结构词汇测试组。覆盖查询壳位置、名称中含查看/总结、礼貌词和“那”追问、句末“工作方案”、访客工作证内部“工作”、family 词不拼造非连续主题、资料保管签领完整及少“签领”反控；矩阵无失败。
- 后端 / Web / 静态：后端 491 passed；Web 56 tests / 12 files；Web typecheck、lint、build 均 exit 0。Ruff、format check、mypy、uv lock --check、uv build 均 exit 0。独立 OpenAPI 生成与 tracked TypeScript 类型隔离比较最终 exit 0、diff 为空。git diff --check exit 0。
- Loopback API：实际本机 HTTP POST `/api/v1/queries` SSE 与 history reopen 的完整、partial、zero、少信息反例、cap+真实缺失、纯 cap 均有原始响应记录，见 evidence/raw/http-sse.log。
- 实际 WebUI：在真实 Chrome 界面操作合成库并可见检查上述完整、partial、zero、反例、cap 场景以及 history reopen。具体文本和操作顺序见 [UI 观察记录](evidence/2026-10-13-m3-package-2-c19-dsh-repair-1-qa-0a1b8dc/ui-observations.md) 、ui-steps.tsv 和 [实际 AX 快照](evidence/2026-10-13-m3-package-2-c19-dsh-repair-1-qa-0a1b8dc/ui-ax-snapshot.txt)；并非以 API/harness 冒充 UI。
- 独立依赖准备：`uv sync --locked --group dev` 与 web 下 `npm ci` 均成功。命令、退出码和原始日志索引见 evidence/commands.tsv 与 evidence/raw。

## 风险与未测边界

本地 run_dev wrapper 在 Ctrl+C 后 Uvicorn 正常关停，但 wrapper 的 finally 清理因重复 SIGINT 路径抛出 `PermissionError: [Errno 1] Operation not permitted`，导致该次 wrapper 退出码为 1。QA 自身监听端口 18874 / 15180 已核验无 listener；只检查本 checkout 相关进程也无匹配存活项。该问题是测试运行器清理风险，源码相对受测 SHA 无变更；没有证据将其归因于本轮产品改动或宣称完整 cleanup exit 0。trace 保存在 raw/run-dev-final.log、processes-after-stop.txt 和 listeners-after-stop.txt。

OpenAPI 类型比较第一次因 CWD 导致 diff 指向不存在的 .local 文件，初次日志/退出码保留为初始失败记录；修正导出与 diff 路径后隔离重新生成，最终 exit 0 且 diff 为空。DevTools console/network、PNG 导出能力不可用，标为 NOT_RUN。真实 provider、飞书、凭据、Keychain、真实材料、native/DMG、五日/双机和发布均 NOT_RUN；runtime UNVERIFIED；本轮 smoke 额度 0/1 未消费。UI 首次打开库时索引尚未就绪属于测试前置条件，准备索引后正常运行。

## 证据

独立 evidence： [evidence 目录](evidence/2026-10-13-m3-package-2-c19-dsh-repair-1-qa-0a1b8dc/README.md)。其中保留逐命令日志与退出码、原始 loopback 响应、独立 harness、UI 观察、固定 SHA 与最终工作树状态；SHA256SUMS 校验清单覆盖 evidence 中其余文件。
