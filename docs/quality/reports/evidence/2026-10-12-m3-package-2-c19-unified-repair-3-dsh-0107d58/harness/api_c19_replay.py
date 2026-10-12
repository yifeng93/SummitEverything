"""C19 end-to-end replay over the real loopback API and SSE stream.

Offline only: Fake providers, isolated profile, synthetic workspace, loopback
listener. Prints observations to stdout and a JSONL file; the exit code is not a
product verdict by itself.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from summit_everything.integrations.embedding import FakeEmbedding  # noqa: E402
from summit_everything.retrieval.query import QueryService  # noqa: E402
from summit_everything.retrieval.store import IndexStore  # noqa: E402
from summit_everything.workspace.manifest import (  # noqa: E402
    create_line,
    create_project,
    create_workspace,
    load_manifest,
)
from summit_everything.workspace.writer import PageWriter  # noqa: E402

BASE = ROOT / ".local" / "dsh" / "c19" / "api-run"
FINGERPRINT = "summit-fake-embedding-v1"
TOKEN = "dsh-c19-local-token"

FULL_PAGES = [
    ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。"),
    ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。"),
    ("玄石展览", "无关", "玄石展览开放时间为周六。"),
]
PARTIAL_PAGES = [
    ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。"),
    ("玄石展览", "无关", "玄石展览开放时间为周六。"),
]
QUALIFIER_PAGES = [
    ("玄石展览", "年度登记", "玄石展览年度访客登记办法为提前一天报备。"),
    ("玄石展览", "日常登记", "玄石展览访客登记办法为提前一天报备。"),
    ("玄石展览", "专项证章", "玄石展览专项证章领取须本人签名。"),
    ("玄石展览", "普通证章", "玄石展览证章领取须本人签名。"),
]

BUDGET = "枫湾活动预算上限为七万二千元。"
DEVICE = "玄石展览访客设备领用须登记姓名并归还胸牌。"
YEAR = "玄石展览年度访客登记办法为提前一天报备。"
SPECIAL = "玄石展览专项证章领取须本人签名。"

# (workspace, case, question, mode, expectation)
CASES = [
    ("ws-full", "device-full-forward-comparison", "比较枫湾活动预算与玄石展览的访客设备领用办法", "comparison", {"excerpts": [BUDGET, DEVICE], "scope_missing": []}),
    ("ws-full", "device-full-reverse-comparison", "比较玄石展览访客设备领用办法与枫湾活动预算", "comparison", {"excerpts": [BUDGET, DEVICE], "scope_missing": []}),
    ("ws-full", "device-full-forward-fact", "比较枫湾活动预算与玄石展览的访客设备领用办法", "fact", {"excerpts": [BUDGET, DEVICE], "scope_missing": []}),
    ("ws-full", "device-full-forward-plan", "比较枫湾活动预算与玄石展览的访客设备领用办法", "plan", {"excerpts": [BUDGET, DEVICE], "scope_missing": []}),
    ("ws-full", "device-single-fact", "玄石展览的访客设备领用办法是什么？", "fact", {"excerpts": [DEVICE], "scope_missing": []}),
    ("ws-full", "device-zero-swapped-topics", "比较枫湾活动访客设备领用办法与玄石展览预算", "comparison", {"excerpts": [], "scope_missing_any": ["枫湾活动", "玄石展览"]}),
    ("ws-partial", "device-partial-b-topic-absent", "比较枫湾活动预算与玄石展览的访客设备领用办法", "comparison", {"excerpts": [BUDGET], "scope_missing": ["玄石展览：缺少访客设备领用依据。"]}),
    ("ws-qualifier", "year-qualifier-target-present", "玄石展览的年度访客登记办法是什么", "fact", {"excerpts": [YEAR], "scope_missing": []}),
    ("ws-qualifier", "year-qualifier-mismatch-zero", "玄石展览的季度访客登记办法是什么", "fact", {"excerpts": [], "scope_missing_any": ["玄石展览"]}),
    ("ws-qualifier", "special-qualifier-target-present", "玄石展览的专项证章领取办法是什么", "fact", {"excerpts": [SPECIAL], "scope_missing": []}),
    ("ws-qualifier", "special-qualifier-mismatch-zero", "玄石展览的专项胸牌领取办法是什么", "fact", {"excerpts": [], "scope_missing_any": ["玄石展览"]}),
]


def build_workspace(name: str, pages: list[tuple[str, str, str]]) -> Path:
    root = BASE / name / "workspace"
    profile = BASE / name / "profile"
    create_workspace(root, name, profile, name)
    line = create_line(root, "活动运营线", f"{name}-line")
    projects: dict[str, object] = {}
    for project_name, _, _ in pages:
        if project_name not in projects:
            projects[project_name] = create_project(root, line.id, project_name, f"{name}-p-{len(projects)}")
    for index, (project_name, title, body) in enumerate(pages):
        PageWriter().confirm(
            root,
            metadata={
                "id": str(uuid4()),
                "title": title,
                "role": "knowledge",
                "kind": "topic",
                "line_id": str(line.id),
                "project_id": str(projects[project_name].id),
            },
            body=body,
            confirmation_id=f"{name}-confirm-{index}",
            operation_id=f"{name}-write-{index}",
        )
    return root


def index_workspace(root: Path, local_profile_dir: str) -> str:
    """Build the index where the service reads it: <profile_root>/<workspace_id>."""
    index_path = Path(local_profile_dir) / "index.sqlite3"
    store = IndexStore(index_path)
    service = QueryService(store, FakeEmbedding())
    service.rebuild(root, fingerprint=FINGERPRINT)
    active = store.active_fingerprint(load_manifest(root).workspace_id)
    service.close()
    return str(active)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_health(port: int, timeout: float = 30.0) -> dict[str, object]:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(  # noqa: S310 - loopback only
                f"http://127.0.0.1:{port}/api/v1/health", timeout=2
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"health never became ready: {last}")


def stream_query(client: httpx.Client, question: str, mode: str) -> dict[str, object]:
    request_id = str(uuid4())
    payload = {
        "question": question,
        "fingerprint": FINGERPRINT,
        "purpose": "current",
        "answer_mode": mode,
        "request_id": request_id,
    }
    events: list[dict[str, object]] = []
    conversation_id = None
    with client.stream("POST", "/api/v1/queries", json=payload) as response:
        conversation_id = response.headers.get("x-conversation-id")
        status = response.status_code
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            events.append(json.loads(line[len("data: ") :]))
    terminal = next((event for event in events if event["type"] in {"completed", "error"}), None)
    return {
        "status": status,
        "request_id": request_id,
        "conversation_id": conversation_id,
        "event_types": [event["type"] for event in events],
        "terminal": terminal,
        "answer": terminal["data"] if terminal and terminal["type"] == "completed" else None,
    }


def evaluate(
    expectation: dict[str, object], excerpts: list[str], scope_missing: list[str]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    expected_excerpts = expectation.get("excerpts")
    if expected_excerpts is not None and sorted(excerpts) != sorted(expected_excerpts):
        reasons.append(f"excerpts {excerpts!r} != {expected_excerpts!r}")
    if "scope_missing" in expectation and scope_missing != expectation["scope_missing"]:
        reasons.append(f"scope_missing {scope_missing!r} != {expectation['scope_missing']!r}")
    for needle in expectation.get("scope_missing_any", []):
        if not any(needle in item for item in scope_missing):
            reasons.append(f"no scope_missing naming {needle!r} in {scope_missing!r}")
    return ("PASS" if not reasons else "FAIL"), reasons


def main() -> int:
    if BASE.exists():
        shutil.rmtree(BASE)
    BASE.mkdir(parents=True)
    roots = {
        "ws-full": build_workspace("ws-full", FULL_PAGES),
        "ws-partial": build_workspace("ws-partial", PARTIAL_PAGES),
        "ws-qualifier": build_workspace("ws-qualifier", QUALIFIER_PAGES),
    }

    port = free_port()
    env = os.environ.copy()
    env["SUMMIT_PROFILE_ROOT"] = str(BASE / "profile-root")
    env["SUMMIT_SESSION_TOKEN"] = TOKEN
    env["SUMMIT_API_PORT"] = str(port)
    env["PYTHONPATH"] = f"{ROOT / 'scripts' / 'offline_guard'}:{ROOT / 'src'}"
    (BASE / "profile-root").mkdir(parents=True, exist_ok=True)
    log = (BASE / "uvicorn.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "summit_everything.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    output = BASE / "api-replay.jsonl"
    try:
        health = wait_health(port)
        print(json.dumps({"health": health, "port": port}, ensure_ascii=False), flush=True)
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", headers=headers, timeout=60.0
        ) as client:
            active_root: str | None = None
            reopen_target: tuple[str, str] | None = None
            with output.open("w", encoding="utf-8") as stream:
                for workspace, case, question, mode, expectation in CASES:
                    if active_root != workspace:
                        opened = client.post(
                            "/api/v1/workspaces",
                            json={
                                "root": str(roots[workspace]),
                                "mode": "open",
                                "operation_id": f"open-{workspace}-{uuid4()}",
                            },
                        )
                        opened.raise_for_status()
                        context = opened.json()
                        active = index_workspace(
                            roots[workspace], str(context["local_profile_dir"])
                        )
                        stream.write(
                            json.dumps(
                                {
                                    "case": "index-built",
                                    "workspace": workspace,
                                    "local_profile_dir": context["local_profile_dir"],
                                    "active_fingerprint": active,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        active_root = workspace
                    result = stream_query(client, question, mode)
                    answer = result["answer"]
                    missing = list((answer or {}).get("missing_information") or [])
                    # Provider caveats (comparison yardstick, plan preconditions) are
                    # separate from scope-pair gaps, which always name a missing basis.
                    scope_missing = [item for item in missing if "缺少" in item and "依据" in item]
                    observed = [item["excerpt"] for item in (answer or {}).get("citations", [])]
                    verdict, reasons = evaluate(expectation, observed, scope_missing)
                    record = {
                        "case": case,
                        "workspace": workspace,
                        "question": question,
                        "mode": mode,
                        "verdict": verdict,
                        "verdict_reasons": reasons,
                        "expected": expectation,
                        "http_status": result["status"],
                        "event_types": result["event_types"],
                        "conversation_id": result["conversation_id"],
                        "excerpts": observed,
                        "scope_missing": scope_missing,
                        "provider_reported_missing": missing,
                        "citation_objects": [
                            {
                                "page_id": item["page_id"],
                                "validity": item["validity"],
                                "availability": item["availability"],
                                "excerpt": item["excerpt"],
                            }
                            for item in (answer or {}).get("citations", [])
                        ],
                        "source_statements": len((answer or {}).get("source_statements", [])),
                        "inferences": len((answer or {}).get("inferences", [])),
                        "advice": len((answer or {}).get("advice", [])),
                        "text": (answer or {}).get("text"),
                    }
                    if case == "device-full-forward-comparison":
                        reopen_target = (workspace, str(result["conversation_id"]))
                    stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                    stream.flush()
                    print(json.dumps(record, ensure_ascii=False, default=str), flush=True)

                if reopen_target is not None:
                    workspace, conversation_id = reopen_target
                    if active_root != workspace:
                        client.post(
                            "/api/v1/workspaces",
                            json={
                                "root": str(roots[workspace]),
                                "mode": "open",
                                "operation_id": f"open-{workspace}-{uuid4()}",
                            },
                        ).raise_for_status()
                        active_root = workspace
                    reopened = client.post(f"/api/v1/conversations/{conversation_id}/reopen")
                    body = reopened.json() if reopened.status_code == 200 else reopened.text
                    messages = body.get("messages", []) if isinstance(body, dict) else []
                    first = messages[0] if messages else {}
                    replayed = [item["excerpt"] for item in first.get("citations", [])]
                    replayed_missing = list(first.get("missing_information") or [])
                    scope_missing = [
                        item for item in replayed_missing if "缺少" in item and "依据" in item
                    ]
                    verdict, reasons = evaluate(
                        {"excerpts": [BUDGET, DEVICE], "scope_missing": []},
                        replayed,
                        scope_missing,
                    )
                    if first.get("state") != "completed":
                        verdict, reasons = "FAIL", [
                            *reasons,
                            f"state {first.get('state')!r} != 'completed'",
                        ]
                    record = {
                        "case": "history-reopen-device-full-forward",
                        "conversation_id": conversation_id,
                        "http_status": reopened.status_code,
                        "verdict": verdict,
                        "verdict_reasons": reasons,
                        "message_count": body.get("message_count") if isinstance(body, dict) else None,
                        "state": first.get("state"),
                        "excerpts": replayed,
                        "scope_missing": scope_missing,
                        "text": first.get("answer"),
                        "reopened": body,
                    }
                    stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                    print(json.dumps(record, ensure_ascii=False, default=str), flush=True)

                listing = client.get("/api/v1/conversations")
                listed = listing.json() if listing.status_code == 200 else {}
                print(
                    json.dumps(
                        {
                            "case": "history-list",
                            "http_status": listing.status_code,
                            "items": len(listed.get("items", [])) if isinstance(listed, dict) else None,
                            "verdict": "PASS"
                            if listing.status_code == 200
                            and isinstance(listed, dict)
                            and len(listed.get("items", [])) >= 1
                            else "FAIL",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    finally:
        if server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            server.wait()
        log.close()
    with socket.socket() as probe:
        probe.settimeout(1.0)
        listener = probe.connect_ex(("127.0.0.1", port)) == 0
    print(json.dumps({"case": "listener-after-stop", "listening": listener}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
