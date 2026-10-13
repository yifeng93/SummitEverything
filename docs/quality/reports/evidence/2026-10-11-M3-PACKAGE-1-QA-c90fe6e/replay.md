# 固定 SHA 复演指南

目标是隔离 QA checkout、固定源码 SHA `c90fe6e2bec5677deb7b069b86fa8971da1d8dcd`。不在 Developer checkout 操作。不要接入真实 provider 或真实资料。

## 全量自动门禁

```sh
uv sync --locked --group dev
npm --prefix web ci
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
npm --prefix web run api:types
npm --prefix web test
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

## 新对话契约失败

```sh
uv run python scripts/run_dev.py
```

首次启动使用空的 `SUMMIT_PROFILE_ROOT`，浏览器访问 README 指定 localhost 页面并在 UI 新建合成空工作库。进入“知识问答”，提交任意非空合成问题，观察 UI 首问 404 且列表不产生历史。随后可用同一 UI 体验直接 API 对照：向 `/api/v1/queries` POST 合成 JSON `{"request_id":"<uuid>","question":"QA synthetic question","fingerprint":"fake"}`，**省略 `conversation_id`**；Dev runner 的 Vite proxy 自动提供本地 bearer，stream 应含 status/delta/completed 并在历史可见。重复相同 payload 应重放；改 question 而沿用 request id 应 409。

## 取消、断流和历史引用

报告内 `harness_app.py` 是本轮隔离边界 harness：真实 `create_app` / FastAPI route、SQLite stores、`QueryService`、workspace/page writer / reader 和引用资格门仍由产品提供；只有 embedding 与 answer provider 用 fake，前缀 `QA-CANCEL-PROBE:` 会在 fake embed 处 sleep 8 秒。

```sh
SUMMIT_PROFILE_ROOT="$PWD/.local/qa/m3-package-1/profile-3" \
SUMMIT_SESSION_TOKEN='qa-only-random-token' \
SUMMIT_API_TARGET='http://127.0.0.1:8875' \
SUMMIT_WEB_PORT=5275 \
PYTHONPATH="$PWD/src:$PWD/docs/quality/reports/evidence/2026-10-11-M3-PACKAGE-1-QA-c90fe6e" \
uv run uvicorn harness_app:app --host 127.0.0.1 --port 8875
```

另开本机终端启动 Web：

```sh
SUMMIT_API_TARGET='http://127.0.0.1:8875' \
SUMMIT_SESSION_TOKEN='qa-only-random-token' \
npm --prefix web run dev -- --host 127.0.0.1 --port 5275
```

在 `http://127.0.0.1:5275` 新建合成 workspace / project / 页面，通过真实 UI/API 确认页面并按真实索引计划建 fake embedding 索引；问答得到 citation 后确认页面更新，再打开历史 citation，对比卡片、当前页面和必要版本提示。取消复演：打开一个有效的已有会话，在问题开头写 `QA-CANCEL-PROBE:`，提交后立即按“停止回答”，检查历史与 SQLite 的终态/事件序列。不可用引用复演：从隔离 workspace 移走合成来源页文件，再取历史，确认历史 snapshot 不变但 availability=`unavailable`，UI 提示且不导航。

本轮原始脱敏请求、响应、数据库核验和服务 logs 在 `.local/qa/m3-package-1/`；其 SHA-256 列于同目录证据目录 `sha256.txt`。为避免依赖历史会话，本指南只使用新建合成 profile/workspace 和合成内容。
