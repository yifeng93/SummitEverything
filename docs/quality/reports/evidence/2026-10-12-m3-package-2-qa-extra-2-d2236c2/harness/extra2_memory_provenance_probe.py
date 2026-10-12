from __future__ import annotations
import json,os,uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]; API='http://127.0.0.1:18373/api/v1'; H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
def events(r):return [json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
results=[]
with httpx.Client(headers=H,timeout=30) as c:
 fp=c.get(API+'/settings').json()['embedding_fingerprint']
 positives=['我偏好用简短中文回答，并明确标出资料没有提供的数字']
 negatives=[('quoted-source','引用材料原文：“我偏好用简短中文回答，并明确标出资料没有提供的数字”；这不是我的偏好。'),('blockquote','> 我偏好用简短中文回答，并明确标出资料没有提供的数字\n这段是粘贴材料，不代表本人偏好。'),('material-attribution-first-person','材料中的负责人写道：我偏好用简短中文回答，并明确标出资料没有提供的数字；这是材料里他人的表达。')]
 ids={}
 for label,text in [('positive',positives[0]),*negatives]:
  rid=str(uuid.uuid4()); q=c.post(API+'/queries',json={'request_id':rid,'question':text,'fingerprint':fp,'answer_mode':'fact','purpose':'current'})
  ids[label]=(rid,text,q)
  if label=='positive':
   r=c.post(API+'/memory/candidates',json={'message_id':rid,'text':text,'user_expression':True}); results.append({'case':'explicit-first-person-positive-control','query_http':q.status_code,'candidate_http':r.status_code,'candidate_state':r.json().get('state'),'status':'PASS' if q.status_code==200 and r.status_code==201 and r.json().get('state')=='pending' else 'FAIL'})
  else:
   r=c.post(API+'/memory/candidates',json={'message_id':rid,'text':text,'user_expression':True}); results.append({'case':label,'query_http':q.status_code,'candidate_http':r.status_code,'error_code':r.json().get('error',{}).get('code'),'status':'PASS' if q.status_code==200 and r.status_code in (400,422) else 'FAIL'})
 # no/false attestation for a genuine message
 rid,text,_=ids['positive']
 for label,payload in [('attestation-omitted',{'message_id':rid,'text':text}),('attestation-false',{'message_id':rid,'text':text,'user_expression':False}),('forged-message-id',{'message_id':str(uuid.uuid4()),'text':'我偏好短句。','user_expression':True})]:
  r=c.post(API+'/memory/candidates',json=payload); results.append({'case':label,'http':r.status_code,'error_code':r.json().get('error',{}).get('code'),'status':'PASS' if r.status_code in (400,404,422) else 'FAIL'})
 # assistant answer can't be used as candidate against real user-message source
 rid=str(uuid.uuid4()); q=c.post(API+'/queries',json={'request_id':rid,'question':'青岚计划预算上限是多少？','fingerprint':fp,'answer_mode':'fact','purpose':'current'}); final=next((e['data'] for e in events(q) if e['type']=='completed'),{}); answer=final.get('text','')
 r=c.post(API+'/memory/candidates',json={'message_id':rid,'text':answer,'user_expression':True});results.append({'case':'assistant-answer-as-memory','query_http':q.status_code,'assistant_text_chars':len(answer),'candidate_http':r.status_code,'error_code':r.json().get('error',{}).get('code'),'status':'PASS' if q.status_code==200 and r.status_code in (400,422) else 'FAIL'})
result={'case':'C20-provenance-controls','results':results,'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL'}
(BASE/'harness'/'extra2-memory-provenance-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
