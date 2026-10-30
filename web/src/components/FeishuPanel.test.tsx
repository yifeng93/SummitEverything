import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { FeishuPanel } from './FeishuPanel'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

type TestResponse = { ok: boolean; status: number; json: () => Promise<unknown>; clone?: () => { json: () => Promise<unknown> } }
type TestFetch = (input: RequestInfo | URL, init?: RequestInit) => Promise<TestResponse>

function stubFetch(implementation: TestFetch) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    const response = await implementation(input, init)
    if (!response.ok) return response
    let data: unknown
    try { data = await (typeof response.clone === 'function' ? response.clone() : response).json() } catch { return response }
    if (path.endsWith('/acceptance-plans') && init?.method === 'POST' && (!data || typeof data !== 'object' || !('plan' in data))) {
      const request = typeof init?.body === 'string' ? JSON.parse(init.body) as { scope?: unknown } : {}
      return Response.json({ plan: { plan_id: 'test-plan', scope_sha256: 'test-scope', request_limit: 2 }, scope: request.scope ?? {} }, { status: 201 })
    }
    if (path.includes('/calendar?') && (!data || typeof data !== 'object' || !('items' in data))) {
      return Response.json({ items: [], next_cursor: null, timezone: 'Asia/Shanghai' })
    }
    return response
  }))
}

function renderFeishu() { return render(<FeishuPanel onImported={async () => {}} />) }

async function confirmOperationRead() {
  fireEvent.click(await screen.findByRole('button', { name: '确认并执行本次读取' }))
}

it('shows authorization setup failure and never claims success', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.endsWith('/authorizations')) return { ok: false, status: 403, json: async () => ({ error: { message: '授权暂未完成' } }) }
    const data = path.endsWith('/status') ? { mode: 'real', authorized: false, app_configured: true, scopes: [], token_type: 'user' } : []
    return { ok: true, status: 200, json: async () => data }
  })
  stubFetch(fetchMock)
  renderFeishu()
  const button = await screen.findByRole('button', { name: '连接飞书用户身份' })
  fireEvent.click(button)
  expect(await screen.findByText('授权暂未完成')).toBeTruthy()
  expect(screen.queryByText('用户已授权')).toBeNull()
})

it('keeps an expired user authorization and asks for the missing application secret', async () => {
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.endsWith('/status')) return Response.json({
      mode: 'real', authorized: false, refreshable: true, calendar_ready: false,
      app_configured: false, identity: 'user', scopes: ['calendar:calendar.event:read'],
      credential_error: 'application_credential_missing',
    })
    return Response.json([])
  }))
  renderFeishu()
  expect(await screen.findByText('需补应用密钥')).toBeTruthy()
  expect(screen.getByText(/尚未配置应用密钥/)).toBeTruthy()
  expect(screen.queryByText('授权已过期')).toBeNull()
})

it('clears the local authorization when the user disconnects Feishu', async () => {
  let authorized = true
  let finishDelete: (() => void) | undefined
  let deleteCalls = 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (path.endsWith('/status')) return { ok: true, status: 200, json: async () => ({ mode: 'real', authorized, scopes: [], token_type: 'user' }) }
    if (path.endsWith('/authorizations') && init?.method === 'DELETE') {
      deleteCalls += 1
      await new Promise<void>((resolve) => { finishDelete = resolve })
      authorized = false
      return { ok: true, status: 204, json: async () => undefined }
    }
    return { ok: true, status: 200, json: async () => [] }
  })
  stubFetch(fetchMock)
  renderFeishu()
  await screen.findByText('用户已授权')

  fireEvent.click(screen.getByRole('button', { name: '断开飞书授权' }))
  expect(screen.getByRole('dialog', { name: '断开飞书用户授权？' })).toBeTruthy()
  expect(deleteCalls).toBe(0)
  fireEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(deleteCalls).toBe(0)
  fireEvent.click(screen.getByRole('button', { name: '断开飞书授权' }))
  fireEvent.click(screen.getByRole('button', { name: '确认断开授权' }))
  fireEvent.click(screen.getByRole('button', { name: '正在断开…' }))
  expect(deleteCalls).toBe(1)
  finishDelete?.()

  expect(await screen.findByText('用户未授权')).toBeTruthy()
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/integrations/feishu/authorizations', expect.objectContaining({ method: 'DELETE' }))
  expect(deleteCalls).toBe(1)
})

