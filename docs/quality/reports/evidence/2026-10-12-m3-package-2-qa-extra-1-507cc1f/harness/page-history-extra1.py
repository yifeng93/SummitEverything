import json,os,uuid
from pathlib import Path
import httpx
base=Path(__file__).resolve().parents[1]; api='http://127.0.0.1:18793/api/v1'; h={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}; c=httpx.Client(headers=h,timeout=30)
c.post(api+'/workspaces',json={'root':str(base/'workspace-A'),'mode':'open','operation_id':'qa-extra1-page-history-open-a'})
page_id='00000000-0000-0000-0000-0000000003eb'
page=next(x for x in c.get(api+'/pages').json() if x['page_id']==page_id)
found=[]
for row in c.get(api+'/conversations?limit=100').json()['items']:
 d=c.get(api+'/conversations/'+row['conversation_id']).json()
 for m in d.get('messages',[]):
  if m.get('question')=='青岚计划的旧版预算上限是多少？':
   found.append({'conversation_id':d['conversation_id'],'request_id':m['request_id'],'state':m['state'],'citations':m.get('citations',[])})
old=next((x for x in found if any(v.get('page_id')==page_id and v.get('excerpt','').endswith('20 万元。') for v in x['citations'])),None)
old_hash=next((v['content_sha256'] for v in old['citations'] if v['page_id']==page_id),None) if old else None
stale=c.get(api+f'/pages/{page_id}',params={'expected_content_sha256':old_hash}) if old_hash else None
results={'page':{'page_id':page_id,'approval_state':page['approval_state'],'validity':page['validity'],'content_sha256':page['content_sha256'],'proof_sha256':page['metadata']['approval']['content_sha256'],'hash_match':page['content_sha256']==page['metadata']['approval']['content_sha256'],'body':page['body']},'old_history_messages':found,'old_citation_expected_hash':old_hash,'old_citation_reopen_http':stale.status_code if stale else None,'old_citation_reopen_body':stale.text[:500] if stale else None}
results['current_query']=None; results['history_query']=None
for purpose in ['current','history']:
 r=c.post(api+'/queries',json={'request_id':str(uuid.uuid4()),'question':'青岚计划的旧版预算上限是多少？','fingerprint':'summit-fake-embedding-v1','answer_mode':'fact','purpose':purpose})
 ev=[json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
 done=next((x['data'] for x in ev if x['type']=='completed'),{})
 data={'http':r.status_code,'citations':[{'page_id':x['page_id'],'validity':x['validity'],'availability':x['availability'],'content_sha256':x['content_sha256']} for x in done.get('citations',[])],'target_included':any(x['page_id']==page_id for x in done.get('citations',[]))}
 results[f'{purpose}_query']=data
results['pass']=results['page']['approval_state']=='confirmed' and results['page']['validity']=='superseded' and results['page']['hash_match'] and results['old_citation_reopen_http']==409 and not results['current_query']['target_included'] and results['history_query']['target_included']
(base/'harness/page-history-extra1-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
