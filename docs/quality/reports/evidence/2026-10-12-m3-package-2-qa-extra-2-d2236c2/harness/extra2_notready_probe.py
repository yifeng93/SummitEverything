from __future__ import annotations
import json, os, uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]; API='http://127.0.0.1:18373/api/v1'; H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}; root=BASE/'workspace-notready'
CAP=BASE/'harness'/'deepseek-payloads.jsonl'
def count():return len(CAP.read_text().splitlines()) if CAP.exists() else 0
def ev(r):return [json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
results=[]
with httpx.Client(headers=H,timeout=30) as c:
    opened=c.post(API+'/workspaces',json={'root':str(root),'mode':'create','name':'QA not-ready synthetic workspace','operation_id':'qa-extra2-notready-create'})
    if opened.status_code!=201:raise RuntimeError((opened.status_code,opened.text))
    opened=c.post(API+'/workspaces',json={'root':str(root),'mode':'open','operation_id':'qa-extra2-notready-open'})
    status=c.get(API+'/index/status').json(); before=count(); fp=c.get(API+'/settings').json()['embedding_fingerprint']
    for mode in ('fact','comparison','plan'):
        r=c.post(API+'/queries',json={'request_id':str(uuid.uuid4()),'question':f'QA无索引状态{mode}未提供数字的资料是什么？','fingerprint':fp,'answer_mode':mode,'purpose':'current'})
        e=ev(r); done=next((x['data'] for x in e if x['type']=='completed'),{})
        results.append({'mode':mode,'http':r.status_code,'index_status':done.get('index_status'),'citations':len(done.get('citations',[])),'missing_information':done.get('missing_information'),'provider_before':before,'provider_after':count()})
    result={'case':'C19-not-ready-index-three-modes','workspace_open_http':opened.status_code,'index':status,'queries':results}
    result['status']='PASS' if status.get('state') in ('not_ready','not-ready','unbuilt') and all(x['http']==200 and x['index_status'] in ('not_ready','not-ready','unbuilt') and x['citations']==0 and bool(x['missing_information']) and x['provider_after']==before for x in results) else 'FAIL'
    (BASE/'harness'/'extra2-notready-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
