const { test, expect } = require('../../web/node_modules/@playwright/test')
const fs = require('node:fs')
const path = require('node:path')
const q = '青榆访客登记流程是什么？'
const pageHash = 'a'.repeat(64)
const settings = {
  mode: 'real', model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'synthetic-account', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', region: 'cn', dimensions: 512, base_url: '', enabled: true },
  rerank: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', region: 'cn', dimensions: 512, base_url: '', enabled: true },
  capabilities: {}, credential_status: { feishu_app: false, deepseek: true, dashscope: false }, keychain_available: true,
  embedding_fingerprint: 'synthetic-local-fingerprint',
  local_model: { model: 'BAAI/bge-small-zh-v1.5', revision: 'synthetic-revision', dimensions: 512, token_limit: 512, download_size_bytes: 95330972, state: 'ready', downloaded_bytes: 95330972, progress_percent: 100, error_code: null },
}
function sse(id) {
  const events = [
    { request_id: id, seq: 1, type: 'status', data: { state: 'retrieving', conversation_id: 'synthetic-conversation' } },
    { request_id: id, seq: 2, type: 'citation', data: { page_id: 'synthetic-page', content_sha256: pageHash, chunk_id: 'synthetic-chunk', heading: '访客登记', excerpt: '访客先在前台核验姓名并记录来访时间。', validity: 'current', availability: 'available' } },
    { request_id: id, seq: 3, type: 'delta', data: { text: '访客先在前台核验姓名并记录来访时间。' } },
    { request_id: id, seq: 4, type: 'completed', data: { answer_id: 'synthetic-answer', question: q, text: '访客先在前台核验姓名并记录来访时间。', citations: [{ page_id: 'synthetic-page', content_sha256: pageHash, chunk_id: 'synthetic-chunk', heading: '访客登记', excerpt: '访客先在前台核验姓名并记录来访时间。', validity: 'current', availability: 'available' }], answer_mode: 'fact', source_statements: ['访客先在前台核验姓名并记录来访时间。'], inferences: [], advice: [], missing_information: [], purpose: 'current', index_status: 'ready' } },
  ]
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
}
async function appRoutes(page, options = {}) {
  const calls = []
  let queryPosts = 0
  let activeSettings = options.settings ?? settings
  let preparePosts = 0
  await page.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url()), method = req.method()
    if (url.origin !== 'http://127.0.0.1:5174') return route.abort()
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const p = url.pathname.replace('/api/v1', '')
    calls.push({ method, path: p, search: url.search, body: req.postDataJSON?.() })
    let body = []
    if (p === '/workspaces/current') body = { workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }
    else if (p === '/first-use/progress') body = method === 'PUT' ? req.postDataJSON() : { step: 5, completed: true, open: false }
    else if (p === '/projects' || p === '/roles' || p === '/memory' || p === '/memory/candidates') body = []
    else if (p === '/pages') body = options.pages ?? []
    else if (p === '/pages/synthetic-page') body = { page_id: 'synthetic-page', relative_path: '合成项目/访客登记.md', metadata: { id: 'synthetic-page', title: '访客登记说明', role: 'knowledge', kind: 'topic', line_id: 'synthetic-line', project_id: 'synthetic-project' }, body: '访客先在前台核验姓名并记录来访时间。', content_sha256: pageHash, raw_sha256: pageHash, storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
    else if (p === '/settings' && method === 'PATCH') {
      const patch = req.postDataJSON()
      activeSettings = { ...activeSettings, ...patch }
      body = activeSettings
    }
    else if (p === '/settings') body = activeSettings
    else if (p === '/retrieval-model/prepare' && method === 'POST') {
      preparePosts++
      if (options.failPrepareOnce && preparePosts === 1) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'synthetic_download_failed', message: '模拟下载失败，可重试' } }) })
      activeSettings = { ...activeSettings, local_model: { ...activeSettings.local_model, state: 'ready', progress_percent: 100, downloaded_bytes: activeSettings.local_model.download_size_bytes } }
      body = activeSettings.local_model
    }
    else if (p === '/index/status') body = options.indexStatus ?? { fingerprint: 'synthetic-local-fingerprint', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 }
    else if (p === '/index/plans' && method === 'POST') { const request = req.postDataJSON(); body = { plan_id: 'synthetic-index-plan', workspace_id: 'synthetic-workspace', mode: request.mode, fingerprint: request.fingerprint, page_ids: ['synthetic-page'], page_versions: { 'synthetic-page': pageHash }, estimated_tokens: 15, estimated_cost: 0, page_preview: [{ title: '访客登记说明', version: 'v1' }] } }
    else if (p === '/index/jobs' && method === 'POST') body = { indexed_pages: 1, indexed_chunks: 1, embedded_chunks: 1, reused_chunks: 0, active_fingerprint: 'synthetic-local-fingerprint' }
    else if (p === '/conversations' || p.startsWith('/conversations?')) body = { items: [], next_cursor: null }
    else if (p === '/action-intents') body = { items: [], next_cursor: null }
    else if (p === '/acceptance-plans' && method === 'POST') body = { plan: { plan_id: 'synthetic-query-plan', scope_sha256: 'synthetic-scope-sha', request_limit: 1 }, scope: { question: q, purpose: 'current', source_versions: { 'synthetic-page': pageHash }, max_output_tokens: 2048, reasoning_effort: 'low' } }
    else if (p === '/acceptance-plans/synthetic-query-plan/confirm' && method === 'POST') return route.fulfill({ status: 204, body: '' })
    else if (p === '/queries' && method === 'POST') {
      queryPosts++
      const id = req.postDataJSON().request_id
      return route.fulfill({ status: 200, contentType: 'text/event-stream', headers: { 'X-Conversation-ID': 'synthetic-conversation' }, body: sse(id) })
    }
    else if (p === '/conversations/synthetic-conversation/reopen') body = { conversation_id: 'synthetic-conversation', title: q, created_at: '', updated_at: '', message_count: 1, state: 'completed', messages: [{ request_id: 'synthetic-request', question: q, answer: '访客先在前台核验姓名并记录来访时间。', state: 'completed', purpose: 'current', answer_mode: 'fact', citations: [], events: [], created_at: '' }] }
    else if (p === '/first-use/progress') body = { step: 5, completed: true, open: false }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  return { calls, get queryPosts() { return queryPosts }, get settings() { return activeSettings } }
}
test('AskView real/local512/DeepSeek with DashScope absent reaches confirmation, SSE citation, and desktop viewport', async ({ page }, info) => {
  const tracker = await appRoutes(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: '知识问答' }).click()
  await expect(page.getByRole('heading', { name: '知识问答' })).toBeVisible()
  const input = page.getByLabel('你的问题')
  await input.fill(q)
  await page.getByRole('button', { name: '开始检索' }).click()
  await expect(page.getByText('请确认本次问答发送范围')).toBeVisible()
  await expect(page.getByText(/最多 1 次云端请求：DeepSeek 生成回答；向量化与排序在本机完成/)).toBeVisible()
  expect(tracker.calls.some(c => c.path.includes('dashscope') || c.path.includes('credentials/dashscope'))).toBe(false)
  expect(tracker.calls.filter(c => c.path === '/queries')).toHaveLength(0)
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'ask-confirm-desktop.png'), fullPage: true })
  await page.getByRole('button', { name: '确认并发送本次问题' }).click()
  await expect(page.getByText('访客先在前台核验姓名并记录来访时间。').first()).toBeVisible()
  const citationButton = page.getByRole('button', { name: /访客登记/ })
  await expect(citationButton).toBeVisible()
  await expect(page.getByText('原引用版本已更新')).toHaveCount(0)
  await citationButton.click()
  await expect(page.getByText('访客登记说明', { exact: true }).first()).toBeVisible()
  await expect(page.locator('.page-reader .page-body')).toContainText('访客先在前台核验姓名并记录来访时间。')
  expect(tracker.calls.some(c => c.path === '/pages/synthetic-page' && c.search === `?expected_content_sha256=${pageHash}` && c.method === 'GET')).toBe(true)
  await expect.poll(() => tracker.queryPosts).toBe(1)
  const geometry = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  expect(geometry).toEqual({ width: 1440, scroll: 1440, body: 1440 })
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'ask-citation-current-desktop.png'), fullPage: true })
  await info.attach('ask-390-geometry', { body: JSON.stringify(geometry), contentType: 'application/json' })
})
test('missing local model retains the question and provides a settings action', async ({ page }) => {
  await appRoutes(page, { settings: { ...settings, local_model: { ...settings.local_model, state: 'not_prepared', progress_percent: 0 } } })
  await page.goto('/')
  await page.getByRole('button', { name: '知识问答' }).click()
  const input = page.getByLabel('你的问题')
  await input.fill('保留的合成问题')
  await page.getByRole('button', { name: '开始检索' }).click()
  await expect(page.getByText(/本地检索模型尚未准备/)).toBeVisible()
  await expect(input).toHaveValue('保留的合成问题')
  await page.getByRole('button', { name: '去设置配置模型' }).click()
  await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
})

