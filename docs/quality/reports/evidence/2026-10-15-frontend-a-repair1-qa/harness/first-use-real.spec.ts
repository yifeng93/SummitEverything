import { mkdirSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'

const { expect, test } = createRequire(resolve(process.cwd(), 'package.json'))('@playwright/test')

test('first use completes with real FastAPI and isolated Fake workspace', async ({ page }, testInfo) => {
  const externalAttempts: string[] = []
  const apiCalls: { method: string; path: string }[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5174') {
      externalAttempts.push(url.origin)
      return route.abort()
    }
    if (url.pathname.startsWith('/api/v1/')) apiCalls.push({ method: route.request().method(), path: url.pathname })
    return route.continue()
  })

  const workspaceRoot = testInfo.outputPath('isolated-fake-workspace')
  mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })
  const evidenceDir = resolve(process.cwd(), '../.local/qa/frontend-a-repair1/fastapi-integration')
  mkdirSync(evidenceDir, { recursive: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByText('首次配置 · 第 1 步，共 5 步')).toBeVisible()
  await page.getByLabel('工作库名称').fill('集成测试模拟库')
  await page.getByLabel('文件夹路径').fill(workspaceRoot)
  await page.getByRole('button', { name: '创建本地工作库' }).click()

  await expect(page.getByRole('heading', { name: '第 2 步 · 模型与密钥' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '设置' })).toHaveCount(0)
  await expect(page.getByRole('checkbox', { name: /整理与问答/ })).not.toBeChecked()
  await page.screenshot({ path: resolve(evidenceDir, 'fastapi-onboarding-step-2.png'), fullPage: true })

  await page.getByRole('button', { name: '稍后再说' }).click()
  await page.getByRole('button', { name: '稍后再说' }).click()
  await page.getByRole('button', { name: '稍后再说' }).click()
  await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  expect(apiCalls.some(({ method, path }) => method === 'POST' && path.includes('/provider-smoke/'))).toBe(false)
  await page.screenshot({ path: resolve(evidenceDir, 'fastapi-onboarding-complete.png'), fullPage: true })
  await page.getByRole('button', { name: '完成并进入今日' }).click()
  await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()

  await page.getByRole('button', { name: '设置' }).click()
  await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
  expect(apiCalls.some(({ method, path }) => method === 'GET' && path === '/api/v1/settings')).toBe(true)
  expect(apiCalls.some(({ method, path }) => method === 'GET' && path === '/api/v1/workspaces/current')).toBe(true)
  expect(apiCalls.some(({ method, path }) => method === 'POST' && path === '/api/v1/workspaces')).toBe(true)
  expect(apiCalls.some(({ method, path }) => method === 'POST' && path.includes('/provider-smoke/'))).toBe(false)
  expect(externalAttempts).toEqual([])
  writeFileSync(resolve(evidenceDir, 'fastapi-request-manifest.json'), JSON.stringify({ apiCalls, externalAttempts }, null, 2))
})
