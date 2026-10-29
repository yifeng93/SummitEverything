import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'

const root = path.dirname(new URL(import.meta.url).pathname)
const origin = 'http://127.0.0.1:5191'
const results = []
const screenshots = []
function record(id, pass, detail) { results.push({ id, status: pass ? 'PASS' : 'FAIL', detail }); if (!pass) throw new Error(`${id}: ${detail}`) }
const response = (body, status = 200, headers = {}) => ({ status, headers: { 'content-type': 'application/json', ...headers }, body: JSON.stringify(body) })
const fakeStatus = () => ({ counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 } })
const syntheticSettings = (keychain = true, complete = false) => ({
  mode: 'real', model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: 'http://127.0.0.1:5191/api/v1/integrations/feishu/callback', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: complete ? 'deepseek' : 'fake', model: complete ? 'deepseek-flash' : null, account_id: 'synthetic-account', enabled: complete, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: complete ? 'dashscope' : 'fake', model: complete ? 'qwen3.7-text-embedding' : null, region: 'cn', dimensions: 1024, base_url: 'https://example.aliyuncs.com/compatible-mode/v1', enabled: complete },
  rerank: { provider: complete ? 'dashscope' : 'fake', model: complete ? 'qwen3.7-text-rerank' : null, region: 'cn', dimensions: 1024, base_url: 'https://example.aliyuncs.com/api/v1', enabled: complete },
  capabilities: {}, credential_status: { deepseek: complete, dashscope: complete, feishu_app: false },
  keychain_available: keychain, embedding_fingerprint: complete ? 'synthetic-fp' : null,
})
const scopeFor = (question) => ({ question, purpose: 'current', answer_mode: 'fact', source_versions: { 'synthetic-page-id': 'synthetic-sha' }, context: { user_memories: [], previous_user_questions: [] }, max_output_tokens: 2048, reasoning_effort: 'low' })
const sse = (events) => events.map(({ id, seq, type, data }) => `data: ${JSON.stringify({ request_id: id, seq, type, data })}\n\n`).join('')

