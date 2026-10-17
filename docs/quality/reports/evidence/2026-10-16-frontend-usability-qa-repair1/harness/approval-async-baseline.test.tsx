import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ApprovalView } from '../baseline/web/src/components/ApprovalView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const item = (id: string, sourceId: string, title: string) => ({ item_id: id, source_id: sourceId, origin_kind: 'quick_note', title, filename: `${title}.md`, original_relative_path: 'synthetic/path.md', created_at: '2026-10-16T00:00:00Z', state: 'pending' })
const basics: Record<string, unknown> = {
  '/api/v1/drafts': [], '/api/v1/pages': [],
  '/api/v1/index/status': { state: 'not_ready', fingerprint: null, pages: 0, chunks: 0, current_pages: 0, stale_pages: 0 },
  '/api/v1/actions': [], '/api/v1/action-intents?limit=20': { items: [], next_cursor: null },
  '/api/v1/settings': { mode: 'fake', embedding_fingerprint: null },
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done }); return { promise, resolve } }
function fetchStub(handler: (path: string) => Promise<Response> | Response) {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => handler(String(input).replace('http://localhost', ''))))
}
function sourceDetail(sourceId: string, text: string) { return Response.json({ source: { source_id: sourceId, filename: `${sourceId}.md`, origin_kind: 'quick_note' }, text }) }

it('does not consume an exact-ID target before delayed source data exists', async () => {
  const response = deferred<Response>()
  const handled = vi.fn()
  fetchStub((path) => path === '/api/v1/intake/items' ? response.promise : path.startsWith('/api/v1/sources/') ? sourceDetail('late', 'late body') : Response.json(basics[path] ?? []))
  render(<ApprovalView target={{ kind: 'source', itemIds: ['late'] }} onTargetHandled={handled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(fetch).toHaveBeenCalled())
  expect(handled).not.toHaveBeenCalled()
  expect(screen.queryByText(/已定位到本次保存/)).toBeNull()
  await act(async () => { response.resolve(Response.json([item('late', 'late', '稍后到达')])) })
  const focus = await screen.findByRole('region', { name: '来源详情：稍后到达' })
  expect(within(focus).getByText('late body')).toBeTruthy()
  expect(handled).toHaveBeenCalledTimes(1)
})

it('prevents an older refresh epoch from replacing the latest exact-ID target', async () => {
  const first = deferred<Response>()
  let listReads = 0
  const oldItem = item('old-id', 'old-source', '旧目标')
  const latestItem = item('new-id', 'new-source', '最新目标')
  fetchStub((path) => {
    if (path === '/api/v1/intake/items') { listReads += 1; return listReads === 1 ? first.promise : Response.json([latestItem]) }
    if (path === '/api/v1/sources/new-source') return sourceDetail('new-source', '当前正文')
    if (path === '/api/v1/sources/old-source') return sourceDetail('old-source', '迟到旧正文')
    return Response.json(basics[path] ?? [])
  })
  const props = { onTargetHandled: vi.fn(), onPendingCount: vi.fn(), onError: vi.fn() }
  const view = render(<ApprovalView {...props} target={{ kind: 'source', itemIds: ['old-id'] }} />)
  await waitFor(() => expect(listReads).toBe(1))
  view.rerender(<ApprovalView {...props} target={{ kind: 'source', itemIds: ['new-id'] }} refreshEpoch={1} />)
  const current = await screen.findByRole('region', { name: '来源详情：最新目标' })
  expect(within(current).getByText('当前正文')).toBeTruthy()
  await act(async () => { first.resolve(Response.json([oldItem])) })
  await waitFor(() => expect(screen.getByRole('region', { name: '来源详情：最新目标' })).toBeTruthy())
  expect(screen.queryByRole('region', { name: '来源详情：旧目标' })).toBeNull()
  expect(screen.getByText('当前正文')).toBeTruthy()
})

it('does not let an older source-detail response replace the current route', async () => {
  const oldDetail = deferred<Response>()
  const handled = vi.fn()
  fetchStub((path) => {
    if (path === '/api/v1/intake/items') return Response.json([item('a', 'source-a', '先选材料'), item('b', 'source-b', '后选材料')])
    if (path === '/api/v1/sources/source-a') return oldDetail.promise
    if (path === '/api/v1/sources/source-b') return sourceDetail('source-b', '当前来源正文')
    return Response.json(basics[path] ?? [])
  })
  const view = render(<ApprovalView target={{ kind: 'source', itemIds: ['a'] }} onTargetHandled={handled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/sources/source-a'))).toBe(true))
  view.rerender(<ApprovalView target={{ kind: 'source', itemIds: ['b'] }} onTargetHandled={handled} onPendingCount={vi.fn()} onError={vi.fn()} />)
  const current = await screen.findByRole('region', { name: '来源详情：后选材料' })
  expect(within(current).getByText('当前来源正文')).toBeTruthy()
  await act(async () => { oldDetail.resolve(sourceDetail('source-a', '过期来源正文')) })
  expect(screen.getByText('当前来源正文')).toBeTruthy()
  expect(screen.queryByText('过期来源正文')).toBeNull()
})

it('allows already-handled target detail to finish during a later refresh', async () => {
  const detail = deferred<Response>()
  let listReads = 0
  const handled = vi.fn()
  fetchStub((path) => {
    if (path === '/api/v1/intake/items') { listReads += 1; return Response.json([item('x', 'source-x', '已消费目标')]) }
    if (path === '/api/v1/sources/source-x') return detail.promise
    return Response.json(basics[path] ?? [])
  })
  const props = { target: { kind: 'source', itemIds: ['x'] } as const, onTargetHandled: handled, onPendingCount: vi.fn(), onError: vi.fn() }
  const view = render(<ApprovalView {...props} />)
  await waitFor(() => expect(handled).toHaveBeenCalledTimes(1))
  view.rerender(<ApprovalView {...props} target={null} refreshEpoch={1} />)
  await waitFor(() => expect(listReads).toBe(2))
  await act(async () => { detail.resolve(sourceDetail('source-x', '刷新时仍应完成')) })
  const focus = await screen.findByRole('region', { name: '来源详情：已消费目标' })
  expect(within(focus).getByText('刷新时仍应完成')).toBeTruthy()
})

it('safely ignores a delayed response after the view unmounts', async () => {
  const detail = deferred<Response>()
  fetchStub((path) => path === '/api/v1/intake/items' ? Response.json([item('u', 'source-u', '待卸载')]) : path === '/api/v1/sources/source-u' ? detail.promise : Response.json(basics[path] ?? []))
  const view = render(<ApprovalView target={{ kind: 'source', itemIds: ['u'] }} onPendingCount={vi.fn()} onError={vi.fn()} />)
  await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/sources/source-u'))).toBe(true))
  view.unmount()
  await act(async () => { detail.resolve(sourceDetail('source-u', '卸载后返回')) })
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(screen.queryByText('卸载后返回')).toBeNull()
})