it('lists metadata, imports only explicit selection, and shows partial outcomes', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'selected-operation' })
  const imported: unknown[] = []
  let page = 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'real', authorized: true, scopes: ['calendar:read'], token_type: 'user' }
    if (path.includes('/materials?')) {
      page += 1
      data = { items: [{ material_id: page === 1 ? 'first' : 'second', title: page === 1 ? '第一份模拟材料' : '第二份模拟材料', visibility: 'owner' }], next_cursor: page === 1 ? 'next' : null }
    }
    if (path.includes('/imports')) {
      imported.push(JSON.parse(String(init?.body)))
      data = { operation_id: 'selected-operation', state: 'partial', outcomes: [{ material_id: 'first', state: 'succeeded' }, { material_id: 'second', state: 'failed', message: '缺少读取权限' }] }
    }
    return { ok: true, status: 200, json: async () => data }
  })
  stubFetch(fetchMock)
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  await confirmOperationRead()
  expect(await screen.findByText('第一份模拟材料')).toBeTruthy()
  expect(imported).toHaveLength(0)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '下一页材料' }))
  await confirmOperationRead()
  expect(await screen.findByText('第二份模拟材料')).toBeTruthy()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '导入所选 · 2' }))
  await confirmOperationRead()
  expect(await screen.findByText('部分材料导入失败，请查看逐项结果。')).toBeTruthy()
  expect(imported).toEqual([{ material_ids: ['first', 'second'], operation_id: 'selected-operation' }])
  expect(screen.getByText(/缺少读取权限/)).toBeTruthy()
  expect(screen.getByText(/第一份模拟材料：/)).toBeTruthy()
})

it('cancels selection without importing and keeps prior calendar data on service failure', async () => {
  let calendarCalls = 0
  const imported: unknown[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'real', authorized: true, calendar_ready: true, scopes: ['calendar:read'], token_type: 'user' }
    if (path.includes('/materials?')) data = { items: [{ material_id: 'one', title: '可取消的材料', visibility: 'shared' }], next_cursor: null }
    if (path.endsWith('/imports')) imported.push(path)
    if (path.includes('/calendar?')) {
      calendarCalls += 1
      if (calendarCalls === 2) return { ok: false, status: 503, json: async () => ({ error: { message: '日历服务暂不可用。' } }) }
      data = { items: [], next_cursor: null, timezone: 'Asia/Shanghai' }
    }
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  await confirmOperationRead()
  expect(await screen.findByText('可取消的材料')).toBeTruthy()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '取消选择' }))
  expect((screen.getByRole('button', { name: '导入所选 · 0' }) as HTMLButtonElement).disabled).toBe(true)
  expect(imported).toHaveLength(0)
  // calendar_ready triggers the initial read; the next refresh fails and keeps it.
  expect(await screen.findByText('所选时间内没有日程。')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '刷新日历' }))
  expect(await screen.findByText(/日历服务暂不可用/)).toBeTruthy()
  expect(screen.getByText('所选时间内没有日程。')).toBeTruthy()
})

it('shows a truncation notice and offers no unusable next page for an explicit range', async () => {
  const calls: string[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    calls.push(path)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'real', authorized: true, calendar_ready: true, app_configured: true, scopes: ['calendar:read'], token_type: 'user' }
    if (path.includes('/materials?')) data = { items: [], next_cursor: null }
    if (path.includes('/calendar?')) {
      data = {
        items: [{ event_id: 'e1', title: '合成日程', start: '2026-10-09T01:00:00Z', end: '2026-10-09T02:00:00Z' }],
        next_cursor: null,
        timezone: 'Asia/Shanghai',
        truncated: true,
      }
    }
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '刷新日历' }) as HTMLButtonElement).disabled).toBe(false))
  expect(await screen.findByText('仅显示部分日程，请缩小时间范围。')).toBeTruthy()
  expect(calls.filter((path) => path.includes('/calendar?'))).toHaveLength(1)
  expect(calls.some((path) => path.endsWith('/acceptance-plans'))).toBe(false)
  expect(screen.queryByRole('button', { name: '下一页日程' })).toBeNull()
})

