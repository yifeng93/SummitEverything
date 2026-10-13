from __future__ import annotations
import json, os, uuid
from pathlib import Path
import httpx
base=Path(__file__).resolve().parents[1]
api='http://127.0.0.1:18793/api/v1'; h={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}
c=httpx.Client(headers=h,timeout=30)
page_id='00000000-0000-0000-0000-0000000003ef'
pages=c.get(api+'/pages').json(); page=next(x for x in pages if x['page_id']==page_id)
results={'invalid_before_confirmation':{'approval_state':page['approval_state'],'validity':page['validity'],'content_hash':page['content_sha256'],'proof_hash':page['metadata']['approval']['content_sha256'],'hash_match':page['content_sha256']==page['metadata']['approval']['content_sha256']}}
def query(purpose, question):
 r=c.post(api+'/queries',json={'request_id':str(uuid.uuid4()),'question':question,'fingerprint':'summit-fake-embedding-v1','answer_mode':'fact','purpose':purpose})
 ev=[json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')]
 done=next((x['data'] for x in ev if x['type']=='completed'),{})
 return {'http':r.status_code,'citations':[{'page_id':x['page_id'],'validity':x['validity'],'availability':x['availability']} for x in done.get('citations',[])],'cited_invalid':any(x['page_id']==page_id for x in done.get('citations',[]))}
results['before_reconfirm']={'current':query('current','海棠项目旧流程上限是多少？'),'history':query('history','海棠项目旧流程上限是多少？')}
confirm=c.post(api+f'/pages/{page_id}/confirmations',json={'metadata':page['metadata'],'body':'海棠项目旧流程上限为 6.8 万元。','confirmation_id':'qa-extra1-invalid-explicit-confirm','operation_id':'qa-extra1-invalid-explicit-write','expected_base_sha256':page['content_sha256']})
results['explicit_reconfirm']={'http':confirm.status_code,'mutation':confirm.json()}
current=next(x for x in c.get(api+'/pages').json() if x['page_id']==page_id)
results['after_reconfirm']={'approval_state':current['approval_state'],'validity':current['validity'],'content_hash':current['content_sha256'],'proof_hash':current['metadata']['approval']['content_sha256'],'hash_match':current['content_sha256']==current['metadata']['approval']['content_sha256'],'current_query':query('current','海棠项目旧流程上限是多少？'),'history_query':query('history','海棠项目旧流程上限是多少？')}
results['pass']=results['invalid_before_confirmation']['approval_state']=='confirmed' and results['invalid_before_confirmation']['hash_match'] and not results['before_reconfirm']['current']['cited_invalid'] and results['before_reconfirm']['history']['cited_invalid'] and confirm.status_code==200 and current['approval_state']=='confirmed' and current['validity']=='invalid' and results['after_reconfirm']['hash_match'] and not results['after_reconfirm']['current_query']['cited_invalid'] and results['after_reconfirm']['history_query']['cited_invalid']
(base/'harness/history-eligibility-extra1-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
