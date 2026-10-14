"""Independent checks for ordering/request-id claims (runs on whichever tree PYTHONPATH selects)."""

from __future__ import annotations

import json
import secrets
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "qa-ordering-token"
H = {"Authorization": f"Bearer {TOKEN}"}
out: dict = {}

tmp = Path(tempfile.mkdtemp(prefix="qa-order-"))
app = create_app(
    session_token=TOKEN,
    profile_root=tmp / "profile",
    secret_backend=MemorySecretBackend(),
)
api = TestClient(app, raise_server_exceptions=False)

# Structural: middleware order as the app declares it.
out["user_middleware_order"] = [m.cls.__name__ for m in app.user_middleware]

opened = api.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws"), "mode": "create", "name": "qa", "operation_id": "o1"},
)
out["open_status"] = opened.status_code
current = api.get("/api/v1/workspaces/current", headers=H)
profile_dir = Path(current.json()["local_profile_dir"])
profile_dir.mkdir(parents=True, exist_ok=True)
(profile_dir / "provider-settings.json").write_text(
    json.dumps({"embedding": "not-an-object"}), encoding="utf-8"
)

# Runtime: count token_hex allocations during one corrupt-profile request.
calls: list[str] = []
original = secrets.token_hex


def counting_token_hex(n: int = 8, *a, **k):
    value = original(n, *a, **k)
    calls.append(value)
    return value


secrets.token_hex = counting_token_hex  # type: ignore[assignment]
try:
    resp = api.get("/api/v1/settings", headers=H)
finally:
    secrets.token_hex = original  # type: ignore[assignment]

body = resp.json() if "json" in resp.headers.get("content-type", "") else {}
returned_id = (body.get("error") or {}).get("request_id")
out["corrupt_status"] = resp.status_code
out["token_hex_calls"] = len(calls)
out["returned_request_id"] = returned_id
out["request_id_matches_sole_allocation"] = bool(calls) and returned_id == calls[0]
out["request_id_shape_ok"] = isinstance(returned_id, str) and len(returned_id) == 16

# Runtime: does the escaping exception on the old tree prove an unhandled SettingsError?
paired = TestClient(
    create_app(
        session_token=TOKEN,
        profile_root=tmp / "profile2",
        secret_backend=MemorySecretBackend(),
    )
)
p2 = paired.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws2"), "mode": "create", "name": "qa2", "operation_id": "o2"},
)
cur2 = paired.get("/api/v1/workspaces/current", headers=H)
pdir2 = Path(cur2.json()["local_profile_dir"])
pdir2.mkdir(parents=True, exist_ok=True)
(pdir2 / "provider-settings.json").write_text(json.dumps({"rerank": {"base_url": 5}}), encoding="utf-8")
try:
    paired.get("/api/v1/settings", headers=H)
    out["escaping_exception"] = None
except Exception as exc:
    out["escaping_exception"] = f"{type(exc).__module__}.{type(exc).__name__}: {exc}"

# Runtime: a genuinely unauthenticated request under a corrupt profile.
bare = TestClient(app, raise_server_exceptions=False)
resp_noauth = bare.get("/api/v1/settings")
out["noauth_status"] = resp_noauth.status_code
out["noauth_body"] = resp_noauth.text[:160]

print(json.dumps(out, ensure_ascii=False, indent=2))
Path(__file__).with_name("ordering-result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
