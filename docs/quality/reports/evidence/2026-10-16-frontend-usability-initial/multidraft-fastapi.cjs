const { spawn } = require('node:child_process')
const { setTimeout: sleep } = require('node:timers/promises')
const path = require('node:path')
const fs = require('node:fs')
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve('.local/qa/frontend-usability-0957/browsers')
const { chromium } = require(path.resolve('web/node_modules/playwright'))
const root = path.resolve(`.local/qa/frontend-usability-0957/multidraft-${process.pid}`)
const workspaceRoot = path.join(root, 'workspace')
const profileRoot = path.join(root, 'profile')
fs.mkdirSync(workspaceRoot, { recursive: true })
fs.mkdirSync(profileRoot, { recursive: true })
const token = `qa-multidraft-${process.pid}`
const env = { ...process.env, SUMMIT_PROFILE_ROOT: profileRoot, SUMMIT_FIRST_USE_DEFAULTS: path.resolve('web/e2e/fixtures/empty-first-use-defaults.json'), SUMMIT_SESSION_TOKEN: token, SUMMIT_API_PORT: '8795', SUMMIT_WEB_PORT: '5175', SUMMIT_OFFLINE_GUARD_ACTIVE: '1' }
const api = spawn('uv', ['--directory', '.', 'run', 'uvicorn', 'web.e2e.fixtures.fastapi_conflict_app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8795'], { cwd: process.cwd(), env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
const web = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5175'], { cwd: path.resolve('web'), env: { ...env, SUMMIT_API_TARGET: 'http://127.0.0.1:8795' }, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
let serverLog = ''
for (const child of [api, web]) { child.stdout.on('data', (b) => { serverLog += b.toString() }); child.stderr.on('data', (b) => { serverLog += b.toString() }) }
const externalAttempts = []
const writes = []
const failedResponses = []
let actualJob = null
async function waitFor(url) { for (let i = 0; i < 300; i++) { try { const r = await fetch(url); if (r.ok) return } catch {} await sleep(200) } throw new Error(`server readiness timeout: ${url}\n${serverLog}`) }
async function stop(child) { try { process.kill(-child.pid, 'SIGTERM') } catch {} }
async function main() {
  await waitFor('http://127.0.0.1:8795/api/v1/health')
  await waitFor('http://127.0.0.1:5175')
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await context.newPage(); page.setDefaultTimeout(15000)
  const consoleErrors = []
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
  page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`))
  page.on('response', async (response) => { if (response.status() >= 400) failedResponses.push({ status: response.status(), method: response.request().method(), url: response.url() }); const req = response.request(); if (req.method() === 'POST' && new URL(response.url()).pathname === '/api/v1/intake/jobs') { try { actualJob = await response.json() } catch {} } })
  page.on('request', (req) => { const u = new URL(req.url()); if (u.pathname.startsWith('/api/v1/') && req.method() !== 'GET') writes.push(`${req.method()} ${u.pathname}`) })
  page.on('requestfailed', (req) => { const u = new URL(req.url()); if (u.origin !== 'http://127.0.0.1:5175' && u.origin !== 'http://127.0.0.1:8795') externalAttempts.push(`${u.origin} ${req.failure()?.errorText}`) })
  await page.route('**/*', async (route) => { const origin = new URL(route.request().url()).origin; if (!['http://127.0.0.1:5175', 'http://127.0.0.1:8795'].includes(origin)) { externalAttempts.push(origin); return route.abort() } return route.continue() })
  await page.goto('http://127.0.0.1:5175/')
  await page.getByText('首次配置 · 第 1 步，共 5 步').waitFor()
  await page.getByLabel('工作库名称').fill('多稿独立验收库')
  await page.getByLabel('文件夹路径').fill(workspaceRoot)
  await page.getByRole('button', { name: '创建本地工作库' }).click()
  for (let step = 2; step < 5; step++) await page.getByRole('button', { name: '稍后再说' }).click()
  await page.getByRole('heading', { name: '第 5 步 · 完成' }).waitFor()
  await page.getByRole('button', { name: '完成并进入今日' }).click()
  await page.getByRole('heading', { name: '今日' }).waitFor()
  consoleErrors.length = 0
  const seeded = await page.evaluate(async () => {
    const token = window.__SUMMIT_SESSION_TOKEN__
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const lineResponse = await fetch('/api/v1/lines', { method: 'POST', headers, body: JSON.stringify({ name: '合成主线', operation_id: crypto.randomUUID() }) })
    const line = await lineResponse.json(); if (!lineResponse.ok) throw Error(JSON.stringify(line))
    const projectResponse = await fetch('/api/v1/projects', { method: 'POST', headers, body: JSON.stringify({ line_id: line.id, name: '用户选定项目', operation_id: crypto.randomUUID() }) })
    const project = await projectResponse.json(); if (!projectResponse.ok) throw Error(JSON.stringify(project))
    return { line, project }
  })
  const body = '## 预算\n\n预算上限为 100 元。\n\n## 时间\n\n计划在周五完成。\n'
  await page.getByLabel('记下一句话').fill(body)
  await page.getByRole('button', { name: '保存原文' }).click()
  await page.getByRole('button', { name: '继续整理' }).click()
  const sourceFocus = page.getByRole('region', { name: '来源详情：快速记录' })
  await sourceFocus.waitFor()
  await sourceFocus.getByRole('button', { name: /整理所选/ }).click()
  const organize = page.getByRole('dialog', { name: '确认整理所选来源？' })
  await organize.getByRole('button', { name: '确认并整理所选材料' }).click()
  const result = sourceFocus.getByRole('region', { name: '本次整理结果' })
  await result.getByText('已完成，生成 2 份待审核稿。').waitFor()
  const intake = await page.evaluate(async () => await (await fetch('/api/v1/intake/items', { headers: { Authorization: `Bearer ${window.__SUMMIT_SESSION_TOKEN__}` } })).json())
  const job = actualJob
  const jobId = job?.job_id
  if (!jobId) throw new Error(`未捕获真实POST /intake/jobs回执: ${JSON.stringify(job)}`)
  if (job.draft_ids?.length !== 2) throw new Error(`job.draft_ids应有2份: ${JSON.stringify(job)}`)
  const draftIds = [...job.draft_ids]
  await result.getByRole('button', { name: '打开这份稿件' }).first().click()
  const review = page.getByRole('region', { name: /稿件审核：/ })
  await review.waitFor()
  await review.getByLabel(/暂时未决/).check()
  await review.getByRole('button', { name: '确认并保存当前版本' }).click()
  await page.getByRole('dialog', { name: '确认并保存当前稿件版本？' }).getByRole('button', { name: '确认并保存当前版本' }).click()
  await page.getByRole('region', { name: '稿件确认结果' }).waitFor()
  const drafts = await page.evaluate(async () => await (await fetch('/api/v1/drafts', { headers: { Authorization: `Bearer ${window.__SUMMIT_SESSION_TOKEN__}` } })).json())
  const pages = await page.evaluate(async () => await (await fetch('/api/v1/pages', { headers: { Authorization: `Bearer ${window.__SUMMIT_SESSION_TOKEN__}` } })).json())
  const actions = await page.evaluate(async () => await (await fetch('/api/v1/actions', { headers: { Authorization: `Bearer ${window.__SUMMIT_SESSION_TOKEN__}` } })).json())
  const projects = await page.evaluate(async () => await (await fetch('/api/v1/projects', { headers: { Authorization: `Bearer ${window.__SUMMIT_SESSION_TOKEN__}` } })).json())
  const remaining = drafts.filter((d) => d.state === 'pending')
  if (remaining.length !== 1 || !draftIds.includes(remaining[0].draft_id)) throw new Error(`确认一份后应仅剩另一份待审核稿: ${JSON.stringify(remaining)}`)
  if (pages.filter((p) => p.approval_state === 'confirmed').length !== 1) throw new Error('确认一稿应只产生一页正式内容')
  if (actions.length !== 0) throw new Error(`Fake flow意外产生动作建议: ${JSON.stringify(actions)}`)
  if (projects[0].progress_version !== 0 || projects[0].progress) throw new Error(`项目进度被隐式修改: ${JSON.stringify(projects[0])}`)
  const taskWrites = writes.filter((w) => /\/actions\/|\/tasks/.test(w))
  if (taskWrites.length) throw new Error(`发现任务外部写请求: ${taskWrites.join(', ')}`)
  const unexpectedResponses = failedResponses.filter((r) => !(r.status === 409 && r.method === 'GET' && r.url.endsWith('/api/v1/workspaces/current')) && !(r.status === 404 && r.method === 'GET' && r.url.endsWith('/api/v1/first-use/progress')))
  if (externalAttempts.length || consoleErrors.length || unexpectedResponses.length) throw new Error(`外部请求/意外console error: ${JSON.stringify({ externalAttempts, consoleErrors, unexpectedResponses })}`)
  await page.screenshot({ path: path.join(root, 'one-confirmed-one-pending.png'), fullPage: true })
  const evidence = { workspace: workspaceRoot, lineId: seeded.line.id, projectId: seeded.project.id, jobId, jobDraftIds: draftIds, sourceItemIds: intake.map((x) => x.item_id), remainingPendingDraftIds: remaining.map((x) => x.draft_id), confirmedPageIds: pages.filter((x) => x.approval_state === 'confirmed').map((x) => x.page_id), actionCandidates: actions.length, projectProgressVersion: projects[0].progress_version, taskWrites, externalAttempts, consoleErrors, expectedEmptyWorkspaceBootstrapResponses: failedResponses, writes }
  fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify(evidence, null, 2))
  console.log(JSON.stringify(evidence, null, 2))
  await browser.close()
}
main().catch((e) => { console.error(e.stack || e); stop(api); stop(web); process.exit(1) }).finally(() => { stop(api); stop(web) })
