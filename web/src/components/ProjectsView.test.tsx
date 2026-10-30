import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  expect(await screen.findAllByText('模拟主线')).not.toHaveLength(0)
  fireEvent.click(screen.getByText(/主线管理/))
  expect(await screen.findByRole('button', { name: '重命名主线' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '重命名主线' }))
  fireEvent.change(screen.getByLabelText('主线名称'), { target: { value: '改名主线' } })
  fireEvent.click(screen.getByRole('button', { name: '保存主线' }))
  await waitFor(() => expect(screen.getAllByText('改名主线').length).toBeGreaterThan(0))
  fireEvent.click(screen.getByRole('button', { name: '新建主线' }))
  expect((screen.getByLabelText('新主线名称') as HTMLInputElement).value).toBe('')
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/lines/line-1', expect.objectContaining({ method: 'PATCH' }))

  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  fireEvent.click(await screen.findByRole('button', { name: '重命名项目' }))
  fireEvent.change(screen.getByLabelText('项目名称'), { target: { value: '改名项目' } })
  fireEvent.click(screen.getByRole('button', { name: '保存名称' }))
  await waitFor(() => expect(screen.getAllByText('改名项目').length).toBeGreaterThan(0))
  fireEvent.click(screen.getByRole('button', { name: '返回项目列表' }))
  fireEvent.click(screen.getByRole('button', { name: '新建项目' }))
  expect((screen.getByPlaceholderText('输入项目名称') as HTMLInputElement).value).toBe('')
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/projects/project-1', expect.objectContaining({ method: 'PATCH' }))
})

it('creates a project from the explicit list action and keeps archived projects folded by default', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/projects' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as { line_id: string; name: string }
      const created = { ...projects[0], id: 'project-new', line_id: body.line_id, name: body.name, archived: false }
      projects.push(created)
      return { ok: true, status: 201, json: async () => created }
    }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  await screen.findByRole('button', { name: /模拟项目/ })
  const archived = screen.getByText(/已归档 · 1/).closest('details')
  expect(archived?.open).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: '新建项目' }))
  fireEvent.change(screen.getByLabelText('项目名称'), { target: { value: '新项目' } })
  fireEvent.click(screen.getByRole('button', { name: '创建项目' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects' && init?.method === 'POST')).toBe(true))
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/projects', expect.objectContaining({ method: 'POST', body: expect.stringContaining('新项目') }))
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
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  fireEvent.change(await screen.findByLabelText('筛选状态'), { target: { value: 'archived' } })
  fireEvent.click(await screen.findByRole('button', { name: /已归档项目/ }))
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  const archivedTree = await screen.findByRole('navigation', { name: '文档目录' })
  expect(within(archivedTree).getByRole('button', { name: '归档事实' })).toBeTruthy()
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

it('requires confirmation before archiving an active project and writes exactly once', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'archive-operation' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/projects/project-1' && init?.method === 'PATCH') {
      projects[0].archived = true
      return { ok: true, status: 200, json: async () => projects[0] }
    }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  fireEvent.click(screen.getByText('更多'))
  fireEvent.click(screen.getByRole('button', { name: '归档项目' }))
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(0)
  const dialog = within(screen.getByRole('dialog', { name: '归档这个项目？' }))
  fireEvent.click(dialog.getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '归档项目' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '归档项目' }))
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1))
})

it('keeps deleting an empty project behind confirmation and sends one delete after acceptance', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'delete-operation' })
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/projects/project-1' && init?.method === 'DELETE') return { ok: true, status: 204, json: async () => ({}) }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => [] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  fireEvent.click(screen.getByText('更多'))
  fireEvent.click(screen.getByRole('button', { name: '删除空项目' }))
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '删除空项目' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '删除空项目' }))
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(1))
})

it('shows the workspace refusal when deleting a non-empty line', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  const onError = vi.fn()
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (init?.method === 'DELETE') return { ok: false, status: 409, json: async () => ({ error: { message: 'Move projects before deleting this line' } }) }
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={onError} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '删除空主线' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '删除空主线' }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '删除空主线' }))
  await waitFor(() => expect(onError).toHaveBeenCalledWith('Move projects before deleting this line'))
})

