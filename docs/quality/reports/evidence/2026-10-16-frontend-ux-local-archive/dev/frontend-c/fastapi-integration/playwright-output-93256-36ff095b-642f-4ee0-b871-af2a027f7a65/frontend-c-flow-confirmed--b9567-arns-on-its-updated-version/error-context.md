# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: frontend-c-flow.spec.ts >> confirmed synthetic page indexes, answers, opens citation, then warns on its updated version
- Location: e2e/frontend-c-flow.spec.ts:5:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('region', { name: '页面阅读' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('region', { name: '页面阅读' }) with timeout 5000ms
  - waiting for getByRole('region', { name: '页面阅读' })

```

```yaml
- link "跳到主内容":
  - /url: "#main-content"
- complementary:
  - strong: SummitEverything
  - text: 个人知识工作台
  - navigation "主导航":
    - button "今日"
    - button "审批"
    - button "项目"
    - button "知识问答"
    - button "设置"
  - button "切换工作库":
    - strong: C 合成验收库
    - text: 切换…
  - text: 仅本机运行
- banner:
  - text: 知识问答 合成会议地点
  - status: 已保存
  - combobox "主题":
    - option "跟随系统" [selected]
    - option "浅色"
    - option "深色"
- main:
  - article:
    - button "← 返回知识问答"
    - text: 已确认知识
    - heading "合成会议地点" [level=1]
    - heading "会议地点" [level=2]
    - paragraph: 会议在北馆举行。
    - region "页面组织操作":
      - text: 移动到项目
      - combobox "移动到项目":
        - option "选择项目" [selected]
      - button "移动页面" [disabled]
      - text: 添加页面链接
      - combobox "链接到页面":
        - option "选择已确认页面" [selected]
      - button "插入链接" [disabled]
```

# Test source

```ts
  1   | import { mkdirSync, writeFileSync } from 'node:fs'
  2   | import { resolve } from 'node:path'
  3   | import { expect, test } from '@playwright/test'
  4   | 
  5   | test('confirmed synthetic page indexes, answers, opens citation, then warns on its updated version', async ({ page }, testInfo) => {
  6   |   const externalAttempts: string[] = []
  7   |   const apiCalls: { method: string; path: string }[] = []
  8   |   await page.route('**/*', async (route) => {
  9   |     const url = new URL(route.request().url())
  10  |     if (url.origin !== 'http://127.0.0.1:5188') {
  11  |       externalAttempts.push(url.origin)
  12  |       return route.abort()
  13  |     }
  14  |     if (url.pathname.startsWith('/api/v1/')) apiCalls.push({ method: route.request().method(), path: url.pathname })
  15  |     return route.continue()
  16  |   })
  17  | 
  18  |   const evidenceDir = resolve(process.cwd(), '../.local/dev/frontend-c/fastapi-integration')
  19  |   mkdirSync(evidenceDir, { recursive: true })
  20  |   const workspaceRoot = testInfo.outputPath('isolated-fake-workspace')
  21  |   mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })
  22  | 
  23  |   await page.setViewportSize({ width: 1280, height: 900 })
  24  |   await page.goto('/')
  25  |   await expect(page.getByText('首次配置 · 第 1 步，共 5 步')).toBeVisible()
  26  |   await page.getByLabel('工作库名称').fill('C 合成验收库')
  27  |   await page.getByLabel('文件夹路径').fill(workspaceRoot)
  28  |   await page.getByRole('button', { name: '创建本地工作库' }).click()
  29  |   for (let step = 2; step < 5; step += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  30  |   await expect(page.getByRole('heading', { name: '第 5 步 · 完成' })).toBeVisible()
  31  |   await page.getByRole('button', { name: '完成并进入今日' }).click()
  32  |   await expect(page.getByRole('heading', { name: '今日' })).toBeVisible()
  33  | 
  34  |   const seeded = await page.evaluate(async () => {
  35  |     const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
  36  |     const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  37  |     const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: 'C 合成主线', operation_id: crypto.randomUUID() }) })
  38  |     if (!lineResponse.ok) throw new Error(`line seed failed: ${lineResponse.status}`)
  39  |     const line = await lineResponse.json() as { id: string }
  40  |     const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: 'C 合成项目', operation_id: crypto.randomUUID() }) })
  41  |     if (!projectResponse.ok) throw new Error(`project seed failed: ${projectResponse.status}`)
  42  |     const project = await projectResponse.json() as { id: string }
  43  |     const pageId = crypto.randomUUID()
  44  |     const created = await fetch('/api/v1/pages', {
  45  |       method: 'POST', headers,
  46  |       body: JSON.stringify({
  47  |         metadata: { id: pageId, title: '合成会议地点', role: 'knowledge', kind: 'topic', line_id: line.id, project_id: project.id },
  48  |         body: '## 会议地点\n会议在北馆举行。', confirmation_id: crypto.randomUUID(), operation_id: crypto.randomUUID(),
  49  |       }),
  50  |     })
  51  |     if (!created.ok) throw new Error(`page seed failed: ${created.status} ${await created.text()}`)
  52  |     return { line, project, pageId }
  53  |   })
  54  | 
  55  |   await page.getByRole('button', { name: '审批' }).click()
  56  |   const indexGroup = page.getByRole('region', { name: /4 · 索引/ })
  57  |   await indexGroup.getByRole('button', { name: '预览首次索引' }).click()
  58  |   await expect(indexGroup.getByText(/本次范围：1 页/)).toBeVisible()
  59  |   await indexGroup.getByRole('button', { name: '查看范围并确认' }).click()
  60  |   await indexGroup.getByRole('dialog', { name: '确认本次索引范围？' }).getByRole('button', { name: '确认并开始索引' }).click()
  61  |   await expect(indexGroup.getByText('当前状态：可用')).toBeVisible({ timeout: 20_000 })
  62  | 
  63  |   await page.getByRole('button', { name: '知识问答' }).click()
  64  |   await page.getByLabel('你的问题').fill('合成会议地点在哪里？')
  65  |   await page.getByRole('button', { name: '开始检索' }).click()
  66  |   await expect(page.getByRole('heading', { name: '引用依据' })).toBeVisible({ timeout: 30_000 })
  67  |   const citation = page.getByRole('button', { name: /会议地点/ }).last()
  68  |   await expect(citation).toBeVisible()
  69  |   await citation.click()
