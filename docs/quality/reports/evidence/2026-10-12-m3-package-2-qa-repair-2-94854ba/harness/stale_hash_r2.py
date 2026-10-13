import json, uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]
PAGE_ID='00000000-0000-0000-0000-0000000003eb'
PAGE=BASE/'workspace-A/QA青岚与朱雀合成线/QA青岚朱雀对照项目/青岚旧预算规则.md'
API='http://127.0.0.1:18793/api/v1'; H={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}
c=httpx.Client(headers=H,timeout=20)
old=c.get(API+'/pages').json(); p=next(x for x in old if x['page_id']==PAGE_ID)
oldsha=p['content_sha256']; oldapproval=p['metadata']['approval']['content_sha256']
text=PAGE.read_text(encoding='utf-8'); assert '青岚计划旧版预算上限为 20 万元。' in text
PAGE.write_text(text.replace('青岚计划旧版预算上限为 20 万元。','青岚计划旧版预算上限为 21 万元。'),encoding='utf-8')
newp=next(x for x in c.get(API+'/pages').json() if x['page_id']==PAGE_ID)
results={'case':'C13-external-edit-stale-index-and-reopen','before':{'content_sha256':oldsha,'approval_sha256':oldapproval,'validity':p['validity']},'after_external_edit':{'content_sha256':newp['content_sha256'],'approval_sha256':newp['metadata']['approval']['content_sha256'],'approval_state':newp['approval_state'],'validity':newp['validity'],'hash_mismatch':newp['content_sha256']!=newp['metadata']['approval']['content_sha256']},'queries':{}}
for purpose in ['current','history']:
 r=c.post(API+'/queries',json={'request_id':str(uuid.uuid4()),'question':'青岚计划旧版预算上限是多少？','fingerprint':'summit-fake-embedding-v1','purpose':purpose,'answer_mode':'fact'})
 events=[json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
 d=next(x['data'] for x in events if x['type']=='completed')
 results['queries'][purpose]={'http':r.status_code,'citations':[{'page_id':x['page_id'],'validity':x['validity'],'availability':x['availability'],'content_sha256':x['content_sha256']} for x in d['citations']],'source_statements':d['source_statements']}
results['historical_citation_reopen']={'http':c.get(API+f'/pages/{PAGE_ID}',params={'expected_content_sha256':oldsha}).status_code,'body':c.get(API+f'/pages/{PAGE_ID}',params={'expected_content_sha256':oldsha}).text}
(BASE/'harness/stale-hash-r2-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
