import fs from 'node:fs/promises'
import {createHash} from 'node:crypto'
const base='/Users/yifengstudio/.codex/worktrees/qa-c18-reconcile-ui-309'
const evidence=`${base}/docs/quality/reports/evidence/2026-10-10-stage-a-recovery-ui-309`
const workspace=`${base}/.local/qa/c18-309/workspace`
const control=`${base}/.local/qa/c18-309/control.json`
const page=(await(await fetch('http://127.0.0.1:19337/json/list')).json()).find(x=>x.type==='page')
const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let seq=0;const pending=new Map(),requests=new Map(),network=[],bodyWaits=[]
const consoleCounts={log:0,info:0,warning:0,error:0,exception:0}
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,m=>m.error?reject(Error(m.error.message)):resolve(m));ws.send(JSON.stringify({id,method,params}))})}
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return}
 if(m.method==='Network.requestWillBeSent'){const q=m.params.request,u=new URL(q.url),x={method:q.method,path:u.pathname};try{if(q.postData){const b=JSON.parse(q.postData);x.body={};for(const k of ['action_id','kind','payload','mode','name'])if(k in b)x.body[k]=b[k];if(x.body.payload)x.body.payload=Object.fromEntries(Object.entries(x.body.payload).filter(([k])=>['project_id','expected_version','progress'].includes(k)));if('root'in b)x.body.root='<isolated-path>'}}catch{x.body='<omitted>'}requests.set(m.params.requestId,x)}
 else if(m.method==='Network.responseReceived'){const x=requests.get(m.params.requestId);if(x)x.http_status=m.params.response.status}
 else if(m.method==='Network.loadingFinished'){const x=requests.get(m.params.requestId);if(x){network.push(x);bodyWaits.push(send('Network.getResponseBody',{requestId:m.params.requestId}).then(r=>{try{const b=JSON.parse(r.result.body);x.response=Object.fromEntries(Object.entries(b).filter(([k])=>['action_id','kind','state','progress','progress_version'].includes(k)));if(b.evidence)x.response.evidence=b.evidence.map(v=>({kind:v.kind,found:v.found}))}catch{x.response='<omitted>'}}).catch(()=>{}))}}
 else if(m.method==='Network.loadingFailed'){const x=requests.get(m.params.requestId);if(x){x.error='network loading failed';network.push(x)}}
 else if(m.method==='Runtime.consoleAPICalled')consoleCounts[m.params.type==='warning'?'warning':m.params.type==='error'?'error':m.params.type==='info'?'info':'log']++
 else if(m.method==='Runtime.exceptionThrown')consoleCounts.exception++}
async function ev(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw Error(r.result.exceptionDetails.text);return r.result.result.value}
const pause=ms=>new Promise(r=>setTimeout(r,ms));async function wait(text,ms=12000){const until=Date.now()+ms;while(Date.now()<until){if((await ev('document.body.innerText')).includes(text))return;await pause(80)}throw Error('UI wait timed out')}
async function click(text){if(!await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().includes(${JSON.stringify(text)}));if(!b)return false;b.click();return true})()`))throw Error('UI button missing')}
async function shot(name){await ev('window.scrollTo(0,0)');await pause(160);const r=await send('Page.captureScreenshot',{format:'png'});await fs.writeFile(`${evidence}/screenshots/${name}.png`,Buffer.from(r.result.data,'base64'))}
async function action(){return ev(`(()=>{const p=[...document.querySelectorAll('.action-detail pre')].find(x=>x.textContent.includes('"action_id"'));return p?JSON.parse(p.textContent):null})()`)}
async function disk(){const raw=await fs.readFile(`${workspace}/.summit-everything/manifest.json`);const m=JSON.parse(raw);return{sha256:createHash('sha256').update(raw).digest('hex'),projects:m.projects.map(p=>({id:p.id,name:p.name,progress:p.progress,progress_version:p.progress_version}))}}
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false})
await wait('审阅进度变化');await wait('QA Recovery Project');const selected=await ev('document.querySelector(".action-form select")?.value');if(!selected)throw Error('project selection empty; do not proceed')
const out={run_id:'qa-c18-reconcile-ui-30903c4',source_sha:'30903c4cdf73855af71a201e3edea6c535ee8199',case:'C18 local progress persisted, success receipt write interrupted',project_id:selected,network,console:consoleCounts}
out.disk_before=await disk();await shot('c18-309-before-review')
await click('审阅进度变化');await wait('待独立确认');let a=await action();if(!a)throw Error('proposal action details absent');out.action_id=a.action_id;out.payload=a.payload;out.state_proposed=a.state;await shot('c18-309-confirmation-before')
await click('独立确认此动作');await wait('已确认，尚未执行');a=await action();out.state_confirmed=a.state;await shot('c18-309-confirmation-after')
await fs.writeFile(control,JSON.stringify({mode:'receipt_success_write_failure',fired:false}));await click('执行已确认动作');await wait('动作正在执行，请刷新结果');await pause(300);out.ui_receipt_lost=await ev('document.querySelector(".action-detail")?.innerText');out.disk_after_write=await disk();await shot('c18-309-receipt-lost-running')
await pause(300);await Promise.all(bodyWaits);out.network=network;out.console=consoleCounts;out.trace=await fs.readFile(`${base}/.local/qa/c18-309/trace.jsonl`,'utf8').then(s=>s.trim().split('\n').filter(Boolean).map(JSON.parse).map(x=>({event:x.event,mode:x.mode,counts:x.counts})))
await fs.writeFile(`${evidence}/cdp-c18-lost-receipt-sanitized.json`,JSON.stringify(out,null,2)+'\n');ws.close();process.stdout.write(JSON.stringify({action_id:out.action_id,state_proposed:out.state_proposed,state_confirmed:out.state_confirmed,manifest_before:out.disk_before.sha256,manifest_after:out.disk_after_write.sha256,requests:network.map(x=>[x.method,x.path,x.http_status,x.response?.state]),console:consoleCounts}))
