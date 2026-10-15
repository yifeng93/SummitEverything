import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const lineId = '11111111-1111-4111-8111-111111111111'
const projectId = '22222222-2222-4222-8222-222222222222'
const pageId = '33333333-3333-4333-8333-333333333333'
const hash = 'a'.repeat(64)
const line = { id: lineId, name: '模拟主线', directory: '模拟主线' }
const project = { id: projectId, line_id: lineId, name: '模拟测试项目', directory: '模拟主线/模拟测试项目', overview_id: null, archived: false, progress: '已完成首次访谈', progress_version: 1 }
const pageRecord = {
  page_id: pageId,
  relative_path: '模拟主线/模拟测试项目/会议记录.md',
  metadata: { id: pageId, title: '合成会议记录', role: 'knowledge', kind: 'meeting', line_id: lineId, project_id: projectId },
  body: '## 会议地点\n会议在北馆举行。\n\n[[未知页面]]',
  content_sha256: hash,
  raw_sha256: 'b'.repeat(64),
  storage_area: 'formal',
  approval_state: 'confirmed',
  validity: 'current',
}
const settings = {
  mode: 'fake', model_studio_account_id: 'synthetic-account',
  feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
  rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
  capabilities: {}, credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: false, embedding_fingerprint: 'synthetic-fingerprint',
}

test('C project, reader and question-first views fit required widths and themes', async ({ page }) => {
  const externalAttempts: string[] = []
  const apiCalls: string[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5191') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    apiCalls.push(`${route.request().method()} ${url.pathname}`)
    let body: unknown = []
    if (url.pathname.endsWith('/workspaces/current')) body = { workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }
    else if (url.pathname.endsWith('/settings')) body = settings
    else if (url.pathname.endsWith('/lines')) body = [line]
    else if (url.pathname.endsWith('/projects')) body = [project]
    else if (url.pathname.endsWith('/pages')) body = [pageRecord]
    else if (url.pathname.endsWith(`/pages/${pageId}`)) body = pageRecord
    else if (url.pathname.endsWith('/index/status')) body = { fingerprint: 'synthetic-fingerprint', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 }
    else if (url.pathname.endsWith('/action-intents')) body = { items: [], next_cursor: null }
    else if (url.pathname.endsWith('/provider-smoke')) body = { counts: {}, limits: {}, remaining: {} }
    else if (url.pathname.endsWith('/integrations/feishu/status')) body = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
    else if (url.pathname.endsWith('/conversations')) body = { items: [], next_cursor: null }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  const evidenceDir = resolve(process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-c/view')
  mkdirSync(evidenceDir, { recursive: true })
  const measurements: unknown[] = []
  for (const width of [320, 390, 768, 960, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    for (const theme of ['light', 'dark'] as const) {
      await page.goto('/')
      await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
      await page.getByRole('combobox', { name: '主题' }).selectOption(theme)
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)

      await page.getByRole('button', { name: '项目' }).click()
      await expect(page.getByRole('button', { name: /模拟测试项目/ })).toBeVisible()
      const listMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth, font: parseFloat(getComputedStyle(document.body).fontSize) }))
      expect(listMetrics.document, `project list overflow ${width}/${theme}`).toBe(listMetrics.viewport)
      expect(listMetrics.body, `project list body overflow ${width}/${theme}`).toBe(listMetrics.viewport)
      expect(listMetrics.font).toBeGreaterThanOrEqual(12)
      await page.screenshot({ path: resolve(evidenceDir, `projects-list-${width}-${theme}.png`), fullPage: true })

      await page.getByRole('button', { name: /模拟测试项目/ }).click()
      await expect(page.getByRole('region', { name: '项目详情' })).toBeVisible()
      const detailMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
      expect(detailMetrics.document, `project detail overflow ${width}/${theme}`).toBe(detailMetrics.viewport)
      expect(detailMetrics.body, `project detail body overflow ${width}/${theme}`).toBe(detailMetrics.viewport)
      await page.screenshot({ path: resolve(evidenceDir, `projects-detail-${width}-${theme}.png`), fullPage: true })

      await page.getByRole('button', { name: /合成会议记录/ }).click()
      await expect(page.locator('.page-reader')).toBeVisible()
      const readerMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
      expect(readerMetrics.document, `reader overflow ${width}/${theme}`).toBe(readerMetrics.viewport)
      expect(readerMetrics.body, `reader body overflow ${width}/${theme}`).toBe(readerMetrics.viewport)
      await page.screenshot({ path: resolve(evidenceDir, `reader-${width}-${theme}.png`), fullPage: true })
      await page.getByRole('button', { name: '← 返回项目' }).click()
      await expect(page.getByRole('region', { name: '项目详情' })).toBeVisible()

      await page.getByRole('button', { name: '知识问答' }).click()
      const askForm = page.locator('.query-form')
      await expect(askForm).toBeVisible()
      const questionFirst = await askForm.evaluate((element) => element.getBoundingClientRect().top < element.parentElement!.querySelector('.ask-secondary')!.getBoundingClientRect().top)
      expect(questionFirst).toBe(true)
      const askMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
      expect(askMetrics.document, `ask overflow ${width}/${theme}`).toBe(askMetrics.viewport)
      expect(askMetrics.body, `ask body overflow ${width}/${theme}`).toBe(askMetrics.viewport)
      await page.screenshot({ path: resolve(evidenceDir, `ask-${width}-${theme}.png`), fullPage: true })
      measurements.push({ width, theme, listMetrics, detailMetrics, readerMetrics, askMetrics })
    }
  }
  expect(externalAttempts).toEqual([])
  expect(apiCalls.some((call) => call.startsWith('POST '))).toBe(false)
  writeFileSync(resolve(evidenceDir, 'measurements.json'), JSON.stringify({ measurements, apiCalls, externalAttempts }, null, 2))
})
