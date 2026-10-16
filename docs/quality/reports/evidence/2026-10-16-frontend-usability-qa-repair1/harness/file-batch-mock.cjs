const path = require('node:path')
const { chromium } = require(path.resolve('web/node_modules/playwright'))
const base = 'http://127.0.0.1:5193'
const { spawn } = require('node:child_process')
const { setTimeout: sleep } = require('node:timers/promises')
const host = spawn('npm', ['run','dev','--','--host','127.0.0.1','--port','5193'], { cwd: path.resolve('web'), stdio: ['ignore','pipe','pipe'] })
const requests = []
const sourceReads = []
const entries = []
const counts = new Map()
const definitions = {
  'good.md': { id: 'good-item-qa-1', source: 'good-source-qa-1', status: 201 },
  'failed.md': { id: 'failed-item-qa-1', source: 'failed-source-qa-1', status: 400 },
  'unknown.md': { id: 'unknown-item-qa-1', source: 'unknown-source-qa-1', status: 503 },
  'retryable.md': { id: 'retry-item-qa-1', source: 'retry-source-qa-1', status: 400, retryStatus: 201 },
  'unknown-2.md': { id: 'unknown-item-qa-2', source: 'unknown-source-qa-2', status: 503 },
}
const items = []
const baseItem = (d, name) => ({ item_id:d.id, source_id:d.source, title:name, filename:name, created_at:'2026-10-16T10:00:00+08:00', origin_kind:'file', state:'pending', attempt_no:0, revision:0 })
async function main() {
  for (let i=0;i<100;i++) { try { const r=await fetch(base); if(r.ok) break } catch {} await sleep(200) }
  const browser = await chromium.launch({headless:true})
  const page = await browser.newPage({viewport:{width:1280,height:900}})
  page.setDefaultTimeout(12000)
  const consoleErrors = [], pageErrors = [], externalAttempts = []
  page.on('console', m => { if (m.type()==='error') consoleErrors.push(m.text()) })
  page.on('pageerror', e => pageErrors.push(e.message))
  await page.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url()), method = req.method(), p = url.pathname
    if (url.origin !== base) { externalAttempts.push(url.origin); return route.abort() }
    if (!p.startsWith('/api/v1/')) return route.continue()
    if (method==='GET' && p.includes('/sources/')) sourceReads.push(p.split('/').pop())
    let body = {}, status = 200
    if (p.endsWith('/workspaces/current')) body = {workspace_id:'qa-workspace',name:'批次验收库',root:'/tmp/qa',local_profile_dir:'/tmp/qa-profile'}
    else if (p.endsWith('/first-use/progress') && method==='GET') body = {step:2,completed:true,open:false}
    else if (p.endsWith('/first-use/progress')) body = {step:2,completed:true,open:false}
    else if (p.endsWith('/action-intents')) body = process.env.QA_BAD_INTENTS_SHAPE==='1' ? [] : {items:[],next_cursor:null}
    else if (p.endsWith('/actions')) body = []
    else if (p.endsWith('/projects')) body = []
    else if (p.endsWith('/intake/items') && method==='GET') body = items
    else if (p.endsWith('/index/status')) body = {fingerprint:'qa',pages:0,chunks:0,state:'not_ready',current_pages:0,stale_pages:0}
    else if (p.endsWith('/lines')) body = []
    else if (p.endsWith('/pages')) body = []
    else if (p.includes('/sources/')) {
      const id = p.split('/').pop(), found = items.find(x=>x.source_id===id)
      body = found ? {source:{source_id:found.source_id,filename:found.filename,origin_kind:'file'},text:`合成原文 ${found.filename}`} : {error:{message:'missing'}}
      if (!found) status=404
    } else if (p.endsWith('/intake/files') && method==='POST') {
      const form = await req.postDataBuffer()
      const text = form.toString('latin1')
      const match = text.match(/filename="([^"]+)"/)
      const name = match?.[1] || 'unknown-file.md'
      const d = definitions[name] || {id:`${name}-item`,source:`${name}-source`,status:500}
      const n = (counts.get(name)||0)+1; counts.set(name,n)
      const effective = n>1 && d.retryStatus ? d.retryStatus : d.status
      requests.push({method,path:p,name,status:effective,attempt:n})
      status=effective
      if (status<400) { const item=baseItem(d,name); items.push(item); body=item }
      else body={error:{message:status===503?'upstream result unavailable':'明确拒绝该文件'}}
    } else { requests.push({method,path:p,status}); body = [] }
    return route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
  })
  await page.goto(base)
  await page.getByRole('button',{name:'今日',exact:true}).click(); await page.getByRole('heading',{name:'今日'}).waitFor()
  if (process.env.QA_BAD_INTENTS_SHAPE==='1') { await page.waitForTimeout(500); console.log(JSON.stringify({diagnostic:'intentionally malformed ActionPage fixture',pageErrors,consoleErrors},null,2)); await browser.close(); return }
  async function openImport() { await page.getByRole('button',{name:'导入材料'}).click(); return page.getByRole('dialog',{name:'导入材料'}) }
  async function uploadBatch(dialog,names) {
    await dialog.getByLabel('选择多个文件').setInputFiles(names.map(name=>({name,mimeType:'text/markdown',buffer:Buffer.from(`# ${name}\n合成内容`)})))
    await dialog.getByRole('button',{name:'导入可用文件'}).click()
  }
  let dialog=await openImport()
  await uploadBatch(dialog,['good.md','failed.md','unknown.md'])
  await dialog.getByText('已导入').waitFor()
  await dialog.getByText('导入失败').waitFor()
  await dialog.getByText('结果未知').waitFor()
  if ((counts.get('unknown.md')||0)!==1) throw Error('unknown.md first batch request count not 1')
  await dialog.getByRole('button',{name:'关闭'}).click()
  await page.getByRole('button',{name:'继续整理'}).click()
  await page.getByRole('region',{name:/来源详情/}).waitFor()
  const checked = await page.locator('input[type=checkbox]:checked').evaluateAll(xs=>xs.map(x=>x.value || x.getAttribute('aria-label') || x.closest('label')?.innerText || 'checked'))
  const sourceTexts = await page.getByRole('region',{name:/来源详情/}).innerText()
  if (!sourceReads.includes('good-source-qa-1') || sourceReads.some(id=>['failed-source-qa-1','unknown-source-qa-1'].includes(id))) throw Error(`source fetch IDs mismatch: ${JSON.stringify(sourceReads)}`)
  if (!sourceTexts.includes('good.md')) throw Error(`continue did not target successful file: ${sourceTexts}`)
  if (sourceTexts.includes('failed.md') || sourceTexts.includes('unknown.md')) throw Error(`continue included non-success files: ${sourceTexts}`)
  await page.getByRole('button',{name:'返回审批清单'}).click().catch(async()=>await page.getByRole('button',{name:/返回清单/}).click())
  await page.getByRole('button',{name:'今日',exact:true}).click(); await page.getByRole('heading',{name:'今日'}).waitFor()
  dialog=await openImport()
  await uploadBatch(dialog,['retryable.md','unknown-2.md'])
  await dialog.getByText('导入失败').waitFor()
  await dialog.getByText('结果未知').waitFor()
  await dialog.getByRole('button',{name:'重试失败项'}).click()
  await dialog.getByText('已导入').waitFor()
  if ((counts.get('retryable.md')||0)!==2) throw Error(`explicit failed-item retry expected 2, got ${counts.get('retryable.md')}`)
  if ((counts.get('unknown-2.md')||0)!==1) throw Error(`unknown item was automatically/repeatedly posted: ${counts.get('unknown-2.md')}`)
  await dialog.getByRole('button',{name:'关闭'}).click()
  await page.getByRole('button',{name:'继续整理'}).click()
  await page.getByRole('region',{name:/来源详情/}).waitFor()
  const secondText=await page.getByRole('region',{name:/来源详情/}).innerText()
  if (!sourceReads.includes('retry-source-qa-1') || sourceReads.includes('unknown-source-qa-2')) throw Error(`second source fetch IDs mismatch: ${JSON.stringify(sourceReads)}`)
  if (!secondText.includes('retryable.md') || secondText.includes('unknown-2.md')) throw Error(`retry receipt target mismatch: ${secondText}`)
  if (externalAttempts.length || pageErrors.length) throw Error(JSON.stringify({externalAttempts,pageErrors}))
  const manifest={requests,counts:Object.fromEntries(counts),items:items.map(x=>({item_id:x.item_id,source_id:x.source_id,filename:x.filename})),firstContinueSource:sourceTexts,secondContinueSource:secondText,sourceReads,checked,externalAttempts,pageErrors,consoleErrors}
  const fs=require('node:fs'); const out=path.resolve('.local/qa/frontend-usability-d9f49c1/evidence/batch')
  fs.mkdirSync(out,{recursive:true})
  fs.writeFileSync(path.join(out,'file-batch-mock-manifest.json'),JSON.stringify(manifest,null,2))
  await page.screenshot({path:path.join(out,'file-batch-mock-final.png'),fullPage:true})
  console.log(JSON.stringify(manifest,null,2))
  await browser.close()
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1}).finally(()=>host.kill('SIGTERM'))
