from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON = ROOT / ".venv" / "bin" / "python"
CONSOLE = ROOT / ".venv" / "bin" / "summit-everything-mcp"
SECRET = "MCP-SENTINEL-DO-NOT-LEAK with spaces"


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mcp-config-probe-") as temp:
        temp_path = Path(temp)
        bad_file = temp_path / "bad-token"
        bad_file.write_text("bad token\n", encoding="utf-8")
        bad_file.chmod(0o600)
        broad_file = temp_path / "broad-token"
        broad_file.write_text("synthetic-token\n", encoding="utf-8")
        broad_file.chmod(0o644)
        cases: dict[str, tuple[dict[str, str | None], str]] = {
            "dns_non_ip": ({"SUMMIT_API_URL": "http://example.com:8793", "SUMMIT_MCP_TOKEN": "safe-token"}, "有效的 loopback IP"),
            "non_loopback_ip": ({"SUMMIT_API_URL": "http://8.8.8.8:8793", "SUMMIT_MCP_TOKEN": "safe-token"}, "仅允许无凭据的 HTTP loopback"),
            "url_path": ({"SUMMIT_API_URL": "http://127.0.0.1:8793/api", "SUMMIT_MCP_TOKEN": "safe-token"}, "不得包含路径"),
            "https": ({"SUMMIT_API_URL": "https://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": "safe-token"}, "仅允许无凭据的 HTTP loopback"),
            "missing_token": ({"SUMMIT_API_URL": "http://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": None, "SUMMIT_MCP_TOKEN_FILE": None}, "SUMMIT_MCP_TOKEN"),
            "malformed_token": ({"SUMMIT_API_URL": "http://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": SECRET}, "token 不能为空"),
            "missing_token_file": ({"SUMMIT_API_URL": "http://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": None, "SUMMIT_MCP_TOKEN_FILE": str(temp_path / "missing")}, "无法安全读取 token 文件"),
            "malformed_token_file": ({"SUMMIT_API_URL": "http://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": None, "SUMMIT_MCP_TOKEN_FILE": str(bad_file)}, "token 不能为空"),
            "insecure_token_file_mode": ({"SUMMIT_API_URL": "http://127.0.0.1:8793", "SUMMIT_MCP_TOKEN": None, "SUMMIT_MCP_TOKEN_FILE": str(broad_file)}, "token 文件必须归当前用户所有"),
        }
        for entrypoint, command in (("module", [str(PYTHON), "-m", "summit_everything.mcp_server"]), ("console_script", [str(CONSOLE)])):
            for name, (overrides, expected) in cases.items():
                env = dict(os.environ)
                for key in ("SUMMIT_API_URL", "SUMMIT_MCP_TOKEN", "SUMMIT_MCP_TOKEN_FILE", "SUMMIT_WORKSPACE_ID"):
                    env.pop(key, None)
                env.update({k: v for k, v in overrides.items() if v is not None})
                if overrides.get("SUMMIT_MCP_TOKEN") is None:
                    env.pop("SUMMIT_MCP_TOKEN", None)
                if overrides.get("SUMMIT_MCP_TOKEN_FILE") is None:
                    env.pop("SUMMIT_MCP_TOKEN_FILE", None)
                if entrypoint == "module":
                    env["PYTHONPATH"] = str(ROOT / "src")
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=15, check=False)
                safe = SECRET not in result.stdout + result.stderr and "Traceback" not in result.stderr
                passed = result.returncode == 2 and result.stdout == "" and expected in result.stderr and safe
                print(f"{entrypoint}/{name}: {'PASS' if passed else 'FAIL'} exit={result.returncode} stdout_empty={not result.stdout} expected_message={expected in result.stderr} no_traceback={'Traceback' not in result.stderr} no_secret={SECRET not in result.stdout + result.stderr}")
                if not passed:
                    print(f"  stderr={result.stderr[:500]!r}")
                    failures.append(f"{entrypoint}/{name}")
    print(f"summary: {18-len(failures)}/18 passed")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
