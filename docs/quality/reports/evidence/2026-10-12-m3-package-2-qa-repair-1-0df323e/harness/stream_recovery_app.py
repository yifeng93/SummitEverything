from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from summit_everything.integrations.embedding import FakeEmbedding  # noqa: E402
from summit_everything.integrations.feishu.provider import FeishuConfig  # noqa: E402
from summit_everything.integrations.llm import DeepSeekLLM  # noqa: E402
from summit_everything.integrations.runtime import ModelRuntime  # noqa: E402
from summit_everything.retrieval.query import QueryService  # noqa: E402
from summit_everything.retrieval.store import IndexStore  # noqa: E402
from summit_everything.workspace.manifest import load_manifest, open_workspace  # noqa: E402
from summit_everything.workspace.writer import PageWriter  # noqa: E402

BASE = Path(os.environ["QA_M3_BASE"]).resolve()
WORKSPACE = Path(os.environ.get("QA_M3_WORKSPACE", str(BASE / "workspace-A"))).resolve()
PROFILE_A = BASE / "profiles-R"
PROFILE_B = BASE / "profiles-S"
TOKEN = os.environ["QA_M3_SESSION_TOKEN"]
FINGERPRINT = "m3-package2-synthetic-fake-v1"
CAPTURE = BASE / "harness" / "deepseek-payloads.jsonl"


def mock_http(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    user_raw = payload["messages"][1]["content"]
    user = json.loads(user_raw)
    CAPTURE.parent.mkdir(parents=True, exist_ok=True)
    with CAPTURE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"model": payload["model"], "body": user}, ensure_ascii=False) + "\n")
    passages = user["passages"]
    question = user["question"]
    mode = user["mode"]
    result = {
        "text": "本地合成 provider 已收到问题与合格材料；请以来源陈述为准。" if passages else "没有找到匹配的已确认依据。",
        "source_statements": [f"{item['heading']}：{item['excerpt']}" for item in passages],
        "inferences": ["该结论只适用于当前列出的材料。"] if mode == "comparison" and passages else [],
        "advice": ["先核实缺失条件，再由用户决定下一步。"] if mode == "plan" else [],
        "missing_information": ["材料没有提供相关依据。"] if not passages else (["未提供执行负责人。"] if mode == "plan" else []),
    }
    content = json.dumps(result, ensure_ascii=False)
    response = {
        "id": "chatcmpl-synthetic-qa",
        "object": "chat.completion",
        "created": 1,
        "model": "deepseek-flash",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }
    return httpx.Response(200, json=response)


def synthetic_llm(self: ModelRuntime, *, max_tokens: int = 2048) -> DeepSeekLLM:
    return DeepSeekLLM(
        "synthetic-stub-key",
        client=httpx.Client(transport=httpx.MockTransport(mock_http)),
        max_tokens=max_tokens,
    )


ModelRuntime.llm = synthetic_llm  # type: ignore[method-assign]

manifest = load_manifest(WORKSPACE)
if len(manifest.lines) != 1 or len(manifest.projects) != 1:
    raise RuntimeError("Expected the UI-created synthetic line and project")
line = manifest.lines[0]
project = manifest.projects[0]
writer = PageWriter()
fixtures = [
    ("QA 青岚预算与排期", "青岚计划的设备采购预算上限为 18 万元，负责人已确认。排期为 11 月启动；运维费用未提供。"),
    ("QA 朱雀预算", "朱雀项目的设备采购预算上限为 12 万元，负责人已确认。排期为 12 月启动；运维费用未提供。"),
    ("QA 青岚旧预算规则", "青岚计划旧版预算上限为 20 万元。", "superseded"),
]
page_ids = []
for idx, record in enumerate(fixtures):
    title, body, *validity = record
    metadata = {
        "id": str(UUID(int=idx + 1001)),
        "title": title,
        "role": "knowledge",
        "kind": "topic",
        "line_id": str(line.id),
        "project_id": str(project.id),
        "validity": validity[0] if validity else "current",
    }
    page = writer.confirm(
        WORKSPACE,
        metadata=metadata,
        body=body,
        confirmation_id=f"qa-package2-confirm-v2-{idx}",
        operation_id=f"qa-package2-write-v2-{idx}",
    )
    page_ids.append(metadata["id"])

PROFILE_A.mkdir(parents=True, exist_ok=True)
PROFILE_B.mkdir(parents=True, exist_ok=True)
for profile in (PROFILE_A, PROFILE_B):
    context = open_workspace(WORKSPACE, profile)
    service = QueryService(IndexStore(Path(context.local_profile_dir) / "index.sqlite3"), FakeEmbedding())
    active = service.store.active_fingerprint(manifest.workspace_id)
    mode = "initial" if active is None else ("incremental" if active == FINGERPRINT else "model_change")
    service.execute_plan(WORKSPACE, service.plan(WORKSPACE, fingerprint=FINGERPRINT, mode=mode))
    service.close()

from summit_everything.api.app import create_app  # noqa: E402

config = FeishuConfig(allowed_origins=("http://127.0.0.1:15173", "http://127.0.0.1:18793"))
app = create_app(session_token=TOKEN, profile_root=PROFILE_A, feishu_config=config)
app_b = create_app(session_token=TOKEN, profile_root=PROFILE_B, feishu_config=config)

with (BASE / "harness" / "fixture-manifest.json").open("w", encoding="utf-8") as stream:
    json.dump({"workspace_id": str(manifest.workspace_id), "line_id": str(line.id), "project_id": str(project.id), "page_ids": page_ids, "fingerprint": FINGERPRINT, "token": "[synthetic-test-token-redacted]"}, stream, ensure_ascii=False, indent=2)
