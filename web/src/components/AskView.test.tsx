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

it('creates a first conversation on the server, adopts its ID, then continues it', async () => {
  vi.stubGlobal('crypto', { randomUUID: vi.fn()
    .mockReturnValueOnce('first-request')
    .mockReturnValueOnce('second-request') })
  const bodies: Record<string, unknown>[] = []
  const queryAuthorization: string[] = []
  const reopened: string[] = []
  const serverConversation = 'server-created-conversation'
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      queryAuthorization.push(new Headers(init?.headers).get('Authorization') ?? '')
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      bodies.push(body)
      if (body.conversation_id !== undefined && body.conversation_id !== serverConversation) {
        return Response.json({ error: { code: 'not_found', message: 'conversation not found' } }, { status: 404 })
      }
      const requestId = String(body.request_id)
      const payload = [
        event(requestId, 1, 'status', { state: 'retrieving', conversation_id: serverConversation }),
        event(requestId, 2, 'delta', { text: `回答 ${bodies.length}` }),
        event(requestId, 3, 'completed', { text: `回答 ${bodies.length}` }),
      ].join('')
      return new Response(payload, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': serverConversation },
      })
    }
    if (url.endsWith(`/conversations/${serverConversation}/reopen`)) {
      reopened.push(url)
      const questions = bodies.map((body) => String(body.question))
      return Response.json({
        conversation_id: serverConversation, title: questions[0], created_at: '2026-10-11T01:00:00Z',
        updated_at: '2026-10-11T01:01:00Z', message_count: questions.length, state: 'completed',
        messages: questions.map((question, index) => ({
          request_id: String(bodies[index].request_id), question, answer: `回答 ${index + 1}`,
          state: 'completed', purpose: 'current', answer_mode: 'fact', citations: [], events: [], created_at: '2026-10-11T01:00:00Z',
        })),
      })
    }
    throw new Error(`Unexpected fetch ${url}`)
  })
  ;(window as Window & { __SUMMIT_SESSION_TOKEN__?: string }).__SUMMIT_SESSION_TOKEN__ = 'test-session'
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '首次问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('回答 1')).toBeTruthy()
  await waitFor(() => expect(reopened).toHaveLength(1))
  expect(bodies[0]).not.toHaveProperty('conversation_id')
  expect(queryAuthorization[0]).toBe('Bearer test-session')

  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '接着追问' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('回答 2')).toBeTruthy()
  await waitFor(() => expect(bodies).toHaveLength(2))
  expect(bodies[1]).toMatchObject({ question: '接着追问', conversation_id: serverConversation })
  expect(reopened).toHaveLength(2)
})

it('puts the question first and keeps history, indexing, and personalization collapsed', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  const question = await screen.findByLabelText('你的问题')
  const queryForm = question.closest('form')!
  const historySummary = screen.getByText('本机历史', { selector: 'summary' })
  expect(queryForm.compareDocumentPosition(historySummary.closest('details')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(historySummary.closest('details')?.open).toBe(false)
  expect(screen.getByText('本机索引与更新').closest('details')?.open).toBe(false)
  expect(screen.getByText('问答角色与记忆', { selector: 'summary' }).closest('details')?.open).toBe(false)
  expect(screen.getByText('资料范围与回答方式').closest('details')?.open).toBe(false)
})

it('requires confirmation before deleting local history, roles, or confirmed memories', async () => {
  const deletes: string[] = []
  const role = { role_id: 'role-1', name: '简明', instructions: '', context_budget: 2000, created_at: '', updated_at: '' }
  const memory = { memory_id: 'memory-1', source_message_id: 'private-request-id', text: '合成记忆', created_at: '', updated_at: '' }
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ conversation_id: 'conversation-1', title: '合成问题', updated_at: '', message_count: 1, state: 'completed' }], next_cursor: null })
    if (url.endsWith('/conversations/conversation-1')) { deletes.push(url); return new Response(null, { status: 204 }) }
    if (url === '/api/v1/roles') return method === 'DELETE' ? new Response(null, { status: 204 }) : Response.json([role])
    if (url === '/api/v1/memory') return method === 'DELETE' ? new Response(null, { status: 204 }) : Response.json([memory])
    if (url === '/api/v1/memory/candidates' || url === '/api/v1/pages') return Response.json([])
    if (url === '/api/v1/roles/role-1' || url === '/api/v1/memory/memory-1') { deletes.push(url); return new Response(null, { status: 204 }) }
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.click(await screen.findByText('本机历史', { selector: 'summary' }))
  fireEvent.click(await screen.findByRole('button', { name: '删除 合成问题' }))
  expect(screen.getByRole('dialog', { name: '删除这段问答历史？' })).toBeTruthy()
  expect(deletes).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(deletes).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '删除 合成问题' }))
  fireEvent.click(screen.getByRole('button', { name: '确认删除' }))
  await waitFor(() => expect(deletes).toContain('/api/v1/conversations/conversation-1'))

  fireEvent.click(screen.getByText('问答角色与记忆', { selector: 'summary' }))
  fireEvent.change(screen.getAllByLabelText('使用角色')[0], { target: { value: 'role-1' } })
  fireEvent.click(screen.getByRole('button', { name: '删除角色' }))
  expect(deletes).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: '确认删除' }))
  await waitFor(() => expect(deletes).toContain('/api/v1/roles/role-1'))

  fireEvent.click(screen.getByRole('button', { name: '删除记忆' }))
  expect(deletes).toHaveLength(2)
  fireEvent.click(screen.getByRole('button', { name: '确认删除' }))
  await waitFor(() => expect(deletes).toContain('/api/v1/memory/memory-1'))
  expect(rawFetch.mock.calls.some(([input]) => String(input).includes('private-request-id'))).toBe(false)
})