it('renders the project overview read-only with no body editor or create controls', async () => {
  const onOpenPage = vi.fn()
  const overviewPage = { page_id: 'overview-1', relative_path: '模拟主线/模拟项目/概览.md', metadata: { id: 'overview-1', title: '模拟项目 概览', role: 'knowledge', kind: 'project_overview', line_id: 'line-1', project_id: 'project-1' }, body: '目标', content_sha256: 'e'.repeat(64), raw_sha256: 'f'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' }
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => [overviewPage] }
    if (url.endsWith('/pages/overview-1')) return { ok: true, status: 200, json: async () => overviewPage }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={onOpenPage} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  expect(await screen.findByText('目标')).toBeTruthy()
  expect(await screen.findByRole('heading', { name: '模拟项目 概览' })).toBeTruthy()
  expect(screen.queryByLabelText('概览正文（Markdown）')).toBeNull()
  expect(screen.queryByRole('button', { name: '编辑' })).toBeNull()
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/overview/confirmations'))).toBe(false)
  expect(onOpenPage).not.toHaveBeenCalled()
})

it('keeps a deleted selected document unavailable instead of opening a neighboring page', async () => {
  let directoryPages: typeof pages = [pages[0]]
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json(projects.slice(0, 1))
    if (url.endsWith('/pages/directory')) return Response.json(directoryPages)
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '找不到页面' } }, { status: 404 })
    if (url.includes('/pages/page-1')) return Response.json(pages[0])
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  const props = { onError: vi.fn(), onOpenPage: vi.fn() }
  const view = render(<ProjectsView {...props} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  fireEvent.click(await screen.findByRole('button', { name: '模拟事实' }))
  expect(await screen.findByText('正文')).toBeTruthy()
  directoryPages = []
  view.rerender(<ProjectsView {...props} externalPagesRevision={1} />)
  expect(await screen.findByText(/这个页面已删除或暂时无法读取/)).toBeTruthy()
  expect(screen.queryByText('正文')).toBeNull()
})

it('opens a full project detail and preserves list search/filter state on return', async () => {
  const onOpenPage = vi.fn()
  const overview = { ...pages[0], page_id: 'overview-1', metadata: { ...pages[0].metadata, title: '概览' }, body: '## 下一步\n安排访谈\n\n```md\n## 阻塞\n误识别\n```\n\n## 决策记录\n采用方案甲' }
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [{ ...projects[0], progress: '进行中', progress_version: 3 }] }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => [overview, pages[0]] }
    if (url.endsWith('/pages/overview-1')) return { ok: true, status: 200, json: async () => overview }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={onOpenPage} />)
  fireEvent.change(await screen.findByLabelText('搜索项目'), { target: { value: '模拟' } })
  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  expect(screen.getAllByText('在推进').length).toBeGreaterThan(0)
  // 概览直接渲染在右侧阅读区，不再有重复的「档案」区块。
  const pane = document.querySelector('.project-docs-body') as HTMLElement
  expect(await within(pane).findByRole('heading', { name: '概览' })).toBeTruthy()
  expect(within(pane).getByText('安排访谈')).toBeTruthy()
  expect(within(pane).getByText('采用方案甲')).toBeTruthy()
  // 代码块里的「误识别」不能被当成小节标题（高亮后文本会被拆成 span，按标题断言）。
  expect(screen.queryByRole('heading', { name: '误识别' })).toBeNull()
  expect(screen.queryByText(/project-1|overview-1|模拟主线\/模拟项目/)).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '返回项目列表' }))
  expect(screen.getByLabelText('搜索项目')).toHaveProperty('value', '模拟')
  expect(screen.getByLabelText('筛选状态')).toHaveProperty('value', 'all')
})

