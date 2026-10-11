# Sol DEV readiness 反例与证据复演

这些文件来自2026-10-10独立DEV候选评估，不是正式固定SHA QA。实现检查点1fede419a49b76c2f82e392be2803597cedab1f2，原文档检查点4966a6824bcc98b065e754e2e7a27d3f94a1539c；源码与执行快照逐文件一致。完整结论见上级2026-10-10-STAGE-B-SOL-DEV-REVIEW.md。

## 文件与原始性

- test_review_regressions.py：正式归档版本实际执行，8个预期行为断言FAIL；早期logout测试访问错误URI的输出未用作结论。
- test_review_additional.py：实际执行2 FAIL，能力状态与HTTP响应读取边界。
- SettingsView.review.test.tsx：实际执行1 FAIL，Model Studio account保存。
- sitecustomize.py：实际使用的Python守卫；禁用系统Keychain构造/读/写/删，阻止非loopback socket connect/connect_ex。测试明确注入的Memory和Stub subclass只保存合成值。
- counterexamples.log/additional.log/frontend-counterexample.log：对应执行stdout。归档时替换临时review-root路径与生成的合成OAuth state；只归档脱敏输出，并去除stdout行末空白/尾部空行以满足diff检查。harness归档为实际最终执行字节；additional仅规范末尾换行后重新执行并仍为2 FAIL。
- source-snapshot-manifest.json：复制测试前390项源码与文档SHA-256；提交后390项匹配。它不是新的报告/证据全库manifest。
- observations.json：实际检查结果与独立性边界摘要。通过检查的原stdout保留在聊天工具记录；没有声称此目录含全量通过矩阵的原始日志。
- manifest.json：本目录除自身的实际字节SHA-256，用于验证归档证据没有被篡改。它不证明产品功能通过。

## 如何重跑

在源码库和真实工作库之外建立专用临时replay目录。不要在实现者工作树增加文件、改依赖、切branch。先验证manifest，再把固定源码archive解到replay/candidate，将本目录两个Pythonharness原样复制至replay根，sitecustomize.py复制至replay/guard。harness读取replay/candidate/tests/integration的合成helper。前端harness原样复制至replay/candidate/web/src/components；这是临时测试文件，不是修改产品实现。

依赖按该SHA的lock安装到临时candidate，或复用一致的现成venv并复制前端node_modules；禁止升级。可用uv sync --locked --group dev --offline / npm ci --offline，缓存缺失就报告环境BLOCKED，不静默改lock。将PYTHONPATH设为绝对replay/guard:replay/candidate/src，UV_OFFLINE=1，然后从candidate执行：

```sh
uv run --no-sync pytest ../test_review_regressions.py -q -p no:cacheprovider
uv run --no-sync pytest ../test_review_additional.py -q -p no:cacheprovider
npm --prefix web test -- --run src/components/SettingsView.review.test.tsx
```

在该DEV实现上预期退出码分别1/1/1，失败8/2/1。这些FAIL是缺陷证明，不应改为期待错误行为的绿测试。修复后在新SHA重跑相同期望并回归Stage A；保留本报告的旧FAIL。本次没有真正浏览器/原生/OS Keychain或真实服务操作，不能据fixture通过将这些未测项改PASS。
