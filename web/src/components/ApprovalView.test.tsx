import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ApprovalView } from './ApprovalView'
import type { ApprovalTarget } from '../approvalTarget'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const source = { item_id: 'source-1', source_id: 'source-1', origin_kind: 'quick_note', title: '合成速记', filename: '随手记.md', original_relative_path: '原件/secret-path.md', created_at: '2026-10-14T00:00:00Z', state: 'pending' }
const draft = { draft_id: 'draft-1', input_ids: [], target_page_id: null, metadata: { title: '合成稿件' }, body: '# 稿件正文', source_ids: ['source-1'], important_conflicts: [], state: 'pending', created_at: '2026-10-14T00:00:00Z', version: 1 }
const page = { page_id: 'page-1', relative_path: '项目/页面.md', metadata: { id: 'page-1', title: '正式页', kind: 'decision' }, body: '当前正式正文 **内容**', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'pending', validity: 'current' }
const candidate = { action_id: 'candidate-1', kind: 'todo', description: '合成任务建议', related_project_id: null, state: 'proposed', source_draft_id: 'draft-1', created_at: '2026-10-14T00:00:00Z' }
const intent = { action_id: 'action-1', kind: 'project_progress', payload: { progress: '合成' }, payload_sha256: 'b'.repeat(64), state: 'proposed', confirmation_id: null, created_at: '2026-10-14T00:00:00Z' }

function setup(overrides: Record<string, unknown> = {}, props: { target?: ApprovalTarget | null; onTargetHandled?: () => void; refreshEpoch?: number; onOpenPage?: (pageId: string, expectedHash?: string) => void } = {}) {
  const calls: Array<{ path: string; method: string; body?: Record<string, unknown> }> = []
  const onError = vi.fn()
  const responses: Record<string, unknown> = {
    '/api/v1/intake/items': [source], '/api/v1/drafts': [draft], '/api/v1/pages': [page],
    '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 0, current_pages: 0, stale_pages: 1 },
    '/api/v1/actions': [candidate], '/api/v1/action-intents?limit=20': { items: [intent], next_cursor: null },
    '/api/v1/projects': [],
    '/api/v1/lines': [],
    '/api/v1/settings': { mode: 'fake', embedding_fingerprint: 'fake-fingerprint' },
    ...overrides,
  }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('http://localhost', '')
    const method = init?.method ?? 'GET'
    calls.push({ path, method, ...(init?.body ? { body: JSON.parse(String(init.body)) as Record<string, unknown> } : {}) })
    const value = responses[path]
    if (path.startsWith('/api/v1/sources/')) return Response.json({ source: { source_id: path.slice('/api/v1/sources/'.length), filename: '合成材料.md', origin_kind: 'quick_note' }, text: '这是对应ID的合成原文。' })
    if (value instanceof Error) return Response.json({ error: { message: value.message } }, { status: 503 })
    if (path.endsWith('/confirmations') && method === 'POST') return Response.json(responses[path] ?? { state: 'succeeded', index_update: 'updated' })
    if (path.endsWith('/acceptance-plans') && method === 'POST') return Response.json({ plan: { plan_id: 'plan-1', scope_sha256: 'scope', request_limit: 2 }, scope: {} })
    if (path.includes('/acceptance-plans/') && path.endsWith('/confirm')) return Response.json({})
    if (path.endsWith('/index/plans') && method === 'POST') return Response.json({ plan_id: 'index-1', workspace_id: 'workspace', mode: 'initial', fingerprint: 'fake-fingerprint', page_ids: ['page-1'], page_versions: { 'page-1': 'hash' }, estimated_tokens: 12, estimated_cost: 0, page_preview: [{ title: '正式页', version: 'v1' }] })
    if (path.endsWith('/index/jobs') && method === 'POST') return Response.json({ indexed_pages: 1, indexed_chunks: 1, embedded_chunks: 0, reused_chunks: 1, active_fingerprint: 'fake-fingerprint' })
    if (path.includes('/actions/') && path.endsWith('/confirmations')) return Response.json({ ...intent, state: 'confirmed' })
    return Response.json(value ?? {})
  }))
  const onPendingCount = vi.fn()
  const view = render(<ApprovalView {...props} onPendingCount={onPendingCount} onError={onError} />)
  return { calls, onPendingCount, onError, rerender: (nextProps: typeof props = props) => view.rerender(<ApprovalView {...nextProps} onPendingCount={onPendingCount} onError={onError} />) }
}