it('previews real question context and cancels without posting a query', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'stable-query' })
  const calls: { url: string; method: string }[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'; calls.push({ url, method })
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ mode: 'real', embedding_fingerprint: 'real-fp' })
    if (url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url.endsWith('/acceptance-plans') && method === 'POST') return Response.json({
      plan: { plan_id: 'query-plan', scope_sha256: 'scope-hash', request_limit: 3 },
      scope: { question: '合成问题', context: { role_instructions: '合成角色', user_memories: ['合成记忆'], previous_user_questions: ['前问'] }, source_versions: { 'page-1': 'a'.repeat(64) }, max_output_tokens: 2048 },
    })
    if (url.endsWith('/acceptance-plans/query-plan') && method === 'DELETE') return new Response(null, { status: 204 })
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('请确认本次问答发送范围')).toBeTruthy()
  expect(screen.getByText(/最多 3 次 HTTP 请求/)).toBeTruthy()
  expect(screen.getAllByText('合成问题')).toHaveLength(2)
  expect(calls.filter((item) => item.url === '/api/v1/queries')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '取消，不发送' }))
  await waitFor(() => expect(calls.some((item) => item.url.endsWith('/acceptance-plans/query-plan') && item.method === 'DELETE')).toBe(true))
  expect(calls.filter((item) => item.url === '/api/v1/queries')).toHaveLength(0)
})

it('revokes a real embedding plan when cancelling its scope preview', async () => {
  const calls: { url: string; method: string }[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'; calls.push({ url, method })
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ mode: 'real', embedding_fingerprint: 'real-fp' })
    if (url === '/api/v1/pages') return Response.json([{ page_id: 'page-1', metadata: { title: '合成页面' } }])
    if (url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/index/plans') return Response.json({ mode: 'initial', fingerprint: 'real-fp', page_ids: ['page-1'], page_versions: { 'page-1': 'a'.repeat(64) }, estimated_tokens: 1000, estimated_cost: null })
    if (url === '/api/v1/acceptance-plans') return Response.json({
      plan: { plan_id: 'index-plan', scope_sha256: 'b'.repeat(64), request_limit: 1 },
      scope: { mode: 'initial', fingerprint: 'real-fp', page_ids: ['page-1'], page_versions: { 'page-1': 'a'.repeat(64) } },
    })
    if (url === '/api/v1/acceptance-plans/index-plan' && method === 'DELETE') return new Response(null, { status: 200 })
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '准备索引计划' }))
  expect(await screen.findByText('真实索引范围待独立确认')).toBeTruthy()
  expect(screen.getByText('合成页面')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '取消计划' }))
  await waitFor(() => expect(calls.some((item) => item.url.endsWith('/acceptance-plans/index-plan') && item.method === 'DELETE')).toBe(true))
  expect(calls.some((item) => item.url === '/api/v1/index/jobs')).toBe(false)
})

