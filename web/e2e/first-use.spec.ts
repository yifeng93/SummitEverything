import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const settings = {
  mode: 'fake', model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
  capabilities: {}, credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: false,
  embedding_fingerprint: 'synthetic-fingerprint',
}

test('first use stays in one app-owned flow and resumes to a requested step', async ({ page }) => {
  const externalAttempts: string[] = []
  const apiCalls: string[] = []
  let workspaceOpened = false
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5173') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    const method = route.request().method()
    apiCalls.push(`${method} ${url.pathname}`)
    if (url.pathname.endsWith('/workspaces/current')) {
      return workspaceOpened
        ? route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }) })
        : route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: { code: 'workspace_not_open', message: '先打开工作库' } }) })
    }
    if (method === 'POST' && url.pathname.endsWith('/workspaces')) {
      if (route.request().postDataJSON()?.root === '/tmp/unwritable-workspace') {
        return route.fulfill({ status: 422, contentType: 'application/json', body: JSON.stringify({ error: { code: 'validation_error', message: '无法创建工作库，请选择可写的空文件夹。' } }) })
      }
      workspaceOpened = true
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }) })
    }
    if (url.pathname.endsWith('/settings')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) })
    if (url.pathname.endsWith('/provider-smoke')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ counts: {}, limits: {}, remaining: {} }) })
    if (url.pathname.endsWith('/integrations/feishu/status')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }) })
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByText('首次配置 · 第 1 步，共 5 步')).toBeVisible()
  await page.getByLabel('工作库名称').fill('模拟工作库')
  await page.getByLabel('文件夹路径').fill('/tmp/unwritable-workspace')
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  await expect(page.getByRole('alert')).toContainText('无法创建工作库，请选择可写的空文件夹。')
  const evidenceDir = resolve(process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-a/current')
  mkdirSync(evidenceDir, { recursive: true })
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-workspace-error.png'), fullPage: true })

  await page.getByLabel('文件夹路径').fill('/tmp/synthetic-workspace')
  await page.getByRole('button', { name: '创建本地工作库' }).click()

  await expect(page.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '设置' })).toHaveCount(0)
  await expect(page.getByRole('checkbox', { name: /整理与问答/ })).not.toBeChecked()
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-2.png'), fullPage: true })

  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 3 步 · 检查连接' })).toBeVisible()
  expect(apiCalls.some((call) => call.includes('/provider-smoke/'))).toBe(false)
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-3.png'), fullPage: true })

  await page.reload()
  await expect(page.getByRole('heading', { name: '第 3 步 · 检查连接' })).toBeVisible()
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-3-reloaded-open.png'), fullPage: true })
  await page.getByRole('button', { name: '关闭向导' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  await page.getByRole('button', { name: '设置' }).click()
  await expect(page.getByRole('button', { name: '打开连接向导' })).toBeVisible()
  await page.getByRole('button', { name: '打开连接向导' }).click()
  await expect(page.getByRole('heading', { name: '第 3 步 · 检查连接' })).toBeVisible()
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-3-manual-resume.png'), fullPage: true })
  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 4 步 · 飞书' })).toBeVisible()
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-4.png'), fullPage: true })
  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-step-5.png'), fullPage: true })
  await page.getByRole('button', { name: '完成并进入今日' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  await expect(page.getByRole('heading', { name: /首次配置/ })).toHaveCount(0)

  await page.getByRole('button', { name: '设置' }).click()
  await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
  await expect(page.getByRole('dialog', { name: '首次配置向导' })).toHaveCount(0)
  const progress = await page.evaluate(() => Object.entries(localStorage).map(([key, value]) => [key, value]))
  expect(JSON.stringify(progress)).not.toContain('synthetic-secret')

  await page.getByRole('button', { name: '连接 / 重新授权飞书' }).click()
  await expect(page.getByRole('heading', { name: '第 4 步 · 飞书' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '设置' })).toHaveCount(0)
  await page.screenshot({ path: resolve(evidenceDir, 'onboarding-reauthorize-step-4.png'), fullPage: true })
  await page.getByRole('button', { name: '关闭向导' }).click()
  await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
  expect(externalAttempts).toEqual([])
})
