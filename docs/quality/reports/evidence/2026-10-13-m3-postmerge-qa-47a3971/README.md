# M3 post-merge QA evidence

受测固定 merge SHA：`47a3971ea3dccf6ffbc7107b2d5995043b4e25a2`。

本轮核验 merge identity / parents / candidate ancestry / product-tree identity，并在此 detached checkout 独立准备 locked Python 与 Web 依赖，执行完整 guarded 后端与当前关联静态、生成及 Web 自动检查。Post-merge QA 不重复候选QA已经通过的 C19 对抗矩阵、HTTP/SSE、Chrome UI、history reopen。真实服务、凭据、DMG、五日与双机维持 NOT_RUN。

`raw/` 保存实际运行输出与独立退出码。候选 QA 的原始 71 项 manifest 另保存在同一仓库既有 evidence 目录；此处记录其验证输出和 SHA。OpenAPI / TS 临时产物与导出脚本仅在被忽略的 `.local/qa/m3-postmerge-47a3971/`，没有写回 tracked 文件。

首轮命令包装曾在 zsh 把只读的 `status` 用作变量名，导致包装器退出 1；前端首轮重定向路径也错误地相对 `web/`。相关首轮日志保留在测试 checkout `.local/qa/m3-postmerge-47a3971/raw/`。所有受影响检查都用绝对日志路径及可写 `rc` 变量重跑，最终退出码 0；这属于QA记录脚本失误，不是产品测试失败。
