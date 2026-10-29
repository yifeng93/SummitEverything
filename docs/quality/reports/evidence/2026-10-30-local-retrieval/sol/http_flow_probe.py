"""Synthetic API closure with pinned local weights and mocked DeepSeek only."""
import json
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.local.retrieval_model import LocalRetrievalModelStore

MODEL = Path('/Users/hanwenbo/ai/SummitEverything/.local/qa/local-retrieval-probe/models/46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59')
SOURCE = '青榆的访客登记须由前台核验姓名并记录来访时间。'
calls = []
network_attempts = []
credential_reads = []

def synthetic_credential(self, provider, account_id):
    credential_reads.append(provider)
    assert provider == "deepseek"
    return self.vault.get_secret(provider, account_id=account_id)

def reject_network(*args, **kwargs):
    network_attempts.append('socket connection rejected')
    raise AssertionError('Unexpected socket network attempt')

def handler(request):
    assert request.url.host == 'api.deepseek.com', str(request.url)
    assert request.url.path.endswith('/chat/completions'), str(request.url)
    payload = json.loads(request.content)
    organize = 'Faithfully reorganize' in payload['messages'][0]['content']
    calls.append('organize' if organize else 'answer')
    if organize:
        content = {'proposals': [{'title': '访客登记办法', 'kind': 'topic', 'body': SOURCE,
            'input_indexes': [0], 'important_conflicts': [], 'action_suggestions': []}]}
    else:
        assert SOURCE in json.dumps(payload, ensure_ascii=False)
        content = {'text': SOURCE, 'source_statements': [SOURCE], 'inferences': [], 'advice': [], 'missing_information': []}
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(content, ensure_ascii=False)}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 15, 'completion_tokens': 25, 'total_tokens': 40}}, headers={'x-request-id': f'synthetic-{len(calls)}'})

def mock_client():
    return httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)

