"""Fail-closed sweep: with a corrupt profile no request may be treated as allowed."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "qa-sweep-token"
H = {"Authorization": f"Bearer {TOKEN}"}
tmp = Path(tempfile.mkdtemp(prefix="qa-sweep-"))
api = TestClient(
    create_app(
        session_token=TOKEN,
        profile_root=tmp / "profile",
        secret_backend=MemorySecretBackend(),
    ),
    raise_server_exceptions=False,
)
api.post(
    "/api/v1/workspaces",
    headers=H,
    json={"root": str(tmp / "ws"), "mode": "create", "name": "qa", "operation_id": "o"},
)
cur = api.get("/api/v1/workspaces/current", headers=H)
pdir = Path(cur.json()["local_profile_dir"])
pdir.mkdir(parents=True, exist_ok=True)
corrupt = json.dumps({"embedding": "not-an-object", "rerank": {"base_url": 5}})
(pdir / "provider-settings.json").write_text(corrupt, encoding="utf-8")

PATHS = [
    ("GET", "/api/v1/settings"),
    ("PATCH", "/api/v1/settings"),
    ("GET", "/api/v1/workspaces/current"),
    ("GET", "/api/v1/workspaces"),
    ("POST", "/api/v1/workspaces"),
    ("GET", "/api/v1/lines"),
    ("GET", "/api/v1/jobs"),
    ("GET", "/api/v1/credentials/deepseek"),
    ("DELETE", "/api/v1/credentials/deepseek"),
    ("GET", "/api/v1/integrations/feishu/status"),
    ("GET", "/api/v1/integrations/feishu/callback"),
    ("POST", "/callback"),
    ("GET", "/"),
    ("GET", "/api/v1/openapi.json"),
    ("GET", "/api/v1/does-not-exist"),
]
ORIGINS = [None, "http://127.0.0.1:18793", "http://evil.invalid"]

findings = []
for method, path in PATHS:
    for origin in ORIGINS:
        headers = dict(H)
        if origin:
            headers["Origin"] = origin
        resp = api.request(method, path, headers=headers, json={} if method in {"PATCH", "POST", "DELETE"} else None)
        body = resp.text
        entry = {
            "method": method,
            "path": path,
            "origin": origin,
            "status": resp.status_code,
            "ctype": resp.headers.get("content-type", ""),
            "envelope_ok": False,
            "echoes_corrupt": False,
        }
        try:
            err = resp.json().get("error")
            entry["envelope_ok"] = (
                isinstance(err, dict)
                and set(err) == {"code", "message", "request_id"}
                and err.get("code") == "settings_unavailable"
                and bool(err.get("message"))
                and bool(err.get("request_id"))
            )
        except Exception:
            pass
        for needle in ("not-an-object", "base_url", "embedding", "rerank", str(pdir)):
            if needle in body:
                entry["echoes_corrupt"] = True
        findings.append(entry)

allowed = [f for f in findings if f["status"] in (200, 201, 204)]
bad_envelope = [f for f in findings if not f["envelope_ok"]]
leaks = [f for f in findings if f["echoes_corrupt"]]
summary = {
    "total_probes": len(findings),
    "status_histogram": {},
    "any_allowed_2xx": allowed,
    "not_envelope": bad_envelope,
    "leaks": leaks,
    "callback_and_static_statuses": [
        f for f in findings if f["path"] in {"/", "/callback", "/api/v1/integrations/feishu/callback"}
    ],
}
for f in findings:
    summary["status_histogram"][str(f["status"])] = (
        summary["status_histogram"].get(str(f["status"]), 0) + 1
    )
print(json.dumps(summary, ensure_ascii=False, indent=2)[:6000])
Path(__file__).with_name("sweep-result.json").write_text(
    json.dumps({"summary": summary, "findings": findings}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
