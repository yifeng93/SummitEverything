# ADR-003：单一 Python 后端与能力移植

状态：Accepted engineering baseline。日期：2026-10-09。用户委托技术选择。

## 背景

两旧产品的处理与检索能力主要为 Python。现有分块、SQLite / NumPy 检索、飞书和原子写入值得复用，但旧三端规则、两种 UI 与服务器不应留作新运行时。

## 决定

Python 3.12+ / FastAPI 唯一后端，React / TypeScript / Vite 唯一 UI，本地 SQLite 与 NumPy 检索，薄 macOS 壳。uv.lock 与前端 lockfile 固定实际依赖版本。

逐模块吸收旧能力，并适配新的身份、版本和 provider 接口。域层无 I/O；workspace、retrieval、integrations、local 和 API 按责任组织，避免通用插件框架或多进程微服务。

## 比较

Go 或全新检索引擎可以实现产品，但当前没有需要重写成熟 Python 算法的证据。保留旧 Flask 与 FastAPI 双服务会继续制造状态和规则漂移。把两旧仓库 import 到新产品会绑定本机路径与旧业务假设。

## 影响

需要认真处理 Python 依赖、流式取消、NumPy arm64 打包与服务生命周期。技术可随事实调整，但不能通过换技术删掉产品范围或降低验收门；重大的协议 / 架构变化另写 ADR。
