# 最新实现交接

## M2.1–M2.3 最终 DEV 固定候选

- **代码 SHA：** `09398fcae597b2478001d40aedf580ea91322c11`；分支 `codex/m2-feishu-actions-journal`；基线 `393e63ac95be3ebbee916fcd2c911ed3dec8e86d`。
- **状态：** DEV完成待独立验收。M2.1 / M2.2 的窄范围代码审查已完成；M2.2 P2 空白核实依据已修复并复核。自动检查与实际 WebUI 复演记录在 [M2 DEV 报告](../quality/reports/2026-10-10-M2-DEV.md)。
- **文档 checkpoint：** 本文件和 M2 实施 / 验收记录在独立 docs commit；提交后 docs SHA 由本文件末尾补记。
- **验证摘要：** 后端 135 passed；Web 8 个文件 / 31 测试 passed；ruff / format / mypy / lock / uv build、OpenAPI 类型生成、前端 typecheck / lint / build、Swift build 通过。保留 1 条既有 Starlette/httpx deprecation 和 3 条既有 React effect lint warnings。
- **边界：** WebUI 主流程与 unknown 故障恢复已实际复演；原生壳 UI 因同名 QA checkout 窗口归属冲突未验证。Fake-only，没有访问真实 Feishu、模型或业务材料，也没有创建真实任务。没有 push / PR / merge，没有启动 M3–M5。
- **独立 QA 交接：** 另建 checkout/worktree 并固定到上面代码 SHA。不得在此共同目录切换分支或修改实现；使用 [TESTER 手册](TESTER.md)、[验收矩阵](../quality/ACCEPTANCE.md) 和 M2 DEV 报告。原生壳 UI 需由独立验收者在能确认路径属于本固定候选的窗口补测。

下文保留 M1 独立 QA 历史。

## 固定候选

- **阶段：** M1.1–M1.5 DEV、独立模拟验收及 main 合并后检查均通过。
- **首次 QA 固定代码 SHA：** `73ec81a06f2557c006f98ff88fa81b08d14ef315`。
- **当前修复候选代码 SHA：** `f349fe6cb5da86c3fdafff11738e2a55335d8874`。
- **合并提交：** `4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`（PR #1，merge commit；远端 `main` 已包含受测代码）。
- **分支：** `codex/m1-close`。
- **材料边界：** 只用隔离模拟工作库与 Fake providers；没有导入真实“场地与酒店”材料、付费模型或真实飞书。
- **DEV 自测记录：** [2026-10-09-M1-close-DEV.md](../quality/reports/2026-10-09-M1-close-DEV.md)（已提交，不是独立 QA 报告）。详细隔离运行记录另保存在 ignored `.local/m1-close/evidence/dev-self-check.md`。
- **独立 QA：** 首轮发现 C03 P1，已由执行者修复；同一 QA 在新 checkout 的 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 上复验通过。报告：[首次失败记录](../quality/reports/2026-10-09-M1-close-73ec81a.md)、[最终复验报告](../quality/reports/2026-10-09-M1-close-retest-f349fe6.md)。M1 模拟范围 P0/P1=0；报告记录 1 个 P2 英文删除拒绝提示及后续本地化安排。
- **合并后验证：** 在远端 `main` merge commit 的独立 checkout 上，后端 77 项、前端 10 项、OpenAPI 类型生成、类型 / lint / 构建、lock、uv build 与 Swift build 全通过；远端 `main` 包含受测 SHA 与两份 QA 报告。

## 修复摘要

- 修复 C05：来源状态由最新整理作业和关联稿件派生并持久化，覆盖 pending、processing、reviewing、completed、failed、cancelled；正在整理或仍有待审稿的来源不能用新 operation ID 另起作业。失败、取消或全部处理完成后，只有显式 `reprocess=true` 才能重新整理；相同 operation ID 按原意图幂等重试。
- C06：用户先选一个项目，一份多主题来源可生成多份稿件，逐份确认并保持完整来源关联；不进行自动跨项目分流。
- C07：未决或选择结果会写入最终正文，未决内容明确标为未确定；稿件编辑区预览结果。
- C08/C10：真实 UI 显示外部版本差异、阻止覆盖；保留稿件、显式比较基准、重新确认后，索引重建并恢复最新正文检索。
- C03/C13/C14 的 M1 部分：既有测试覆盖归档知识检索、非空删除保护、失效 / 被替代内容区分、SSE 顺序 / 唯一终态 / 取消不伪装完成。
- C03 初次 QA 暴露的界面缺口已修复：稳定 ID 重命名、归档项目查看 / 恢复、仅空目录可删除、页面移动及新增相对链接后明确确认。新增 ProjectsView / PageReader 界面回归；QA 已在真实浏览器复验移动、引用修复和链接确认。
- C11/C12/C23 的 M1 部分：旧版本资格门、邻页复核、索引 fingerprint 变化与失败重建保护、原子写恢复和同意图重试由自动测试覆盖；QA 已对固定候选完成 M1 范围复验。
- 本地开发壳：API / Web 端口与 profile 可隔离；run identity 防止误连其它 checkout 服务；runner 只清理自己启动的进程组。正常 Quit、最后窗口关闭、`swift run` Ctrl+C 均以本轮独立端口复演并确认无监听残留。

