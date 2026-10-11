# Stage B 8b6259a 独立 UI 复验

固定代码 `8b6259a9aa6ff2e52b700134abadff24de46dc08`，新 detached checkout `/Users/yifengstudio/.codex/worktrees/qa-stage-b-ui-retest/SummitEverything`。不是对整体候选的通过声明：同期新增 strict refresh marker 修复尚待下一固定 SHA；初始 7f 全流程 UI 记录保留，Web/native 树 `git diff --quiet` 相同（exit0），可据此作为未改变界面流程的基线，不能冒充本 SHA 实际重演。

本次独立环境重新 uv sync --locked/npm ci/Swift build，均exit0；guard下 refresh restart3+vault10=13 passed（1既有Starlette warning）。实际 IAB新合成库→Fake授权→3条合成材料metadata与日历空态→Real/app_id保存→Keychain不可用、smoke均剩余1、任务创建disabled/本地进度enabled。未录入秘密、没有真实provider/Keychain/授权链接点击；0/1真实调用次数不变。IABwarn/error=[]。

原生新bundle `local.summit.stageb.ui.retest.qa`，exact新checkout Swift binary，API18895/Web15175，新profile/workspace。首次启动health ready且run_id/guard/path匹配，但WKWebView空白（AX无页面URL，截图保留）；原因未确定，不归因环境、不隐去。正常关闭后重新启动，页面加载成功；打开仅合成库，Real任务禁写与settings持久/credential禁用均有实际AX/截图。第二运行UUID与native child一致；最后窗口关闭，checkoutbinary/runner/uvicorn/vite无残留、两个端口无监听。结果：首启动观察保留待最终SHA继续冷/热启动复核；第二启动及GUI子范围PASS，整体QA仍由最终报告判断。

网络：native product丢弃stdout/stderr，本次没有HTTP访问日志，只有loopback socket快照，不能称HAR或完整网络捕获。7f浏览器132条access log仍只对应7f。后续最终SHA将用browser runner单独捕获访问日志。完整新 evidence 在相邻 `evidence/2026-10-11-stage-b-ui-retest/`，manifest逐项匹配。真实OAuth外部浏览器、app-configured无user日历实际GUI、DMG/OS/真实质量/样板/五日/双机与M3–M5继续NOT_RUN。

## QA-UI-B-01：原生首启动竞态（P1 / FAIL）

此项追加覆核将上方“首启动待核实”明确更新为FAIL；第二启动及其他GUI局部PASS不改变整体阻断。

固定8b源码native不变，只在测试wrapper PATH插入npm shim：sleep5后exec实际`/usr/local/bin/npm "$@"`。未替代业务route/store，未改产品。独立bundle `local.summit.stageb.ui.delay.qa`，18897/15177、独立delay-profile，相同offline guard。实际native启动后，APIhealth ready、WebGET200（run_id A81B3996-857E-4604-8BA0-962F48877AAB），native仍为空白WKWebView，AX无URL、截图白屏。源码waitForReadiness只检查API/run_id便load webURL，失败导航不重试；run_dev虽另检查两服务，native不等待完整readiness。延迟触发的现象与源码一致；正常重启能恢复不免除首启动失败。第一次未注入亦有相同空白，原观察保留。

期望native等待API身份及Web就绪，并对未完成导航作有界恢复；实际两服务后来就绪也无恢复，首启动不可用，影响C14/B05。截图/AX/runtime-ready、实际npm shim/测试wrapper/log均归档；故障fixture最后窗口关闭后18897/15177无监听。执行者修复后用新SHA同样延迟及正常启动复验。
