import json,os,uuid
from pathlib import Path
import httpx
base=Path(__file__).resolve().parents[1]; api='http://127.0.0.1:18793/api/v1'; h={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}; c=httpx.Client(headers=h,timeout=30)
question='为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。'
payloads=base/'harness/deepseek-payloads.jsonl'
def count(): return len(payloads.read_text(encoding='utf-8').splitlines()) if payloads.exists() else 0
status=c.get(api+'/index/status').json(); before=count()
r=c.post(api+'/queries',json={'request_id':str(uuid.uuid4()),'question':question,'fingerprint':'summit-fake-embedding-v1','answer_mode':'plan','purpose':'current'})
lines=[x for x in r.text.splitlines() if x.startswith('data: ')]
events=[json.loads(x[6:]) for x in lines]; done=next((x['data'] for x in events if x['type']=='completed'),{})
after=count()
result={'question':question,'index_status_before':status,'http':r.status_code,'event_types':[x['type'] for x in events],'completed':{'text':done.get('text'),'citations':done.get('citations'),'source_statements':done.get('source_statements'),'inferences':done.get('inferences'),'advice':done.get('advice'),'missing_information':done.get('missing_information'),'index_status':done.get('index_status')},'provider_calls_before':before,'provider_calls_after':after,'provider_called':after>before}
(base/'harness/no-data-diagnostic-extra1-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
