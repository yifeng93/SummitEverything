"""Envelope parity: guard path vs route-level SettingsError handler (503 and 422)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app, settings_error_response
from summit_everything.integrations.settings import (
    MemorySecretBackend,
    UnavailableSecretBackend,
)

TOKEN = "qa-parity-token"
H = {"Authorization": f"Bearer {TOKEN}"}
out: dict = {}


def shape(resp):
    ctype = resp.headers.get("content-type", "")
    parsed = resp.json() if "json" in ctype else None
    err = parsed.get("error") if isinstance(parsed, dict) else None
    return {
        "status": resp.status_code,
        "top_level_keys": sorted(parsed) if isinstance(parsed, dict) else None,
        "error_keys": sorted(err) if isinstance(err, dict) else None,
        "code": err.get("code") if isinstance(err, dict) else None,
        "message_nonempty": bool(err.get("message")) if isinstance(err, dict) else False,
        "request_id_nonempty": bool(err.get("request_id")) if isinstance(err, dict) else False,
        "request_id_len": len(err.get("request_id", "")) if isinstance(err, dict) else None,
        "body": resp.text[:200],
    }


tmp = Path(tempfile.mkdtemp(prefix="qa-parity-"))

# --- route-level 503: unusable credential store ------------------------------
api503 = TestClient(
    create_app(
        session_token=TOKEN,
        profile_root=tmp / "p503",
        secret_backend=UnavailableSecretBackend(),
    ),
    raise_server_exceptions=False,
)
api503.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws503"), "mode": "create", "name": "qa", "operation_id": "o"},
)
summary = api503.get("/api/v1/settings", headers=H)
out["settings_status_for_503_app"] = summary.status_code
acct = None
try:
    acct = summary.json()["llm"]["account_id"]
except Exception:
    pass
out["deepseek_account_id"] = acct
route503 = api503.request(
    "DELETE", "/api/v1/credentials/deepseek", headers=H, json={"account_id": acct}
)
out["route_level_503"] = shape(route503)

# --- route-level 422: validation_error --------------------------------------
api422 = TestClient(
    create_app(
        session_token=TOKEN,
        profile_root=tmp / "p422",
        secret_backend=MemorySecretBackend(),
    ),
    raise_server_exceptions=False,
)
api422.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws422"), "mode": "create", "name": "qa", "operation_id": "o"},
)
route422 = api422.request(
    "DELETE", "/api/v1/credentials/deepseek", headers=H, json={"account_id": "not-configured"}
)
out["route_level_422"] = shape(route422)

# --- guard-level 503 ---------------------------------------------------------
api503b = TestClient(
    create_app(
        session_token=TOKEN,
        profile_root=tmp / "pguard",
        secret_backend=MemorySecretBackend(),
    ),
    raise_server_exceptions=False,
)
api503b.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "wsguard"), "mode": "create", "name": "qa", "operation_id": "o"},
)
cur = api503b.get("/api/v1/workspaces/current", headers=H)
pdir = Path(cur.json()["local_profile_dir"])
pdir.mkdir(parents=True, exist_ok=True)
(pdir / "provider-settings.json").write_text(
    json.dumps({"embedding": "not-an-object"}), encoding="utf-8"
)
out["guard_level_503"] = shape(api503b.get("/api/v1/settings", headers=H))

# --- parity verdicts ---------------------------------------------------------
g = out["guard_level_503"]
r5 = out["route_level_503"]
r4 = out["route_level_422"]
out["parity_guard_vs_route503_keyset"] = g["error_keys"] == r5["error_keys"]
out["parity_guard_vs_route422_keyset"] = g["error_keys"] == r4["error_keys"]
out["parity_top_level"] = g["top_level_keys"] == r5["top_level_keys"] == r4["top_level_keys"]
out["parity_request_id_shape"] = (
    g["request_id_len"] == r5["request_id_len"] == r4["request_id_len"] == 16
)
out["helper_is_module_level_callable"] = callable(settings_error_response)

print(json.dumps(out, ensure_ascii=False, indent=2))
Path(__file__).with_name("parity-result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
