import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TodayView } from './TodayView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('shows Feishu authorization and never claims success after denied callback', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.includes('/callback')) return { ok: false, status: 403, json: async () => ({ error: { message: '授权已取消' } }) }
    const data = path.endsWith('/status') ? { mode: 'fake', authorized: false, scopes: [], token_type: 'user' } : path.endsWith('/authorizations') ? { authorization_url: 'http://localhost/api/v1/integrations/feishu/callback?state=state&code=fake-ok', expires_in_seconds: 300 } : []
    return { ok: true, status: 200, json: async () => data }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<TodayView onError={vi.fn()} />)
  const button = await screen.findByRole('button', { name: '模拟授权飞书' })
  fireEvent.click(button)
  expect(await screen.findByText('授权已取消')).toBeTruthy()
  expect(screen.queryByText('已授权')).toBeNull()
})

it('clears the local authorization when the user disconnects Feishu', async () => {
  let authorized = true
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/status')) return { ok: true, status: 200, json: async () => ({ mode: 'fake', authorized, scopes: [], token_type: 'user' }) }
    if (path.endsWith('/authorizations') && init?.method === 'DELETE') {
      authorized = false
      return { ok: true, status: 204, json: async () => undefined }
    }
    return { ok: true, status: 200, json: async () => [] }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<TodayView onError={vi.fn()} />)
  await screen.findByText('已授权')

  fireEvent.click(screen.getByRole('button', { name: '断开飞书授权' }))

  expect(await screen.findByText('未授权')).toBeTruthy()
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/integrations/feishu/authorizations', expect.objectContaining({ method: 'DELETE' }))
})

it('lists metadata, imports only explicit selection, and shows partial outcomes', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'selected-operation' })
  const imported: unknown[] = []
  let page = 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'fake', authorized: true, scopes: [], token_type: 'user' }
    if (path.includes('/materials?')) {
      page += 1
      data = { items: [{ material_id: page === 1 ? 'first' : 'second', title: page === 1 ? '第一份模拟材料' : '第二份模拟材料', visibility: 'owner' }], next_cursor: page === 1 ? 'next' : null }
    }
    if (path.endsWith('/imports')) {
      imported.push(JSON.parse(String(init?.body)))
      data = { operation_id: 'selected-operation', state: 'partial', outcomes: [{ material_id: 'first', state: 'succeeded' }, { material_id: 'second', state: 'failed', message: '缺少读取权限' }] }
    }
    return { ok: true, status: 200, json: async () => data }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<TodayView onError={vi.fn()} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  expect(await screen.findByText('第一份模拟材料')).toBeTruthy()
  expect(imported).toHaveLength(0)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '下一页材料' }))
  expect(await screen.findByText('第二份模拟材料')).toBeTruthy()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '导入所选 · 2' }))
  expect(await screen.findByText('部分材料导入失败，请查看逐项结果。')).toBeTruthy()
  expect(imported).toEqual([{ material_ids: ['first', 'second'], operation_id: 'selected-operation' }])
  expect(screen.getByText(/缺少读取权限/)).toBeTruthy()
  expect(screen.getByText(/第一份模拟材料：/)).toBeTruthy()
})

it('cancels selection without importing and displays calendar empty and error states', async () => {
  let calendarCalls = 0
  const imported: unknown[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'fake', authorized: true, scopes: [], token_type: 'user' }
    if (path.includes('/materials?')) data = { items: [{ material_id: 'one', title: '可取消的材料', visibility: 'shared' }], next_cursor: null }
    if (path.endsWith('/imports')) imported.push(path)
    if (path.includes('/calendar?')) {
      calendarCalls += 1
      if (calendarCalls === 2) return { ok: false, status: 401, json: async () => ({ error: { message: '飞书授权已过期，请重新授权。' } }) }
      data = { items: [], next_cursor: null, timezone: 'Asia/Shanghai' }
    }
    return { ok: true, status: 200, json: async () => data }
  }))
  render(<TodayView onError={vi.fn()} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  expect(await screen.findByText('可取消的材料')).toBeTruthy()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '取消选择' }))
  expect((screen.getByRole('button', { name: '导入所选 · 0' }) as HTMLButtonElement).disabled).toBe(true)
  expect(imported).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '刷新日历' }))
  expect(await screen.findByText('所选时间内没有日程。')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '刷新日历' }))
  expect(await screen.findByText('飞书授权已过期，请重新授权。')).toBeTruthy()
  expect(screen.queryByText('所选时间内没有日程。')).toBeNull()
})

