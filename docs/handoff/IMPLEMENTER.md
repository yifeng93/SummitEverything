# 实现者手册

你的职责：按当前任务和已确认规格实现、自测、固定源码 SHA，并交给 Sol 做独立 QA 调度和最终判门。用户已授权通用代码开发；仍须遵守当前任务的范围与外部操作授权。

## 开始前

1. 读取 [AGENTS.md](../../AGENTS.md)、[PROGRESS](../implementation/PROGRESS.md)、[LATEST-IMPLEMENTATION](LATEST-IMPLEMENTATION.md) 和任务指定的规格、契约与验收标准。
2. 核对真实 HEAD、分支和工作区；使用任务要求的隔离 worktree。保留他人修改，不覆盖或撤销其工作。
3. 按需阅读本手册所引用的完整实施计划。已完成阶段的旧提示词、旧 SHA 和历史 QA 结论只供追溯，不能作为当前指令。

## 实现与自测

- 先验证相关契约与失败路径，再做最小可维护改动。业务、文件和索引路径保持真实，仅在边界处替代外部服务。
- 使用合成内容、Fake provider 和隔离临时工作库。不得读取或提交未经批准的真实业务材料，不得接触真实凭据、外部服务或安装应用，除非当前任务明确授权。
- 用户确认是正式知识写入门；任务及项目进度动作各自独立确认。资格判断统一调用 `domain/content.py`。
- README 提供常用检查入口；详细命令、首次安装和 Internal 构建步骤以本手册为准。新增真实运行命令时同步更新 README 与相关手册。
- 记录命令、真实退出码、证据位置、模拟/真实边界、未测项与已知问题。测试通过不等于阶段验收通过。

### 本地开发与检查命令

在仓库根目录执行；首次跑 dev runner 前先装 Web 依赖：

```sh
uv sync --locked --group dev
(cd web && npm ci)
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
swift test --package-path native
npm --prefix web test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

启动 WebUI：`uv run python scripts/run_dev.py`，浏览器打开 `http://127.0.0.1:5173`。默认使用 Fake provider 和隔离工作库。

仅在 arm64 macOS 构建机器上构建 Internal 候选。产物路径必须是全新路径；脚本会强制构建 WebUI、打包并校验 bundle/DMG，不会安装或覆盖应用：

```sh
uv sync --locked --group dev --group build
npm --prefix web ci
scripts/release-macos.sh "$PWD/.local/dev/m41/artifacts/SummitEverything Internal.app" "$PWD/.local/dev/m41/artifacts/SummitEverything-Internal.dmg"
```

## 本机检索索引

本地索引由 SQLite 状态/活动代指针和 profile 内嵌入式 LanceDB 组成。旧 SQLite `vector_json` 不自动迁移或作为证据；用户通过已确认 Markdown 的索引预览/执行路径显式重建。不要在开发命令中默认清理或重建已有 profile。

```sh
uv run python scripts/inspect_index.py --json
uv run python scripts/prune_local_index.py --index-db "/actual/profile/path/index.sqlite3" --app-stopped
```

检查脚本只读；generation 清理要求应用完全退出，保留活动代和最近一个旧代，不移除旧 SQLite chunk 行。

## 固定交接

1. 对照任务和 [ACCEPTANCE](../quality/ACCEPTANCE.md) 检查覆盖项。
2. 完成自测，检查差异和工作区，提交小逻辑变更，取得完整 clean SHA。
3. 更新 [PROGRESS](../implementation/PROGRESS.md) 中的当前状态；[LATEST-IMPLEMENTATION](LATEST-IMPLEMENTATION.md) 只写当前任务、固定 SHA、QA 所需指令及状态链接。
4. 将完整 SHA、范围、命令退出码、复演说明、限制和 DEV 报告交 Sol。由全新 QA 在独立 checkout 对固定 SHA 验收，Developer 不得自判 QA 或阶段通过。

QA 首轮失败后，最多自动修复两轮；每轮使用新 SHA 和 fresh QA。两轮后仍未通过则停止并交 Sol 请用户决定。不得删除测试、降低验收门或把未测项写成通过。

真实 provider、飞书、业务材料、OS Keychain、用户安装/公证、五日试用、双机与发布均按各自授权和证据单独验收。未观察到的 runtime 配置记为 UNVERIFIED；缺授权或凭据时记录 NOT_RUN / BLOCKED 并继续独立工作。
