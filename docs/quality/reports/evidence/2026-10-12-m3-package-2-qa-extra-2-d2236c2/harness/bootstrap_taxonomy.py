import json
import os
import httpx
base = 'http://127.0.0.1:18373/api/v1'
headers = {'Authorization': f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'}
with httpx.Client(base_url=base, headers=headers, timeout=10) as client:
    line = client.post('/lines', json={'name':'QA青岚与朱雀合成线','operation_id':'qa-r2-line-create'} )
    assert line.status_code == 201, (line.status_code, line.text)
    project = client.post('/projects', json={'line_id':line.json()['id'],'name':'QA青岚朱雀对照项目','operation_id':'qa-r2-project-create'})
    assert project.status_code == 201, (project.status_code, project.text)
    print(json.dumps({'line':line.json(),'project':project.json()},ensure_ascii=False))
