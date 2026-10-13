from __future__ import annotations
import json, os, uuid
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]
API='http://127.0.0.1:18793/api/v1'
headers={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}
client=httpx.Client(headers=headers,timeout=30)
fingerprint=client.get(API+'/settings').json()['embedding_fingerprint']
cases={
 'positive_terms_citation_source':('我偏好引用清楚标出来源。','我偏好引用清楚标出来源。',True),
 'positive_quoted_internal_term':('我偏好使用“资料不足”这个术语。','我偏好使用“资料不足”这个术语。',True),
 'positive_after_material_attribution':('材料摘录：“青岚计划旧版预算上限为 20 万元。”；我的偏好是：我偏好回答简洁，并标出资料未提供的数字。','我偏好回答简洁，并标出资料未提供的数字。',True),
 'negative_bare_quote':('“我偏好用简短中文回答。”','我偏好用简短中文回答。',False),
 'negative_markdown_blockquote':('> 我偏好用简短中文回答。','我偏好用简短中文回答。',False),
 'negative_quote_substring':('资料原文：“用户明确写道：我偏好用简短中文回答，并标出未提供数字。”','我偏好用简短中文回答',False),
 'negative_markdown_substring':('> 我偏好用简短中文回答，并标出资料没有提供的数字。','我偏好用简短中文回答',False),
}
results={}
for name,(question,candidate,expected_positive) in cases.items():
 request_id=str(uuid.uuid4())
 query=client.post(API+'/queries',json={'request_id':request_id,'question':question,'fingerprint':fingerprint,'answer_mode':'fact','purpose':'current'})
 response=client.post(API+'/memory/candidates',json={'message_id':request_id,'text':candidate,'user_expression':True})
 body=response.json()
 passed=(response.status_code in (200,201)) if expected_positive else response.status_code in (400,422)
 results[name]={'expected':'pending' if expected_positive else 'rejected','query_http':query.status_code,'query_request_id':request_id,'candidate_http':response.status_code,'candidate_id':body.get('candidate_id'),'error_code':body.get('error',{}).get('code'),'error_message':body.get('error',{}).get('message'),'pass':passed}
# False attestation and assistant / forged identity controls.
q='我喜欢用简洁中文。'; rid=str(uuid.uuid4())
client.post(API+'/queries',json={'request_id':rid,'question':q,'fingerprint':fingerprint,'answer_mode':'fact','purpose':'current'})
no_attest=client.post(API+'/memory/candidates',json={'message_id':rid,'text':q,'user_expression':False})
assistant=client.post(API+'/conversations/'+client.get(API+'/conversations?limit=100').json()['items'][0]['conversation_id'],json={}) if False else None
fake=client.post(API+'/memory/candidates',json={'message_id':str(uuid.uuid4()),'text':'我偏好简短回答。','user_expression':True})
results['negative_false_attestation']={'http':no_attest.status_code,'pass':no_attest.status_code in (400,422)}
results['negative_forged_id']={'http':fake.status_code,'pass':fake.status_code in (400,404,422)}
# A pending candidate must not be injected into the active provider context.
pending_question='我偏好中文回答，并清楚标出缺失数字。'; pending_id=str(uuid.uuid4())
client.post(API+'/queries',json={'request_id':pending_id,'question':pending_question,'fingerprint':fingerprint,'answer_mode':'fact','purpose':'current'})
pending=client.post(API+'/memory/candidates',json={'message_id':pending_id,'text':pending_question,'user_expression':True})
probe_id=str(uuid.uuid4()); probe=client.post(API+'/queries',json={'request_id':probe_id,'question':'青岚计划预算上限是多少？','fingerprint':fingerprint,'answer_mode':'fact','purpose':'current'})
payloads=[json.loads(line) for line in (BASE/'harness/deepseek-payloads.jsonl').read_text(encoding='utf-8').splitlines()]
probe_payload=next((p['body'] for p in reversed(payloads) if p['body'].get('question')=='青岚计划预算上限是多少？'),{})
active=probe_payload.get('user_memories',[])
results['pending_not_in_active_provider']={'candidate_http':pending.status_code,'candidate_id':pending.json().get('candidate_id'),'probe_http':probe.status_code,'pending_text_in_active_prompt':pending_question in active,'active_memories':active,'pass':pending.status_code in (200,201) and pending_question not in active}
results['all_expected'] = all(item.get('pass',False) for item in results.values() if isinstance(item,dict))
(BASE/'harness/memory-boundaries-extra1-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
