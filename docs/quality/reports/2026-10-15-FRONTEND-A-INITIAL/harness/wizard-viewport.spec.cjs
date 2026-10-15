const { createRequire } = require('node:module')
const { resolve } = require('node:path')
const { expect, test } = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')
const widths = [320, 390, 768, 960, 1280]
const themes = ['light', 'dark']
const settings = {
  mode: 'fake', model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/api/v1', enabled: false },
  capabilities: {}, credential_status: { deepseek: false, dashscope: false, feishu_app: false }, keychain_available: false,
}

for (const width of widths) for (const theme of themes) test(`wizard no-overflow at ${width}px/${theme}`, async ({ page }, testInfo) => {
  const externalAttempts = []
  const apiCalls = []
  await page.addInitScript((value) => localStorage.setItem('sx:theme-preference', value), theme)
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5176') { externalAttempts.push(url.origin); return route.abort() }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const method = route.request().method()
    const path = url.pathname
    apiCalls.push({ method, path })
    if (path.endsWith('/workspaces/current')) return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: { code: 'workspace_not_open', message: '先打开工作库' } }) })
    if (method === 'POST' && path.endsWith('/workspaces')) return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: 'QA模拟库', root: '/tmp/qa-workspace', local_profile_dir: '/tmp/qa-profile' }) })
    if (path.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) })
    if (path.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ counts: {}, limits: {}, remaining: {} }) })
    if (path.endsWith('/integrations/feishu/status')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }) })
    if (path.endsWith('/intake/items') || path.endsWith('/drafts') || path.endsWith('/actions') || path.endsWith('/lines') || path.endsWith('/projects') || path.endsWith('/pages')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/')
  await expect(page.getByLabel('文件夹路径')).toBeVisible()
  const measurements = []
  async function measure(step) {
    const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
    measurements.push({ step, ...metrics })
    expect(metrics.document, `${step} document overflow at ${width}/${theme}`).toBe(metrics.viewport)
    expect(metrics.body, `${step} body overflow at ${width}/${theme}`).toBe(metrics.viewport)
  }
  await measure('step-1-workspace')
  await page.getByLabel('工作库名称').fill('QA模拟库')
  await page.getByLabel('文件夹路径').fill('/tmp/qa-workspace')
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  await expect(page.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
  await measure('step-2-model-and-secrets')
  expect(await page.locator('#wizard-secret-deepseek').getAttribute('type')).toBe('password')
  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 3 步 · 检查连接' })).toBeVisible()
  await measure('step-3-check')
  await page.getByRole('button', { name: '下一步' }).click()
  await expect(page.getByRole('heading', { name: '第 4 步 · 飞书' })).toBeVisible()
  await measure('step-4-feishu')
  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  await measure('step-5-complete')
  expect(apiCalls.filter((call) => call.method === 'POST' && call.path.includes('/provider-smoke/'))).toHaveLength(0)
  expect(externalAttempts).toEqual([])
  await testInfo.attach(`measurements-${width}-${theme}.json`, { body: JSON.stringify(measurements, null, 2), contentType: 'application/json' })
})

test('secret input is password-only, never persisted, and clears when the wizard exits', async ({ page }) => {
  const secret = 'QA-SECRET-CANARY-DO-NOT-PERSIST'
  const apiBodies = []
  const externalAttempts = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5176') { externalAttempts.push(url.origin); return route.abort() }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const method = route.request().method()
    const path = url.pathname
    apiBodies.push(route.request().postData() ?? '')
    if (path.endsWith('/workspaces/current')) return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: { code: 'workspace_not_open', message: '先打开工作库' } }) })
    if (method === 'POST' && path.endsWith('/workspaces')) return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: 'QA模拟库', root: '/tmp/qa-workspace', local_profile_dir: '/tmp/qa-profile' }) })
    if (path.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) })
    if (path.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ counts: {}, limits: {}, remaining: {} }) })
    if (path.endsWith('/integrations/feishu/status')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }) })
    if (path.endsWith('/intake/items') || path.endsWith('/drafts') || path.endsWith('/actions') || path.endsWith('/lines') || path.endsWith('/projects') || path.endsWith('/pages')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.goto('/')
  await page.getByLabel('工作库名称').fill('QA模拟库')
  await page.getByLabel('文件夹路径').fill('/tmp/qa-workspace')
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  const secretInput = page.locator('#wizard-secret-deepseek')
  await page.getByRole('checkbox', { name: /整理与问答/ }).check()
  const saveButton = page.getByRole('button', { name: '保存密钥并继续' })
  expect(await saveButton.isEnabled()).toBe(true)
  expect(await saveButton.getAttribute('title')).toBeNull()
  await saveButton.click()
  await expect(page.getByRole('alert')).toContainText('所选模型能力需要先配置对应密钥')
  await secretInput.fill(secret)
  expect(await secretInput.getAttribute('type')).toBe('password')
  await saveButton.click()
  await expect(page.getByRole('alert')).toContainText('无法访问 macOS 钥匙串')
  expect(apiBodies.some((body) => body.includes('settings'))).toBe(false)
  const storedBeforeExit = await page.evaluate(() => JSON.stringify({ local: Object.values(localStorage), session: Object.values(sessionStorage) }))
  expect(storedBeforeExit).not.toContain(secret)
  await page.getByRole('button', { name: '关闭向导' }).click()
  expect(apiBodies.join('\n')).not.toContain(secret)
  await page.getByRole('button', { name: '设置' }).click()
  await page.getByRole('button', { name: '打开连接向导' }).click()
  await expect(page.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await expect(page.locator('#wizard-secret-deepseek')).toHaveValue('')
  expect(externalAttempts).toEqual([])
})

test('connecting, no-workspace, and unreachable are distinct first-screen states', async ({ page }) => {
  let resolveCurrent
  await page.route('**/api/v1/workspaces/current', async (route) => {
    await new Promise((resolve) => { resolveCurrent = resolve })
    return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: { code: 'workspace_not_open', message: '先打开工作库' } }) })
  })
  await page.goto('/')
  await expect(page.getByRole('status')).toContainText('正在连接本机服务')
  expect(await page.getByLabel('文件夹路径').count()).toBe(0)
  resolveCurrent()
  await expect(page.getByLabel('文件夹路径')).toBeVisible()
  await page.unrouteAll()
  await page.route('**/api/v1/workspaces/current', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'service_unavailable', message: '模拟服务不可达' } }) }))
  await page.reload()
  await expect(page.getByRole('heading', { name: '没有连上本机服务' })).toBeVisible()
  expect(await page.getByLabel('文件夹路径').count()).toBe(0)
})
