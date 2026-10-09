# 初始框架核验记录

日期：2026-10-09。角色：框架建立者自检，**尚未由另一 Luna 独立验收**。

## 被测版本与范围

基础代码提交：949f0b0d2af5362091630f0b49f4c70eb59740d0，分支 codex/project-foundation。后续文档提交未改该源码和测试；此记录不追逐文档自身 HEAD。

范围仅为内容 canonical hash、来源 / 稿件排除、批准与当前版本绑定、缓存版本检查，以及 Python 工程工具。运行目录为 SummitEverything，使用本项目 .venv 和隔离合成数据。

## 实际检查

| 命令 | 退出码 | 实际结果 |
|---|---|---|
| uv run pytest -q | 0 | 22 passed |
| uv run ruff check src tests | 0 | All checks passed |
| uv run ruff format --check src tests | 0 | 4 files already formatted |
| uv run mypy src | 0 | 3 source files，无类型错误 |
| uv lock --check | 0 | 依赖锁一致 |
| uv build | 0 | sdist 和 wheel 构建成功，仅 Python 包，不是 DMG |
| git diff --cached --check | 0 | 基础代码提交无空白错误 |
| 一次性 Python 文档链接检查 | 0 | 22 份 Markdown，34 个本地链接，0 个失效目标 |

测试先在没有实现的状态实际失败，再实现并通过。hash fixture 依据独立 UTF-8 JSON 字节配方预先计算，不用被测 hash 函数生成基准答案。

额外对源码做三次**仅内存**变异，每次使用独立 Python 进程装载变体再运行对应 pytest：

- 去掉存储区排除：3 个 source / draft / system 反例失败，pytest 退出 1。
- 去掉批准 hash 比较：外部改正文的反例失败，pytest 退出 1。
- 去掉缓存版本比较：新版本重新批准、旧缓存仍存在的反例失败，pytest 退出 1。

变异核验脚本确认三次均被检出后退出 0；没有改动磁盘上的受测源文件。证明这些测试能发现关键保护被移除，不能证明未来 reader / route 已正确调用它们。

文档本地链接另以一次性 Python 检查：按 Markdown 所在目录解析相对目标，排除 HTTP / mailto 和页内锚点，验证目标存在。复用地图同时核对旧仓库的实际模块路径；未调用旧应用。

## 审阅结果和限度

核对了规格、契约、分阶段计划与验收矩阵。补清 OAuth 回调的单次 state 认证例外、手动动作候选入口、共用 writer 的建立顺序，以及 M4 / M5 验收范围。

基础模块没有 I/O、网络、秘密或签发批准能力。完整 UUID / frontmatter 验证、真实路径分类、用户确认、事务、索引、HTTP、UI 与包尚未实现，必须在 M1 及后续阶段验收。

未调用真实模型、创建飞书任务、初始化真实样板或改写旧工作库。M1–M5、真实账户质量、场地与酒店业务、五日试用和双机均未通过；详见 PROGRESS 与 LATEST-IMPLEMENTATION。

下一步：执行 Luna 从 M1.1 开始，用隔离模拟材料推进到 M1 DEV 交接；另一 Luna 用固定提交独立验收。
