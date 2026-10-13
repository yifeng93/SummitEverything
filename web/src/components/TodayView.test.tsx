import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TodayView } from './TodayView'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('shows source lifecycle states and requires an explicit reprocess action', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const items = [
    { item_id: 'pending-id', source_id: 'source-1', title: '新来源', filename: 'new.txt', original_relative_path: '原件/new.txt', created_at: '2026-10-09T00:00:00Z', state: 'pending' },
    { item_id: 'processing-id', source_id: 'source-2', title: '整理中来源', filename: 'processing.txt', original_relative_path: '原件/processing.txt', created_at: '2026-10-09T00:00:00Z', state: 'processing' },
    { item_id: 'reviewing-id', source_id: 'source-3', title: '待审核来源', filename: 'reviewing.txt', original_relative_path: '原件/reviewing.txt', created_at: '2026-10-09T00:00:00Z', state: 'reviewing' },
    { item_id: 'completed-id', source_id: 'source-4', title: '已处理来源', filename: 'completed.txt', original_relative_path: '原件/completed.txt', created_at: '2026-10-09T00:00:00Z', state: 'completed' },
    { item_id: 'failed-id', source_id: 'source-5', title: '失败来源', filename: 'failed.txt', original_relative_path: '原件/failed.txt', created_at: '2026-10-09T00:00:00Z', state: 'failed' },
  ]
  const responseData: Record<string, unknown> = {
    '/api/v1/intake/items': items,
    '/api/v1/drafts': [],
    '/api/v1/actions': [],
    '/api/v1/lines': [{ id: 'line-id', name: '模拟主线', directory: '模拟主线' }],
    '/api/v1/projects': [{ id: 'project-id', line_id: 'line-id', name: '模拟项目', directory: '模拟主线/模拟项目', overview_id: 'overview-id', archived: false }],
    '/api/v1/pages': [],
    '/api/v1/intake/jobs': { job_id: 'job-id' },
    '/api/v1/settings': { mode: 'fake' },
  }
  const jobBodies: Record<string, unknown>[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith('/intake/jobs')) {
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      jobBodies.push(body)
      if (jobBodies.length === 1) {
        items[0].state = 'failed'
        return {
          ok: false,
          status: 503,
          json: async () => ({ error: { message: 'Fake provider failed' } }),
        }
      }
      items[0].state = 'reviewing'
    }
    return {
      ok: true,
      status: 200,
      json: async () => responseData[String(input)],
    }
  })
  vi.stubGlobal('fetch', fetchMock)

  const onError = vi.fn()
  render(<TodayView onError={onError} />)
  expect(await screen.findByText('新来源')).toBeTruthy()
  expect(screen.getByText('整理中')).toBeTruthy()
  expect(screen.getByText('待审核')).toBeTruthy()
  expect(screen.getByText('已完成')).toBeTruthy()
  expect(screen.getByText('整理失败')).toBeTruthy()

  const processingRow = screen.getByText('整理中来源').closest('li')
  const reviewingRow = screen.getByText('待审核来源').closest('li')
  expect((within(processingRow as HTMLElement).getByRole('checkbox') as HTMLInputElement).disabled).toBe(true)
  expect((within(reviewingRow as HTMLElement).getByRole('checkbox') as HTMLInputElement).disabled).toBe(true)

  const pendingRow = screen.getByText('新来源').closest('li')
  fireEvent.click(within(pendingRow as HTMLElement).getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '整理所选 · 1' }))
  await waitFor(() => expect(screen.getByText('新来源').closest('li')?.textContent).toContain('整理失败'))
  expect(onError).toHaveBeenLastCalledWith('Fake provider failed')
  fireEvent.click(screen.getByRole('button', { name: '重新整理所选 · 1' }))
  await waitFor(() => expect(jobBodies).toHaveLength(2))
  expect(jobBodies[1]).toMatchObject({ item_ids: ['pending-id'], reprocess: true })

  const completedRow = screen.getByText('已处理来源').closest('li')
  fireEvent.click(within(completedRow as HTMLElement).getByRole('checkbox'))
  expect(screen.getByText(/原件与既有稿件会保留/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '重新整理所选 · 1' }))
  await waitFor(() => {
    expect(jobBodies).toHaveLength(3)
  })
  expect(jobBodies[2]).toMatchObject({ item_ids: ['completed-id'], reprocess: true })
})

