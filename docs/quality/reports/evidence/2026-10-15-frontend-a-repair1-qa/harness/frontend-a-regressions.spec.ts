import { resolve } from 'node:path'
import { createRequire } from 'node:module'

const { expect, test } = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')

const workspace = {
  workspace_id: 'synthetic-workspace',
  name: 'QA 合成工作库',
  root: '/tmp/summit-qa-synthetic-workspace',
  local_profile_dir: '/tmp/summit-qa-synthetic-profile',
  read_only: false,
}

function settings(overrides: Record<string, unknown> = {}) {
  return {
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
    ...overrides,
  }
}

const smoke = { counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 } }
const emptySettings = settings({
  mode: 'fake',
  llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/api/v1', enabled: false },
  capabilities: {},
  credential_status: { feishu_app: false, deepseek: false, dashscope: false },
  keychain_available: false,
})
const llmOnlyWithSavedCredential = settings({
  mode: 'real',
  llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'synthetic-account', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://synthetic.invalid/api/v1', enabled: false },
  capabilities: { llm: { available: false, configured: true, disabled_reason: 'acceptance_plan_required' } },
  credential_status: { feishu_app: false, deepseek: true, dashscope: false },
  keychain_available: false,
})

async function routeApp(page: any, options: { initialSettings?: any; noWorkspace?: boolean; feishu?: (read: number) => any; smokeResult?: (path: string, count: number) => any }) {
  const calls: { method: string; path: string; body: string }[] = []
  const externalAttempts: string[] = []
  let currentSettings = options.initialSettings ?? settings()
  let feishuReads = 0
  const smokePosts: Record<string, number> = {}
  await page.route('**/*', async (route: any) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5175') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const method = route.request().method()
    const path = url.pathname
    const body = route.request().postData() ?? ''
    calls.push({ method, path, body })
    if (method === 'GET' && path.endsWith('/workspaces/current')) {
      return options.noWorkspace
        ? route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: { code: 'workspace_not_open', message: '先打开工作库' } }) })
        : route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(workspace) })
    }
    if (method === 'POST' && path.endsWith('/workspaces')) return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(workspace) })
    if (method === 'GET' && path.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentSettings) })
    if (method === 'PATCH' && path.endsWith('/settings')) {
      const patch = JSON.parse(body)
      currentSettings = { ...currentSettings, ...patch, ...(patch.rerank ? { rerank: { ...currentSettings.rerank, ...patch.rerank } } : {}) }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(currentSettings) })
    }
    if (method === 'GET' && path.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smoke) })
    if (method === 'GET' && path.endsWith('/integrations/feishu/status')) {
      feishuReads += 1
      const answer = options.feishu?.(feishuReads) ?? { status: 200, body: { mode: 'real', authorized: false, app_configured: true, user_identity_verified: false } }
      return route.fulfill({ status: answer.status, contentType: 'application/json', body: typeof answer.body === 'string' ? answer.body : JSON.stringify(answer.body) })
    }
    if (method === 'POST' && path.includes('/provider-smoke/')) {
      const checkPath = path.split('/').at(-1) ?? ''
      smokePosts[checkPath] = (smokePosts[checkPath] ?? 0) + 1
      const answer = options.smokeResult?.(checkPath, smokePosts[checkPath]) ?? { status: 200, body: {} }
      return route.fulfill({ status: answer.status, contentType: 'application/json', body: JSON.stringify(answer.body) })
    }
    if (method === 'DELETE' && path.endsWith('/credentials/feishu_app')) {
      currentSettings = { ...currentSettings, credential_status: { ...currentSettings.credential_status, feishu_app: false } }
      return route.fulfill({ status: 204, body: '' })
    }
    if (path.endsWith('/intake/items') || path.endsWith('/drafts') || path.endsWith('/actions') || path.endsWith('/lines') || path.endsWith('/projects') || path.endsWith('/pages')) return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  return { calls, externalAttempts, smokePosts, getFeishuReads: () => feishuReads }
}

