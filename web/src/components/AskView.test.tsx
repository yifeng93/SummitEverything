import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AskView, clearConversationCacheForTests } from './AskView'
import { MarkdownText } from './MarkdownText'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); clearConversationCacheForTests() })

const citation = {
  page_id: 'page-1', content_sha256: 'a'.repeat(64), chunk_id: 'chunk-1',
  heading: '地点', excerpt: '会议地点是北馆。', validity: 'current' as const,
  availability: 'updated' as const,
}

const realQuerySettings = {
  mode: 'real', embedding_fingerprint: 'real-fp', keychain_available: true,
  credential_status: { deepseek: true, feishu_app: false },
  llm: { provider: 'deepseek', model: 'deepseek-flash', enabled: true },
  embedding: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', enabled: true },
  rerank: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', enabled: true },
  local_model: { state: 'ready' },
}

const readyQueryIndex = {
  fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0,
  vector: 'real',
}

// AskView now reads the complete runtime setup and index status before enabling
// a query. Merge older per-test overrides over a valid real-mode baseline so
// each test can still focus on its specific scenario.
function stubFetch(implementation: typeof fetch) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    try {
      const response = await implementation(input, init)
      if (!response.ok) return response
      if (url === '/api/v1/index/status') {
        const value = await response.clone().json() as Record<string, unknown>
        if (value.state === 'ready' && value.vector === undefined) return Response.json({ ...value, vector: 'real' })
      }
      if (url.endsWith('/acceptance-plans') && init?.method === 'POST') return response
      if (/\/acceptance-plans\/[^/]+\/(confirm)$/.test(url) && init?.method === 'POST') return response
      if (/\/acceptance-plans\/[^/]+$/.test(url) && init?.method === 'DELETE') return response
      return response
    } catch (error) {
      if (url === '/api/v1/settings') return Response.json(realQuerySettings)
      if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
      if (url.endsWith('/acceptance-plans') && init?.method === 'POST') return Response.json({ plan: { plan_id: 'test-plan', scope_sha256: 'test-scope', request_limit: 1 }, scope: {} }, { status: 201 })
      if (/\/acceptance-plans\/[^/]+\/(confirm)$/.test(url) && init?.method === 'POST') return Response.json({})
      if (/\/acceptance-plans\/[^/]+$/.test(url) && init?.method === 'DELETE') return new Response(null, { status: 204 })
      throw error
    }
  }))
}

async function startQuestion() {
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  await waitFor(() => expect(Boolean(screen.queryByRole('button', { name: '确认并发送本次问题' }) || document.querySelector('.query-recovery'))).toBe(true))
  const confirm = screen.queryByRole('button', { name: '确认并发送本次问题' })
  if (confirm) fireEvent.click(confirm)
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
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
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
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '首次问题' } })
  await startQuestion()
  expect(await screen.findByText('回答 1')).toBeTruthy()
  await waitFor(() => expect(reopened).toHaveLength(1))
  expect(bodies[0]).not.toHaveProperty('conversation_id')
  expect(queryAuthorization[0]).toBe('Bearer test-session')

  fireEvent.click(screen.getByRole('button', { name: /继续追问/ }))
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '接着追问' } })
  await startQuestion()
  expect(await screen.findByText('回答 2')).toBeTruthy()
  await waitFor(() => expect(bodies).toHaveLength(2))
  expect(bodies[1]).toMatchObject({ question: '接着追问', conversation_id: serverConversation })
  expect(reopened).toHaveLength(2)
})

it('puts the question first and keeps recent conversations below it', async () => {
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  const question = await screen.findByLabelText('你的问题')
  const queryForm = question.closest('form')!
  const historyHeading = await screen.findByRole('heading', { name: '最近的问答' })
  expect(queryForm.compareDocumentPosition(historyHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.getByLabelText('资料范围')).toBeTruthy()
  // 索引与角色记忆已经搬到设置页，问答页只剩「搜索 + 列表」。
  expect(screen.queryByRole('heading', { name: '本机索引与更新' })).toBeNull()
  expect(screen.queryByRole('heading', { name: '问答角色与记忆' })).toBeNull()
  expect(document.querySelector('.query-options details')).toBeNull()
})

it('shows loading while Ask history is unresolved, then shows empty only after success', async () => {
  let resolveHistory: ((response: Response) => void) | undefined
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.startsWith('/api/v1/conversations?')) return await new Promise<Response>((resolve) => { resolveHistory = resolve })
    if (url === '/api/v1/pages' || url === '/api/v1/roles') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  await screen.findByRole('heading', { name: '最近的问答' })
  expect(screen.getByText('正在读取问答历史…')).toBeTruthy()
  expect(screen.queryByText(/还没有问答历史/)).toBeNull()

  resolveHistory!(Response.json({ items: [], next_cursor: null }))
  expect(await screen.findByText(/还没有问答历史/)).toBeTruthy()
})

