# 检索标题 scope 修复 + 真实 provider 验证

日期：2026-10-17
分支：`codex/retrieval-title-scope-20261017`
产品修复提交：`c82aecf09b195ddcbae40e3b5c5db31d959aea6e`
基线：`36842f4`（含 API key / 整理 kind / 取消修复）
DMG：`.local/internal-builds/c82aecf-20261017/SummitEverything-Internal-c82aecf.dmg`
DMG SHA-256：`775d147bab3f4c6ce9c669b95e1a97464f15b9691952885550da29aa9de6f6c5`

## 现象与根因

真实 `Test2` 工作库中，已确认并已索引的页面
「系统增加学员28号晚住宿需求自动勾选流程」无法被以下问题引用：

- 学员28号晚住宿需求自动勾选流程是什么？
- 28号晚住宿需求自动勾选流程是什么？

查询返回 0 引用，答案退化为“没有找到该主题的依据”；`acceptance-plans.json` 只记录
embedding 用量，rerank/LLM 未触发。

根因：`QueryService._in_scope` 只把 chunk 正文用于 scope 匹配；该页面没有 Markdown
标题，chunk heading 为空，页面标题只存在于 manifest/metadata。问题的维度词是**页面
标题的子串**，但不是正文子串，因此正文匹配为空，页面被排除。

## 修改

`src/summit_everything/retrieval/query.py`：

- 仅在**没有明确对象且正文分段没有命中维度**时启用页面标题兜底；
- 页面标题必须匹配请求的维度 term，才把该 chunk 纳入候选；
- 引用摘录仍使用正文，标题不作为证据；
- 资格门、确认状态、索引版本校验、对象排除逻辑均不变；
- 不需要重建索引。

新增回归 `tests/integration/test_c19_topic_scope_normalization.py`：

- 页面标题命中、正文没有该标题短语时，精确问法得到正文引用；
- 含糊问题「28个学员是什么」仍 0 引用，且不调用 answer provider；
- 原有 C19 对象/限定词/部分支持测试保持通过。

## 验证结果

### 离线回归

| 检查 | 结果 |
|---|---|
| 定向 C19 scope | 42 passed |
| Python 全量 | **731 passed**，1 条既有 Starlette/httpx warning |
| Web 全量 | **241 passed / 26 files** |
| Ruff / format / mypy | exit 0 |
| Web typecheck / lint / build | typecheck/build exit 0；2 条既有 warning |
| DMG | codesign strict、hdiutil verify、packaged smoke 均 exit 0；`dirty=false` |

### 真实 `Test2` 工作库

- 整理：job `8c79b00d-…` `completed`，12 份稿，4 份已确认，8 份待审；DeepSeek
  3137 输入 / 1408 输出 tokens，无 schema 错误。
- 索引：`model.index` 成功，百炼 embedding 299 tokens；4 chunk，索引 ready。
- 修复前精确问法（07:28/07:29）：0 引用，仅 embedding。
- 修复后查询（07:43:20）：`model.query` 成功，1 条引用，页面
  `1a2e7658-…`「系统增加学员28号晚住宿需求自动勾选流程」；
  - embedding 28 tokens
  - rerank 85 tokens
  - DeepSeek 390 输入 / 588 输出 tokens
  - 回答内容忠实于页面正文：当前不是自动勾选，需告知 EC 手动备注，计划增加系统勾选流程。
- 同一工作库的旧含糊问题仍返回缺少依据，没有伪造答案。

### 未测

- 真实飞书 OAuth / 读取：NOT_RUN（日志中的 Feishu 计划没有 provider usage，不能证明真实读取）。
- 已安装 App / 公证 / 五日 / 双机 / 发布：NOT_RUN。
- Keychain：真实整理与查询在重启后继续可用，推断读取 PASS；未单独做删除/重录生命周期测试。
- 标题兜底的多 chunk 页面可能把该页全部 chunk 纳入候选，属 P3 范围；本轮测试页面只有一个 chunk。

## 合并建议

**建议合并。** 三组用户可见问题现在都有真实证据：

1. 百炼点分隔 key 被接受；
2. 真实整理不再因 `kind` 失败（12 份稿）；
3. 真实问答能返回正确引用，且 rerank/LLM 实际被调用。

前置：分支目前只在本地，尚未 push/PR/CI；合并前需按正常流程跑远端 CI。
合并后仍需单独走真实飞书、安装/公证、五日/双机/发布等产品门，不能把本轮结论扩大为
完整产品真实 PASS。
