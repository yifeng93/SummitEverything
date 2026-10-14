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
    if (url.endsWith('/settings')) return { ok: true, status: 200, json: async () => ({ mode: 'fake' }) }
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

it('previews the full real journal text, cancels without sending, and requires a new confirmation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  let mode: 'fake' | 'real' = 'fake'
  const paths: string[] = []
  const source = '合成日志正文：今天完成了访客流程演练。'
  const plan = { plan_id: 'journal-plan', scope_sha256: 'a'.repeat(64), request_limit: 1 }
  const scope = { text: source, max_output_tokens: 2048 }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    paths.push(`${method} ${url}`)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/settings')) return { ok: true, status: 200, json: async () => ({ mode, llm: { model: 'deepseek-flash' } }) }
    if (url.endsWith('/journal/assist')) return { ok: true, status: 200, json: async () => ({ title: '旧建议', body: '旧建议正文' }) }
    if (url.endsWith('/acceptance-plans') && method === 'POST') return { ok: true, status: 201, json: async () => ({ plan, scope }) }
    if (url.endsWith('/acceptance-plans/journal-plan') && method === 'DELETE') return { ok: true, status: 204, json: async () => undefined }
    if (url.endsWith('/acceptance-plans/journal-plan/confirm')) return { ok: true, status: 200, json: async () => ({}) }
    if (url.endsWith('/journal/assist')) return { ok: true, status: 200, json: async () => ({ title: '建议标题', body: '建议正文' }) }
    throw new Error(`Unexpected request ${method} ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<JournalView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('正文'), { target: { value: source } })
  fireEvent.click(screen.getByRole('button', { name: 'AI 辅助建议' }))
  expect(await screen.findByText('可编辑建议 · 尚未保存')).toBeTruthy()
  mode = 'real'
  fireEvent.click(screen.getByRole('button', { name: 'AI 辅助建议' }))
  expect(await screen.findByRole('region', { name: 'AI 辅助预览' })).toBeTruthy()
  expect(screen.getByText(source, { selector: 'pre' })).toBeTruthy()
  expect(screen.getByText(/deepseek-flash.*最多生成 2048 个 token.*一次模型请求/)).toBeTruthy()
  expect((screen.getByRole('button', { name: '确认并保存在本机' }) as HTMLButtonElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: 'AI 辅助建议' }) as HTMLButtonElement).disabled).toBe(true)
  expect((screen.getByRole('button', { name: '采用到编辑区' }) as HTMLButtonElement).disabled).toBe(true)
  expect((screen.getByLabelText('正文') as HTMLTextAreaElement).disabled).toBe(true)
  expect(paths.filter((path) => path.endsWith('/journal/assist'))).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: '取消，不发送' }))
  await waitFor(() => expect(paths.some((path) => path === 'DELETE /api/v1/acceptance-plans/journal-plan')).toBe(true))
  expect(paths.filter((path) => path.endsWith('/journal/assist'))).toHaveLength(1)

  fireEvent.click(screen.getByRole('button', { name: 'AI 辅助建议' }))
  expect(await screen.findByRole('region', { name: 'AI 辅助预览' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: /确认并生成建议/ }))
  expect(await screen.findByText('可编辑建议 · 尚未保存')).toBeTruthy()
  expect(paths.some((path) => path.includes('/acceptance-plans/journal-plan/confirm'))).toBe(true)
  expect(paths.filter((path) => path.endsWith('/journal/assist'))).toHaveLength(2)
  expect(paths.some((path) => path.endsWith('/journal/log'))).toBe(false)
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
