from __future__ import annotations
import json,os,uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]; API='http://127.0.0.1:18373/api/v1'; H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}; CAP=BASE/'harness'/'deepseek-payloads.jsonl'
def n():return len(CAP.read_text().splitlines()) if CAP.exists() else 0
with httpx.Client(headers=H,timeout=30) as c:
 fp=c.get(API+'/settings').json()['embedding_fingerprint']; role=c.post(API+'/roles',json={'name':'QA预算拒绝角色','instructions':'四个字符','context_budget':2})
 role_data=role.json(); before=n(); r=c.post(API+'/queries',json={'request_id':str(uuid.uuid4()),'question':'朱雀项目预算上限是多少？','fingerprint':fp,'answer_mode':'fact','purpose':'current','role_id':role_data['role_id']}); after=n()
 result={'case':'C20-role-instruction-context-budget-readable-422-no-provider','role_http':role.status_code,'query_http':r.status_code,'error':r.json(),'provider_before':before,'provider_after':after,'role_id_redacted':'local synthetic role','status':'PASS' if role.status_code==201 and r.status_code==422 and r.json().get('error',{}).get('code')=='context_budget_exceeded' and after==before else 'FAIL'}
 if role.status_code==201: result['delete_role_http']=c.delete(API+'/roles/'+role_data['role_id']).status_code
 (BASE/'harness'/'extra2-role-budget-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