test('F1 required credential blocks submission with field guidance; existing credential is reusable and unavailable Keychain fails closed', async ({ page }: any) => {
  const observed = await routeApp(page, { noWorkspace: true, initialSettings: emptySettings })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await expect(page.getByLabel('文件夹路径')).toBeVisible()
  await page.getByLabel('工作库名称').fill('QA 合成工作库')
  await page.getByLabel('文件夹路径').fill('/tmp/summit-qa-synthetic-workspace')
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  await expect(page.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await page.getByRole('checkbox', { name: /整理与问答/ }).check()
  const save = page.getByRole('button', { name: '保存密钥并继续' })
  await expect(save).toBeDisabled()
  await expect(save).toHaveAttribute('title', /DeepSeek API Key/)
  await expect(page.locator('#wizard-secret-deepseek')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.locator('#wizard-secret-deepseek-guidance')).toContainText('需要填写 DeepSeek API Key')
  expect(observed.calls.filter((call) => call.method === 'PATCH' || call.method === 'PUT')).toHaveLength(0)
  const canary = '<SYNTHETIC_SECRET_CANARY>'
  await page.locator('#wizard-secret-deepseek').fill(canary)
  await expect(save).toBeDisabled()
  await expect(save).toHaveAttribute('title', /钥匙串/)
  expect(observed.calls.filter((call) => call.method === 'PATCH' || call.method === 'PUT')).toHaveLength(0)
  expect(observed.calls.map((call) => call.body).join('\n')).not.toContain(canary)
  expect(await page.evaluate((value: string) => JSON.stringify({ local: Object.values(localStorage), session: Object.values(sessionStorage) }).includes(value), canary)).toBe(false)
  await page.getByRole('button', { name: '关闭向导' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  expect(observed.externalAttempts).toEqual([])

  const other = await page.context().newPage()
  const savedObserved = await routeApp(other, { noWorkspace: true, initialSettings: llmOnlyWithSavedCredential })
  await other.goto('/')
  await other.getByLabel('工作库名称').fill('QA 合成工作库')
  await other.getByLabel('文件夹路径').fill('/tmp/summit-qa-synthetic-workspace')
  await other.getByRole('button', { name: '创建本地工作库' }).click()
  await expect(other.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await expect(other.getByRole('checkbox', { name: /整理与问答/ })).toBeChecked()
  const savedCredentialButton = other.getByRole('button', { name: '保存密钥并继续' })
  await expect(savedCredentialButton).toBeEnabled()
  await expect(other.locator('#wizard-secret-deepseek')).toHaveValue('')
  await savedCredentialButton.click()
  await expect(other.getByRole('heading', { name: '第 3 步 · 检查连接' })).toBeVisible()
  expect(savedObserved.calls.filter((call) => call.method === 'PUT')).toHaveLength(0)
  expect(savedObserved.externalAttempts).toEqual([])
  expect(observed.externalAttempts).toEqual([])
})

test('F2 per-capability failures remain visible after another check succeeds; changed config expires only its old result', async ({ page }: any) => {
  const observed = await routeApp(page, {
    smokeResult: (path) => path === 'model-studio-rerank'
      ? { status: 502, body: { error: { code: 'synthetic_rerank_failure', message: 'QA 合成失败' } } }
      : { status: 200, body: { outcome: 'synthetic-success' } },
  })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: '设置' }).click()
  const ai = page.getByRole('region', { name: 'AI 模型' })
  await page.locator('details.settings-advanced-block > summary').click()
  const rerank = page.getByRole('button', { name: /Rerank（剩余 1）/ })
  await rerank.click()
  const smokeDialog = page.getByRole('dialog', { name: /确认本次连接检查：Rerank/ })
  await expect(smokeDialog).toHaveAttribute('aria-modal', 'true')
  await expect(smokeDialog.getByRole('button', { name: '取消' })).toBeFocused()
  await smokeDialog.getByRole('button', { name: '取消' }).click()
  expect(Object.values(observed.smokePosts)).toEqual([])
  await rerank.click()
  await page.getByRole('dialog').getByRole('button', { name: '确认发送本次检查' }).dblclick()
  await expect(ai.getByText('有检查失败', { exact: true })).toBeVisible()
  await expect(ai.locator('.settings-capability-item').filter({ hasText: '检索结果排序' })).toContainText('本次检查失败')
  await page.getByRole('button', { name: /DeepSeek Chat（剩余 1）/ }).click()
  await page.getByRole('dialog').getByRole('button', { name: '确认发送本次检查' }).click()
  await expect(ai.getByText('有检查失败', { exact: true })).toBeVisible()
  await expect(ai.locator('.settings-capability-item').filter({ hasText: '整理与问答模型' })).toContainText('本次合成检查通过')
  await expect(ai.locator('.settings-capability-item').filter({ hasText: '检索结果排序' })).toContainText('本次检查失败')
  expect(await ai.getByText('三项检查通过', { exact: true }).count()).toBe(0)
  expect(observed.smokePosts['model-studio-rerank']).toBe(1)
  expect(observed.smokePosts['deepseek-chat']).toBe(1)

  await page.locator('label.settings-field').filter({ hasText: 'Rerank API Base URL' }).locator('input').fill('https://qa-sentinel.invalid/api/v1')
  await page.getByRole('button', { name: '保存 provider 设置' }).click()
  await expect(page.locator('p.settings-notice')).toContainText('高级设置已保存在本机')
  await expect(ai.getByText('部分已检查', { exact: true })).toBeVisible()
  await expect(ai.locator('.settings-capability-item').filter({ hasText: '检索结果排序' })).toContainText('已配置，待本次确认')
  await expect(ai.locator('.settings-capability-item').filter({ hasText: '整理与问答模型' })).toContainText('本次合成检查通过')
  const pageText = await page.locator('body').innerText()
  expect(pageText).not.toContain('qa-sentinel.invalid')
  const dom = await page.locator('body').evaluate((el: HTMLElement) => el.outerHTML)
  expect(dom).not.toContain('configStamp')
  expect(observed.externalAttempts).toEqual([])
})

test('F3 Feishu read failure retains last success time/value and confirmed credential deletion invalidates it', async ({ page }: any) => {
  let failFeishu = false
  const observed = await routeApp(page, {
    feishu: () => !failFeishu
      ? { status: 200, body: { mode: 'real', authorized: true, app_configured: true, user_identity_verified: false } }
      : { status: 503, body: { error: { code: 'synthetic_unavailable', message: 'QA 合成读取失败' } } },
  })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: '设置' }).click()
  const feishu = page.getByRole('region', { name: '飞书' })
  await expect(feishu.locator('.conn-badge').getByText('已授权', { exact: true })).toBeVisible()
  await page.locator('details.settings-advanced-block > summary').click()
  failFeishu = true
  await page.getByRole('button', { name: '重新读取授权状态' }).click()
  await expect(feishu.getByRole('alert')).toContainText('本次读取失败')
  await expect(feishu.getByRole('alert')).toContainText('可能已过时')
  await expect(feishu.getByRole('alert')).toContainText('成功读取于')
  await expect(feishu.locator('.conn-badge').getByText('已授权', { exact: true })).toBeVisible()
  await expect(feishu.getByRole('button', { name: '重试读取' })).toBeVisible()

  await page.getByRole('button', { name: '删除飞书应用密钥' }).click()
  const dialog = page.getByRole('dialog', { name: '删除所选本机密钥？' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveAttribute('aria-modal', 'true')
  const cancel = dialog.getByRole('button', { name: '取消' })
  const confirm = dialog.getByRole('button', { name: '删除密钥' })
  await expect(cancel).toBeFocused()
  expect(observed.calls.filter((call) => call.method === 'DELETE')).toHaveLength(0)
  await cancel.press('Shift+Tab')
  await expect(confirm).toBeFocused()
  await confirm.press('Tab')
  await expect(cancel).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.getByRole('button', { name: '删除飞书应用密钥' })).toBeFocused()
  expect(observed.calls.filter((call) => call.method === 'DELETE')).toHaveLength(0)
  await page.getByRole('button', { name: '删除飞书应用密钥' }).click()
  await page.getByRole('dialog', { name: '删除所选本机密钥？' }).getByRole('button', { name: '删除密钥' }).dblclick()
  await expect(page.locator('p.settings-notice')).toContainText('已从本机钥匙串删除')
  await expect(feishu.locator('.conn-badge').getByText('未配置', { exact: true })).toBeVisible()
  expect(await feishu.locator('.conn-badge').getByText('已授权', { exact: true }).count()).toBe(0)
  expect(observed.calls.filter((call) => call.method === 'DELETE' && call.path.endsWith('/credentials/feishu_app'))).toHaveLength(1)
  expect(observed.externalAttempts).toEqual([])
})
