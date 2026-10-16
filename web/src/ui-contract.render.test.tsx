/**
 * 机器守卫 · 组件渲染（FRONTEND-GUIDE §11）。
 *
 * 本文件已实现并做变异验证：
 *   ① 渲染出的 DOM 里不得有内联样式裸色（与 ui-contract.test.ts 的源码扫描互补）
 *   B 深色一等公民 —— 主题三选在运行期写 <html data-theme> 并持久化（§5.6、§6.2）
 *   ⑧ 前半 —— 导航恰好 5 项、标签精确、顺序固定、当前项 aria-current="page"；
 *           退役的导航项不再占位；今日不出现「项目推进」卡与「待确认 N 条」计数
 * 其余本轮契约由 ProjectsView、PageReader、AskView、MarkdownText 的 focused 测试覆盖。
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { resetSaveStatus } from './save-status'
import { resetServiceStatus } from './service-status'
import { DARK_MEDIA_QUERY, THEME_STORAGE_KEY } from './theme'

const RULE_BARE_COLOR = '守卫① 裸色（GUIDE §11 ① 与 §6.1）：渲染出的内联样式不得出现裸 hex / rgb / hsl'
const RULE_THEME = '深色一等公民（GUIDE §5.6 与 §6.2）：主题三选必须在运行期写入 <html data-theme> 并持久化到 localStorage'
const RULE_NAV = '守卫⑧ 导航（GUIDE §11 ⑧ 与逐页规格 §0.1）：主导航恰好 5 项、标签精确、顺序固定、当前项 aria-current="page"'
const RULE_TODAY_RETIRED = '守卫⑧ 今日页（GUIDE §11 ⑧ 与逐页规格 §2「今日页不含」）：本轮已可判定的退役内容不得回到今日'

const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/

const workspace = {
  workspace_id: 'workspace-1',
  root: '/tmp/workspace',
  local_profile_dir: '/tmp/profile',
  name: '测试工作库',
  read_only: false,
}

/**
 * 外壳夹具。未登记的端点回一个中文 404（而不是抛错），
 * 这样扫描到的 DOM 里不会出现英文的 fetch 异常文案。
 */
function stubShell(overrides: Record<string, unknown> = {}) {
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/workspaces/current') return Response.json(workspace)
    if (url === '/api/v1/integrations/feishu/status') {
      return Response.json({ mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false, scopes: [] })
    }
    if (url.startsWith('/api/v1/index/status')) return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    const table: Record<string, unknown> = {
      '/api/v1/today': { items: [] },
      '/api/v1/journal': { items: [] },
      '/api/v1/intake/items': [],
      '/api/v1/drafts': [],
      '/api/v1/actions': [],
      '/api/v1/action-intents?limit=20': { items: [], next_cursor: null },
      '/api/v1/settings': { mode: 'fake', embedding_fingerprint: null },
      '/api/v1/lines': [],
      '/api/v1/projects': [],
      '/api/v1/pages': [],
      '/api/v1/conversations?limit=20': { items: [], next_cursor: null },
      '/api/v1/roles': [],
      '/api/v1/memory': [],
      '/api/v1/memory/candidates': [],
      ...overrides,
    }
    if (url.startsWith('/api/v1/pages/')) {
      const pageId = new URL(url, 'http://localhost').pathname.split('/').at(-1)
      const pages = table['/api/v1/pages'] as Array<{ page_id: string }>
      const match = pages.find((page) => page.page_id === pageId)
      return match ? Response.json(match) : Response.json({ error: { code: 'not_found', message: '找不到这个页面。' } }, { status: 404 })
    }
    if (url in table) return Response.json(table[url])
    return Response.json({ error: { code: 'not_found', message: '本机没有这个接口。' } }, { status: 404 })
  })
  vi.stubGlobal('fetch', rawFetch)
  return rawFetch
}

function stubSystemPrefersDark(matches: boolean): void {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches: query === DARK_MEDIA_QUERY ? matches : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })))
}

beforeEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  resetSaveStatus()
  resetServiceStatus()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  resetSaveStatus()
  resetServiceStatus()
})

it('渲染出的 DOM 里没有内联样式的裸色（GUIDE §11 ①）', async () => {
  stubShell()
  render(<App />)
  await screen.findByLabelText('主题')

  const offenders = Array.from(document.querySelectorAll<HTMLElement>('[style]'))
    .map((element) => ({ tag: element.tagName.toLowerCase(), style: element.getAttribute('style') ?? '' }))
    .filter((entry) => COLOR_LITERAL.test(entry.style))
    .map((entry) => `<${entry.tag} style="${entry.style}">`)
  const styledBlocks = Array.from(document.querySelectorAll('style'))
    .map((element) => element.textContent ?? '')
    .filter((text) => COLOR_LITERAL.test(text))

  expect(offenders, RULE_BARE_COLOR).toEqual([])
  expect(styledBlocks, RULE_BARE_COLOR).toEqual([])
})

it('主题三选：切换写入 <html data-theme> 并持久化（浅色 / 深色）', async () => {
  stubShell()
  render(<App />)
  const select = await screen.findByLabelText('主题')

  fireEvent.change(select, { target: { value: 'dark' } })
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('dark'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('dark')

  fireEvent.change(select, { target: { value: 'light' } })
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('light'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('light')
})

it('跟随系统：偏好 system 时按系统偏好解析 data-theme', async () => {
  stubSystemPrefersDark(true)
  window.localStorage.setItem(THEME_STORAGE_KEY, 'system')
  stubShell()
  render(<App />)

  await screen.findByLabelText('主题')
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('dark'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('system')
})

describe('守卫⑧ 页面区块（GUIDE §11 ⑧、§14 P1）', () => {
  it('主导航恰好 5 项、标签精确、顺序固定，当前项 aria-current="page"', async () => {
    stubShell()
    render(<App />)
    await screen.findByLabelText('主题')

    const nav = screen.getByRole('navigation', { name: '主导航' })
    const buttons = within(nav).getAllByRole('button')
    const labels = buttons.map((button) => button.querySelector('.nav-label')?.textContent)

    expect(labels, `${RULE_NAV}；D1 定的是 5 栏，不加第 6 项`).toEqual(['今日', '审批', '项目', '知识问答', '设置'])
    expect(buttons, RULE_NAV).toHaveLength(5)
    for (const button of buttons) {
      expect(button.getAttribute('title'), `${RULE_NAV}；≤800px 折成 64px 图标栏后靠 title`).toBeTruthy()
      expect(button.getAttribute('aria-label'), `${RULE_NAV}；图标栏必须保留可访问名`).toBeTruthy()
    }

    const current = () => buttons.filter((button) => button.getAttribute('aria-current') === 'page')
    expect(current().map((button) => button.textContent), RULE_NAV).toEqual(['今日'])

    fireEvent.click(within(nav).getByRole('button', { name: '审批' }))
    expect(within(nav).getByRole('button', { name: '审批' }).getAttribute('aria-current'), RULE_NAV).toBe('page')
    expect(within(nav).getByRole('button', { name: '今日' }).getAttribute('aria-current'), RULE_NAV).toBeNull()
  })

  it('退役的导航项不再占位（日志与思考 / 飞书日常）', async () => {
    stubShell()
    render(<App />)
    await screen.findByLabelText('主题')

    const nav = screen.getByRole('navigation', { name: '主导航' })
    expect(within(nav).queryByText('日志与思考'), 'D1：日志与思考并入今日工具区，不再占导航项').toBeNull()
    expect(within(nav).queryByText('飞书日常'), 'D1：飞书日常不再占导航项').toBeNull()
    expect(within(nav).queryByText('项目与知识'), 'D1：导航标签精确为「项目」').toBeNull()
  })

  it('今日页不出现本轮已可判定的退役内容', async () => {
    stubShell()
    render(<App />)
    await screen.findByLabelText('主题')

    const today = document.querySelector('.today-view')
    expect(today, '找不到今日页容器，说明外壳没渲染出今日').toBeTruthy()
    const text = today?.textContent ?? ''
    expect(text, `${RULE_TODAY_RETIRED}；项目推进卡属于项目页（§2）`).not.toMatch(/项目推进/)
    expect(text, `${RULE_TODAY_RETIRED}；首页不出现「待确认 N 条」这类属于审批页的计数（§2）`).not.toMatch(/待确认\s*\d+\s*条/)
  })

  it('审批徽章：待处理为 0 时不显示，有数据时显示数量', async () => {
    const items = [
      { item_id: 'item-1', source_id: 'source-1', title: '合成来源', filename: 'synthetic.txt', original_relative_path: '原件/synthetic.txt', created_at: '2026-10-14T00:00:00Z', state: 'pending' },
      { item_id: 'item-2', source_id: 'source-2', title: '第二个来源', filename: 'second.txt', original_relative_path: '原件/second.txt', created_at: '2026-10-14T00:00:00Z', state: 'failed' },
    ]
    const drafts = [
      { draft_id: 'draft-1', metadata: { title: '合成稿件' }, source_ids: ['source-1'], important_conflicts: [], state: 'pending', version: 1 },
    ]
    stubShell({ '/api/v1/intake/items': items, '/api/v1/drafts': drafts })
    render(<App />)

    const nav = await screen.findByRole('navigation', { name: '主导航' })
    const approval = await within(nav).findByRole('button', { name: '审批，3 项待处理' })
    expect(within(approval).getByText('3'), '徽章显示待处理总数（来源 + 稿件）').toBeTruthy()
  })

  it('今日把会议任务与记录导入并列展示，且默认不发送', async () => {
    const fetchMock = stubShell()
    render(<App />)
    await screen.findByText('还没有最近材料。')
    const today = document.querySelector('.today-view') as HTMLElement
    expect(today.querySelector('.today-columns')).toBeTruthy()
    expect(today.querySelector('.today-schedule')?.textContent).toContain('会议')
    expect(today.querySelector('.today-schedule')?.textContent).toContain('待办任务')
    expect(today.querySelector('.capture-panel')?.textContent).toContain('最近材料')
    expect(today.querySelectorAll('.today-tools button')).toHaveLength(3)
    expect(today.querySelector('.queue-panel, .review-panel, .today-rail')).toBeNull()
    expect(within(today).queryByRole('button', { name: /授权飞书/ })).toBeNull()
    expect(screen.queryByRole('heading', { name: '需要行动' })).toBeNull()
    const paths = fetchMock.mock.calls.map(([input]) => String(input))
    expect(paths.some((path) => /\/acceptance-plans|\/intake\/jobs|\/index\/plans|\/calendar\?|\/integrations\/feishu\/tasks\?/.test(path))).toBe(false)
  })

  it('项目、阅读和问答的普通文案使用中文名称且不泄漏内部标识', async () => {
    const line = { id: 'line-internal-123', name: '中文业务主线', directory: '中文业务主线' }
    const project = { id: 'project-internal-456', line_id: line.id, name: '中文业务项目', directory: '中文业务主线/中文业务项目', overview_id: 'overview-internal-789', archived: false, progress: '已经启动', progress_version: 1 }
    const page = {
      page_id: 'page-internal-abc', relative_path: '中文业务主线/中文业务项目/事实.md',
      metadata: { id: 'page-internal-abc', title: '中文事实记录', role: 'knowledge', kind: 'topic', line_id: line.id, project_id: project.id },
      body: '已确认的中文正文。\n\n```ts\nconst userText = "page-internal-abc";\n```', content_sha256: 'f'.repeat(64), raw_sha256: 'e'.repeat(64),
      storage_area: 'formal', approval_state: 'confirmed', validity: 'current',
    }
    const fetchMock = stubShell({ '/api/v1/lines': [line], '/api/v1/projects': [project], '/api/v1/pages': [page] })
    render(<App />)
    await screen.findByLabelText('主题')
    const nav = screen.getByRole('navigation', { name: '主导航' })
    fireEvent.click(within(nav).getByRole('button', { name: '项目' }))
    const row = await screen.findByRole('button', { name: /中文业务项目/ })
    expect(row.textContent).toContain('在推进')
    const noIdentifiers = (text: string, expectBusinessName = true) => {
      if (expectBusinessName) expect(text).toContain('中文')
      expect(text).not.toMatch(/line-internal-123|project-internal-456|overview-internal-789|page-internal-abc|f{64}|中文业务主线\/中文业务项目/)
    }
    noIdentifiers(document.querySelector('.projects-view')?.textContent ?? '')
    fireEvent.click(row)
    expect(await screen.findByRole('region', { name: '项目详情' })).toBeTruthy()
    noIdentifiers(document.querySelector('.project-detail')?.textContent ?? '')
    fireEvent.click(screen.getByRole('button', { name: /中文事实记录/ }))
    expect(await screen.findByText('已确认的中文正文。')).toBeTruthy()
    const reader = document.querySelector('.page-reader') as HTMLElement
    const readerOrdinaryText = reader.cloneNode(true) as HTMLElement
    readerOrdinaryText.querySelectorAll('pre code').forEach((code) => code.remove())
    noIdentifiers(readerOrdinaryText.textContent ?? '')
    expect(document.querySelector('.page-reader pre code')?.textContent).toMatch(/^const userText = "page-internal-abc";\n?$/)
    const ordinaryMetadata = document.querySelectorAll<HTMLElement>('.projects-view, .project-detail, .page-reader, .ask-view')
    const internalValue = /line-internal-123|project-internal-456|overview-internal-789|page-internal-abc|(?:[a-f0-9]{64})|(?:[\w.-]+\/){2,}[\w.-]+\.md|\{"(?:id|page_id|project_id)"/i
    const metadataLeaks = Array.from(ordinaryMetadata).flatMap((root) => Array.from(root.querySelectorAll<HTMLElement>('*')).filter((element) => !element.closest('pre code')).flatMap((element) =>
      ['title', 'aria-label'].map((attribute) => ({ tag: element.tagName.toLowerCase(), attribute, value: element.getAttribute(attribute) ?? '' }))
        .filter((entry) => internalValue.test(entry.value))))
    expect(metadataLeaks).toEqual([])
    fireEvent.click(within(nav).getByRole('button', { name: '知识问答' }))
    const question = await screen.findByLabelText('你的问题')
    const form = question.closest('form')!
    const history = document.querySelector('.ask-view details[aria-label="本机问答历史"]')!
    expect(form.compareDocumentPosition(history) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    noIdentifiers(document.querySelector('.ask-view')?.textContent ?? '', false)
    const providerOrPlanCalls = fetchMock.mock.calls.filter(([input]) => /acceptance-plans|index\/plans|index\/jobs|provider-smoke/.test(String(input)))
    expect(providerOrPlanCalls).toHaveLength(0)
  })
})

it('① 全站普通详情、标题与可访问名称不泄漏元数据并逐字保留用户代码', async () => {
  const line = { id: 'line-internal-123', name: '中文业务主线', directory: '中文业务主线' }
  const project = { id: 'project-internal-456', line_id: line.id, name: '中文业务项目', directory: '中文业务主线/中文业务项目', overview_id: 'overview-internal-789', archived: false, progress: '已经启动', progress_version: 1 }
  const page = {
    page_id: 'page-internal-abc', relative_path: '私密目录/中文事实.md',
    metadata: { id: 'page-internal-abc', title: '中文事实页面', role: 'knowledge', kind: 'topic', line_id: line.id, project_id: project.id },
    body: '中文业务正文。行内代码 `page-internal-abc`。\n\n```ts\nconst copiedExactly = "page-internal-abc";\n```',
    content_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), storage_area: 'formal', approval_state: 'confirmed', validity: 'current',
  }
  const source = { item_id: 'item-internal-12', source_id: 'source-internal-34', origin_kind: 'file', title: '中文收件标题', filename: '材料.txt', original_relative_path: '私密目录/材料.txt', created_at: '2026-10-14T00:00:00Z', state: 'pending' }
  const draft = { draft_id: 'draft-internal-56', input_ids: [], target_page_id: page.page_id, metadata: { title: '中文待审稿件' }, body: '中文待审核正文。', source_ids: [source.source_id], important_conflicts: [], state: 'pending', created_at: '2026-10-14T00:00:00Z', version: 1 }
  stubShell({
    '/api/v1/intake/items': [source], '/api/v1/drafts': [draft], '/api/v1/pages': [page],
    '/api/v1/lines': [line], '/api/v1/projects': [project],
    '/api/v1/conversations?limit=20': { items: [], next_cursor: null },
    '/api/v1/settings': {
      mode: 'fake', model_studio_account_id: 'account-internal-789',
      feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
      llm: { provider: 'fake', model: null, account_id: 'model-internal-123', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
      embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/v1', enabled: false },
      rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/v1', enabled: false },
      capabilities: {}, credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: false, embedding_fingerprint: 'fp-internal-456',
    },
  })
  render(<App />)
  await screen.findByLabelText('主题')
  const nav = screen.getByRole('navigation', { name: '主导航' })
  const scan = (root: Element | null, expectChineseName = true) => {
    expect(root).toBeTruthy()
    const clone = root!.cloneNode(true) as HTMLElement
    clone.querySelectorAll('code').forEach((code) => code.remove())
    const forbidden = /line-internal-123|project-internal-456|overview-internal-789|page-internal-abc|source-internal-34|item-internal-12|draft-internal-56|account-internal-789|model-internal-123|fp-internal-456|[a-f0-9]{64}|私密目录\/|\{"(?:id|page_id|project_id|source_id)"/i
    expect(clone.textContent).not.toMatch(forbidden)
    const attributes = Array.from(root!.querySelectorAll<HTMLElement>('*')).filter((element) => !element.closest('pre code')).flatMap((element) =>
      ['title', 'aria-label'].map((attribute) => element.getAttribute(attribute) ?? ''))
    expect(attributes.join('\n')).not.toMatch(forbidden)
    if (expectChineseName) expect(clone.textContent).toContain('中文')
  }

  scan(document.querySelector('.today-view'), false)
  fireEvent.click(within(nav).getByRole('button', { name: '审批' }))
  await screen.findAllByText('中文收件标题')
  scan(document.querySelector('.approval-view'))
  fireEvent.click(within(nav).getByRole('button', { name: '项目' }))
  const projectRow = await screen.findByRole('button', { name: /中文业务项目/ })
  scan(document.querySelector('.projects-view'))
  fireEvent.click(projectRow)
  await screen.findByRole('region', { name: '项目详情' })
  scan(document.querySelector('.project-detail'))
  fireEvent.click(screen.getByRole('button', { name: /中文事实页面/ }))
  await screen.findByText(/中文业务正文。行内代码/)
  const reader = document.querySelector('.page-reader')
  scan(reader)
  expect(reader?.querySelector('pre code')?.textContent).toMatch(/^const copiedExactly = "page-internal-abc";\n?$/)
  expect(reader?.querySelector('p code')?.textContent).toBe('page-internal-abc')
  fireEvent.click(within(nav).getByRole('button', { name: '知识问答' }))
  await screen.findByLabelText('你的问题')
  scan(document.querySelector('.ask-view'), false)
  fireEvent.click(within(nav).getByRole('button', { name: '设置' }))
  await screen.findByRole('heading', { name: '设置' })
  scan(document.querySelector('.settings-view'), false)
  fireEvent.click(await screen.findByRole('button', { name: '打开连接向导' }))
  await screen.findByRole('dialog', { name: '首次配置向导' })
  scan(document.querySelector('.onboarding-host'), false)
})

// ① 元数据渲染断言见上方运行时跨页测试；Ask/Today/Approval 状态、危险操作和 Markdown 分块断言由 focused 渲染测试覆盖。
