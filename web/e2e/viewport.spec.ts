import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Locator } from '@playwright/test'

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

async function expectDialogWithinViewport(dialog: Locator) {
  const layout = await dialog.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    return {
      backdropPosition: getComputedStyle(element.parentElement!).position,
      rect: { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right },
      viewport: { width: innerWidth, height: innerHeight },
    }
  })
  expect(layout.backdropPosition).toBe('fixed')
  expect(layout.rect.top).toBeGreaterThanOrEqual(0)
  expect(layout.rect.bottom).toBeLessThanOrEqual(layout.viewport.height)
  expect(layout.rect.left).toBeGreaterThanOrEqual(0)
  expect(layout.rect.right).toBeLessThanOrEqual(layout.viewport.width)
}

test('offline viewport and theme baseline for today, approvals, tools and settings', async ({ page }, testInfo) => {
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
    else if (url.pathname.endsWith('/index/status')) body = { fingerprint: 'synthetic-fingerprint', pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 }
    else if (url.pathname.endsWith('/action-intents')) body = { items: [], next_cursor: null }
    else if (url.pathname.endsWith('/provider-smoke')) {
      body = { counts: {}, limits: {}, remaining: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 } }
    } else if (url.pathname.endsWith('/integrations/feishu/status')) {
      body = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  const evidenceDir = resolve(process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-b/viewport')
  mkdirSync(evidenceDir, { recursive: true })
  const emptyFolderPath = resolve(evidenceDir, 'empty-folder')
  mkdirSync(emptyFolderPath, { recursive: true })
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
      expect(todayMetrics.document, `today horizontal overflow at ${width}px/${theme}`).toBe(todayMetrics.viewport)
      expect(todayMetrics.body, `today body overflow at ${width}px/${theme}`).toBe(todayMetrics.viewport)
      await page.screenshot({ path: resolve(evidenceDir, `today-${width}-${theme}.png`), fullPage: true })

      const todaySections = page.locator('.today-stack > section')
      await expect(todaySections.nth(0).getByRole('heading', { name: '会议' })).toBeVisible()
      await expect(todaySections.nth(1).getByRole('heading', { name: '待办任务' })).toBeVisible()
      await expect(page.locator('.today-tools button')).toHaveCount(2)
      {
        const importTrigger = page.getByRole('button', { name: '导入会议' })
        await importTrigger.click()
        const importDialog = page.getByRole('dialog', { name: '导入会议与材料' })
        await expect(importDialog).toBeVisible()
        await expect(importDialog).toContainText('选择本机文件')
        expect(await importDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
        await expectDialogWithinViewport(importDialog)
        await page.keyboard.press('Tab')
        const filesInput = importDialog.locator('input[type="file"]').nth(0)
        await expect(filesInput).toBeFocused()
        const filesLabel = filesInput.locator('..')
        await expect(filesLabel).toHaveCSS('outline-style', 'solid')
        await page.screenshot({ path: resolve(evidenceDir, `import-focus-files-${width}-${theme}.png`) })
        const filesChooserPromise = page.waitForEvent('filechooser')
        await page.keyboard.press('Enter')
        const filesChooser = await filesChooserPromise
        expect(filesChooser.isMultiple()).toBe(true)
        await filesChooser.setFiles([])
        await page.keyboard.press('Tab')
        const folderInput = importDialog.locator('input[type="file"]').nth(1)
        await expect(folderInput).toBeFocused()
        const folderLabel = folderInput.locator('..')
        await expect(folderLabel).toHaveCSS('outline-style', 'solid')
        const folderChooserPromise = page.waitForEvent('filechooser')
        await page.keyboard.press('Space')
        const folderChooser = await folderChooserPromise
        expect(folderChooser.isMultiple()).toBe(true)
        await folderChooser.setFiles(emptyFolderPath)
        await page.screenshot({ path: resolve(evidenceDir, `import-drawer-${width}-${theme}.png`) })
        await page.keyboard.press('Shift+Tab')
        expect(await importDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
        await page.keyboard.press('Escape')
        await expect(importDialog).toHaveCount(0)
        await expect(importTrigger).toBeFocused()
        await page.getByRole('button', { name: '工作日志 / 思考' }).click()
        const journalDialog = page.getByRole('dialog', { name: '工作日志与思考' })
        await expect(journalDialog).toBeVisible()
        await expectDialogWithinViewport(journalDialog)
        expect(await journalDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
        await page.screenshot({ path: resolve(evidenceDir, `journal-dialog-${width}-${theme}.png`) })
        await page.keyboard.press('Escape')
        await expect(journalDialog).toHaveCount(0)
        await expect(page.getByRole('button', { name: '工作日志 / 思考' })).toBeFocused()
      }

      await page.getByRole('button', { name: '审批' }).click()
      await expect(page.getByRole('heading', { name: '审批' })).toBeVisible()
      for (const heading of ['1 · 来源', '2 · 稿件', '3 · 正式内容', '4 · 索引', '5 · 外部动作']) await expect(page.getByRole('heading', { name: heading })).toBeVisible()
      {
        const indexGroup = page.getByRole('region', { name: /4 · 索引/ })
        await indexGroup.getByRole('checkbox', { name: '选择索引事项进行检查' }).check()
        const summaryTrigger = page.getByRole('button', { name: /检查并应用/ })
        await summaryTrigger.click()
        const summaryDialog = page.getByRole('dialog', { name: '检查所选事项' })
        await expect(summaryDialog).toBeVisible()
        expect(await summaryDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
        await expectDialogWithinViewport(summaryDialog)
        await page.screenshot({ path: resolve(evidenceDir, `approval-selection-summary-${width}-${theme}.png`) })
        await page.keyboard.press('Escape')
        await expect(summaryDialog).toHaveCount(0)
        await expect(summaryTrigger).toBeFocused()
      }
      const approvalMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
      expect(approvalMetrics.document, `approval horizontal overflow at ${width}px/${theme}`).toBe(approvalMetrics.viewport)
      expect(approvalMetrics.body, `approval body overflow at ${width}px/${theme}`).toBe(approvalMetrics.viewport)
      await page.screenshot({ path: resolve(evidenceDir, `approval-${width}-${theme}.png`), fullPage: true })
      await page.getByRole('button', { name: '今日' }).click()

      await page.getByRole('button', { name: '设置' }).click()
      await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
      await expect(page.getByRole('region', { name: '工作库' })).toBeVisible()
      await expect(page.getByRole('button', { name: '配置 AI 模型与密钥' })).toBeVisible()
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
      expect(settingsMetrics.document, `settings horizontal overflow at ${width}px/${theme}`).toBe(settingsMetrics.viewport)
      expect(settingsMetrics.body, `settings body overflow at ${width}px/${theme}`).toBe(settingsMetrics.viewport)
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
