import fs from 'node:fs/promises'
const base='/Users/yifengstudio/.codex/worktrees/qa-c18-reconcile-ui-309'
const workspace=`${base}/.local/qa/c18-309/workspace`
const evidence=`${base}/docs/quality/reports/evidence/2026-10-10-stage-a-recovery-ui-309`
const cdp=19337
const page=(await(await fetch(`http://127.0.0.1:${cdp}/json/list`)).json()).find(x=>x.type==='page')
const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let seq=0;const pending=new Map(),events=[],counts={log:0,info:0,warning:0,error:0,exception:0}
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,m=>m.error?reject(Error(m.error.message)):resolve(m));ws.send(JSON.stringify({id,method,params}))})}
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return}if(m.method==='Network.requestWillBeSent'){const u=new URL(m.params.request.url);events.push({method:m.params.request.method,path:u.pathname})}else if(m.method==='Network.responseReceived'){const e=events.findLast(x=>x.path===new URL(m.params.response.url).pathname&&!x.http_status);if(e)e.http_status=m.params.response.status}else if(m.method==='Runtime.consoleAPICalled')counts[m.params.type==='warning'?'warning':m.params.type==='error'?'error':m.params.type==='info'?'info':'log']++;else if(m.method==='Runtime.exceptionThrown')counts.exception++}
async function ev(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw Error(r.result.exceptionDetails.text);return r.result.result.value}
const pause=ms=>new Promise(r=>setTimeout(r,ms));async function wait(text){for(let i=0;i<150;i++){if((await ev('document.body.innerText')).includes(text))return;await pause(100)}throw Error('UI state timeout')}
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});await wait('先连接一个工作库')
await ev(`(()=>{const a=document.querySelector('#workspace-name'),b=document.querySelector('#workspace-path');for(const [e,v] of [[a,'QA C18 repair retest'],[b,${JSON.stringify(workspace)}]]){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}return true})()`)
const click=async label=>{if(!await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()===${JSON.stringify(label)});if(!b)return false;b.click();return true})()`))throw Error('UI control not found')}
await click('创建本地工作库');await wait('飞书任务与独立动作');await click('模拟授权飞书');await wait('已授权');
await fs.writeFile(`${evidence}/cdp-workspace-bootstrap-sanitized.json`,JSON.stringify({run_id:'qa-c18-reconcile-ui-30903c4',source_sha:'30903c4cdf73855af71a201e3edea6c535ee8199',requests:events,console:counts},null,2)+'\n');ws.close()
