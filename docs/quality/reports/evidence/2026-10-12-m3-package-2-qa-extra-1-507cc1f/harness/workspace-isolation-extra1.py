from __future__ import annotations
import json, os, uuid
from pathlib import Path
import httpx
from summit_everything.workspace.manifest import open_workspace, load_manifest
from summit_everything.workspace.writer import PageWriter
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.integrations.embedding import FakeEmbedding
base=Path(__file__).resolve().parents[1]; root=base/'workspace-C'
A='http://127.0.0.1:18793/api/v1'; B='http://127.0.0.1:18795/api/v1'; headers={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}
a=httpx.Client(base_url=A,headers=headers,timeout=30); b=httpx.Client(base_url=B,headers=headers,timeout=30)
def state(c):
 w=c.get('/workspaces/current').json(); roles=c.get('/roles').json(); mem=c.get('/memory').json(); conv=c.get('/conversations?limit=100').json()['items']
 questions=[]
 for x in conv:
  d=c.get('/conversations/'+x['conversation_id']).json(); questions.extend(m['question'] for m in d.get('messages',[]))
 return {'workspace_id':w['workspace_id'],'profile':w['local_profile_dir'],'role_ids':[x['role_id'] for x in roles],'memory_ids':[x['memory_id'] for x in mem],'questions':questions,'history_count':len(conv)}
workspace_a=state(a); profile_b_open=b.post('/workspaces',json={'root':str(base/'workspace-A'),'mode':'open','operation_id':'qa-extra1-profile-b-open'}); b_state=state(b)
created=a.post('/workspaces',json={'root':str(root),'mode':'create','name':'QA extra1 隔离工作库 C','operation_id':'qa-extra1-workspace-c-create'}); assert created.status_code==201,(created.status_code,created.text)
line=a.post('/lines',json={'name':'QA extra1 C线','operation_id':'qa-extra1-c-line'}).json(); project=a.post('/projects',json={'line_id':line['id'],'name':'QA extra1 C项目','operation_id':'qa-extra1-c-project'}).json()
manifest=load_manifest(root); metadata={'id':str(uuid.uuid4()),'title':'C隔离标识','role':'knowledge','kind':'topic','line_id':line['id'],'project_id':project['id'],'validity':'current'}
PageWriter().confirm(root,metadata=metadata,body='QA C 工作库隔离标识为 C-ALPHA-901。',confirmation_id='qa-extra1-c-page-confirm',operation_id='qa-extra1-c-page-write')
context=open_workspace(root,Path(workspace_a['profile'])); service=QueryService(IndexStore(Path(context.local_profile_dir)/'index.sqlite3'),FakeEmbedding()); fp='summit-fake-embedding-v1'; active=service.store.active_fingerprint(manifest.workspace_id); plan=service.plan(root,fingerprint=fp,mode='initial' if active is None else 'incremental'); service.execute_plan(root,plan); service.close()
role=a.post('/roles',json={'name':'QA extra1 workspace C role','instructions':'C marker only','context_budget':300}); assert role.status_code==201,(role.status_code,role.text)
request_id=str(uuid.uuid4()); q='我偏好工作库C里的简洁回答 marker QA-C-901。'; query=a.post('/queries',json={'request_id':request_id,'question':q,'fingerprint':fp,'answer_mode':'fact','purpose':'current'}); assert query.status_code==200,(query.status_code,query.text)
candidate=a.post('/memory/candidates',json={'message_id':request_id,'text':q,'user_expression':True}); assert candidate.status_code==201,(candidate.status_code,candidate.text)
confirmed=a.post(f"/memory/candidates/{candidate.json()['candidate_id']}/confirmations",json={'confirmation_id':'qa-extra1-c-memory-confirm','text':q}); assert confirmed.status_code==200,(confirmed.status_code,confirmed.text)
state_c=state(a)
open_a=a.post('/workspaces',json={'root':str(base/'workspace-A'),'mode':'open','operation_id':'qa-extra1-switch-to-a'}); state_a=state(a)
returned=a.post('/workspaces',json={'root':str(root),'mode':'open','operation_id':'qa-extra1-return-c'}); state_c_return=state(a)
state_b=state(b)
result={'profile_b_open_http':profile_b_open.status_code,'workspace_c_create_http':created.status_code,'switch_http':[open_a.status_code,returned.status_code],'workspace_a_before':workspace_a,'profile_b_same_workspace':b_state,'workspace_c_populated':state_c,'workspace_a_during':state_a,'workspace_c_after_return':state_c_return,'profile_b_after':state_b}
result['pass']=profile_b_open.status_code==201 and created.status_code==201 and open_a.status_code==201 and returned.status_code==201 and b_state['workspace_id']==workspace_a['workspace_id'] and b_state['profile']!=workspace_a['profile'] and not b_state['role_ids'] and not b_state['memory_ids'] and state_a['workspace_id']==workspace_a['workspace_id'] and role.json()['role_id'] not in state_a['role_ids'] and confirmed.json()['memory_id'] not in state_a['memory_ids'] and q not in state_a['questions'] and state_c_return['workspace_id']==state_c['workspace_id'] and role.json()['role_id'] in state_c_return['role_ids'] and confirmed.json()['memory_id'] in state_c_return['memory_ids'] and q in state_c_return['questions'] and state_b['workspace_id']==workspace_a['workspace_id'] and not state_b['role_ids'] and not state_b['memory_ids'] and state_b['history_count']==0
(base/'harness/workspace-isolation-extra1-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