it('preserves configured callback destination when Web and API ports differ', async () => {
  const destination = 'http://127.0.0.1:8793/api/v1/integrations/feishu/callback?state=synthetic-state&code=fake-ok'
  const requests: { path: string; init?: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input); requests.push({ path, init })
    return { ok: true, status: 200, json: async () => path.endsWith('/authorizations') ? { authorization_url: destination, expires_in_seconds: 300 } : path.includes('/integrations/feishu/') ? { mode: 'fake', authorized: path.includes('/callback'), scopes: [], token_type: 'user' } : [] }
  }))
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '模拟授权飞书' }))
  await screen.findByText('已授权')
  expect(requests.some((request) => request.path === destination)).toBe(true)
  const callback = requests.find((request) => request.path === destination)
  expect(callback?.init?.credentials).toBe('omit')
  expect(callback?.init?.redirect).toBe('error')
})

for (const [code, expectedLabel, remainsAuthorized] of [['token_expired', '授权已过期', false], ['not_authorized', '未授权', false], ['missing_scope', '权限不足', true]] as const) {
  it(`updates authorization state distinctly for ${code}`, async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.includes('/materials?')) return { ok: false, status: code === 'missing_scope' ? 403 : 401, json: async () => ({ error: { code, message: '模拟授权读取失败' } }) }
      return { ok: true, status: 200, json: async () => path.endsWith('/status') ? { mode: 'fake', authorized: true, scopes: [], token_type: 'user' } : [] }
    }))
    render(<TodayView onError={vi.fn()} />)
    await screen.findByText('已授权')
    fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
    await screen.findByText('模拟授权读取失败')
    expect(screen.getByText(expectedLabel)).toBeTruthy()
    expect((screen.getByRole('button', { name: '刷新日历' }) as HTMLButtonElement).disabled).toBe(!remainsAuthorized)
    expect(screen.queryByText('已授权')).toBeNull()
  })
}

it('blocks callback destinations outside the narrow local OAuth boundary', async () => {
  const { api } = await import('../api/client')
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  for (const url of ['https://external.invalid/api/v1/integrations/feishu/callback?state=x&code=fake-ok', 'http://127.0.0.1:8793/api/v1/workspaces?state=x&code=fake-ok', 'http://user:password@127.0.0.1:8793/api/v1/integrations/feishu/callback?state=x&code=fake-ok', 'http://127.0.0.1:8793/api/v1/integrations/feishu/callback?state=x&code=fake-ok&token=secret', 'http://127.0.0.1:8793/api/v1/integrations/feishu/callback?state=x&state=y&code=fake-ok']) {
    await expect(api.oauthCallback(url)).rejects.toThrow('授权回调地址无效')
  }
  expect(fetchMock).not.toHaveBeenCalled()
})

it('allows the registered localhost slash-callback path', async () => {
  const { api } = await import('../api/client')
  const destination = 'http://localhost:8765/callback?state=synthetic-state&code=fake-ok'
  const fetchMock = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({ mode: 'fake', authorized: true, scopes: [], token_type: 'user' }),
  }))
  vi.stubGlobal('fetch', fetchMock)

  const result = await api.oauthCallback<{ authorized: boolean }>(destination)

  expect(result.authorized).toBe(true)
  expect(fetchMock).toHaveBeenCalledWith(destination, {
    credentials: 'omit', redirect: 'error', cache: 'no-store',
  })
})
