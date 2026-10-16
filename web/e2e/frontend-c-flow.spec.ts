import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

test('confirmed synthetic page indexes, answers, opens citation, then warns on its updated version', async ({ page }, testInfo) => {
  const externalAttempts: string[] = []
  const apiCalls: { method: string; path: string }[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5188') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (url.pathname.startsWith('/api/v1/')) apiCalls.push({ method: route.request().method(), path: url.pathname })
    return route.continue()
  })

  const evidenceDir = resolve(process.cwd(), process.env.SUMMIT_E2E_EVIDENCE_DIR ?? '../.local/dev/frontend-c/fastapi-integration')
  mkdirSync(evidenceDir, { recursive: true })
  const workspaceRoot = testInfo.outputPath('isolated-fake-workspace')
  mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await expect(page.getByText('首次配置 · 第 1 步，共 5 步')).toBeVisible()
  await page.getByLabel('工作库名称').fill('C 合成验收库')
  await page.getByLabel('文件夹路径').fill(workspaceRoot)
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  for (let step = 2; step < 5; step += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  await page.getByRole('button', { name: '完成并进入今日' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()

  const seeded = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: 'C 合成主线', operation_id: crypto.randomUUID() }) })
    if (!lineResponse.ok) throw new Error(`line seed failed: ${lineResponse.status}`)
    const line = await lineResponse.json() as { id: string }
    const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: 'C 合成项目', operation_id: crypto.randomUUID() }) })
    if (!projectResponse.ok) throw new Error(`project seed failed: ${projectResponse.status}`)
    const project = await projectResponse.json() as { id: string }
    const pageId = crypto.randomUUID()
    const created = await fetch('/api/v1/pages', {
      method: 'POST', headers,
      body: JSON.stringify({
        metadata: { id: pageId, title: '合成会议地点', role: 'knowledge', kind: 'topic', line_id: line.id, project_id: project.id },
        body: '## 会议地点\n会议在北馆举行。', confirmation_id: crypto.randomUUID(), operation_id: crypto.randomUUID(),
      }),
    })
    if (!created.ok) throw new Error(`page seed failed: ${created.status} ${await created.text()}`)
    return { line, project, pageId }
  })

  await page.getByRole('button', { name: '审批' }).click()
  const indexGroup = page.getByRole('region', { name: /4 · 索引/ })
  await indexGroup.getByRole('button', { name: '预览首次索引' }).click()
  await expect(indexGroup.getByText(/本次范围：1 页/)).toBeVisible()
  await indexGroup.getByRole('button', { name: '查看范围并确认' }).click()
  await indexGroup.getByRole('dialog', { name: '确认本次索引范围？' }).getByRole('button', { name: '确认并开始索引' }).click()
  await expect(indexGroup.getByText('当前状态：可用')).toBeVisible({ timeout: 20_000 })

  await page.getByRole('button', { name: '知识问答' }).click()
  await page.getByLabel('你的问题').fill('合成会议地点在哪里？')
  await page.getByRole('button', { name: '开始检索' }).click()
  await expect(page.getByRole('heading', { name: '引用依据' })).toBeVisible({ timeout: 30_000 })
  const citation = page.getByRole('button', { name: /会议地点/ }).last()
  await expect(citation).toBeVisible()
  await citation.click()
  await expect(page.locator('.page-reader')).toBeVisible()
  await expect(page.locator('.page-reader .page-body').getByText('会议在北馆举行。')).toBeVisible()
  await page.getByRole('button', { name: '← 返回知识问答' }).click()
  await expect(page.getByRole('heading', { name: '引用依据' })).toBeVisible()

  const updated = await page.evaluate(async (pageId) => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const currentResponse = await fetch(`/api/v1/pages/${pageId}`, { headers })
    if (!currentResponse.ok) throw new Error(`page read failed: ${currentResponse.status}`)
    const current = await currentResponse.json() as { metadata: Record<string, unknown>; body: string; content_sha256: string }
    const response = await fetch(`/api/v1/pages/${pageId}/confirmations`, {
      method: 'POST', headers,
      body: JSON.stringify({
        metadata: current.metadata, body: `${current.body}\n补充说明：改在南馆。`,
        confirmation_id: crypto.randomUUID(), operation_id: crypto.randomUUID(), expected_base_sha256: current.content_sha256,
      }),
    })
    if (!response.ok) throw new Error(`page update failed: ${response.status} ${await response.text()}`)
    return true
  }, seeded.pageId)
  expect(updated).toBe(true)
  await page.getByRole('button', { name: /会议地点/ }).last().click()
  await expect(page.getByText('引用保存的是回答当时的页面版本；该页面已更新。当前显示的是新版本，不能替代原回答依据。')).toBeVisible()
  await expect(page.locator('.page-reader')).toBeVisible()
  await expect(page.locator('.page-reader .page-body').getByText('补充说明：改在南馆。')).toBeVisible()
  expect(externalAttempts).toEqual([])
  expect(apiCalls.some(({ method, path }) => method === 'POST' && path.includes('/acceptance-plans'))).toBe(false)
  expect(apiCalls.some(({ method, path }) => method === 'POST' && path.includes('/provider-smoke/'))).toBe(false)
  writeFileSync(resolve(evidenceDir, 'frontend-c-flow-manifest.json'), JSON.stringify({ seeded, apiCalls, externalAttempts }, null, 2))
  await page.screenshot({ path: resolve(evidenceDir, 'citation-updated-page.png'), fullPage: true })
})