async function setupPage(browser, config = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const state = {
    settings: config.settings ?? syntheticSettings(true, false),
    plans: 0, confirms: 0, queries: [], indexCalls: 0,
    historyFail: false, queryMode: 'complete', planMode: 'success',
    statusGate: config.statusFirst === 'loading-failure' ? (() => { let unlock; const promise = new Promise((resolve) => { unlock = resolve }); return { promise, released: false, release() { this.released = true; unlock() } } })() : null,
  }
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== origin) return route.abort('blockedbyclient')
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const p = url.pathname.slice('/api/v1'.length)
    const method = route.request().method()
    if (p === '/workspaces/current') return route.fulfill(response({ workspace_id: 'synthetic-ws', name: 'Synthetic Test Workspace', local_profile_dir: '/synthetic/profile' }))
    if (p === '/projects') return route.fulfill(response([]))
    if (p === '/first-use/progress') return route.fulfill(response({ step: 2, completed: false, open: false }))
    if (p === '/settings' && method === 'GET') return route.fulfill(response(state.settings))
    if (p === '/settings' && method === 'PATCH') {
      const patch = route.request().postDataJSON()
      state.settings = { ...state.settings, ...patch,
        llm: { ...state.settings.llm, ...(patch.llm ?? {}) },
        embedding: { ...state.settings.embedding, ...(patch.embedding ?? {}) },
        rerank: { ...state.settings.rerank, ...(patch.rerank ?? {}) },
        feishu: { ...state.settings.feishu, ...(patch.feishu ?? {}) },
      }
      return route.fulfill(response(state.settings))
    }
    if (p.startsWith('/credentials/') && method === 'PUT') {
      const provider = p.split('/').at(-1)
      if (provider === 'deepseek' || provider === 'dashscope') state.settings.credential_status[provider] = true
      return route.fulfill(response({ provider, configured: true }))
    }
    if (p === '/provider-smoke' && method === 'GET') return route.fulfill(response(fakeStatus()))
    if (p === '/integrations/feishu/status') return route.fulfill(response({ mode: 'real', authorized: false, app_configured: false, identity: 'app', token_type: 'user', scopes: [], user_identity_verified: false, credential_error: null }))
    if (p === '/index/status') {
      state.indexCalls++
      if (state.statusGate && !state.statusGate.released) {
        await state.statusGate.promise
        return route.fulfill(response({ error: { code: 'unavailable', message: 'synthetic read failure' } }, 503))
      }
      return route.fulfill(response({ fingerprint: 'synthetic-index-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 }))
    }
    if (p === '/pages') return route.fulfill(response([{ page_id: 'synthetic-page-id', relative_path: 'Synthetic/Page.md', content_sha256: 'synthetic-sha', metadata: { title: 'Synthetic confirmed page' }, body: null }]))
    if (p === '/conversations' && method === 'GET') return route.fulfill(response({ items: [], next_cursor: null }))
    if (p === '/roles' || p === '/memory' || p === '/memory/candidates') return route.fulfill(response([]))
    if (p === '/acceptance-plans' && method === 'POST') {
      state.plans++
      if (state.planMode === 'reject') return route.fulfill(response({ error: { code: 'provider_disabled', message: '所需 AI 服务尚未配置完成：合成配置变化。请到设置重新配置。' } }, 409))
      const scope = scopeFor(route.request().postDataJSON().scope.question)
      return route.fulfill(response({ plan: { plan_id: `synthetic-plan-${state.plans}`, scope_sha256: `synthetic-scope-${state.plans}`, request_limit: 3, available: false, disabled_reason: 'acceptance_plan_required' }, scope }))
    }
    if (p.startsWith('/acceptance-plans/') && p.endsWith('/confirm')) { state.confirms++; return route.fulfill(response({ confirmed: true })) }
    if (p === '/queries' && method === 'POST') {
      const body = route.request().postDataJSON()
      state.queries.push(body)
      if (state.queryMode === 'reject') return route.fulfill(response({ error: { code: 'provider_disabled', message: '所需 AI 服务已发生变化，请到设置复核。' } }, 409))
      const requestId = body.request_id
      const conversationId = 'synthetic-conversation'
      const text = state.queryMode === 'truncated' ? '合成的部分回答' : '合成回答已完成。'
      const events = [{ id: requestId, seq: 1, type: 'status', data: { state: 'retrieving', conversation_id: conversationId } }, { id: requestId, seq: 2, type: 'delta', data: { text } }]
      if (state.queryMode === 'complete') events.push({ id: requestId, seq: 3, type: 'completed', data: { text, source_statements: [], inferences: [], advice: [], missing_information: [] } })
      return route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream', 'X-Conversation-ID': conversationId }, body: sse(events) })
    }
    if (p.endsWith('/reopen') && method === 'POST') {
      if (state.historyFail) return route.fulfill(response({ error: { code: 'unavailable', message: '合成历史读取失败' } }, 503))
      return route.fulfill(response({ conversation_id: 'synthetic-conversation', title: '合成问题', created_at: '2026-10-29T00:00:00Z', updated_at: '2026-10-29T00:00:00Z', message_count: 1, state: 'completed', messages: [] }))
    }
    return route.fulfill(response({ error: { code: 'unexpected', message: `unexpected synthetic route ${method} ${p}` } }, 500))
  })
  page.on('console', (message) => { if (message.type() === 'error') results.push({ id: 'browser-console', status: 'OBSERVED', detail: message.text() }) })
  page.on('pageerror', (error) => results.push({ id: 'browser-pageerror', status: 'FAIL', detail: error.message }))
  await page.goto(origin)
  await page.getByRole('button', { name: '知识问答' }).click()
  await page.getByLabel('你的问题').waitFor()
  return { context, page, state }
}
async function shot(page, name) {
  const file = path.join(root, `${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  screenshots.push(file)
}

const browser = await chromium.launch({ headless: true })
try {
  // Real-mode incomplete provider preflight and settings round trip.
  const { context, page, state } = await setupPage(browser, { statusFirst: 'loading-failure' })
  await page.getByText('正在读取本机索引状态…').waitFor()
  await shot(page, 'index-loading')
  record('Q5-index-loading', !(await page.getByText('还没有本机索引').count()), '索引尚在读取时没有显示未建立空态')
  state.statusGate.release()
  await page.getByRole('alert').filter({ hasText: '暂时无法读取本机索引状态' }).waitFor()
  record('Q5-index-failed', !(await page.getByText('还没有本机索引').count()), '索引失败显示读取失败而非未建立')
  await shot(page, 'index-read-failed')
  await page.getByRole('button', { name: '重新读取' }).click()
  await page.getByText('已就绪', { exact: true }).waitFor()
  record('Q5-index-retry', state.indexCalls >= 2, `点击重试后 ready；status 请求数=${state.indexCalls}`)

  const question = '合成问题：场地怎么安排？'
  await page.getByLabel('你的问题').fill(question)
  await page.getByRole('button', { name: '开始检索' }).click()
  await page.getByText(/真实问答暂不可用/).waitFor()
  record('Q1-preflight-block', state.plans === 0 && state.queries.length === 0, `三项 Fake/禁用在真实模式下提示具体配置缺项；计划=${state.plans} 查询=${state.queries.length}`)
  record('Q1-no-false-disconnect', !(await page.getByText('连接中断').count()) && !(await page.getByText('没有找到可引用的依据').count()), '未把配置缺项显示成连接中断或无依据')
  record('Q1-retains-question', await page.getByLabel('你的问题').inputValue() === question, '配置失败后问题仍在输入框')
  await shot(page, 'real-preflight-missing')
  await page.getByRole('button', { name: '去设置配置模型' }).click()
  await page.getByRole('heading', { name: '设置' }).waitFor()
  await page.getByRole('button', { name: '配置 AI 模型与密钥' }).click()
  const llm = page.getByLabel('整理与问答模型')
  const embedding = page.getByLabel('知识索引向量化模型')
  const rerank = page.getByLabel('检索结果排序模型')
  await llm.selectOption('deepseek')
  await embedding.selectOption('dashscope')
  await rerank.selectOption('dashscope')
  await page.getByLabel('DeepSeek API Key').fill('synthetic-only-not-a-real-key')
  await page.getByLabel('阿里云 Model Studio API Key').fill('synthetic-only-not-a-real-key')
  await page.getByRole('button', { name: '保存 AI 模型设置' }).click()
  await page.getByText(/设置已保存在本机/).waitFor()
  const visibleSettingsText = await page.locator('body').innerText()
  console.log('SETTINGS_FLAGS=' + JSON.stringify({ real: visibleSettingsText.includes('正式连接（各项服务需完成配置）'), confirm: visibleSettingsText.includes('真实调用前需逐次确认'), embedding: visibleSettingsText.includes('知识索引向量化配置'), stale: visibleSettingsText.includes('真实 provider 已选择') }))
  await shot(page, 'settings-saved')
  const settingsGood = visibleSettingsText.includes('正式连接（各项服务需完成配置）') && visibleSettingsText.includes('真实调用前需逐次确认') && visibleSettingsText.includes('知识索引向量化配置') && !visibleSettingsText.includes('真实 provider 已选择')
  console.log('SETTINGS_GOOD=' + settingsGood)
  record('Q6-settings-language', settingsGood, '设置状态用中文说明配置和逐次确认，移除会误导为已可调用的状态词')
  await page.getByRole('button', { name: '知识问答' }).click()
  record('Q1-return-retains-question', await page.getByLabel('你的问题').inputValue() === question, '从设置返回后原问题仍在输入框')
  await page.getByRole('button', { name: '开始检索' }).click()
  await page.getByRole('region', { name: '真实问答发送预览' }).waitFor()
  record('Q2-preview', state.plans === 1 && state.queries.length === 0, '完整合成配置产生预览，尚未发查询')
  const previewText = await page.getByRole('region', { name: '真实问答发送预览' }).innerText()
  console.log('PREVIEW_TEXT=' + previewText.replace(/\n/g, ' | '))
  await shot(page, 'real-query-preview')
  record('Q2-plan-reason-not-blocked', previewText.includes(question) && previewText.includes('Synthetic confirmed page'), 'available=false / acceptance_plan_required 不阻止计划预览')
  await shot(page, 'real-query-preview')
  state.historyFail = true
  await page.getByRole('button', { name: '确认并发送本次问题' }).click()
  await page.getByText('合成回答已完成。').waitFor()
  await page.getByText('完成', { exact: false }).first().waitFor()
  await page.getByText(/历史同步失败/).waitFor()
  record('Q4-completed-history-fail', state.queries.length === 1 && state.queries[0].acceptance_plan_id === 'synthetic-plan-1' && !(await page.getByText('连接中断').count()), '查询仅发一次；completed 后历史读取失败保留完成态和结果')
  record('Q2-confirm-once', state.confirms === 1, `独立确认请求数=${state.confirms}`)
  await shot(page, 'completed-history-read-failed')

  // True SSE truncation must retain partial text, mark interrupted, and never auto replay.
  await page.getByRole('button', { name: '新建对话' }).click()
  state.historyFail = false
  state.queryMode = 'truncated'
  const secondQuestion = '合成问题：断流复演'
  await page.getByLabel('你的问题').fill(secondQuestion)
  await page.getByRole('button', { name: '开始检索' }).click()
  await page.getByRole('region', { name: '真实问答发送预览' }).waitFor()
  await page.getByRole('button', { name: '确认并发送本次问题' }).click()
  await page.getByText('合成的部分回答').waitFor()
  await page.getByText('连接中断', { exact: false }).waitFor()
  record('Q4-truncated-no-replay', state.queries.length === 2 && state.queries[1].question === secondQuestion && await page.getByLabel('你的问题').inputValue() === '', `SSE 无 completed 后保留部分、显示断流且没有自动重复请求；查询数=${state.queries.length}`)
  await shot(page, 'truncated-query-partial')
  await context.close()

  // Keychain unavailable blocks locally with no acceptance plan or query.
  const keychain = await setupPage(browser, { settings: syntheticSettings(false, false) })
  await keychain.page.getByLabel('你的问题').fill('合成问题：钥匙串不可用')
  await keychain.page.getByRole('button', { name: '开始检索' }).click()
  await keychain.page.getByText(/本机钥匙串不可用/).waitFor()
  record('Q1-keychain-unavailable', keychain.state.plans === 0 && keychain.state.queries.length === 0, `Keychain 不可用不发计划或查询；plans=${keychain.state.plans}, queries=${keychain.state.queries.length}`)
  await keychain.page.getByRole('button', { name: '去设置配置模型' }).click()
  await keychain.page.getByRole('button', { name: '配置 AI 模型与密钥' }).click()
  await keychain.page.getByText('真实模式保存密钥会失败关闭').first().waitFor()
  record('Q1-keychain-settings-guidance', (await keychain.page.locator('body').innerText()).includes('不可用（密钥保存失败关闭）'), '设置页给钥匙串故障具体说明')
  await shot(keychain.page, 'keychain-unavailable-settings')
  await keychain.context.close()

  // Fresh settings but server-side provider state changes between preflight and API gate.
  const race = await setupPage(browser, { settings: syntheticSettings(true, true) })
  race.state.planMode = 'reject'
  await race.page.getByLabel('你的问题').fill('合成问题：计划时配置变化')
  await race.page.getByRole('button', { name: '开始检索' }).click()
  await race.page.getByText(/配置变化/).waitFor()
  record('Q3-preview-409', race.state.plans === 1 && race.state.queries.length === 0 && await race.page.getByLabel('你的问题').inputValue() === '合成问题：计划时配置变化', 'preview 409 显示可恢复配置错误并保留问题，不提交 query')
  race.state.planMode = 'success'; race.state.queryMode = 'reject'
  await race.page.getByRole('button', { name: '开始检索' }).click()
  await race.page.getByRole('region', { name: '真实问答发送预览' }).waitFor()
  await race.page.getByRole('button', { name: '确认并发送本次问题' }).click()
  await race.page.getByText(/所需 AI 服务已发生变化/).waitFor()
  record('Q3-query-409', race.state.plans === 2 && race.state.confirms === 1 && race.state.queries.length === 1 && !(await race.page.getByText('连接中断').count()), 'queries 409 配置變更為明確失敗，未假斷流亦未自動重發')
  await shot(race.page, 'query-config-race-409')
  await race.context.close()

  for (const result of results) if (result.status === 'FAIL') throw new Error(result.detail)
  await fs.writeFile(path.join(root, 'browser-results.json'), JSON.stringify({ sha: '2e85af7ef580246b10d7d359849f2584a2bad0bb', parentSyntheticBaseline: 'f39c15b4f1a691757c92c214bf11eb11f5b9ce39', runtimeMetadata: 'UNVERIFIED', mode: 'Chromium headless, local Vite; every /api/v1 route was intercepted with synthetic responses; non-local requests aborted', results, screenshots }, null, 2))
  console.log(JSON.stringify({ results, screenshots }, null, 2))
} catch (error) {
  await fs.writeFile(path.join(root, 'browser-results.partial.json'), JSON.stringify({ results, screenshots, error: String(error) }, null, 2))
  console.error(error)
  process.exitCode = 1
} finally {
  await browser.close()
}
