"""Local-only browser QA API with synthetic secrets and a hard HTTP mock."""
from pathlib import Path
import httpx
import uvicorn
from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.integrations.feishu.provider import FeishuConfig
import summit_everything.integrations.embedding as embedding_module
import summit_everything.integrations.llm as llm_module
import summit_everything.integrations.rerank as rerank_module

calls: list[str] = []

def handler(request: httpx.Request) -> httpx.Response:
    calls.append(request.url.path)
    return httpx.Response(503, json={"error": "QA offline mock: provider request blocked"})

def mock_client(*args, **kwargs):
    return httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)

embedding_module.create_http_client = mock_client
llm_module.create_http_client = mock_client
rerank_module.create_http_client = mock_client
app = create_app(
    session_token="qa-synthetic-session-20261029",
    profile_root=Path(__file__).parent / "profile",
    secret_backend=MemorySecretBackend(),
    feishu_config=FeishuConfig(allowed_origins=("http://127.0.0.1:5281", "http://127.0.0.1:8798")),
)
uvicorn.run(app, host="127.0.0.1", port=8798, log_level="warning")
