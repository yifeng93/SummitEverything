import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TodayView } from './TodayView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function mockApi(overrides: Record<string, unknown> = {}) {
  const requests: { path: string; method: string; body?: unknown }[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input), method = init?.method ?? 'GET'
    requests.push({ path, method, body: typeof init?.body === 'string' ? JSON.parse(init.body) : init?.body })
    let data: unknown = []
    if (path.endsWith('/integrations/feishu/status')) data = { mode: 'fake', authorized: true, scopes: [], token_type: 'user' }
    for (const [route, value] of Object.entries(overrides)) if (path.endsWith(route) || path.split('?')[0].endsWith(route)) data = value
    if (path.endsWith('/intake/items') && method === 'POST') data = { item_id: 'new', origin_kind: 'quick_note', state: 'pending' }
    return { ok: true, status: 200, json: async () => data }
  }))
  return requests
}

it('places meetings and tasks beside capture tools while keeping remote data opt-in', async () => {
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  render(<TodayView onError={vi.fn()} />)
  const schedule = screen.getByRole('region', { name: '今天的安排' })
  const capture = screen.getByRole('region', { name: '记录与导入' })
  expect(schedule.contains(screen.getByRole('heading', { name: '会议' }))).toBe(true)
  expect(schedule.contains(screen.getByRole('heading', { name: '待办任务' }))).toBe(true)
  expect(capture.contains(screen.getByRole('heading', { name: '记录与导入' }))).toBe(true)
  expect(screen.getByRole('button', { name: '导入材料' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: '需要行动' })).toBeNull()
  await waitFor(() => expect(screen.getByText('还没有最近材料。')).toBeTruthy())
  expect(requests.some((item) => item.path.includes('/calendar?') || item.path.includes('/integrations/feishu/tasks?'))).toBe(false)
  expect(screen.queryByRole('button', { name: /授权飞书/ })).toBeNull()
  await waitFor(() => expect(requests.some((item) => item.path.endsWith('/integrations/feishu/status'))).toBe(true))
})

it('keeps a successful note receipt in place and continues with the exact saved item id', async () => {
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  const onOpenApproval = vi.fn()
  render(<TodayView onError={vi.fn()} onOpenApproval={onOpenApproval} />)
  const note = screen.getByLabelText('记下一句话')
  fireEvent.change(note, { target: { value: '本机合成会议记录' } })
  fireEvent.click(screen.getByRole('button', { name: '保存原文' }))
  await screen.findByRole('status', { name: /原文已保存/ })
  expect((screen.getByLabelText('记下一句话') as HTMLTextAreaElement).value).toBe('')
  fireEvent.click(screen.getByRole('button', { name: '继续整理' }))
  expect(onOpenApproval).toHaveBeenCalledWith({ kind: 'source', itemIds: ['new'] })
  expect(requests.some((item) => item.path.endsWith('/drafts') || item.path.includes('/intake/jobs'))).toBe(false)
})

it('offers a direct connection action when calendar authorization is unavailable', async () => {
  mockApi({ '/integrations/feishu/status': { mode: 'fake', authorized: false, scopes: [], token_type: 'user' } })
  const onOpenConnectionWizard = vi.fn()
  render(<TodayView onError={vi.fn()} onOpenConnectionWizard={onOpenConnectionWizard} />)
  fireEvent.click(await screen.findByRole('button', { name: '连接飞书' }))
  expect(onOpenConnectionWizard).toHaveBeenCalledTimes(1)
})

it('continues from a successful file import with the returned source item id', async () => {
  const onOpenApproval = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/integrations/feishu/status')) return Response.json({ mode: 'fake', authorized: false })
    if (path.endsWith('/intake/files') && init?.method === 'POST') return Response.json({ item_id: 'exact-file-item', origin_kind: 'file', state: 'pending' }, { status: 201 })
    if (path.endsWith('/intake/items')) return Response.json([])
    return Response.json([])
  }))
  render(<TodayView onError={vi.fn()} onOpenApproval={onOpenApproval} />)
  fireEvent.click(screen.getByRole('button', { name: '导入材料' }))
  fireEvent.change(await screen.findByLabelText('选择多个文件'), { target: { files: [new File(['record'], 'record.md')] } })
  fireEvent.click(screen.getByRole('button', { name: '导入可用文件' }))
  await screen.findByRole('status', { name: /原文已保存/ })
  fireEvent.click(screen.getByRole('button', { name: '继续整理' }))
  expect(onOpenApproval).toHaveBeenCalledWith({ kind: 'source', itemIds: ['exact-file-item'] })
})