it('continues with returned source IDs when titles collide and preselects only those exact items', async () => {
  const onTargetHandled = vi.fn()
  const first = { ...source, item_id: 'same-title-old', source_id: 'source-old', title: '同名会议记录' }
  const second = { ...source, item_id: 'returned-item-a', source_id: 'source-a', title: '同名会议记录' }
  const third = { ...source, item_id: 'returned-item-b', source_id: 'source-b', title: '另一条会议记录' }
  const { calls } = setup({ '/api/v1/intake/items': [first, second, third], '/api/v1/drafts': [] }, { target: { kind: 'source', itemIds: ['returned-item-a', 'returned-item-b'] }, onTargetHandled })
  await screen.findByText('已定位到本次成功保存的 2 项材料。选择归属后可继续整理。')
  const sourceFocus = await screen.findByRole('region', { name: '来源详情：同名会议记录' })
  expect(within(sourceFocus).getByText('这是对应ID的合成原文。')).toBeTruthy()
  expect(within(sourceFocus).getByRole('button', { name: /整理所选 · 2/ })).toBeTruthy()
  expect(calls.some(({ path }) => path === '/api/v1/sources/source-a')).toBe(true)
  expect(calls.some(({ path }) => path === '/api/v1/sources/source-old')).toBe(false)
  expect(onTargetHandled).toHaveBeenCalledTimes(1)
  expect(calls.some(({ path }) => path.includes('/intake/jobs'))).toBe(false)
})

it('routes formal-page targets by page ID when titles collide', async () => {
  const older = { ...page, page_id: 'older-page', metadata: { ...page.metadata, id: 'older-page' }, body: '旧的同名正文' }
  const returned = { ...page, page_id: 'returned-page', metadata: { ...page.metadata, id: 'returned-page' }, body: '本次实际页面正文' }
  setup({ '/api/v1/pages': [older, returned] }, { target: { kind: 'formal', pageIds: ['returned-page'] } })
  const focus = await screen.findByRole('region', { name: '正式内容：正式页' })
  expect(within(focus).getByText('本次实际页面正文')).toBeTruthy()
  expect(within(focus).queryByText('旧的同名正文')).toBeNull()
})

