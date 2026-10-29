# 知识问答配置阻断与状态误报修复 — DEV（2026-10-29）

## 固定源码与隔离基线

- Developer 源码 SHA：`2e85af7ef580246b10d7d359849f2584a2bad0bb`。
- 合成基线 SHA：`f39c15b4f1a691757c92c214bf11eb11f5b9ce39`；由主目录 HEAD `b658aae82df80f2fce73ab728b5b04de02c699b8`、当时 tracked diff、必要的 `web/src` 与产品决策文件组成。该 commit 仅为隔离快照，不是用户成果；未复制 `.local`、真实凭据或真实资料。
- 分支：`codex/developer-query-provider-config-20261029`；worktree：`/Users/hanwenbo/.codex/worktrees/summit-ask-provider-config-20261029/SummitEverything`。
- 使用合成设置和 Mock/Fake 检查；没有调用真实模型、飞书、OS Keychain 或真实工作库，没有安装或重启应用。主目录未改文件、分支、依赖或配置。

## 修复内容

- 问答提交前按 Settings 返回的运行模式、模型选择、启用状态、密钥状态与钥匙串状态检查真实问答所需能力。缺项时按能力名称说明缺少项，显示「去设置」，保留原问题；不建立一次性计划、不发送问题、不自动切换离线模拟或启用模型。若计划预览或 `/queries` 在真实配置竞态中返回 provider-disabled，也提供同一设置恢复入口。
- 后端共用 provider 门禁保留原有 provider/enabled 判定，将通用内部错误改为具体中文能力与恢复说明；未增加预览路径上的钥匙串读取或改变真实执行的授权门。
- 将“没有引用”限定为正常完成的回答；设置读取/计划预览失败、请求状态未知、流中断分别呈现为尚未发送、结果未知或保留部分内容，不自动重发。SSE 正常完成后若对话历史回读失败，保持已有完成状态和答案。
- 索引状态有加载、读取失败、空、已读与陈旧状态；读取失败可重试，已有成功状态会保留并标注可能过时。
- 设置页的 Real/离线摘要和向量化诊断改用真实模式、provider、enabled、model 与密钥字段，修正“Real provider 已选择”和仅用非空 fingerprint 推断“已配置”的文案。同步了知识问答页面错误与恢复规格。

## DEV 验证

固定 SHA `2e85af7ef580246b10d7d359849f2584a2bad0bb` 的定向命令均退出码 `0`：

| 检查 | 结果 |
|---|---|
| `npm --prefix web test -- --run src/App.shell.test.tsx src/components/AskView.test.tsx src/components/SettingsView.cards.test.tsx src/components/SettingsView.regressions.test.tsx` | 4 个文件、57 tests passed |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" /Users/hanwenbo/ai/SummitEverything/.venv/bin/pytest -q tests/integration/test_provider_settings_api.py tests/integration/test_real_model_approval_flow.py tests/unit/test_acceptance_plan_ledger.py` | 20 passed；1 条 Starlette/httpx deprecation warning |
| `npm --prefix web run typecheck` | 通过 |
| `ruff check src/summit_everything/api/app.py tests/integration/test_provider_settings_api.py` | 通过 |
| `ruff format --check src/summit_everything/api/app.py tests/integration/test_provider_settings_api.py` | 2 files already formatted |
| `git diff --check`（提交前） | 通过 |

前端回归覆盖：三项 Real 服务仍处离线/未启用时就地指出缺项、保留问题并去设置，且不创建计划或 POST `/queries`；Settings 已变化时服务器计划门返回 409 的恢复入口；全配置 Real 仍经过预览、独立确认并只提交一次；缺终态的 SSE 保留部分且不自动重发；历史回读失败不改写已完成状态；索引读取加载、错误和显式重试；设置诊断状态文案。

定向原始日志在忽略目录 `.local/dev/evidence/ask-query-provider-config-20261029/`，本 SHA 的最终日志以 `fixed-sha-` 前缀命名。开发中曾试加 backend credential-vault 前置读取，Real adapter 定向测试暴露此举会改变所有计划预览并阻断现有 Mock runtime fixture；按范围复核已撤销该行为及相应 fixture 修改。早期失败日志原样保留，不作为本 SHA 的结果；最终固定 SHA 检查为上表命令。

## 边界与交接

- 本轮没有独立 QA、实际应用浏览器复验、真实 Keychain / 真实服务 / 安装包验证；这些门由独立 QA 或后续授权执行。
- 独立 QA 请固定复核 Developer SHA，重点验证输入往返设置、服务端配置竞态恢复、Real 预览确认、未知响应/流中断与索引读取失败恢复。已确认设置的真实模型质量、外部调用和运行时元数据仍未由本轮证明。