it('reads an authorized calendar directly without preparing an acceptance plan', async () => {
  const calls: string[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input); calls.push(path)
    const data = path.endsWith('/status')
      ? { mode: 'real', authorized: false, refreshable: true, calendar_ready: true, app_configured: true, identity: 'app', scopes: ['calendar:read'], token_type: 'tenant' }
      : path.includes('/calendar?') ? { items: [], next_cursor: null, timezone: 'Asia/Shanghai' }
        : []
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  await screen.findByText('所选时间内没有日程。')
  expect(calls.filter((path) => path.includes('/calendar?'))).toHaveLength(1)
  expect(calls.some((path) => path.includes('/acceptance-plans'))).toBe(false)
  expect(calls.some((path) => path.endsWith('/authorizations'))).toBe(false)
})

it('never renders a next-page control for an explicit range, even when a cursor comes back', async () => {
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'real', authorized: true, calendar_ready: true, scopes: ['calendar:read'], token_type: 'user' }
    if (path.includes('/materials?')) data = { items: [], next_cursor: null }
    if (path.includes('/calendar?')) {
      data = {
        items: [{ event_id: 'e1', title: '合成日程', start: '2026-10-09T01:00:00Z', end: '2026-10-09T02:00:00Z' }],
        next_cursor: 'page-2',
        timezone: 'Asia/Shanghai',
        truncated: false,
      }
    }
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '刷新日历' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '刷新日历' }))
  expect(await screen.findByText('合成日程')).toBeTruthy()
  // 显式范围查询本身不分页；即使后端回了 cursor 也不给一个点了没用的按钮。
  expect(screen.queryByRole('button', { name: '下一页日程' })).toBeNull()
  expect(screen.queryByText('仅显示部分日程，请缩小时间范围。')).toBeNull()
})

it('keeps OAuth callback registration in the official browser URL without fetching it from the UI', async () => {
  const destination = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize?client_id=cli_synthetic&redirect_uri=http%3A%2F%2F127.0.0.1%3A8793%2Fapi%2Fv1%2Fintegrations%2Ffeishu%2Fcallback&state=synthetic-state'
  const requests: { path: string; init?: RequestInit }[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input); requests.push({ path, init })
    return { ok: true, status: 200, json: async () => path.endsWith('/authorizations') ? { authorization_url: destination, expires_in_seconds: 300 } : { mode: 'real', authorized: false, calendar_ready: false, app_configured: true, scopes: [], token_type: 'user' } }
  }))
  renderFeishu()
  fireEvent.click(await screen.findByRole('button', { name: '连接飞书用户身份' }))
  const link = await screen.findByRole('link', { name: '打开飞书授权页面' })
  expect(link.getAttribute('href')).toBe(destination)
  expect(screen.getByText('用户未授权')).toBeTruthy()
  expect(requests.map((request) => request.path)).toEqual(['/api/v1/integrations/feishu/status', '/api/v1/integrations/feishu/authorizations'])
})

for (const [code, expectedLabel, remainsAuthorized] of [['token_expired', '授权已过期', false], ['not_authorized', '用户未授权', false], ['missing_scope', '权限不足', true]] as const) {
  it(`updates authorization state distinctly for ${code}`, async () => {
    stubFetch(vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.includes('/materials?')) return { ok: false, status: code === 'missing_scope' ? 403 : 401, json: async () => ({ error: { code, message: '模拟授权读取失败' } }) }
      return { ok: true, status: 200, json: async () => path.endsWith('/status') ? { mode: 'real', authorized: true, calendar_ready: true, scopes: ['calendar:read'], token_type: 'user' } : path.includes('/calendar?') ? { items: [], next_cursor: null, timezone: 'Asia/Shanghai' } : [] }
    }))
    renderFeishu()
    await screen.findByText('用户已授权')
    fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
    await confirmOperationRead()
    await screen.findByText('模拟授权读取失败')
    expect(screen.getByText(expectedLabel)).toBeTruthy()
    expect((screen.getByRole('button', { name: '刷新日历' }) as HTMLButtonElement).disabled).toBe(!remainsAuthorized)
    expect(screen.queryByText('用户已授权')).toBeNull()
  })
}

