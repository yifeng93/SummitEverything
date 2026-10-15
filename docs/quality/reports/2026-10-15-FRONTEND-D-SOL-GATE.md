# 前端 UX 里程碑 D repair1 · Sol 门判断

- 受测产品源码 SHA：`faa1edd611a74dcdc26bff234de810bdf47761cb`（父 `876008e1d33420f57fb31772c76e471379e6b98d`）。
- 本轮 docs 提交 `d390530`、`834695e`、以及本判断所在的 docs 提交都**不是**受测产品 SHA；`git diff faa1edd <docs tip> -- src tests web pyproject.toml uv.lock` 为空，受测产品树未被后续提交改动。
- 本判断基于：Developer 报告、QA 报告原件与 raw 日志、两处 QA checkout 的真实 `git status`/HEAD、真实退出码与计数、OpenAPI 复生成 diff，以及对本轮「检查被改写」问题的独立核对。

## 判定

| 范围 | 判定 |
|---|---|
| **repair1 的 P1（首配进度在重启后丢失 → 被拉回向导 step 2）** | **CLOSED**，限「真实 FastAPI + 生产 WebUI（`web/dist`）+ 真实后端进程重启 + 隔离 profile/工作库」范围 |
| repair1 离线前端范围（①–⑧ 项） | **PASS**（QA 自判 PASS；Sol 核对证据后同意） |
| **D 里程碑整个门** | **NOT PASS / 未完成** |
| 自动修复轮次 | 使用 **0/2**（初次 QA 即判限定范围 PASS，未触发修复轮） |

D 门之所以**不能**判 PASS：原始 P1 是在 **native WKWebView（nonPersistent 存储）** 中观察到的，而本轮按用户决定**没有**构建新候选 App/DMG，也没有启动原生 GUI，因此 native 同 profile 重启 **NOT_RUN**。浏览器 + 真实后端进程重启只能覆盖到「磁盘 durable 记录 + 落点判定」，不能替代 WKWebView 的存储语义。此外 876 的十条变异与全站视口矩阵本轮未重跑。

## Sol 的核对动作与结果

| 核对项 | 结果 |
|---|---|
| 受测 SHA 可解析且产品树自固定后未变 | ✅ `faa1edd` 是当前分支祖先；`faa1edd..HEAD` 只含 README 与 docs |
| Developer worktree `git status` | ✅ 空 |
| 两个 QA checkout 的 HEAD 与 clean 状态 | ✅ `frontend-d-qa-repair1` = `faa1edd`，`frontend-d-qa-repair1-parent` = `876008e`，均 `git status` 空 |
| QA 是否独立（未复用开发者测试） | ✅ QA 自建 3 个 harness（HTTP/浏览器/静态服务），未引用开发者测试文件 |
| harness 是否具备判别力（排除「太软」） | ✅ 同一 harness 在父 `876008e` 上 20 checks / 8 failed / exit 1，受测 SHA 上 64/64 / exit 0 |
| 计数与退出码 | ✅ Python 686、Web 220 passed / 0 todo、默认 e2e 2 passed、静态/buid/lock 全 exit 0，与 Developer 声称零差异 |
| lint warning 是否既存 | ✅ QA 在父 SHA 重跑确认为既存 2 条（`react(set-state-in-effect)`） |
| OpenAPI 门 | ✅ 复生成后与 tracked `openapi.json`、`generated.ts` 逐字节一致；diff +234/−0，无删除、无既有 schema 改动 |
| 是否触碰真实服务/凭据/安装/生产 | ✅ 无；offline guard 开启、隔离 profile/工作库、合成 defaults |
| 是否 push / merge / 删 branch 或 worktree | ✅ 无 |
| 证据是否含 token / 真实数据 | ✅ Sol 做凭据形状扫描无命中 |
| 「检查被改写」问题 | ✅ 已核实为**修正错误期望并加强断言**，不是降低验收门（详见下） |