it('keeps Ask request failures distinct from successful empty results', async () => {
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/conversations?')) throw new Error('history unavailable')
    if (url === '/api/v1/pages' || url === '/api/v1/roles') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  await screen.findByRole('heading', { name: '最近的问答' })
  expect(await screen.findByText(/问答历史读取失败：history unavailable/)).toBeTruthy()
  expect(screen.queryByText(/还没有问答历史/)).toBeNull()
})

it('does not turn a cancelled partial answer into visible Markdown delimiters', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'partial-request' })
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/queries') {
      const payload = [
        event('partial-request', 1, 'delta', { text: '**半句尚未结束' }),
        event('partial-request', 2, 'error', { code: 'cancelled', message: '已取消' }),
      ].join('')
      return new Response(payload, { status: 200, headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': 'conversation-partial' } })
    }
    if (url.endsWith('/conversations/conversation-partial/reopen')) return Response.json({
      conversation_id: 'conversation-partial', title: '合成问题', created_at: '', updated_at: '', message_count: 1, state: 'cancelled',
      messages: [{ request_id: 'partial-request', question: '合成问题', answer: '**半句尚未结束', state: 'cancelled', purpose: 'current', answer_mode: 'fact', citations: [], events: [], created_at: '' }],
    })
    throw new Error(`Unexpected fetch ${url} ${init?.method ?? 'GET'}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  await startQuestion()
  await screen.findByText('半句尚未结束')
  expect(document.querySelector('.ask-view')?.textContent).not.toContain('**')
  expect(document.querySelector('.ask-view')?.textContent).toContain('半句尚未结束')
})

it('renders actual SSE delta frames with stable syntax and matches the terminal static DOM', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'golden-request' })
  let streamController: ReadableStreamDefaultController<Uint8Array> | undefined
  const encoder = new TextEncoder()
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/queries') return new Response(new ReadableStream<Uint8Array>({ start(controller) { streamController = controller } }), {
      status: 200, headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': 'stream-conversation' },
    })
    if (url.endsWith('/conversations/stream-conversation/reopen')) return Response.json({
      conversation_id: 'stream-conversation', title: '合成问题', created_at: '', updated_at: '', message_count: 1, state: 'completed',
      messages: [{ request_id: 'golden-request', question: '合成问题', answer: '**hello world**', state: 'completed', purpose: 'current', answer_mode: 'fact', citations: [], events: [], created_at: '' }],
    })
    throw new Error(`Unexpected fetch ${url} ${init?.method ?? 'GET'}`)
  })
  stubFetch( rawFetch)
  const { container } = render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  await startQuestion()
  await waitFor(() => expect(streamController).toBeTruthy())
  const send = (seq: number, type: string, data: Record<string, unknown>) => streamController!.enqueue(encoder.encode(event('golden-request', seq, type, data)))
  send(1, 'delta', { text: '**hello' })
  await screen.findByText('hello', { selector: '.answer-panel strong' })
  const answerPanel = container.querySelector('.answer-panel')!
  const recentHistory = container.querySelector('.recent-asks')!
  expect(answerPanel.compareDocumentPosition(recentHistory) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(container.querySelector('.answer-panel .answer-text')?.textContent).toContain('hello')
  expect(container.querySelector('.answer-panel .answer-text')?.textContent).not.toContain('**')
  send(2, 'delta', { text: ' world' })
  await waitFor(() => expect(container.querySelector('.answer-panel .answer-text')?.textContent).toContain('world'))
  expect(container.querySelector('.answer-panel .answer-text')?.textContent).not.toContain('**')
  send(3, 'completed', { text: '**hello world**' })
  streamController!.close()
  await screen.findByText('回答 · 事实问答 · 已完成')
  const answer = container.querySelector('.conversation-thread .answer-text')!
  const staticAnswer = render(<MarkdownText content="**hello world**" />)
  expect(answer.innerHTML).toBe(staticAnswer.container.querySelector('.markdown-content')?.innerHTML)
})

it('requires confirmation before deleting local history', async () => {
  const deletes: string[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ conversation_id: 'conversation-1', title: '合成问题', updated_at: '', message_count: 1, state: 'completed' }], next_cursor: null })
    if (url.endsWith('/conversations/conversation-1') && method === 'DELETE') { deletes.push(url); return new Response(null, { status: 204 }) }
    if (url === '/api/v1/roles' || url === '/api/v1/pages') return Response.json([])
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  await screen.findByRole('heading', { name: '最近的问答' })
  fireEvent.click(await screen.findByRole('button', { name: '删除 合成问题' }))
  expect(screen.getByRole('dialog', { name: '删除这段问答历史？' })).toBeTruthy()
  expect(deletes).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(deletes).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '删除 合成问题' }))
  fireEvent.click(screen.getByRole('button', { name: '确认删除' }))
  await waitFor(() => expect(deletes).toContain('/api/v1/conversations/conversation-1'))
})

it('previews real question context and cancels without posting a query', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'stable-query' })
  const calls: { url: string; method: string }[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'; calls.push({ url, method })
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url.endsWith('/acceptance-plans') && method === 'POST') return Response.json({
      plan: { plan_id: 'query-plan', scope_sha256: 'scope-hash', request_limit: 3 },
      scope: { question: '合成问题', context: { role_instructions: '合成角色', user_memories: ['合成记忆'], previous_user_questions: ['前问'] }, source_versions: { 'page-1': 'a'.repeat(64) }, max_output_tokens: 2048 },
    })
    if (url.endsWith('/acceptance-plans/query-plan') && method === 'DELETE') return new Response(null, { status: 204 })
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('请确认本次问答发送范围')).toBeTruthy()
  expect(screen.getByText(/最多 1 次云端请求：DeepSeek 生成回答；向量化与排序在本机完成/)).toBeTruthy()
  expect(screen.getAllByText('合成问题')).toHaveLength(2)
  expect(calls.filter((item) => item.url === '/api/v1/queries')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '取消，不发送' }))
  await waitFor(() => expect(calls.some((item) => item.url.endsWith('/acceptance-plans/query-plan') && item.method === 'DELETE')).toBe(true))
  expect(calls.filter((item) => item.url === '/api/v1/queries')).toHaveLength(0)
})

it('explains missing real providers before creating a plan and preserves the question for Settings', async () => {
  const calls: string[] = []
  const onOpenSettings = vi.fn()
  const incomplete = {
    ...realQuerySettings,
    mode: 'fake',
    llm: { provider: 'fake', model: null, enabled: false },
    embedding: { provider: 'fake', model: null, enabled: false },
    rerank: { provider: 'fake', model: null, enabled: false },
    credential_status: { deepseek: false, dashscope: false, feishu_app: false },
  }
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input); calls.push(url)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(incomplete)
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenSettings={onOpenSettings} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: '配置能力检查问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText(/真实问答暂不可用/)).toBeTruthy()
  expect(screen.getByText(/整理与问答模型仍为离线试用/)).toBeTruthy()
  expect(screen.queryByText('没有找到可引用的依据')).toBeNull()
  expect(screen.getByRole('button', { name: '前往设置完成真实连接' })).toBeTruthy()
  expect(calls.some((url) => url.endsWith('/acceptance-plans'))).toBe(false)
  expect(calls.some((url) => url === '/api/v1/queries')).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '前往设置完成真实连接' }))
  expect(onOpenSettings).toHaveBeenCalledTimes(1)
  expect(question.value).toBe('配置能力检查问题')
})

it('keeps submission disabled until settings and the index are rechecked after approval', async () => {
  let prepared = false
  const reads: string[] = []
  const onOpenApproval = vi.fn()
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/index/status') {
      reads.push('index')
      return Response.json(prepared ? readyQueryIndex : { ...readyQueryIndex, fingerprint: 'old-fp' })
    }
    if (url === '/api/v1/settings') { reads.push('settings'); return Response.json(realQuerySettings) }
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenApproval={onOpenApproval} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: '准备索引后恢复的问题' } })
  expect(await screen.findByText(/本地索引尚未就绪或待更新/)).toBeTruthy()
  expect((screen.getByRole('button', { name: '开始检索' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '前往审批检查或建立本地索引' }))
  expect(onOpenApproval).toHaveBeenCalledTimes(1)

  prepared = true
  const previousReads = reads.length
  fireEvent.click(screen.getByRole('button', { name: '重新检查就绪状态' }))
  await waitFor(() => expect(reads.length).toBeGreaterThan(previousReads + 1))
  expect(reads.slice(previousReads)).toEqual(expect.arrayContaining(['settings', 'index']))
  expect((screen.getByRole('button', { name: '开始检索' }) as HTMLButtonElement).disabled).toBe(false)
  expect(question.value).toBe('准备索引后恢复的问题')
})

it('keeps recovery actions inside a spaced error container', async () => {
  stubFetch(vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/acceptance-plans' && init?.method === 'POST') return Response.json({ plan: { plan_id: 'layout-plan', scope_sha256: 'hash', request_limit: 1 }, scope: { question: '布局检查' } }, { status: 201 })
    if (url.endsWith('/acceptance-plans/layout-plan/confirm')) return new Response(null, { status: 204 })
    if (url === '/api/v1/queries') return Response.json({ error: { code: 'local_model_not_ready', message: '合成服务错误' } }, { status: 409 })
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenSettings={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '布局检查' } })
  await startQuestion()
  const recovery = await screen.findByText('合成服务错误', { selector: '.form-error' })
  const container = recovery.parentElement!
  expect(container.classList.contains('query-recovery')).toBe(true)
  expect(container.firstElementChild?.classList.contains('form-error')).toBe(true)
  expect(container.querySelector('button')?.parentElement).toBe(container)
})

it('routes a stale Fake-index query to Approval before creating a paid plan and keeps the question', async () => {
  const calls: { url: string; method: string }[] = []
  const onOpenApproval = vi.fn()
  let planAttempts = 0
  let indexPrepared = false
  stubFetch( vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'
    calls.push({ url, method })
    if (url === '/api/v1/index/status') return Response.json(indexPrepared ? readyQueryIndex : { fingerprint: 'summit-fake-embedding-v1', pages: 154, chunks: 3532, state: 'ready', current_pages: 154, stale_pages: 0, vector: 'fake' })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/acceptance-plans' && method === 'POST') {
      planAttempts += 1
      return Response.json({ plan: { plan_id: 'retry-query-plan', scope_sha256: 'retry-hash', request_limit: 3 }, scope: { question: 'Fake索引切换后查价格' } }, { status: 201 })
    }
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenApproval={onOpenApproval} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: 'Fake索引切换后查价格' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText(/本地索引尚未就绪或待更新/)).toBeTruthy()
  expect((screen.getByRole('button', { name: '开始检索' }) as HTMLButtonElement).disabled).toBe(true)
  const approvalButton = screen.getByRole('button', { name: '前往审批检查或建立本地索引' })
  expect(question.value).toBe('Fake索引切换后查价格')
  expect(calls.some(({ url }) => url === '/api/v1/queries')).toBe(false)
  expect(calls.some(({ url, method }) => url.endsWith('/confirm') && method === 'POST')).toBe(false)
  expect(planAttempts).toBe(0)
  fireEvent.click(approvalButton)
  expect(onOpenApproval).toHaveBeenCalledTimes(1)

  // Once the user prepares an index, recheck both settings and index before
  // enabling a new real-operation preview.
  indexPrepared = true
  fireEvent.click(screen.getByRole('button', { name: '重新检查就绪状态' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: '前往审批检查或建立本地索引' })).toBeNull())
  expect((screen.getByRole('button', { name: '开始检索' }) as HTMLButtonElement).disabled).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByRole('button', { name: '确认并发送本次问题' })).toBeTruthy()
})

it('routes an index change after query preview back to Approval without clearing the question', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'index-changed-query' })
  const calls: { url: string; method: string }[] = []
  const onOpenApproval = vi.fn()
  stubFetch( vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'
    calls.push({ url, method })
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/acceptance-plans' && method === 'POST') return Response.json({ plan: { plan_id: 'query-plan', scope_sha256: 'scope-hash', request_limit: 3 }, scope: { question: '索引变动问题' } }, { status: 201 })
    if (url.endsWith('/acceptance-plans/query-plan/confirm')) return Response.json({})
    if (url === '/api/v1/queries') return Response.json({ error: { code: 'index_not_ready', message: '索引配置已变化，请重新准备。' } }, { status: 409 })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenApproval={onOpenApproval} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: '索引变动问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认并发送本次问题' }))

  expect(await screen.findByText('索引配置已变化，请重新准备。')).toBeTruthy()
  expect(screen.getByRole('button', { name: '前往审批建立或更新索引' })).toBeTruthy()
  expect(question.value).toBe('索引变动问题')
  expect(calls.some(({ url }) => url === '/api/v1/queries')).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '前往审批建立或更新索引' }))
  expect(onOpenApproval).toHaveBeenCalledTimes(1)
})

it('routes a server-detected provider change back to Settings without losing the question', async () => {
  const calls: string[] = []
  const onOpenSettings = vi.fn()
  stubFetch( vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); calls.push(url)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 1, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/acceptance-plans' && init?.method === 'POST') return Response.json({
      error: { code: 'provider_disabled', message: '所需 AI 服务尚未配置完成：检索结果排序未启用。' },
    }, { status: 409 })
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenSettings={onOpenSettings} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: '配置发生变化的问题' } })
  await startQuestion()
  expect(await screen.findByText(/本次问题尚未发送：所需 AI 服务尚未配置完成/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '前往设置完成真实连接' }))
  expect(onOpenSettings).toHaveBeenCalledTimes(1)
  expect(question.value).toBe('配置发生变化的问题')
  expect(calls.some((url) => url === '/api/v1/queries')).toBe(false)
})

it('allows ready local retrieval without a legacy DashScope credential', async () => {
  const calls: string[] = []
  stubFetch( vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'; calls.push(`${method} ${url}`)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/acceptance-plans' && method === 'POST') return Response.json({
      plan: { plan_id: 'local-ready-plan', scope_sha256: 'scope', request_limit: 1 },
      scope: { question: '本机检索问题', source_versions: {}, max_output_tokens: 2048, reasoning_effort: 'low' },
    }, { status: 201 })
    throw new Error(`Unexpected fetch ${method} ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '本机检索问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText('请确认本次问答发送范围')).toBeTruthy()
  expect(document.body.textContent).not.toContain('Model Studio')
  expect(calls.some((call) => call.includes('/credentials/'))).toBe(false)
  expect(calls.some((call) => call === 'POST /api/v1/queries')).toBe(false)
})

