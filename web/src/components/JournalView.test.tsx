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
    if (url.endsWith('/journal/thought') && init?.method === 'POST') return { ok: true, status: 201, json: async () => ({ saved_locally: true, index_update: 'updated' }) }
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
  expect(await screen.findByText('本机索引已更新。')).toBeTruthy()
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

it('shows the saved page confirmation and knowledge validity states', async () => {
  const rows = [
    { page_id: 'invalid-log', relative_path: '线/项目/log.md', metadata: { title: '外部编辑日志', kind: 'log' }, body: '正文', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'invalid', validity: 'current' },
    { page_id: 'old-thought', relative_path: '线/项目/thought.md', metadata: { title: '旧思考', kind: 'thought' }, body: '正文', content_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'superseded' },
  ]
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => rows }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<JournalView onError={vi.fn()} onOpenPage={vi.fn()} />)
  expect(await screen.findByText('需要重新确认 · 本机保存')).toBeTruthy()
  expect(await screen.findByText('已被替代 · 本机保存')).toBeTruthy()
})