## 启动与检查

```sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
```

默认 API `127.0.0.1:8793`、Web `127.0.0.1:5173`。并发隔离可设 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT`、`SUMMIT_API_TARGET`、`SUMMIT_PROFILE_ROOT`。访问 `http://127.0.0.1:5173`。原生开发壳：`cd native && swift run`。

固定修复候选 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 与合并后的 main 树均完整复跑：后端 77 passed；前端 5 个测试文件 / 10 项测试；OpenAPI 类型生成、typecheck、lint、production build、ruff check / format、mypy、lock check、uv build、Swift build 均退出 0。保留 1 条 Starlette/httpx 弃用提示及 3 条既有 React effect lint 警告。

## 真实 UI 复演

完整隔离路径和步骤见 DEV 自测证据。真实浏览器复演覆盖 C06 的单项目多稿、部分与全部确认；C10 外部编辑、旧证据失效、重新确认及增量索引恢复；C08 目标外部变化的冲突保护、稿件保存 / 重新确认及最新正文检索。材料全部是本地合成文本。

## 尚未完成或未测

- M1 独立模拟验收已通过，详情按案例见最终复验报告。受测实现固定 SHA 为 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；执行者后续提交均为文档和 QA 报告导入。
- C13 历史会话 UI、C14 断流恢复 / 历史引用 UI 属 M3；C25 DMG、干净机器安装和发版身份属 M4；均不得记作 M1 PASS。
- 真实“场地与酒店”材料确认、真实模型质量、真实飞书权限 / 写入、五个实际工作日、双机往返未测且需要各自授权门。
- 1 条 Starlette/httpx 弃用提示和 3 条前端 effect lint 警告保留；未通过隐藏警告或降低期望获得绿灯。

## 合并后检查记录

- PR：[SummitEverything M1 closeout](https://github.com/yifeng93/SummitEverything/pull/1)，以 merge commit 合并至 `main`。
- 合并提交 SHA：`4ca3fffb696bbe57622dda8c82eb9ed6b6e3d6aa`；已确认该树包含受测代码 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 和 QA 报告提交 `0fd0102ad8a22fae336339e7fd635acc15438224` / `49ce008446339c723b83ee39cfe3e2ae029b4437`。
- 在该 main 树复跑：后端 77 passed，ruff check / format、mypy、`uv lock --check`、`uv build`、OpenAPI 类型生成、前端 10 tests、typecheck、lint、production build、Swift build 均退出码 0。保留 Starlette/httpx deprecation 和 3 条既有 React effect lint 警告。
- 合并后服务端口和 UI 服务均未启动；真实材料、模型、飞书、DMG 与多设备门仍未测。

## QA 交接

独立验收在源码仓库外的 `/Users/yifengstudio/.codex/worktrees/qa-m1-close-r3` 固定到 `f349fe6cb5da86c3fdafff11738e2a55335d8874`。报告与隔离模拟 UI 证据已保存；不修改产品实现。M2/M3/M4/M5 场景和真实外部门按最终复验报告保持 NOT_RUN。

## 下一阶段

M1 已收口；M2.1–M2.3 的 Fake-only 开发自测与 WebUI 复演完成，等待固定 SHA 独立 QA。M2.2 审查 P2 已修复，M2.3 UI 误标也已修复；代码 SHA `09398fcae597b2478001d40aedf580ea91322c11`。独立 docs SHA：见最终文档提交后补记。真实飞书读取、写入与权限核验仍未完成；执行前需用户明确指定材料范围和动作。不要启动 M3–M5。