it('reopens local history, continues the same conversation, and labels an updated citation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'next-request' })
  const original: Record<string, unknown> = {
    conversation_id: 'conversation-1', title: '旧问题', created_at: '2026-10-11T01:00:00Z',
    updated_at: '2026-10-11T01:00:00Z', message_count: 1, state: 'completed',
    messages: [{ request_id: 'old-request', question: '原问题', answer: '原回答', state: 'completed', purpose: 'current', answer_mode: 'fact', citations: [citation], events: [], created_at: '2026-10-11T01:00:00Z' }],
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
  expect(screen.getByText(/原引用版本已更新 · 引用版本仍可用/)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '继续追问' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  await waitFor(() => expect(requestBodies).toHaveLength(1))
  expect(requestBodies[0]).toMatchObject({
    question: '继续追问', conversation_id: 'conversation-1', request_id: 'next-request',
    fingerprint: 'fake-fingerprint', purpose: 'current',
  })
  expect(await screen.findByText('后续回答')).toBeTruthy()
  expect(await screen.findByText(/回答 · 事实问答 · 已完成/)).toBeTruthy()
})

it('lets the user opt into historical sources and labels their limited effect', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'history-request' })
  let submitted: Record<string, unknown> | null = null
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'fake-fingerprint', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      submitted = JSON.parse(String(init?.body)) as Record<string, unknown>
      return new Response([
        event('history-request', 1, 'status', { state: 'retrieving', conversation_id: 'history-conversation' }),
        event('history-request', 2, 'citation', { ...citation, validity: 'superseded', availability: 'available' }),
        event('history-request', 3, 'citation', { ...citation, page_id: 'invalid-history-page', validity: 'invalid', availability: 'updated' }),
        event('history-request', 4, 'completed', { text: '历史版本所载地点为北馆。' }),
      ].join(''), { status: 200, headers: { 'X-Conversation-ID': 'history-conversation' } })
    }
    if (url.endsWith('/conversations/history-conversation/reopen')) return Response.json({ conversation_id: 'history-conversation', title: '历史问题', created_at: '', updated_at: '', message_count: 1, state: 'completed', messages: [] })
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('资料范围'), { target: { value: 'history' } })
  expect(screen.getByText(/会包含已被替代或失效的版本/)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '旧版本地点是什么？' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  await waitFor(() => expect(submitted).toMatchObject({ purpose: 'history' }))
  expect(await screen.findByText('已被替代的历史版本，仅限历史参考')).toBeTruthy()
  expect(screen.getByText(/原引用版本已更新 · 已失效版本，仅限历史参考/)).toBeTruthy()
})

it('shows an explicit server input error without marking the query interrupted or saving history', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'budget-request' })
  let conversationReads = 0
  const onError = vi.fn()
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'fake-fingerprint', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) { conversationReads += 1; return Response.json({ items: [], next_cursor: null }) }
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') return Response.json({ error: { code: 'context_budget_exceeded', message: '角色说明超过设定预算；请编辑角色内容后重试。' } }, { status: 422 })
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={onError} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '请回答问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText('回答失败')).toBeTruthy()
  expect(screen.getByText('角色说明超过设定预算；请编辑角色内容后重试。')).toBeTruthy()
  expect(screen.queryByText(/连接中断/)).toBeNull()
  expect(conversationReads).toBe(1)
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
      return new Response(event('interrupted-request', 1, 'delta', { text: '部分' }), {
        status: 200, headers: { 'X-Conversation-ID': 'new-conversation' },
      })
    }
    if (url.endsWith('/reopen')) return Response.json({ conversation_id: 'new-conversation', title: '问题', created_at: '', updated_at: '', message_count: 1, state: 'interrupted', messages: [] })
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText(/连接已结束，回答未完整送达/)).toBeTruthy()
  expect(screen.getByText(/^部分/)).toBeTruthy()
  expect(queryCalls).toBe(1)
})

it.each([
  ['request id 不匹配', [event('other-request', 3, 'delta', { text: '不得显示' })]],
  ['seq 不连续', [event('malformed-request', 4, 'delta', { text: '不得显示' })]],
  ['终态后仍有事件', [event('malformed-request', 3, 'completed', { text: '部分回答' }), event('malformed-request', 4, 'error', { message: '重复终态' })]],
])('拒绝 %s 并保留部分内容且不自动重发', async (_label, trailingEvents) => {
  vi.stubGlobal('crypto', { randomUUID: () => 'malformed-request' })
  let queryCalls = 0
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      queryCalls += 1
      return new Response([
        event('malformed-request', 1, 'status', { state: 'retrieving', conversation_id: 'malformed-conversation' }),
        event('malformed-request', 2, 'delta', { text: '部分' }), ...trailingEvents,
      ].join(''), { status: 200, headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': 'malformed-conversation' } })
    }
    if (url.endsWith('/conversations/malformed-conversation/reopen')) return Response.json({ conversation_id: 'malformed-conversation', title: '合成问题', created_at: '', updated_at: '', message_count: 1, state: 'interrupted', messages: [] })
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText(/问答流顺序异常/)).toBeTruthy()
  expect(screen.getByText(/^部分/)).toBeTruthy()
  await waitFor(() => expect(queryCalls).toBe(1))
})

