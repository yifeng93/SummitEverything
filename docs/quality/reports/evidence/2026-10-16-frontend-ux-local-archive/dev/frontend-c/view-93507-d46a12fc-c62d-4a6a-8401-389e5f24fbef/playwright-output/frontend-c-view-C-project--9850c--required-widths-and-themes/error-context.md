# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: frontend-c-view.spec.ts >> C project, reader and question-first views fit required widths and themes
- Location: e2e/frontend-c-view.spec.ts:31:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: true
Received: false
```

# Test source

```ts
  1   | import { mkdirSync, writeFileSync } from 'node:fs'
  2   | import { resolve } from 'node:path'
  3   | import { expect, test } from '@playwright/test'
  4   | 
  5   | const lineId = '11111111-1111-4111-8111-111111111111'
  6   | const projectId = '22222222-2222-4222-8222-222222222222'
  7   | const pageId = '33333333-3333-4333-8333-333333333333'
  8   | const hash = 'a'.repeat(64)
  9   | const line = { id: lineId, name: '模拟主线', directory: '模拟主线' }
  10  | const project = { id: projectId, line_id: lineId, name: '模拟测试项目', directory: '模拟主线/模拟测试项目', overview_id: null, archived: false, progress: '已完成首次访谈', progress_version: 1 }
  11  | const pageRecord = {
  12  |   page_id: pageId,
  13  |   relative_path: '模拟主线/模拟测试项目/会议记录.md',
  14  |   metadata: { id: pageId, title: '合成会议记录', role: 'knowledge', kind: 'meeting', line_id: lineId, project_id: projectId },
  15  |   body: '## 会议地点\n会议在北馆举行。\n\n[[未知页面]]',
  16  |   content_sha256: hash,
  17  |   raw_sha256: 'b'.repeat(64),
  18  |   storage_area: 'formal',
  19  |   approval_state: 'confirmed',
  20  |   validity: 'current',
  21  | }
  22  | const settings = {
  23  |   mode: 'fake', model_studio_account_id: 'synthetic-account',
  24  |   feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
  25  |   llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
  26  |   embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
  27  |   rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
  28  |   capabilities: {}, credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: false, embedding_fingerprint: 'synthetic-fingerprint',
  29  | }
  30  | 
  31  | test('C project, reader and question-first views fit required widths and themes', async ({ page }) => {
  32  |   const externalAttempts: string[] = []
  33  |   const apiCalls: string[] = []
  34  |   await page.route('**/*', async (route) => {
  35  |     const url = new URL(route.request().url())
  36  |     if (url.origin !== 'http://127.0.0.1:5191') {
  37  |       externalAttempts.push(url.origin)
  38  |       return route.abort()
  39  |     }
  40  |     if (!url.pathname.startsWith('/api/v1/')) return route.continue()
  41  |     apiCalls.push(`${route.request().method()} ${url.pathname}`)
  42  |     let body: unknown = []
  43  |     if (url.pathname.endsWith('/workspaces/current')) body = { workspace_id: 'synthetic-workspace', name: '模拟工作库', root: '/tmp/synthetic-workspace', local_profile_dir: '/tmp/synthetic-profile' }
  44  |     else if (url.pathname.endsWith('/settings')) body = settings
  45  |     else if (url.pathname.endsWith('/lines')) body = [line]
  46  |     else if (url.pathname.endsWith('/projects')) body = [project]
  47  |     else if (url.pathname.endsWith('/pages')) body = [pageRecord]
  48  |     else if (url.pathname.endsWith(`/pages/${pageId}`)) body = pageRecord
  49  |     else if (url.pathname.endsWith('/index/status')) body = { fingerprint: 'synthetic-fingerprint', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 }
  50  |     else if (url.pathname.endsWith('/action-intents')) body = { items: [], next_cursor: null }
  51  |     else if (url.pathname.endsWith('/provider-smoke')) body = { counts: {}, limits: {}, remaining: {} }
  52  |     else if (url.pathname.endsWith('/integrations/feishu/status')) body = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
  53  |     return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  54  |   })
  55  | 
  56  |   const evidenceDir = resolve(process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-c/view')
  57  |   mkdirSync(evidenceDir, { recursive: true })
  58  |   const measurements: unknown[] = []
  59  |   for (const width of [320, 390, 768, 960, 1280]) {
  60  |     await page.setViewportSize({ width, height: 900 })
  61  |     for (const theme of ['light', 'dark'] as const) {
  62  |       await page.goto('/')
  63  |       await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  64  |       await page.getByRole('combobox', { name: '主题' }).selectOption(theme)
  65  |       await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
  66  | 
  67  |       await page.getByRole('button', { name: '项目' }).click()
  68  |       await expect(page.getByRole('button', { name: /模拟测试项目/ })).toBeVisible()
  69  |       const listMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth, font: parseFloat(getComputedStyle(document.body).fontSize) }))
  70  |       expect(listMetrics.document, `project list overflow ${width}/${theme}`).toBe(listMetrics.viewport)
  71  |       expect(listMetrics.body, `project list body overflow ${width}/${theme}`).toBe(listMetrics.viewport)
  72  |       expect(listMetrics.font).toBeGreaterThanOrEqual(12)
  73  |       await page.screenshot({ path: resolve(evidenceDir, `projects-list-${width}-${theme}.png`), fullPage: true })
  74  | 
  75  |       await page.getByRole('button', { name: /模拟测试项目/ }).click()
  76  |       await expect(page.getByRole('region', { name: '项目详情' })).toBeVisible()
  77  |       const detailMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  78  |       expect(detailMetrics.document, `project detail overflow ${width}/${theme}`).toBe(detailMetrics.viewport)
  79  |       expect(detailMetrics.body, `project detail body overflow ${width}/${theme}`).toBe(detailMetrics.viewport)
  80  |       await page.screenshot({ path: resolve(evidenceDir, `projects-detail-${width}-${theme}.png`), fullPage: true })
  81  | 
  82  |       await page.getByRole('button', { name: /合成会议记录/ }).click()
  83  |       await expect(page.locator('.page-reader')).toBeVisible()
  84  |       const readerMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  85  |       expect(readerMetrics.document, `reader overflow ${width}/${theme}`).toBe(readerMetrics.viewport)
  86  |       expect(readerMetrics.body, `reader body overflow ${width}/${theme}`).toBe(readerMetrics.viewport)
  87  |       await page.screenshot({ path: resolve(evidenceDir, `reader-${width}-${theme}.png`), fullPage: true })
  88  |       await page.getByRole('button', { name: '← 返回项目' }).click()
  89  |       await expect(page.getByRole('region', { name: '项目详情' })).toBeVisible()
  90  | 
  91  |       await page.getByRole('button', { name: '知识问答' }).click()
  92  |       const askForm = page.locator('.query-form')
  93  |       await expect(askForm).toBeVisible()
  94  |       const questionFirst = await askForm.evaluate((element) => element.getBoundingClientRect().top < element.parentElement!.querySelector('details')!.getBoundingClientRect().top)
> 95  |       expect(questionFirst).toBe(true)
      |                             ^ Error: expect(received).toBe(expected) // Object.is equality
  96  |       const askMetrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  97  |       expect(askMetrics.document, `ask overflow ${width}/${theme}`).toBe(askMetrics.viewport)
  98  |       expect(askMetrics.body, `ask body overflow ${width}/${theme}`).toBe(askMetrics.viewport)
  99  |       await page.screenshot({ path: resolve(evidenceDir, `ask-${width}-${theme}.png`), fullPage: true })
  100 |       measurements.push({ width, theme, listMetrics, detailMetrics, readerMetrics, askMetrics })
  101 |     }
  102 |   }
  103 |   expect(externalAttempts).toEqual([])
  104 |   expect(apiCalls.some((call) => call.startsWith('POST '))).toBe(false)
  105 |   writeFileSync(resolve(evidenceDir, 'measurements.json'), JSON.stringify({ measurements, apiCalls, externalAttempts }, null, 2))
  106 | })
  107 | 
```