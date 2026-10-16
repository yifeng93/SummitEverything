import { mkdirSync, writeFileSync } from 'node:fs'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'

test('FastAPI Fake flow keeps intake, knowledge confirmation, indexing and actions separate', async ({ page }, testInfo) => {
  const externalAttempts: string[] = []
  const writes: string[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5174') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (url.pathname.startsWith('/api/v1/') && route.request().method() !== 'GET') {
      writes.push(`${route.request().method()} ${url.pathname}`)
    }
    return route.continue()
  })

  const workspaceRoot = testInfo.outputPath('isolated-fake-workspace')
  mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })
  const evidenceDir = resolve(process.cwd(), '../.local/dev/frontend-b/fastapi-integration')
  mkdirSync(evidenceDir, { recursive: true })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')
  await expect(page.getByText('首次配置 · 第 1 步，共 5 步')).toBeVisible()
  await page.getByLabel('工作库名称').fill('B 合成验收库')
  await page.getByLabel('文件夹路径').fill(workspaceRoot)
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  for (let step = 2; step < 5; step += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  await page.getByRole('button', { name: '完成并进入今日' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()

  const seeded = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: 'B 合成主线', operation_id: crypto.randomUUID() }) })
    if (!lineResponse.ok) throw new Error(`line seed failed: ${lineResponse.status}`)
    const line = await lineResponse.json() as { id: string }
    const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: 'B 合成项目', operation_id: crypto.randomUUID() }) })
    if (!projectResponse.ok) throw new Error(`project seed failed: ${projectResponse.status}`)
    return { line: await lineResponse.json().catch(() => line), project: await projectResponse.json() as { id: string } }
  })
  // Only create local synthetic structure here; all intake, review, confirmation and indexing below use the UI.
  expect(seeded.line).toBeTruthy()

  const quickNote = '  合成记录：周五前确认会议安排。  \n'
  await page.getByLabel('记下一句话').fill(quickNote)
  await page.getByLabel('记下一句话').press('Enter')
  await expect(page.getByText('记一句 · 待整理')).toBeVisible()

  await page.getByRole('button', { name: '导入会议' }).click()
  const importDialog = page.getByRole('dialog', { name: '导入会议与材料' })
  await importDialog.locator('input[type=file]').first().setInputFiles({ name: '合成会议.md', mimeType: 'text/markdown', buffer: Buffer.from('导入原件正文\n') })
  await importDialog.getByRole('button', { name: '导入可用文件' }).click()
  await expect(importDialog.locator('li').filter({ hasText: '合成会议.md' })).toContainText('已导入')
  await importDialog.getByRole('button', { name: '关闭' }).click()

  const intakeEvidence = await page.evaluate(async () => {
    const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}` }
    const response = await fetch('/api/v1/intake/items', { headers })
    if (!response.ok) throw new Error(`intake list failed: ${response.status}`)
    return await response.json() as Array<{ item_id: string; source_id: string; origin_kind: string; original_relative_path: string }>
  })
  expect(intakeEvidence).toHaveLength(2)
  expect(intakeEvidence.map((item) => item.origin_kind).sort()).toEqual(['file', 'quick_note'])
  const rawNote = intakeEvidence.find((item) => item.origin_kind === 'quick_note')!
  const rawFile = intakeEvidence.find((item) => item.origin_kind === 'file')!
  expect(readFileSync(resolve(workspaceRoot, rawNote.original_relative_path))).toEqual(Buffer.from(quickNote))
  expect(readFileSync(resolve(workspaceRoot, rawFile.original_relative_path))).toEqual(Buffer.from('导入原件正文\n'))

  await page.getByRole('button', { name: '审批' }).click()
  const sourceGroup = page.getByRole('region', { name: /1 · 来源/ })
  const noteRow = sourceGroup.locator('label').filter({ hasText: '记一句' })
  await expect(noteRow.getByRole('checkbox')).toBeVisible()
  await noteRow.getByRole('checkbox').check()
  await expect(sourceGroup.getByLabel('主线')).toHaveValue(seeded.line.id)
  await expect(sourceGroup.getByLabel('项目')).toHaveValue(seeded.project.id)
  await sourceGroup.getByRole('button', { name: /整理所选/ }).click()
  const organizeDialog = page.getByRole('dialog', { name: '确认整理所选来源？' })
  await expect(organizeDialog).toBeVisible()
  const beforeCancel = writes.length
  await organizeDialog.getByRole('button', { name: '取消' }).click()
  expect(writes.slice(beforeCancel).some((entry) => entry.includes('/intake/jobs'))).toBe(false)

  await noteRow.getByRole('checkbox').check()
  await sourceGroup.getByRole('button', { name: /整理所选/ }).click()
  await page.getByRole('dialog', { name: '确认整理所选来源？' }).getByRole('button', { name: '确认并整理所选材料' }).click()
  const draftGroup = page.getByRole('region', { name: /2 · 稿件/ })
  await expect(draftGroup.getByRole('button', { name: '打开复核' })).toBeVisible({ timeout: 20_000 })
  await draftGroup.getByRole('button', { name: '打开复核' }).click()
  const review = draftGroup.getByRole('region', { name: '审核稿编辑' })
  await expect(review.getByLabel('正文')).toContainText('周五前确认会议安排')
  await expect(review.getByText('状态是否已确认？')).toBeVisible()
  const confirmDraft = review.getByRole('button', { name: '确认并保存当前版本' })
  await expect(confirmDraft).toBeDisabled()
  await review.getByLabel(/暂时未决/).check()
  await expect(confirmDraft).toBeEnabled()
  await confirmDraft.click()
  const knowledgeDialog = page.getByRole('dialog', { name: '确认并保存当前稿件版本？' })
  await expect(knowledgeDialog).toBeVisible()
  await expect(knowledgeDialog).toContainText('不会创建飞书任务')
  await knowledgeDialog.getByRole('button', { name: '确认并保存当前版本' }).click()
  await page.getByRole('combobox', { name: '显示' }).selectOption('all')
  const formalGroup = page.getByRole('region', { name: /3 · 正式内容/ })
  await expect(formalGroup.getByText('模拟整理稿 1')).toBeVisible()
  await formalGroup.getByText('查看完整正文').click()
  await expect(page.getByText('合成记录：周五前确认会议安排。')).toBeVisible()
  await expect(page.getByText(/状态是否已确认？：暂时未决/)).toBeVisible()
  await formalGroup.getByRole('button', { name: '确认并保存当前版本' }).click()
  const formalConfirmation = page.getByRole('dialog', { name: '确认并保存当前正式版本？' })
  await formalConfirmation.getByRole('button', { name: '确认并保存当前版本' }).click()
  await expect(page.getByText('当前版本已确认并保存。索引自动更新状态会单独显示。')).toBeVisible()
  const indexGroup = page.getByRole('region', { name: /4 · 索引/ })
  await indexGroup.getByRole('button', { name: '预览首次索引' }).click()
  await expect(indexGroup.getByText(/本次范围：1 页/)).toBeVisible()
  await indexGroup.getByRole('button', { name: '查看范围并确认' }).click()
  await indexGroup.getByRole('dialog', { name: '确认本次索引范围？' }).getByRole('button', { name: '确认并开始索引' }).click()
  await expect(indexGroup.getByText('当前状态：可用')).toBeVisible({ timeout: 20_000 })

  const actionGroup = page.getByRole('region', { name: /5 · 外部动作/ })
  await expect(actionGroup.getByText('没有已保存的外部动作')).toBeVisible()
  expect(writes.some((entry) => /\/actions\/[^/]+\/(confirmations|executions)/.test(entry))).toBe(false)
  expect(externalAttempts).toEqual([])
  writeFileSync(resolve(evidenceDir, 'workflow-manifest.json'), JSON.stringify({ writes, externalAttempts }, null, 2))
  await page.screenshot({ path: resolve(evidenceDir, 'approval-after-fake-flow.png'), fullPage: true })
})