it('sends the selected answer mode and role, and confirms a server-verified memory candidate', async () => {
  vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValueOnce('request-1').mockReturnValueOnce('confirmation-1') })
  const role = { role_id: 'role-1', name: '简明', instructions: '先列依据', context_budget: 2000, created_at: '', updated_at: '' }
  const candidate = { candidate_id: 'candidate-1', message_id: 'request-1', text: '我偏好用简短中文回答，并明确标出资料没有提供的数字。', state: 'pending', created_at: '' }
  let roles: typeof role[] = []
  let candidates: typeof candidate[] = []
  const queryBodies: Record<string, unknown>[] = []
  let confirmation: Record<string, unknown> | null = null
  const conversation = {
    conversation_id: 'conversation-1', title: '工作问题', created_at: '', updated_at: '', message_count: 1, state: 'completed',
    messages: [{ request_id: 'request-1', question: '我偏好用简短中文回答，并明确标出资料没有提供的数字。', answer: '已确认资料回答。', state: 'completed', purpose: 'current', answer_mode: 'plan', source_statements: ['预算已确认。'], inferences: [], advice: ['补齐负责人。'], missing_information: ['未提供负责人。'], citations: [], events: [], created_at: '' }],
  }
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/roles') {
      if (init?.method === 'POST') { roles = [role]; return Response.json(role, { status: 201 }) }
      return Response.json(roles)
    }
    if (url === '/api/v1/memory') return Response.json([])
    if (url === '/api/v1/memory/candidates') {
      if (init?.method === 'POST') { candidates = [candidate]; return Response.json(candidate, { status: 201 }) }
      return Response.json(candidates)
    }
    if (url === '/api/v1/settings') return Response.json({ embedding_fingerprint: 'fake-fingerprint' })
    if (url === '/api/v1/queries') {
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      queryBodies.push(body)
      return new Response([
        event('request-1', 1, 'status', { state: 'retrieving', conversation_id: 'conversation-1' }),
        event('request-1', 2, 'completed', { text: '已确认资料回答。', source_statements: ['预算已确认。'], advice: ['补齐负责人。'], missing_information: ['未提供负责人。'] }),
      ].join(''), { status: 200, headers: { 'X-Conversation-ID': 'conversation-1' } })
    }
    if (url.endsWith('/conversations/conversation-1/reopen')) return Response.json(conversation)
    if (url.endsWith('/memory/candidates/candidate-1/confirmations')) {
      confirmation = JSON.parse(String(init?.body)) as Record<string, unknown>
      candidates = []
      return Response.json({ memory_id: 'memory-1', source_message_id: 'request-1', text: confirmation.text, created_at: '', updated_at: '' })
    }
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('角色名称'), { target: { value: '简明' } })
  fireEvent.change(screen.getByLabelText('表达偏好'), { target: { value: '先列依据' } })
  fireEvent.click(screen.getByRole('button', { name: '保存角色' }))
  expect(await screen.findAllByRole('option', { name: '简明' })).toHaveLength(2)
  fireEvent.change(screen.getByLabelText('回答方式'), { target: { value: 'plan' } })
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '这项计划下一步呢' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('补齐负责人。')).toBeTruthy()
  expect(await screen.findByText(/回答 · 工作方案 · 已完成/)).toBeTruthy()
  await waitFor(() => expect(queryBodies).toHaveLength(1))
  expect(queryBodies[0]).toMatchObject({ answer_mode: 'plan', role_id: 'role-1', question: '这项计划下一步呢' })

  fireEvent.click(await screen.findByLabelText('这是我本人表达的偏好或事实，不是我粘贴、转述的材料或引用'))
  fireEvent.click(await screen.findByRole('button', { name: '创建待确认记忆候选' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认并保存' }))
  await waitFor(() => expect(confirmation).toMatchObject({ confirmation_id: 'confirmation-1', text: '我偏好用简短中文回答，并明确标出资料没有提供的数字。' }))
})
