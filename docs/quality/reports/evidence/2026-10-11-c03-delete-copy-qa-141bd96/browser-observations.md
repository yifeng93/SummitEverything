# C03 浏览器观察（固定 141bd96）

- 服务：Fake 默认模式，本机 `http://127.0.0.1:15813`，API `http://127.0.0.1:18813`；profile 和工作库都在本 checkout 的 `.local/qa/c03-delete-copy-qa-141bd96/`。
- 浏览器：Codex IAB 临时标签（不是用户 Chrome / 日常会话）。通过 `cua_repl` 建库、建主线、建项目概览、归档 / 恢复、触发删除；标签页 AX 文本用于记录实际 UI，截图由工具当轮显示，未导出为本地文件。
- 建库操作：填 `C03 QA 合成库` 和合成工作库绝对路径，点击“创建本地工作库”；进入今日页，再点“项目与知识”。创建主线“合成主线”、项目“合成内容项目”，通过“创建项目概览”保存合成正文“仅用于 C03 删除保护验收的合成内容。”
- 活跃非空项目拒删：项目下已有 `合成内容项目-概览.md` 时点击“删除空项目”。实际 UI banner：`这个项目仍有内容，无法删除；如需收起，请归档项目。`，服务日志记录 DELETE 409。操作前后 `manifest.json` SHA-256 均为 `4b17a408b9be523fb7b164b5ff0011800aac078de0bbdc4b8eebd5845d991679`；原概览文件 SHA-256 均为 `69296aaff69990546e7cf76507ad25b8f3ad3d6afd724a66d5ba8239945c98a7`，原目录及文件仍存在。指纹在 `logs/active-project-before.txt` / `active-project-after.txt`，逐字 diff 无差异。
- 已归档非空项目拒删：归档项目后勾选“显示已归档项目”，再点“删除空项目”。实际 UI banner 仍是上面的项目提示，服务日志记录 DELETE 409。拒绝操作前后 manifest SHA-256 均为 `a4368a694e148d762974aa053fa547596df1977cc1623377fd460c0c4b9b839b`；概览文件 SHA-256 均为 `69296aaff69990546e7cf76507ad25b8f3ad3d6afd724a66d5ba8239945c98a7`，目录和文件仍在。见 `logs/archived-project-before.txt` / `archived-project-after.txt`。
- 含项目主线拒删：该项目先归档，选中“合成主线”，点击“删除空主线”。实际 UI banner：`这条主线下仍有项目，请先移动项目，再删除空主线。`；服务日志 DELETE 409。这个提示要求移动项目，没有暗示归档就能删主线。
- 仅文件主线拒删：WebUI 建立“仅文件主线”后，在其目录放入合成 `retained.txt`（内容 `合成保留文件`，hash `c06d0d28bf739fac6c91ca4c50516640b278a40de36654a8a6ed70517d2df5c5`），点击“删除空主线”。实际 UI banner：`这条主线目录仍有内容，请先移动内容，再删除空主线。`，服务日志 DELETE 409。拒绝操作前后 manifest SHA-256 均为 `a4368a694e148d762974aa053fa547596df1977cc1623377fd460c0c4b9b839b`，retained.txt hash 不变，主线目录和文件仍存在；见 `logs/file-line-before.txt` / `file-line-after.txt`。
- 空组织删除：在主线下创建不含内容的“空项目删除验证”，点“删除空项目”；项目从 UI 移除，服务日志 DELETE 204。随后建立“空主线删除验证”，点“删除空主线”；主线从 UI 移除，服务日志 DELETE 204。后端合同测试还检查相应目录不存在、记录列表为空。
- 捕获限制：已通过 IAB 实际交互并观察 DOM/AX 与画面；没有专用 DevTools 网络面板或独立 console 采集接口。服务端 access log 记录本地 API 方法 / 路径 / HTTP 状态，但不含响应体。409 标准错误体由定向真实 FastAPI contract 测试核对（409、`workspace_error`、string `request_id`、中文提示和拒绝写入不变量）。因此不据此宣称完整网络请求 / console 采集或零 warning。
- 服务关闭：用 Ctrl-C 结束本轮 `scripts/run_dev.py`，日志显示 Uvicorn shutdown complete；本机服务不再运行。
