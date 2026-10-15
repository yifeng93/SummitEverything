import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
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

beforeEach(() => {
  lines[0].name = '模拟主线'
  projects[0].name = '模拟项目'
  projects[0].archived = false
  projects[1].name = '已归档项目'
  projects[1].archived = true
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
  fireEvent.click(screen.getByRole('button', { name: '重命名主线' }))
  fireEvent.change(screen.getByLabelText('主线名称'), { target: { value: '改名主线' } })
  fireEvent.click(screen.getByRole('button', { name: '保存主线' }))
  await waitFor(() => expect(screen.getAllByText('改名主线').length).toBeGreaterThan(0))
  expect((screen.getByPlaceholderText('新增主线名称') as HTMLInputElement).value).toBe('')
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/lines/line-1', expect.objectContaining({ method: 'PATCH' }))

  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  fireEvent.click(await screen.findByRole('button', { name: '重命名项目' }))
  fireEvent.change(screen.getByLabelText('项目名称'), { target: { value: '改名项目' } })
  fireEvent.click(screen.getByRole('button', { name: '保存名称' }))
  await waitFor(() => expect(screen.getAllByText('改名项目').length).toBeGreaterThan(0))
  fireEvent.click(screen.getByRole('button', { name: '← 返回项目列表' }))
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

  fireEvent.change(await screen.findByLabelText('筛选状态'), { target: { value: 'archived' } })
  fireEvent.click(await screen.findByRole('button', { name: /已归档项目/ }))
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  expect(screen.getByText('归档事实')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '恢复项目' }))
  const dialog = within(screen.getByRole('dialog'))
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(false)
  fireEvent.click(dialog.getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '恢复项目' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '恢复项目' }))
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
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '删除空主线' }))
  await waitFor(() => expect(onError).toHaveBeenCalledWith('Move projects before deleting this line'))
})

it('creates a project overview only after an explicit confirmation and then opens it', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'overview-operation' })
  const onOpenPage = vi.fn()
  let created = false
  const overviewPage = { page_id: 'overview-1', relative_path: '模拟主线/模拟项目/概览.md', metadata: { id: 'overview-1', title: '模拟项目 概览', role: 'knowledge', kind: 'project_overview', line_id: 'line-1', project_id: 'project-1' }, body: '目标', content_sha256: 'e'.repeat(64), raw_sha256: 'f'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/projects/project-1/overview/confirmations') && init?.method === 'POST') { created = true; return { ok: true, status: 201, json: async () => ({ saved_locally: true, index_update: 'updated' }) } }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => created ? [overviewPage] : [] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={onOpenPage} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  fireEvent.click(await screen.findByRole('button', { name: '创建项目概览' }))
  fireEvent.change(screen.getByLabelText('自由 Markdown 正文'), { target: { value: '目标' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并创建概览' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/overview/confirmations') && init?.method === 'POST')).toBe(true))
  expect(await screen.findByText('本机索引已更新。')).toBeTruthy()
  fireEvent.click(await screen.findByRole('button', { name: '打开概览' }))
  expect(onOpenPage).toHaveBeenCalledWith('overview-1')
})

it('opens a full project detail and preserves list search/filter state on return', async () => {
  const onOpenPage = vi.fn()
  const overview = { ...pages[0], page_id: 'overview-1', metadata: { ...pages[0].metadata, title: '概览' }, body: '## 下一步\n安排访谈\n\n```md\n## 阻塞\n误识别\n```\n\n## 决策记录\n采用方案甲' }
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [{ ...projects[0], progress: '进行中', progress_version: 3 }] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => [overview, pages[0]] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={onOpenPage} />)
  fireEvent.change(await screen.findByLabelText('搜索项目'), { target: { value: '模拟' } })
  fireEvent.change(screen.getByLabelText('排序方式'), { target: { value: 'name' } })
  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  expect(screen.getByText('进行中')).toBeTruthy()
  expect(screen.getAllByText('安排访谈').length).toBeGreaterThanOrEqual(2)
  expect(screen.getAllByText('还没有记录')).toHaveLength(2)
  expect(screen.getAllByText('采用方案甲')).toHaveLength(2)
  expect(screen.queryByText('误识别')).toBeNull()
  expect(screen.queryByText(/project-1|overview-1|模拟主线\/模拟项目/)).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '← 返回项目列表' }))
  expect(screen.getByLabelText('搜索项目')).toHaveProperty('value', '模拟')
  expect(screen.getByLabelText('排序方式')).toHaveProperty('value', 'name')
})

it('uses confirmed overview or explicit progress for status and keeps undated pages honest', async () => {
  const base = { ...projects[0], progress: '', progress_version: 0 }
  const archived = { ...projects[1], progress: '推进中', progress_version: 2 }
  const pagesWithDates = [
    { ...pages[0], page_id: 'new-fact', relative_path: 'relative/new.md', metadata: { ...pages[0].metadata, title: '新事实', created_at: '2026-10-12T10:30:00Z' } },
    { ...pages[0], page_id: 'old-fact', relative_path: 'relative/old.md', metadata: { ...pages[0].metadata, title: '旧事实' } },
    { ...pages[0], page_id: 'overview-1', metadata: { ...pages[0].metadata, title: '概览' }, body: '正文' },
  ]
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [{ ...base, overview_id: 'overview-1' }, archived] }
    if (url.endsWith('/pages')) return { ok: true, status: 200, json: async () => pagesWithDates }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  const progressing = await screen.findByRole('button', { name: /模拟项目/ })
  expect(progressing.textContent).toContain('在推进')
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'needs_setup' } })
  expect(screen.getByText('没有符合状态的项目')).toBeTruthy()
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'all' } })
  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  const list = await screen.findByRole('list')
  expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
    expect.stringContaining('新事实'),
    expect.stringContaining('旧事实'),
  ])
  expect(within(list).getByText(/日期未记录/)).toBeTruthy()
})
