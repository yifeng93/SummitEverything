# M3 包 2 C19 DSH 候选统一返工 1/2：Developer 报告

**状态：DEV 自测通过，等待全新独立 QA。** 本报告不签发 QA 或 M3 通过结论。

本轮从干净提交 `4010c54c36f197748f0e0f71c79f6a38c978af66` 开始，分支为 `codex/c19-dsh-sol-gate`，唯一实现工作树是 `/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-sol-gate/SummitEverything`。受测固定产品源码 SHA 为 **`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`**。源码提交之后没有产品文件改动，后续 HEAD 只包含本报告、evidence 和状态入口文档；Sol handoff 需分别记录源码 SHA 与文档 HEAD。main、M3 冻结基线和 DSH 交接目录未修改。

## 修复行为

主题解析不再通过 `_TOPIC_FILLER` 在对象候选、family-specific dimension、主题短语和别名尾部全局删除词语，也不再把整句所有“的”改为空格。信息性词留在原主题范围里；请求外壳只在明确的句首 / 句尾位置剥除。句末“工作方案”可识别为方案请求，而“访客工作证”中的“工作”继续作为主题内容。family-specific 问法按 family 词所在位置拆成连续片段，例如“年度资料保管签领”表达为 `storage & term:年度资料 & term:签领`，不会拼造出正文中不存在的“年度资料签领”。主体跨度也保留了比较外壳后的“查看明细项目”完整名称，不会退化匹配库内更短的“明细项目”。

引用上限说明按对象 / 主题 pair 判因。当前仍符合资格且确实支持该 pair 的候选若被前 20 候选或最终 citation 上限排除，会报告相应的截断范围；没有当前合格支持的 pair 保留真实“缺少依据”。尾部旧版本或资格不符材料不会被计作隐藏支持。若上限只排除了已覆盖范围的重复材料，系统只给中性上限提示，不把另一个真缺失改成上限问题。资格复核仍使用统一的当前内容规则和引用前 SHA 检查，没有放宽 `domain/content.py`、角色权限、provider 边界或索引预算。

## 验证结果

初次固定 QA 中两组失败 harness 已原样复制到本工作树 `.local/dev/c19-dsh-r1/harness/` 后复现 RED：信息主题 **5 failed / 1 passed**；citation cap **3 failed / 1 passed**。新 tracked 集成测试共 **41 项**，复用真实 PageWriter、IndexStore 和 QueryService fixture，覆盖三种问答模式、信息 / 资料主题、缺词近似正文、计划尾壳与复合词、family 中断词连续性、对象名起始动词、真实缺失与有效候选截断、limit 1 / 默认 5 / 高上限、前 20 外支持和失效尾候选。

固定源码上的结果：

- guarded 全后端：**491 passed**，exit 0；保留 1 条现有 Starlette / httpx 弃用警告。
- C19 tracked 回归和初验旧 / 新 holdout 合并：**107 executions passed**，exit 0；对副本路径归一化后为 **85 个不同测试 ID**。其中 `test_c19_r2_expanded_matrix.py` 与 `test_c19_fresh_holdout_corrected.py` 是字节相同的 22 项矩阵副本，QA 只需保留其中一份复跑。
- Ruff、format、mypy（43 个源文件）、`uv lock --check`、`uv build`、API / TS 类型生成稳定性、`git diff --check`：均 exit 0；OpenAPI 与生成 TypeScript 无 diff。
- Web：**56 tests / 12 files**，typecheck、lint、build 均 exit 0。lint 保留两条既有 `react(set-state-in-effect)` warning。
- 独立 Fake loopback Uvicorn：complete、partial、zero 的真实 HTTP SSE 请求及 history reopen 均 PASS。合成信息主题完整正文可引用；混合比较只引用有支持的对象并列出另一对象真缺失；无资料时保持正确缺失且无 citation。脚本和原始输出在 evidence 中。此项是 API loopback，不是浏览器 DevTools / WebUI 观察。
- Web 依赖 `npm ci` 与 Python `uv sync --locked --group dev` 仅在本工作树执行并成功。loopback Uvicorn 已停止；未触碰外部服务。

每条命令的实际结果、原始日志和初始 RED 输出见 [evidence](evidence/2026-10-13-m3-package-2-c19-dsh-repair-1-0a1b8dc/README.md)。

## 范围与后续

实现只修改 `planner.py`、`query.py` 和新增的 `test_c19_topic_scope_normalization.py`；本轮不开发包 1 / 包 3功能。历史 QA / DSH 报告和 evidence 均未改写。真实 provider、飞书、凭据 / Keychain、真实材料、native / DMG、五日 / 双机、发布与 runtime 检查为 **NOT_RUN / UNVERIFIED**。

下一步由 Sol 在隔离 checkout 对固定源码 SHA `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 启动全新独立 QA。Developer 不启动 QA、不宣布 C19 / 包 2 / M3 通过，也不合并或推送。
