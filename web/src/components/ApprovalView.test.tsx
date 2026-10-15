import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ApprovalView } from './ApprovalView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const source = { item_id: 'source-1', source_id: 'source-1', origin_kind: 'quick_note', title: '合成速记', filename: '随手记.md', original_relative_path: '原件/secret-path.md', created_at: '2026-10-14T00:00:00Z', state: 'pending' }
const draft = { draft_id: 'draft-1', input_ids: [], target_page_id: null, metadata: { title: '合成稿件' }, body: '# 稿件正文', source_ids: ['source-1'], important_conflicts: [], state: 'pending', created_at: '2026-10-14T00:00:00Z', version: 1 }
const page = { page_id: 'page-1', relative_path: '项目/页面.md', metadata: { id: 'page-1', title: '正式页', kind: 'decision' }, body: '当前正式正文 **内容**', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'pending', validity: 'current' }
const candidate = { action_id: 'candidate-1', kind: 'todo', description: '合成任务建议', related_project_id: null, state: 'proposed', source_draft_id: 'draft-1', created_at: '2026-10-14T00:00:00Z' }
const intent = { action_id: 'action-1', kind: 'project_progress', payload: { progress: '合成' }, payload_sha256: 'b'.repeat(64), state: 'proposed', confirmation_id: null, created_at: '2026-10-14T00:00:00Z' }

function setup(overrides: Record<string, unknown> = {}) {
  const calls: Array<{ path: string; method: string; body?: Record<string, unknown> }> = []
  const onError = vi.fn()
  const responses: Record<string, unknown> = {
    '/api/v1/intake/items': [source], '/api/v1/drafts': [draft], '/api/v1/pages': [page],
    '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 0, current_pages: 0, stale_pages: 1 },
    '/api/v1/actions': [candidate], '/api/v1/action-intents?limit=20': { items: [intent], next_cursor: null },
    '/api/v1/projects': [],
    '/api/v1/settings': { mode: 'fake', embedding_fingerprint: 'fake-fingerprint' },
    ...overrides,
  }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('http://localhost', '')
    const method = init?.method ?? 'GET'
    calls.push({ path, method, ...(init?.body ? { body: JSON.parse(String(init.body)) as Record<string, unknown> } : {}) })
    const value = responses[path]
    if (value instanceof Error) return Response.json({ error: { message: value.message } }, { status: 503 })
    if (path.endsWith('/confirmations') && method === 'POST') return Response.json({ state: 'succeeded', index_update: 'updated' })
    if (path.endsWith('/acceptance-plans') && method === 'POST') return Response.json({ plan: { plan_id: 'plan-1', scope_sha256: 'scope', request_limit: 2 }, scope: {} })
    if (path.includes('/acceptance-plans/') && path.endsWith('/confirm')) return Response.json({})
    if (path.endsWith('/index/plans') && method === 'POST') return Response.json({ plan_id: 'index-1', workspace_id: 'workspace', mode: 'initial', fingerprint: 'fake-fingerprint', page_ids: ['page-1'], page_versions: { 'page-1': 'hash' }, estimated_tokens: 12, estimated_cost: 0, page_preview: [{ title: '正式页', version: 'v1' }] })
    if (path.endsWith('/index/jobs') && method === 'POST') return Response.json({ indexed_pages: 1, indexed_chunks: 1, embedded_chunks: 0, reused_chunks: 1, active_fingerprint: 'fake-fingerprint' })
    if (path.includes('/actions/') && path.endsWith('/confirmations')) return Response.json({ ...intent, state: 'confirmed' })
    return Response.json(value ?? {})
  }))
  const onPendingCount = vi.fn()
  render(<ApprovalView onPendingCount={onPendingCount} onError={onError} />)
  return { calls, onPendingCount, onError }
}

