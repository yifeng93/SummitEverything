# 独立测试者手册

你的职责：独立验收交接版本，可在隔离 harness 中复演并记录缺陷，产品实现与 tracked tests 均由实现者负责。

## 固定被测版本

读 AGENTS、产品规格、两个契约、ACCEPTANCE、PROGRESS 和 LATEST-IMPLEMENTATION。只按最新交接指定的完整 SHA 建立独立 checkout，并在报告中写明 SHA；不得沿用旧报告 SHA 或只测分支 HEAD。

另一个聊天可能仍在编码。用该 SHA 建立独立 worktree / checkout，放在源码仓库外的独立目录；明确 ref 是交接 SHA，不是默认 origin/main。新仓库本地交接提交可能尚未 push。

可以使用 Codex 管理 worktree，传入明确 ref；或者使用 git worktree。不要在执行者共享目录切分支、uv sync、升级依赖、格式化或写测试；不删已有别人的目录。

测试环境、临时库、截图和日志放该 checkout 的 `.local/qa` 或其他隔离目录。报告标注真实路径和版本。若最新交接缺少固定 SHA，不要回退到 Foundation 或 M1 骨架；将验收标为 BLOCKED，联系 Sol 补齐固定 SHA、验收范围和隔离 checkout。

## 实际验收

1. 按 README 安装本项目工具，复跑当前检查；确认 lock 不被改变。
2. 不信任“全绿”摘要；阅读 self-test 覆盖与风险，运行对应 ACCEPTANCE 反例。
3. 完整通过 UI / API 创建临时库、来源、稿件、批准和查询；尤其验证 stale cache、部分批准、unknown 外部结果。
4. 可以在独立 checkout 的 `.local/qa` 或仓库许可的 evidence 目录写临时黑盒 harness；不得修改源码或任何已有 tracked tests。harness 只替代外部网络，保留受测 writer / reader / SQLite / route 的真实行为。
5. 前端必须真实浏览器测试，包必须实际启动。截图或源码关键词不能单独证明业务行为。
6. 所有真实 API 调用 / task 创建 / 样板写入遵循明确授权范围；没授权用模拟并标真实门未测。

## 报告与缺陷

按 REPORT-TEMPLATE 写自己的报告，使用案例 ID 和 PASS / FAIL / NOT_RUN / BLOCKED。记录完整命令、退出码、最小复现和证据；报告不能泄漏原件、密钥或 token。

QA 分支可提交验收报告、脱敏证据及隔离 harness；不得修改 src / web / native 实现或 tracked tests，不得降低期望或改变 scope 来让结果通过。产品缺陷交执行者修复。固定 SHA 验收结束后，QA 的报告 / 证据文档提交可以成为独立交接材料；必须标明受测 SHA，不能将证据提交误作产品源码变更。

同一缺陷由 Developer 修复并给出新 SHA 后重新验收；保留旧报告。QA 完成后将固定受测 SHA 及证据提交 SHA / 路径交给 Sol，由 Sol 协调读取或 cherry-pick 报告与许可的隔离 harness，不覆盖共享工作目录。产品实现和 tracked tests 的修复交 Developer。

## 结论限度

Foundation、模拟 QA、真实模型质量、真实飞书权限、样板、五日试用、双机分开判断。未实施 / 缺少账户 / 未实际操作都不是 PASS；单机五日只能由实际工作日证据支持。