test('settings shows failed prepare retry and explicit legacy migration while retaining legacy credential state', async ({ page }) => {
  const legacy = { ...settings, embedding: { ...settings.embedding, provider: 'dashscope', model: 'qwen3.7-text-embedding', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' }, rerank: { ...settings.rerank, provider: 'dashscope', model: 'qwen3.7-text-rerank', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1' }, credential_status: { ...settings.credential_status, dashscope: true }, local_model: { ...settings.local_model, state: 'not_prepared', downloaded_bytes: 0, progress_percent: 0 } }
  const tracker = await appRoutes(page, { settings: legacy, failPrepareOnce: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: '设置' }).click()
  await expect(page.getByText('旧云端检索设置已停用')).toBeVisible()
  expect(await page.getByRole('button', { name: '切换到本地检索' }).count()).toBe(1)
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'settings-legacy-migration-desktop.png'), fullPage: true })
  await page.getByRole('button', { name: '切换到本地检索' }).click()
  await expect(page.getByText(/原有云端密钥仍留在本机/)).toBeVisible()
  expect(tracker.settings.credential_status.dashscope).toBe(true)
  expect(tracker.calls.some(c => c.method === 'DELETE' && c.path.includes('credentials'))).toBe(false)
  await page.getByRole('button', { name: '准备本地模型' }).click()
  await expect(page.getByRole('alert').filter({ hasText: '模拟下载失败，可重试' })).toBeVisible()
  await expect(page.getByRole('button', { name: '准备本地模型' })).toBeVisible()
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'settings-prepare-failure-desktop.png'), fullPage: true })
  await page.getByRole('button', { name: '准备本地模型' }).click()
  await expect(page.getByRole('status').filter({ hasText: '已准备好' })).toBeVisible()
  expect(tracker.calls.filter(c => c.path === '/retrieval-model/prepare' && c.method === 'POST')).toHaveLength(2)
  expect(tracker.calls.some(c => c.path.includes('acceptance-plans'))).toBe(false)
  const metrics = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  expect(metrics).toEqual({ width: 1440, scroll: 1440, body: 1440 })
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'settings-prepare-ready-desktop.png'), fullPage: true })
})

