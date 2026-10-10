import fs from 'node:fs/promises'

const root = '/Users/yifengstudio/.codex/worktrees/qa-stage-a-evidence/SummitEverything'
const evidence = `${root}/docs/quality/reports/evidence/2026-10-10-stage-a-evidence-supplement`
const profile = `${root}/.local/qa/stage-a-evidence-20261010-run7`
const target = (await (await fetch('http://127.0.0.1:19317/json/list')).json()).find(
  (entry) => entry.type === 'page' && entry.url === 'http://127.0.0.1:5173/',
)
if (!target) throw new Error('isolated QA Chrome page not found')
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject })
let nextId = 0
const pending = new Map()
const requests = new Map()
const events = []
const consoleCounts = { log: 0, info: 0, warning: 0, error: 0, exception: 0 }
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); return }
  if (msg.method === 'Network.requestWillBeSent') {
    const req = msg.params.request
    const url = new URL(req.url)
    const item = { method: req.method, path: url.pathname, query: url.search ? '<redacted>' : '' }
    try {
      const body = req.postData ? JSON.parse(req.postData) : null
      if (body) {
        item.body = {}
        for (const key of ['action_id', 'kind', 'payload', 'expected_payload_sha256', 'payload_sha256', 'confirmation_id']) {
          if (Object.hasOwn(body, key)) item.body[key] = body[key]
        }
        if (item.body.payload && typeof item.body.payload === 'object') {
          const payload = item.body.payload
          item.body.payload = Object.fromEntries(Object.entries(payload).filter(([key]) => ['summary', 'description', 'due', 'task', 'task_guid', 'update_fields'].includes(key)))
        }
        for (const key of ['expected_payload_sha256', 'payload_sha256', 'confirmation_id']) if (key in item.body) item.body[key] = '<redacted>'
      }
    } catch { item.body = '<non-json redacted>' }
    requests.set(msg.params.requestId, item)
  } else if (msg.method === 'Network.responseReceived') {
    const request = requests.get(msg.params.requestId)
    if (request) request.http_status = msg.params.response.status
  } else if (msg.method === 'Network.loadingFinished') {
    const request = requests.get(msg.params.requestId)
    if (request) {
      const params = { requestId: msg.params.requestId }
      send('Network.getResponseBody', params).then((result) => {
        try {
          const body = JSON.parse(result.result.body)
          request.response = {}
          for (const key of ['action_id', 'kind', 'state', 'summary', 'guid', 'due', 'completed_at', 'detail']) {
            if (Object.hasOwn(body, key)) request.response[key] = body[key]
          }
          if (body.detail && typeof body.detail === 'object') {
            request.response.error = { code: body.detail.code ?? null, message: '<redacted>' }
          }
        } catch { request.response = '<body omitted>' }
      }).catch(() => { request.response = '<body unavailable>' })
      events.push(request)
    }
  } else if (msg.method === 'Network.loadingFailed') {
    const request = requests.get(msg.params.requestId)
    if (request) events.push({ ...request, failed: true })
  } else if (msg.method === 'Runtime.consoleAPICalled') {
    const type = msg.params.type
    consoleCounts[type === 'warning' ? 'warning' : type === 'error' ? 'error' : type === 'info' ? 'info' : 'log']++
  } else if (msg.method === 'Runtime.exceptionThrown') consoleCounts.exception++
}
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId
    pending.set(id, (msg) => msg.error ? reject(new Error(msg.error.message)) : resolve(msg))
    ws.send(JSON.stringify({ id, method, params }))
  })
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (result.result.exceptionDetails) throw new Error(result.result.exceptionDetails.text)
  return result.result.result.value
}
const pause = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms))
async function waitFor(text, timeout = 6000) {
  const start = Date.now()
  while (Date.now() - start < timeout) {
    const body = await evaluate('document.body.innerText')
    if (body.includes(text)) return body
    await pause(100)
  }
  throw new Error(`Timed out waiting for UI text: ${text}`)
}
async function click(label) {
  const found = await evaluate(`(() => { const b=[...document.querySelectorAll('button')].find(x => x.innerText.trim() === ${JSON.stringify(label)}); if (!b) return false; b.click(); return true })()`)
  if (!found) throw new Error(`Button not found: ${label}`)
}
async function setInput(selector, value) {
  const result = await evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); if(!el)return false; const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; const setter=Object.getOwnPropertyDescriptor(proto,'value').set; setter.call(el,${JSON.stringify(value)}); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return true })()`)
  if (!result) throw new Error(`Input not found: ${selector}`)
}
async function setLabeledInput(prefix, value, tag = 'input') {
  const ok = await evaluate(`(() => { const label=[...document.querySelectorAll('label')].find(x=>x.innerText.trim()===${JSON.stringify(prefix)}); const el=label?.querySelector(${JSON.stringify(tag)}); if(!el)return false; const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(el,${JSON.stringify(value)}); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return true })()`)
  if (!ok) throw new Error(`Labeled ${tag} not found: ${prefix}`)
}
async function saveScreenshot(name) {
  await evaluate(`(() => { const el=document.querySelector('.action-detail') ?? document.querySelector('.tasks-panel') ?? document.querySelector('.setup-screen'); el?.scrollIntoView({block:'start'}); return !!el })()`)
  await pause(100)
  const result = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  await fs.writeFile(`${evidence}/screenshots/${name}.png`, Buffer.from(result.result.data, 'base64'))
}
async function actionId() {
  const details = await evaluate(`(() => { const pre=[...document.querySelectorAll('.action-detail details pre')].find(x=>x.textContent.includes('"action_id"')); return pre?.textContent ?? '' })()`)
  return JSON.parse(details).action_id
}
async function keepActionDetailsVisible() {
  await evaluate(`(() => { const d=document.querySelector('.action-detail details'); if(d)d.open=false; return true })()`)
}
async function publicActionUi() {
  return evaluate(`(() => ({fields:document.querySelector('.action-detail dl')?.innerText ?? '',state:document.querySelector('.action-detail [role="status"]')?.innerText ?? ''}))()`)
}
async function doCreate({ key, title, mode, value = '', timezone = 'Asia/Shanghai' }) {
  await click('新建飞书任务')
  await waitFor('审阅任务内容')
  await setLabeledInput('任务标题', title)
  await setLabeledInput('任务描述', `Synthetic UI evidence: ${key}`, 'textarea')
  await evaluate(`(() => { const label=[...document.querySelectorAll('label')].find(x=>x.innerText.trim().startsWith('截止日期方式')); const s=label?.querySelector('select'); if(!s)return false; Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(s,${JSON.stringify(mode)}); s.dispatchEvent(new Event('change',{bubbles:true})); return true })()`)
  if (value) await setLabeledInput('截止日期', value)
  if (mode !== 'none') await setLabeledInput('日期时区', timezone)
  const formValues = await evaluate(`(() => ({title:document.querySelector('label input')?.value, inputs:[...document.querySelectorAll('.tasks-panel form input, .tasks-panel form textarea, .tasks-panel form select')].map(x=>({type:x.type||x.tagName.toLowerCase(),value:x.value})), text:document.querySelector('.tasks-panel form')?.innerText}))()`)
  await saveScreenshot(`${key}-input-form`)
  await click('审阅任务内容')
  await waitFor('待独立确认')
  const id = await actionId()
  await saveScreenshot(`${key}-preview`)
  const previewText = await evaluate(`document.querySelector('.action-detail')?.innerText ?? ''`)
  await click('独立确认此动作')
  await waitFor('已确认，尚未执行')
  await saveScreenshot(`${key}-confirmed`)
  await click('执行已确认动作')
  const expectedStateText = key === 'c17-mismatch' ? '结果未知，请核实；此动作不会重发。' : '动作已成功'
  await waitFor(expectedStateText)
  await keepActionDetailsVisible()
  await saveScreenshot(`${key}-result`)
  return { id, formValues, previewText, finalUi: await publicActionUi() }
}

await send('Page.enable')
await send('Runtime.enable')
await send('Log.enable')
await send('Network.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1200, deviceScaleFactor: 1, mobile: false })
await evaluate('window.scrollTo(0,0)')

await setInput('#workspace-name', 'Stage A evidence supplement synthetic')
await setInput('#workspace-path', `${profile}/workspace`)
await saveScreenshot('workspace-create-form')
await click('创建本地工作库')
await waitFor('飞书任务与独立动作', 10000)
await saveScreenshot('workspace-opened-tasks')
await click('模拟授权飞书')
await waitFor('已授权', 10000)
await saveScreenshot('fake-provider-authorized')

const cases = []
cases.push(await doCreate({ key: 'c17-no-due', title: 'QA supplement no due', mode: 'none' }))
cases.push(await doCreate({ key: 'c17-all-day', title: 'QA supplement all-day', mode: 'all_day', value: '2026-10-14' }))
cases.push(await doCreate({ key: 'c17-offset-time', title: 'QA supplement offset time', mode: 'time', value: '2026-10-15T09:30:00+08:00' }))
cases.push(await doCreate({ key: 'c17-mismatch', title: 'QA supplement mismatch', mode: 'time', value: '2026-10-16T11:00:00+08:00' }))
const mismatch = cases.at(-1)
const countBeforeReplay = JSON.parse(await fs.readFile(`${profile}/remote/simulated_remote_tasks.json`, 'utf8')).tasks
const replay = await evaluate(`(async()=>{const pre=document.querySelector('.action-detail pre');const action=JSON.parse(pre.textContent);const r=await fetch('/api/v1/actions/'+action.action_id+'/executions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({payload_sha256:action.payload_sha256,confirmation_id:action.confirmation_id})});const body=await r.json();return {http_status:r.status,body:{action_id:body.action_id,kind:body.kind,state:body.state}}})()`)
await pause(250)
const countAfterReplay = JSON.parse(await fs.readFile(`${profile}/remote/simulated_remote_tasks.json`, 'utf8')).tasks
await evaluate('window.scrollTo(0,0)')
await saveScreenshot('c17-mismatch-replay-unknown')
await click('只读核实远端结果')
await waitFor('动作已成功')
await keepActionDetailsVisible()
await saveScreenshot('c17-mismatch-reconciled')
const mismatchResult = await publicActionUi()
await pause(500)
for (const event of events) {
  if (event.response?.detail?.code) event.response.detail = '<redacted>'
}
const remote = JSON.parse(await fs.readFile(`${profile}/remote/simulated_remote_tasks.json`, 'utf8'))
const sanitizedRemote = Object.values(remote.tasks ?? {}).map((task) => ({
  guid: task.guid, summary: task.summary, description: task.description,
  due: task.due ? { timestamp: task.due.timestamp, is_all_day: task.due.is_all_day, timezone: task.due.timezone } : null,
  completed_at: task.completed_at,
}))
const report = {
  run_id: 'qa-stage-a-evidence-supplement-run7', origin: 'http://127.0.0.1:5173', api_port: 18917, web_port: 5173, cdp_port: 19317,
  isolated_profile: '.local/qa/stage-a-evidence-20261010-run7/chrome-profile',
  cases, mismatch: { action_id: mismatch.id, count_before_replay: Object.keys(countBeforeReplay).length, count_after_replay: Object.keys(countAfterReplay).length, replay, reconciliation_ui: mismatchResult },
  fake_remote_fields: sanitizedRemote,
  cdp_events: events, console_counts: consoleCounts,
}
await fs.writeFile(`${evidence}/c17-ui-run-sanitized.json`, JSON.stringify(report, null, 2) + '\n')
ws.close()
console.log(JSON.stringify({ case_ids: cases.map((item) => item.id), mismatch_id: mismatch.id, cdp_events: events.length, console_counts: consoleCounts, remote_tasks: sanitizedRemote.length }))
