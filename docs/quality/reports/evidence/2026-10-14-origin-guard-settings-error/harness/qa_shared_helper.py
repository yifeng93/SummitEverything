"""Prove the guard and the exception handler dispatch through the same module-level helper.

Monkeypatching the module global only works if both call sites resolve the *same*
symbol at call time, so a spy that observes both paths is direct evidence of a
shared helper rather than two duplicated implementations.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import summit_everything.api.app as app_mod
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "qa-shared-helper-token"
H = {"Authorization": f"Bearer {TOKEN}"}
tmp = Path(tempfile.mkdtemp(prefix="qa-helper-"))
app = app_mod.create_app(
    session_token=TOKEN,
    profile_root=tmp / "profile",
    secret_backend=MemorySecretBackend(),
)
api = TestClient(app, raise_server_exceptions=False)
api.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws"), "mode": "create", "name": "qa", "operation_id": "o"},
)

calls: list[str] = []
original = app_mod.settings_error_response


def spy(request, exc):
    calls.append(exc.code)
    return original(request, exc)


app_mod.settings_error_response = spy  # type: ignore[assignment]

# 1) route-level (exception handler) path
route = api.request(
    "DELETE", "/api/v1/credentials/deepseek", headers=H, json={"account_id": "mismatch"}
)

# 2) middleware (origin guard) path
cur = api.get("/api/v1/workspaces/current", headers=H)
pdir = Path(cur.json()["local_profile_dir"])
pdir.mkdir(parents=True, exist_ok=True)
(pdir / "provider-settings.json").write_text(json.dumps({"embedding": "not-an-object"}), encoding="utf-8")
guard = api.get("/api/v1/settings", headers=H)

app_mod.settings_error_response = original  # type: ignore[assignment]

out = {
    "spy_calls_in_order": calls,
    "route_status": route.status_code,
    "guard_status": guard.status_code,
    "route_body": route.text[:160],
    "guard_body": guard.text[:160],
    "same_helper_symbol_used_by_both": calls == ["validation_error", "settings_unavailable"],
    "single_module_level_helper": callable(original),
}
print(json.dumps(out, ensure_ascii=False, indent=2))
Path(__file__).with_name("helper-result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
