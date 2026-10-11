import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AskView } from './AskView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const citation = {
  page_id: 'page-1', content_sha256: 'a'.repeat(64), chunk_id: 'chunk-1',
  heading: '地点', excerpt: '会议地点是北馆。', validity: 'current' as const,
  availability: 'updated' as const,
}

function event(requestId: string, seq: number, type: string, data: Record<string, unknown>) {
  return `data: ${JSON.stringify({ request_id: requestId, seq, type, data })}\n\n`
}

it('reopens local history, continues the same conversation, and labels an updated citation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'next-request' })
  const original: Record<string, unknown> = {
    conversation_id: 'conversation-1', title: '旧问题', created_at: '2026-10-11T01:00:00Z',
    updated_at: '2026-10-11T01:00:00Z', message_count: 1, state: 'completed',
    messages: [{ request_id: 'old-request', question: '原问题', answer: '原回答', state: 'completed', purpose: 'current', citations: [citation], events: [], created_at: '2026-10-11T01:00:00Z' }],
  }
  const requestBodies: Record<string, unknown>[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ ...original, messages: undefined }], next_cursor: null })
    if (url.endsWith('/conversations/conversation-1/reopen')) return Response.json(original)
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      requestBodies.push(body)
      const payload = [
        event('next-request', 1, 'status', { state: 'retrieving', conversation_id: 'conversation-1' }),
        event('next-request', 2, 'delta', { text: '后续回答' }),
        event('next-request', 3, 'completed', { text: '后续回答' }),
      ].join('')
      return new Response(payload, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
    }
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  const openButton = (await screen.findAllByRole('button', { name: /旧问题/ }))[0]
  fireEvent.click(openButton)
  expect((await screen.findAllByText('原回答')).length).toBeGreaterThan(0)
  expect(screen.getByText('原引用版本已更新')).toBeTruthy()
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '继续追问' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  await waitFor(() => expect(requestBodies).toHaveLength(1))
  expect(requestBodies[0]).toMatchObject({
    question: '继续追问', conversation_id: 'conversation-1', request_id: 'next-request',
    fingerprint: 'fake-fingerprint', purpose: 'current',
  })
  expect(await screen.findByText('后续回答')).toBeTruthy()
  expect(await screen.findByText('回答 · 已完成')).toBeTruthy()
})

it('does not retry a stream that ends without its single terminal event', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'interrupted-request' })
  let queryCalls = 0
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      queryCalls += 1
      return new Response(event('interrupted-request', 1, 'delta', { text: '部分' }), { status: 200 })
    }
    if (url.endsWith('/reopen')) return Response.json({ conversation_id: 'new-conversation', title: '问题', created_at: '', updated_at: '', message_count: 1, state: 'interrupted', messages: [] })
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText(/连接已结束，回答未完整送达/)).toBeTruthy()
  expect(screen.getByText('部分')).toBeTruthy()
  expect(queryCalls).toBe(1)
})