it('五类固定顺序独立读取，局部失败不会把其他分组画成空态', async () => {
  setup({ '/api/v1/pages': new Error('本地读取暂不可用') })
  await screen.findByText('合成速记')
  const headings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
  expect(headings.filter((heading) => /[1-5] ·/.test(heading ?? ''))).toEqual(['1 · 来源', '2 · 稿件', '3 · 正式内容', '4 · 索引', '5 · 外部动作'])
  expect(screen.getByText('合成速记').closest('label')?.textContent).toContain('记一句')
  expect(screen.getByText('合成稿件')).toBeTruthy()
  expect(screen.getByRole('alert').textContent).toContain('本地读取暂不可用')
  expect(screen.getByText('当前状态：尚未建立')).toBeTruthy()
})

it('来源尚未读取时显示加载而非空态，成功读取后才显示空态', async () => {
  let finishRead: ((response: Response) => void) | undefined
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).replace('http://localhost', '')
    if (path === '/api/v1/intake/items') return await new Promise<Response>((resolve) => { finishRead = resolve })
    if (path === '/api/v1/index/status') return Response.json({ state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 })
    if (path === '/api/v1/action-intents?limit=20') return Response.json({ items: [], next_cursor: null })
    if (path === '/api/v1/settings') return Response.json({ mode: 'fake', embedding_fingerprint: null })
    return Response.json([])
  }))
  render(<ApprovalView onPendingCount={vi.fn()} onError={vi.fn()} />)
  const sourceGroup = screen.getByRole('region', { name: /1 · 来源/ })
  expect(within(sourceGroup).getByRole('status').textContent).toContain('正在读取')
  expect(within(sourceGroup).queryByText('没有待整理的来源')).toBeNull()
  finishRead?.(Response.json([]))
  expect(await within(sourceGroup).findByText('没有待整理的来源')).toBeTruthy()
})

it('审批业务正文不暴露来源ID、文件路径、hash或原始JSON', async () => {
  setup()
  await screen.findByText('合成速记')
  const visible = document.querySelector('.approval-view')?.textContent ?? ''
  expect(visible).toContain('合成速记')
  expect(visible).not.toContain('source-1')
  expect(visible).not.toContain('原件/secret-path.md')
  expect(visible).not.toMatch(/[a-f0-9]{64}/)
  expect(visible).not.toMatch(/\{\s*"(?:item_id|source_id|page_id)"\s*:/)
})

it('来源归属下拉显示中文名称，内部英文ID不进入业务文案或tooltip', async () => {
  setup({
    '/api/v1/lines': [{ id: 'huoman-logistics', name: '中文主线' }],
    '/api/v1/projects': [{ id: 'project-internal-42', name: '中文项目', line_id: 'huoman-logistics', archived: false }],
  })
  await screen.findByText('合成速记')
  fireEvent.click(within(screen.getByRole('region', { name: /1 · 来源/ })).getByRole('checkbox'))
  const line = await screen.findByRole('option', { name: '中文主线' })
  const projectOption = await screen.findByRole('option', { name: '中文项目' })
  expect(line.getAttribute('value')).toBe('huoman-logistics')
  expect(projectOption.getAttribute('value')).toBe('project-internal-42')
  expect(line.getAttribute('title')).toBeNull()
  expect(projectOption.getAttribute('title')).toBeNull()
  expect(line.textContent).not.toContain('huoman-logistics')
  expect(projectOption.textContent).not.toContain('project-internal-42')
})

it('顶部检查并应用只汇总已选类别，不写入、不确认，也不建计划', async () => {
  const { calls } = setup()
  await screen.findByText('正式页')
  const formal = screen.getByRole('region', { name: /3 · 正式内容/ })
  fireEvent.click(within(formal).getByRole('checkbox'))
  fireEvent.click(screen.getByRole('checkbox', { name: '选择索引事项进行检查' }))
  fireEvent.click(screen.getByRole('button', { name: /检查并应用/ }))
  expect(screen.getByRole('dialog').textContent).toContain('正式内容：1 项')
  expect(screen.getByRole('dialog').textContent).toContain('索引：1 项')
  expect(calls.filter(({ method }) => method === 'POST')).toHaveLength(0)
})

it('检查并应用弹窗捕获 Tab、Escape 关闭并归还焦点', async () => {
  setup()
  await screen.findByText('正式页')
  fireEvent.click(within(screen.getByRole('region', { name: /3 · 正式内容/ })).getByRole('checkbox'))
  const trigger = screen.getByRole('button', { name: /检查并应用/ })
  trigger.focus()
  fireEvent.click(trigger)
  const dialog = screen.getByRole('dialog', { name: '检查所选事项' })
  const first = within(dialog).getByRole('button', { name: '去查看' })
  first.focus()
  fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })
  expect(document.activeElement).toBe(within(dialog).getByRole('button', { name: '完成检查' }))
  fireEvent.keyDown(dialog, { key: 'Escape' })
  await waitFor(() => expect(screen.queryByRole('dialog', { name: '检查所选事项' })).toBeNull())
  expect(document.activeElement).toBe(trigger)
})

