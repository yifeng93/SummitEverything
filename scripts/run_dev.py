"""Run the local API and WebUI together for development.

Two ways to use it:

    uv run python scripts/run_dev.py            # 浏览器调试（Vite HMR + uvicorn --reload）
    uv run python scripts/run_dev.py --app      # 原生壳调试（同一套服务 + Swift 壳）

设计目标：改前端只等 Vite 热更新，改后端只等 uvicorn 自动重载；不再重新打包
DMG / 重新安装应用。默认使用仓库内的开发工作库与 profile，启动后自动打开，
所以每次进来都直接落在「今日」，不需要重新选目录、重新过首次配置。

所有状态都在 `.local/dev/` 下，可用 `--fresh` 清空重建；不会碰真实工作库。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from summit_everything.integrations.first_use_defaults import (
    DEFAULTS_ENV_VAR as FIRST_USE_DEFAULTS_ENV_VAR,
)
from summit_everything.integrations.first_use_defaults import (
    REPO_DEFAULTS_RELATIVE_PATH,
)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DEV_ROOT = ROOT / ".local" / "dev"
DEV_PROFILE = DEV_ROOT / "profile"
DEV_WORKSPACE = DEV_ROOT / "workspace"
NATIVE_PACKAGE = ROOT / "native"


def first_use_defaults_environment(env: dict[str, str]) -> dict[str, str]:
    """Point the dev API at the Git-ignored local defaults file when it exists.

    The runtime never reads the repository file implicitly, so the development
    preview opts in explicitly here. An already configured environment variable
    wins, and a missing file changes nothing.
    """
    configured = dict(env)
    path = ROOT / REPO_DEFAULTS_RELATIVE_PATH
    if path.is_file():
        configured.setdefault(FIRST_USE_DEFAULTS_ENV_VAR, str(path))
    return configured


class DevError(RuntimeError):
    """A startup problem with a human-readable next step."""


# ── Node 原生绑定 ────────────────────────────────────────────────────────────
def node_arch(node: str) -> str:
    result = subprocess.run(
        [node, "-p", "process.arch"], capture_output=True, text=True, check=False
    )
    arch = result.stdout.strip()
    if result.returncode != 0 or not arch:
        raise DevError("无法读取 node 架构；请检查 node 是否可执行。")
    return arch


def installed_package_version(package_json: Path) -> str | None:
    try:
        return str(json.loads(package_json.read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, ValueError):
        return None


def ensure_native_binding(
    host_package: str, scope: str, name: str, platform_id: str, arch: str
) -> str | None:
    """Ensure one native optional dependency matches the running node.

    npm 的可选依赖按安装时的架构挑选；换一个 node（例如 nvm 的 x64 与系统
    arm64）后 Vite / oxlint 会直接报 "Cannot find native binding"，看起来像
    依赖坏了。这里按当前 node 架构补齐缺失的平台包，不重装整个 node_modules，
    也不改全局 npmrc。
    """
    package = f"{scope}/{name}-{platform_id}"
    target = WEB / "node_modules" / scope / f"{name}-{platform_id}"
    if any(target.glob("*.node")):
        return None

    version = installed_package_version(WEB / "node_modules" / host_package / "package.json")
    if not version:
        return f"{host_package} 未安装；请先在 web/ 运行 npm ci。"
    if shutil.which("npm") is None:
        return f"缺少 {package}@{version}，但找不到 npm；请手动安装该平台包。"

    print(f"[dev] 补齐 {package}@{version}（当前 node: {arch}）…", flush=True)
    with tempfile.TemporaryDirectory(prefix="summit-binding-") as tmp:
        result = subprocess.run(
            ["npm", "pack", f"{package}@{version}", "--silent", "--pack-destination", tmp],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return (
                f"无法下载 {package}@{version}：{result.stderr.strip() or 'npm pack 失败'}。"
                " 请检查网络，或在 web/ 重新运行 npm ci。"
            )
        archives = list(Path(tmp).glob("*.tgz"))
        if not archives:
            return f"npm pack 没有产出 {package} 的压缩包。"
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archives[0]) as archive:
            members = [m for m in archive.getmembers() if m.name.startswith("package/")]
            for member in members:
                member.name = member.name[len("package/") :]
            archive.extractall(target, members=members, filter="data")
    if not any(target.glob("*.node")):
        return f"{package} 解压后仍然没有 .node 文件。"
    return None


def ensure_native_bindings() -> str | None:
    node = shutil.which("node")
    if not node:
        # PATH 里没有 node（例如集成测试只放了一个 npm shim）时，API 仍应能启动；
        # Vite 子进程会自己报明确错误，这里不要抢先退出。
        return None
    arch = node_arch(node)
    system = platform.system().lower()
    if system == "darwin":
        platform_id = f"darwin-{arch}"
    elif system == "linux":
        platform_id = f"linux-{arch}"
    else:
        return None
    for host_package, scope, name in (
        ("rolldown", "@rolldown", "binding"),
        ("oxlint", "@oxlint", "binding"),
    ):
        problem = ensure_native_binding(host_package, scope, name, platform_id, arch)
        if problem:
            return problem
    return None


# ── 进程工具 ────────────────────────────────────────────────────────────────
def http_json(url: str, token: str | None = None) -> dict[str, object] | None:
    request = Request(url, headers={"Accept": "application/json"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read())
    except (OSError, URLError, HTTPError, ValueError):
        return None


def post_json(
    url: str, token: str, body: dict[str, object]
) -> tuple[int, dict[str, object] | None]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except HTTPError as error:
        try:
            payload = json.loads(error.read() or b"{}")
        except ValueError:
            payload = None
        return error.code, payload
    except (OSError, URLError, ValueError):
        return 0, None


def put_json(url: str, token: str, body: dict[str, object]) -> int:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status
    except (OSError, URLError, HTTPError) as error:
        return getattr(error, "code", 0)


def mark_first_use_complete(api_origin: str, token: str) -> None:
    """Development workspaces should open straight into 今日.

    Without a progress record the shell shows a one-off "no first-use record"
    toast on every boot. A dev library has nothing to configure, so record a
    completed wizard once; later boots stay silent.
    """
    if http_json(f"{api_origin}/api/v1/first-use/progress", token) is not None:
        return
    put_json(
        f"{api_origin}/api/v1/first-use/progress",
        token,
        {"step": 5, "completed": True, "open": False},
    )


def probe(url: str) -> bool:
    try:
        with urlopen(url, timeout=1) as response:
            return response.status == 200
    except (OSError, URLError, HTTPError):
        return False


def wait_until_ready(
    api_url: str,
    web_url: str,
    children: list[subprocess.Popen[bytes]],
    deadline: float,
    interrupted: Callable[[], bool],
) -> str:
    """Wait for both services, but never ignore a dead child or Ctrl+C.

    Returns "ready", "interrupted", "child-exited" or "timeout". The old
    implementation only checked child processes after both probes succeeded,
    so a port collision (or a hung npm shim) could sit for the full timeout.
    """
    api_ready = web_ready = False
    while time.monotonic() < deadline:
        if interrupted():
            return "interrupted"
        if any(child.poll() is not None for child in children):
            return "child-exited"
        api_ready = api_ready or probe(api_url)
        web_ready = web_ready or probe(web_url)
        if api_ready and web_ready:
            return "ready"
        time.sleep(0.2)
    return "timeout"


def open_dev_workspace(api_origin: str, token: str) -> str:
    """Attach the dev server to a stable local workspace.

    Never raises: a workspace problem should not stop the dev server from
    booting — the UI gate still lets the developer pick a directory by hand.
    """
    current = http_json(f"{api_origin}/api/v1/workspaces/current", token)
    if current and current.get("workspace_id"):
        return f"已打开开发工作库：{current.get('name', '开发库')}"

    DEV_WORKSPACE.mkdir(parents=True, exist_ok=True)
    manifest = DEV_WORKSPACE / ".summit-everything" / "manifest.json"
    body: dict[str, object] = {
        "root": str(DEV_WORKSPACE),
        "mode": "open" if manifest.is_file() else "create",
        "operation_id": secrets.token_hex(16),
    }
    if body["mode"] == "create":
        body["name"] = "开发库"

    status, payload = post_json(f"{api_origin}/api/v1/workspaces", token, body)
    if status in (200, 201):
        name = (payload or {}).get("name") or "开发库"
        return f"已打开开发工作库：{name}"
    if body["mode"] == "open":
        # 目录里有残留但不是有效工作库：明确重建，而不是停在错误页。
        body = {**body, "mode": "create", "name": "开发库"}
        status, payload = post_json(f"{api_origin}/api/v1/workspaces", token, body)
        if status in (200, 201):
            return "已重建开发工作库：开发库"
    message = None
    if payload:
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
    return f"未能自动打开开发工作库（{status}）：{message or '请在页面上手动选择目录'}"


def keep_workspace_open(
    api_origin: str, token: str, stop: threading.Event, announce: Callable[[str], None]
) -> None:
    """Re-open the dev workspace after a backend reload.

    uvicorn --reload restarts the process, which drops the in-memory active
    workspace; a browser refresh would otherwise land on the "choose a
    workspace" gate again. Poll the health flag (no auth needed) and reopen
    only when the backend explicitly reports `workspace_open: false`.
    """
    while not stop.wait(2):
        health = http_json(f"{api_origin}/api/v1/health")
        if health is None or health.get("workspace_open") is not False:
            continue
        note = open_dev_workspace(api_origin, token)
        announce(note)


# ── 原生壳 ──────────────────────────────────────────────────────────────────
def build_native_app() -> Path:
    binary = NATIVE_PACKAGE / ".build" / "debug" / "SummitEverything"
    sources = list((NATIVE_PACKAGE / "Sources").rglob("*.swift"))
    newest_source = max((path.stat().st_mtime for path in sources), default=0)
    if binary.is_file() and binary.stat().st_mtime >= newest_source:
        return binary
    if shutil.which("swift") is None:
        raise DevError("找不到 swift；安装 Xcode Command Line Tools 后才能用 --app。")
    print("[dev] 编译原生壳（源码变化时一次，通常十几秒）…", flush=True)
    result = subprocess.run(
        [
            "swift",
            "build",
            "--package-path",
            str(NATIVE_PACKAGE),
            "-c",
            "debug",
            "--disable-sandbox",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-12:]
        raise DevError("原生壳编译失败：\n" + "\n".join(detail))
    if not binary.is_file():
        raise DevError(f"编译完成但没有找到可执行文件：{binary}")
    return binary


# ── 主流程 ──────────────────────────────────────────────────────────────────
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SummitEverything 本地开发服务")
    parser.add_argument("--app", action="store_true", help="启动原生 macOS 壳并指向 Vite（热更新）")
    parser.add_argument(
        "--api-port", type=int, default=int(os.environ.get("SUMMIT_API_PORT", "8793"))
    )
    parser.add_argument(
        "--web-port", type=int, default=int(os.environ.get("SUMMIT_WEB_PORT", "5173"))
    )
    parser.add_argument("--no-workspace", action="store_true", help="不自动打开开发工作库")
    parser.add_argument(
        "--fresh", action="store_true", help="清空 .local/dev 后重建 profile 与工作库"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not (WEB / "node_modules").is_dir():
        print("Web 依赖缺失。先运行：cd web && npm ci", file=sys.stderr)
        return 2

    if args.fresh:
        if DEV_ROOT.exists():
            print(f"[dev] 清空 {DEV_ROOT.relative_to(ROOT)} …", flush=True)
            shutil.rmtree(DEV_ROOT)

    problem = ensure_native_bindings()
    if problem:
        print(f"[dev] {problem}", file=sys.stderr)
        return 2

    env = first_use_defaults_environment(os.environ)
    api_port = args.api_port
    web_port = args.web_port
    env.setdefault("SUMMIT_RUN_ID", secrets.token_hex(16))
    token = env.get("SUMMIT_SESSION_TOKEN")
    token_file = env.get("SUMMIT_SESSION_TOKEN_FILE")
    if not token and token_file:
        token_path = Path(token_file)
        try:
            token_stat = token_path.lstat()
            if (
                not stat.S_ISREG(token_stat.st_mode)
                or token_stat.st_uid != os.getuid()
                or stat.S_IMODE(token_stat.st_mode) & 0o077
            ):
                raise RuntimeError("SUMMIT_SESSION_TOKEN_FILE must be an owner-only regular file")
            token = token_path.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError:
            raise RuntimeError("Cannot read SUMMIT_SESSION_TOKEN_FILE") from None
        if not token or any(
            not (char.isascii() and (char.isalnum() or char in "-_.~")) for char in token
        ):
            raise RuntimeError("SUMMIT_SESSION_TOKEN_FILE does not contain a valid token")
        env["SUMMIT_SESSION_TOKEN"] = token
    if not token:
        env["SUMMIT_SESSION_TOKEN"] = secrets.token_urlsafe(32)
    token = env["SUMMIT_SESSION_TOKEN"]
    env.setdefault("SUMMIT_PROFILE_ROOT", str(DEV_PROFILE))
    env.setdefault("SUMMIT_API_TARGET", f"http://127.0.0.1:{api_port}")
    # 只有仓库内开发 profile 才自动建库/写进度；集成测试会注入临时 profile，
    # 那里不应该在仓库里留下任何工作库或首次配置记录。
    dev_profile_active = (
        Path(env["SUMMIT_PROFILE_ROOT"]).expanduser().resolve() == DEV_PROFILE.resolve()
    )
    if dev_profile_active:
        DEV_PROFILE.mkdir(parents=True, exist_ok=True)
        DEV_WORKSPACE.mkdir(parents=True, exist_ok=True)
    api_origin = f"http://127.0.0.1:{api_port}"
    api_health = f"{api_origin}/api/v1/health"
    web_url = f"http://127.0.0.1:{web_port}/"
    children: list[subprocess.Popen[bytes]] = []
    interrupted = False
    workspace_watch_stop = threading.Event()

    def stop_children(*_: object) -> None:
        nonlocal interrupted
        interrupted = True
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                child.wait()

    signal.signal(signal.SIGINT, stop_children)
    signal.signal(signal.SIGTERM, stop_children)

    try:
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "summit_everything.api.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--reload",
                    "--reload-dir",
                    str(ROOT / "src"),
                ],
                cwd=ROOT,
                env=env,
                start_new_session=True,
            )
        )
        children.append(
            subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=WEB,
                env={**env, "SUMMIT_WEB_PORT": str(web_port)},
                start_new_session=True,
            )
        )

        deadline = time.monotonic() + 45
        state = wait_until_ready(api_health, web_url, children, deadline, lambda: interrupted)
        if state == "interrupted":
            return 0
        if state == "child-exited":
            return next(child.returncode or 1 for child in children if child.poll() is not None)
        if state == "timeout":
            print("本机 API 或 Vite 在 45 秒内没有就绪。检查上面的报错。", file=sys.stderr)
            return 1

        if not args.no_workspace and dev_profile_active:
            print(f"[dev] {open_dev_workspace(api_origin, token)}", flush=True)
            mark_first_use_complete(api_origin, token)
            threading.Thread(
                target=keep_workspace_open,
                args=(
                    api_origin,
                    token,
                    workspace_watch_stop,
                    lambda note: print(f"[dev] {note}", flush=True),
                ),
                daemon=True,
                name="summit-dev-workspace",
            ).start()

        if args.app:
            binary = build_native_app()
            children.append(
                subprocess.Popen(
                    [str(binary)],
                    cwd=ROOT,
                    env={
                        **os.environ,
                        "SUMMIT_DEV_SERVER_URL": web_url,
                        "SUMMIT_PROFILE_ROOT": str(DEV_PROFILE),
                    },
                    start_new_session=True,
                )
            )
            print("[dev] 原生壳已启动；窗口内同样是 Vite 热更新。", flush=True)

        print(f"[dev] API   {api_health}", flush=True)
        print(f"[dev] WebUI {web_url}", flush=True)
        print("[dev] 前端改动即时生效；后端改动由 uvicorn 自动重载。Ctrl+C 停止。", flush=True)

        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        if interrupted:
            return 0
        return next(child.returncode or 0 for child in children if child.poll() is not None)
    finally:
        workspace_watch_stop.set()
        stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
