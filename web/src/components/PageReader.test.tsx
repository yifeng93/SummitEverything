import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Page } from '../api/client'
import { PageReader } from './PageReader'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('renders a confirmed page as read-only Markdown and only allows changing its project', async () => {
  const page: Page = { page_id: 'page-1', relative_path: 'line/project/facts.md', metadata: { id: 'page-1', title: 'Facts', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' }, body: 'Current facts\n\n[[related.md|Related]]', content_sha256: 'a'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const target = { ...page, page_id: 'page-2', relative_path: 'line/project/related.md', metadata: { ...page.metadata, id: 'page-2', title: 'Related' }, body: 'Related body', content_sha256: 'b'.repeat(64) }
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page, target] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  const onOpenPage = vi.fn()
  render(<PageReader page={page} onClose={vi.fn()} onReload={vi.fn(async () => {})} onOpenPage={onOpenPage} />)

  // 正文按 Markdown 渲染；页面详情不提供编辑或新增正文的入口。
  expect(document.querySelector('.page-body')?.textContent).toContain('Current facts')
  expect(screen.queryByRole('textbox')).toBeNull()
  expect(screen.queryByLabelText('页面正文')).toBeNull()
  expect(screen.queryByRole('button', { name: '插入链接' })).toBeNull()

  fireEvent.click(await screen.findByRole('link', { name: 'Related' }))
  expect(onOpenPage).toHaveBeenCalledWith('page-2', 'b'.repeat(64))

  // 同分类翻页：不必回项目列表也能接着读下一篇。
  const pager = await screen.findByRole('navigation', { name: '同分类翻页' })
  expect(within(pager).queryByText('上一篇')).toBeNull()
  fireEvent.click(within(pager).getByRole('button', { name: /Related/ }))
  expect(onOpenPage).toHaveBeenCalledWith('page-2', 'b'.repeat(64))

  // 唯一的写操作是归属：「页面操作」抽屉里没有正文相关控件。
  fireEvent.click(screen.getByRole('button', { name: '页面操作' }))
  expect(await screen.findByLabelText('移动到项目')).toBeTruthy()
  expect(screen.queryByLabelText('链接到页面')).toBeNull()
  expect(screen.queryByRole('button', { name: '插入链接' })).toBeNull()
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

  fireEvent.click(await screen.findByRole('button', { name: '页面操作' }))
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
  // 待确认页也只读：能确认当前版本，但不能在这里改正文。
  expect(screen.getByRole('button', { name: '确认当前版本' })).toBeTruthy()
  expect(screen.queryByLabelText('页面正文')).toBeNull()
  expect(screen.queryByRole('textbox')).toBeNull()
})

it('正文开头的一级标题与页面标题相同时只渲染一次', async () => {
  const page: Page = {
    page_id: 'page-dup',
    relative_path: 'line/project/vendored.md',
    metadata: { id: 'page-dup', title: 'Vendored 包改名', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' },
    body: '# Vendored 包改名\n\n[English](rescope.md) | 中文\n\n正文段落。',
    content_sha256: 'c'.repeat(64),
    storage_area: 'formal',
    approval_state: 'confirmed',
    validity: 'current',
  }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [page] }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<PageReader page={page} onClose={vi.fn()} onReload={vi.fn(async () => {})} onOpenPage={vi.fn()} />)
  await waitFor(() => expect(document.querySelector('.page-body')?.textContent).toContain('正文段落'))
  expect(document.querySelectorAll('.page-reader h1')).toHaveLength(1)
  expect(document.querySelectorAll('.page-body h1')).toHaveLength(0)
})
