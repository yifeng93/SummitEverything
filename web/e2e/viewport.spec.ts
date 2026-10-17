import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Locator } from '@playwright/test'

const viewports = [320, 390, 768, 960, 1024, 1280, 1440]
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
  test.setTimeout(180_000)
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
    } else if (url.pathname.endsWith('/first-use/progress') && route.request().method() === 'GET') {
      body = { step: 2, completed: true, open: false }
    } else if (url.pathname.endsWith('/first-use/progress') && route.request().method() === 'PUT') {
      body = route.request().postDataJSON()
    } else if (url.pathname.endsWith('/settings')) body = settings
    else if (url.pathname.endsWith('/index/status')) body = { fingerprint: 'synthetic-fingerprint', pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 }
    else if (url.pathname.endsWith('/intake/items')) body = [{ item_id: 'synthetic-source-item', source_id: 'synthetic-source', origin_kind: 'quick_note', title: '合成会议记录', filename: '合成记录.md', created_at: '2026-10-16T09:00:00+08:00', state: 'pending', attempt_no: 0, revision: 0 }]
    else if (url.pathname.endsWith('/sources/synthetic-source')) body = { source: { source_id: 'synthetic-source', filename: '合成记录.md', origin_kind: 'quick_note' }, text: '合成原文：周五前确认会议安排。' }
    else if (url.pathname.endsWith('/drafts')) body = [{ draft_id: 'synthetic-draft', input_ids: [], target_page_id: null, metadata: { id: 'synthetic-draft', title: '合成待审核稿', role: 'knowledge', kind: 'topic', line_id: 'synthetic-line', project_id: 'synthetic-project' }, body: '# 合成审核正文\n\n会议安排需要再次核对。', expected_base_sha256: null, important_conflicts: [{ id: 'date', question: '会议日期是否已确认？', alternatives: ['已确认', '仍待确认'] }], action_suggestions: [], conflict_resolutions: {}, source_ids: ['synthetic-source'], state: 'pending', created_at: '2026-10-16T09:00:00+08:00', version: 1 }]
    else if (url.pathname.endsWith('/pages')) body = [{ page_id: 'synthetic-page', relative_path: '合成项目/合成页.md', metadata: { id: 'synthetic-page', title: '合成正式页', role: 'knowledge', kind: 'meeting', line_id: 'synthetic-line', project_id: 'synthetic-project' }, body: '合成正式正文。', content_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'pending', validity: 'current' }]
    else if (url.pathname.endsWith('/lines')) body = [{ id: 'synthetic-line', name: '合成主线', directory: 'lines/synthetic' }]
    else if (url.pathname.endsWith('/projects')) body = [{ id: 'synthetic-project', line_id: 'synthetic-line', name: '合成项目', directory: 'projects/synthetic', overview_id: 'synthetic-overview', archived: false, progress: '', progress_version: 0 }]
    else if (url.pathname.endsWith('/integrations/feishu/calendar')) body = { items: Array.from({ length: 4 }, (_, index) => ({ event_id: `synthetic-meeting-${index + 1}`, title: index === 0 ? '合成项目周会' : `合成会议 ${index + 1}`, start: `2026-10-16T${10 + index}:00:00+08:00`, end: `2026-10-16T${10 + index}:30:00+08:00` })), next_cursor: null, truncated: false }
    else if (url.pathname.endsWith('/integrations/feishu/tasks')) body = { items: Array.from({ length: 6 }, (_, index) => ({ guid: `synthetic-task-${index + 1}`, summary: index === 0 ? '核对会议安排' : `合成待办 ${index + 1}`, completed_at: null, due: { timestamp: '2026-10-16T17:00:00+08:00', is_all_day: false } })), next_cursor: null }
    else if (url.pathname.endsWith('/action-intents')) body = { items: [], next_cursor: null }
    else if (url.pathname.endsWith('/provider-smoke')) {
      body = { counts: {}, limits: {}, remaining: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 } }
    } else if (url.pathname.endsWith('/integrations/feishu/status')) {
      body = { mode: 'fake', authorized: true, app_configured: false, user_identity_verified: false }
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

      await page.getByRole('button', { name: '刷新日历' }).click()
      await expect(page.getByText('合成项目周会')).toBeVisible()
      await expect(page.getByText('合成会议 4')).toHaveCount(0)
      await expect(page.getByRole('button', { name: '显示全部日程（4）' })).toBeVisible()
      await page.getByRole('button', { name: '刷新飞书任务' }).click()
      await expect(page.getByText('核对会议安排')).toBeVisible()
      await expect(page.getByText('合成待办 6')).toHaveCount(0)
      await expect(page.getByRole('button', { name: '显示全部待办（6）' })).toBeVisible()
      const todaySections = page.locator('.today-schedule > section')
      await expect(todaySections.nth(0).getByRole('heading', { name: '会议' })).toBeVisible()
      await expect(todaySections.nth(1).getByRole('heading', { name: '待办任务' })).toBeVisible()
      await expect(page.locator('.today-tools button')).toHaveCount(3)
      if (width === 1280 && theme === 'light') {
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.setViewportSize({ width: 1280, height: 800 })
        const firstScreen = await page.evaluate(() => Object.fromEntries([
          '.today-schedule > section:nth-child(1) h2',
          '.today-schedule > section:nth-child(1) li',
          '.today-schedule > section:nth-child(2) h2',
          '.today-schedule > section:nth-child(2) li',
          '#today-quick-note',
          '.today-tools button:nth-child(2)',
        ].map((selector) => {
          const rect = document.querySelector(selector)!.getBoundingClientRect()
          return [selector, { top: Math.round(rect.top), bottom: Math.round(rect.bottom) }]
        })))
        expect(firstScreen['.today-schedule > section:nth-child(1) h2'].top).toBeLessThan(800)
        expect(firstScreen['.today-schedule > section:nth-child(1) li'].bottom).toBeLessThanOrEqual(800)
        expect(firstScreen['.today-schedule > section:nth-child(2) h2'].top).toBeLessThan(800)
        expect(firstScreen['.today-schedule > section:nth-child(2) li'].bottom).toBeLessThanOrEqual(800)
        expect(firstScreen['#today-quick-note'].bottom).toBeLessThanOrEqual(800)
        expect(firstScreen['.today-tools button:nth-child(2)'].bottom).toBeLessThanOrEqual(800)
        await page.screenshot({ path: resolve(evidenceDir, 'today-1280-800-nonempty.png') })
        await page.setViewportSize({ width, height: 900 })
      }
      await page.getByRole('button', { name: '显示全部日程（4）' }).click()
      await expect(page.getByText('合成会议 4')).toBeVisible()
      await page.getByRole('button', { name: '收起日程' }).click()
      await page.getByRole('button', { name: '显示全部待办（6）' }).click()
      await expect(page.getByText('合成待办 6')).toBeVisible()
      await page.getByRole('button', { name: '收起任务' }).click()
      {
        const importTrigger = page.getByRole('button', { name: '导入材料' })
        await importTrigger.click()
        const importDialog = page.getByRole('dialog', { name: '导入材料' })
        await expect(importDialog).toBeVisible()
        await expect(importDialog).toContainText('选择本机文件')
        expect(await importDialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
        await expectDialogWithinViewport(importDialog)
        await page.keyboard.press('Tab')
        await expect(importDialog.getByRole('tab', { name: '本机文件' })).toBeFocused()
        await page.keyboard.press('Tab')
        await expect(importDialog.getByRole('tab', { name: '飞书材料' })).toBeFocused()
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
        const emptyActionsGroup = page.locator('#approval-actions')
        await expect(emptyActionsGroup).not.toHaveAttribute('open', '')
        await emptyActionsGroup.locator('summary').click()
        await expect(emptyActionsGroup).toHaveAttribute('open', '')
        const emptyIndexGroup = page.locator('#approval-index')
        await expect(emptyIndexGroup).not.toHaveAttribute('open', '')
        await emptyIndexGroup.locator('summary').click()
        await expect(emptyIndexGroup).toHaveAttribute('open', '')
        const sourceGroup = page.getByRole('region', { name: /1 · 来源/ })
        await sourceGroup.getByRole('button', { name: '合成会议记录' }).click()
        const sourceFocus = page.getByRole('region', { name: '来源详情：合成会议记录' })
        await expect(sourceFocus.getByText('合成原文：周五前确认会议安排。')).toBeVisible()
        await sourceFocus.getByRole('button', { name: '返回审批清单' }).click()
        const draftGroup = page.getByRole('region', { name: /2 · 稿件/ })
        await draftGroup.getByRole('button', { name: '打开稿件：合成待审核稿' }).click()
        const draftFocus = page.getByRole('region', { name: '稿件审核：合成待审核稿' })
        await expect(draftFocus.getByText('会议安排需要再次核对。', { exact: true })).toBeVisible()
        await expect(draftFocus.getByText('会议日期是否已确认？')).toBeVisible()
        await expect(draftFocus.locator('.draft-edit-details')).not.toHaveAttribute('open', '')
        await draftFocus.getByRole('button', { name: '返回审批清单' }).click()
        await expect(emptyActionsGroup).toHaveAttribute('open', '')
        await expect(emptyIndexGroup).toHaveAttribute('open', '')
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
  // This is a 640 CSS-pixel reflow check only; it does not simulate browser zoom.
  await page.setViewportSize({ width: 640, height: 450 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const theme of ['light', 'dark'] as const) {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
    await page.getByRole('combobox', { name: '主题' }).selectOption(theme)
    for (const [label, selector] of [['今日', '.today-view'], ['审批', '.approval-view'], ['设置', '.settings-view']] as const) {
      if (label !== '今日') await page.getByRole('button', { name: label }).click()
      const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
      expect(metrics.document, `${label} 640px viewport overflow/${theme}`).toBe(metrics.viewport)
      expect(metrics.body, `${label} 640px viewport body overflow/${theme}`).toBe(metrics.viewport)
      expect(await page.locator(selector).count()).toBe(1)
      await page.screenshot({ path: resolve(evidenceDir, `${label}-effective-640-${theme}.png`), fullPage: true })
    }
    const motion = await page.evaluate(() => ({
      reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
      transition: getComputedStyle(document.querySelector('.nav-item')!).transitionDuration,
      scroll: getComputedStyle(document.documentElement).scrollBehavior,
    }))
    expect(motion.reduced).toBe(true)
    expect(motion.scroll).toBe('auto')
    expect(motion.transition.split(',').every((value) => Number.parseFloat(value) <= 0.00001)).toBe(true)
    await page.screenshot({ path: resolve(evidenceDir, `reduced-motion-${theme}.png`), fullPage: true })
  }
  writeFileSync(resolve(evidenceDir, 'measurements.json'), JSON.stringify(measurements, null, 2))
  expect(externalAttempts).toEqual([])
})
