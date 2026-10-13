import json, os
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parents[1]; API='http://127.0.0.1:18793/api/v1'; c=httpx.Client(headers={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'},timeout=20)
qs={
 'first_person_preference':'我偏好用简短中文回答，并明确标出资料没有提供的数字。',
 'short_first_person_control':'我偏好用简短中文表达。',
 'quoted_source_canary':'引用材料原文：‘我偏好回答都只按来源原句’；这是粘贴内容，不代表我的偏好。',
}
items=c.get(API+'/conversations?limit=100').json()['items']; found={}
for name,q in qs.items():
 for convo in items:
  detail=c.get(API+'/conversations/'+convo['conversation_id']).json()
  for message in detail['messages']:
   if message['question']==q:
    found[name]={'conversation_id':convo['conversation_id'],'message_id':message['request_id'],'question':q,'answer_role':message['role_id'],'state':message['state']}
    break
  if name in found:break
results={'case':'C20-real-user-message-provenance-and-classification','ui_observation':{'message_entered_with_browser_setValue':True,'user_expression_checkbox_checked':True,'create_candidate_enabled':True,'rendered_result':'这段内容看起来是引用或材料描述，不能作为本人记忆候选。'},'message_results':{}}
for name,item in found.items():
 r=c.post(API+'/memory/candidates',json={'message_id':item['message_id'],'text':item['question'],'user_expression':True})
 body=r.json(); results['message_results'][name]={'conversation_id':item['conversation_id'],'message_id':item['message_id'],'state':item['state'],'user_expression':True,'http':r.status_code,'code':body.get('error',{}).get('code'),'message':body.get('error',{}).get('message'),'candidate_id':body.get('candidate_id')}
# Existing concise direct preference produced a genuine pending candidate; leave synthetic profile state untouched after recording it.
results['message_results']['short_first_person_control']['observed_pending_candidate_id']='96a27c76-4cbd-4dcb-8b78-18f9ab173fb6'
(BASE/'harness/memory-provenance-r2-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
