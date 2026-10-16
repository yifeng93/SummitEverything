import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
      json: async () => ({ error: { code: 'version_conflict', message: '页面内容已变化。' } }),
    })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ...draft, version: 2, expected_base_sha256: page.content_sha256 }) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ state: 'succeeded', index_update: 'updated', page_versions: { 'saved-page-id': 'saved-hash' } }) })
  vi.stubGlobal('fetch', fetchMock)
  const onError = vi.fn()
  const onUpdated = vi.fn().mockResolvedValue(undefined)
  const onConfirmed = vi.fn().mockResolvedValue(undefined)
  const props = { draft, onError, onUpdated, onConfirmed }
  const view = render(<DraftReview {...props} pages={[page]} />)

  fireEvent.click(within(document.querySelector('.review-actions') as HTMLElement).getByRole('button', { name: '确认并保存当前版本' }))
  const dialog = await screen.findByRole('dialog')
  fireEvent.click(within(dialog).getByRole('button', { name: '确认并保存当前版本' }))
  await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1))
  expect(onError).toHaveBeenLastCalledWith('页面内容已变化。')
  view.rerender(<DraftReview {...props} pages={[currentPage]} />)

  expect(screen.getByText(/目标页面已变化/)).toBeTruthy()
  expect(screen.getByText(/合同金额是 999 元/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '采用当前页面作为比较基准' }))
  fireEvent.click(within(document.querySelector('.review-actions') as HTMLElement).getByRole('button', { name: '确认并保存当前版本' }))
  const retryDialog = await screen.findByRole('dialog')
  fireEvent.click(within(retryDialog).getByRole('button', { name: '确认并保存当前版本' }))
  await waitFor(() => expect(onConfirmed).toHaveBeenCalledTimes(1))
  expect(onConfirmed).toHaveBeenCalledWith(expect.objectContaining({ index_update: 'updated' }))
  const patchCall = fetchMock.mock.calls[1] as [string, RequestInit]
  expect(patchCall[1].method).toBe('PATCH')
  expect(JSON.parse(String(patchCall[1].body))).toMatchObject({
    target_page_id: 'page-id',
    expected_base_sha256: currentPage.content_sha256,
    body: draft.body,
  })
})

it('recognizes expected-version conflicts by API status and code while preserving unsaved edits', async () => {
  const draft = {
    draft_id: 'version-draft', input_ids: [], target_page_id: null,
    metadata: { id: 'version-draft', title: '版本稿', role: 'knowledge', kind: 'topic' },
    body: '服务器原稿', expected_base_sha256: null, important_conflicts: [], action_suggestions: [],
    conflict_resolutions: {}, source_ids: [], state: 'pending', created_at: '2026-10-09T00:00:00Z', version: 3,
  } as Draft
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ error: { code: 'version_conflict', message: '内容变化。' } }, { status: 409 })))
  vi.stubGlobal('confirm', vi.fn(() => true))
  const onUpdated = vi.fn().mockResolvedValue(undefined)
  render(<DraftReview draft={draft} pages={[]} onError={vi.fn()} onConfirmed={vi.fn()} onUpdated={onUpdated} />)
  fireEvent.click(screen.getByText('编辑稿件与归属'))
  fireEvent.change(screen.getByLabelText('正文'), { target: { value: '尚未保存的本地修改' } })
  fireEvent.click(screen.getByRole('button', { name: '保存修改' }))

  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(onUpdated).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('正文')).toHaveProperty('value', '尚未保存的本地修改')
  fireEvent.click(screen.getByRole('button', { name: '放弃当前编辑并载入最新版本' }))
  expect(window.confirm).toHaveBeenCalled()
})

it('previews how an unresolved conflict will be recorded in the confirmed page', () => {
  const draft = {
    draft_id: 'conflict-draft',
    input_ids: ['input-id'],
    target_page_id: null,
    metadata: { id: 'conflict-draft', title: '状态事实', role: 'knowledge', kind: 'topic' },
    body: '原文中的状态仍不明确。',
    expected_base_sha256: null,
    important_conflicts: [{ id: 'status-conflict', question: '状态是否已确认？', alternatives: ['已确认', '仍待确认'] }],
    action_suggestions: [],
    conflict_resolutions: {},
    source_ids: ['source-id'],
    state: 'pending',
    created_at: '2026-10-09T00:00:00Z',
    version: 1,
  } as Draft
  render(<DraftReview draft={draft} pages={[]} onError={vi.fn()} onConfirmed={vi.fn()} onUpdated={vi.fn()} />)

  fireEvent.click(screen.getByLabelText(/暂时未决/))
  expect(screen.getByLabelText('确认结果预览').textContent).toContain('状态是否已确认？：暂时未决')
})

it('conflict choices are protected locally, not misrepresented as persisted until confirmation', async () => {
  const draft = {
    draft_id: 'choice-draft', input_ids: [], target_page_id: null,
    metadata: { id: 'choice-draft', title: '待判定事实', role: 'knowledge', kind: 'topic' },
    body: '状态暂不明确。', expected_base_sha256: null,
    important_conflicts: [{ id: 'state', question: '目前状态？', alternatives: ['已确认', '待确认'] }],
    action_suggestions: [], conflict_resolutions: {}, source_ids: ['source-id'], state: 'pending',
    created_at: '2026-10-09T00:00:00Z', version: 1,
  } as Draft
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === 'POST') return Response.json({ state: 'succeeded', index_update: 'updated', page_versions: { 'new-page-id': 'saved-hash' } })
    return Response.json(draft)
  })
  vi.stubGlobal('fetch', fetchMock)
  const onDirtyChange = vi.fn()
  render(<DraftReview draft={draft} pages={[]} onError={vi.fn()} onConfirmed={vi.fn().mockResolvedValue(undefined)} onUpdated={vi.fn().mockResolvedValue(undefined)} onDirtyChange={onDirtyChange} />)

  fireEvent.click(screen.getByLabelText('采用：已确认'))
  expect(onDirtyChange).toHaveBeenLastCalledWith(true)
  expect(screen.getByText('冲突选择尚未提交，将在确认时生效。')).toBeTruthy()
  expect(screen.getByRole('button', { name: '保存修改' })).toHaveProperty('disabled', true)

  fireEvent.click(within(document.querySelector('.review-actions') as HTMLElement).getByRole('button', { name: '确认并保存当前版本' }))
  const dialog = await screen.findByRole('dialog')
  fireEvent.click(within(dialog).getByRole('button', { name: '确认并保存当前版本' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
  const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit]
  expect(url).toContain('/drafts/choice-draft/confirmations')
  expect(JSON.parse(String(request.body))).toMatchObject({ conflict_resolutions: { state: '已确认' } })
})
