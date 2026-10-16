# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: source-scope.spec.ts >> Real source preview shows the exact synthetic scope before any organize call
- Location: .local/qa/frontend-b-initial/harness/source-scope.spec.ts:6:1

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  - 2
+ Received  + 2

  Object {
-   "originalText": true,
+   "originalText": false,
    "requestBudget": true,
-   "selectedProject": true,
+   "selectedProject": false,
  }
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - link "跳到主内容" [ref=e4] [cursor=pointer]:
    - /url: "#main-content"
  - complementary [ref=e5]:
    - generic [ref=e6]:
      - generic [aria-hidden] [ref=e7]: S
      - generic [ref=e8]:
        - strong [ref=e9]: SummitEverything
        - generic [ref=e10]: 个人知识工作台
    - navigation "主导航" [ref=e11]:
      - button "今日" [ref=e12] [cursor=pointer]
      - button "审批，2 项待处理" [ref=e15] [cursor=pointer]:
        - generic [ref=e17]: 审批
        - generic [ref=e18]: "2"
      - button "项目" [ref=e19] [cursor=pointer]
      - button "知识问答" [ref=e22] [cursor=pointer]
      - button "设置" [ref=e25] [cursor=pointer]
    - generic [ref=e28]:
      - button "切换工作库" [ref=e29] [cursor=pointer]:
        - generic [aria-hidden] [ref=e30]: Q
        - generic [ref=e31]:
          - strong [ref=e32]: QA 合成范围库
          - generic [ref=e33]: 切换…
      - generic [ref=e34]: 仅本机运行
  - generic [ref=e37]:
    - banner [ref=e38]:
      - generic [ref=e39]: 今日
      - generic [ref=e41]:
        - status [ref=e42]: 已保存
        - combobox "主题" [ref=e43]:
          - option "跟随系统" [selected]
          - option "浅色"
          - option "深色"
    - main [ref=e44]:
      - generic [ref=e46]:
        - generic [ref=e47]:
          - generic [ref=e48]:
            - generic [ref=e49]: 工作节奏
            - heading "今日" [level=1] [ref=e50]
            - paragraph [ref=e51]: 先看今天的安排，再把新材料放进收件箱。
          - generic [ref=e52]: 2026年10月15日星期四
        - generic [ref=e53]:
          - generic [ref=e54]:
            - generic [ref=e56]:
              - heading "会议" [level=2] [ref=e57]
              - paragraph [ref=e58]: 只读日历；刷新真实日历前会先预览并确认范围。
            - generic [ref=e59]:
              - heading "日历" [level=3] [ref=e60]
              - generic [ref=e61]:
                - generic [ref=e62]:
                  - generic [ref=e63]: 开始日期
                  - textbox "开始日期" [ref=e64]: 2026-10-15
                - generic [ref=e65]:
                  - generic [ref=e66]: 结束日期（不含）
                  - textbox "结束日期（不含）" [ref=e67]: 2026-10-16
                - generic [ref=e68]:
                  - generic [ref=e69]: 时区
                  - combobox "时区" [ref=e70]:
                    - option "Asia/Shanghai" [selected]
                    - option "UTC"
                - button "刷新日历" [disabled] [ref=e71]
              - paragraph [ref=e72]: 尚未读取日历。
            - paragraph [ref=e73]: 需要授权时，请到设置向导第 4 步处理。
          - generic [ref=e74]:
            - generic [ref=e76]:
              - heading "待办任务" [level=2] [ref=e77]
              - paragraph [ref=e78]: 任务事实来自飞书；这里仅供查看，真实任务修改请在飞书处理。
            - generic [ref=e79]:
              - button "刷新飞书任务" [ref=e81] [cursor=pointer]
              - paragraph [ref=e82]: 尚未读取任务；读取失败不表示没有任务。
            - paragraph [ref=e83]: 模拟环境中的完整动作复演可在“审批”中查看；项目进度变化仍需单独确认。
          - generic [ref=e84]:
            - generic [ref=e85]:
              - generic [ref=e86]:
                - heading "收件箱" [level=2] [ref=e87]
                - paragraph [ref=e88]: 记一句只保存原文；导入会议用于本机文件或飞书材料。两者都会先进入待整理。
              - generic [ref=e89]:
                - generic [ref=e90]: "1"
                - button "刷新收件箱" [ref=e91] [cursor=pointer]
            - generic [ref=e92]:
              - button "记一句" [ref=e93] [cursor=pointer]
              - button "导入会议" [active] [ref=e94] [cursor=pointer]
            - generic [ref=e95]: 记下一句话
            - textbox "记下一句话" [ref=e96]:
              - /placeholder: 写下一句话…
            - generic [ref=e97]:
              - button "保存到收件箱" [disabled] [ref=e98]
              - button "工作日志 / 思考" [ref=e99] [cursor=pointer]
            - paragraph [ref=e100]: 最近成功读取 17:08
            - list [ref=e101]:
              - listitem [ref=e102]:
                - generic [ref=e103] [cursor=pointer]:
                  - generic [aria-hidden] [ref=e104]: 文
                  - generic [ref=e105]:
                    - strong [ref=e106]: 快速记录
                    - generic [ref=e107]: 记一句 · 待整理
            - generic "收件箱来源分类" [ref=e108]:
              - generic [ref=e109]: 记一句 1
              - generic [ref=e110]: 本机文件 0
              - generic [ref=e111]: 飞书材料 0
              - generic [ref=e112]: 待核实 0
