# 最新实现交接

## M2 阶段 A — Fake-only 整改与独立复验

- **当前代码 SHA：** `32da67e9c0280e3dae18fd374e30c925565b0b82`，分支 `codex/m2-stage-a-closeout`，基线为原 M2 交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。
- **原候选：** `09398fcae597b2478001d40aedf580ea91322c11`。原候选 QA 测试与报告提交 `f64c565b7c5105867e0c19e7e1e716dc726f8ff7`；A-01 P0、A-02–A-04 P1、A-05 P2 复现结果见 [原候选定向 QA](../quality/reports/2026-10-10-M2-stage-a-original-qa.md)。报告结论保持原样。
- **当前状态：** Fake-only M2.1–M2.3 阶段 A 已由独立 QA 在固定代码 SHA `32da67e9c0280e3dae18fd374e30c925565b0b82` 复验通过；最终报告提交 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`。原候选缺陷初验及后续各轮复验报告均保留，结论与受测 SHA 对应。
- **初始文档 checkpoint：** M2 核心规格 checkpoint `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`；执行交接头 `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb`。本阶段更新文档将在修复代码之后单独提交；它不改变受测代码 SHA。
- **自测摘要：** Python 142 passed；Web 8 files / 32 tests；Ruff、format、mypy、lock、uv build、OpenAPI 类型生成、typecheck、lint、web build 与 Swift build 退出 0。保留 1 条既有 Starlette/httpx 弃用警告和 3 条既有 React effect lint 警告。以上不是独立 QA 结论。
- **独立验收摘要：** A-01–A-05 与阶段 A Fake-only MUST 场景通过；未关闭 P0/P1/P2=0。浏览器 Fake 流程和 console、原生开发壳归属 / 窗口 / Quit / 退出清理均有独立报告和证据。API 没有 OAuth cancel UI 控件的变体记 NOT_RUN，API denial 已覆盖。
- **边界与待办：** 当前正在进行合并前审查、PR、main 合并与独立 main checkout 复核；这些完成前不宣告阶段 A 完整闭环。
- **真实门：** 当前只有 Fake providers；本轮未访问真实 Feishu、付费模型、真实业务材料或 Keychain，未执行 DMG、五日或双机验证。用户备好的真实资源未被消费；真实门继续 NOT_RUN。
- **阶段边界：** 未启动 M3–M5；阶段 A 结束后等待用户将最终报告交独立技术评定者，再决定阶段 B/C。

以下 `M1` 区域为历史交接记录。

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

此处保留阶段 A 开始前的历史交接状态：当时 M2.1–M2.3 等待固定 SHA 独立 QA，原代码 SHA 为 `09398fcae597b2478001d40aedf580ea91322c11`，核心文档 checkpoint 为 `0f8e61bd1f0523f7cb93d04ef4eddf4d2f6a25d4`。最新阶段状态见本文件顶部；真实资源的边界与 M3–M5 暂缓决议仍有效。