### 对「HTTP harness 检查被改写」的独立核对

QA 最初把 `{"step": 3.0}` 列入「必须 422」并因此 exit 1；随后判定该期望写错（JSON Schema 的 `integer` 允许零小数部分的数字），于是：

- 把该用例改写成**更强的观察断言 A9b**：断言返回 200、落盘归一化为整数 `3`、磁盘上不出现浮点；
- 把 `bad_steps` 由 8 项扩为 9 项（新增 `-1`、`4.5`），总数 32→33 且全绿。

Sol 判定：这属于**修正错误的验收期望**，不是删测试或降低门；`bad_steps` 仍覆盖 `1/0/6/"3"/2.5/null/true/-1/4.5`，且新增的 A9b 比原先的错误期望更具体。

**同时记录一处证据处理瑕疵**：HTTP harness 那条最初失败的 raw 日志被后续 33/33 的运行覆盖，未像浏览器 harness 那样留档。该发现本身已被 D-4 记录并以 A9b 固定，故不改变判定；但按本项目「失败 raw 应保留或在报告中披露」的做法，本次报告未主动披露该覆盖，后续应避免覆盖原始失败日志。

## 缺陷处置

| 编号 | 级别 | Sol 处置 |
|---|---|---|
| D-1 pre-repair1 工作库再被 onboarding 一次，且关闭前 Today 不可达 | P3（非回归、自愈） | **待用户决议**：接受为已记录限制，或给「无记录但已配好」一条不遮 Today 的可区分落点（例如按 create/open 区分，或改为非阻塞提示）。属产品可见行为，不由 Sol 单方改动 |
| D-2 StrictMode dev 下迁移 PUT 发 2 次 | P3（dev 专属） | 已在 [D repair1 DEV 报告](2026-10-15-FRONTEND-D-DEV-REPAIR1.md) 收紧表述为「生产构建语义」；产品不改 |
| D-3 OpenAPI 未声明 401/404/503 | INFO | 记为本轮接受的限制，列为后续契约补全项 |
| D-4 `{"step": 3.0}` 归一化接受 | INFO（产品面不可达，已由 A9b 固定） | Sol **建议**在下一轮小修中收紧为「仅接受真整数」，使「非法 step 一律拒绝」的字面表述成立；是否立刻做取决于是否愿意再走一轮 fresh QA |

Developer 报告中原先过宽/偏轻的三处表述（非法 step 一律拒绝、老工作库只会「看到一次向导」、e2e 2/2 的覆盖范围）已按 QA 指正收紧，属 docs-only 更正，不改变受测产品 SHA。

## D 门还需要什么

1. **native 候选**：用户授权后按 [D repair1 交接](../../handoff/history/2026-10-15-NEXT-FRONTEND-D-REPAIR1.md) 的流程新建 managed build worktree + 全新 App/DMG，记录 source SHA / dirty=false / build ID / frontend 与 dependencies hash / DMG hash。
2. **native 同 profile 重启复验**：完成 → quit → 同 profile 重启 → 手动 open existing → 直接 Today；未完成 step 3/4 → 重启 → open existing → 原 step；明确 close → 重启 → 不弹、设置可手动续接。backend smoke 不能代替 WKWebView。
3. 可继承的 876 证据（十条变异、全站视口矩阵）需在报告中明确标注为「fixed tree unchanged」或按需重跑，不得冒充新 SHA 结果。
4. 真实 provider / OAuth / 飞书 / Keychain / 用户材料 / 安装 / 公证 / 五日 / 双机继续各自独立门，仍全部 NOT_RUN。

**结论一句话**：repair1 的 P1 在 API + 浏览器（生产构建）层**已修复并经独立对照验证**；但 D 里程碑门**未通过**，缺口是 native 候选与 WKWebView 同 profile 重启，另有 D-1（待用户决议）与 D-3/D-4（INFO）留档。
