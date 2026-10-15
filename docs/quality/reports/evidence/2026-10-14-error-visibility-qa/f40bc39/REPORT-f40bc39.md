# QA 验收记录 — f40bc39445258d954166143e094156c788be36e1

- QA worktree: `/Users/yifengstudio/.codex/worktrees/qa-f40bc39/SummitEverything`
- 起止 `git status --porcelain`: 空；HEAD = `f40bc39445258d954166143e094156c788be36e1`
- 本轮只新增 `.local/qa/**`（gitignored），未修改产品实现、已有 tracked tests；未 commit/push
- 全程未联网、未使用真实 key；pytest 均在 `PYTHONPATH=scripts/offline_guard:src` 下运行（keychain 被 guard 拒绝，测试用 `MemorySecretBackend`）

## 1. 身份与范围

```
$ git rev-parse HEAD
f40bc39445258d954166143e094156c788be36e1
$ git status --porcelain      # 起、止各一次 → 空
$ git diff --name-status 19078de..f40bc39
M  docs/quality/reports/2026-10-14-REAL-FIRST-USE-FINDINGS.md
M  src/summit_everything/api/app.py
M  src/summit_everything/local/event_log.py
M  tests/integration/test_assist_and_index_failure_records.py
M  tests/unit/test_profile_event_log.py
$ git diff --name-only 19078de..f40bc39 -- web/ | wc -l
0
```
判定 **PASS**：`web/**` 未改。

## 2/3. D1 触发 A / B（assist + 索引两条端点路径）

harness `.local/qa/test_d1_endpoints.py`（23 项，全过）。两条路径都真正走了 HTTP 端点后读盘：

- A（脱敏回显 `... api key: sk-*** is invalid`）：`assistant_failed` / `index_update_failed` 均写出，reason 含 `sk-***`，无未掩码凭据。
- B（258 字符与 tracked test 实际的 278 字符两种）：两条路径事件均写出，reason 长度 `0 < len <= 200` 且不等于原消息。
- 另有 `test_trigger_a_realistic_boundary_masking_then_record`：先跑真实 `sanitize_provider_text()`（得 `... sk-*** is invalid`）再走 assist 端点。
判定 **PASS**。

## 4. 安全约束未放松

- 未掩码 `sk-abcdefghijklmnop` 出现在 reason 时：文件里无原串、含 `sk-***`；assist 与索引均验证。
- 掩码先于截断（`"x"*190 + " " + KEY` → `sk-***` 保留、总长 ≤200）。
- 换行/`\r`/`\t` 折叠为单行，文件每事件恰一行且为合法 JSON。
- 空串 / 纯空白 / 非字符串 → `profile_event` 仍抛 `ValueError`；经 `record_diagnostic` 回退为 `unrecorded`，**事件仍然写出**。
- 白名单 / state / record_id / count 仍拒绝，且拒绝时不产生文件。
判定 **PASS**。

## 5. 不存在静默丢弃（实际检查清单）

| 位置 | 结论 |
|---|---|
| `record_assistant_failure`（assist 端点） | 已无 try/except，改走 `record_diagnostic` |
| `index_after_approval`（索引失败） | 同上 |
| `record_diagnostic` | 捕 `ValueError`→回退 `unrecorded`；捕 `OSError`→静默返回（磁盘故障，设计如此）；`TypeError` 会外抛（实测） |
| `app.py:2343/2369/2540/2554/2567/2620` 六处直接 `profile_event` | 无 try/except → 失败**大声**抛出（用 monkeypatch 注入 ValueError 实测 `pytest.raises(ValueError)`） |
| `except ...: pass`（全 src） | 仅 5 处，均为异常类体（3）、`state.py` 的 `FileNotFoundError` 清理、`app.py` 的 `asyncio.CancelledError`；与诊断无关 |
| `contextlib.suppress`（全 src） | 0 处 |
| 其它日志落盘点 | 仅 `event_log.py` 一个 `RotatingFileHandler`；query record 的 `store.terminate` 未被吞掉，且 `diagnostic` 经同一 `sanitize_provider_text` |

判定 **PASS**（并见第 9 项残留）。

## 6. 既有契约未回归

```
$ pytest tests/integration/test_app_lifecycle.py tests/unit/test_profile_event_log.py \
         tests/integration/test_assist_and_index_failure_records.py \
         tests/integration/test_qualified_retrieval.py
53 passed   EXIT=0
```
含 `test_app_lifecycle` 的 `synthetic-private-probe` 不入 caplog、事件白名单/状态元数据/轮转（`_MAX_BYTES` monkeypatch，`1 < files <= _BACKUPS+1`）、`test_an_unmasked_credential_never_reaches_the_file`。判定 **PASS**。