it('正式页面点击确认前先预览，确认后原子保存当前metadata/body/hash', async () => {
  const { calls } = setup()
  await screen.findByText('正式页')
  fireEvent.click(within(screen.getByRole('region', { name: /3 · 正式内容/ })).getByRole('button', { name: '确认并保存当前版本' }))
  expect(screen.getByRole('dialog').textContent).toContain('不会创建飞书任务')
  expect(calls.some(({ path }) => path.endsWith('/confirmations'))).toBe(false)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '取消' }))
  expect(calls.some(({ path }) => path.endsWith('/confirmations'))).toBe(false)
  fireEvent.click(within(screen.getByRole('region', { name: /3 · 正式内容/ })).getByRole('button', { name: '确认并保存当前版本' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '确认并保存当前版本' }))
  await waitFor(() => expect(calls.some(({ path, method }) => path.endsWith('/pages/page-1/confirmations') && method === 'POST')).toBe(true))
  const request = calls.find(({ path }) => path.endsWith('/pages/page-1/confirmations'))
  expect(calls.filter(({ path, method }) => path.endsWith('/pages/page-1/confirmations') && method === 'POST')).toHaveLength(1)
  expect(request?.body).toMatchObject({ metadata: page.metadata, body: page.body, expected_base_sha256: page.content_sha256 })
})

it('索引计划需要自己的范围预览确认；action未知时仅提供核对', async () => {
  const { calls } = setup({ '/api/v1/action-intents?limit=20': { items: [{ ...intent, state: 'unknown' }], next_cursor: null } })
  await screen.findByText('合成速记')
  fireEvent.click(screen.getByRole('button', { name: '预览首次索引' }))
  await screen.findByText(/本次范围：1 页/)
  fireEvent.click(screen.getByRole('button', { name: '查看范围并确认' }))
  expect(screen.getByRole('dialog').textContent).toContain('Fake 模式仅使用本机合成索引')
  expect(calls.some(({ path }) => path.endsWith('/index/jobs'))).toBe(false)
  expect(screen.getByText('结果未知，请核对')).toBeTruthy()
})

it('Real 索引授权预览失败时清除旧计划且不开放确认或发起索引', async () => {
  const { calls, onError } = setup({ '/api/v1/settings': { mode: 'real', embedding_fingerprint: 'real-fingerprint' }, '/api/v1/acceptance-plans': new Error('授权预览失败') })
  await screen.findByText('合成速记')
  const preview = screen.getByRole('button', { name: '预览首次索引' })
  await waitFor(() => expect(preview).toHaveProperty('disabled', false))
  fireEvent.click(preview)
  await waitFor(() => expect(onError).toHaveBeenCalledWith('授权预览失败'))
  expect(screen.queryByText(/本次范围：/)).toBeNull()
  expect(screen.queryByRole('button', { name: '查看范围并确认' })).toBeNull()
  expect(calls.some(({ path }) => path.endsWith('/index/jobs') || path.endsWith('/confirm'))).toBe(false)
})