> 70  |   await expect(page.getByRole('region', { name: '页面阅读' })).toBeVisible()
      |                                                            ^ Error: expect(locator).toBeVisible() failed
  71  |   await expect(page.getByText('会议在北馆举行。')).toBeVisible()
  72  |   await page.getByRole('button', { name: '← 返回知识问答' }).click()
  73  |   await expect(page.getByRole('heading', { name: '引用依据' })).toBeVisible()
  74  | 
  75  |   const updated = await page.evaluate(async (pageId) => {
  76  |     const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
  77  |     const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  78  |     const currentResponse = await fetch(`/api/v1/pages/${pageId}`, { headers })
  79  |     if (!currentResponse.ok) throw new Error(`page read failed: ${currentResponse.status}`)
  80  |     const current = await currentResponse.json() as { metadata: Record<string, unknown>; body: string; content_sha256: string }
  81  |     const response = await fetch(`/api/v1/pages/${pageId}/confirmations`, {
  82  |       method: 'POST', headers,
  83  |       body: JSON.stringify({
  84  |         metadata: current.metadata, body: `${current.body}\n补充说明：改在南馆。`,
  85  |         confirmation_id: crypto.randomUUID(), operation_id: crypto.randomUUID(), expected_base_sha256: current.content_sha256,
  86  |       }),
  87  |     })
  88  |     if (!response.ok) throw new Error(`page update failed: ${response.status} ${await response.text()}`)
  89  |     return true
  90  |   }, seeded.pageId)
  91  |   expect(updated).toBe(true)
  92  |   await page.getByRole('button', { name: /会议地点/ }).last().click()
  93  |   await expect(page.getByText('引用保存的是回答当时的页面版本；该页面已更新。当前显示的是新版本，不能替代原回答依据。')).toBeVisible()
  94  |   await expect(page.getByRole('region', { name: '页面阅读' })).toBeVisible()
  95  |   await expect(page.getByText('补充说明：改在南馆。')).toBeVisible()
  96  |   expect(externalAttempts).toEqual([])
  97  |   expect(apiCalls.some(({ method, path }) => method === 'POST' && path.startsWith('/acceptance-plans'))).toBe(false)
  98  |   expect(apiCalls.some(({ method, path }) => method === 'POST' && path.startsWith('/provider-smoke/'))).toBe(false)
  99  |   writeFileSync(resolve(evidenceDir, 'frontend-c-flow-manifest.json'), JSON.stringify({ seeded, apiCalls, externalAttempts }, null, 2))
  100 |   await page.screenshot({ path: resolve(evidenceDir, 'citation-updated-page.png'), fullPage: true })
  101 | })
  102 | 
```