it('keeps the project loading state distinct from a confirmed empty directory', async () => {
  let resolveLines!: (response: Response) => void
  let resolveProjects!: (response: Response) => void
  let resolvePages!: (response: Response) => void
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return new Promise<Response>((resolve) => { resolveLines = resolve })
    if (url.endsWith('/projects')) return new Promise<Response>((resolve) => { resolveProjects = resolve })
    if (url.endsWith('/pages/directory')) return new Promise<Response>((resolve) => { resolvePages = resolve })
    return Promise.reject(new Error(`Unexpected request ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  expect(await screen.findByText('正在读取项目目录…')).toBeTruthy()
  expect(screen.queryByText('还没有项目。先建一条主线，再建项目。')).toBeNull()
  resolveLines(Response.json([]))
  resolveProjects(Response.json([]))
  await waitFor(() => expect(resolvePages).toBeTypeOf('function'))
  resolvePages(Response.json([]))
  expect(await screen.findByText('还没有项目。先建一条主线，再建项目。')).toBeTruthy()
  expect(screen.queryByText('正在读取项目目录…')).toBeNull()
})

it('shows the project directory while page and index auxiliaries are still pending, then retries failures', async () => {
  let pageCalls = 0
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Promise.resolve(Response.json(lines))
    if (url.endsWith('/projects')) return Promise.resolve(Response.json(projects))
    if (url.endsWith('/pages/directory')) {
      pageCalls += 1
      if (pageCalls === 1) return Promise.reject(new TypeError('offline'))
      return Promise.resolve(Response.json(pages))
    }
    if (url.endsWith('/index/status')) return new Promise<Response>(() => undefined)
    return Promise.reject(new Error(`Unexpected request ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  expect(await screen.findByRole('button', { name: /模拟项目/ })).toBeTruthy()
  expect(screen.getByText('页面目录读取失败。').textContent).toContain('重试')
  expect(screen.getByText('已确认页').nextElementSibling?.textContent).toBe('—')
  fireEvent.click(screen.getAllByRole('button', { name: '重试' })[0])
  await waitFor(() => expect(pageCalls).toBe(2))
  await waitFor(() => expect(screen.getByText('已确认页').nextElementSibling?.textContent).toBe('2'))
})

it('turns a stalled project-directory request into a retryable timeout state', async () => {
  vi.useFakeTimers()
  const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
    init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
  }))
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
  expect(screen.getByText('项目目录读取超时，请重试。')).toBeTruthy()
  expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy()
  vi.useRealTimers()
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
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pagesWithDates }
    if (url.endsWith('/pages/overview-1')) return { ok: true, status: 200, json: async () => pagesWithDates[2] }
    if (url.includes('/pages/new-fact?')) return { ok: true, status: 200, json: async () => pagesWithDates[0] }
    if (url.includes('/pages/old-fact?')) return { ok: true, status: 200, json: async () => pagesWithDates[1] }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  const progressing = await screen.findByRole('button', { name: /模拟项目/ })
  expect(progressing.textContent).toContain('在推进')
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'needs_setup' } })
  expect(screen.getByText('这个状态下还没有项目')).toBeTruthy()
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'all' } })
  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  // 左侧是文档树（文件夹 + 文档），右侧直接显示所选文档的正文。
  const tree = await screen.findByRole('navigation', { name: '文档目录' })
  expect(within(tree).getByRole('button', { name: /新事实/ })).toBeTruthy()
  expect(within(tree).getByRole('button', { name: /旧事实/ })).toBeTruthy()
  // 有概览时默认停在概览；点文档才切到正文。
  fireEvent.click(within(tree).getByRole('button', { name: /新事实/ }))
  const pane = document.querySelector('.project-docs-body') as HTMLElement
  expect(await within(pane).findByRole('heading', { name: '新事实' })).toBeTruthy()
  fireEvent.click(within(tree).getByRole('button', { name: /旧事实/ }))
  expect(await within(pane).findByRole('heading', { name: '旧事实' })).toBeTruthy()
})

