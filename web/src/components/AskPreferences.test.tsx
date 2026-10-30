import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AskPreferences } from './AskPreferences'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const role = { role_id: 'role-1', name: '简明', instructions: '先列依据', context_budget: 2000, created_at: '', updated_at: '' }
const memory = { memory_id: 'memory-1', source_message_id: 'request-1', text: '合成记忆', created_at: '', updated_at: '' }
const candidate = { candidate_id: 'candidate-1', message_id: 'request-1', text: '合成候选', state: 'pending', created_at: '' }

function stubApi(overrides: Record<string, (init?: RequestInit) => Response | Promise<Response>> = {}) {
  const calls: { url: string; method: string; body?: string }[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    calls.push({ url, method, body: init?.body as string | undefined })
    const custom = overrides[`${method} ${url}`] ?? overrides[url]
    if (custom) return custom(init)
    if (url === '/api/v1/index/status') return Response.json({ fingerprint: 'fp', pages: 153, chunks: 900, state: 'stale', current_pages: 154, stale_pages: 1 })
    if (url === '/api/v1/roles') {
      if (method === 'POST') {
        const payload = JSON.parse(String(init?.body ?? '{}')) as { name?: string; instructions?: string; context_budget?: number }
        return Response.json({ ...role, role_id: 'role-new', name: payload.name ?? role.name, instructions: payload.instructions ?? '', context_budget: payload.context_budget ?? 2000 }, { status: 201 })
      }
      return Response.json([role])
    }
    if (url === '/api/v1/memory') return Response.json([memory])
    if (url === '/api/v1/memory/candidates') return Response.json([candidate])
    return Response.json({})
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock }
}

it('reads the index status and sends index work to Approval', async () => {
  stubApi()
  const onOpenApproval = vi.fn()
  render(<AskPreferences onOpenApproval={onOpenApproval} />)

  expect(await screen.findByText(/可索引 154 页/)).toBeTruthy()
  expect(screen.getByText(/已索引 153 页/)).toBeTruthy()
  expect(screen.getByText(/待更新 1 页/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '前往审批处理索引' }))
  expect(onOpenApproval).toHaveBeenCalledTimes(1)
})

it('shows index read failure and recovers on retry', async () => {
  let fail = true
  stubApi({
    'GET /api/v1/index/status': () => fail ? Promise.reject(new Error('索引读不到')) : Response.json({ fingerprint: 'fp', pages: 3, chunks: 4, state: 'ready', current_pages: 3, stale_pages: 0 }),
  })
  render(<AskPreferences />)
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', '索引读不到')
  fail = false
  fireEvent.click(screen.getByRole('button', { name: '重新读取' }))
  expect(await screen.findByText(/已索引 3 页/)).toBeTruthy()
})

it('saves a role and deletes a confirmed memory only after confirmation', async () => {
  const { calls } = stubApi()
  render(<AskPreferences />)

  await screen.findByLabelText('编辑已确认记忆')
  const memoryBlock = (await screen.findByRole('heading', { name: '问答记忆' })).closest('section')!
  fireEvent.click(within(memoryBlock).getByRole('button', { name: '删除记忆' }))
  const dialog = await screen.findByRole('dialog', { name: '删除这条已确认记忆？' })
  expect(calls.some(({ url, method }) => url === '/api/v1/memory/memory-1' && method === 'DELETE')).toBe(false)
  fireEvent.click(within(dialog).getByRole('button', { name: '确认删除' }))
  await waitFor(() => expect(calls.some(({ url, method }) => url === '/api/v1/memory/memory-1' && method === 'DELETE')).toBe(true))

  fireEvent.change(screen.getByLabelText('角色名称'), { target: { value: '新角色' } })
  fireEvent.click(screen.getByRole('button', { name: '保存角色' }))
  await waitFor(() => expect(calls.some(({ url, method }) => url === '/api/v1/roles' && method === 'POST')).toBe(true))
  expect(JSON.parse(calls.find(({ url, method }) => url === '/api/v1/roles' && method === 'POST')!.body!)).toMatchObject({ name: '新角色' })
})

it('confirms a memory candidate with the edited text', async () => {
  const { calls } = stubApi()
  render(<AskPreferences />)

  const input = await screen.findByLabelText('编辑记忆候选')
  fireEvent.change(input, { target: { value: '改过的候选' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并保存' }))
  await waitFor(() => expect(calls.some(({ url }) => url === '/api/v1/memory/candidates/candidate-1/confirmations')).toBe(true))
  expect(JSON.parse(calls.find(({ url }) => url.endsWith('/confirmations'))!.body!)).toMatchObject({ text: '改过的候选' })
})
