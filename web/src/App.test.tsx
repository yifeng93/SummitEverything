import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('keeps the updated citation version warning visible after navigating to the page', async () => {
  const oldHash = 'a'.repeat(64)
  const requestedPageUrls: string[] = []
  const citation = {
    page_id: 'page-1', content_sha256: oldHash, chunk_id: 'chunk-1',
    heading: '地点', excerpt: '会议地点是北馆。', validity: 'current', availability: 'updated',
  }
  const conversation = {
    conversation_id: 'conversation-1', title: '旧问题', created_at: '2026-10-11T01:00:00Z',
    updated_at: '2026-10-11T01:00:00Z', message_count: 1, state: 'completed',
    messages: [{ request_id: 'old-request', question: '会议在哪里？', answer: '北馆。', state: 'completed', purpose: 'current', citations: [citation], events: [], created_at: '2026-10-11T01:00:00Z' }],
  }
  const page = {
    page_id: 'page-1', relative_path: 'Projects/demo/location.md', metadata: { title: '地点' },
    body: '会议地点已改为西馆。', content_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current',
  }
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/workspaces/current') return Response.json({ workspace_id: 'workspace-1', root: '/tmp/workspace', local_profile_dir: '/tmp/profile', name: '测试工作库', read_only: false })
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ ...conversation, messages: undefined }], next_cursor: null })
    if (url.endsWith('/conversations/conversation-1/reopen')) return Response.json(conversation)
    if (url === `/api/v1/pages/page-1?expected_content_sha256=${oldHash}`) {
      requestedPageUrls.push(url)
      return Response.json({ error: { code: 'version_conflict', message: '页面版本已更新。' } }, { status: 409 })
    }
    if (url === '/api/v1/pages/page-1') return Response.json(page)
    if (url === '/api/v1/projects' || url === '/api/v1/pages') return Response.json([])
    if (url === '/api/v1/today' || url === '/api/v1/journal') return Response.json({ items: [] })
    // 外壳重构后 App 挂载时会读取今日与审批清单（侧栏徽章）；补全夹具，避免无关的加载失败提示。
    if (url === '/api/v1/intake/items' || url === '/api/v1/drafts' || url === '/api/v1/actions'
      || url === '/api/v1/lines' || url === '/api/v1/roles' || url === '/api/v1/memory'
      || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: '知识问答' }))
  fireEvent.click((await screen.findAllByRole('button', { name: /旧问题/ }))[0])
  fireEvent.click(await screen.findByRole('button', { name: /会议地点是北馆/ }))

  expect(await screen.findByText('会议地点已改为西馆。')).toBeTruthy()
  expect((await screen.findByRole('alert')).textContent).toContain('该页面已更新')
  await waitFor(() => expect(requestedPageUrls).toEqual([`/api/v1/pages/page-1?expected_content_sha256=${oldHash}`]))
  fireEvent.click(screen.getByRole('button', { name: '← 返回目录' }))
  expect(await screen.findByRole('button', { name: /会议地点是北馆/ })).toBeTruthy()
  expect(screen.queryByText('会议地点已改为西馆。')).toBeNull()
})
