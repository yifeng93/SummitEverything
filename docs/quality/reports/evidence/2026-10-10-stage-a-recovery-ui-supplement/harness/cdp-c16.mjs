import fs from 'node:fs/promises'
const base = '/Users/yifengstudio/.codex/worktrees/qa-stage-a-recovery-ui-supplement'
const evidence = `${base}/docs/quality/reports/evidence/2026-10-10-stage-a-recovery-ui-supplement`
const workspace = `${base}/.local/qa/stage-a-recovery-ui/workspace`
const control = `${base}/.local/qa/stage-a-recovery-ui/control.json`
const chrome = 19327
const page = (await (await fetch(`http://127.0.0.1:${chrome}/json/list`)).json()).find(x => x.type === 'page' && x.url.startsWith('http://127.0.0.1:17327'))
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let seq=0; const pending=new Map(), requests=new Map(), events=[]; const consoleCounts={log:0,info:0,warning:0,error:0,exception:0}
function send(method,params={}) { return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,m=>m.error?reject(Error(m.error.message)):resolve(m));ws.send(JSON.stringify({id,method,params}))}) }
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return}
 if(m.method==='Network.requestWillBeSent'){const q=m.params.request,u=new URL(q.url),x={method:q.method,path:u.pathname};try{if(q.postData){const b=JSON.parse(q.postData);x.body={};for(const k of ['action_id','kind','payload','confirmation_id','payload_sha256','mode','name'] )if(k in b)x.body[k]=b[k];if(x.body.payload)x.body.payload=Object.fromEntries(Object.entries(x.body.payload).filter(([k])=>['summary','description','due','project_id','progress','expected_version'].includes(k)));for(const k of ['confirmation_id','payload_sha256'])if(k in x.body)x.body[k]='<redacted>';if('root'in b)x.body.root='<isolated-path>'}}catch{x.body='<redacted>'}requests.set(m.params.requestId,x)}
 else if(m.method==='Network.responseReceived'){const x=requests.get(m.params.requestId);if(x)x.http_status=m.params.response.status}
 else if(m.method==='Network.loadingFinished'){const x=requests.get(m.params.requestId);if(x){events.push(x);send('Network.getResponseBody',{requestId:m.params.requestId}).then(r=>{try{const b=JSON.parse(r.result.body);if(Array.isArray(b))x.response={items:b.length};else{x.response=Object.fromEntries(Object.entries(b).filter(([k])=>['action_id','kind','state','progress','progress_version','authorized','service','workspace_open'].includes(k)));if(b.detail?.message)x.error_message=b.detail.message}}catch{x.response='<omitted>'}}).catch(()=>x.response='<unavailable>')}}
 else if(m.method==='Network.loadingFailed'){const x=requests.get(m.params.requestId);if(x){x.network_error=m.params.errorText;events.push(x)}}
 else if(m.method==='Runtime.consoleAPICalled'){const t=m.params.type;consoleCounts[t==='warning'?'warning':t==='error'?'error':t==='info'?'info':'log']++}else if(m.method==='Runtime.exceptionThrown')consoleCounts.exception++ }
async function ev(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw Error(r.result.exceptionDetails.text);return r.result.result.value}
const pause=(ms=250)=>new Promise(r=>setTimeout(r,ms))
async function waitText(text,ms=12000){const end=Date.now()+ms;while(Date.now()<end){if((await ev('document.body.innerText')).includes(text))return;await pause(100)}throw Error('UI wait timed out: '+text+' :: '+(await ev('document.body.innerText')).slice(-400))}
async function click(text){const ok=await ev(`(()=>{const e=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()===${JSON.stringify(text)});if(!e)return false;e.click();return true})()`);if(!ok)throw Error('button not found '+text)}
async function setLabel(prefix,val){const ok=await ev(`(()=>{const l=[...document.querySelectorAll('label')].find(x=>x.innerText.trim().startsWith(${JSON.stringify(prefix)}));if(!l)return false;const e=l.querySelector('input,textarea,select');if(!e)return false;const p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(val)});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);if(!ok)throw Error('field not found '+prefix)}
async function shot(name){await ev('window.scrollTo(0,0)');await pause(150);const r=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(`${evidence}/screenshots/${name}.png`,Buffer.from(r.result.data,'base64'))}
async function action(){return ev(`(()=>{const p=[...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"'));return p?JSON.parse(p.textContent):null})()`)}
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false})
const out={run_id:'qa-stage-a-recovery-ui-409b907',source_sha:'409b90704046c623184846c09c873cec053e946d',console:consoleCounts,network:events,steps:[]}
await waitText('先连接一个工作库');await shot('workspace-create-form')
await ev(`(()=>{const a=document.querySelector('#workspace-name'),b=document.querySelector('#workspace-path');for(const [e,v] of [[a,'QA 隔离模拟库'],[b,${JSON.stringify(workspace)}]]){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}return true})()`);await click('创建本地工作库');await waitText('飞书任务与独立动作');out.steps.push({step:'create_workspace',ui:(await ev('document.body.innerText')).includes('QA 隔离模拟库')?'已连接隔离模拟库':'unexpected'})
await click('模拟授权飞书');await waitText('已授权');await shot('fake-authorized')
await click('新建飞书任务');await waitText('审阅任务内容');await setLabel('任务标题','QA R4 process exit');await setLabel('任务描述','Synthetic crash reconciliation, no external material');await setLabel('截止日期方式','none');await click('审阅任务内容');await waitText('待独立确认');await shot('c16-confirmation-before')
const a=await action();out.c16_crash={action_id:a.action_id,payload_sha256:a.payload_sha256,payload:a.payload,state_before_confirmation:a.state};await click('独立确认此动作');await waitText('已确认，尚未执行');await shot('c16-confirmation-after');const ac=await action();out.c16_crash.confirmation_id=ac.confirmation_id;out.c16_crash.state_after_confirmation=ac.state
await fs.writeFile(control,JSON.stringify({mode:'',fired:false}));const btn=await ev(`(()=>[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='执行已确认动作')?.disabled)()`);out.c16_crash.execute_button_disabled_before=btn
await fs.writeFile(control,JSON.stringify({mode:'',fired:false}));await shot('c16-before-process-crash-execute');await fs.writeFile(control,JSON.stringify({mode:'',fired:false}));
// Re-arm to the process-exit fault used only by the local FakeFeishu task_create monkeypatch.
await fs.writeFile(control,JSON.stringify({mode:'',fired:false}));
// Fake harness selects faults by synthetic task title and no other provider is enabled.
await fs.writeFile(`${base}/.local/qa/stage-a-recovery-ui/fault-armed.json`,JSON.stringify({fault:'task_create_process_exit_after_persist',action_id:ac.action_id}))
// The harness's existing FakeFeishu patch performs process exit on this exact synthetic title.
await click('执行已确认动作');await pause(1600);await shot('c16-ui-after-process-exit')
out.c16_crash.remote_path='<isolated FakeFeishu remote file>';out.c16_crash.harness_trace_path='<isolated harness trace>'
out.console=consoleCounts;await fs.writeFile(`${evidence}/cdp-c16-initial-sanitized.json`,JSON.stringify(out,null,2)+'\n');ws.close();process.stdout.write(JSON.stringify({action_id:ac.action_id,events:events.length,console:consoleCounts}))
