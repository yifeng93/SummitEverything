# API key 形状校验修复 — Developer 记录

日期：2026-10-17
分支：`codex/credential-key-shape-20261017`
基线：`e1bbcee0f9e3e71e077e813db360cb3b802b57c3`（main）
产品修复提交：`f1f0982be75aadd9a74021a7ee5641317ddc2113`

## 现象

用户在首次配置向导第 2 步填入两把真实 key：

- DeepSeek key 通过校验。
- 阿里云百炼 / Model Studio key 被 422 拒绝，界面显示
  “这不像一把 API key：请确认它以 sk- 开头，且不含空格或换行。”

本地只读诊断显示该百炼 key：

- 以 `sk-` 开头，长度 117；
- 不含空白、控制字符、引号、非 ASCII 或零宽字符；
- 含 3 个 `.`（JWT 风格点分隔），因此不匹配旧白名单。

## 根因

`src/summit_everything/api/app.py` 的 `_API_KEY_SHAPE` 只允许
`sk-[A-Za-z0-9_-]{16,}`。真实 Model Studio key 使用点分隔格式，被过窄的
字符类误判，而不是用户输入错误。

同一过窄字符类还存在于两处日志/错误脱敏规则中：

- `src/summit_everything/local/event_log.py`
- `src/summit_everything/integrations/http_boundary.py`

如果只放宽写入校验而不同步脱敏，含点 key 在诊断日志和 provider 错误文案中
只会被截断到第一个点之前，留下可读片段。

## 修改

- 校验改为 `sk-[\x21-\x7e]{16,}`：`sk-` 前缀 + 至少 16 个单行可见 ASCII 字符；
  保留 512 字符上限；额外拒绝引号/反引号/中文引号，避免把粘贴包裹符存进钥匙串。
- 两处脱敏规则同步改为 `sk-[\x21-\x7e]{8,}`，点分隔 key 作为整体替换为 `sk-***`。
- 错误文案补充“或引号”。
- 新增回归：
  - `tests/integration/test_provider_failure_visibility.py`：点分隔、`+/=`、长点分隔 key 通过；零宽字符、内部引号、500+ 字符仍 422。
  - `tests/unit/test_profile_event_log.py`：点分隔 key 在诊断日志中整体遮蔽，无片段残留。
  - `tests/unit/test_provider_error_reporting.py`：provider 错误文案中的点分隔 key 整体遮蔽。

## 验证（本机 arm64 macOS 27.0.1）

| 检查 | 结果 |
|---|---|
| 定向 pytest（3 个文件） | 54 passed |
| 全量 pytest | 719 passed，1 条既有 Starlette/httpx 弃用 warning |
| `ruff check src tests` | exit 0 |
| `ruff format --check src tests` | exit 0（101 files） |
| `mypy src` | exit 0（47 files） |
| 内部 App/DMG 构建 | release、strict codesign、hdiutil verify 均 exit 0 |
| packaged smoke | PASS（空 PATH、身份、静态 UI、认证边界、端口冲突、父管道清理） |

构建身份：

- `source_sha=f1f0982be75aadd9a74021a7ee5641317ddc2113`
- `dirty=false`
- DMG：`.local/internal-builds/f1f0982-20261017/SummitEverything-Internal-f1f0982.dmg`
- DMG SHA-256：`b8c725765dbf2590dc9a493bf3053248624278551fe7a084f48304431806dc4b`

## 边界

- 本轮只修复 key 形状门禁，没有调用真实 provider；两把 key 的账户有效性、权限、
  配额与账单仍由用户点击应用内连接检查单独验证。
- 真实 provider / 飞书 / Keychain 生命周期 / 安装与公证 / 五日 / 双机 / 发布仍按
  PROGRESS 标为 NOT_RUN。
- 未执行独立 QA，未合并、未推送；分支与构建产物保留，供用户在应用内复验。
- 用户真实 key 未写入本报告、源码、测试或 Git；诊断脚本只输出长度和字符类别。