it('keeps the question and offers Settings when the local retrieval model is missing', async () => {
  const calls: string[] = []
  const onOpenSettings = vi.fn()
  const settings = { ...realQuerySettings, local_model: { state: 'not_prepared' } }
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input); calls.push(url)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(settings)
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenSettings={onOpenSettings} />)
  const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
  fireEvent.change(question, { target: { value: '模型缺失仍需保留的问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))

  expect(await screen.findByText(/本地检索模型尚未准备/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '前往设置完成真实连接' }))
  expect(onOpenSettings).toHaveBeenCalledTimes(1)
  expect(question.value).toBe('模型缺失仍需保留的问题')
  expect(calls.some((url) => url.endsWith('/acceptance-plans'))).toBe(false)
  expect(calls.some((url) => url.endsWith('/queries'))).toBe(false)
})

it.each(['local_model_not_ready', 'local_provider_required', 'legacy_provider_migration_required'])(
  'routes server query setup error %s to Settings without losing the question', async (code) => {
    const onOpenSettings = vi.fn()
    stubFetch( vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
      if (url === '/api/v1/settings') return Response.json(realQuerySettings)
      if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
      if (url === '/api/v1/acceptance-plans' && init?.method === 'POST') return Response.json({ error: { code, message: '本地检索配置需要处理' } }, { status: 409 })
      throw new Error(`Unexpected fetch ${url}`)
    }))
    render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} onOpenSettings={onOpenSettings} />)
    const question = await screen.findByLabelText('你的问题') as HTMLTextAreaElement
    fireEvent.change(question, { target: { value: `保留问题 ${code}` } })
    fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
    expect(await screen.findByText(/本次问题尚未发送：本地检索配置需要处理/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '前往设置完成真实连接' }))
    expect(onOpenSettings).toHaveBeenCalledTimes(1)
    expect(question.value).toBe(`保留问题 ${code}`)
  },
)