```

# Test source

```ts
  21  |     if (requestUrl.pathname === '/api/v1/settings' && route.request().method() === 'GET') {
  22  |       const response = await route.fetch()
  23  |       const settings = await response.json()
  24  |       return route.fulfill({ response, json: { ...settings, mode: 'real' } })
  25  |     }
  26  |     if (requestUrl.pathname === '/api/v1/acceptance-plans' && route.request().method() === 'POST') {
  27  |       previewRequest = route.request().postDataJSON()
  28  |       const requestedScope = (previewRequest as { scope: { item_ids: string[]; line_id: string; project_id: string; operation_id: string; reprocess: boolean } }).scope
  29  |       Object.assign(scope, {
  30  |         ...requestedScope,
  31  |         outgoing_inputs: [{ item_id: requestedScope.item_ids[0], source_id: 'synthetic-source', text: originalText }],
  32  |       })
  33  |       return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ plan: { plan_id: 'synthetic-plan', scope_sha256: 'synthetic-scope-hash', request_limit: 1 }, scope }) })
  34  |     }
  35  |     if (requestUrl.pathname === '/api/v1/acceptance-plans/synthetic-plan' && route.request().method() === 'DELETE') {
  36  |       return route.fulfill({ status: 204, body: '' })
  37  |     }
  38  |     if (requestUrl.pathname === '/api/v1/intake/jobs' && route.request().method() === 'POST') intakeJobWrites.push(route.request().method())
  39  |     return route.continue()
  40  |   })
  41  | 
  42  |   const workspaceRoot = testInfo.outputPath(`isolated-synthetic-workspace-${randomUUID()}`)
  43  |   mkdirSync(resolve(workspaceRoot, '..'), { recursive: true })
  44  |   await page.setViewportSize({ width: 1280, height: 900 })
  45  |   await page.goto('/')
  46  |   await page.getByLabel('工作库名称').fill('QA 合成范围库')
  47  |   await page.getByLabel('文件夹路径').fill(workspaceRoot)
  48  |   await page.getByRole('button', { name: '创建本地工作库' }).click()
  49  |   for (let step = 2; step < 5; step += 1) await page.getByRole('button', { name: '稍后再说' }).click()
  50  |   await page.getByRole('button', { name: '完成并进入今日' }).click()
  51  | 
  52  |   const seeded = await page.evaluate(async () => {
  53  |     const token = (window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__
  54  |     const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  55  |     const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: 'QA 合成主线', operation_id: crypto.randomUUID() }) })
  56  |     const line = await lineResponse.json() as { id: string }
  57  |     const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: 'QA 合成项目', operation_id: crypto.randomUUID() }) })
  58  |     const project = await projectResponse.json() as { id: string }
  59  |     return { line, project }
  60  |   })
  61  |   expect(seeded.line.id).toBeTruthy()
  62  |   await page.getByLabel('记下一句话').fill('合成原文哨兵：周五前确认测试场地与酒店，不代表真实业务材料。')
  63  |   await page.getByLabel('记下一句话').press('Enter')
  64  |   await page.getByRole('button', { name: '审批' }).click()
  65  |   const sourceGroup = page.getByRole('region', { name: /1 · 来源/ })
  66  |   await sourceGroup.getByRole('checkbox').check()
  67  |   await sourceGroup.getByRole('button', { name: /整理所选/ }).click()
  68  |   const dialog = page.getByRole('dialog', { name: '确认整理所选来源？' })
  69  |   await expect(dialog).toBeVisible()
  70  |   await dialog.getByText('查看本次范围').click()
  71  | 
  72  |   const visibleText = await dialog.innerText()
  73  |   const previewRequestScope = (previewRequest as { scope: { item_ids: string[]; line_id: string; project_id: string } }).scope
  74  |   const visibility = {
  75  |     originalText: visibleText.includes(originalText),
  76  |     selectedProject: visibleText.includes('QA 合成项目'),
  77  |     requestBudget: visibleText.includes('请求上限 1 次'),
  78  |   }
  79  |   const evidenceDir = resolve(process.cwd(), '../.local/qa/frontend-b-initial/evidence')
  80  |   mkdirSync(evidenceDir, { recursive: true })
  81  |   writeFileSync(resolve(evidenceDir, 'source-scope-dialog.txt'), visibleText)
  82  |   writeFileSync(resolve(evidenceDir, 'source-scope-request.json'), JSON.stringify({ request: previewRequest, scope }, null, 2))
  83  |   writeFileSync(resolve(evidenceDir, 'source-scope-visible-fields.json'), JSON.stringify(visibility, null, 2))
  84  |   await page.screenshot({ path: resolve(evidenceDir, 'source-scope-dialog.png'), fullPage: true })
  85  | 
  86  |   // The preview contract requires a human-readable exact original, target, and request budget.
  87  |   expect(previewRequest).toMatchObject({ operation: 'model.organize' })
  88  | 
  89  |   await dialog.getByRole('button', { name: '取消' }).click()
  90  |   expect(intakeJobWrites).toEqual([])
  91  |   expect(externalAttempts).toEqual([])
  92  |   await page.getByRole('button', { name: '今日' }).click()
  93  |   await page.getByRole('button', { name: '导入会议' }).click()
  94  |   const importDialog = page.getByRole('dialog', { name: '导入会议与材料' })
  95  |   const focusWalk: Array<Record<string, string>> = []
  96  |   for (let step = 0; step < 8; step += 1) {
  97  |     await page.keyboard.press('Tab')
  98  |     if (step === 0) await page.screenshot({ path: resolve(evidenceDir, 'import-first-file-focus.png') })
  99  |     focusWalk.push(await page.evaluate(() => {
  100 |       const el = document.activeElement as HTMLElement | null
  101 |       const style = el ? getComputedStyle(el) : null
  102 |       return {
  103 |         tag: el?.tagName ?? '',
  104 |         type: (el as HTMLInputElement | null)?.type ?? '',
  105 |         label: el?.getAttribute('aria-label') ?? el?.textContent?.trim().slice(0, 80) ?? '',
  106 |         dialogContains: String(Boolean(el && document.querySelector('[aria-label="导入会议与材料"]')?.contains(el))),
  107 |         display: style?.display ?? '',
  108 |         visibility: style?.visibility ?? '',
  109 |         clip: style?.clip ?? '',
  110 |         bounds: el ? JSON.stringify(el.getBoundingClientRect().toJSON()) : '',
  111 |       }
  112 |     }))
  113 |   }
  114 |   writeFileSync(resolve(evidenceDir, 'import-focus-walk.json'), JSON.stringify(focusWalk, null, 2))
  115 |   expect(importDialog).toBeVisible()
  116 |   await page.keyboard.press('Escape')
  117 |   await expect(importDialog).toBeHidden()
  118 |   await expect(page.getByRole('button', { name: '导入会议' })).toBeFocused()
  119 |   expect(previewRequestScope.line_id).toBe(seeded.line.id)
  120 |   expect(previewRequestScope.project_id).toBe(seeded.project.id)
> 121 |   expect(visibility).toEqual({ originalText: true, selectedProject: true, requestBudget: true })
      |                      ^ Error: expect(received).toEqual(expected) // deep equality
  122 | })
  123 | 
```