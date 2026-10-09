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
