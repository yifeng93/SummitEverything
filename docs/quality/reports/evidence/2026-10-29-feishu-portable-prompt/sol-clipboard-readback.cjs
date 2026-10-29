const { chromium } = require('/Users/hanwenbo/ai/SummitEverything/web/node_modules/playwright')
const fs = require('node:fs')
;(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/Users/hanwenbo/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
  const context = await browser.newContext()
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://127.0.0.1:5191' })
  const page = await context.newPage()
  const consoleErrors = []
  const requests = []
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()) })
  page.on('pageerror', e => consoleErrors.push(e.message))
  await page.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (url.origin !== 'http://127.0.0.1:5191') { requests.push(url.href); return route.abort() }
    return route.continue()
  })
  await page.goto('http://127.0.0.1:5191/.local/qa/sol-portable-clipboard/index.html', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '连接飞书' }).click()
  const status = await page.getByRole('status').innerText()
  const clipboard = await page.evaluate(() => navigator.clipboard.readText())
  const checks = {
    promptPresent: clipboard.includes('请在本机为 SummitEverything'),
    sanitizedOrigin: clipboard.includes('当前应用网页 origin：http://127.0.0.1:5191') && !clipboard.includes('token=') && !clipboard.includes('#fragment'),
    apiOriginSafety: clipboard.includes('不能默认它等同于 API origin') && clipboard.includes('若证据证实同源 API 或受支持的本机代理'),
    exactForbiddenAction: clipboard.includes('不要创建任务、导入材料或确认正式知识'),
    notAlteredForbiddenAction: !clipboard.includes('不得创建任务、导入材料或确认正式知识'),
    copiedFeedback: status.includes('已复制，粘贴到 Codex / WorkBuddy'),
    noExternalRequests: requests.length === 0,
    noConsoleErrors: consoleErrors.length === 0,
  }
  fs.writeFileSync(__dirname + '/result.json', JSON.stringify({ checks, copiedLength: clipboard.length, status, consoleErrors, blockedExternalRequests: requests }, null, 2) + '\n')
  await page.screenshot({ path: __dirname + '/clipboard-readback.png', fullPage: true })
  console.log(JSON.stringify({ checks, copiedLength: clipboard.length, status, consoleErrors, blockedExternalRequests: requests }, null, 2))
  await browser.close()
  if (Object.values(checks).some(v => v !== true)) process.exitCode = 1
})().catch(error => { console.error(error.stack || error); process.exitCode = 1 })
