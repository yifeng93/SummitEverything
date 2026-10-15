import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const viewports = [320, 390, 768, 960, 1280]
const settings = {
  mode: 'fake',
  model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
  capabilities: {},
  credential_status: { feishu_app: false, deepseek: false, dashscope: false },
  keychain_available: false,
  embedding_fingerprint: 'synthetic-fingerprint',
}

test('offline viewport and theme baseline for today and settings', async ({ page }, testInfo) => {
  const apiCalls: string[] = []
  const externalAttempts: string[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5173') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    apiCalls.push(`${route.request().method()} ${url.pathname}`)
    let body: unknown = []
    if (url.pathname.endsWith('/workspaces/current')) {
      body = { workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }
    } else if (url.pathname.endsWith('/settings')) body = settings
    else if (url.pathname.endsWith('/provider-smoke')) {
      body = { counts: {}, limits: {}, remaining: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 } }
    } else if (url.pathname.endsWith('/integrations/feishu/status')) {
      body = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  const evidenceDir = resolve(process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-a/baseline')
  mkdirSync(evidenceDir, { recursive: true })
  const measurements: unknown[] = []
  for (const width of viewports) {
    await page.setViewportSize({ width, height: 900 })
    for (const theme of ['light', 'dark'] as const) {
      await page.goto('/')
      await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
      await page.getByRole('combobox', { name: '主题' }).selectOption(theme)
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      const todayMetrics = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }))
      await page.screenshot({ path: resolve(evidenceDir, `today-${width}-${theme}.png`), fullPage: true })

      await page.getByRole('button', { name: '设置' }).click()
      await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
      await expect(page.getByRole('region', { name: '工作库' })).toBeVisible()
      const settingsMetrics = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
        overflow: [...document.querySelectorAll<HTMLElement>('*')]
          .map((element) => ({ selector: `${element.tagName.toLowerCase()}${element.className && typeof element.className === 'string' ? `.${element.className.trim().replace(/\s+/g, '.')}` : ''}`, right: Math.round(element.getBoundingClientRect().right) }))
          .filter((element) => element.right > document.documentElement.clientWidth + 1)
          .slice(0, 12),
        layout: ['.app-frame', '.main-shell', '.main-content', '.content-wrap', '.settings-cards', '.settings-card'].map((selector) => {
          const element = document.querySelector<HTMLElement>(selector)
          const rect = element?.getBoundingClientRect()
          return { selector, width: rect && Math.round(rect.width), left: rect && Math.round(rect.left), right: rect && Math.round(rect.right), scrollWidth: element?.scrollWidth }
        }),
      }))
      console.log(JSON.stringify({ width, theme, todayMetrics, settingsMetrics }))
      measurements.push({ width, theme, today: todayMetrics, settings: settingsMetrics, apiCalls: apiCalls.slice() })
      await page.screenshot({ path: resolve(evidenceDir, `settings-${width}-${theme}.png`), fullPage: true })
      await testInfo.attach(`measure-${width}-${theme}`, {
        body: JSON.stringify({ today: todayMetrics, settings: settingsMetrics, apiCalls: apiCalls.slice() }, null, 2),
        contentType: 'application/json',
      })
    }
  }
  writeFileSync(resolve(evidenceDir, 'measurements.json'), JSON.stringify(measurements, null, 2))
  expect(externalAttempts).toEqual([])
})
