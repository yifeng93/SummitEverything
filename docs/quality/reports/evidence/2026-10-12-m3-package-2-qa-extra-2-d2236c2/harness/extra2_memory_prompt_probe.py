from __future__ import annotations
import json,os,uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]; A='http://127.0.0.1:18373/api/v1'; B='http://127.0.0.1:18375/api/v1'; H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}; ROOT=str(BASE/'workspace-A'); PREF='我偏好用简短中文回答，并明确标出资料没有提供的数字'; CAP=BASE/'harness'/'deepseek-payloads.jsonl'
def events(r):return [json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
def capture():return [json.loads(x) for x in CAP.read_text().splitlines()]
with httpx.Client(headers=H,timeout=30) as a,httpx.Client(headers=H,timeout=30) as b:
  for c,api,ident in ((a,A,'a'),(b,B,'b')):
    o=c.post(api+'/workspaces',json={'root':ROOT,'mode':'open','operation_id':f'qa-extra2-memory-prompt-open-{ident}'})
    assert o.status_code==201,(o.status_code,o.text)
  fp_b=b.get(B+'/settings').json()['embedding_fingerprint']; req_b=str(uuid.uuid4())
  q=b.post(B+'/queries',json={'request_id':req_b,'question':PREF,'fingerprint':fp_b,'answer_mode':'fact','purpose':'current'})
  ev=events(q); candidate=b.post(B+'/memory/candidates',json={'message_id':req_b,'text':PREF,'user_expression':True})
  pending_id=candidate.json().get('candidate_id')
  mem_b=b.get(B+'/memory').json()
  before_b=len(capture()); q_b=b.post(B+'/queries',json={'request_id':str(uuid.uuid4()),'question':'朱雀项目预算上限是多少？','fingerprint':fp_b,'answer_mode':'fact','purpose':'current'}); after_b=capture(); prompt_b=after_b[-1].get('system_prompt','') if len(after_b)>before_b else ''
  fp_a=a.get(A+'/settings').json()['embedding_fingerprint']; req_a=str(uuid.uuid4())
  q=a.post(A+'/queries',json={'request_id':req_a,'question':PREF,'fingerprint':fp_a,'answer_mode':'fact','purpose':'current'})
  ca=a.post(A+'/memory/candidates',json={'message_id':req_a,'text':PREF,'user_expression':True}); cid=ca.json().get('candidate_id')
  confirm=a.post(A+f'/memory/candidates/{cid}/confirmations',json={'confirmation_id':'qa-extra2-exact-pref-confirm','text':PREF})
  before_a=len(capture()); q_a=a.post(A+'/queries',json={'request_id':str(uuid.uuid4()),'question':'朱雀项目预算上限是多少？','fingerprint':fp_a,'answer_mode':'fact','purpose':'current'}); after_a=capture(); prompt_a=after_a[-1].get('system_prompt','') if len(after_a)>before_a else ''
  result={'case':'C20-pending-memory-excluded-active-memory-included-in-provider-prompt','pending_candidate_http':candidate.status_code,'pending_candidate_id':pending_id,'profile_b_memories_before_query':mem_b,'pending_phrase_in_system_prompt':PREF in prompt_b,'pending_query_http':q_b.status_code,'active_candidate_http':ca.status_code,'confirmation_http':confirm.status_code,'active_memory_text':next((x['text'] for x in a.get(A+'/memory').json() if x.get('memory_id')==confirm.json().get('memory_id')),None),'active_phrase_in_system_prompt':PREF in prompt_a,'active_query_http':q_a.status_code,'active_payload_prompt_sha256':__import__('hashlib').sha256(prompt_a.encode()).hexdigest(),'pending_payload_prompt_sha256':__import__('hashlib').sha256(prompt_b.encode()).hexdigest(),'provider_prompt_evidence':{'pending_fragment':prompt_b[:2400],'active_fragment':prompt_a[:2400]}}
  result['status']='PASS' if candidate.status_code==201 and not mem_b and q_b.status_code==200 and PREF not in prompt_b and ca.status_code in (200,201) and confirm.status_code==200 and q_a.status_code==200 and PREF in prompt_a else 'FAIL'
  (BASE/'harness'/'extra2-memory-prompt-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({k:v for k,v in result.items() if k!='provider_prompt_evidence'},ensure_ascii=False))
