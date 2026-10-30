import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ApprovalView } from './ApprovalView'
import type { ApprovalTarget } from '../approvalTarget'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

const source = { item_id: 'source-1', source_id: 'source-1', origin_kind: 'quick_note', title: '合成速记', filename: '随手记.md', original_relative_path: '原件/secret-path.md', created_at: '2026-10-14T00:00:00Z', state: 'pending' }
const draft = { draft_id: 'draft-1', input_ids: [], target_page_id: null, metadata: { title: '合成稿件' }, body: '# 稿件正文', source_ids: ['source-1'], important_conflicts: [], state: 'pending', created_at: '2026-10-14T00:00:00Z', version: 1 }
const page = { page_id: 'page-1', relative_path: '项目/页面.md', metadata: { id: 'page-1', title: '正式页', kind: 'decision' }, body: '当前正式正文 **内容**', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'pending', validity: 'current' }
const candidate = { action_id: 'candidate-1', kind: 'todo', description: '合成任务建议', related_project_id: null, state: 'proposed', source_draft_id: 'draft-1', created_at: '2026-10-14T00:00:00Z' }
const intent = { action_id: 'action-1', kind: 'project_progress', payload: { progress: '合成' }, payload_sha256: 'b'.repeat(64), state: 'proposed', confirmation_id: null, created_at: '2026-10-14T00:00:00Z' }

function setup(overrides: Record<string, unknown> = {}, props: { target?: ApprovalTarget | null; onTargetHandled?: () => void; refreshEpoch?: number; externalPagesRevision?: number; onOpenPage?: (pageId: string, expectedHash?: string) => void } = {}) {
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
    if (typeof value === 'function') return await (value as () => Promise<Response>)()
    if (path.startsWith('/api/v1/sources/')) return Response.json({ source: { source_id: path.slice('/api/v1/sources/'.length), filename: '合成材料.md', origin_kind: 'quick_note' }, text: '这是对应ID的合成原文。' })
    if (value instanceof Error) return Response.json({ error: { message: value.message } }, { status: 503 })
    if (path.endsWith('/confirmations') && method === 'POST') return Response.json(responses[path] ?? { state: 'succeeded', index_update: 'updated' })
    if (path.endsWith('/acceptance-plans') && method === 'POST') {
      const requestBody = JSON.parse(String(init?.body ?? '{}')) as { scope?: Record<string, unknown> }
      const scope = requestBody.scope ?? {}
      const items = responses['/api/v1/intake/items'] as Array<{ item_id: string; source_id: string }>
      const itemIds = scope.item_ids as string[] | undefined
      const outgoingInputs = itemIds?.map((itemId) => {
        const item = items.find((candidate) => candidate.item_id === itemId)
        return item ? { item_id: item.item_id, source_id: item.source_id, text: '这是对应ID的合成原文。' } : null
      })
      const reviewedScope = { ...scope, max_output_tokens: 512, outgoing_inputs: outgoingInputs }
      responses['/api/v1/acceptance-plans:scope'] = reviewedScope
      return Response.json({ plan: { plan_id: 'plan-1', scope_sha256: 'scope', request_limit: 2 }, scope: reviewedScope })
    }
    if (path.includes('/acceptance-plans/') && path.endsWith('/confirm')) return Response.json({})
    if (path.endsWith('/index/plans') && method === 'POST') {
      const body = JSON.parse(String(init?.body ?? '{}')) as { mode?: string; fingerprint?: string }
      return Response.json({ plan_id: 'index-1', workspace_id: 'workspace', mode: body.mode ?? 'initial', fingerprint: body.fingerprint ?? 'fake-fingerprint', page_ids: ['page-1'], page_versions: { 'page-1': 'hash' }, estimated_tokens: 12, estimated_cost: 0, page_preview: [{ title: '正式页', version: 'v1' }] })
    }
    if (path.endsWith('/index/jobs') && method === 'POST') return Response.json({ indexed_pages: 1, indexed_chunks: 1, embedded_chunks: 0, reused_chunks: 1, active_fingerprint: 'fake-fingerprint' })
    if (path.includes('/actions/') && path.endsWith('/confirmations')) return Response.json({ ...intent, state: 'confirmed' })
    return Response.json(value ?? {})
  }))
  const onPendingCount = vi.fn()
  const view = render(<ApprovalView {...props} onPendingCount={onPendingCount} onError={onError} />)
  return { calls, responses, onPendingCount, onError, rerender: (nextProps: typeof props = props) => view.rerender(<ApprovalView {...nextProps} onPendingCount={onPendingCount} onError={onError} />) }
}