it('shows index coverage and groups a document project by source directory', async () => {
  const docPages = [
    { page_id: 'p-sub', relative_path: '模拟主线/模拟项目/slots.md', metadata: { title: 'Slots 概览', kind: 'topic', project_id: 'project-1', source_path: 'docs/subsystems/slots.zh.md' }, body: '正文', content_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' },
    { page_id: 'p-arch', relative_path: '模拟主线/模拟项目/overview.md', metadata: { title: '总览', kind: 'topic', project_id: 'project-1', source_path: 'docs/architecture/overview.zh.md' }, body: '正文', content_sha256: 'c'.repeat(64), raw_sha256: 'd'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current' },
  ]
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => docPages }
    if (url.includes('/pages/p-sub?')) return { ok: true, status: 200, json: async () => docPages[0] }
    if (url.includes('/pages/p-arch?')) return { ok: true, status: 200, json: async () => docPages[1] }
    if (url.endsWith('/index/status')) {
      return { ok: true, status: 200, json: async () => ({ fingerprint: 'summit-fake-embedding-v1', pages: 2, chunks: 14, state: 'ready', current_pages: 2, stale_pages: 0, vector: 'simulated' }) }
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  await screen.findByRole('button', { name: /模拟项目/ })
  expect(screen.getByText('已确认页').nextElementSibling?.textContent).toBe('2')
  expect(screen.getByText('已索引页').nextElementSibling?.textContent).toBe('2')
  expect(screen.getByText('分块').nextElementSibling?.textContent).toBe('14')
  // 索引正常时不追加状态句：四个指标已说明覆盖范围，运行模式在设置里说。
  expect(screen.queryByText(/索引可用|仿真向量|真实向量/)).toBeNull()

  fireEvent.click(screen.getByRole('button', { name: /模拟项目/ }))
  // 文件夹在左树里可展开，文档是叶子；右侧直接是正文。
  const tree = await screen.findByRole('navigation', { name: '文档目录' })
  expect(within(tree).getByRole('button', { name: /架构/ })).toBeTruthy()
  expect(within(tree).getByRole('button', { name: /子系统/ })).toBeTruthy()
  // 默认只展开当前文档所在路径，其余文件夹收起。
  expect(await within(tree).findByRole('button', { name: 'Slots 概览' })).toBeTruthy()
  expect(within(tree).queryByRole('button', { name: '总览' })).toBeNull()
  fireEvent.click(within(tree).getByRole('button', { name: /架构/ }))
  fireEvent.click(await within(tree).findByRole('button', { name: '总览' }))
  const pane = document.querySelector('.project-docs-body') as HTMLElement
  expect(await within(pane).findByRole('heading', { name: '总览' })).toBeTruthy()
})

it('automatically refreshes the directory after a version race between listing and body read', async () => {
  const oldEntry = { ...pages[0], page_id: 'page-race', content_sha256: 'a'.repeat(64) }
  const updatedPage = { ...oldEntry, content_sha256: 'b'.repeat(64), body: '刚更新的正文' }
  let directoryReads = 0
  let detailReads = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json(projects)
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '没有概览' } }, { status: 404 })
    if (url.endsWith('/pages/directory')) { directoryReads += 1; return Response.json([directoryReads === 1 ? oldEntry : updatedPage]) }
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '没有概览' } }, { status: 404 })
    if (url.includes('/pages/page-race?expected_content_sha256=')) {
      detailReads += 1
      if (detailReads === 1) return Response.json({ error: { message: '页面已更新' } }, { status: 409 })
      return Response.json(updatedPage)
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  const tree = await screen.findByRole('navigation', { name: '文档目录' })
  fireEvent.click(within(tree).getByRole('button', { name: '模拟事实' }))
  expect(await screen.findByText('刚更新的正文')).toBeTruthy()
  expect(directoryReads).toBe(2)
  expect(detailReads).toBe(2)
})

it('automatically retries the body after a directory refresh even when its content hash is unchanged', async () => {
  const listedPage = { ...pages[0], page_id: 'page-same-hash', content_sha256: 'a'.repeat(64) }
  const recoveredPage = { ...listedPage, body: '恢复后的正文' }
  let directoryReads = 0
  let detailReads = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json(projects)
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/directory')) { directoryReads += 1; return Response.json([listedPage]) }
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '没有概览' } }, { status: 404 })
    if (url.includes('/pages/page-same-hash?expected_content_sha256=')) {
      detailReads += 1
      if (detailReads === 1) return Response.json({ error: { message: '页面已更新' } }, { status: 409 })
      return Response.json(recoveredPage)
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  const tree = await screen.findByRole('navigation', { name: '文档目录' })
  fireEvent.click(within(tree).getByRole('button', { name: '模拟事实' }))
  expect(await screen.findByText('恢复后的正文')).toBeTruthy()
  expect(directoryReads).toBe(2)
  expect(detailReads).toBe(2)
})

it('retries a transient project-inline detail failure with a fresh request', async () => {
  let detailReads = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json(projects)
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '没有概览' } }, { status: 404 })
    if (url.endsWith('/pages/directory')) return Response.json([{ ...pages[0], page_id: 'page-transient' }])
    if (url.includes('/pages/page-transient?expected_content_sha256=')) {
      detailReads += 1
      if (detailReads === 1) return Response.json({ error: { message: '暂时不可用' } }, { status: 503 })
      return Response.json({ ...pages[0], page_id: 'page-transient', body: '短暂失败后恢复的正文' })
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  const tree = await screen.findByRole('navigation', { name: '文档目录' })
  fireEvent.click(within(tree).getByRole('button', { name: '模拟事实' }))
  expect(await screen.findByText('短暂失败后恢复的正文', {}, { timeout: 3000 })).toBeTruthy()
  expect(detailReads).toBe(2)
})