it('still previews, confirms, and executes a fully configured real query once', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'approved-query' })
  const calls: { url: string; method: string; body?: Record<string, unknown> }[] = []
  const conversationId = 'real-conversation'
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'
    const call = { url, method, ...(init?.body ? { body: JSON.parse(String(init.body)) as Record<string, unknown> } : {}) }
    calls.push(call)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'real-fp', pages: 1, chunks: 2, state: 'ready', current_pages: 1, stale_pages: 0 })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/acceptance-plans' && method === 'POST') return Response.json({
      plan: { plan_id: 'real-plan', scope_sha256: 'scope-hash', request_limit: 3 },
      scope: { question: '确认后的合成问题', source_versions: {}, max_output_tokens: 2048, reasoning_effort: 'low' },
    })
    if (url.endsWith('/acceptance-plans/real-plan/confirm')) return new Response(null, { status: 204 })
    if (url === '/api/v1/queries') {
      const body = call.body!
      return new Response([
        event(String(body.request_id), 1, 'status', { state: 'retrieving', conversation_id: conversationId }),
        event(String(body.request_id), 2, 'completed', { text: '合成真实模式回答' }),
      ].join(''), { headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': conversationId } })
    }
    if (url === `/api/v1/conversations/${conversationId}/reopen`) return Response.json({
      conversation_id: conversationId, title: '确认后的合成问题', created_at: '', updated_at: '', message_count: 1, state: 'completed',
      messages: [{ request_id: 'approved-query', question: '确认后的合成问题', answer: '合成真实模式回答', state: 'completed', purpose: 'current', answer_mode: 'fact', citations: [], events: [], created_at: '' }],
    })
    throw new Error(`Unexpected fetch ${method} ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '确认后的合成问题' } })
  fireEvent.click(screen.getByRole('button', { name: '开始检索' }))
  expect(await screen.findByText('请确认本次问答发送范围')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '确认并发送本次问题' }))
  expect(await screen.findByText('合成真实模式回答')).toBeTruthy()
  expect(calls.filter((item) => item.url === '/api/v1/queries')).toHaveLength(1)
  expect(calls.find((item) => item.url === '/api/v1/queries')?.body).toMatchObject({ acceptance_plan_id: 'real-plan', question: '确认后的合成问题' })
})

it('keeps a completed answer completed when the follow-up history refresh fails', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'history-refresh-query' })
  const queryCalls: string[] = []
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ ...readyQueryIndex })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/pages' || url === '/api/v1/roles' || url === '/api/v1/memory' || url === '/api/v1/memory/candidates') return Response.json([])
    if (url === '/api/v1/queries') {
      queryCalls.push(url)
      const body = JSON.parse(String(init?.body)) as { request_id: string }
      return new Response([
        event(body.request_id, 1, 'status', { state: 'retrieving', conversation_id: 'history-gap-conversation' }),
        event(body.request_id, 2, 'completed', { text: '已经完成的合成回答' }),
      ].join(''), { headers: { 'Content-Type': 'text/event-stream', 'X-Conversation-ID': 'history-gap-conversation' } })
    }
    if (url.endsWith('/conversations/history-gap-conversation/reopen')) throw new Error('synthetic history refresh failure')
    throw new Error(`Unexpected fetch ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '状态保留问题' } })
  await startQuestion()
  expect(await screen.findByText('已经完成的合成回答')).toBeTruthy()
  expect(screen.getByText('已完成')).toBeTruthy()
  expect(screen.getByText(/本次问答已结束，但历史同步失败/)).toBeTruthy()
  expect(queryCalls).toHaveLength(1)
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
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ ...original, messages: undefined }], next_cursor: null })
    if (url.endsWith('/conversations/conversation-1/reopen')) return Response.json(original)
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
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
  stubFetch( rawFetch)
  const onOpenPage = vi.fn()
  render(<AskView onError={vi.fn()} onOpenPage={onOpenPage} />)

  const openButton = (await screen.findAllByRole('button', { name: /旧问题/ }))[0]
  fireEvent.click(openButton)
  expect((await screen.findAllByText('原回答')).length).toBeGreaterThan(0)
  expect(screen.getByText(/原引用版本已更新 · 引用版本仍可用/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: /地点/ }))
  expect(onOpenPage).toHaveBeenCalledWith('page-1', 'a'.repeat(64))
  fireEvent.click(screen.getByRole('button', { name: /继续追问/ }))
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '继续追问' } })
  await startQuestion()

  await waitFor(() => expect(requestBodies).toHaveLength(1))
  expect(requestBodies[0]).toMatchObject({
    question: '继续追问', conversation_id: 'conversation-1', request_id: 'next-request',
    fingerprint: 'real-fp', purpose: 'current',
  })
  expect(await screen.findByText('后续回答')).toBeTruthy()
  expect(await screen.findByText(/回答 · 事实问答 · 已完成/)).toBeTruthy()
})

