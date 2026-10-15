const { createRequire } = require('node:module')
const { resolve } = require('node:path')
const { expect, test } = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')

const settings = {
  mode: 'real',
  model_studio_account_id: 'synthetic-account',
  feishu: { app_id: 'synthetic-app', redirect_uri: 'http://127.0.0.1:18793/callback', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'synthetic-account', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'dashscope', model: 'qwen3.7-text-embedding', region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/compatible-mode/v1', enabled: true },
  rerank: { provider: 'dashscope', model: 'qwen3.7-text-rerank', region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/api/v1', enabled: true },
  capabilities: Object.fromEntries(['llm', 'embedding', 'rerank'].map((id) => [id, { available: false, configured: true, disabled_reason: 'acceptance_plan_required' }])),
  credential_status: { feishu_app: true, deepseek: true, dashscope: true },
  keychain_available: true,
  embedding_fingerprint: 'synthetic-fingerprint-only',
}

const smoke = { counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 } }

test('settings reads are local, destructive action is confirmed, and AI badge reflects only last check', async ({ page }, testInfo) => {
  const calls = []
  const externalAttempts = []
  let rerankAttempt = 0
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5175') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const method = route.request().method()
    const path = url.pathname
    calls.push({ method, path })
    if (method === 'GET' && path.endsWith('/workspaces/current')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/qa-profile' }) })
    if (method === 'GET' && path.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) })
    if (method === 'GET' && path.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smoke) })
    if (method === 'GET' && path.endsWith('/integrations/feishu/status')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'real', authorized: false, app_configured: true, user_identity_verified: false }) })
    if (method === 'POST' && path.endsWith('/provider-smoke/model-studio-rerank')) {
      rerankAttempt += 1
      return route.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ error: { code: 'synthetic_failure', message: '模拟失败' } }) })
    }
    if (method === 'POST' && path.endsWith('/provider-smoke/deepseek-chat')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ outcome: 'synthetic-success' }) })
    if (method === 'DELETE' && path.endsWith('/credentials/deepseek')) return route.fulfill({ status: 204, body: '' })
    if (method === 'GET' && path.endsWith('/intake/items')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    if (method === 'GET' && path.endsWith('/drafts')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    if (method === 'GET' && path.endsWith('/actions')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    if (method === 'GET' && path.endsWith('/lines')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    if (method === 'GET' && path.endsWith('/projects')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    if (method === 'GET' && path.endsWith('/pages')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  await page.getByRole('button', { name: '设置' }).click()
  await expect(page.getByRole('region', { name: 'AI 模型' })).toBeVisible()
  const aiCard = page.getByRole('region', { name: 'AI 模型' })
  await expect(aiCard.getByText('整理与问答模型', { exact: true })).toBeVisible()
  await expect(aiCard.getByText('知识索引向量化', { exact: true })).toBeVisible()
  await expect(aiCard.getByText('检索结果排序', { exact: true })).toBeVisible()
  await expect(aiCard.getByText('已配置，待本次确认')).toHaveCount(3)
  expect(calls.some((call) => call.method === 'POST')).toBe(false)

  await page.locator('details.settings-advanced-block > summary').click()
  await page.getByRole('button', { name: /Rerank（剩余 1）/ }).click()
  const dialog = page.getByRole('dialog', { name: /Rerank/ })
  await expect(dialog).toBeVisible()
  expect(calls.filter((call) => call.method === 'POST')).toHaveLength(0)
  await dialog.getByRole('button', { name: '取消' }).click()
  expect(calls.filter((call) => call.method === 'POST')).toHaveLength(0)

  await page.getByRole('button', { name: /Rerank（剩余 1）/ }).click()
  await page.getByRole('dialog').getByRole('button', { name: '确认发送本次检查' }).click()
  await expect(aiCard.getByText('验证失败', { exact: true })).toBeVisible()
  expect(calls.filter((call) => call.method === 'POST' && call.path.endsWith('/provider-smoke/model-studio-rerank'))).toHaveLength(1)

  await page.getByRole('button', { name: /DeepSeek Chat（剩余 1）/ }).click()
  await page.getByRole('dialog').getByRole('button', { name: '确认发送本次检查' }).click()
  await expect(aiCard.getByText('验证通过', { exact: true })).toBeVisible()
  expect(rerankAttempt).toBe(1)
  expect(calls.filter((call) => call.method === 'POST')).toHaveLength(2)
  expect(await aiCard.locator('.settings-capability-item').allTextContents()).toEqual([
    expect.stringContaining('整理与问答模型'),
    expect.stringContaining('知识索引向量化'),
    expect.stringContaining('检索结果排序'),
  ])

  await page.getByRole('button', { name: '删除 DeepSeek 密钥' }).click()
  const deleteDialog = page.getByRole('dialog', { name: '删除所选本机密钥？' })
  await expect(deleteDialog).toBeVisible()
  expect(await page.evaluate(() => document.activeElement?.textContent)).toBe('取消')
  expect(calls.filter((call) => call.method === 'DELETE')).toHaveLength(0)
  await deleteDialog.getByRole('button', { name: '取消' }).click()
  expect(calls.filter((call) => call.method === 'DELETE')).toHaveLength(0)
  await page.getByRole('button', { name: '删除 DeepSeek 密钥' }).click()
  await page.getByRole('dialog', { name: '删除所选本机密钥？' }).getByRole('button', { name: '删除密钥' }).dblclick()
  await expect.poll(() => calls.filter((call) => call.method === 'DELETE').length).toBe(1)
  expect(externalAttempts).toEqual([])
  await testInfo.attach('api-manifest.json', { body: JSON.stringify({ calls, externalAttempts }, null, 2), contentType: 'application/json' })
})

test('Feishu status refresh discards the last successful card value on a later read error', async ({ page }, testInfo) => {
  let feishuReads = 0
  let failNextRead = false
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5175') return route.abort()
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const path = url.pathname
    if (path.endsWith('/workspaces/current')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/qa-profile' }) })
    if (path.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) })
    if (path.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smoke) })
    if (path.endsWith('/integrations/feishu/status')) {
      feishuReads += 1
      return failNextRead
        ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'synthetic_failure', message: '模拟读取失败' } }) })
        : route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'real', authorized: true, app_configured: true, user_identity_verified: false }) })
    }
    if (path.endsWith('/intake/items') || path.endsWith('/drafts') || path.endsWith('/actions') || path.endsWith('/lines') || path.endsWith('/projects') || path.endsWith('/pages')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.goto('/')
  await page.getByRole('button', { name: '设置' }).click()
  const feishuCard = page.getByRole('region', { name: '飞书' })
  await expect(feishuCard.getByText('已授权', { exact: true })).toBeVisible()
  await page.locator('details.settings-advanced-block > summary').click()
  failNextRead = true
  await page.getByRole('button', { name: '重新读取授权状态' }).click()
  await expect(feishuCard.locator('.conn-badge').getByText('授权状态暂时无法读取', { exact: true })).toBeVisible()
  await testInfo.attach('observed-state.json', { body: JSON.stringify({ successfulState: '已授权', afterFailedRefresh: '授权状态暂时无法读取', reads: feishuReads }, null, 2), contentType: 'application/json' })
})
