# Stage B 离线源码合并后核验与收口

日期：2026-10-11。按用户1A/2A授权完成离线修复、独立固定SHA QA、PR/main整合和可恢复清理；本轮没有使用真实凭据或消费已有有限smoke次数。

## 固定对象与结果

- 受测源码：`576895f6983ca41cacbbad45a9075b97b9986189`；[PR #10](https://github.com/yifeng93/SummitEverything/pull/10)以merge commit `41207e5bfb81b535c0254fd4ac242df11da40d67` 合入main，保留受测提交及历史FAIL。
- main的src/tests/web/native/scripts/pyproject.toml/uv.lock与受测源码逐路径零差异；源码为merge祖先。此次追加仅文档/证据。
- 独立Luna High精确SHA后端388项、25项独立失败路径、Swift及实际合成浏览器/原生开发壳复验通过。[后端复验](2026-10-11-STAGE-B-LUNA-OFFLINE-RETEST-576895f.md)、[实际UI复验](2026-10-11-STAGE-B-LUNA-UI-RETEST-576895f.md)。Web独立完整检查来自fd相同Web源码树；main合并后实际重跑45项。
- main在外网/DNS/Keychain guard下完整13项检查exit 0：后端388、Ruff/check/format、mypy、lock、uv package、API types、Web45/typecheck/lint/build、Swift build、diff check。[命令/退出码](evidence/2026-10-11-stage-b-postmerge/checks/results.json)，[可复演runner](evidence/2026-10-11-stage-b-postmerge/checks/replay.py)。保留1条Starlette弃用与3条既有React lint warning；API生成/lock未改变产品树。

## 合并后初次失败与复验

初次全量后端387通过/1失败，原始日志与results-first-failure保留。失败为R4-02慢响应头10次循环中的服务端peer-closed断言：该次cfg.sockets为空，合成server未记录接受的HTTP连接，故测试前置条件未满足。同期另有归档读写，尚无证据证明它是原因，不断言归因，也不将失败静默删除。

未修改产品/测试/期望或放宽容差；原例单独重跑1 passed（内部10次），随后串行完整388 passed及其余检查全部通过。deadline仍0.15秒、容差0.10秒、10次循环和连接关闭断言不变。焦点与首轮失败均归档；这是一项需留意的测试稳定性记录，不称新产品修复。

## 证据发布更正

收尾按实际仓库字节核验发现：fd后端QA原manifest的30条有2条__pycache__/*.pyc未发布；576后端复验20条也有2条未发布。它们是运行时编译缓存，按源码/归档政策不提交，tar也未保留原字节，不能声称原manifest在发布树30/30或20/20匹配。此前QA活动目录校验与当前发布核验是两种范围。

原始报告、FAIL/PASS与runtime manifest字节保持不变；追加[fd publication manifest](evidence/2026-10-11-stage-b-luna-final-offline-qa/publication-manifest.json)及[576 publication manifest](evidence/2026-10-11-stage-b-luna-offline-retest-576895f/publication-manifest.json)：分别28/28、18/18实际报告/源码harness/log文件匹配，各自report hash匹配，遗漏的4条缓存文件路径和原hash逐项列明。其他历史manifest已逐文件匹配；总账见[发布核验](evidence/2026-10-11-stage-b-postmerge/publication-audit.json)。不能把遗漏缓存写成已恢复原件；重演应从已存harness源码生成新缓存。

## 清理与证据限制

20个闲置/完成试验和QA工作树均先可恢复归档后清理；最后9份tar与Git bundle有逐项验证，详见[清理恢复记录](2026-10-11-STAGE-B-CLEANUP.md)。仅保留main工作树；两个Stage B临时分支已从本地/远端删除。历史证据和可恢复Git引用不删。源码结构未混入.venv/node_modules/build/pyc或真实业务材料。

fd后端QA曾遗留PID14593/14594服务进程组（52936/52937），root核实cwd后SIGTERM清理，最终监听已消失；[最终扫描](evidence/2026-10-11-stage-b-postmerge/final-process-scan.json)将保留的Codex CUA工具运行时与产品服务分别列明；[记录](evidence/2026-10-11-stage-b-postmerge/checks/orphan-service-cleanup.json)中的after_listeners为终止后的即时过渡采样，closed=true须结合后续最终扫描。不能用worker计数代替进程清理证明。

浏览器/原生截图在CUA返回中可见，但没有独立图像文件；已归档DOM、console、loopback访问日志和实际观察。network不是HAR。合成凭据故障有真实route/service/vault+MemorySecretBackend覆盖；OS Keychain真实故障不在离线PASS内。

## 保持未测与禁用

本次只完成Stage B离线源码范围；真实Feishu身份/scope/OAuth/材料/日历/task、真实模型及R03质量、OS Keychain、DMG、M3–M5、五日和双机仍NOT_RUN，完整Stage B/v1尚未验收。默认Fake；real_data_enabled=false；真实任务写result_proof_unavailable保持disabled；真实模型业务门未放开。

code exchange、必要refresh、chat、embedding、rerank账本各0/1，真实task写0。不索取/使用key、不访问真实身份/数据；不重置既有授权、不扩大范围。后续使用原有有限smoke边界，数据/模型质量与交付必须按原全v1门继续，代码变化重新固定SHA独立QA。
