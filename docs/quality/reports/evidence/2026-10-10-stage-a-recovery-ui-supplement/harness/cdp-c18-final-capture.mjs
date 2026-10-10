import fs from 'node:fs/promises'
const base='/Users/yifengstudio/.codex/worktrees/qa-stage-a-recovery-ui-supplement'
const evidence=`${base}/docs/quality/reports/evidence/2026-10-10-stage-a-recovery-ui-supplement`
const page=(await(await fetch('http://127.0.0.1:19327/json/list')).json()).find(x=>x.type==='page')
const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let seq=0;const pending=new Map(),events=[]
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,m=>m.error?reject(Error(m.error.message)):resolve(m));ws.send(JSON.stringify({id,method,params}))})}
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return}if(m.method==='Network.requestWillBeSent'){let u=new URL(m.params.request.url);events.push({method:m.params.request.method,path:u.pathname})}if(m.method==='Network.responseReceived'){let x=events.findLast(x=>x.path===new URL(m.params.response.url).pathname);if(x)x.http_status=m.params.response.status}}
async function ev(expression){return(await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.result.value}
async function click(t){return ev(`(()=>{let b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().includes(${JSON.stringify(t)}));if(!b)return false;b.click();return true})()`)}
async function wait(t){for(let i=0;i<100;i++){if((await ev('document.body.innerText')).includes(t))return;await new Promise(r=>setTimeout(r,100))}throw Error('wait '+t)}
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false})
await click('查看动作记录');await wait('改变项目进度 · 动作已成功');await click('改变项目进度 · 动作已成功');await wait('最终动作：改变项目进度');await new Promise(r=>setTimeout(r,300))
const ui=await ev('document.querySelector(".action-detail")?.innerText');if(!ui?.includes('动作已成功'))throw Error('selected action detail not succeeded: '+ui)
await ev('window.scrollTo(0,0)');const png=(await send('Page.captureScreenshot',{format:'png'})).result.data;await fs.writeFile(`${evidence}/screenshots/c18-reconciled-succeeded-final.png`,Buffer.from(png,'base64'));await fs.writeFile(`${evidence}/cdp-c18-final-visible-succeeded.json`,JSON.stringify({action_id:'ed8a32f0-9580-4e8a-a1d1-c2f9bfeecefd',ui,network:events},null,2)+'\n');process.stdout.write(JSON.stringify({action_id:'ed8a32f0-9580-4e8a-a1d1-c2f9bfeecefd',hasSucceeded:ui.includes('动作已成功'),requests:events.length}));ws.close()
