"""Independent DEV review counterexamples. Synthetic data; no provider network/Keychain."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent / 'candidate/tests/integration'))
from test_qualified_retrieval import approve_page, create_test_workspace
from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import FeishuConfig, MemoryCredentialStore, UserCredentials
from summit_everything.integrations.feishu.service import FeishuService
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.integrations.rerank import ModelStudioReranker
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.reader import list_pages

FP = 'summit-fake-embedding-v1'
HEADERS = {'Authorization': 'Bearer review-synthetic-session'}

def _workspace(tmp_path, body='SYNTHETIC_STALE_CANARY 合成地点北馆。'):
    root, line, project = create_test_workspace(tmp_path / 'workspace')
    page_id, _ = approve_page(root, line, project, body=body)
    path = root / next(p.relative_path for p in list_pages(root) if p.page_id == page_id)
    return root, path

def _client(tmp_path, *, service=None):
    app = create_app(session_token='review-synthetic-session', profile_root=tmp_path / 'profile', secret_backend=MemorySecretBackend(), query_service=service)
    return TestClient(app)

def _open(c, path, mode='create'):
    return c.post('/api/v1/workspaces', headers=HEADERS, json={'root': str(path), 'mode': mode, 'name': 'Synthetic Review', 'operation_id': 'open'})

def test_stale_cached_text_must_not_reach_reranker(tmp_path):
    root, path = _workspace(tmp_path)
    captured = []
    class Spy:
        def rank(self, question, texts):
            captured.extend(texts)
            return [(i, 1.0) for i in range(len(texts))]
    query = QueryService(IndexStore(tmp_path / 'index.sqlite3'), reranker=Spy())
    query.rebuild(root, fingerprint=FP)
    path.write_text(path.read_text().replace('北馆', '西馆'))
    answer = query.query(root, '合成地点', fingerprint=FP)
    assert answer.citations == []  # Existing final gate works.
    assert not any('SYNTHETIC_STALE_CANARY' in t for t in captured), captured

def test_citations_must_be_rechecked_after_answer_provider_returns(tmp_path):
    root, path = _workspace(tmp_path)
    class EditingAnswerer:
        def answer(self, question, passages):
            path.write_text(path.read_text().replace('北馆', '西馆'))
            return GroundedAnswer(text='北馆。')
    query = QueryService(IndexStore(tmp_path / 'index.sqlite3'), answer_provider=EditingAnswerer())
    query.rebuild(root, fingerprint=FP)
    answer = query.query(root, '合成地点', fingerprint=FP)
    assert not answer.citations, answer.model_dump()

def test_cancel_during_embedding_must_suppress_later_provider_calls(tmp_path):
    root, _ = _workspace(tmp_path)
    entered, release = Event(), Event()
    calls = []
    class BlockingEmbedding(FakeEmbedding):
        def embed(self, text, *, fingerprint):
            entered.set()
            assert release.wait(5)
            return super().embed(text, fingerprint=fingerprint)
    class SpyRerank:
        def rank(self, question, texts):
            calls.append('rerank')
            return [(i, 1.0) for i in range(len(texts))]
    class SpyAnswer:
        def answer(self, question, passages):
            calls.append('answer')
            return GroundedAnswer(text='合成回答')
    store = IndexStore(tmp_path / 'index.sqlite3')
    QueryService(store).rebuild(root, fingerprint=FP)
    service = QueryService(store, embedding=BlockingEmbedding(), reranker=SpyRerank(), answer_provider=SpyAnswer())
    c = _client(tmp_path, service=service)
    assert _open(c, root, 'open').status_code == 201
    query_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(c.post, '/api/v1/queries', headers=HEADERS, json={'question': '合成地点', 'fingerprint': FP, 'request_id': query_id})
        assert entered.wait(5)
        cancellation = c.delete('/api/v1/queries/' + query_id, headers=HEADERS)
        assert cancellation.status_code == 202
        release.set()
        response = future.result(timeout=5)
    assert 'cancelled' in response.text and 'completed' not in response.text
    assert calls == [], calls

def test_query_with_101_chunks_must_use_bounded_candidates(tmp_path):
    root, _ = _workspace(tmp_path, body='\n\n'.join(f'## Section {i}\n合成地点 {i}。' for i in range(101)))
    query = QueryService(IndexStore(tmp_path / 'index.sqlite3'))
    result = query.rebuild(root, fingerprint=FP)
    assert result.indexed_chunks == 101
    seen = []
    def handler(request):
        seen.append(request)
        count = len(json.loads(request.content)['input']['documents'])
        return httpx.Response(200, json={'output': {'results': [{'index': i, 'relevance_score': 1.0} for i in range(count)]}})
    query.reranker = ModelStudioReranker('synthetic-key', client=httpx.Client(transport=httpx.MockTransport(handler)))
    answer = query.query(root, '合成地点', fingerprint=FP)
    assert answer.citations and seen

def test_persisted_callback_must_be_restored_on_restart(tmp_path):
    c = _client(tmp_path)
    assert _open(c, tmp_path/'workspace').status_code == 201
    callback = 'http://localhost:8765/callback'
    assert c.patch('/api/v1/settings', headers=HEADERS, json={'feishu': {'app_id': 'synthetic-a', 'redirect_uri': callback}}).status_code == 200
    restarted = _client(tmp_path)
    assert _open(restarted, tmp_path/'workspace', 'open').status_code == 201
    assert restarted.get('/api/v1/settings', headers=HEADERS).json()['feishu']['redirect_uri'] == callback
    issued = restarted.post('/api/v1/integrations/feishu/authorizations', headers=HEADERS).json()['authorization_url']
    parsed = urlsplit(issued)
    assert parsed.scheme+'://'+parsed.netloc+parsed.path == callback, issued

def test_workspace_switch_must_not_reuse_feishu_settings_or_authorization(tmp_path):
    c = _client(tmp_path)
    assert _open(c, tmp_path/'workspace-a').status_code == 201
    c.patch('/api/v1/settings', headers=HEADERS, json={'feishu': {'app_id': 'synthetic-a', 'redirect_uri': 'http://localhost:8765/callback'}})
    issued = c.post('/api/v1/integrations/feishu/authorizations', headers=HEADERS).json()['authorization_url']
    parsed = urlsplit(issued)
    state = parse_qs(parsed.query)['state'][0]
    c.get('http://localhost:8765/callback', params={'state': state, 'code': 'fake-ok'})
    assert c.get('/api/v1/integrations/feishu/status', headers=HEADERS).json()['authorized']
    assert _open(c, tmp_path/'workspace-b').status_code == 201
    assert c.get('/api/v1/settings', headers=HEADERS).json()['feishu']['app_id'] == ''
    assert not c.get('/api/v1/integrations/feishu/status', headers=HEADERS).json()['authorized']

def test_logout_must_invalidate_pending_oauth_state(tmp_path):
    c = _client(tmp_path)
    assert _open(c, tmp_path/'workspace').status_code == 201
    issued = c.post('/api/v1/integrations/feishu/authorizations', headers=HEADERS).json()['authorization_url']
    state = parse_qs(urlsplit(issued).query)['state'][0]
    assert c.delete('/api/v1/integrations/feishu/authorizations', headers=HEADERS).status_code == 204
    response = c.get(issued)
    assert response.status_code == 400 and response.json()['error']['code'] == 'invalid_state'

def test_concurrent_refresh_must_not_overwrite_newest_refresh_token(tmp_path):
    entered, release = Event(), Event()
    class RacingFake(FakeFeishu):
        count = 0
        def refresh(self, credentials):
            self.count += 1
            number = self.count
            if number == 1:
                entered.set()
                assert release.wait(5)
            return UserCredentials(access_token=f'synthetic-access-{number}', refresh_token=f'synthetic-refresh-{number}', expires_at=2000, scopes=credentials.scopes)
    store = MemoryCredentialStore()
    store.put(UserCredentials(access_token='synthetic-old', refresh_token='synthetic-old', expires_at=1050, scopes=['minutes:read']))
    provider = RacingFake(tmp_path/'remote')
    service = FeishuService(provider, store, FeishuConfig(), 'synthetic-session', clock=lambda: 1000)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(service.materials, '', None, None, 10)
        assert entered.wait(5)
        service.materials('', None, None, 10)
        release.set()
        first.result(timeout=5)
    assert provider.count == 1, (provider.count, store.get().refresh_token)