it('continues with returned source IDs when titles collide and opens the exact item', async () => {
  const onTargetHandled = vi.fn()
  const line = { id: 'line-a', name: '合成主线', directory: '合成主线' }
  const project = { id: 'project-a', line_id: line.id, name: '合成项目', directory: '合成主线/合成项目', overview_id: 'overview-a', archived: false, progress: '', progress_version: 0 }
  const first = { ...source, item_id: 'same-title-old', source_id: 'source-old', title: '同名会议记录' }
  const second = { ...source, item_id: 'returned-item-a', source_id: 'source-a', title: '同名会议记录' }
  const third = { ...source, item_id: 'returned-item-b', source_id: 'source-b', title: '另一条会议记录' }
  const { calls, responses } = setup({
    '/api/v1/intake/items': [first, second, third], '/api/v1/drafts': [],
    '/api/v1/lines': [line], '/api/v1/projects': [project],
    '/api/v1/index/status': { state: 'ready', fingerprint: 'real-fingerprint', vector: 'real', pages: 1, chunks: 2, current_pages: 1, stale_pages: 0 },
    '/api/v1/settings': { mode: 'real', embedding_fingerprint: 'real-fingerprint', local_model: { state: 'ready' } },
  }, { target: { kind: 'source', itemIds: ['returned-item-a', 'returned-item-b'] }, onTargetHandled })
  await screen.findByText('已定位到本次成功保存的 2 项材料。选择归属后可继续整理。', {}, { timeout: 10000 })
  const sourceFocus = await screen.findByRole('dialog', { name: '来源详情：同名会议记录' })
  expect(within(sourceFocus).getByText('这是对应ID的合成原文。')).toBeTruthy()
  expect(onTargetHandled).toHaveBeenCalled()
  await within(sourceFocus).findByRole('option', { name: line.name })
  fireEvent.change(within(sourceFocus).getByLabelText('主线'), { target: { value: line.id } })
  await within(sourceFocus).findByRole('option', { name: project.name })
  fireEvent.change(within(sourceFocus).getByLabelText('项目'), { target: { value: project.id } })
  await waitFor(() => expect((within(sourceFocus).getByRole('button', { name: '整理' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(within(sourceFocus).getByRole('button', { name: '整理' }))
  const preview = await screen.findByRole('dialog', { name: '确认整理所选来源？' })
  expect(responses['/api/v1/acceptance-plans:scope']).toMatchObject({ outgoing_inputs: [{ item_id: 'returned-item-a', source_id: 'source-a', text: '这是对应ID的合成原文。' }] })
  fireEvent.click(within(preview).getByRole('button', { name: '确认并整理所选材料' }))
  await waitFor(() => expect(calls.some(({ path }) => path === '/api/v1/intake/jobs')).toBe(true))
  const job = calls.find(({ path }) => path === '/api/v1/intake/jobs')
  expect(job?.body).toMatchObject({ item_ids: ['returned-item-a'], line_id: line.id, project_id: project.id, acceptance_plan_id: 'plan-1' })
  expect(calls.some(({ path }) => path === '/api/v1/sources/source-a')).toBe(true)
  expect(calls.some(({ path }) => path === '/api/v1/sources/source-old')).toBe(false)
  expect(calls.some(({ path }) => path.includes('/intake/jobs'))).toBe(true)
})

it('routes formal-page targets by page ID when titles collide', async () => {
  const older = { ...page, page_id: 'older-page', metadata: { ...page.metadata, id: 'older-page' }, body: '旧的同名正文' }
  const returned = { ...page, page_id: 'returned-page', metadata: { ...page.metadata, id: 'returned-page' }, body: '本次实际页面正文' }
  setup({ '/api/v1/pages': [older, returned] }, { target: { kind: 'formal', pageIds: ['returned-page'] } })
  const focus = await screen.findByRole('region', { name: '正式内容：正式页' })
  expect(within(focus).getByText('本次实际页面正文')).toBeTruthy()
  expect(within(focus).queryByText('旧的同名正文')).toBeNull()
})

it('marks a deleted focused formal page unavailable and restores it when it returns', async () => {
  let currentPages = [page]
  const { rerender } = setup({ '/api/v1/pages': () => Promise.resolve(Response.json(currentPages)) }, { target: { kind: 'formal', pageIds: [page.page_id] } })
  const focus = await screen.findByRole('region', { name: '正式内容：正式页' })
  expect(within(focus).getByRole('button', { name: '确认并保存当前版本' })).toBeTruthy()
  currentPages = []
  rerender({ externalPagesRevision: 1 })
  expect(await screen.findByText(/页面已删除或暂时无法读取/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: '确认并保存当前版本' })).toBeNull()
  currentPages = [page]
  rerender({ externalPagesRevision: 2 })
  expect(await screen.findByRole('region', { name: '正式内容：正式页' })).toBeTruthy()
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

  const focus = await screen.findByRole('dialog', { name: '来源详情：稍后到达的材料' })
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
  const latestFocus = await screen.findByRole('dialog', { name: '来源详情：最新目标材料' })
  expect(within(latestFocus).getByText('最新目标原文。')).toBeTruthy()
  finishFirstSources!(Response.json([oldSource]))

  await waitFor(() => expect(onTargetHandled).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('dialog', { name: '来源详情：最新目标材料' })).toBeTruthy()
  expect(screen.queryByRole('dialog', { name: '来源详情：旧目标材料' })).toBeNull()
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

  const latestFocus = await screen.findByRole('dialog', { name: '来源详情：后选材料' })
  expect(within(latestFocus).getByText('后选材料原文。')).toBeTruthy()
  await act(async () => {
    finishOldDetail!(Response.json({ source: { source_id: 'first-target-source', filename: '先选材料.md', origin_kind: 'quick_note' }, text: '过期的先选材料原文。' }))
    await Promise.resolve()
  })
  expect(screen.getByRole('dialog', { name: '来源详情：后选材料' })).toBeTruthy()
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
  const focus = await screen.findByRole('dialog', { name: '来源详情：合成速记' })
  expect(within(focus).getByText('刷新期间仍可完成的原文。')).toBeTruthy()
})

it('shows an existing processing source without starting a second intake job', async () => {
  const processing = { ...source, item_id: 'processing-item', source_id: 'processing-source', state: 'processing' }
  const { calls } = setup({ '/api/v1/intake/items': [processing] }, { target: { kind: 'source', itemIds: ['processing-item'] } })
  const focus = await screen.findByRole('dialog', { name: '来源详情：合成速记' })
  expect(within(focus).getByText('这条材料已有整理任务或稿件，不会再次发起整理。')).toBeTruthy()
  expect(within(focus).queryByRole('button', { name: /整理所选/ })).toBeNull()
  expect(calls.some(({ path, method }) => path === '/api/v1/intake/jobs' && method === 'POST')).toBe(false)
})

it('reopening a reviewing source restores all associated drafts by source ID and labels confirmed drafts read-only', async () => {
  const reviewing = { ...source, state: 'reviewing' }
  const secondDraft = { ...draft, draft_id: 'draft-2', metadata: { title: '合成稿件' }, body: '# 第二份关联稿' }
  const confirmedDraft = { ...draft, draft_id: 'draft-confirmed', state: 'confirmed', metadata: { title: '合成稿件' }, body: '# 已确认稿正文' }
  const unrelatedDraft = { ...draft, draft_id: 'draft-unrelated', source_ids: ['other-source'], metadata: { title: '合成稿件' }, body: '# 同名但无关的稿' }
  const { calls } = setup({ '/api/v1/intake/items': [reviewing], '/api/v1/drafts': [draft, secondDraft, confirmedDraft, unrelatedDraft] })

  fireEvent.click(await screen.findByRole('button', { name: /合成速记/ }))
  let sourceFocus = await screen.findByRole('dialog', { name: '来源详情：合成速记' })
  expect(within(sourceFocus).getAllByRole('button', { name: '打开这份稿件' })).toHaveLength(2)
  expect(within(sourceFocus).getByRole('button', { name: '查看已确认稿件' })).toBeTruthy()
  expect(within(sourceFocus).getByText('这条材料已有整理任务或稿件，不会再次发起整理。')).toBeTruthy()
  fireEvent.click(within(sourceFocus).getByRole('button', { name: '关闭' }))

  fireEvent.click(screen.getByRole('button', { name: /合成速记/ }))
  sourceFocus = await screen.findByRole('dialog', { name: '来源详情：合成速记' })
  expect(within(sourceFocus).getAllByRole('button', { name: '打开这份稿件' })).toHaveLength(2)
  fireEvent.click(within(sourceFocus).getByRole('button', { name: '查看已确认稿件' }))

  const confirmedFocus = await screen.findByRole('region', { name: '稿件审核：合成稿件' })
  expect(within(confirmedFocus).getByRole('heading', { level: 1, name: '已确认稿正文' })).toBeTruthy()
  expect(within(confirmedFocus).getByText('这份稿件已确认，当前只读查看。')).toBeTruthy()
  expect(within(confirmedFocus).queryByRole('button', { name: '确认并保存当前版本' })).toBeNull()
  expect(calls.some(({ path, method }) => path === '/api/v1/intake/jobs' && method === 'POST')).toBe(false)
})

it('lets a confirmed draft open its original source while keeping editing and confirmation controls hidden', async () => {
  const confirmedDraft = { ...draft, draft_id: 'draft-confirmed', state: 'confirmed' }
  setup({ '/api/v1/drafts': [confirmedDraft] }, { target: { kind: 'draft', draftIds: ['draft-confirmed'] } })
  const focus = await screen.findByRole('region', { name: '稿件审核：合成稿件' })

  expect(within(focus).getByText('这份稿件已确认，当前只读查看。')).toBeTruthy()
  expect(within(focus).queryByText('编辑稿件与归属')).toBeNull()
  expect(within(focus).queryByRole('button', { name: '确认并保存当前版本' })).toBeNull()
  fireEvent.click(within(focus).getByText('查看来源'))
  fireEvent.click(within(focus).getByRole('button', { name: '打开来源 1' }))
  expect(await within(focus).findByText('这是对应ID的合成原文。')).toBeTruthy()
})

it('shows associated-draft loading failure and retry instead of an empty result', async () => {
  const reviewing = { ...source, state: 'reviewing' }
  let draftReads = 0
  const { calls } = setup({
    '/api/v1/intake/items': [reviewing],
    '/api/v1/drafts': () => Promise.resolve(draftReads++ === 0
      ? Response.json({ error: { message: '稿件暂时无法读取' } }, { status: 503 })
      : Response.json([draft])),
  })

  fireEvent.click(await screen.findByRole('button', { name: /合成速记/ }))
  const sourceFocus = await screen.findByRole('dialog', { name: '来源详情：合成速记' })
  expect((await within(sourceFocus).findByRole('alert')).textContent).toContain('稿件暂时无法读取')
  expect(within(sourceFocus).queryByText('当前没有可打开的关联稿件。')).toBeNull()
  fireEvent.click(within(sourceFocus).getByRole('button', { name: '重试' }))
  expect(await within(sourceFocus).findByRole('button', { name: '打开这份稿件' })).toBeTruthy()
  expect(calls.filter(({ path }) => path === '/api/v1/drafts')).toHaveLength(2)
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
  const headings = Array.from(document.querySelectorAll('.approval-group-head h2')).map((heading) => heading.textContent)
  // 五组是并列队列，不是步骤：标题不带序号。
  expect(headings).toEqual(['来源', '稿件', '正式内容', '搜索与问答准备', '外部动作'])
  expect(screen.getByText('合成速记').closest('li')?.textContent).toContain('记一句')
  expect(screen.getByText('合成稿件')).toBeTruthy()
  expect(screen.getByRole('alert').textContent).toContain('本地读取暂不可用')
  expect(screen.getByText('无法读取已确认内容')).toBeTruthy()
})

it('已有正式页但索引尚未建立时把首次索引算作待处理事项', async () => {
  const confirmedPage = { ...page, approval_state: 'confirmed' }
  setup({ '/api/v1/pages': [confirmedPage], '/api/v1/drafts': [], '/api/v1/intake/items': [], '/api/v1/actions': [], '/api/v1/action-intents?limit=20': { items: [], next_cursor: null }, '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const indexGroup = await screen.findByRole('region', { name: '搜索与问答准备' })
  await waitFor(() => expect(within(indexGroup).getByText('1')).toBeTruthy())
  expect(within(indexGroup).getByRole('button', { name: '准备已确认的内容' })).toBeTruthy()
})

it('没有正式页时初次索引不显示待处理入口', async () => {
  setup({ '/api/v1/pages': [], '/api/v1/drafts': [], '/api/v1/intake/items': [], '/api/v1/actions': [], '/api/v1/action-intents?limit=20': { items: [], next_cursor: null }, '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const indexGroup = await screen.findByRole('region', { name: '搜索与问答准备' })
  await waitFor(() => expect(within(indexGroup).getByText('0')).toBeTruthy())
  expect(within(indexGroup).getByText(/先添加并确认正式内容/)).toBeTruthy()
  expect(within(indexGroup).queryByRole('button', { name: '准备已确认的内容' })).toBeNull()
})

it('ready 状态说明内容无需重复准备，普通卡片没有预览按钮或 token', async () => {
  const { calls } = setup({
    '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }],
    '/api/v1/index/status': { state: 'ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 3, current_pages: 1, stale_pages: 0 },
  })
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  expect(within(group).getByText('内容已是最新，无需操作')).toBeTruthy()
  expect(within(group).getByText('已准备 1 页。')).toBeTruthy()
  expect(within(group).queryByRole('button', { name: '查看重新准备范围' })).toBeNull()
  expect(within(group).getByText('高级维护').closest('details')?.open).toBe(false)
  expect(group.textContent).not.toMatch(/token|fingerprint|hash|计划类型/i)
  expect(calls.some(({ path }) => path.endsWith('/index/plans'))).toBe(false)
})

it('高级维护展开不请求计划，显式点击才查看全量范围', async () => {
  const { calls } = setup({
    '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }],
    '/api/v1/index/status': { state: 'ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 3, current_pages: 1, stale_pages: 0 },
  })
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  fireEvent.click(within(group).getByText('高级维护'))
  expect(calls.some(({ path }) => path.endsWith('/index/plans'))).toBe(false)
  fireEvent.click(within(group).getByRole('button', { name: '重新准备全部内容' }))
  await waitFor(() => expect(calls.find(({ path }) => path.endsWith('/index/plans'))?.body?.mode).toBe('full'))
})

it('未知状态与搜索配置未读取时不显示可准备或已就绪，只能刷新', async () => {
  const unknown = setup({ '/api/v1/index/status': { state: 'unknown', fingerprint: 'old-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  expect(within(group).getByText('需要刷新状态')).toBeTruthy()
  expect(within(group).getByRole('button', { name: '刷新状态' })).toBeTruthy()
  expect(within(group).queryByRole('button', { name: '重新准备全部内容' })).toBeNull()
  expect(unknown.calls.some(({ path }) => path.endsWith('/index/plans'))).toBe(false)
})

it('状态刷新从有计划变为 unknown 后撤销旧预览', async () => {
  const { calls, responses, rerender } = setup({ '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }], '/api/v1/index/status': { state: 'stale', fingerprint: 'fake-fingerprint', pages: 1, chunks: 2, current_pages: 1, stale_pages: 1 } })
  await screen.findByText('合成速记')
  fireEvent.click(screen.getByRole('button', { name: '查看待更新内容' }))
  await screen.findByText(/将检查 1 页/)
  expect(calls.some(({ path }) => path.endsWith('/index/plans'))).toBe(true)
  responses['/api/v1/index/status'] = { state: 'unknown', fingerprint: 'old-fingerprint', pages: 1, chunks: 2, current_pages: 1, stale_pages: 1 }
  rerender({ refreshEpoch: 1 })
  await screen.findByRole('button', { name: '刷新状态' })
  expect(screen.queryByText(/将检查 1 页/)).toBeNull()
  expect(screen.queryByRole('button', { name: '查看范围并确认' })).toBeNull()
})

it('搜索配置读取失败时不把 ready 状态显示为可用', async () => {
  const { calls } = setup({ '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }], '/api/v1/settings': new Error('设置暂不可用'), '/api/v1/index/status': { state: 'ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 2, current_pages: 1, stale_pages: 0 } })
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  expect(within(group).getByText('需要刷新状态')).toBeTruthy()
  expect(within(group).queryByText('内容已是最新，无需操作')).toBeNull()
  expect(within(group).getByRole('button', { name: '刷新状态' })).toBeTruthy()
  expect(calls.some(({ path }) => path.endsWith('/index/plans'))).toBe(false)
})

it.each(['迟到成功', '迟到失败'] as const)('手动刷新后%s的旧设置响应不能覆盖新模式', async (oldOutcome) => {
  const oldSettings = deferred<Response>()
  let settingsCalls = 0
  const { calls } = setup({
    '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }],
    '/api/v1/index/status': { state: 'ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 2, current_pages: 1, stale_pages: 0 },
    '/api/v1/settings': () => {
      settingsCalls += 1
      return settingsCalls === 1
        ? oldSettings.promise
        : Promise.resolve(Response.json({ mode: 'real', embedding_fingerprint: 'real-fingerprint' }))
    },
  })
  await waitFor(() => expect(calls.filter(({ path }) => path === '/api/v1/settings')).toHaveLength(1))
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  fireEvent.click(within(group).getByRole('button', { name: '刷新状态' }))
  await waitFor(() => expect(within(group).getByText('搜索方式已更换')).toBeTruthy())
  expect(settingsCalls).toBe(2)

  await act(async () => {
    if (oldOutcome === '迟到成功') oldSettings.resolve(Response.json({ mode: 'fake', embedding_fingerprint: 'fake-fingerprint' }))
    else oldSettings.reject(new Error('过期设置请求失败'))
    await Promise.resolve()
  })
  await waitFor(() => expect(within(group).getByText('搜索方式已更换')).toBeTruthy())
  expect(within(group).queryByText('内容已是最新，无需操作')).toBeNull()
})

it('refreshEpoch 清理旧设置读取；卸载代次内的迟到结果不能覆盖新设置', async () => {
  const oldSettings = deferred<Response>()
  let settingsCalls = 0
  const { calls, rerender } = setup({
    '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }],
    '/api/v1/index/status': { state: 'ready', fingerprint: 'fake-fingerprint', pages: 1, chunks: 2, current_pages: 1, stale_pages: 0 },
    '/api/v1/settings': () => {
      settingsCalls += 1
      return settingsCalls === 1
        ? oldSettings.promise
        : Promise.resolve(Response.json({ mode: 'real', embedding_fingerprint: 'real-fingerprint' }))
    },
  })
  await waitFor(() => expect(calls.filter(({ path }) => path === '/api/v1/settings')).toHaveLength(1))
  rerender({ refreshEpoch: 1 })
  await waitFor(() => expect(screen.getByText('搜索方式已更换')).toBeTruthy())
  expect(settingsCalls).toBe(2)

  await act(async () => {
    oldSettings.resolve(Response.json({ mode: 'fake', embedding_fingerprint: 'fake-fingerprint' }))
    await Promise.resolve()
  })
  await waitFor(() => expect(screen.getByText('搜索方式已更换')).toBeTruthy())
  expect(screen.queryByText('内容已是最新，无需操作')).toBeNull()
})

it('页面目录读取失败时不把首次准备伪装为空库或开放入口', async () => {
  setup({ '/api/v1/pages': new Error('正式页读取失败'), '/api/v1/index/status': { state: 'not_ready', fingerprint: 'fake-fingerprint', pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 } })
  const group = await screen.findByRole('region', { name: '搜索与问答准备' })
  expect(within(group).getByText('无法读取已确认内容')).toBeTruthy()
  expect(within(group).queryByRole('button', { name: '准备已确认的内容' })).toBeNull()
  expect(within(group).getByRole('button', { name: '刷新状态' })).toBeTruthy()
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
  const sourceGroup = screen.getByRole('region', { name: '来源' })
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
  // 现在整行就是入口：点开来源详情，整理区在弹层底部。
  fireEvent.click(within(screen.getByRole('region', { name: '来源' })).getByRole('button', { name: /合成速记/ }))
  await screen.findByRole('dialog', { name: /来源详情/ })
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
  fireEvent.click(within(screen.getByRole('region', { name: '正式内容' })).getByRole('button', { name: '确认并保存当前版本' }))
  expect(screen.getByRole('dialog').textContent).toContain('不会创建飞书任务')
  expect(calls.some(({ path }) => path.endsWith('/confirmations'))).toBe(false)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '取消' }))
  expect(calls.some(({ path }) => path.endsWith('/confirmations'))).toBe(false)
  fireEvent.click(within(screen.getByRole('region', { name: '正式内容' })).getByRole('button', { name: '确认并保存当前版本' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '确认并保存当前版本' }))
  await waitFor(() => expect(calls.some(({ path, method }) => path.endsWith('/pages/page-1/confirmations') && method === 'POST')).toBe(true))
  const request = calls.find(({ path }) => path.endsWith('/pages/page-1/confirmations'))
  expect(calls.filter(({ path, method }) => path.endsWith('/pages/page-1/confirmations') && method === 'POST')).toHaveLength(1)
  expect(request?.body).toMatchObject({ metadata: page.metadata, body: page.body, expected_base_sha256: page.content_sha256 })
})

it('准备计划需要自己的范围预览确认；action未知时仅提供核对', async () => {
  const confirmedPage = { ...page, approval_state: 'confirmed' }
  const { calls } = setup({ '/api/v1/pages': [confirmedPage], '/api/v1/action-intents?limit=20': { items: [{ ...intent, state: 'unknown' }], next_cursor: null } })
  await screen.findByText('合成速记')
  fireEvent.click(screen.getByRole('button', { name: '准备已确认的内容' }))
  await screen.findByText(/将准备 1 页已确认内容/)
  fireEvent.click(screen.getByRole('button', { name: '查看范围并确认' }))
  expect(screen.getByRole('dialog').textContent).toContain('演示模式只体验本机操作流程')
  expect(calls.some(({ path }) => path.endsWith('/index/jobs'))).toBe(false)
  expect(screen.getByText('结果未知，请核对')).toBeTruthy()
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '取消' }))
  expect(calls.some(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')).toBe(false)
})

it.each([
  ['Fake 模型变更', { state: 'ready', fingerprint: 'old-fingerprint', pages: 1, chunks: 1, current_pages: 1, stale_pages: 1 }, 'fake-fingerprint', 'model_change', '查看重新准备范围'],
  ['Fake stale 内容', { state: 'stale', fingerprint: 'fake-fingerprint', pages: 1, chunks: 1, current_pages: 1, stale_pages: 1 }, 'fake-fingerprint', 'incremental', '查看待更新内容'],
  ['Fake manual_required 内容', { state: 'manual_required', fingerprint: 'fake-fingerprint', pages: 1, chunks: 1, current_pages: 0, stale_pages: 1 }, 'fake-fingerprint', 'incremental', '查看待更新内容'],
] as const)('%s 只需本地范围确认即可执行', async (_label, indexStatus, configuredFingerprint, expectedMode, buttonLabel) => {
  const { calls } = setup({
    '/api/v1/index/status': indexStatus,
    '/api/v1/settings': { mode: 'fake', embedding_fingerprint: configuredFingerprint },
  })
  await screen.findByText('合成速记')
  fireEvent.click(screen.getByRole('button', { name: buttonLabel }))
  await screen.findByText(/将(检查|准备) 1 页/)
  expect(calls.find(({ path }) => path.endsWith('/index/plans'))?.body?.mode).toBe(expectedMode)
  expect(calls.some(({ path }) => path.endsWith('/acceptance-plans'))).toBe(false)
  expect(calls.some(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '查看范围并确认' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '确认并开始准备' }))
  await waitFor(() => expect(calls.some(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')).toBe(true))
  expect(calls.some(({ path }) => path.endsWith('/acceptance-plans'))).toBe(false)
  expect(calls.find(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')?.body).not.toHaveProperty('acceptance_plan_id')
})

it('Real 本地索引范围预览失败时清除旧计划且不开放确认或发起索引', async () => {
  const { calls, onError } = setup({ '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }], '/api/v1/settings': { mode: 'real', embedding_fingerprint: 'real-fingerprint', local_model: { state: 'ready' } }, '/api/v1/index/plans': new Error('准备范围读取失败') })
  await screen.findByText('合成速记')
  const preview = screen.getByRole('button', { name: '准备已确认的内容' })
  await waitFor(() => expect(preview).toHaveProperty('disabled', false))
  fireEvent.click(preview)
  await waitFor(() => expect(onError).toHaveBeenCalledWith('准备范围读取失败'))
  expect(screen.queryByText(/本次范围：/)).toBeNull()
  expect(screen.queryByRole('button', { name: '查看范围并确认' })).toBeNull()
  expect(calls.some(({ path }) => path.endsWith('/index/jobs') || path.endsWith('/confirm'))).toBe(false)
})

it('Real 本地索引先预览并单独确认，不创建付费授权计划', async () => {
  const { calls } = setup({ '/api/v1/pages': [{ ...page, approval_state: 'confirmed' }], '/api/v1/settings': { mode: 'real', embedding_fingerprint: 'real-fingerprint', local_model: { state: 'ready' } } })
  await screen.findByText('合成速记')
  fireEvent.click(screen.getByRole('button', { name: '准备已确认的内容' }))
  await screen.findByText(/将准备 1 页已确认内容/)
  fireEvent.click(screen.getByRole('button', { name: '查看范围并确认' }))
  const dialog = screen.getByRole('dialog')
  expect(dialog.textContent).toContain('本机模型将处理本次范围内的页面')
  expect(dialog.textContent).toContain('不会向 DeepSeek 或其他云端服务发送索引内容')
  fireEvent.click(within(dialog).getByRole('button', { name: '确认并开始准备' }))
  await waitFor(() => expect(calls.some(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')).toBe(true))
  expect(calls.some(({ path, method }) => path.endsWith('/index/plans') && method === 'POST')).toBe(true)
  expect(calls.some(({ path }) => path.endsWith('/acceptance-plans'))).toBe(false)
  expect(calls.find(({ path, method }) => path.endsWith('/index/jobs') && method === 'POST')?.body).not.toHaveProperty('acceptance_plan_id')
  expect(calls.find(({ path, method }) => path.endsWith('/index/plans') && method === 'POST')?.body).toMatchObject({ mode: 'initial', fingerprint: 'real-fingerprint' })
})
