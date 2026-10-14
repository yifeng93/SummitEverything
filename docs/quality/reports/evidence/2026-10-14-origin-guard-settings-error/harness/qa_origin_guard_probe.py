"""Independent QA probe for the origin_guard / SettingsError envelope fix.

Black-box: drives the real FastAPI app through TestClient with
raise_server_exceptions=False so we observe exactly what an HTTP client sees.
Source tree is selected purely via PYTHONPATH, so this identical file runs
against the fixed worktree and against an exported main tree.

Usage:  python .local/qa/qa_origin_guard_probe.py <label>
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

TOKEN = "qa-independent-synthetic-token"
H = {"Authorization": f"Bearer {TOKEN}"}
RESULTS: list[dict] = []
RAISED: list[dict] = []


def new_client(profile_root: Path, *, raise_server_exceptions: bool = False) -> TestClient:
    app = create_app(
        session_token=TOKEN,
        profile_root=profile_root,
        secret_backend=MemorySecretBackend(),
    )
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def open_workspace(api: TestClient, root: Path) -> dict:
    resp = api.post(
        "/api/v1/workspaces",
        headers=H,
        json={
            "root": str(root),
            "mode": "create",
            "name": "QA 模拟库",
            "operation_id": "qa-open-1",
        },
    )
    return {"status": resp.status_code, "body": _short(resp)}


def _short(resp) -> dict:
    ctype = resp.headers.get("content-type", "")
    text = resp.text
    parsed = None
    if "json" in ctype:
        try:
            parsed = resp.json()
        except Exception as exc:  # pragma: no cover
            parsed = {"__unparsable__": repr(exc)}
    error = parsed.get("error") if isinstance(parsed, dict) else None
    return {
        "status": resp.status_code,
        "content_type": ctype,
        "body_head": text[:220],
        "is_json": "json" in ctype,
        "error_keys": sorted(error) if isinstance(error, dict) else None,
        "error_code": error.get("code") if isinstance(error, dict) else None,
        "error_message": error.get("message") if isinstance(error, dict) else None,
        "request_id": error.get("request_id") if isinstance(error, dict) else None,
        "raw_error_present": isinstance(parsed, dict) and "error" in parsed,
    }


def probe(label: str, api: TestClient, method: str, path: str, *, origin=None, json_body=None, extra=None):
    headers = dict(H)
    if origin is not None:
        headers["Origin"] = origin
    entry: dict = {"label": label, "method": method, "path": path, "origin": origin}
    if extra:
        entry.update(extra)
    try:
        # A second, exception-raising client tells us whether the failure was a
        # genuine unhandled escape (as opposed to a rendered response).
        resp = api.request(method, path, headers=headers, json=json_body)
        entry.update(_short(resp))
        entry["client_exception"] = None
    except Exception as exc:  # harness must never crash on the buggy tree
        entry.update(
            {
                "status": None,
                "client_exception": f"{type(exc).__name__}: {exc}",
                "traceback_tail": traceback.format_exc().strip().splitlines()[-1],
            }
        )
        RAISED.append({"label": label, "exception": entry["client_exception"]})
    RESULTS.append(entry)
    print(json.dumps(entry, ensure_ascii=False))
    return entry


def write_corrupt(profile_dir: Path, document) -> Path:
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "provider-settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "unlabelled"
    tmp = Path(tempfile.mkdtemp(prefix=f"qa-{label}-"))
    profile_root = tmp / "profile"
    api = new_client(profile_root)

    meta: dict = {"label": label, "tmp": str(tmp), "app_module": None}
    import summit_everything.api.app as app_mod

    meta["app_module"] = app_mod.__file__
    meta["has_helper"] = hasattr(app_mod, "settings_error_response")
    print(json.dumps({"META": meta}, ensure_ascii=False))

    # --- open a workspace -------------------------------------------------
    opened = open_workspace(api, tmp / "workspace")
    print(json.dumps({"OPEN_WORKSPACE": opened}, ensure_ascii=False))

    current = api.get("/api/v1/workspaces/current", headers=H)
    if current.status_code != 200:
        print(json.dumps({"FATAL": "workspace not open", "status": current.status_code}))
        return 2
    profile_dir = Path(current.json()["local_profile_dir"])
    meta["local_profile_dir"] = str(profile_dir)
    meta["profile_dir_under_root"] = str(profile_dir).startswith(str(profile_root))
    meta["settings_file_exists_before"] = (profile_dir / "provider-settings.json").exists()
    print(json.dumps({"PROFILE": meta}, ensure_ascii=False))

    # --- healthy baseline -------------------------------------------------
    probe("healthy.get_settings", api, "GET", "/api/v1/settings")
    cb = "http://127.0.0.1:18793/api/v1/integrations/feishu/callback"
    probe(
        "healthy.patch_settings.callback",
        api,
        "PATCH",
        "/api/v1/settings",
        json_body={"feishu": {"app_id": "", "redirect_uri": cb}},
    )
    probe("healthy.patch_settings.noop", api, "PATCH", "/api/v1/settings", json_body={})
    probe("healthy.get_settings.readback", api, "GET", "/api/v1/settings")
    probe(
        "healthy.allowed_origin",
        api,
        "GET",
        "/api/v1/settings",
        origin="http://127.0.0.1:18793",
    )
    probe(
        "healthy.foreign_origin",
        api,
        "GET",
        "/api/v1/settings",
        origin="http://evil.invalid",
    )
    probe(
        "healthy.foreign_origin.no_origin_read",
        api,
        "GET",
        "/api/v1/workspaces/current",
        origin="http://evil.invalid",
    )

    # --- route-level SettingsError (exception handler path) ---------------
    probe(
        "route_level.validation_error",
        api,
        "DELETE",
        "/api/v1/credentials/deepseek",
        json_body={"account_id": "definitely-not-the-configured-account"},
    )

    # --- corrupt case 1 ---------------------------------------------------
    p = write_corrupt(profile_dir, {"embedding": "not-an-object"})
    meta["corrupt1_bytes"] = p.read_text()
    probe("corrupt1.get_settings", api, "GET", "/api/v1/settings")
    probe("corrupt1.get_workspaces_current", api, "GET", "/api/v1/workspaces/current")
    probe("corrupt1.patch_settings", api, "PATCH", "/api/v1/settings", json_body={})
    probe(
        "corrupt1.get_settings.with_allowed_origin",
        api,
        "GET",
        "/api/v1/settings",
        origin="http://127.0.0.1:18793",
    )
    probe(
        "corrupt1.get_settings.with_foreign_origin",
        api,
        "GET",
        "/api/v1/settings",
        origin="http://evil.invalid",
    )
    probe(
        "corrupt1.get_settings.no_auth",
        api,
        "GET",
        "/api/v1/settings",
        extra={"note": "no token -> guard must still not leak"},
    )

    # --- corrupt case 2 ---------------------------------------------------
    p2 = write_corrupt(profile_dir, {"rerank": {"base_url": 5}})
    meta["corrupt2_bytes"] = p2.read_text()
    probe("corrupt2.get_settings", api, "GET", "/api/v1/settings")
    probe("corrupt2.get_workspaces_current", api, "GET", "/api/v1/workspaces/current")
    probe("corrupt2.patch_settings", api, "PATCH", "/api/v1/settings", json_body={})

    # --- leak checks ------------------------------------------------------
    leaks = []
    for entry in RESULTS:
        head = entry.get("body_head") or ""
        for needle in ("not-an-object", "base_url", "embedding", "rerank", str(profile_dir)):
            if needle in head:
                leaks.append({"label": entry["label"], "needle": needle})
    print(json.dumps({"LEAKS": leaks}, ensure_ascii=False))
    print(json.dumps({"RAISED": RAISED}, ensure_ascii=False))

    with open(Path(__file__).with_name(f"probe-{label}.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "results": RESULTS, "leaks": leaks, "raised": RAISED}, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
