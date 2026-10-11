# 本地刷新消费标记严格解析 DEV（2026-10-11）

独立8b复核指出P2：本地消费标记接受Pydantic字符串/数字布尔转换，不符合损坏槽拒绝契约。不是已证明的付费请求绕过；真实生产写出JSONbool，P1重启防重发在8b已复验关闭。

真实API/vault合成损坏槽字段false字符串/0：before2FAIL（status错误声称authorized），严格Field后5PASS（同文件含重启/保存失败/合法轮换），损坏槽401credential_unreadable且零新增HTTP。旧凭据缺字段defaultFalse与合法True/False兼容；不改变token协议或权限。

最终全检查在字段修改后：backend388/Web45；ruff/format/mypy36/lock/API幂等/type/lint/webbuild/Swift/diff0；package使用本venv hatchling+uv build --no-build-isolation，guard正常加载。原warnings保持。该报告是DEV，最终SHA独立QA尚待完成；真实账本0/1、真实任务写disabled、OS/DMG/R03等NOT_RUN不变。