it('keeps the same project overview reader mounted while an external change refreshes it', async () => {
  const overviewPage = {
    page_id: 'overview-1', relative_path: '模拟主线/模拟项目/概览.md',
    metadata: { id: 'overview-1', title: '项目概览', role: 'knowledge', kind: 'project_overview', line_id: 'line-1', project_id: 'project-1' },
    body: '项目概览长正文', content_sha256: 'e'.repeat(64), raw_sha256: 'f'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current',
  }
  let overviewReads = 0
  let releaseRefresh: (() => void) | undefined
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json(projects)
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/directory')) return Response.json([])
    if (url.endsWith('/pages/overview-1')) {
      overviewReads += 1
      if (overviewReads === 2) await new Promise<void>((resolve) => { releaseRefresh = resolve })
      return Response.json(overviewPage)
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  const view = render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /模拟项目/ }))
  await screen.findByText('项目概览长正文')
  const originalReader = document.querySelector('.project-overview-pane .page-reader')
  expect(originalReader).toBeTruthy()
  view.rerender(<ProjectsView externalPagesRevision={1} onError={vi.fn()} onOpenPage={vi.fn()} />)
  await waitFor(() => expect(overviewReads).toBe(2))
  expect(document.querySelector('.project-overview-pane .page-reader')).toBe(originalReader)
  expect(screen.getByText('项目概览长正文')).toBeTruthy()
  act(() => releaseRefresh?.())
})

it('shows unavailable auxiliary state on failure and an honest empty summary after recovery', async () => {
  let directoryReads = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return Response.json(lines)
    if (url.endsWith('/projects')) return Response.json([{ ...projects[0], progress: '' }])
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    if (url.endsWith('/pages/overview-1')) return Response.json({ error: { message: '没有概览' } }, { status: 404 })
    if (url.endsWith('/pages/directory')) {
      directoryReads += 1
      if (directoryReads === 1) return Promise.reject(new TypeError('offline'))
      return Response.json([])
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  const row = await screen.findByRole('button', { name: /模拟项目/ })
  expect(row.textContent).toContain('暂不可用')
  expect(row.textContent).toContain('项目资料暂不可用')
  expect(screen.getByText(/项目状态暂不可用/)).toBeTruthy()
  fireEvent.click(row)
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  expect(screen.getByText('项目页面目录读取失败。').textContent).toContain('重试')
  expect(screen.getByRole('region', { name: '项目详情' }).textContent).toContain('暂不可用')
  fireEvent.click(screen.getByRole('button', { name: '返回项目列表' }))
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'in_progress' } })
  expect(screen.getByText('项目状态暂不可用')).toBeTruthy()
  fireEvent.click(screen.getAllByRole('button', { name: '重试' }).slice(-1)[0])
  await waitFor(() => expect(directoryReads).toBe(2))
  fireEvent.change(screen.getByLabelText('筛选状态'), { target: { value: 'needs_setup' } })
  const recoveredRow = await screen.findByRole('button', { name: /模拟项目/ })
  expect(recoveredRow.textContent).toContain('新')
  expect(recoveredRow.textContent).toContain('还没有推进记录')
  expect(directoryReads).toBe(2)
})

it('keeps the summary honest when the index has never been built', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => projects }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    if (url.endsWith('/index/status')) {
      return { ok: true, status: 200, json: async () => ({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0, vector: 'unknown' }) }
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  render(<ProjectsView onError={vi.fn()} onOpenPage={vi.fn()} />)

  await screen.findByRole('button', { name: /模拟项目/ })
  expect(screen.getByText('尚未建立索引')).toBeTruthy()
  expect(screen.getByText('已索引页').nextElementSibling?.textContent).toBe('0')
})

it('opens the exact project requested by the sidebar shortcut and reports it as active', async () => {
  const second = { id: 'project-2', line_id: 'line-1', name: '第二项目', directory: '模拟主线/第二项目', overview_id: 'overview-2', archived: false }
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines')) return { ok: true, status: 200, json: async () => lines }
    if (url.endsWith('/projects')) return { ok: true, status: 200, json: async () => [projects[0], second] }
    if (url.endsWith('/pages/directory')) return { ok: true, status: 200, json: async () => pages }
    if (url.endsWith('/index/status')) {
      return { ok: true, status: 200, json: async () => ({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0, vector: 'unknown' }) }
    }
    throw new Error(`Unexpected request ${url}`)
  }))
  const onTargetHandled = vi.fn()
  const onActiveProjectChange = vi.fn()
  const onError = vi.fn()
  const { rerender } = render(<ProjectsView onError={onError} onOpenPage={vi.fn()} target={null} onTargetHandled={onTargetHandled} onActiveProjectChange={onActiveProjectChange} />)
  await screen.findByRole('button', { name: /第二项目/ })

  rerender(<ProjectsView onError={onError} onOpenPage={vi.fn()} target={{ id: 'project-2', nonce: 1 }} onTargetHandled={onTargetHandled} onActiveProjectChange={onActiveProjectChange} />)
  expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: '第二项目' })).toBeTruthy()
  expect(onTargetHandled).toHaveBeenCalled()
  await waitFor(() => expect(onActiveProjectChange).toHaveBeenCalledWith('project-2'))
})
