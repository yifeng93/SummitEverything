/**
 * 机器守卫 · 组件渲染（FRONTEND-GUIDE §11）。
 *
 * 本文件已实现并做变异验证：
 *   ① 渲染出的 DOM 里不得有内联样式裸色（与 ui-contract.test.ts 的源码扫描互补）
 *   B 深色一等公民 —— 主题三选在运行期写 <html data-theme> 并持久化（§5.6、§6.2）
 *   ⑧ 前半 —— 导航恰好 5 项、标签精确、顺序固定、当前项 aria-current="page"；
 *           退役的导航项不再占位；今日不出现「项目推进」卡与「待确认 N 条」计数
 * 其余渲染类守卫以 it.todo 登记归属切片（不得当成已通过）。
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
      ...overrides,
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

  it('今日主内容按会议、任务、行动、收件箱排列，只提供两个主工具并且默认不发送', async () => {
    const fetchMock = stubShell()
    render(<App />)
    await screen.findByText('收件箱目前没有内容。')
    const today = document.querySelector('.today-view') as HTMLElement
    const stack = today.querySelector('.today-stack') as HTMLElement
    const headings = Array.from(stack.children).map((section) => section.querySelector('h2')?.textContent).filter(Boolean)
    expect(headings).toEqual(['会议', '待办任务', '收件箱'])
    expect(today.querySelectorAll('.today-tools button')).toHaveLength(2)
    expect(today.querySelector('.queue-panel, .review-panel, .today-rail')).toBeNull()
    expect(within(today).queryByRole('button', { name: /授权飞书/ })).toBeNull()
    expect(screen.queryByRole('heading', { name: '需要行动' })).toBeNull()
    const paths = fetchMock.mock.calls.map(([input]) => String(input))
    expect(paths.some((path) => /\/acceptance-plans|\/intake\/jobs|\/index\/plans|\/calendar\?|\/integrations\/feishu\/tasks\?/.test(path))).toBe(false)
  })
})

// ── 本轮不实现，登记归属切片（禁止当成通过）───────────────────────────────────
it.todo('② 中文优先：渲染含英文 ID 的项目/主线，可见文本含中文名且不含 ID，ID 能在某个 title 里找到 —— 归属 P4 · 项目与问答（需要项目页）')
it.todo('④ 加载与空分离：对今日/审批/项目/问答 mock 永不 resolve 的 fetch，断言出现「正在读取…」且不出现空态文案 —— 归属 P3 · 信息架构（需要四个视图）')
it.todo('⑤ 删除/断开类动作必须确认：点击后出现 role="dialog" 且 API 未被调用，确认后恰好 1 次 —— 归属 P3/P4（需要页面实现确认弹层）')
it.todo('⑥ Markdown 渲染与流式容错：断言输出含 <strong>/标题/<table>，可见文本不含 ** / [[，三分块流式中间态不出现未闭合标记 —— 归属 P2 · 阅读与流式（含 react-markdown + remark-gfm 新依赖）')
it.todo('⑨ 项目/问答列表渲染不得调用模型：对 /acceptance-plans、/index/plans 的调用次数为 0 —— 归属 P4（需项目与问答空/加载覆盖）')
