import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

const qaExpect = expect.configure({ timeout: 15_000 })
const evidence = resolve(process.cwd(), '.local/qa/external-watch-20261030')
mkdirSync(resolve(evidence, 'logs'), { recursive: true })
mkdirSync(resolve(evidence, 'screenshots'), { recursive: true })

 test('desktop business UI uses real FastAPI and isolated synthetic workspace', async ({ page }, info) => {
  test.setTimeout(360_000)
  page.setDefaultTimeout(15_000)
  const externalAttempts: string[] = []
  let reopenedDraftLinkCount = -1
  const localRequests: Array<{ method: string; path: string; status?: number }> = []
  const indexJobResponses: Array<{ status: number; body: string }> = []
  const indexPlanResponses: Array<{ status: number; body: string }> = []
  const revisionConfirmationResponses: Array<{ status: number; body: string }> = []
  const indexStatusResponses: Array<{ status: number; body: string }> = []
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:8895') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (url.pathname.startsWith('/api/v1/')) {
      localRequests.push({ method: route.request().method(), path: url.pathname })
    }
    await route.continue()
  })
  page.on('response', (response) => {
    const url = new URL(response.url())
    if (url.origin === 'http://127.0.0.1:8895' && url.pathname.startsWith('/api/v1/')) {
      const item = [...localRequests].reverse().find((entry) => entry.path === url.pathname && entry.status === undefined)
      if (item) item.status = response.status()
      if (url.pathname === '/api/v1/index/jobs') {
        void response.text().then((body) => indexJobResponses.push({ status: response.status(), body }))
      }
      if (url.pathname === '/api/v1/index/plans') {
        void response.text().then((body) => {
          indexPlanResponses.push({ status: response.status(), body })
          writeFileSync(resolve(evidence, 'logs/index-plan-responses.json'), JSON.stringify(indexPlanResponses, null, 2))
        })
      }
      if (url.pathname.endsWith('/confirmations')) {
        void response.text().then((body) => {
          revisionConfirmationResponses.push({ status: response.status(), body })
          writeFileSync(resolve(evidence, 'logs/revision-confirmation-responses.json'), JSON.stringify(revisionConfirmationResponses, null, 2))
        })
      }
      if (url.pathname === '/api/v1/index/status') {
        void response.text().then((body) => {
          indexStatusResponses.push({ status: response.status(), body })
          writeFileSync(resolve(evidence, 'logs/index-status-responses.json'), JSON.stringify(indexStatusResponses, null, 2))
        })
      }
      if (url.pathname === '/api/v1/settings') {
        void response.json().then((body: { mode?: string; llm?: { provider?: string }; embedding_fingerprint?: string }) => {
          writeFileSync(resolve(evidence, 'logs/settings-runtime.json'), JSON.stringify({ status: response.status(), mode: body.mode, llm_provider: body.llm?.provider, embedding_fingerprint: body.embedding_fingerprint }, null, 2))
        }).catch(() => undefined)
      }
    }
  })
  const libraryPath = info.outputPath('library-one')
  mkdirSync(libraryPath, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.goto('/')
  await page.screenshot({ path: resolve(evidence, 'screenshots/01-first-use.png') })
  await qaExpect(page.getByRole('heading', { name: '新建工作库' })).toBeVisible({ timeout: 20_000 })
  await page.getByLabel('工作库名称').fill('桌面合成验收库')
  await page.getByLabel('文件夹路径').fill(libraryPath)
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  await qaExpect(page.getByRole('heading', { name: /第 2 步/ })).toBeVisible({ timeout: 20_000 })
  for (let i = 0; i < 3; i += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  await qaExpect(page.getByRole('heading', { name: /第 5 步/ })).toBeVisible()
  await page.getByRole('button', { name: /开始使用|完成并进入今日/ }).click()
  await qaExpect(page.getByRole('heading', { name: '今日' })).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: '项目' }).click()
  await qaExpect(page.getByRole('heading', { name: '项目' })).toBeVisible()
  await page.getByRole('button', { name: '新建第一条主线' }).click()
  await page.locator('#new-line').fill('合成验收主线')
  await page.getByRole('button', { name: '新建主线' }).click()
  await qaExpect(page.getByLabel('管理主线')).toHaveValue(/.+/)
  await page.getByRole('button', { name: '新建项目' }).click()
  await page.getByLabel('新项目主线').selectOption({ label: '合成验收主线' })
  await page.locator('#new-project').fill('飞纸读书会')
  await page.getByRole('button', { name: '创建项目' }).click()
  await qaExpect(page.getByRole('button', { name: /新 飞纸读书会/ })).toBeVisible()
  const apiEvidence = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const call = async (path: string, method: string, body?: unknown) => {
      const response = await fetch(`/api/v1${path}`, { method, headers, ...(body ? { body: JSON.stringify(body) } : {}) })
      const data = response.status === 204 ? null : await response.json()
      if (!response.ok) throw new Error(`${method} ${path}: ${response.status} ${JSON.stringify(data)}`)
      return data
    }
    const [lines, projects] = await Promise.all([call('/lines', 'GET'), call('/projects', 'GET')]) as [Array<{ id: string }>, Array<{ id: string; line_id: string }>]
    const lineId = lines[0].id
    const projectId = projects[0].id
    await call('/settings', 'PATCH', {
      mode: 'real',
      llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'external-watch-qa', enabled: true },
      embedding: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', dimensions: 512, enabled: true },
    })
    await call('/credentials/deepseek', 'PUT', { account_id: 'external-watch-qa', secret: 'sk-synthetic-external-watch-qa-key' })
    const pageId = crypto.randomUUID()
    const title = '合成外部更新规则'
    const body = '合成事实：活动于 2026-10-30 14:00 至 16:00，最多 24 人。集合地点：临时西门合成大厅。'
    const created = await call('/pages', 'POST', {
      metadata: { id: pageId, title, role: 'knowledge', kind: 'topic', validity: 'current', line_id: lineId, project_id: projectId },
      body,
      confirmation_id: crypto.randomUUID(),
      operation_id: crypto.randomUUID(),
    }) as { index_update?: string }
    const settings = await call('/settings', 'GET') as { embedding_fingerprint: string; local_model?: { state: string } }
    const pages = await call('/pages', 'GET') as Array<{ page_id: string; content_sha256: string; relative_path: string; approval_state: string; metadata: { title: string } }>
    const index = await call('/index/status', 'GET')
    return { created, page: pages.find((item) => item.page_id === pageId), pages, index, settings }
  })
  const formalTitle = apiEvidence.page?.metadata.title ?? ''
  expect(apiEvidence.page?.approval_state).toBe('confirmed')
  expect(apiEvidence.created.index_update).toBe('not_enabled')
  expect(apiEvidence.index.state).toBe('not_ready')
  writeFileSync(resolve(evidence, 'logs/seeded-index.json'), JSON.stringify(apiEvidence, null, 2))

  await page.locator('button.nav-item[title="审批"]').click()
  const firstIndexGroup = page.getByRole('region', { name: '搜索与问答准备' })
  await firstIndexGroup.getByRole('button', { name: '准备已确认的内容' }).click()
  await firstIndexGroup.getByRole('button', { name: '查看范围并确认' }).click()
  const initialIndexConfirm = page.getByRole('dialog', { name: '确认准备搜索和问答内容？' })
  await qaExpect(initialIndexConfirm).toContainText('将准备 1 页已确认内容。')
  await initialIndexConfirm.getByRole('button', { name: '确认并开始准备' }).click()
  await qaExpect(firstIndexGroup).toContainText('内容已是最新，无需操作', { timeout: 120_000 })
  const establishedIndex = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    return fetch('/api/v1/index/status', { headers: { Authorization: `Bearer ${token}` } }).then((response) => response.json())
  })
  expect(establishedIndex.state).toBe('ready')
  expect(establishedIndex.current_pages).toBe(1)
  const indexEvidence = { pages: apiEvidence.pages, index: establishedIndex }
  await page.locator('button.nav-item[title="知识问答"]').click()
  await page.locator('#knowledge-question').fill('活动的集合地点是什么？')
  await page.getByRole('button', { name: '开始检索' }).click()
  const askPreview = page.getByRole('region', { name: '真实问答发送预览' })
  await qaExpect(askPreview).toContainText(formalTitle)
  await askPreview.getByRole('button', { name: '确认并发送本次问题' }).click()
  const conversation = page.getByRole('region', { name: '对话内容' })
  await qaExpect(conversation).toContainText('临时西门合成大厅', { timeout: 60_000 })
  await page.locator('.citation-list button').first().click()
  const initialReader = page.locator('.page-reader')
  await qaExpect(initialReader).toContainText('临时西门合成大厅')
  await qaExpect(initialReader).not.toHaveJSProperty('isContentEditable', true)
  await page.screenshot({ path: resolve(evidence, 'screenshots/05-confirmed-indexed-reader.png'), fullPage: true })

  // External atomic save: keep this browser and inline reader mounted.
  const originalFormalPage = indexEvidence.pages[0] as { relative_path: string; page_id: string; content_sha256: string }
  const formalFile = resolve(libraryPath, originalFormalPage.relative_path)
  const oldMarkdown = readFileSync(formalFile, 'utf-8')
  const oldFact = '合成事实：活动于 2026-10-30 14:00 至 16:00，最多 24 人。集合地点：临时西门合成大厅。'
  const updatedFact = '合成事实：活动于 2026-10-30 14:00 至 16:00，最多 24 人。集合地点：东门合成大厅。'
  expect(oldMarkdown).toContain(oldFact)
  const tempFile = `${formalFile}.qa-tmp`
  writeFileSync(tempFile, oldMarkdown.replace(oldFact, updatedFact))
  const { renameSync } = await import('node:fs')
  renameSync(tempFile, formalFile)
  let injectedDetailFailures = 0
  let detailGets = 0
  await page.route(`**/api/v1/pages/${originalFormalPage.page_id}**`, async (route) => {
    const request = route.request()
    if (request.method() === 'GET' && new URL(request.url()).pathname === `/api/v1/pages/${originalFormalPage.page_id}`) {
      detailGets += 1
      if (injectedDetailFailures === 0) {
        injectedDetailFailures += 1
        return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'synthetic transient detail failure' }) })
      }
    }
    await route.continue()
  })
  const pageReader = page.locator('.page-reader')
  await qaExpect(pageReader).toContainText('东门合成大厅', { timeout: 45_000 })
  await qaExpect(pageReader.locator('.page-reconfirmation')).toBeVisible()
  await qaExpect(pageReader.locator('.page-status-invalid')).toContainText('待确认')
  await qaExpect.poll(() => detailGets).toBeGreaterThanOrEqual(2)
  const revisionText = await pageReader.innerText()
  await page.screenshot({ path: resolve(evidence, 'screenshots/07-external-change-pending.png'), fullPage: true })

  const beforeConfirm = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}` }
    const [index, pages] = await Promise.all([
      fetch('/api/v1/index/status', { headers }).then((response) => response.json()),
      fetch('/api/v1/pages', { headers }).then((response) => response.json()),
    ])
    return { index, pages }
  })
  const persistedPage = beforeConfirm.pages.find((candidate: { page_id: string }) => candidate.page_id === originalFormalPage.page_id)
  expect(persistedPage.approval_state).not.toBe('confirmed')
  expect(revisionText).toContain('待确认')
  const formalConfirmation = pageReader.locator('.page-reconfirmation').getByRole('button', { name: '确认当前版本' })
  await qaExpect(formalConfirmation).toBeEnabled()
  const confirmationResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === 'POST' && url.pathname === `/api/v1/pages/${originalFormalPage.page_id}/confirmations`
  })
  await formalConfirmation.click()
  const confirmationResponse = await confirmationResponsePromise
  const externalConfirmationResult = await confirmationResponse.json() as { index_update?: string }
  expect(confirmationResponse.status()).toBe(200)
  expect(externalConfirmationResult.index_update).toBe('updated')
  await qaExpect(pageReader.locator('.page-meta')).toContainText('已确认')
  await qaExpect(pageReader).toContainText('东门合成大厅')
  const finalEvidence = await page.evaluate(async (oldHash: string) => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}` }
    const [index, pages, conversations] = await Promise.all([
      fetch('/api/v1/index/status', { headers }).then((response) => response.json()),
      fetch('/api/v1/pages', { headers }).then((response) => response.json()),
      fetch('/api/v1/conversations?limit=20', { headers }).then((response) => response.json()),
    ])
    const previous = conversations.items.find((item: { title: string }) => item.title === '活动的集合地点是什么？')
    const previousDetail = previous ? await fetch(`/api/v1/conversations/${previous.conversation_id}`, { headers }).then((response) => response.json()) : null
    return { index, pages, previousDetail, oldHash }
  }, originalFormalPage.content_sha256)
  const updatedPage = finalEvidence.pages.find((candidate: { page_id: string }) => candidate.page_id === originalFormalPage.page_id)
  expect(updatedPage.content_sha256).not.toBe(originalFormalPage.content_sha256)
  expect(finalEvidence.index.state).toBe('ready')
  expect(finalEvidence.index.stale_pages).toBe(0)
  expect(finalEvidence.previousDetail.messages[0].citations[0].availability).toBe('updated')
  writeFileSync(resolve(evidence, 'logs/external-watch-flow.json'), JSON.stringify({
    pageId: originalFormalPage.page_id,
    oldHash: originalFormalPage.content_sha256,
    newHash: updatedPage.content_sha256,
    injectedDetailFailures,
    detailGets,
    beforeConfirm: { approvalState: persistedPage.approval_state, index: beforeConfirm.index },
    confirmationStatus: confirmationResponse.status(),
    indexUpdate: externalConfirmationResult.index_update,
    finalIndex: finalEvidence.index,
    finalApprovalState: updatedPage.approval_state,
  }, null, 2))
  await page.screenshot({ path: resolve(evidence, 'screenshots/08-confirmed-current-version.png'), fullPage: true })
  await page.locator('button.nav-item[title="知识问答"]').click()
  await page.getByRole('button', { name: '新建对话' }).click()
  await page.locator('#knowledge-question').fill('活动的集合地点是什么？')
  await page.getByRole('button', { name: '开始检索' }).click()
  const updatedAskPreview = page.getByRole('region', { name: '真实问答发送预览' })
  await qaExpect(updatedAskPreview).toContainText(formalTitle)
  await updatedAskPreview.getByRole('button', { name: '确认并发送本次问题' }).click()
  const updatedConversation = page.getByRole('region', { name: '对话内容' })
  await qaExpect(updatedConversation.locator('.assistant-answer').last()).toContainText('东门合成大厅', { timeout: 60_000 })
  const providerEvidence = JSON.parse(readFileSync(resolve(evidence, 'logs/provider-requests.json'), 'utf-8'))
  writeFileSync(resolve(evidence, 'logs/provider-evidence-summary.json'), JSON.stringify({ calls: providerEvidence.calls, answerRequests: providerEvidence.requests.filter((entry: { kind?: string }) => entry.kind === 'answer').length }, null, 2))
  writeFileSync(resolve(evidence, 'logs/browser-network.json'), JSON.stringify({ externalAttempts, localRequests, consoleErrors, pageErrors }, null, 2))
  expect(externalAttempts).toEqual([])
  expect(pageErrors).toEqual([])
  expect(localRequests.some((request) => request.path === '/api/v1/pages/revision')).toBeTruthy()
 })
