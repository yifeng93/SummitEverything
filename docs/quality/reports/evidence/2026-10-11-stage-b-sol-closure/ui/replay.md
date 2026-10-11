# DEV 界面复演（不是独立 QA）

工作区：`/Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial`。API18893 / Web15173；`.local/sol-closure/profile`、`.local/sol-closure/workspace`，名称Stage B合成验证。只用合成非秘密AppID `cli_synthetic_sol_dev`，没有录入凭据。

1. `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" SUMMIT_API_PORT=18893 SUMMIT_WEB_PORT=15173 SUMMIT_PROFILE_ROOT="$PWD/.local/sol-closure/profile" uv run python scripts/run_dev.py`。
2. IAB打开15173，创建隔离空库，打开设置；保存Real+合成AppID。设置显示“钥匙串不可用”，保存/删除密钥和3种smoke控件禁用，剩余次数均1。DOM见settings-dom.txt；console warn/error捕获为[]。API观察到POST workspace201、GET status/settings/provider-smoke200、PATCHsettings200；未访问外部地址。未声称完整HAR。
3. Swift开发壳build后用独立测试bundle启动。wrapper须含实际uv/npm目录PATH（本机`~/.local/bin`和`/usr/local/bin`），上述guard/ports/profile环境；binary是该checkout编译出的SummitEverything。首次wrapper缺PATH导致启动失败，native-initial-failure.png保留。
4. 正常原生run_id `0886AFB0-4B56-4365-AD95-D39482DFF658`，health service ready，打开的是15173；目录选择器直接Go To合成workspace，打开已有库。
5. Real任务面板起初仍显示Fake且写按钮可用，促成Sol新增UI修复。组件测试before/tasks-real-ui.log保留1FAIL/11PASS；after Web43全部通过。原生HMR后显示真实禁写原因，新建按钮disabled、本地项目进度可用。截图/AX见native-real-tasks。
6. 原生设置显示Keychain不可用、全部真实能力未启用，native-settings.png。关闭最后窗口后18893/15173无监听、该binary/runner进程无残留。旧8793/5173服务没有借用。

OS Keychain拒绝/锁定/重启和真实服务全部NOT_RUN；合成存储故障由MemorySecretBackend/UnavailableSecretBackend API与单元回归覆盖。完整固定SHA浏览器网络与磁盘对照由独立QA另外记录。
