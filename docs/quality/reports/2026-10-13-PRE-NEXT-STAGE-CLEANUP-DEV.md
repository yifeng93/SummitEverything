# 2026-10-13 清理维护 DEV 记录

## 范围与固定基线

Developer 在 `codex/maintenance-cleanup-20261013` 上，从本轮清理前 main `879c82464903a7aed91b30955d7355064fa85088` 开始。产品 M3 用户批准合并点仍是 `47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`；C19 固定源码 `0a1b8dc94a5d8f797161c38430dccfcb211a9e07` 的既有 QA 只覆盖该历史源码。本轮新 SHA 必须由独立 QA 验收，不能沿用 M3 报告作为本轮通过证明。

本轮目标是减少已证实未调用代码、收拢相互冲突的当前文档入口，并清理已完成项目的临时工作树 / 本地分支。未添加功能、未改产品契约与测试期望、未移除任何原始 QA 报告或 evidence；M3 parser 不做整体重构。

## 实际变更

- `src/summit_everything/intake/review.py`：移除 `IntakeReviewService._load_items` 的 3 行未调用私有薄封装，并移除唯一因其删除而变未用的 `IntakeItem` import。保留 `_ResponseStream.__aiter__` 协议入口。AST / 全仓文本候选范围与反射、导出、注册、fixture、API 及协议入口排除见 [死代码审计](evidence/2026-10-13-cleanup-dev/dead-code-audit.json)。删除前固定源码的 `git grep` 只有 `_load_items` 定义一处；Sol 复核并批准该删除。首次 Ruff 报 F401 后仅移除该 import，后续 Ruff exit 0；完整初次与最终运行日志均保留。
- 更新 README、进度账本、最新交接、验收矩阵、报告索引、架构 / API / 工作库契约与全 v1 / M3 计划，让当前 M3 离线验收 PASS 和仍未测的真实 / M4/M5 门一致。全 v1 计划的已完成 M1/M2/M3 文件清单按当前仓库模块修正；M4/M5 的文件位置仍是计划。旧逐轮状态保存到有明确历史标记的副本，产品规格、验收 MUST、两个验收者判定规则和原始历史证据保留。
- DSH-C19 从当前入口移至历史交接，旧路径保留短 redirect；M3 历史收尾与本次恢复记录新建。历史 QA 中三个绝对路径仍指向已删除临时 checkout，未改写不可变报告；其固定 Git 对象可从本机恢复 bundle / refs 找回。
- 删除盘点中的 12 个 clean 旧工作树与五条过期 local branches。删除前按清单核对 HEAD / clean 状态；分支以 expected-OID 比对删除。远端 C03 pilot 删除由 Sol 执行并留 raw receipt，本 DEV 没有改远端 refs。
- 清理本任务工作树中 19 项测试缓存和构建产物（`dist`、`web/dist`、pytest / mypy / Ruff cache、Python `__pycache__`）。本工作树无 `.local`；保留其有效 `.venv` 与 `web/node_modules`。主 checkout 的私有 `.local/archives`、其他项目、`_vault`、真实资料、凭据与安装应用没有改动。

## 验收事实与边界

本任务自身不是独立验收。Developer 自测观察如下；Sol 判断门状态，Fresh QA 对完整固定提交复验后才可记 QA PASS。

| 检查 | 观察结果 |
|---|---|
| Guarded backend | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`：491 passed，exit 0；有一条已有 Starlette/httpx 弃用 warning |
| Web | `npm --prefix web test`：12 files、56 tests passed，exit 0 |
| Ruff | 最初因 unused `IntakeItem` 报 F401；移除该 import 后 `uv run ruff check src tests` exit 0。`uv run ruff format --check src tests`：79 files already formatted，exit 0 |
| Python 静态 / packaging | `uv run mypy src` 成功；`uv lock --check` 成功；最终源码再次 `uv build` 成功 |
| Web 静态 / build | typecheck、lint、build exit 0。Lint 保留两个既有 `react(set-state-in-effect)` warning（TodayView、ProjectsView） |
| API 契约生成 | 曾在工作树执行 `npm --prefix web run api:types`，exit 0，OpenAPI / TS 文件与命令前逐字节相同；这项单独称为工作树再生成稳定性。另在系统临时目录复制 exporter 和当前 `summit_everything` 包，隔离生成 OpenAPI 与 TypeScript，两个命令均 exit 0，临时输出与 tracked `web/openapi.json`、`web/src/api/generated.ts` 完全一致。临时目录由 `TemporaryDirectory` 自动清理；隔离命令 / 输出 SHA 见 evidence |
| Markdown 链接 | 扫描 187 个 Markdown 文件；项目内相对链接缺失数为 0。剩下三个失效的旧绝对 checkout 路径只在不可变历史 QA 报告中，已在历史索引说明；它们不属于 repo-relative link failure |
| 原始验收证据 | 对清理前 main 的 `docs/quality/reports/` 全部 1,762 个 tracked 文件逐字节比较，跳过有意重写的 `reports/README.md` 后比较 1,761 个，mismatch 为 0。原始 QA 报告、manifest、签名 / SHA 清单及 evidence 未改 |
| 本机恢复包 / 目录 | 盘点中 12 个旧 checkout 实际不存在，12 个 cleanup tags 与各预期 HEAD 一致；11 个有 `.local` 的旧树 tar SHA 与私有清单一致，`m3-integrated-packages` 没有 `.local`。bundle `SHA256=8efc21cfb4065766a91ec34791ecf9a18c3a36359b3841c03b8dcececf3bf6e3`，`git bundle verify` exit 0。私有目录 `0700`、恢复包 `0600`。重复 `SummitEverything-local.tar.gz` 的逐文件内容与规范 C03 pilot tar 一致，故只删除重复副本；保留规范 tar。已有额外 ref `archive/cleanup-2026-10-13/SummitEverything` 指向 `2251ec8`，保留且不算入 12 个新 cleanup tags |
| 主 checkout 与 refs | 主 checkout `879c824` 保持 clean；Git 当前仅 `main` 与本任务 branch 两个本地 branch、两个 worktree（主 checkout 和本维护 checkout）。Sol 报告远端只剩 main，并留有 C03 branch 删除 exit 0 回执 |

测试使用合成 / 离线边界；没有启服务或浏览器，没有调用付费 smoke、真实 provider / Feishu / 业务材料 / OS Keychain，也没有打开真实材料。runtime 元数据仍 UNVERIFIED。已知 `scripts/run_dev.py` Ctrl+C 清理可能 `PermissionError` / exit 1，本轮未改此行为。

## 独立 QA

**DEV 自测不是 QA 结论。** fresh QA 尚未在此 DEV 记录写入；请 Sol 以本次提交的完整 SHA 建立独立 checkout，并按 `docs/handoff/TESTER.md`、`docs/quality/ACCEPTANCE.md` 和 cleanup handoff 验收。QA 需确认产品源码仅有获批的私有 helper / import 删除，文档与本机清理证据完整，原始历史证据字节不变。真实 / M4/M5 门依旧 NOT_RUN；runtime 为 UNVERIFIED。

完整命令原始输出、退出码、隔离生成比较、链接 / 死代码审计、immutability hash 比较与目录恢复验证位于 [DEV evidence](evidence/2026-10-13-cleanup-dev/)。
