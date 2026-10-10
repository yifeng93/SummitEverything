import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { JournalView } from './JournalView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('lists without assistance and saves an explicitly confirmed thought with optional association', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => [{ id: 'line-1', name: '模拟线', directory: '模拟线' }] }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [{ id: 'project-1', line_id: 'line-1', name: '模拟项目', directory: '模拟线/模拟项目', overview_id: 'overview-1', archived: false }] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/journal/thought') && init?.method === 'POST') return { ok: true, status: 201, json: async () => ({ saved_locally: true }) }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<JournalView onError={vi.fn()} onOpenPage={vi.fn()} />)
  expect(await screen.findByText('暂无日志或思考。')).toBeTruthy()
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/journal/assist'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '工作思考' }))
  fireEvent.change(screen.getByLabelText('标题'), { target: { value: '模拟想法' } })
  fireEvent.change(screen.getByLabelText('正文'), { target: { value: '这是模拟正文。' } })
  fireEvent.change(screen.getByLabelText('主线（可选）'), { target: { value: 'line-1' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并保存在本机' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/journal/thought') && init?.method === 'POST')).toBe(true))
})

it('returns an editable suggestion separately from saved pages', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/journal/assist')) return { ok: true, status: 200, json: async () => ({ title: '建议标题', body: '建议正文' }) }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<JournalView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('正文'), { target: { value: '原始正文' } })
  fireEvent.click(screen.getByRole('button', { name: 'AI 辅助建议' }))
  expect(await screen.findByText('可编辑建议 · 尚未保存')).toBeTruthy()
  expect(screen.getByLabelText('建议正文')).toBeTruthy()
  expect(await screen.findByText('暂无日志或思考。')).toBeTruthy()
})