it('waits for refreshed target data before handling an exact-ID destination', async () => {
  let finishSources: ((response: Response) => void) | undefined
  const onTargetHandled = vi.fn()
  const targetSource = { ...source, item_id: 'ready-later-item', source_id: 'ready-later-source', title: '稍后到达的材料' }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).replace('http://localhost', '')
    if (path === '/api/v1/intake/items') return await new Promise<Response>((resolve) => { finishSources = resolve })
    if (path.startsWith('/api/v1/sources/')) return Response.json({ source: { source_id: 'ready-later-source', filename: '稍后到达.md', origin_kind: 'quick_note' }, text: '目标原文已就绪。' })
    if (path === '/api/v1/index/status') return Response.json({ state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 })
    if (path === '/api/v1/action-intents?limit=20') return Response.json({ items: [], next_cursor: null })
    if (path === '/api/v1/settings') return Response.json({ mode: 'fake', embedding_fingerprint: null })
    return Response.json([])
  }))
  render(<ApprovalView target={{ kind: 'source', itemIds: ['ready-later-item'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)

  await waitFor(() => expect(finishSources).toBeTypeOf('function'))
  expect(onTargetHandled).not.toHaveBeenCalled()
  finishSources!(Response.json([targetSource]))

  const focus = await screen.findByRole('region', { name: '来源详情：稍后到达的材料' })
  expect(within(focus).getByText('目标原文已就绪。')).toBeTruthy()
  expect(onTargetHandled).toHaveBeenCalledTimes(1)
})

it('ignores an older refresh when a newer exact-ID target arrives first', async () => {
  let finishFirstSources: ((response: Response) => void) | undefined
  let sourceReadCount = 0
  const onTargetHandled = vi.fn()
  const oldSource = { ...source, item_id: 'old-target-item', source_id: 'old-target-source', title: '旧目标材料' }
  const latestSource = { ...source, item_id: 'latest-target-item', source_id: 'latest-target-source', title: '最新目标材料' }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).replace('http://localhost', '')
    if (path === '/api/v1/intake/items') {
      sourceReadCount += 1
      if (sourceReadCount === 1) return await new Promise<Response>((resolve) => { finishFirstSources = resolve })
      return Response.json([latestSource])
    }
    if (path.startsWith('/api/v1/sources/')) return Response.json({ source: { source_id: path.slice('/api/v1/sources/'.length), filename: '最新材料.md', origin_kind: 'quick_note' }, text: '最新目标原文。' })
    if (path === '/api/v1/index/status') return Response.json({ state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 })
    if (path === '/api/v1/action-intents?limit=20') return Response.json({ items: [], next_cursor: null })
    if (path === '/api/v1/settings') return Response.json({ mode: 'fake', embedding_fingerprint: null })
    return Response.json([])
  }))
  const view = render(<ApprovalView target={{ kind: 'source', itemIds: ['old-target-item'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(finishFirstSources).toBeTypeOf('function'))

  view.rerender(<ApprovalView refreshEpoch={1} target={{ kind: 'source', itemIds: ['latest-target-item'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  const latestFocus = await screen.findByRole('region', { name: '来源详情：最新目标材料' })
  expect(within(latestFocus).getByText('最新目标原文。')).toBeTruthy()
  finishFirstSources!(Response.json([oldSource]))

  await waitFor(() => expect(onTargetHandled).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('region', { name: '来源详情：最新目标材料' })).toBeTruthy()
  expect(screen.queryByRole('region', { name: '来源详情：旧目标材料' })).toBeNull()
})

it('ignores an older source-detail response after a newer target takes focus', async () => {
  let finishOldDetail: ((response: Response) => void) | undefined
  const first = { ...source, item_id: 'first-target-item', source_id: 'first-target-source', title: '先选材料' }
  const latest = { ...source, item_id: 'latest-target-item', source_id: 'latest-target-source', title: '后选材料' }
  const onTargetHandled = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).replace('http://localhost', '')
    if (path === '/api/v1/intake/items') return Response.json([first, latest])
    if (path === '/api/v1/sources/first-target-source') return await new Promise<Response>((resolve) => { finishOldDetail = resolve })
    if (path.startsWith('/api/v1/sources/')) return Response.json({ source: { source_id: 'latest-target-source', filename: '后选材料.md', origin_kind: 'quick_note' }, text: '后选材料原文。' })
    if (path === '/api/v1/index/status') return Response.json({ state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 })
    if (path === '/api/v1/action-intents?limit=20') return Response.json({ items: [], next_cursor: null })
    if (path === '/api/v1/settings') return Response.json({ mode: 'fake', embedding_fingerprint: null })
    return Response.json([])
  }))
  const view = render(<ApprovalView target={{ kind: 'source', itemIds: ['first-target-item'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(finishOldDetail).toBeTypeOf('function'))
  view.rerender(<ApprovalView target={{ kind: 'source', itemIds: ['latest-target-item'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)

  const latestFocus = await screen.findByRole('region', { name: '来源详情：后选材料' })
  expect(within(latestFocus).getByText('后选材料原文。')).toBeTruthy()
  await act(async () => {
    finishOldDetail!(Response.json({ source: { source_id: 'first-target-source', filename: '先选材料.md', origin_kind: 'quick_note' }, text: '过期的先选材料原文。' }))
    await Promise.resolve()
  })
  expect(screen.getByRole('region', { name: '来源详情：后选材料' })).toBeTruthy()
  expect(screen.queryByText('过期的先选材料原文。')).toBeNull()
})

it('keeps an in-flight source detail when a handled target is followed by a refresh epoch', async () => {
  let finishDetail: ((response: Response) => void) | undefined
  let sourceListReads = 0
  const onTargetHandled = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).replace('http://localhost', '')
    if (path === '/api/v1/intake/items') { sourceListReads += 1; return Response.json([source]) }
    if (path === '/api/v1/sources/source-1') return await new Promise<Response>((resolve) => { finishDetail = resolve })
    if (path === '/api/v1/index/status') return Response.json({ state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 })
    if (path === '/api/v1/action-intents?limit=20') return Response.json({ items: [], next_cursor: null })
    if (path === '/api/v1/settings') return Response.json({ mode: 'fake', embedding_fingerprint: null })
    return Response.json([])
  }))
  const view = render(<ApprovalView target={{ kind: 'source', itemIds: ['source-1'] }} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(finishDetail).toBeTypeOf('function'))
  await waitFor(() => expect(onTargetHandled).toHaveBeenCalledTimes(1))

  view.rerender(<ApprovalView target={null} refreshEpoch={1} onTargetHandled={onTargetHandled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(sourceListReads).toBe(2))
  await act(async () => {
    finishDetail!(Response.json({ source: { source_id: 'source-1', filename: '随手记.md', origin_kind: 'quick_note' }, text: '刷新期间仍可完成的原文。' }))
    await Promise.resolve()
  })
  const focus = await screen.findByRole('region', { name: '来源详情：合成速记' })
  expect(within(focus).getByText('刷新期间仍可完成的原文。')).toBeTruthy()
})

it('shows an existing processing source without starting a second intake job', async () => {
  const processing = { ...source, item_id: 'processing-item', source_id: 'processing-source', state: 'processing' }
  const { calls } = setup({ '/api/v1/intake/items': [processing] }, { target: { kind: 'source', itemIds: ['processing-item'] } })
  const focus = await screen.findByRole('region', { name: '来源详情：合成速记' })
  expect(within(focus).getByText('这条材料已有整理任务或稿件，不会再次发起整理。')).toBeTruthy()
  expect(within(focus).queryByRole('button', { name: /整理所选/ })).toBeNull()
  expect(calls.some(({ path, method }) => path === '/api/v1/intake/jobs' && method === 'POST')).toBe(false)
})

it('opens one draft in a focused reading view and returns to its compact list', async () => {
  setup()
  await screen.findByText('合成稿件')
  fireEvent.click(screen.getByRole('button', { name: '打开稿件：合成稿件' }))
  const focus = await screen.findByRole('region', { name: '稿件审核：合成稿件' })
  expect(within(focus).getByText('稿件正文')).toBeTruthy()
  expect(focus.querySelector('.draft-edit-details')?.hasAttribute('open')).toBe(false)
  fireEvent.click(within(focus).getByRole('button', { name: '返回审批清单' }))
  expect(await screen.findByRole('region', { name: '审批清单' })).toBeTruthy()
  expect(screen.getByText('合成稿件')).toBeTruthy()
})

it('keeps unsaved draft edits when a hidden approval view receives a refresh epoch', async () => {
  const { rerender } = setup()
  await screen.findByText('合成稿件')
  fireEvent.click(screen.getByRole('button', { name: '打开稿件：合成稿件' }))
  const focus = await screen.findByRole('region', { name: '稿件审核：合成稿件' })
  fireEvent.click(within(focus).getByText('编辑稿件与归属'))
  const body = within(focus).getByLabelText('正文') as HTMLTextAreaElement
  fireEvent.change(body, { target: { value: '# 本地尚未保存' } })

  rerender({ refreshEpoch: 1 })
  await waitFor(() => expect(body.value).toBe('# 本地尚未保存'))
  expect(screen.getByText('正文或归属尚未保存。')).toBeTruthy()
})

it('preserves the actual confirmation result and opens the exact saved page for one selected draft', async () => {
  const secondDraft = { ...draft, draft_id: 'draft-2', metadata: { title: '另一份合成稿' }, body: '第二份正文' }
  const onOpenPage = vi.fn()
  const { calls } = setup({
    '/api/v1/drafts': [draft, secondDraft],
    '/api/v1/drafts/draft-1/confirmations': { state: 'succeeded', index_update: 'update_failed', page_versions: { 'actual-saved-page': 'saved-hash' } },
    '/api/v1/pages': [page, { ...page, page_id: 'actual-saved-page', metadata: { title: '正式保存页' }, body: '新保存正文' }],
  }, { onOpenPage })
  await screen.findByText('合成稿件')
  fireEvent.click(screen.getByRole('button', { name: '打开稿件：合成稿件' }))
  const focus = await screen.findByRole('region', { name: '稿件审核：合成稿件' })
  fireEvent.click(within(focus).getByRole('button', { name: '确认并保存当前版本' }))
  fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: '确认并保存当前版本' }))
  expect(await screen.findAllByText(/索引更新未完成/)).toHaveLength(2)
  fireEvent.click(screen.getByRole('button', { name: '打开本次保存的正式页' }))
  expect(onOpenPage).toHaveBeenCalledWith('actual-saved-page')
  expect(calls.filter(({ path, method }) => path === '/api/v1/drafts/draft-1/confirmations' && method === 'POST')).toHaveLength(1)
  expect(calls.some(({ path, method }) => path === '/api/v1/drafts/draft-2/confirmations' && method === 'POST')).toBe(false)
})

it('五类固定顺序独立读取，局部失败不会把其他分组画成空态', async () => {
  setup({ '/api/v1/pages': new Error('本地读取暂不可用') })
  await screen.findByText('合成速记')
  const headings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
  expect(headings.filter((heading) => /[1-5] ·/.test(heading ?? ''))).toEqual(['1 · 来源', '2 · 稿件', '3 · 正式内容', '4 · 索引', '5 · 外部动作'])
  expect(screen.getByText('合成速记').closest('li')?.textContent).toContain('记一句')
  expect(screen.getByText('合成稿件')).toBeTruthy()
  expect(screen.getByRole('alert').textContent).toContain('本地读取暂不可用')
  expect(screen.getByText('当前状态：尚未建立')).toBeTruthy()
})

it('已有正式页但索引尚未建立时将首次索引作为待处理事项展开', async () => {
  const confirmedPage = { ...page, approval_state: 'confirmed' }
  setup({ '/api/v1/pages': [confirmedPage], '/api/v1/drafts': [], '/api/v1/intake/items': [], '/api/v1/actions': [], '/api/v1/action-intents?limit=20': { items: [], next_cursor: null }, '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const indexGroup = await screen.findByRole('region', { name: /4 · 索引/ })
  await waitFor(() => expect(indexGroup.hasAttribute('open')).toBe(true))
  expect(within(indexGroup).getByText('1')).toBeTruthy()
  expect(within(indexGroup).getByRole('button', { name: '预览首次索引' })).toBeTruthy()
})

it('没有正式页的初次索引保持折叠', async () => {
  setup({ '/api/v1/pages': [], '/api/v1/drafts': [], '/api/v1/intake/items': [], '/api/v1/actions': [], '/api/v1/action-intents?limit=20': { items: [], next_cursor: null }, '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const indexGroup = await screen.findByRole('region', { name: /4 · 索引/ })
  await waitFor(() => expect(indexGroup.hasAttribute('open')).toBe(false))
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
  await waitFor(() => expect(finishRead).toBeTypeOf('function'))
  await act(async () => { finishRead?.(Response.json([])) })
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

it('移除只汇总选中类别的检查清单，保留各项自己的确认入口', async () => {
  const { calls } = setup()
  await screen.findByText('正式页')
  expect(screen.queryByRole('button', { name: /检查并应用/ })).toBeNull()
  expect(screen.queryByRole('checkbox', { name: '选择索引事项进行检查' })).toBeNull()
  expect(screen.getByRole('button', { name: '确认并保存当前版本' })).toBeTruthy()
  expect(calls.filter(({ method }) => method === 'POST')).toHaveLength(0)
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
