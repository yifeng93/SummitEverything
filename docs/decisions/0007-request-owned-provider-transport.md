# ADR 0007：Provider 请求独立取消与资源所有权

日期：2026-10-11。范围：Stage B 离线源码收口，不扩大真实服务授权。

R3/R4 的同步 HTTP worker 在 DNS 未完成时没有 socket 可以关闭；有限 join 后报错仍可能在后台发请求。遍历共享连接池关闭 socket 又会取消其他合法请求。因此停止使用连接池私有属性和后台 daemon 取消方案。

生产 provider 使用 `create_http_client()`：HTTPX 的同步接口保持不变，自定义 `DeadlineTransport` 为每次请求创建独立 HTTPCore async pool。整体 `asyncio.timeout` 覆盖解析、TCP、TLS、响应头和正文；runner 为非 daemon，返回前必须完成 join。借用 client 不被边界关闭，provider 业务租约决定自有 client 的退役时机；新租约检查和登记在同一生命周期锁内完成。

采用 aiodns/c-ares 取消解析，避免不可取消的系统 getaddrinfo worker。解析器由请求持有并关闭；TCP stream 从连接建立时就由 backend 持有，包含尚未完成 TLS、尚未交给 HTTP connection 的情况。任何退出路径都关闭自有 stream。TLS 保留系统 CA 和原始主机名验证；HTTP 不重试、不跟随重定向、不使用环境代理。多地址 TCP 候选不等于重发 HTTP。只请求 identity 编码，响应头声明其他 content-encoding 时在读取/解压前拒绝，避免同步解压产生无界分配；raw 响应累计字节有上限。完整 JSON 请求使用 HTTPX 相同 wire 编码检查 1MB（含转义与 envelope）。

HTTPCore 从 HTTPX 的传递依赖提升为直接依赖；新增 aiodns，锁定其 pycares/cffi 依赖。增加少量依赖换取可取消解析和明确请求所有权，避免自写 DNS、遍历私有 pool 或每请求外部进程。同步 MockTransport 只用于合成外部边界；其他不具备取消契约的注入 transport 在发请求前拒绝；检查 URL 实际选中的 mount，不只看默认 transport。DNS 返回的 bytes 地址先 ASCII 解码并验证为 IP，不能回退到系统 DNS。

官方依据：[HTTPCore network backends](https://www.encode.io/httpcore/network-backends/)、[aiodns API / cancel / close](https://github.com/aio-libs/aiodns)。网络与 Keychain guard 新增 DNS 门，防止 native c-ares 绕过 Python socket guard。自动检查只允许 loopback 和明确的合成 DNS fixture。

代价：每请求创建连接，不保留 provider HTTP keepalive；首版个人应用优先保证有界调用和副作用隔离。性能优化须保留请求级取消、资源所有权及同 client 并发不误伤的回归。

此决议不证明真实 Feishu scope、用户身份、模型质量、OS Keychain 或安装包验收。真实调用次数保持 0；真实任务写、真实模型业务和未授权数据读取仍按服务端能力门禁处理。
