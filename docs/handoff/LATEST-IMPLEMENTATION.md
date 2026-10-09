# 最新实现交接

## 固定候选

- **阶段：** M1.1–M1.5 DEV 收口；首次独立 QA 发现 C03 P1，已修复并交固定提交复验。
- **首次 QA 固定代码 SHA：** `73ec81a06f2557c006f98ff88fa81b08d14ef315`。
- **当前修复候选代码 SHA：** `f349fe6cb5da86c3fdafff11738e2a55335d8874`。
- **分支：** `codex/m1-close`。
- **材料边界：** 只用隔离模拟工作库与 Fake providers；没有导入真实“场地与酒店”材料、付费模型或真实飞书。
- **DEV 自测记录：** [2026-10-09-M1-close-DEV.md](../quality/reports/2026-10-09-M1-close-DEV.md)（已提交，不是独立 QA 报告）。详细隔离运行记录另保存在 ignored `.local/m1-close/evidence/dev-self-check.md`。
- **独立 QA：** 首次报告已提交 QA 分支，发现 C03 真实界面缺少主线 / 项目重命名、归档、删除及页面移动 / 链接，结论 FAIL/P1。当前 SHA 已补齐界面，由同一 QA 在新 checkout 复验。报告导入与最终 addendum 待复验完成。

## 修复摘要

- 修复 C05：来源状态由最新整理作业和关联稿件派生并持久化，覆盖 pending、processing、reviewing、completed、failed、cancelled；正在整理或仍有待审稿的来源不能用新 operation ID 另起作业。失败、取消或全部处理完成后，只有显式 `reprocess=true` 才能重新整理；相同 operation ID 按原意图幂等重试。
- C06：用户先选一个项目，一份多主题来源可生成多份稿件，逐份确认并保持完整来源关联；不进行自动跨项目分流。
- C07：未决或选择结果会写入最终正文，未决内容明确标为未确定；稿件编辑区预览结果。
- C08/C10：真实 UI 显示外部版本差异、阻止覆盖；保留稿件、显式比较基准、重新确认后，索引重建并恢复最新正文检索。
- C03/C13/C14 的 M1 部分：既有测试覆盖归档知识检索、非空删除保护、失效 / 被替代内容区分、SSE 顺序 / 唯一终态 / 取消不伪装完成。
- C03 初次 QA 暴露的界面缺口已修复：稳定 ID 重命名、归档项目查看 / 恢复、仅空目录可删除、页面移动及新增相对链接后明确确认。新增 ProjectsView / PageReader 界面回归；QA 需浏览器独立复演移动与链接。
- C11/C12/C23 的 M1 部分：旧版本资格门、邻页复核、索引 fingerprint 变化与失败重建保护、原子写恢复和同意图重试由现有测试继续覆盖；需 QA 独立复验。
- 本地开发壳：API / Web 端口与 profile 可隔离；run identity 防止误连其它 checkout 服务；runner 只清理自己启动的进程组。正常 Quit、最后窗口关闭、`swift run` Ctrl+C 均以本轮独立端口复演并确认无监听残留。

## 启动与检查

```sh
uv sync --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
```

默认 API `127.0.0.1:8793`、Web `127.0.0.1:5173`。并发隔离可设 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT`、`SUMMIT_API_TARGET`、`SUMMIT_PROFILE_ROOT`。访问 `http://127.0.0.1:5173`。原生开发壳：`cd native && swift run`。

旧代码候选运行记录与退出码见 `.local/m1-close/evidence/dev-self-check.md`。固定修复代码候选 `f349fe6cb5da86c3fdafff11738e2a55335d8874` 的前端改动复验：前端 5 个测试文件 / 10 项测试、typecheck、lint、production build 均退出 0。其父提交 `34522507f2c5c9856ed859f0593e1967190cae41` 的后端 77 项、ruff / format、mypy、lock、sdist+wheel、OpenAPI 类型生成及 Swift build 均通过；最终 SHA 的完整门禁复跑待 QA 与最终 main 复验。保留 1 条 Starlette/httpx 弃用提示及 3 条既有 React effect lint 警告。

## 真实 UI 复演

完整隔离路径和步骤见 DEV 自测证据。真实浏览器复演覆盖 C06 的单项目多稿、部分与全部确认；C10 外部编辑、旧证据失效、重新确认及增量索引恢复；C08 目标外部变化的冲突保护、稿件保存 / 重新确认及最新正文检索。材料全部是本地合成文本。

## 尚未完成或未测

- 独立 QA 正在复验当前 SHA 的 M1 Foundation 基础门禁及 M1.1–M1.5 必测项；首次 QA 的 C03 P1 在复验通过前保持未关闭。
- QA 必须浏览器复验 C03 页面移动、既有链接修复与新增链接二次确认；并确认 C05、C06、C07、C08/C10、C11/C12、C13/C14 的 M1 部分、C23 原子恢复以及固定版本命令和原生服务归属。
- C13 历史会话 UI、C14 断流恢复 / 历史引用 UI 属 M3；C25 DMG、干净机器安装和发版身份属 M4；均不得记作 M1 PASS。
- 真实“场地与酒店”材料确认、真实模型质量、真实飞书权限 / 写入、五个实际工作日、双机往返未测且需要各自授权门。
- 1 条 Starlette/httpx 弃用提示和 3 条前端 effect lint 警告保留；未通过隐藏警告或降低期望获得绿灯。

## QA 交接

使用源码仓库外的独立 worktree / checkout，固定 ref 为 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；测试者只在自己的隔离目录使用模拟库 / profile、增补测试和新报告，不修改 `src/`、`web/`、`native/` 产品实现。读取 `docs/handoff/TESTER.md` 与 `docs/quality/ACCEPTANCE.md`，覆盖 Foundation 和 M1.1–M1.5 Must 场景，区分跨阶段已实现部分与 M3/M4 未测项。报告新建于 `docs/quality/reports/`，保留两份旧报告。若发现缺陷，把复现、严重度和证据交回执行者；修复后对新固定 SHA 复验修复项与相关回归。
