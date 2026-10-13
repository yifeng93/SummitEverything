# 本机浏览器短复演

固定产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`。Web/API 产品路径在初验 SHA `22e5ad945353929ebd781e1397f641c9d5fcf963` 到本轮源码间无变化；本记录是本轮浏览器实操。

- 服务 A：`http://127.0.0.1:16173/`，profile `.local/qa/m3-package-3-repair-1/profile`。
- 服务 B：`http://127.0.0.1:16174/`，profile `.local/qa/m3-package-3-repair-1/profile-b`。
- 两个独立 profile 打开同一个合成库 `.local/qa/m3-package-3-repair-1/workspace-ui`。
- 库内有一条 FakeLLM 完成但未确认的整理稿，另有一条合成 unknown item；seed 脚本与其输出在 `harness/seed_browser_profiles.py`、`raw-logs/seed-browser-profiles.log`。
- A 重载后显示 `review.txt · 待审核`、`unknown.txt · 请求状态未知` 和一份审核稿。选中 unknown 后按钮为 `重新整理所选 · 1`，提示原文为“请求状态未知，不会自动重发。明确重新整理会创建新操作，可能再次调用模型；原件与既有稿件会保留。”
- B 从独立 profile 打开同一库，也显示同一待审稿、unknown item；选中 unknown 后显示相同的显式重新处理提示。
- 两服务以合成库与 Fake 模式运行，未用真实 provider、外部账号或材料。
- 当前 CUA surface 能读取浏览器 AX 树，但没有 DevTools console/network 导出接口；console、network 及 PNG 文件证据记 **NOT_RUN**。浏览器 UI 行为为实际观察的 PASS。
