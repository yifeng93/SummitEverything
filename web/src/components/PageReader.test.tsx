import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Page } from '../api/client'
import { PageReader } from './PageReader'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('adds a relative link to a confirmed page and saves it only after explicit confirmation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const page: Page = { page_id: 'page-1', relative_path: 'line/project/facts.md', metadata: { id: 'page-1', title: 'Facts', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' }, body: 'Current facts', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const target = { ...page, page_id: 'page-2', relative_path: 'line/project/related.md', metadata: { ...page.metadata, id: 'page-2', title: 'Related' }, body: 'Related body' }
  const savedBodies: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page, target] }
    if (url.endsWith('/confirmations')) { savedBodies.push(String(init?.body)); return { ok: true, status: 200, json: async () => ({}) } }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<PageReader page={page} onClose={vi.fn()} onReload={vi.fn(async () => {})} />)

  fireEvent.change(await screen.findByLabelText('链接到页面'), { target: { value: 'page-2' } })
  fireEvent.click(screen.getByRole('button', { name: '插入链接' }))
  const body = screen.getByLabelText('检查并确认正文') as HTMLTextAreaElement
  expect(body.value).toContain('[Related](related.md)')
  expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/confirmations'), expect.anything())
  fireEvent.click(screen.getByRole('button', { name: '确认新版本' }))

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/pages/page-1/confirmations', expect.objectContaining({ method: 'POST' })))
  expect(JSON.parse(savedBodies[0]).body).toContain('[Related](related.md)')
})

it('moves a confirmed page into the selected project and records cross-project confirmation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const page: Page = { page_id: 'page-1', relative_path: 'line/project-a/facts.md', metadata: { id: 'page-1', title: 'Facts', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-a' }, body: 'Current facts', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const projects = [{ id: 'project-b', line_id: 'line-1', name: 'Project B', directory: 'line/project-b', overview_id: 'overview-b', archived: false }]
  const moveBodies: string[] = []
  const onClose = vi.fn()
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page] }
    if (url.endsWith('/moves')) { moveBodies.push(String(init?.body)); return { ok: true, status: 200, json: async () => ({}) } }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<PageReader page={page} onClose={onClose} onReload={vi.fn(async () => {})} />)

  fireEvent.change(await screen.findByLabelText('移动到项目'), { target: { value: 'project-b' } })
  fireEvent.click(screen.getByRole('button', { name: '移动页面' }))
  await waitFor(() => expect(onClose).toHaveBeenCalled())
  expect(JSON.parse(moveBodies[0])).toMatchObject({ destination_relative_path: 'line/project-b/facts.md', operation_id: 'operation-id', structure_confirmation_id: 'operation-id' })
})
