# M3 包 2 repair 2 QA 证据

受测产品 SHA：`94854bafc0f6aec4d79e55c851be2640ef436739`；原始产品树 SHA：`b7cfd32e1a1991db6e045f282bc0ab39d48aae15`。证据生成后仅新增 QA 报告与本目录；产品树和 tracked tests 未修改。

本目录包含独立 `.local/qa` harness 的脱敏副本、QA 合成 provider payload、运行日志及退出码、manifest、浏览器 AX 观察和 `sha256-manifest.txt`。manifest 文件路径均相对仓库根目录且不包含 manifest 自身。原始临时工作库和 profile 只保存在忽略目录 `.local/qa/m3-package-2-repair-2/`，不纳入 Git。

所有问答走 loopback fake API；DeepSeek adapter 使用 `httpx.MockTransport`，embedding 使用本地 `FakeEmbedding`；请求 capture 是 QA 合成问句与合成正文。没有真实模型、飞书、真实资料或凭据、Keychain、native、DMG，也没有消费 smoke 额度。服务已停止。

初次 harness 准备中有的配置错误保留在 raw log；它们是 QA harness 修正记录，不作为产品缺陷。最终结果只引用各 `*-r2-final` / 本轮后缀日志与独立浏览器实测。