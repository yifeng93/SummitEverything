import { chromium } from '../../web/node_modules/@playwright/test/index.mjs'
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'], viewport: { width: 1280, height: 900 } })
const seen = []
const outside = []
await context.route('**/*', async route => {
  const req = route.request(); const url = new URL(req.url())
  if (url.origin !== 'http://127.0.0.1:5297') { outside.push(req.url()); return route.abort() }
  if (!url.pathname.startsWith('/api/')) return route.continue()
  seen.push({ path: url.pathname + url.search, method: req.method() })
  const settings = { mode:'fake', feishu:{ app_id:'', redirect_uri:'', identity:'app', calendar_id:'' }, llm:{ provider:'fake', model:null, account_id:'default', enabled:false }, embedding:{ provider:'fake', model:null, region:'cn', dimensions:1024, base_url:'https://example.invalid', enabled:false }, rerank:{ provider:'fake', model:null, region:'cn', dimensions:1024, base_url:'https://example.invalid', enabled:false }, credential_status:{}, capabilities:{}, keychain_available:false }
  let body = {}
  if (url.pathname === '/api/v1/workspaces/current') body = { workspace_id:'synthetic-workspace', root:'/tmp/synthetic', local_profile_dir:'/tmp/synthetic-profile', name:'Synthetic', read_only:false }
  else if (url.pathname === '/api/v1/first-use/progress') body = { step:5, completed:true, open:false }
  else if (url.pathname === '/api/v1/settings') body = settings
  else if (url.pathname === '/api/v1/integrations/feishu/status') body = { mode:'fake', authorized:false, app_configured:false, scopes:[], token_type:'user' }
  else if (url.pathname === '/api/v1/provider-smoke') body = { counts:{ deepseek_chat:0, model_studio_embedding:0, model_studio_rerank:0 }, limits:{ deepseek_chat:1, model_studio_embedding:1, model_studio_rerank:1 }, remaining:{ deepseek_chat:1, model_studio_embedding:1, model_studio_rerank:1 } }
  else if (url.pathname.startsWith('/api/v1/provider-smoke/')) body = { state:'succeeded' }
  else if (url.pathname === '/api/v1/action-intents') body = { items:[], next_cursor:null }
  else if (url.pathname === '/api/v1/intake/items' || url.pathname === '/api/v1/drafts' || url.pathname === '/api/v1/actions' || url.pathname === '/api/v1/lines' || url.pathname === '/api/v1/roles' || url.pathname === '/api/v1/memory' || url.pathname === '/api/v1/memory/candidates' || url.pathname === '/api/v1/projects' || url.pathname === '/api/v1/today' || url.pathname === '/api/v1/journal') body = []
  else if (url.pathname === '/api/v1/index/status') body = { fingerprint:null, pages:0, chunks:0, state:'not_ready', current_pages:0, stale_pages:0 }
  else if (url.pathname.includes('/calendar')) body = { items:[] }
  else body = {}
  await route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify(body) })
})
const page = await context.newPage()
page.setDefaultTimeout(7000)
const consoleErrors=[]; page.on('console', m=>{ if(m.type()==='error') consoleErrors.push(m.text()) })
await page.goto('http://127.0.0.1:5297')
await page.getByRole('button', { name:'设置', exact:true }).waitFor()
await page.waitForTimeout(1200)
await page.getByRole('button', { name:'设置', exact:true }).click()
await page.getByRole('button', { name:'连接飞书', exact:true }).click()
await page.getByRole('status').getByText(/已复制/).waitFor()
const copied = await page.evaluate(() => navigator.clipboard.readText())
const dialogCount = await page.locator('[role="dialog"]').count()
const apiAfterCopy = seen.filter(x => x.method !== 'GET' || /authorization|oauth/i.test(x.path))
await page.evaluate(() => { window.__savedClipboard = navigator.clipboard; Object.defineProperty(navigator, 'clipboard', { configurable:true, value:{ writeText: async value => { if (window.__clipReject) throw new Error('denied'); window.__retriedText = value } } }); window.__clipReject = true })
await page.getByRole('button', { name:'连接飞书', exact:true }).click()
await page.getByRole('textbox', { name:'飞书接入提示词' }).waitFor()
const fallbackFullText = await page.getByRole('textbox', { name:'飞书接入提示词' }).inputValue()
await page.evaluate(() => { window.__clipReject = false })
await page.getByRole('button', { name:'重试复制' }).click()
await page.getByText(/已复制，粘贴到 Codex \/ WorkBuddy/).waitFor()
const retrySuccess = await page.evaluate(() => Boolean(window.__retriedText?.includes('docs/contracts/MCP-v1.md')))
await page.setViewportSize({ width:390, height:844 })
const overflow = await page.evaluate(() => ({ scroll:document.documentElement.scrollWidth, client:document.documentElement.clientWidth }))
const result = { copiedOrigin:copied.includes('http://127.0.0.1:5297'), copiedMcpDoc:copied.includes('docs/contracts/MCP-v1.md'), copiedNoSecrets:!copied.includes('?token=') && !copied.includes('#'), fallbackFullText: fallbackFullText.includes('PUT /credentials/{provider}'), retrySuccess, dialogCount, apiAfterCopy, outsideRequests:outside, overflow, consoleErrors, apiSeen:seen, settingsRoute:seen.some(x=>x.path==='/api/v1/settings') }
await page.screenshot({ path:'.local/qa/settings-feishu-prompt.png', fullPage:true })
console.log(JSON.stringify(result,null,2))
await browser.close()
if (!result.retrySuccess || !result.fallbackFullText || !result.copiedOrigin || !result.copiedMcpDoc || !result.copiedNoSecrets || result.dialogCount !== 0 || apiAfterCopy.length || outside.length || overflow.scroll > overflow.client) process.exitCode=1
