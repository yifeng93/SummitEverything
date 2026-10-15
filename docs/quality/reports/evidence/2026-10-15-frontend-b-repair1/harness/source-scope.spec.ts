import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'

test('Real source preview shows the exact synthetic scope before any organize call', async ({ page }, testInfo) => {
  const externalAttempts: string[] = []
  const intakeJobWrites: string[] = []
  let previewRequest: unknown
  let sourceId = ''
  const originalText = '合成原文哨兵：周五前确认测试场地与酒店，不代表真实业务材料。'
  const scope: Record<string, unknown> = {
    item_ids: [], operation_id: 'synthetic-operation', line_id: '', project_id: '', reprocess: false,
    max_output_tokens: 512, outgoing_inputs: [],
  }
  await page.route('**/*', async (route) => {
    const requestUrl = new URL(route.request().url())
    if (requestUrl.origin !== 'http://127.0.0.1:5174') {
      externalAttempts.push(requestUrl.origin)
      return route.abort()
    }
    if (requestUrl.pathname === '/api/v1/settings' && route.request().method() === 'GET') {
      const response = await route.fetch()
      const settings = await response.json()
      return route.fulfill({ response, json: { ...settings, mode: 'real' } })
    }
    if (requestUrl.pathname === '/api/v1/intake/items' && route.request().method() === 'GET') {
      const response = await route.fetch()
      const payload = await response.json() as Array<{ source_id: string }>
      sourceId = payload[0]?.source_id ?? ''
      return route.fulfill({ response, json: payload })
    }
    if (requestUrl.pathname === '/api/v1/acceptance-plans' && route.request().method() === 'POST') {
      previewRequest = route.request().postDataJSON()
      const requestedScope = (previewRequest as { scope: { item_ids: string[]; line_id: string; project_id: string; operation_id: string; reprocess: boolean } }).scope
      Object.assign(scope, {
        ...requestedScope,
        outgoing_inputs: [{ item_id: requestedScope.item_ids[0], source_id: sourceId, text: originalText }],
      })
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ plan: { plan_id: 'synthetic-plan', scope_sha256: 'synthetic-scope-hash', request_limit: 1 }, scope }) })
    }
    if (requestUrl.pathname === '/api/v1/acceptance-plans/synthetic-plan' && route.request().method() === 'DELETE') {
      return route.fulfill({ status: 204, body: '' })
    }
    if (requestUrl.pathname === '/api/v1/intake/jobs' && route.request().method() === 'POST') intakeJobWrites.push(route.request().method())
    return route.continue()
  })

  const workspaceRoot = testInfo.outputPath(`isolated-synthetic-workspace-${randomUUID()}`)
  mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await page.getByLabel('工作库名称').fill('QA 合成范围库')
  await page.getByLabel('文件夹路径').fill(workspaceRoot)
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  for (let step = 2; step < 5; step += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  await page.getByRole('button', { name: '完成并进入今日' }).click()

  const seeded = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: 'QA 合成主线', operation_id: crypto.randomUUID() }) })
    const line = await lineResponse.json() as { id: string }
    const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: 'QA 合成项目', operation_id: crypto.randomUUID() }) })
    const project = await projectResponse.json() as { id: string }
    return { line, project }
  })
  expect(seeded.line.id).toBeTruthy()
  await page.getByLabel('记下一句话').fill('合成原文哨兵：周五前确认测试场地与酒店，不代表真实业务材料。')
  await page.getByLabel('记下一句话').press('Enter')
  await page.getByRole('button', { name: '审批' }).click()
  const sourceGroup = page.getByRole('region', { name: /1 · 来源/ })
  await sourceGroup.getByRole('checkbox').check()
  await sourceGroup.getByRole('button', { name: /整理所选/ }).click()
  const dialog = page.getByRole('dialog', { name: '确认整理所选来源？' })
  await expect(dialog).toBeVisible()
  await dialog.getByText('查看本次范围').click()

  const visibleText = await dialog.innerText()
  const previewRequestScope = (previewRequest as { scope: { item_ids: string[]; line_id: string; project_id: string } }).scope
  const visibility = {
    originalText: visibleText.includes(originalText),
    selectedProject: visibleText.includes('QA 合成项目'),
    requestBudget: visibleText.includes('请求上限 1 次'),
  }
  const evidenceDir = resolve(process.cwd(), '../.local/qa/frontend-b-repair1/evidence')
  mkdirSync(evidenceDir, { recursive: true })
  writeFileSync(resolve(evidenceDir, 'source-scope-dialog.txt'), visibleText)
  writeFileSync(resolve(evidenceDir, 'source-scope-request.json'), JSON.stringify({ request: previewRequest, scope }, null, 2))
  writeFileSync(resolve(evidenceDir, 'source-scope-visible-fields.json'), JSON.stringify(visibility, null, 2))
  await page.screenshot({ path: resolve(evidenceDir, 'source-scope-dialog.png'), fullPage: true })

  // The preview contract requires a human-readable exact original, target, and request budget.
  expect(previewRequest).toMatchObject({ operation: 'model.organize' })

  await dialog.getByRole('button', { name: '取消' }).click()
  expect(intakeJobWrites).toEqual([])
  expect(externalAttempts).toEqual([])
  await page.getByRole('button', { name: '今日' }).click()
  await page.getByRole('button', { name: '导入会议' }).click()
  const importDialog = page.getByRole('dialog', { name: '导入会议与材料' })
  const focusWalk: Array<Record<string, string>> = []
  for (let step = 0; step < 8; step += 1) {
    await page.keyboard.press('Tab')
    if (step === 0) await page.screenshot({ path: resolve(evidenceDir, 'import-first-file-focus.png') })
    focusWalk.push(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      const style = el ? getComputedStyle(el) : null
      return {
        tag: el?.tagName ?? '',
        type: (el as HTMLInputElement | null)?.type ?? '',
        label: el?.getAttribute('aria-label') ?? el?.textContent?.trim().slice(0, 80) ?? '',
        dialogContains: String(Boolean(el && document.querySelector('[aria-label="导入会议与材料"]')?.contains(el))),
        display: style?.display ?? '',
        visibility: style?.visibility ?? '',
        clip: style?.clip ?? '',
        bounds: el ? JSON.stringify(el.getBoundingClientRect().toJSON()) : '',
      }
    }))
  }
  writeFileSync(resolve(evidenceDir, 'import-focus-walk.json'), JSON.stringify(focusWalk, null, 2))
  expect(importDialog).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(importDialog).toBeHidden()
  await expect(page.getByRole('button', { name: '导入会议' })).toBeFocused()
  expect(previewRequestScope.line_id).toBe(seeded.line.id)
  expect(previewRequestScope.project_id).toBe(seeded.project.id)
  expect(visibility).toEqual({ originalText: true, selectedProject: true, requestBudget: true })
})
