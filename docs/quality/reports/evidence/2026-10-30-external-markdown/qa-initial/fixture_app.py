"""QA-only FastAPI factory: real app with isolated, synthetic provider boundaries."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx

from summit_everything.api import app as api_module
from summit_everything.api.app import create_app as create_summit_app
from summit_everything.integrations.llm import DeepSeekLLM as RealDeepSeekLLM
from summit_everything.integrations.settings import MacOSKeychainBackend
from summit_everything.local.retrieval_model import LocalRetrievalModelStore as RealModelStore

MODEL_DIR = Path(os.environ["QA_LOCAL_MODEL_DIR"]).resolve()
EVIDENCE_DIR = Path(os.environ["QA_EVIDENCE_DIR"]).resolve()
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


class SyntheticKeychain(MacOSKeychainBackend):
    """Only proves credential plumbing; all values stay in process memory."""
    def __init__(self) -> None:
        self._values: dict[tuple[str, str], str] = {}

    def get(self, namespace: str, key: str) -> str | None:
        return self._values.get((namespace, key))

    def set(self, namespace: str, key: str, value: str) -> None:
        self._values[(namespace, key)] = value

    def delete(self, namespace: str, key: str) -> None:
        self._values.pop((namespace, key), None)


class InjectedLocalModelStore(RealModelStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root, model_directory=MODEL_DIR)


# Patch only constructor seams; all app routing, source operations, readers,
# writers, index construction and retrieval remain the production implementations.
api_module.LocalRetrievalModelStore = InjectedLocalModelStore

provider_requests: list[dict[str, Any]] = []
provider_calls = {"organize": 0, "answer": 0, "injected_failure": 0}


def response_content(messages: list[dict[str, str]]) -> str:
    system = messages[0]["content"]
    user = messages[1]["content"]
    if "proposals array" in system:
        provider_calls["organize"] += 1
        payload = json.loads(user)
        source_text = payload["inputs"][0]["untrusted_source_text"]
        if "[QA_FAIL_PROVIDER]" in source_text:
            provider_calls["injected_failure"] += 1
            raise httpx.ConnectError("controlled synthetic provider failure")
        token = hashlib.sha256(source_text.encode()).hexdigest()[:8]
        conflicts = []
        if "[QA_NUMBER_CONFLICT]" in source_text:
            conflicts = [{
                "id": "person_limit",
                "question": "活动人数上限是多少？",
                "alternatives": ["24人", "30人"],
            }]
        suggestions = [{
            "kind": "todo",
            "description": "确认合成活动的下一步安排",
            "related_project_id": None,
        }]
        return json.dumps({"proposals": [
            {"title": f"合成规则 {token}", "kind": "decision", "body": source_text,
             "input_indexes": [0], "important_conflicts": conflicts, "action_suggestions": suggestions},
            {"title": f"合成补充 {token}", "kind": "topic", "body": source_text,
             "input_indexes": [0], "important_conflicts": [], "action_suggestions": []},
        ]}, ensure_ascii=False)

    provider_calls["answer"] += 1
    envelope = json.loads(user)
    # Preserve the exact synthetic request shape for later audit, including the
    # actual retrieved passages and query, without exposing auth headers.
    provider_requests.append({"kind": "answer", "request": envelope})
    flush_provider_evidence()
    q = str(envelope.get("question", ""))
    passages = envelope.get("passages", [])
    all_text = "\n".join(str(p.get("excerpt", "")) for p in passages if isinstance(p, dict))
    if "志愿者人数" in q or "蓝色储物箱" in q:
        return json.dumps({"text": "现有已确认资料里没有这项信息。", "source_statements": [],
                           "inferences": [], "advice": [], "missing_information": [q]}, ensure_ascii=False)
    statement = next((line.strip() for line in all_text.splitlines() if line.strip()), "")
    answer = statement or "当前已确认资料未提供可回答的内容。"
    return json.dumps({"text": answer, "source_statements": [answer] if statement else [],
                       "inferences": [], "advice": [],
                       "missing_information": [] if statement else [q]}, ensure_ascii=False)


def flush_provider_evidence() -> None:
    (EVIDENCE_DIR / "provider-requests.json").write_text(
        json.dumps({"calls": provider_calls, "requests": provider_requests}, ensure_ascii=False, indent=2)
    )


def mock_transport(request: httpx.Request) -> httpx.Response:
    try:
        body = json.loads(request.content.decode("utf-8"))
        provider_requests.append({"kind": "wire", "method": request.method,
                                  "url": str(request.url), "body": body})
        messages = body.get("messages", [])
        content = response_content(messages)
        # Persist counters after the call is actually classified and handled.
        flush_provider_evidence()
        reply = {"id": "qa-synthetic", "object": "chat.completion", "created": 0,
                 "model": "deepseek-flash", "choices": [{"index": 0, "finish_reason": "stop",
                 "message": {"role": "assistant", "content": content}}],
                 "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        return httpx.Response(200, json=reply, request=request)
    except httpx.ConnectError:
        flush_provider_evidence()
        return httpx.Response(503, json={"error": {"message": "synthetic provider failure"}}, request=request)


def injected_deepseek(api_key: str, **kwargs: Any) -> RealDeepSeekLLM:
    client = httpx.Client(transport=httpx.MockTransport(mock_transport), trust_env=False,
                          follow_redirects=False)
    return RealDeepSeekLLM(api_key, client=client, **kwargs)

from summit_everything.integrations import runtime as runtime_module
runtime_module.DeepSeekLLM = injected_deepseek


def create_app():
    port = os.environ.get("QA_WEB_PORT", "15197")
    token = os.environ["QA_SESSION_TOKEN"]
    app = create_summit_app(
        session_token=token,
        profile_root=Path(os.environ["QA_PROFILE_ROOT"]).resolve(),
        secret_backend=SyntheticKeychain(),
        feishu_config=__import__("summit_everything.integrations.feishu.provider", fromlist=["FeishuConfig"]).FeishuConfig(
            redirect_uri=f"http://127.0.0.1:{port}/api/v1/integrations/feishu/callback",
            allowed_origins=(f"http://127.0.0.1:{port}",),
        ),
    )
    app.state.qa_provider_counters = provider_calls
    app.state.qa_provider_requests = provider_requests
    app.router.add_event_handler("shutdown", flush_provider_evidence)
    return app