it('blocks callback destinations outside the narrow local OAuth boundary', async () => {
  const { api } = await import('../api/client')
  const fetchMock = vi.fn()
  stubFetch(fetchMock)
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
    json: async () => ({ mode: 'real', authorized: true, scopes: ['calendar:read'], token_type: 'user' }),
  }))
  stubFetch(fetchMock)

  const result = await api.oauthCallback<{ authorized: boolean }>(destination)

  expect(result.authorized).toBe(true)
  expect(fetchMock).toHaveBeenCalledWith(destination, {
    credentials: 'omit', redirect: 'error', cache: 'no-store',
  })
})

it('uses real-mode authorization copy and never calls real OAuth a simulation', async () => {
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    let data: unknown = []
    if (path.endsWith('/status')) {
      data = {
        mode: 'real',
        authorized: false,
        app_configured: true,
        identity: 'app',
        token_type: 'user',
        scopes: [],
        user_identity_verified: false,
      }
    }
    if (path.includes('/materials?')) data = { items: [], next_cursor: null }
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  expect(await screen.findByRole('button', { name: '连接飞书用户身份' })).toBeTruthy()
  expect(await screen.findByText('用户未授权')).toBeTruthy()
  expect(await screen.findByText(/应用密钥已配置。.*用户身份尚未验证。/)).toBeTruthy()
})

it('permits an app-identity calendar without user OAuth but not user-only search', async () => {
  const calls: string[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input); calls.push(path)
    const data = path.endsWith('/status')
      ? { mode: 'real', authorized: false, refreshable: true, calendar_ready: true, app_configured: true, identity: 'app', scopes: ['calendar:read'], token_type: 'tenant' }
      : path.includes('/calendar?') ? { items: [], next_cursor: null, timezone: 'Asia/Shanghai' } : []
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '刷新日历' }) as HTMLButtonElement).disabled).toBe(false))
  expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(true)
  await screen.findByText('所选时间内没有日程。')
  expect(calls.filter((path) => path.includes('/calendar?'))).toHaveLength(1)
  expect(calls.some((path) => path.includes('/acceptance-plans'))).toBe(false)
  expect(calls.filter((path) => path.endsWith('/authorizations'))).toHaveLength(0)
})

it('real OAuth presents an official browser link and refreshes only local status', async () => {
  const calls: string[] = []
  let authorized = false
  const destination = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize?client_id=cli_synthetic&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback&state=synthetic'
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input); calls.push(path)
    const data = path.endsWith('/status') ? { mode: 'real', authorized, app_configured: true, identity: 'app', user_identity_verified: false, scopes: [] }
      : path.endsWith('/authorizations') ? { authorization_url: destination, expires_in_seconds: 300 } : []
    return { ok: true, status: 200, json: async () => data }
  }))
  renderFeishu()
  fireEvent.click(await screen.findByRole('button', { name: '连接飞书用户身份' }))
  const link = await screen.findByRole('link', { name: '打开飞书授权页面' })
  expect(link.getAttribute('href')).toBe(destination)
  expect(link.getAttribute('rel')).toContain('noopener')
  expect(calls.every((path) => path.startsWith('/api/v1/'))).toBe(true)
  expect(screen.queryByText('用户已授权')).toBeNull()
  authorized = true
  fireEvent.click(screen.getByRole('button', { name: '刷新用户授权状态' }))
  await screen.findByText('用户已授权')
  expect(screen.getByText(/用户身份尚未验证/)).toBeTruthy()
  expect(screen.queryByRole('link', { name: '打开飞书授权页面' })).toBeNull()
})