test('approval confirms local index range without paid acceptance plan', async ({ page }) => {
  const confirmedPage = { page_id: 'synthetic-page', relative_path: '合成项目/访客登记.md', metadata: { id: 'synthetic-page', title: '访客登记说明', role: 'knowledge', kind: 'topic', line_id: 'synthetic-line', project_id: 'synthetic-project' }, body: '访客先在前台核验姓名并记录来访时间。', content_sha256: pageHash, raw_sha256: pageHash, storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const tracker = await appRoutes(page, { pages: [confirmedPage], indexStatus: { state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: '审批' }).click()
  const group = page.getByRole('region', { name: '搜索与问答准备' })
  await expect(group.getByRole('button', { name: '准备已确认的内容' })).toBeVisible()
  await group.getByRole('button', { name: '准备已确认的内容' }).click()
  await expect(page.getByText(/将准备 1 页已确认内容/)).toBeVisible()
  await page.getByRole('button', { name: '查看范围并确认' }).click()
  const dialog = page.getByRole('dialog', { name: '确认准备搜索和问答内容？' })
  await expect(dialog).toContainText('不会向 DeepSeek 或其他云端服务发送索引内容')
  expect(tracker.calls.some(c => c.path.includes('/acceptance-plans'))).toBe(false)
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'approval-index-confirm-desktop.png'), fullPage: true })
  await dialog.getByRole('button', { name: '确认并开始准备' }).click()
  await expect.poll(() => tracker.calls.filter(c => c.path === '/index/jobs' && c.method === 'POST').length).toBe(1)
  expect(tracker.calls.filter(c => c.path === '/index/plans' && c.method === 'POST')[0].body).toMatchObject({ mode: 'initial', fingerprint: 'synthetic-local-fingerprint' })
  expect(tracker.calls.some(c => c.path.includes('/acceptance-plans'))).toBe(false)
  const metrics = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  expect(metrics).toEqual({ width: 1440, scroll: 1440, body: 1440 })
  await page.screenshot({ path: path.join(__dirname, 'screenshots', 'approval-index-confirmed-desktop.png'), fullPage: true })
})
