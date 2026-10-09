import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Page } from '../api/client'
import { PageReader } from './PageReader'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('lets the user review and reconfirm the current externally edited page version', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'confirmation-operation-id' })
  const page = {
    page_id: 'page-id',
    relative_path: 'line/project/fact.md',
    metadata: { id: 'page-id', title: '合同事实', role: 'knowledge', kind: 'topic', line_id: 'line-id', project_id: 'project-id', approval: { confirmation_id: 'old-proof' } },
    body: '合同金额是 999 元。',
    content_sha256: 'a'.repeat(64),
    raw_sha256: 'b'.repeat(64),
    storage_area: 'formal',
    approval_state: 'invalid',
    validity: 'current',
  } as Page
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ state: 'succeeded' }) })
  vi.stubGlobal('fetch', fetchMock)
  const onReload = vi.fn().mockResolvedValue(undefined)
  render(<PageReader page={page} onClose={vi.fn()} onReload={onReload} />)

  expect(screen.getByText(/目前不会用于知识问答/)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('页面正文'), { target: { value: '合同金额是 999 元，已核对最新合同。' } })
  fireEvent.click(screen.getByRole('button', { name: '确认当前版本' }))

  await waitFor(() => expect(onReload).toHaveBeenCalledOnce())
  const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
  expect(url).toBe('/api/v1/pages/page-id/confirmations')
  expect(JSON.parse(String(options.body))).toMatchObject({
    metadata: { id: 'page-id', title: '合同事实', approval: { confirmation_id: 'old-proof' } },
    body: '合同金额是 999 元，已核对最新合同。',
    expected_base_sha256: page.content_sha256,
  })
})