it('trusts route-derived source types and keeps legacy unknown unclassified even when filenames look meaningful', async () => {
  mockApi({ '/actions': [], '/intake/items': [
    { item_id: 'n', title: '随手想法', filename: 'daily.md', origin_kind: 'quick_note', state: 'pending', created_at: '2026-10-15T00:00:00Z' },
    { item_id: 'f', title: '本机资料', filename: 'meeting.md', origin_kind: 'file', state: 'pending', created_at: '2026-10-15T00:00:00Z' },
    { item_id: 'legacy', title: '旧记录', filename: 'meeting.md', state: 'pending', created_at: '2026-10-15T00:00:00Z' },
  ] })
  render(<TodayView onError={vi.fn()} />)
  expect(await screen.findByText(/来源类型待核实/)).toBeTruthy()
  expect(screen.getByText('本机资料').closest('li')?.textContent).toContain('本机文件')
  expect(screen.getByText('随手想法').closest('li')?.textContent).toContain('记一句')
})

it('saves a quick note from Enter as source bytes without starting drafting or model work', async () => {
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  render(<TodayView onError={vi.fn()} />)
  await screen.findByText('还没有最近材料。')
  const original = '  合成的一句话  \n'
  fireEvent.change(screen.getByLabelText('记下一句话'), { target: { value: original } })
  fireEvent.keyDown(screen.getByLabelText('记下一句话'), { key: 'Enter', shiftKey: false })
  await waitFor(() => expect(requests.some((item) => item.path.endsWith('/intake/items') && item.method === 'POST')).toBe(true))
  const save = requests.find((item) => item.path.endsWith('/intake/items') && item.method === 'POST')!
  expect(save.body).toMatchObject({ text: original, operation_id: expect.any(String) })
  expect(requests.some((item) => item.path.endsWith('/drafts') || item.path.includes('/intake/jobs') || item.path.includes('/journal/assist'))).toBe(false)
})

it('does not save Enter used to confirm an IME composition', async () => {
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  render(<TodayView onError={vi.fn()} />)
  const note = screen.getByLabelText('记下一句话')
  fireEvent.change(note, { target: { value: '合成中文' } })
  fireEvent.keyDown(note, { key: 'Enter', shiftKey: false, isComposing: true })
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(requests.some((item) => item.path.endsWith('/intake/items') && item.method === 'POST')).toBe(false)
})

it('single-flights same-event quick-note submits while the request is pending', async () => {
  const requests: Record<string, unknown>[] = []
  let finishSave: ((response: Response) => void) | undefined
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/integrations/feishu/status')) return Response.json({ mode: 'fake', authorized: false })
    if (path.endsWith('/intake/items') && init?.method === 'POST') {
      requests.push(JSON.parse(String(init.body)) as Record<string, unknown>)
      return await new Promise<Response>((resolve) => { finishSave = resolve })
    }
    if (path.endsWith('/intake/items')) return Response.json([])
    return Response.json([])
  }))
  render(<TodayView onError={vi.fn()} />)
  const note = screen.getByLabelText('记下一句话')
  fireEvent.change(note, { target: { value: '同一条双击记录' } })
  fireEvent.keyDown(note, { key: 'Enter', shiftKey: false })
  fireEvent.keyDown(note, { key: 'Enter', shiftKey: false })
  await waitFor(() => expect(requests).toHaveLength(1))
  finishSave?.(Response.json({ item_id: 'saved', origin_kind: 'quick_note', state: 'pending' }, { status: 201 }))
  expect(requests).toHaveLength(1)
})