it('keeps a refreshable authorization connected and attempts the calendar read', async () => {
  const calls: string[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    calls.push(path)
    if (path.endsWith('/status')) return Response.json({ mode: 'real', authorized: false, refreshable: true, calendar_ready: true, authorization_generation: 3, app_configured: true, identity: 'app', scopes: ['calendar:read'], token_type: 'app' })
    if (path.includes('/calendar?')) return Response.json({ items: [], next_cursor: null, timezone: 'Asia/Shanghai' })
    return Response.json([])
  }))
  renderFeishu()
  expect(await screen.findByText('所选时间内没有日程。')).toBeTruthy()
  expect(screen.getByText('授权可续期')).toBeTruthy()
  expect(calls.filter((path) => path.includes('/calendar?'))).toHaveLength(1)
})

it('ignores a calendar response from the previous workspace after switching dedupe scope', async () => {
  let resolveOld: ((response: Response) => void) | undefined
  let resolveNew: ((response: Response) => void) | undefined
  let calendarCalls = 0
  stubFetch(vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path.endsWith('/status')) return Response.json({ mode: 'real', authorized: true, calendar_ready: true, authorization_generation: 1, app_configured: true, identity: 'app', scopes: ['calendar:read'], token_type: 'app' })
    if (path.includes('/calendar?')) {
      calendarCalls += 1
      return await new Promise<Response>((resolve) => { if (calendarCalls === 1) resolveOld = resolve; else resolveNew = resolve })
    }
    return Response.json([])
  }))
  const { rerender } = render(<FeishuPanel onImported={async () => {}} view="calendar" dedupeScope="workspace-old" />)
  await waitFor(() => expect(resolveOld).toBeTruthy())
  rerender(<FeishuPanel onImported={async () => {}} view="calendar" dedupeScope="workspace-new" />)
  await waitFor(() => expect(resolveNew).toBeTruthy())
  resolveNew!(Response.json({ items: [{ event_id: 'new', title: '新工作库日程', start: '2026-10-30T02:00:00Z', end: '2026-10-30T02:30:00Z' }], next_cursor: null, timezone: 'Asia/Shanghai' }))
  expect(await screen.findByText('新工作库日程')).toBeTruthy()
  resolveOld!(Response.json({ items: [{ event_id: 'old', title: '旧工作库日程', start: '2026-10-30T01:00:00Z', end: '2026-10-30T01:30:00Z' }], next_cursor: null, timezone: 'Asia/Shanghai' }))
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(screen.queryByText('旧工作库日程')).toBeNull()
  expect(screen.getByText('新工作库日程')).toBeTruthy()
})

it('hides the unsupported visibility filter in real mode and omits it from the request', async () => {
  const calls: string[] = []
  stubFetch(vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input); calls.push(path)
    if (path.endsWith('/status')) return { ok: true, status: 200, json: async () => ({ mode: 'real', authorized: true, app_configured: true, identity: 'user', scopes: [], token_type: 'user' }) }
    if (path.endsWith('/acceptance-plans') && init?.method === 'POST') return { ok: true, status: 201, json: async () => ({ plan: { plan_id: 'materials-plan', scope_sha256: 'scope', request_limit: 2, state: 'preview' }, scope: { query: '会议', visibility: null, cursor: null, limit: 20 } }) }
    if (path.endsWith('/acceptance-plans/materials-plan/confirm')) return { ok: true, status: 200, json: async () => ({}) }
    if (path.includes('/materials?')) return { ok: true, status: 200, json: async () => ({ items: [], next_cursor: null }) }
    return { ok: true, status: 200, json: async () => [] }
  }))
  renderFeishu()
  await waitFor(() => expect((screen.getByRole('button', { name: '搜索 / 刷新材料' }) as HTMLButtonElement).disabled).toBe(false))
  expect(screen.queryByText('可见范围')).toBeNull()
  expect(screen.getByText(/只搜索妙记/)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('搜索材料'), { target: { value: '会议' } })
  fireEvent.click(screen.getByRole('button', { name: '搜索 / 刷新材料' }))
  await screen.findByRole('button', { name: '确认并执行本次读取' })
  fireEvent.click(screen.getByRole('button', { name: '确认并执行本次读取' }))
  await waitFor(() => expect(calls.some((path) => path.includes('/materials?'))).toBe(true))
  const materialCall = calls.find((path) => path.includes('/materials?'))!
  expect(materialCall).not.toContain('visibility=')
})
