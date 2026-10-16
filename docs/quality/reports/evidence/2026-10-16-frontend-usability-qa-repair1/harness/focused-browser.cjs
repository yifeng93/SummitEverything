const { spawn } = require('node:child_process')
const { setTimeout: sleep } = require('node:timers/promises')
const path = require('node:path')
const { chromium } = require(path.resolve('web/node_modules/playwright'))
const webRoot = path.resolve(process.env.QA_WEB_ROOT || 'web')
const port = process.env.QA_PORT || '5192'
const base = `http://127.0.0.1:${port}`
const host = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', port], { cwd: webRoot, stdio: ['ignore', 'pipe', 'pipe'] })
let hostOutput = ''
host.stdout.on('data', (b) => { hostOutput += b.toString() })
host.stderr.on('data', (b) => { hostOutput += b.toString() })
const apiRequests = []
const externalAttempts = []
const consoleErrors = []
const note = { item_id: 'qa-returned-item-7f1', source_id: 'qa-returned-source-7f1', title: '同名快速记录', filename: '快速记录.md', created_at: '2026-10-16T10:00:00+08:00', origin_kind: 'quick_note', state: 'pending', attempt_no: 0, revision: 0 }
const sources = [
  { ...note, item_id: 'qa-old-item-0', source_id: 'qa-old-source-0', created_at: '2026-10-15T10:00:00+08:00' },
  note,
]
const page = { page_id: 'qa-confirmed-page', relative_path: '项目/正式页.md', metadata: { id: 'qa-confirmed-page', title: '已确认正式页', role: 'knowledge', kind: 'topic', line_id: 'qa-line', project_id: 'qa-project' }, body: '# 已确认内容\n\n仅用于首次索引待办复核。', content_sha256: 'c'.repeat(64), raw_sha256: 'd'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
const draft = { draft_id: 'qa-draft-1', input_ids: ['qa-source'], target_page_id: null, metadata: { id: 'qa-draft-1', title: '冲突稿件', role: 'knowledge', kind: 'topic', line_id: 'qa-line', project_id: 'qa-project' }, body: '# 冲突稿件\n\n**排版正文**。', expected_base_sha256: null, important_conflicts: [{ id: 'meeting-date', question: '会议日期是否已确认？', alternatives: ['已确认', '仍待确认'] }], action_suggestions: [], conflict_resolutions: {}, source_ids: ['qa-returned-source-7f1'], state: 'pending', created_at: '2026-10-16T10:00:00+08:00', version: 1 }
let currentDraft = draft
let patchPayload = null
let confirmationPayload = null
const settings = { mode: 'fake', model_studio_account_id: 'synthetic', feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false }, llm: { provider: 'fake', model: null, account_id: 'synthetic', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' }, embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/embedding', enabled: false }, rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/rerank', enabled: false }, capabilities: {}, credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: false, embedding_fingerprint: 'qa-fingerprint' }
async function main() {
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(base); if (r.ok) break } catch {}
    await sleep(200)
  }
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const p = await context.newPage()
  p.setDefaultTimeout(5000)
  p.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()) })
  p.on('pageerror', (error) => consoleErrors.push(`pageerror: ${error.message}`))
  await p.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== base) { externalAttempts.push(url.origin); return route.abort() }
    if (!url.pathname.startsWith('/api/v1/')) return route.continue()
    apiRequests.push(`${route.request().method()} ${url.pathname}`)
    const method = route.request().method()
    const pathName = url.pathname
    let body = []
    if (pathName.endsWith('/workspaces/current')) body = { workspace_id: 'qa-workspace', name: '隔离验收库', root: '/tmp/qa-workspace', local_profile_dir: '/tmp/qa-profile' }
    else if (pathName.endsWith('/first-use/progress') && method === 'GET') body = { step: 5, completed: true, open: false }
    else if (pathName.endsWith('/first-use/progress')) body = route.request().postDataJSON()
    else if (pathName.endsWith('/settings')) body = settings
    else if (pathName.endsWith('/intake/items') && method === 'POST') body = note
    else if (pathName.endsWith('/intake/items')) body = sources
    else if (pathName.endsWith('/sources/qa-returned-source-7f1')) body = { source: { source_id: note.source_id, filename: note.filename, origin_kind: 'quick_note' }, text: '唯一返回ID所指向的合成原文。' }
    else if (pathName.endsWith('/sources/qa-old-source-0')) body = { source: { source_id: 'qa-old-source-0', filename: note.filename, origin_kind: 'quick_note' }, text: '旧同名项，不应被新回执选中。' }
    else if (pathName.endsWith('/drafts/qa-draft-1/confirmations')) { confirmationPayload = route.request().postDataJSON(); body = { page_versions: { 'qa-saved-page': 'e'.repeat(64) }, index_update: 'not_enabled' } }
    else if (pathName.endsWith('/drafts/qa-draft-1') && method === 'PATCH') { patchPayload = route.request().postDataJSON(); currentDraft = { ...currentDraft, body: patchPayload.body, version: 2 }; body = currentDraft }
    else if (pathName.endsWith('/drafts')) body = [currentDraft]
    else if (pathName.endsWith('/pages')) body = [page]
    else if (pathName.endsWith('/index/status')) body = { fingerprint: 'qa-fingerprint', pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 }
    else if (pathName.endsWith('/actions')) body = []
    else if (pathName.endsWith('/action-intents')) body = { items: [], next_cursor: null }
    else if (pathName.endsWith('/integrations/feishu/calendar')) body = { items: [], next_cursor: null, truncated: false }
    else if (pathName.endsWith('/integrations/feishu/tasks')) body = { items: [], next_cursor: null }
    else if (pathName.endsWith('/integrations/feishu/status')) body = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
    else if (pathName.endsWith('/projects')) body = []
    else if (pathName.endsWith('/lines')) body = []
    else body = {}
    return route.fulfill({ status: method === 'POST' && pathName.endsWith('/intake/items') ? 201 : 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await p.goto(base)
  await p.getByRole('heading', { name: '今日' }).waitFor()
  await p.getByLabel('记下一句话').fill('核对回执定位；不触发模型。')
  await p.getByRole('button', { name: '保存原文' }).click()
  await p.getByRole('button', { name: '继续整理' }).waitFor()
  await p.getByRole('button', { name: '继续整理' }).click()
  await p.getByRole('region', { name: '来源详情：同名快速记录' }).waitFor()
  if (!apiRequests.includes('GET /api/v1/sources/qa-returned-source-7f1')) throw new Error('未按POST返回的source_id读取详情')
  if (apiRequests.includes('GET /api/v1/sources/qa-old-source-0')) throw new Error('误按同名旧记录寻址')
  const focus = p.getByRole('region', { name: '来源详情：同名快速记录' })
  if (!(await focus.getByText('唯一返回ID所指向的合成原文。').isVisible())) throw new Error('返回ID对应原文没有展示')
  await focus.getByRole('button', { name: '返回审批清单' }).click()
  const oldRow = p.locator('[data-item-id="qa-old-item-0"]')
  const newRow = p.locator('[data-item-id="qa-returned-item-7f1"]')
  if (!(await newRow.locator('input[type=checkbox]').isChecked())) throw new Error('精确返回ID未被选中')
  if (await oldRow.locator('input[type=checkbox]').isChecked()) throw new Error('同名旧材料被错误选中')
  const indexGroup = p.locator('#approval-index')
  await indexGroup.waitFor()
  if (!(await indexGroup.locator('summary').getAttribute('aria-expanded') === null)) { /* native details has no aria-expanded */ }
  if (!(await indexGroup.getAttribute('open')) && (await indexGroup.getAttribute('open')) !== '') throw new Error('存在已确认页面且not_ready但首次索引组未展开')
  if (await indexGroup.locator('.count-badge').innerText() !== '1') throw new Error('pages=0时已有confirmed页面未计首次索引待办')
  const draftRow = p.locator('[data-draft-id=\"qa-draft-1\"]')
  await draftRow.getByRole('button', { name: '打开稿件：冲突稿件' }).click()
  const draftFocus = p.getByRole('region', { name: '稿件审核：冲突稿件' })
  await draftFocus.getByText('排版正文。', { exact: true }).waitFor()
  if (await draftFocus.locator('.draft-reading-body').innerText() === '# 冲突稿件\n\n**排版正文**。') throw new Error('正文未按Markdown排版渲染')
  await draftFocus.locator('.conflict-item input[type=radio]').first().check()
  await draftFocus.getByText('冲突选择尚未提交，将在确认时生效。').waitFor()
  const navDialog = p.waitForEvent('dialog')
  const navClick = p.getByRole('button', { name: '项目' }).click()
  const pendingNav = await navDialog
  if (!pendingNav.message().includes('未保存')) throw new Error('冲突选择没有触发离开保护')
  await pendingNav.dismiss()
  await navClick
  if (!(await draftFocus.locator('.conflict-item input[type=radio]').first().isChecked())) throw new Error('取消离开后冲突选择丢失')
  await draftFocus.locator('details.draft-edit-details > summary').click()
  await draftFocus.getByLabel('正文').fill('# 冲突稿件\n\n修改后的排版正文。')
  await draftFocus.getByRole('button', { name: '保存修改' }).click()
  await p.waitForFunction(() => document.querySelector('.draft-review')?.textContent?.includes('冲突选择尚未提交，将在确认时生效。'))
  if (!patchPayload || Object.hasOwn(patchPayload, 'conflict_resolutions')) throw new Error('正文PATCH错误地持久化冲突选择')
  await draftFocus.getByRole('button', { name: '确认并保存当前版本' }).click()
  await p.getByRole('dialog', { name: '确认并保存当前稿件版本？' }).getByRole('button', { name: '确认并保存当前版本' }).click()
  const confirmationResult = p.getByRole('region', { name: '稿件确认结果' })
  await confirmationResult.waitFor()
  await confirmationResult.getByText(/首次索引仍需你在知识问答中确认/).waitFor()
  if (confirmationPayload?.conflict_resolutions?.['meeting-date'] !== '已确认') throw new Error('最终稿件确认没有携带选择的冲突结果')
  if (!apiRequests.includes('PATCH /api/v1/drafts/qa-draft-1')) throw new Error('没有观察到正文PATCH')
  if (!apiRequests.includes('POST /api/v1/drafts/qa-draft-1/confirmations')) throw new Error('没有观察到独立稿件确认请求')
  const forbidden = apiRequests.filter((x) => /acceptance-plans|intake\/jobs|index\/jobs|providers|real-data/.test(x))
  if (forbidden.length) throw new Error(`保存/导航隐式调用风险: ${forbidden.join(', ')}`)
  await p.screenshot({ path: path.resolve('.local/qa/frontend-usability-d9f49c1/evidence/focused/focused-exact-id-initial-index.png'), fullPage: true })
  const result = { viewport: { width: 1280, height: 800 }, conflictSelection: { patchHasConflictResolutions: Object.hasOwn(patchPayload ?? {}, 'conflict_resolutions'), finalConfirmationChoice: confirmationPayload?.conflict_resolutions?.['meeting-date'], dirtyLeaveCancelledPreserved: true }, savedReturnedItemId: note.item_id, fetchedSourceId: 'qa-returned-source-7f1', duplicateTitleOldItemSelected: await oldRow.locator('input[type=checkbox]').isChecked(), returnedItemSelected: await newRow.locator('input[type=checkbox]').isChecked(), indexStatusPages: 0, confirmedPages: 1, firstIndexCount: await indexGroup.locator('.count-badge').innerText(), apiRequests, externalAttempts, consoleErrors }
  require('node:fs').writeFileSync('.local/qa/frontend-usability-d9f49c1/evidence/focused/focused-browser-manifest.json', JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result, null, 2))
  await browser.close()
}
main().catch((error) => { console.error(error.stack || error); host.kill('SIGTERM'); process.exit(1) }).finally(() => { host.kill('SIGTERM') })
