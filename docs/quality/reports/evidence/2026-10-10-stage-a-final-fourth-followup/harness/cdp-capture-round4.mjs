import fs from 'node:fs/promises'
const port = 19239
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
const target = targets.find((value) => value.type === 'page' && value.url === 'http://127.0.0.1:15228/')
if (!target) throw new Error('isolated round-four CDP page is unavailable')
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject })
let id = 0
const pending = new Map()
const requested = new Map()
const routes = new Map()
const consoleCounts = { log: 0, info: 0, warning: 0, error: 0, exception: 0 }
const consoleEvents = []
const failed = []
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message)
    pending.delete(message.id)
    return
  }
  if (message.method === 'Network.requestWillBeSent') {
    const request = message.params.request
    const url = new URL(request.url)
    const destination = url.protocol === 'http:' || url.protocol === 'https:'
      ? { origin: url.origin, path: url.pathname }
      : { origin: 'inline-resource', path: `<${url.protocol.slice(0, -1)}>` }
    requested.set(message.params.requestId, { method: request.method, ...destination })
  } else if (message.method === 'Network.responseReceived') {
    const request = requested.get(message.params.requestId)
    if (request) {
      const key = `${request.method} ${request.origin}${request.path} ${message.params.response.status}`
      routes.set(key, (routes.get(key) ?? 0) + 1)
    }
  } else if (message.method === 'Network.loadingFailed') {
    const request = requested.get(message.params.requestId)
    failed.push(request ? { method: request.method, origin: request.origin, path: request.path } : { destination: 'unresolved-local-request' })
  } else if (message.method === 'Runtime.consoleAPICalled') {
    const type = message.params.type
    const key = type === 'warning' ? 'warning' : type === 'error' ? 'error' : type === 'info' ? 'info' : 'log'
    consoleCounts[key] += 1
    if (type === 'warning' || type === 'error') consoleEvents.push({ source: 'console', type, timestamp: message.params.timestamp })
  } else if (message.method === 'Runtime.exceptionThrown') {
    consoleCounts.exception += 1
    consoleEvents.push({ source: 'runtime', type: 'exception', timestamp: message.params.timestamp })
  }
}
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const requestId = ++id
    pending.set(requestId, (message) => message.error ? reject(new Error(message.error.message)) : resolve(message.result))
    ws.send(JSON.stringify({ id: requestId, method, params }))
  })
}
await send('Page.enable')
await send('Runtime.enable')
await send('Log.enable')
await send('Network.enable')
await send('Page.reload', { ignoreCache: true })
await new Promise((resolve) => setTimeout(resolve, 2400))
const result = {
  target_origin: 'http://127.0.0.1:15228',
  profile: '.local/qa/stage-a-final-round4/chrome-profile',
  capture_window_ms: 2400,
  network: {
    response_count: [...routes.values()].reduce((sum, count) => sum + count, 0),
    failed_request_count: failed.length,
    routes: Object.fromEntries([...routes.entries()].sort(([a], [b]) => a.localeCompare(b))),
    failed_destinations: failed,
  },
  console_counts: consoleCounts,
  console_warning_error_exception_events: consoleEvents,
}
await fs.writeFile('docs/quality/reports/evidence/2026-10-10-stage-a-final-fourth-followup/cdp-events-sanitized.json', JSON.stringify(result, null, 2) + '\n')
const screenshot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
await fs.writeFile('.local/qa/stage-a-final-round4/cdp-final-capture.png', Buffer.from(screenshot.data, 'base64'))
ws.close()
console.log(JSON.stringify({ response_count: result.network.response_count, failed_request_count: failed.length, console_counts: consoleCounts, routes: Object.keys(result.network.routes).length }))
