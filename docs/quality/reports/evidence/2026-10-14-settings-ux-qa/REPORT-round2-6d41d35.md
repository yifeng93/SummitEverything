# QA 第二轮（独立、全新）：设置 UX 注入修复 `6d41d35`

受测：worktree `/Users/yifengstudio/.codex/worktrees/settings-ux-qa-6d41d35/SummitEverything`，
detached HEAD `6d41d35782422d56b8ee8c8000c9a00479c729cd`，起始与结束 `git status --porcelain` 均为空。
唯一改动来源：QA 新增的 `.local/qa/*`（未 tracked、未 commit）。tracked 源码与既有测试未改。

## 逐项判定

| 项 | 判定 | 关键证据 |
|---|---|---|
| 1 身份 | PASS | HEAD=6d41d35782422d56b8ee8c8000c9a00479c729cd；起始 `git status --porcelain` 空；结束后仍空 |
| 2 D1 修复 | PASS（有对照） | 自建 harness 在 6d41d35 上 92 passed；同一 harness 在 `git archive e4f15cd` 的只读副本上 56 failed / 36 passed |
| 3 注入语义回归 | PASS | `.local/qa/test_injection_semantics_qa.py` 36 passed（a–f 全覆盖） |
| 4 全量测试 | PASS | guarded pytest 561 passed / exit 0 / 78.46s |
| 5 静态检查 | PASS | ruff check 0；ruff format 0（91 files）；mypy 0（46 files）；uv lock --check 0 |
| 6 前端 | PASS | npm ci 0；npm test 0（14 files/90 tests）；typecheck 0；lint 0（2 既有 warning）；build 0 |
| 7 打包候选 | PASS | DMG SHA-256 与声称一致；包内 defaults 与 .local 来源逐字节相同；build-info 一致；smoke exit 0 |
| 8 冻结端到端 | PASS | `.local/qa/frozen_e2e.py` 19/19，exit 0 |
| 9 新缺陷 | 2 项 | F1 字段级注入不对称（同 D1 类）；F2 损坏 profile 返回 500 而非设计中的 503 |

## D1 前后对照

```
# 修复前（只读导出 e4f15cd 源码树）
$ PYTHONPATH="$PWD/scripts/offline_guard:/tmp/qa-old-e4f15cd/src" .venv/bin/python -m pytest -q \
    -c /tmp/qa-old-e4f15cd/pytest.ini .local/qa/test_d1_corrupted_sections.py
QA_MODULE_UNDER_TEST: /tmp/qa-old-e4f15cd/src/summit_everything/integrations/first_use_defaults.py
56 failed, 36 passed   (exit 1)

# 修复后（6d41d35 工作树）
$ PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" .venv/bin/python -m pytest -q .local/qa/test_d1_corrupted_sections.py
QA_MODULE_UNDER_TEST: .../worktrees/settings-ux-qa-6d41d35/SummitEverything/src/...
92 passed              (exit 0)
```

`probe_field_level_asymmetry.py` 的 before/after 表：e4f15cd 有 10 个「注入更宽松」用例，
6d41d35 有 9 个 —— 少掉的正是 D1 的 section 级用例，字段级 9 个两版都在。

HTTP 层（`probe_api_asymmetry.py`）：section 损坏在有/无注入下均为 500，一致；
`embedding.base_url=5` / `feishu.app_id=123` / `embedding.base_url=null` 为 500 → 200，仍是注入更宽松。

## 新增 harness（均未 commit）

- `.local/qa/test_d1_corrupted_sections.py`（92 用例：section 级 str/list/int/None/bool/float/"" ×
  feishu/embedding/rerank × 有/无注入，`apply()` 不改写、非映射文档、API 非 200、pre-fix 对照子类）
- `.local/qa/test_injection_semantics_qa.py`（36 用例：3a–3f）
- `.local/qa/probe_field_level_asymmetry.py`、`.local/qa/probe_api_asymmetry.py`（复现脚本）
- `.local/qa/frozen_e2e.py`（冻结后端端到端）

## 未测 / 受阻

真实 provider、真实飞书 OAuth、真实 Keychain 生命周期、真实材料与账单、Gatekeeper/公证、
浏览器或真机视觉复核、DMG 内 App 的完整 GUI 交互：NOT_RUN。
端到端只驱动了包内后端二进制（`SUMMIT_OFFLINE_GUARD_ACTIVE=1`，keychain_available=false），
未启动原生外壳；前端只有组件/DOM 级测试。