it('keeps the import dialog open during an in-flight local file write and restores focus on Escape', async () => {
  let finishUpload: ((response: Response) => void) | undefined
  const originalFetch = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith('/integrations/feishu/status')) return Response.json({ mode: 'fake', authorized: false })
    if (String(input).endsWith('/intake/items')) return Response.json([])
    if (String(input).endsWith('/intake/files')) return await new Promise<Response>((resolve) => { finishUpload = resolve })
    return Response.json([])
  })
  vi.stubGlobal('fetch', originalFetch)
  render(<TodayView onError={vi.fn()} />)
  const open = screen.getByRole('button', { name: '导入材料' })
  open.focus()
  fireEvent.click(open)
  const dialog = await screen.findByRole('dialog', { name: '导入材料' })
  const file = new File(['content'], 'meeting.md', { type: 'text/markdown' })
  fireEvent.change(screen.getByLabelText('选择多个文件'), { target: { files: [file] } })
  fireEvent.click(screen.getByRole('button', { name: '导入可用文件' }))
  await screen.findByText(/正在处理导入/)
  expect(screen.getByRole('button', { name: '关闭' })).toHaveProperty('disabled', true)
  finishUpload?.(Response.json({ item_id: 'file', origin_kind: 'file', state: 'pending' }, { status: 201 }))
  await waitFor(() => expect(screen.getByText('meeting.md').closest('li')?.textContent).toContain('已导入'))
  fireEvent.keyDown(dialog, { key: 'Escape' })
  await waitFor(() => expect(screen.queryByRole('dialog', { name: '导入材料' })).toBeNull())
  expect(document.activeElement).toBe(open)
})

it('reuses the same quick-note operation after an uncertain failure', async () => {
  const requests: Record<string, unknown>[] = []
  let saves = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/integrations/feishu/status')) return { ok: true, status: 200, json: async () => ({ mode: 'fake', authorized: false }) }
    if (path.endsWith('/intake/items') && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as Record<string, unknown>
      requests.push(body); saves += 1
      if (saves === 1) return { ok: false, status: 503, json: async () => ({ error: { message: '请求结果未知' } }) }
      return { ok: true, status: 201, json: async () => ({ item_id: 'saved', origin_kind: 'quick_note', state: 'pending' }) }
    }
    if (path.endsWith('/intake/items')) return { ok: true, status: 200, json: async () => [] }
    return { ok: true, status: 200, json: async () => [] }
  }))
  render(<TodayView onError={vi.fn()} />)
  const note = screen.getByLabelText('记下一句话')
  fireEvent.change(note, { target: { value: '同一条合成记录' } })
  fireEvent.keyDown(note, { key: 'Enter', shiftKey: false })
  await waitFor(() => expect(requests).toHaveLength(1))
  fireEvent.keyDown(note, { key: 'Enter', shiftKey: false })
  await waitFor(() => expect(requests).toHaveLength(2))
  expect(requests[0].operation_id).toBe(requests[1].operation_id)
  expect(requests[0].text).toBe(requests[1].text)
})

it('opens the reusable import drawer with file staging and Feishu search but no authorization entry', async () => {
  const requests = mockApi({ '/actions': [], '/intake/items': [], '/integrations/feishu/materials': { items: [{ material_id: 'mat', title: '合成会议材料', visibility: 'owner' }], next_cursor: null } })
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: '导入材料' }))
  expect(await screen.findByRole('dialog', { name: '导入材料' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: /授权飞书/ })).toBeNull()
  const file = new File(['meeting notes'], 'meeting.md', { type: 'text/markdown' })
  fireEvent.change(screen.getByLabelText('选择多个文件'), { target: { files: [file] } })
  expect(screen.getByText(/meeting.md/)).toBeTruthy()
  fireEvent.click(screen.getByRole('tab', { name: '飞书材料' }))
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  await waitFor(() => expect(requests.some((item) => item.path.includes('/materials?'))).toBe(true))
  expect(await screen.findByText('合成会议材料')).toBeTruthy()
  expect(requests.some((item) => item.path.includes('/materials?'))).toBe(true)
})

