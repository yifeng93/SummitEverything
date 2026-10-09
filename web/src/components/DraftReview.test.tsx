import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Draft, Page } from '../api/client'
import { DraftReview } from './DraftReview'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('shows a changed target and requires an explicit current-version baseline before retrying', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const draft = {
    draft_id: 'draft-id',
    input_ids: ['input-id'],
    target_page_id: 'page-id',
    metadata: { id: 'draft-id', title: '合同事实', role: 'knowledge', kind: 'topic', line_id: 'line-id', project_id: 'project-id' },
    body: '合同金额更新为 456 元。',
    expected_base_sha256: 'a'.repeat(64),
    important_conflicts: [],
    action_suggestions: [],
    conflict_resolutions: {},
    source_ids: ['source-id'],
    state: 'pending',
    created_at: '2026-10-09T00:00:00Z',
    version: 1,
  } as Draft
  const page = {
    page_id: 'page-id',
    relative_path: 'line/project/page.md',
    metadata: { id: 'page-id', title: '合同事实', role: 'knowledge', kind: 'topic', line_id: 'line-id', project_id: 'project-id' },
    body: '合同金额是 123 元。',
    content_sha256: 'a'.repeat(64),
    raw_sha256: 'c'.repeat(64),
    storage_area: 'formal',
    approval_state: 'confirmed',
    validity: 'current',
  } as Page
  const currentPage = {
    ...page,
    body: '合同金额是 999 元。\n外部补充：以最新合同为准。',
    content_sha256: 'b'.repeat(64),
    approval_state: 'invalid',
  } as Page
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ error: { message: '目标页面已变化，请检查当前版本后再继续审核。' } }),
    })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ...draft, version: 2, expected_base_sha256: page.content_sha256 }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ state: 'succeeded' }) })
  vi.stubGlobal('fetch', fetchMock)
  const onError = vi.fn()
  const onUpdated = vi.fn().mockResolvedValue(undefined)
  const onConfirmed = vi.fn().mockResolvedValue(undefined)
  const props = { draft, onError, onUpdated, onConfirmed }
  const view = render(<DraftReview {...props} pages={[page]} />)

  fireEvent.click(screen.getByRole('button', { name: '确认并写入知识库' }))
  await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1))
  expect(onError).toHaveBeenLastCalledWith(expect.stringContaining('目标页面已变化'))
  view.rerender(<DraftReview {...props} pages={[currentPage]} />)

  expect(screen.getByText(/目标页面已变化/)).toBeTruthy()
  expect(screen.getByText(/合同金额是 999 元/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '采用当前页面作为比较基准' }))
  fireEvent.click(screen.getByRole('button', { name: '确认并写入知识库' }))
  await waitFor(() => expect(onConfirmed).toHaveBeenCalledTimes(1))
  const patchCall = fetchMock.mock.calls[1] as [string, RequestInit]
  expect(patchCall[1].method).toBe('PATCH')
  expect(JSON.parse(String(patchCall[1].body))).toMatchObject({
    target_page_id: 'page-id',
    expected_base_sha256: currentPage.content_sha256,
    body: draft.body,
  })
})
