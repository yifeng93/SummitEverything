# 独立 QA 证据：origin guard 的 SettingsError 行为（2026-10-14）

本目录保存对固定提交 `c9b3f7cc9af75d1bc46b9ab32e0950ba32995db9`（分支 `codex/origin-guard-error-20261014`）的独立 QA 可提交副本。原始文件位于该轮 QA 独立 worktree 的 `.local/qa/`（Git 忽略），副本未做改写。

- 原始路径：`~/.codex/worktrees/origin-guard-qa-c9b3f7c/SummitEverything/.local/qa/`
- 全部 `harness/*` 与 `raw/*` 的逐文件 SHA-256 清单摘要：`4ec529133362943c046888ffc4f8327eca2bc7b1c94c70c97cfca257f2c85667`（即 `shasum -a 256 harness/* raw/* | shasum -a 256`）
- 已确认这些文件不包含用户账户标识（`WorkspaceId`、Feishu AppID）。

## 内容

| 路径 | 说明 |
|---|---|
| `harness/qa_origin_guard_probe.py` | 同一 harness、同一解释器，仅通过 `PYTHONPATH` 切换源码树，对比本树与 `main` 只读导出树的状态码与正文 |
| `harness/qa_ordering_probe.py` | 运行期验证中间件顺序，并用 `secrets.token_hex` 计数证明 guard 自行分配 `request_id` |
| `harness/qa_envelope_parity.py` | 三条路径（路由级 503、路由级 422、中间件级 503）的信封键集合一致性 |
| `harness/qa_shared_helper.py` | monkeypatch 模块级 `settings_error_response` 为 spy，证明两条路径共用同一 helper |
| `harness/qa_failclosed_sweep.py` | 15 路径 × 3 种 Origin = 45 个探针，检查是否存在 2xx、非信封响应或内容回显 |
| `raw/*.json`、`raw/*.log` | 上述探针的原始结果与运行日志（含未修复 `main` 树的对照结果） |

## 结论摘要（细节见 [DEV / 验收报告](../../2026-10-14-ORIGIN-GUARD-SETTINGS-ERROR.md)）

7 项必做验证全部 PASS，修复本身未发现新缺陷；同时记录三条**既有**观察：`forbidden_origin` 403 信封缺 `request_id`（O1）、损坏 profile 会导致包括 WebUI 根与未认证请求在内的所有请求 503（O2）、以及损坏 profile 无法经 API 自修（O3）。