with tempfile.TemporaryDirectory(prefix='summit-local-http-') as tmp, \
     patch.object(socket.socket, 'connect', reject_network), \
     patch.object(socket, 'create_connection', reject_network), \
     patch('summit_everything.integrations.llm.create_http_client', mock_client), \
     patch('summit_everything.integrations.runtime.ModelRuntime._credential', synthetic_credential):
    root = Path(tmp)
    app = create_app(session_token='synthetic-session', profile_root=root/'profiles', secret_backend=MemorySecretBackend())
    with TestClient(app) as client:
        client.headers.update({'Authorization': 'Bearer synthetic-session'})
        def req(method, path, body=None, status=200):
            res = client.request(method, '/api/v1'+path, json=body) if body is not None else client.request(method, '/api/v1'+path)
            assert res.status_code == status, (method, path, res.status_code, res.text)
            return res.json()
        def plan(operation, scope):
            preview = req('POST','/acceptance-plans',{'operation':operation,'scope':scope},201)
            req('POST',f"/acceptance-plans/{preview['plan']['plan_id']}/confirm",{'scope_sha256':preview['plan']['scope_sha256'],'scope':preview['scope']})
            return preview
        workspace=req('POST','/workspaces',{'root':str(root/'workspace'),'mode':'create','name':'闭环合成库','operation_id':'open'},201)
        profile=root/'profiles'/workspace['workspace_id']
        app.state.local_model_stores[str(profile.resolve())]=LocalRetrievalModelStore(profile/'retrieval-models',model_directory=MODEL)
        settings=req('PATCH','/settings',{'mode':'real','llm':{'provider':'deepseek','model':'deepseek-flash','enabled':True,'account_id':'synthetic'},
            'embedding':{'provider':'local','model':'BAAI/bge-small-zh-v1.5','dimensions':512,'enabled':True},
            'rerank':{'provider':'local','model':'BAAI/bge-small-zh-v1.5','dimensions':512,'enabled':True}})
        assert settings['local_model']['state']=='ready'
        req('PUT','/credentials/deepseek',{'account_id':'synthetic','secret':'sk-synthetic-offline-only'})
        line=req('POST','/lines',{'name':'合成线','operation_id':'line'},201)
        project=req('POST','/projects',{'name':'青榆','line_id':line['id'],'operation_id':'project'},201)
        intake=req('POST','/intake/items',{'text':SOURCE,'filename':'synthetic.txt','operation_id':'intake'},201)
        scope={'item_ids':[intake['item_id']],'line_id':line['id'],'project_id':project['id'],'operation_id':'organize','reprocess':False}
        preview=plan('model.organize',scope)
        assert calls==[]
        assert req('GET','/drafts')==[]
        job=req('POST','/intake/jobs',{**scope,'acceptance_plan_id':preview['plan']['plan_id']},201)
        assert calls==['organize']
        draft_id=job['draft_ids'][0]
        draft=req('GET',f'/drafts/{draft_id}')
        assert draft['body']==SOURCE
        confirmed=req('POST',f'/drafts/{draft_id}/confirmations',{'expected_version':1,'confirmation_id':'human-synthetic','operation_id':'approve'})
        fp=settings['embedding_fingerprint']
        index_mode='initial'
        expected_pages=1
        if '--migration' in sys.argv:
            fake=req('PATCH','/settings',{'mode':'fake'})
            assert fake['embedding_fingerprint']=='summit-fake-embedding-v1',fake
            fake_plan=req('POST','/index/plans',{'mode':'initial','fingerprint':fake['embedding_fingerprint']})
            req('POST','/index/jobs',fake_plan)
            switched=req('PATCH','/settings',{'mode':'real'})
            assert switched['local_model']['state']=='ready'
            assert switched['embedding_fingerprint']==fp
            stale=req('GET','/index/status')
            assert stale['state']=='stale' and stale['reason']=='embedding_model_changed',stale
            before_index=req('GET','/index/status')
            after_switch_approval=req('POST','/pages',{'metadata':{'id':str(uuid4()),'title':'切换后的合成补充','role':'knowledge','kind':'topic','line_id':line['id'],'project_id':project['id']},'body':'这是一份用于模型切换验证的合成补充说明。','confirmation_id':'new-model-approval','operation_id':'approve-before-rebuild'},201)
            assert after_switch_approval['index_update']=='manual_required',after_switch_approval
            after_index=req('GET','/index/status')
            assert after_index['reason']=='embedding_model_changed',after_index
            expected_pages=2
            req('POST','/index/plans',{'mode':'model_change','fingerprint':fake['embedding_fingerprint']},409)
            blocked=req('POST','/queries',{'question':'青榆访客登记办法是什么','fingerprint':fake['embedding_fingerprint'],'request_id':str(uuid4())},409)
            assert blocked['error']['code']=='index_not_ready',blocked
            assert calls==['organize']
            index_mode='model_change'
        indexplan=req('POST','/index/plans',{'mode':index_mode,'fingerprint':fp})
        assert indexplan['estimated_cost']==0
        assert calls==['organize']
        indexed=req('POST','/index/jobs',indexplan)
        assert indexed['indexed_pages']==expected_pages, indexed
        assert calls==['organize']
        assert credential_reads==['deepseek'],credential_reads
        scope={'request_id':str(uuid4()),'question':sys.argv[1] if len(sys.argv)>1 else '青榆访客登记办法是什么','fingerprint':fp,'purpose':'current','answer_mode':'fact'}
        preview=plan('model.query',scope)
        assert preview['plan']['request_limit']==1,preview
        response=client.post('/api/v1/queries',json={**scope,'acceptance_plan_id':preview['plan']['plan_id']})
        assert response.status_code==200,response.text
        events=[json.loads(x[6:]) for x in response.text.splitlines() if x.startswith('data: {')]
        assert not [e for e in events if e['type']=='error'],events
        citations=[e['data'] for e in events if e['type']=='citation']
        assert citations,events
        assert SOURCE in response.text,response.text
        for citation in citations:
            page=req('GET',f"/pages/{citation['page_id']}")
            assert page['content_sha256']==citation['content_sha256']
            assert page['approval_state']=='confirmed'
        assert calls==['organize','answer'],calls
        assert credential_reads==['deepseek','deepseek'],credential_reads
        state=req('GET',f"/acceptance-plans/{preview['plan']['plan_id']}")
        assert state['requests_reserved']==1,state
        assert [u['provider'] for u in state['provider_usage']]==['deepseek'],state
        assert not network_attempts
        print(json.dumps({'result':'PASS','steps':['import','mock organize','explicit formal approval','real local index','one-shot query plan','SSE answer','current citation validation'], 'index_mode':index_mode,'indexed_pages':indexed['indexed_pages'],'indexed_chunks':indexed['indexed_chunks'],'mock_calls':calls,'socket_attempts':0,'events':[e['type'] for e in events],'citation_count':len(citations),'real_cloud_calls':0,'runtime_credential_reads':credential_reads},ensure_ascii=False,indent=2))
