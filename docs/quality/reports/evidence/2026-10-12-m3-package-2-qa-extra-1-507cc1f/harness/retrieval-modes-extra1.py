import json,os,uuid
from pathlib import Path
import httpx
base=Path(__file__).resolve().parents[1]; api='http://127.0.0.1:18793/api/v1'; c=httpx.Client(headers={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'},timeout=30)
c.post(api+'/workspaces',json={'root':str(base/'workspace-A'),'mode':'open','operation_id':'qa-extra1-retrieval-reopen-a'})
def q(text,mode='fact',purpose='current'):
 r=c.post(api+'/queries',json={'request_id':str(uuid.uuid4()),'question':text,'fingerprint':'summit-fake-embedding-v1','answer_mode':mode,'purpose':purpose})
 events=[json.loads(x[6:]) for x in r.text.splitlines() if x.startswith('data: ')]
 done=next((e['data'] for e in events if e['type']=='completed'),{})
 return {'http':r.status_code,'page_ids':[x['page_id'] for x in done.get('citations',[])],'validities':[x['validity'] for x in done.get('citations',[])],'source_statements':done.get('source_statements',[]),'inferences':done.get('inferences',[]),'advice':done.get('advice',[]),'missing_information':done.get('missing_information',[])}
a=q('比较青岚计划和朱雀项目的设备采购预算上限。','comparison','current')
b=q('为没有资料支持的银杏事项提出下一步方案，并列出仍缺的信息。','plan','current')
result={'comparison':a,'unsupported_plan':b}
ids={x['page_id'] for x in c.get(api+'/pages').json() if x['metadata']['title'] in ('设备预算备案','朱雀项目启动安排')}
result['expected_fixture_page_ids']=sorted(ids)
result['comparison_pass']=a['http']==200 and ids.issubset(set(a['page_ids'])) and bool(a['inferences'])
result['unsupported_plan_pass']=b['http']==200 and not b['page_ids'] and bool(b['missing_information']) and bool(b['advice'])
result['pass']=result['comparison_pass'] and result['unsupported_plan_pass']
(base/'harness/retrieval-modes-extra1-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