it('keeps unknown attempts visible and warns before an explicit new operation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const items = [
    { item_id: 'unknown-id', source_id: 'source-unknown', title: '状态未知来源', filename: 'unknown.txt', original_relative_path: '原件/unknown.txt', created_at: '2026-10-09T00:00:00Z', state: 'unknown' },
  ]
  const responses: Record<string, unknown> = {
    '/api/v1/intake/items': items,
    '/api/v1/drafts': [], '/api/v1/actions': [],
    '/api/v1/lines': [{ id: 'line-id', name: '模拟主线', directory: '模拟主线' }],
    '/api/v1/projects': [{ id: 'project-id', line_id: 'line-id', name: '模拟项目', directory: '模拟主线/模拟项目', overview_id: 'overview-id', archived: false }],
    '/api/v1/pages': [],
    '/api/v1/intake/jobs': { job_id: 'new-job', state: 'completed' },
    '/api/v1/settings': { mode: 'fake' },
  }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => ({
    ok: true, status: 200, json: async () => responses[String(input)],
  })))

  render(<TodayView onError={vi.fn()} />)
  expect(await screen.findByText('请求状态未知')).toBeTruthy()
  const row = screen.getByText('状态未知来源').closest('li')
  fireEvent.click(within(row as HTMLElement).getByRole('checkbox'))
  expect(screen.getByText(/不会自动重发.*可能再次调用模型/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '重新整理所选 · 1' }))
  await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).endsWith('/intake/jobs'))).toBe(true))
})

it('requires readable plan confirmation for real organize and sends nothing on cancel', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'organize-operation' })
  const item = { item_id: 'source-id', source_id: 'parent-id', title: '合成会议纪要', filename: 'meeting.txt', original_relative_path: '收件箱/meeting.txt', created_at: '2026-10-09T00:00:00Z', state: 'pending' }
  const plan = { plan_id: 'plan-id', scope_sha256: 'a'.repeat(64), request_limit: 1 }
  const scope = { item_ids: ['source-id'], operation_id: 'organize-operation', line_id: 'line-id', project_id: 'project-id', reprocess: false, max_output_tokens: 2048, outgoing_inputs: [{ item_id: 'source-id', source_id: 'parent-id', text: '合成材料全文：报价尚未批准。' }] }
  const paths: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    paths.push(path)
    const method = init?.method ?? 'GET'
    if (path.endsWith('/acceptance-plans') && method === 'POST') return { ok: true, status: 201, json: async () => ({ plan, scope }) }
    if (path.endsWith('/intake/jobs')) return { ok: true, status: 201, json: async () => ({ job_id: 'job-id', state: 'completed' }) }
    if (path.endsWith('/acceptance-plans/plan-id/confirm')) return { ok: true, status: 200, json: async () => ({}) }
    if (path.endsWith('/acceptance-plans/plan-id')) return { ok: true, status: 204, json: async () => ({}) }
    const data: Record<string, unknown> = {
      '/api/v1/intake/items': [item], '/api/v1/drafts': [], '/api/v1/actions': [],
      '/api/v1/lines': [{ id: 'line-id', name: '合成主线', directory: '合成主线' }],
      '/api/v1/projects': [{ id: 'project-id', line_id: 'line-id', name: '合成项目', directory: '合成主线/合成项目', overview_id: 'overview-id', archived: false }],
      '/api/v1/pages': [], '/api/v1/settings': { mode: 'real' },
    }
    return { ok: true, status: 200, json: async () => data[path] }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<TodayView onError={vi.fn()} />)
  const row = (await screen.findByText('合成会议纪要')).closest('li')
  fireEvent.click(within(row as HTMLElement).getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '整理所选 · 1' }))
  expect(await screen.findByText('合成材料全文：报价尚未批准。')).toBeTruthy()
  expect(paths.some((path) => path.endsWith('/intake/jobs'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '取消，不发送' }))
  await waitFor(() => expect(paths.some((path) => path.endsWith('/acceptance-plans/plan-id'))).toBe(true))
  expect(paths.some((path) => path.endsWith('/intake/jobs'))).toBe(false)
})
