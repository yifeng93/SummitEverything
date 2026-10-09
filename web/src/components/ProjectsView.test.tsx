import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ProjectsView } from './ProjectsView'

const lines = [{ id: 'line-1', name: '模拟主线', directory: '模拟主线' }]
const projects = [
  { id: 'project-1', line_id: 'line-1', name: '模拟项目', directory: '模拟主线/模拟项目', overview_id: 'overview-1', archived: false },
  { id: 'project-archived', line_id: 'line-1', name: '已归档项目', directory: '模拟主线/已归档项目', overview_id: 'overview-archived', archived: true },
]
const pages = [
  { page_id: 'page-1', relative_path: '模拟主线/模拟项目/fact.md', metadata: { id: 'page-1', title: '模拟事实', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-1' }, body: '正文', content_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' },
  { page_id: 'page-archived', relative_path: '模拟主线/已归档项目/history.md', metadata: { id: 'page-archived', title: '归档事实', role: 'knowledge', kind: 'topic', line_id: 'line-1', project_id: 'project-archived' }, body: '归档正文', content_sha256: 'c'.repeat(64), raw_sha256: 'd'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' },
]

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('renames a line and project while keeping their stable IDs', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (init?.method === 'PATCH' && url === '/api/v1/lines/line-1') {
      const body = JSON.parse(String(init.body)) as { name: string }
      lines[0].name = body.name
      return { ok: true, status: 200, json: async () => lines[0] }
    }
    if (init?.method === 'PATCH' && url === '/api/v1/projects/project-1') {
      const body = JSON.parse(String(init.body)) as { name: string }
      projects[0].name = body.name
      return { ok: true, status: 200, json: async () => projects[0] }
    }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  expect(await screen.findAllByText('模拟主线')).not.toHaveLength(0)
  expect(await screen.findByRole('button', { name: '重命名主线' })).toBeTruthy()
  expect(await screen.findByRole('button', { name: '重命名项目' })).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: '重命名主线' }))
  fireEvent.change(screen.getByLabelText('主线名称'), { target: { value: '改名主线' } })
  fireEvent.click(screen.getByRole('button', { name: '保存主线' }))
  await waitFor(() => expect(screen.getAllByText('改名主线').length).toBeGreaterThan(0))
  expect((screen.getByPlaceholderText('新增主线名称') as HTMLInputElement).value).toBe('')
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/lines/line-1', expect.objectContaining({ method: 'PATCH' }))

  fireEvent.click(screen.getByRole('button', { name: '重命名项目' }))
  fireEvent.change(screen.getByLabelText('项目名称'), { target: { value: '改名项目' } })
  fireEvent.click(screen.getByRole('button', { name: '保存项目' }))
  await waitFor(() => expect(screen.getAllByText('改名项目').length).toBeGreaterThan(0))
  expect((screen.getByPlaceholderText('新项目名称') as HTMLInputElement).value).toBe('')
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/projects/project-1', expect.objectContaining({ method: 'PATCH' }))
})

it('keeps archived knowledge retrievable and exposes the archived project in the directory', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (init?.method === 'PATCH' && url === '/api/v1/projects/project-archived') {
      const body = JSON.parse(String(init.body)) as { archived: boolean }
      projects[1].archived = body.archived
      return { ok: true, status: 200, json: async () => projects[1] }
    }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.click(await screen.findByLabelText('显示已归档项目'))
  fireEvent.click(await screen.findByRole('button', { name: /已归档项目/ }))
  expect(screen.getByText('归档事实')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '恢复项目' }))
  await waitFor(() => expect(projects[1].archived).toBe(false))
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/projects/project-archived', expect.objectContaining({ method: 'PATCH' }))
})

it('shows the workspace refusal when deleting a non-empty line', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const onError = vi.fn()
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (init?.method === 'DELETE') return { ok: false, status: 409, json: async () => ({ error: { message: 'Move projects before deleting this line' } }) }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={onError} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '删除空主线' }))
  await waitFor(() => expect(onError).toHaveBeenCalledWith('Move projects before deleting this line'))
})