it('lets the user opt into historical sources and labels their limited effect', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'history-request' })
  let submitted: Record<string, unknown> | null = null
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json({ ...readyQueryIndex })
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
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
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('资料范围'), { target: { value: 'history' } })
  expect(screen.getByText(/会包含已被替代或失效的版本/)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '旧版本地点是什么？' } })
  await startQuestion()

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
    if (url === '/api/v1/index/status') return Response.json({ ...readyQueryIndex })
    if (url.startsWith('/api/v1/conversations?')) { conversationReads += 1; return Response.json({ items: [], next_cursor: null }) }
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/queries') return Response.json({ error: { code: 'context_budget_exceeded', message: '角色说明超过设定预算；请编辑角色内容后重试。' } }, { status: 422 })
    throw new Error(`Unexpected fetch ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={onError} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '请回答问题' } })
  await startQuestion()

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
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
    if (url === '/api/v1/queries') {
      queryCalls += 1
      return new Response(event('interrupted-request', 1, 'delta', { text: '部分' }), {
        status: 200, headers: { 'X-Conversation-ID': 'new-conversation' },
      })
    }
    if (url.endsWith('/reopen')) return Response.json({ conversation_id: 'new-conversation', title: '问题', created_at: '', updated_at: '', message_count: 1, state: 'interrupted', messages: [] })
    throw new Error(`Unexpected fetch ${url}`)
  })
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '问题' } })
  await startQuestion()

  expect(await screen.findByText(/连接已结束，回答未完整送达/)).toBeTruthy()
  expect(screen.getByText(/^部分/)).toBeTruthy()
  expect(screen.queryByText('没有找到可引用的依据')).toBeNull()
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
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [], next_cursor: null })
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
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
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('你的问题'), { target: { value: '合成问题' } })
  await startQuestion()
  expect(await screen.findByText(/问答流顺序异常/)).toBeTruthy()
  expect(screen.getByText(/^部分/)).toBeTruthy()
  await waitFor(() => expect(queryCalls).toBe(1))
})

it('sends the selected answer mode and role, and confirms a server-verified memory candidate', async () => {
  vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValueOnce('request-1').mockReturnValueOnce('confirmation-1') })
  const role = { role_id: 'role-1', name: '简明', instructions: '先列依据', context_budget: 2000, created_at: '', updated_at: '' }
  const candidate = { candidate_id: 'candidate-1', message_id: 'request-1', text: '我偏好用简短中文回答，并明确标出资料没有提供的数字。', state: 'pending', created_at: '' }
  let roles: typeof role[] = [role]
  let candidates: typeof candidate[] = []
  const queryBodies: Record<string, unknown>[] = []
  let confirmation: Record<string, unknown> | null = null
  const conversation = {
    conversation_id: 'conversation-1', title: '工作问题', created_at: '', updated_at: '', message_count: 1, state: 'completed',
    messages: [{ request_id: 'request-1', question: '我偏好用简短中文回答，并明确标出资料没有提供的数字。', answer: '已确认资料回答。', state: 'completed', purpose: 'current', answer_mode: 'plan', source_statements: ['预算已确认。'], inferences: [], advice: ['补齐负责人。'], missing_information: ['未提供负责人。'], citations: [], events: [], created_at: '' }],
  }
  const rawFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/index/status') return Response.json(readyQueryIndex)
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
    if (url === '/api/v1/settings') return Response.json(realQuerySettings)
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
  stubFetch( rawFetch)
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  const roleSelect = await screen.findByLabelText('本次使用角色')
  await screen.findByRole('option', { name: '简明' })
  fireEvent.change(roleSelect, { target: { value: 'role-1' } })
  fireEvent.change(screen.getByLabelText('回答方式'), { target: { value: 'plan' } })
  fireEvent.change(screen.getByLabelText('你的问题'), { target: { value: '这项计划下一步呢' } })
  await startQuestion()
  expect(await screen.findByText('补齐负责人。')).toBeTruthy()
  expect(await screen.findByText(/回答 · 工作方案 · 已完成/)).toBeTruthy()
  await waitFor(() => expect(queryBodies).toHaveLength(1))
  expect(queryBodies[0]).toMatchObject({ answer_mode: 'plan', role_id: 'role-1', question: '这项计划下一步呢' })

  fireEvent.click(await screen.findByLabelText('这是我本人表达的偏好或事实，不是我粘贴、转述的材料或引用'))
  fireEvent.click(await screen.findByRole('button', { name: '创建待确认记忆候选' }))
  // 候选只在问答页创建；确认动作在设置 → 知识问答里完成。
  await waitFor(() => expect(rawFetch.mock.calls.some(([url, init]) => String(url).endsWith('/memory/candidates') && (init as RequestInit | undefined)?.method === 'POST')).toBe(true))
})

it('shows opening feedback and ignores repeated clicks while a conversation loads', async () => {
  let finishReopen: ((response: Response) => void) | undefined
  const reopenCalls: string[] = []
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ conversation_id: 'c-1', title: '合成问题', updated_at: '2026-10-28T22:01:51Z', message_count: 1, state: 'completed' }], next_cursor: null })
    if (url.endsWith('/conversations/c-1/reopen')) { reopenCalls.push(url); return await new Promise<Response>((resolve) => { finishReopen = resolve }) }
    if (url === '/api/v1/pages' || url === '/api/v1/roles') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  const row = await screen.findByRole('button', { name: /^合成问题/ })
  fireEvent.click(row)
  expect(await screen.findByText('正在打开这段对话…')).toBeTruthy()
  // 连点：同一段落只发一次请求
  fireEvent.click(row)
  fireEvent.click(row)
  expect(reopenCalls).toHaveLength(1)

  finishReopen!(Response.json({ conversation_id: 'c-1', title: '合成问题', created_at: '', updated_at: '', message_count: 1, state: 'completed', messages: [{ request_id: 'r-1', question: '合成问题', answer: '合成回答', state: 'completed', purpose: 'current', answer_mode: 'fact', source_statements: [], inferences: [], advice: [], missing_information: [], citations: [], events: [], created_at: '' }] }))
  expect(await screen.findByText('合成回答')).toBeTruthy()
})

it('paints a cached conversation immediately, then refreshes it in the background', async () => {
  let reopenCount = 0
  stubFetch( vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.startsWith('/api/v1/conversations?')) return Response.json({ items: [{ conversation_id: 'cache-1', title: '缓存问题', updated_at: '2026-10-28T22:01:51Z', message_count: 1, state: 'completed' }], next_cursor: null })
    if (url.endsWith('/conversations/cache-1/reopen')) {
      reopenCount += 1
      const answer = reopenCount === 1 ? '第一次回答' : '后台刷新后的回答'
      return Response.json({ conversation_id: 'cache-1', title: '缓存问题', created_at: '', updated_at: '', message_count: 1, state: 'completed', messages: [{ request_id: 'r-1', question: '缓存问题', answer, state: 'completed', purpose: 'current', answer_mode: 'fact', source_statements: [], inferences: [], advice: [], missing_information: [], citations: [], events: [], created_at: '' }] })
    }
    if (url === '/api/v1/pages' || url === '/api/v1/roles') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  }))
  render(<AskView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.click(await screen.findByRole('button', { name: /^缓存问题/ }))
  expect(await screen.findByText('第一次回答')).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: '返回最近的问答' }))
  fireEvent.click(await screen.findByRole('button', { name: /^缓存问题/ }))

  // 第二次打开：先铺缓存，不出现 loading；后台再换成最新内容。
  expect(screen.queryByText('正在打开这段对话…')).toBeNull()
  expect(await screen.findByText('第一次回答')).toBeTruthy()
  await waitFor(() => expect(screen.getByText('后台刷新后的回答')).toBeTruthy())
  expect(reopenCount).toBe(2)
})
