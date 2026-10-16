# 前端 UX 里程碑 C 独立 QA

- 固定受测产品 SHA：`1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c`
- QA checkout：独立 QA worktree；原件保留在该 checkout 忽略的 `.local/qa/frontend-c-initial/`，本报告不复制 QA 原件。
- Sol gate：适用 C 离线前端场景 **PASS**。该结论只覆盖本报告实际执行项。

QA 实际结果：Web 单测 25 files、190 passed / 4 todo；TypeScript、lint、build 与 `npm ci` 均 exit 0（lint 有 2 条 React effect warning，build 提示 584.80 KB JS chunk）。FastAPI + Fake 引用更新闭环 1/1、项目/Reader/Ask 五档 × 双主题 40 图矩阵（横向溢出 0）、项目返回搜索/筛选/滚动/焦点复演、项目日志不改变 `progress` / `progress_version` 均通过。浏览器矩阵、Mock UI 与隔离 FastAPI 是不同场景；没有声称日志的 UI 与真实路由在同一个 E2E 中执行。外部请求计数为 0。

项目返回状态浏览器用例的初始尝试和一次修正后尝试 exit 1，原 harness 错误被保留；最终修正后的复演 exit 0，且 Sol 按最终结果及历史失败记录分别核验。它们不是产品失败，也不能把失败日志替换成通过日志。

QA 没有发现 C 范围产品缺陷。全站守卫 ①、④、⑤、⑥仍 **NOT_RUN / 留 D**；QA Python 661 与 mutation 未重跑。真实 provider、OAuth、飞书、Keychain、真实材料、DMG/安装、公证、五日和双机仍 **NOT_RUN**。本报告不代表全产品、Stage C 或发布验收通过。完整脱敏原始证据索引与 SHA-256 见[证据索引](evidence/2026-10-15-frontend-c-qa/README.md)；原始 `.local/qa/frontend-c-initial/` 留在 QA checkout。