## 7. 全量与静态检查

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=scripts/offline_guard:src uv run pytest -q` | **656 passed**, EXIT=0 |
| `uv run ruff check src tests` | All checks passed! EXIT=0 |
| `uv run ruff format --check src tests` | 97 files already formatted, EXIT=0 |
| `uv run mypy src` | Success: no issues found in 46 source files, EXIT=0 |
| `uv lock --check` | EXIT=0 |

判定 **PASS**。

## 8. 打包候选

- DMG 自算 `shasum -a 256` = `a856a2eb70607f30078197946f4aba67c9a7ad367d639c187c101230172370ce` → 与声称**一致**。
- `Resources/first-use-defaults.json` SHA = `23f3b3f9…04e1`，与主仓库 `.local/first-use/defaults.json` **同 SHA、diff 无差异**。
- `build-info.json`：`source_sha=f40bc39445258d954166143e094156c788be36e1`，`dirty=false`。
- `smoke_packaged_app.py`：`PASS: onedir backend starts with empty PATH; …` EXIT=0。
- 只读挂载 DMG：`diff -r` 与磁盘上的 `.app` **完全一致**（backend 可执行文件 SHA 同为 `aa157748…9dc1`）。
- 包内确实含本轮修复（`.local/qa/pyz_probe.py`，仅用 stdlib 解析 PyInstaller PYZ，不执行包内代码、不写入）：
  - `event_log`：`_CREDENTIAL_SHAPE`/`_MASKED_CREDENTIAL`/`FALLBACK_REASON`/`clean_reason` 在名表中；常量含 `sk-***`、`sk-[A-Za-z0-9_-]{8,}`、`unrecorded`；旧 `_REASON_FORBIDDEN` **已消失**。
  - `api.app`：含 `record_diagnostic`、`FALLBACK_REASON`。
  - 更强证据：把包内 `event_log` / `api.app` / `http_boundary` 的 code object 规范化 filename 后与 worktree 源码 `compile()` 结果比较 → `marshal.dumps` **逐字节相同**。

判定 **PASS**（“触发回显 key 的失败”式行为探测未做，见未测项）。

## 9. 残留

1. **控制字符（低）**：旧规则拒绝一切 `ord < 32`；新 `clean_reason` 只折叠 `str.split()` 认作空白的字符，故 `\x00`/`\x07`/`\x1b`(ANSI)/`\x7f` 会**原样落盘**（实测）。JSON 仍是合法单行（`json.dumps` 转义），危害限于终端转义注入，非凭据泄漏。这是本轮唯一的防御纵深下降点。
2. **logging 层吞异常（既有，非本轮引入）**：handler 流损坏时 `logging.Handler.handleError` 吞掉写入错误，`profile_event` 正常返回，`record_diagnostic` 的 `except OSError` 不会触发 → 事件静默丢失（实测：文件仍 1 行、stderr 出现 `--- Logging error ---`）。这给“绝不静默丢弃”划出了边界；本轮未修，也不声称已修。
3. **掩码形状与边界完全一致（既有）**：`SK-` 大写、`sk-abcdefg`（7 字符）、零宽/双向控制符切断形状等场景不被掩码——但 `clean_reason` 与 `http_boundary._SECRET_LIKE` 对这些输入的输出**逐个相同**（实测），故本轮既未引入也未加重。
4. **长度上限按码点**：200 个 astral 字符 = 800 UTF-8 字节。与旧 `len()` 语义一致。
5. **文档小错**：tracked test `test_assist_failure_with_a_long_message_is_recorded_and_truncated` 注释写 `# 258 characters`，实测该字符串为 **278** 字符（任务书沿用了 258）。非产品缺陷，但注释与实际不符。

极端输入（5,000,000 ASCII / 200,000 CJK / 200,000 emoji / 孤立代理项 / `limit=0`）均无异常、无 ReDoS。

## 未测 / 受限

- 打包应用内**行为级** D1 复现（真的让 provider 回显 key）：需要真实凭据或对外网络，两者均被禁止 → 以 PYZ 字节码等价性 + 常量存在性替代（结论更强于单次行为观测，但确实不是端到端行为证据）。
- 未做真实飞书 / 真实 provider / Keychain / 双机 / 五日门（超出本轮范围）。
