import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Page } from '../api/client'
import { PageReader } from './PageReader'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('adds a relative link to a confirmed page and saves it only after explicit confirmation', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const page: Page = { page_id: 'page-1', relative_path: 'line/project/facts.md', metadata: { id: 'page-1', title: 'Facts', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' }, body: 'Current facts\n\n[[related.md|Related]]', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const target = { ...page, page_id: 'page-2', relative_path: 'line/project/related.md', metadata: { ...page.metadata, id: 'page-2', title: 'Related' }, body: 'Related body', content_sha256: 'b'.repeat(64) }
  const savedBodies: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page, target] }
    if (url.endsWith('/confirmations')) { savedBodies.push(String(init?.body)); return { ok: true, status: 200, json: async () => ({}) } }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  const onOpenPage = vi.fn()
  render(<PageReader page={page} onClose={vi.fn()} onReload={vi.fn(async () => {})} onOpenPage={onOpenPage} />)

  fireEvent.click(await screen.findByRole('link', { name: 'Related' }))
  expect(onOpenPage).toHaveBeenCalledWith('page-2', 'b'.repeat(64))

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
  render(<PageReader page={page} onClose={onClose} onReload={vi.fn(async () => {})} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('移动到项目'), { target: { value: 'project-b' } })
  fireEvent.click(screen.getByRole('button', { name: '移动页面' }))
  expect(moveBodies).toHaveLength(0)
  expect(screen.getByRole('dialog', { name: '将页面移动到“Project B”？' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(moveBodies).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '移动页面' }))
  fireEvent.click(screen.getByRole('button', { name: '确认移动页面' }))
  await waitFor(() => expect(onClose).toHaveBeenCalled())
  expect(JSON.parse(moveBodies[0])).toMatchObject({ destination_relative_path: 'line/project-b/facts.md', operation_id: 'operation-id', structure_confirmation_id: 'operation-id' })
})

it.each([
  ['superseded', '已被替代', '仅供历史参考'],
  ['invalid', '已失效', '仅供历史参考'],
] as const)('shows approved %s knowledge validity separately from confirmation', async (validity, label, description) => {
  const page: Page = {
    page_id: `page-${validity}`,
    relative_path: 'line/project/old-facts.md',
    metadata: { id: `page-${validity}`, title: '历史事实', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' },
    body: '已批准的历史正文',
    content_sha256: 'a'.repeat(64),
    storage_area: 'formal',
    approval_state: 'confirmed',
    validity,
  }
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<PageReader page={page} onClose={vi.fn()} onReload={vi.fn(async () => {})} onOpenPage={vi.fn()} />)

  expect(await screen.findByText(`已确认 · ${label}`)).toBeTruthy()
  expect(screen.getByRole('status').textContent).toContain(description)
  expect(screen.getByText('已批准的历史正文')).toBeTruthy()
  expect(screen.queryByText('待确认')).toBeNull()
  expect(screen.queryByLabelText('重新确认当前页面')).toBeNull()
})

it('keeps the reconfirmation warning when the approved content hash no longer matches', () => {
  const changedPage: Page = {
    page_id: 'page-changed',
    relative_path: 'line/project/facts.md',
    metadata: { id: 'page-changed', title: '已变化事实', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' },
    body: '外部编辑后的正文',
    content_sha256: 'b'.repeat(64),
    storage_area: 'formal',
    approval_state: 'invalid',
    validity: 'superseded',
  }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [changedPage] }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<PageReader page={changedPage} onClose={vi.fn()} onReload={vi.fn(async () => {})} onOpenPage={vi.fn()} />)

  expect(screen.getByText('待确认 · 已被替代')).toBeTruthy()
  expect(screen.getByText(/已被替代，仅供历史参考/)).toBeTruthy()
  expect(screen.getByText(/自上次确认后已有变化/)).toBeTruthy()
  expect(document.querySelector('.page-body')?.textContent).toContain('外部编辑后的正文')
  expect(screen.getByText('编辑 Markdown 源码').closest('details')?.open).toBe(false)
  expect(screen.getByLabelText('页面正文')).toBeTruthy()
})
