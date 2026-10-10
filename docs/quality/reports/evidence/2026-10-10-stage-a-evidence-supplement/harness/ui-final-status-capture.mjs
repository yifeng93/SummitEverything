import fs from 'node:fs/promises'
const root='/Users/yifengstudio/.codex/worktrees/qa-stage-a-evidence/SummitEverything',evidence=`${root}/docs/quality/reports/evidence/2026-10-10-stage-a-evidence-supplement`,profile=`${root}/.local/qa/stage-a-evidence-20261010-run7`
const target=(await(await fetch('http://127.0.0.1:19317/json/list')).json()).find(x=>x.type==='page'&&x.url==='http://127.0.0.1:5173/')
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let seq=0;const pending=new Map(),requests=new Map(),events=[],logs={log:0,info:0,warning:0,error:0,exception:0}
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,m=>m.error?reject(Error(m.error.message)):resolve(m));ws.send(JSON.stringify({id,method,params}))})}
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return}if(m.method==='Network.requestWillBeSent'){const q=m.params.request,u=new URL(q.url),x={method:q.method,path:u.pathname,query:u.search?'<redacted>':''};try{if(q.postData){const b=JSON.parse(q.postData);x.body={};for(const k of ['action_id','kind','payload','confirmation_id','payload_sha256'])if(k in b)x.body[k]=b[k];for(const k of ['confirmation_id','payload_sha256'])if(k in x.body)x.body[k]='<redacted>'}}catch{x.body='<redacted>'}requests.set(m.params.requestId,x)}else if(m.method==='Network.responseReceived'){const x=requests.get(m.params.requestId);if(x)x.http_status=m.params.response.status}else if(m.method==='Network.loadingFinished'){const x=requests.get(m.params.requestId);if(x){events.push(x);send('Network.getResponseBody',{requestId:m.params.requestId}).then(r=>{try{const b=JSON.parse(r.result.body);x.response={};for(const k of ['action_id','kind','state'])if(k in b)x.response[k]=b[k]}catch{x.response='<body omitted>'}}).catch(()=>x.response='<body unavailable>')}}else if(m.method==='Runtime.consoleAPICalled'){const t=m.params.type;logs[t==='warning'?'warning':t==='error'?'error':t==='info'?'info':'log']++}else if(m.method==='Runtime.exceptionThrown')logs.exception++}
async function ev(s){const r=await send('Runtime.evaluate',{expression:s,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw Error(r.result.exceptionDetails.text);return r.result.result.value}
const pause=n=>new Promise(r=>setTimeout(r,n))
async function waitDetail(state){const end=Date.now()+7000;while(Date.now()<end){const x=await ev(`(()=>({id:(()=>{const p=[...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"'));return p?JSON.parse(p.textContent).action_id:null})(),status:document.querySelector('.action-detail [role="status"]')?.innerText??''}))()`);if(x.status.includes(state))return x;await pause(100)}throw Error('specific action-detail status timeout: '+state)}
async function shot(name){await ev(`(()=>{document.querySelector('.action-detail')?.scrollIntoView({block:'start'});return true})()`);await pause(200);const r=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(`${evidence}/screenshots/${name}.png`,Buffer.from(r.result.data,'base64'))}
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false})
const action=await ev(`(()=>{const p=[...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"'));return p?JSON.parse(p.textContent):null})()`)
if(!action)throw Error('no action detail is open')
const beforeState=await waitDetail('结果未知，请核实；此动作不会重发。')
const out={action_id:action.action_id,initial_ui:await ev('document.querySelector(".action-detail")?.innerText??""'),remote_count_before_replay:Object.keys(JSON.parse(await fs.readFile(`${profile}/remote/simulated_remote_tasks.json`,'utf8')).tasks??{}).length}
await shot('c16-supplement-unknown')
out.replay=await ev(`(async()=>{const a=JSON.parse([...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"')).textContent);const r=await fetch('/api/v1/actions/'+a.action_id+'/executions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({payload_sha256:a.payload_sha256,confirmation_id:a.confirmation_id})});const b=await r.json();return{http_status:r.status,action_id:b.action_id,state:b.state}})()`)
await waitDetail('结果未知，请核实；此动作不会重发。')
out.remote_count_after_replay=Object.keys(JSON.parse(await fs.readFile(`${profile}/remote/simulated_remote_tasks.json`,'utf8')).tasks??{}).length
out.replay_ui=await ev('document.querySelector(".action-detail")?.innerText??""')
await shot('c16-supplement-replay-unknown')
const unknownBeforeArchive=action.action_id
await ev(`(()=>{const b=[...document.querySelectorAll('.tasks-panel button')].find(x=>x.innerText.trim()==='查看动作记录');if(!b)return false;b.click();return true})()`)
const until=Date.now()+7000;while(Date.now()<until){if(await ev(`!![...document.querySelectorAll('.candidate-list button')].find(x=>x.innerText.includes('结果未知'))`))break;await pause(100)}
out.archive_records_visible=await ev('document.querySelector(".tasks-panel")?.innerText??""')
await ev(`(()=>{const b=[...document.querySelectorAll('.candidate-list button')].find(x=>x.innerText.includes('结果未知'));if(!b)return false;b.click();return true})()`)
await waitDetail('结果未知，请核实；此动作不会重发。')
out.archive_unknown_detail=await ev(`(()=>{const p=[...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"'));return {action_id:p?JSON.parse(p.textContent).action_id:null,text:document.querySelector('.action-detail')?.innerText??''}})()`)
await shot('c23-supplement-unresolved-after-archive-refresh')
await pause(1000);out.network=events;out.network_count=events.length;out.console=logs
await fs.writeFile(`${evidence}/supplement-final-ui-capture-sanitized.json`,JSON.stringify(out,null,2)+'\n')
ws.close();process.stdout.write(JSON.stringify({initial_id:beforeState.id,unknown_after_archive:out.archive_unknown_detail.action_id,events:events.length,remote:[out.remote_count_before_replay,out.remote_count_after_replay]}))