it('keeps each failed file retryable without repeating successful imports', async () => {
  let uploads = 0
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  const originalFetch = globalThis.fetch as typeof fetch
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/intake/files')) {
      uploads += 1
      requests.push({ path, method: 'POST' })
      if (uploads === 1) return { ok: false, status: 422, json: async () => ({ error: { message: '合成失败' } }) }
      return { ok: true, status: 201, json: async () => ({ item_id: 'file', origin_kind: 'file', state: 'pending' }) }
    }
    return originalFetch(input, init)
  }))
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: '导入材料' }))
  const first = new File(['a'], 'first.md', { type: 'text/markdown' }), second = new File(['b'], 'second.md', { type: 'text/markdown' })
  fireEvent.change(screen.getByLabelText('选择多个文件'), { target: { files: [first, second] } })
  fireEvent.click(screen.getByRole('button', { name: '导入可用文件' }))
  await waitFor(() => expect(screen.getByText('second.md').closest('li')?.textContent).toContain('已导入'))
  expect(screen.getByText('first.md').closest('li')?.textContent).toContain('导入失败')
  fireEvent.click(screen.getByRole('button', { name: '只重试此文件' }))
  await waitFor(() => expect(uploads).toBe(3))
  expect(requests.filter((item) => item.path.endsWith('/intake/files'))).toHaveLength(3)
})

it('does not resend a file whose upload result is unknown', async () => {
  let uploads = 0
  const requests = mockApi({ '/actions': [], '/intake/items': [] })
  const originalFetch = globalThis.fetch as typeof fetch
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/intake/files')) {
      uploads += 1; requests.push({ path, method: 'POST' })
      return { ok: false, status: 503, json: async () => ({ error: { message: '结果暂不可知' } }) }
    }
    return originalFetch(input, init)
  }))
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: '导入材料' }))
  fireEvent.change(screen.getByLabelText('选择多个文件'), { target: { files: [new File(['x'], 'uncertain.md', { type: 'text/markdown' })] } })
  fireEvent.click(screen.getByRole('button', { name: '导入可用文件' }))
  expect(await screen.findByText(/结果未知；不会自动重发/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: '只重试此文件' })).toBeNull()
  expect(uploads).toBe(1)
})

it('shows a stale inbox after a failed refresh instead of treating it as empty', async () => {
  let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.endsWith('/integrations/feishu/status')) return { ok: true, status: 200, json: async () => ({ mode: 'fake', authorized: true, scopes: [], token_type: 'user' }) }
    if (path.endsWith('/intake/items')) { reads += 1; return reads === 1 ? { ok: true, status: 200, json: async () => [{ item_id: 'x', title: '保留的内容', filename: 'one.md', state: 'pending', created_at: '2026-10-15T00:00:00Z', origin_kind: 'unknown' }] } : { ok: false, status: 503, json: async () => ({ error: { message: '离线' } }) } }
    return { ok: true, status: 200, json: async () => [] }
  }))
  render(<TodayView onError={vi.fn()} />)
  expect(await screen.findByText('保留的内容')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '刷新' }))
  await waitFor(() => expect(screen.getByText(/读取失败：离线；保留已有内容/)).toBeTruthy())
  expect(screen.queryByText('还没有最近材料。')).toBeNull()
})

it('keeps the initial Today inbox pending until its first successful read', async () => {
  let finishRead: ((response: Response) => void) | undefined
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.endsWith('/intake/items')) return await new Promise<Response>((resolve) => { finishRead = resolve })
    if (path.endsWith('/integrations/feishu/status')) return Response.json({ mode: 'fake', authorized: false, scopes: [], token_type: 'user' })
    if (path.endsWith('/actions') || path.endsWith('/projects')) return Response.json([])
    return Response.json([])
  }))
  render(<TodayView onError={vi.fn()} />)
  expect(await screen.findByText('正在读取材料…')).toBeTruthy()
  expect(screen.queryByText('还没有最近材料。')).toBeNull()
  finishRead?.(Response.json([]))
  expect(await screen.findByText('还没有最近材料。')).toBeTruthy()
})

it('restores the work journal modal without merging its save workflow into quick notes', async () => {
  mockApi({ '/actions': [], '/intake/items': [], '/lines': [], '/projects': [], '/pages': [] })
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: '工作日志 / 思考' }))
  expect(await screen.findByRole('dialog', { name: '工作日志与思考' })).toBeTruthy()
  expect(screen.getByRole('button', { name: '工作日志' })).toBeTruthy()
  expect(screen.getByRole('button', { name: '工作思考' })).toBeTruthy()
})
