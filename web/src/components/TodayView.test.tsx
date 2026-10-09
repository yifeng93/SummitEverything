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
