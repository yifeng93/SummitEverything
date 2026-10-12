from __future__ import annotations
import json, os, uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]
API='http://127.0.0.1:18373/api/v1'
H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
CAP=BASE/'harness'/'deepseek-payloads.jsonl'
def count(): return len(CAP.read_text().splitlines()) if CAP.exists() else 0
def parse(r): return [json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
with httpx.Client(headers=H,timeout=30) as c:
    before=count(); fp=c.get(API+'/settings').json()['embedding_fingerprint']
    r=c.post(API+'/queries',json={'request_id':str(uuid.uuid4()),'question':'为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。','fingerprint':fp,'answer_mode':'plan','purpose':'current'})
    ev=parse(r); done=next((x['data'] for x in ev if x['type']=='completed'),{})
    after=count()
    out={'case':'C19-fresh-ready-plan-isolated-provider-counter','http':r.status_code,'index_status':done.get('index_status'),'citations':done.get('citations'),'missing_information':done.get('missing_information'),'source_statements':done.get('source_statements'),'inferences':done.get('inferences'),'advice':done.get('advice'),'provider_calls_before':before,'provider_calls_after':after,'provider_called':after>before,'expected':'no provider call, no evidence, actionable missing information consistent with main answer'}
    out['status']='PASS' if r.status_code==200 and done.get('index_status')=='ready' and not done.get('citations') and not done.get('source_statements') and not done.get('inferences') and not done.get('advice') and bool(done.get('missing_information')) and after==before else 'FAIL'
    (BASE/'harness'/'extra2-plan-counter-result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out,ensure_ascii=False))
