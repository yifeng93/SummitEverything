import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs'
import assert from 'node:assert/strict'

const base = 'http://127.0.0.1:5194'
const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
let currentScenario = 'success-ready'
const localReady = { model: 'BAAI/bge-small-zh-v1.5', revision: '46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59', dimensions: 512, token_limit: 512, download_size_bytes: 95330972, state: 'ready', downloaded_bytes: 95330972, progress_percent: 100, error_code: null }
function settingsFor() {
  const ready = currentScenario !== 'success-unprepared'
  const enabled = currentScenario !== 'success-disabled'
  const available = ready && enabled
  return {
    mode: 'real', model_studio_account_id: 'synthetic-account',
    feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '' },
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'synthetic-account', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
    embedding: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', base_url: null, dimensions: 512, enabled },
    rerank: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', base_url: null, dimensions: 512, enabled },
    capabilities: {
      llm: { available: false, configured: true, disabled_reason: 'acceptance_plan_required' },
      embedding: { available, configured: ready, disabled_reason: !ready ? 'local_model_not_prepared' : enabled ? null : 'local_provider_disabled' },
      rerank: { available, configured: ready, disabled_reason: !ready ? 'local_model_not_prepared' : enabled ? null : 'local_provider_disabled' },
      feishu_material_read: { available: false, configured: false, disabled_reason: 'provider_not_configured' },
      feishu_calendar_read: { available: false, configured: false, disabled_reason: 'provider_not_configured' },
      feishu_task_read: { available: false, configured: false, disabled_reason: 'provider_not_configured' },
      feishu_task_write: { available: false, configured: false, disabled_reason: 'result_proof_unavailable' },
    },
    credential_status: { feishu_app: false, deepseek: true, dashscope: false },
    keychain_available: true, embedding_fingerprint: 'synthetic-fingerprint',
    model_call_status: { state: 'succeeded', has_success: true, last_attempt_at: '2026-10-30T05:00:00Z', last_success_at: '2026-10-30T05:00:00Z' },
    local_model: currentScenario === 'success-unprepared' ? { ...localReady, state: 'not_prepared', downloaded_bytes: 0, progress_percent: 0 } : localReady,
    legacy_provider_migration_required: false, feishu_calendar_ready: false,
  }
}
await ctx.route('**/api/v1/**', async (route) => {
  const url = new URL(route.request().url())
  const p = url.pathname.replace('/api/v1', '')
  let payload = {}
  let status = 200
  if (p === '/workspaces/current') payload = { workspace_id: '00000000-0000-4000-8000-000000000001', root: '/synthetic/workspace', local_profile_dir: '/synthetic/profile', name: '合成验收库', read_only: false }
  else if (p === '/first-use/progress') { status = 404; payload = { error: { code: 'first_use_progress_absent', message: 'absent' } } }
  else if (p === '/settings') payload = settingsFor()
  else if (p === '/provider-smoke') payload = { counts: { deepseek_chat: 1, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 0, model_studio_embedding: 1, model_studio_rerank: 1 } }
  else if (p === '/integrations/feishu/status') payload = { mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false }
  else if (p === '/projects' || p === '/today/summary' || p === '/approvals/count') payload = []
  else if (p === '/index/status') payload = { state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0, vector: 'unknown' }
  else payload = []
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(payload) })
})
async function openSettings(page) {
  await page.goto(base)
  await page.getByText('合成验收库', { exact: true }).waitFor({ state: 'visible' })
  console.log('SHELL_BODY=' + (await page.locator('body').innerText()).slice(0, 900))
  console.log('BUTTONS=' + JSON.stringify(await page.getByRole('button').allTextContents()))
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      await page.getByRole('button', { name: '设置', exact: true }).click({ timeout: 3000 })
      break
    } catch (error) {
      if (attempt === 3) throw error
      await page.waitForTimeout(250)
    }
  }
  const card = page.getByRole('region', { name: 'AI 模型' })
  await card.waitFor({ state: 'visible' })
  return card
}
try {
  let page = await ctx.newPage()
  currentScenario = 'success-ready'
  let card = await openSettings(page)
  await card.getByText('已就绪', { exact: true }).waitFor()
  await card.getByText('最近调用成功', { exact: true }).waitFor()
  await page.screenshot({ path: '.local/qa/model-status/browser-success-ready.png', fullPage: true })
  await page.reload()
  await page.getByRole('button', { name: '设置', exact: true }).click()
  card = page.getByRole('region', { name: 'AI 模型' })
  await card.getByText('已就绪', { exact: true }).waitFor()
  await page.close()
  page = await ctx.newPage()
  card = await openSettings(page)
  await card.getByText('已就绪', { exact: true }).waitFor()
  console.log('PASS success state persists after reload and page reopen')
  await page.close()

  currentScenario = 'success-unprepared'
  page = await ctx.newPage()
  card = await openSettings(page)
  await card.getByText('DeepSeek 最近调用成功', { exact: true }).waitFor()
  assert.equal(await card.getByText('已就绪', { exact: true }).count(), 0)
  assert.equal(await card.getByText('本机模型未准备', { exact: true }).count(), 2)
  await page.screenshot({ path: '.local/qa/model-status/browser-unprepared.png', fullPage: true })
  console.log('PASS local model not prepared does not show ready/available')
  await page.close()

  currentScenario = 'success-disabled'
  page = await ctx.newPage()
  card = await openSettings(page)
  await card.getByText('DeepSeek 最近调用成功', { exact: true }).waitFor()
  assert.equal(await card.getByText('本机可用', { exact: true }).count(), 0)
  assert.equal(await card.getByText('已配置，未启用', { exact: true }).count(), 2)
  console.log('PASS disabled local capabilities do not show available')
  await page.screenshot({ path: '.local/qa/model-status/browser-disabled.png', fullPage: true })
  console.log('BROWSER_QA_EXIT=0')
} catch (error) {
  console.error(error)
  console.log('BROWSER_QA_EXIT=1')
  process.exitCode = 1
} finally {
  await ctx.close()
  await browser.close()
}
