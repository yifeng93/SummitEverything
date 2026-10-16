import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { resetSaveStatus } from './save-status'
import { resetServiceStatus } from './service-status'
import { THEME_STORAGE_KEY } from './theme'

/**
 * 外壳三态 + 真实状态 + 审批接入（逐页规格 §0、§11 ⑧ 的前半）。
 *
 * 关键行为：**只有**后端明确回答「还没有工作库」（409 `workspace_not_open`）才进首次配置向导；
 * 连接中显示「正在连接本机服务…」；连不上或 500 显示就地提示，绝不冒充「还没有工作库」。
 */

const workspace = {
  workspace_id: 'workspace-1',
  root: '/tmp/workspace',
  local_profile_dir: '/tmp/profile',
  name: '模拟工作库',
  read_only: false,
}

const feishuStatus = {
  mode: 'fake',
  authorized: false,
  app_configured: false,
  user_identity_verified: false,
  scopes: [],
}

/** 完整的外壳夹具：不制造无关的读取失败，除非用例显式覆盖某个端点。 */
function shellFetch(overrides: Record<string, unknown> = {}, status = 200) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/workspaces/current') return Response.json(workspace)
    if (url === '/api/v1/integrations/feishu/status') return Response.json(feishuStatus)
    if (url.startsWith('/api/v1/index/status')) {
      return Response.json({ fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 })
    }
    const table: Record<string, unknown> = {
      // 外壳夹具代表一个已经完成首次配置的工作库：进度记录必须来自本机后端，
      // 否则 App 会按「新工作库」打开向导。
      '/api/v1/first-use/progress': { step: 5, completed: true, open: false },
      '/api/v1/intake/items': [],
      '/api/v1/drafts': [],
      '/api/v1/actions': [],
      '/api/v1/lines': [],
      '/api/v1/projects': [],
      '/api/v1/pages': [],
      '/api/v1/today': { items: [] },
      '/api/v1/journal': { items: [] },
      '/api/v1/action-intents?limit=20': { items: [], next_cursor: null },
      '/api/v1/settings': {
        mode: 'fake', model_studio_account_id: 'studio-default',
        feishu: { app_id: 'synthetic-app', redirect_uri: '' },
        llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'team-account', enabled: false },
        embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
        rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
        capabilities: { llm: { available: false, configured: false, disabled_reason: 'offline_default' } },
        credential_status: { feishu_app: false, deepseek: false, dashscope: false }, keychain_available: true,
        embedding_fingerprint: null,
      },
      '/api/v1/roles': [],
      '/api/v1/memory': [],
      '/api/v1/memory/candidates': [],
      '/api/v1/conversations?limit=20': { items: [], next_cursor: null },
      ...overrides,
    }
    if (url in table) {
      const payload = table[url]
      if (status !== 200) return Response.json(payload, { status })
      return Response.json(payload)
    }
    return Response.json({ error: { code: 'not_found', message: '本机没有这个接口。' } }, { status: 404 })
  })
}

beforeEach(() => {
  resetSaveStatus()
  resetServiceStatus()
  window.localStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  resetSaveStatus()
  resetServiceStatus()
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

it('加载中显示「正在连接本机服务…」，不显示工作库向导', async () => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
  render(<App />)

  expect(await screen.findByText('正在连接本机服务…')).toBeTruthy()
  expect(screen.queryByRole('button', { name: '创建本地工作库' })).toBeNull()
  expect(screen.queryByLabelText('文件夹路径')).toBeNull()
  expect(screen.queryByRole('navigation', { name: '主导航' })).toBeNull()
})

it('本机服务不可达：就地提示 + 重试 + L2 日志目录，不冒充「还没有工作库」', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
  render(<App />)

  expect(await screen.findByText('没有连上本机服务')).toBeTruthy()
  expect(screen.getByRole('button', { name: '重试' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: '创建本地工作库' }), '逐页规格 §0：连不上时不得进首次配置').toBeNull()
  expect(document.body.textContent).not.toContain('Failed to fetch')

  // 日志目录在 L2（折叠区）里，还是白话说明；默认位置要标出来是默认值。
  fireEvent.click(screen.getByText('查看日志目录'))
  expect(screen.getByText(/_?~?\/?Library\/Application Support\/SummitEverything/)).toBeTruthy()
  expect(document.body.textContent).toContain('默认位置')

  vi.stubGlobal('fetch', shellFetch())
  fireEvent.click(screen.getByRole('button', { name: '重试' }))
  expect(await screen.findByRole('navigation', { name: '主导航' })).toBeTruthy()
  expect(document.querySelector('.local-indicator')?.textContent).toBe('仅本机运行')
})

it('本机服务报 500 也显示就地提示，而不是工作库向导（守卫④ 变体）', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ error: { code: 'internal_error', message: '本机服务出错了。' } }, { status: 500 })))
  render(<App />)

  expect(await screen.findByText('没有连上本机服务')).toBeTruthy()
  expect(screen.queryByRole('button', { name: '创建本地工作库' })).toBeNull()
})

it('后端明确回答「还没有工作库」时才进首次配置向导', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(
    { error: { code: 'workspace_not_open', message: 'Open a workspace first' } },
    { status: 409 },
  )))
  render(<App />)

  expect(await screen.findByRole('button', { name: '创建本地工作库' })).toBeTruthy()
  expect(screen.queryByText('正在连接本机服务…')).toBeNull()
})

it('侧栏审批徽章与审批页共用同一份清单，数量一致', async () => {
  const items = [
    { item_id: 'item-1', source_id: 'source-1', title: '合成会议纪要', filename: 'meeting.txt', original_relative_path: '原件/meeting.txt', created_at: '2026-10-14T00:00:00Z', state: 'pending' },
    { item_id: 'item-2', source_id: 'source-2', title: '已经处理完的材料', filename: 'done.txt', original_relative_path: '原件/done.txt', created_at: '2026-10-14T00:00:00Z', state: 'completed' },
  ]
  const drafts = [
    { draft_id: 'draft-1', metadata: { title: '合成稿件' }, source_ids: ['source-1'], important_conflicts: [], state: 'pending', version: 1 },
    { draft_id: 'draft-2', metadata: { title: '已确认稿件' }, source_ids: ['source-1'], important_conflicts: [], state: 'confirmed', version: 1 },
  ]
  vi.stubGlobal('fetch', shellFetch({ '/api/v1/intake/items': items, '/api/v1/drafts': drafts }))
  render(<App />)

  const nav = await screen.findByRole('navigation', { name: '主导航' })
  const approval = await within(nav).findByRole('button', { name: '审批，2 项待处理' })
  expect(within(approval).getByText('2')).toBeTruthy()

  fireEvent.click(approval)
  expect(await screen.findByText(/2 项待处理 · 共 2 类/)).toBeTruthy()
  const approvalView = document.querySelector('.approval-view') as HTMLElement
  expect(within(approvalView).getByText('合成会议纪要')).toBeTruthy()
  expect(within(approvalView).getByText('合成稿件')).toBeTruthy()
  expect(within(approvalView).queryByText('已经处理完的材料')).toBeNull()
  expect(within(approvalView).queryByText('已确认稿件')).toBeNull()
})

it('dirty draft blocks sidebar navigation and accepted discard returns to the saved list', async () => {
  const reviewDraft = { draft_id: 'draft-focus', metadata: { title: '需保护的稿件' }, body: '# 原正文', source_ids: ['source-focus'], important_conflicts: [], state: 'pending', version: 1 }
  vi.stubGlobal('fetch', shellFetch({ '/api/v1/drafts': [reviewDraft] }))
  render(<App />)
  const nav = await screen.findByRole('navigation', { name: '主导航' })
  fireEvent.click(within(nav).getByRole('button', { name: /^审批/ }))
  fireEvent.click(await screen.findByRole('button', { name: '打开稿件：需保护的稿件' }))
  const focus = await screen.findByRole('region', { name: '稿件审核：需保护的稿件' })
  fireEvent.click(within(focus).getByText('编辑稿件、归属与来源'))
  const body = within(focus).getByLabelText('正文') as HTMLTextAreaElement
  fireEvent.change(body, { target: { value: '# 保留这段修改' } })

  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  fireEvent.click(within(nav).getByRole('button', { name: '项目' }))
  expect(confirm).toHaveBeenCalledWith('稿件有未保存的修改。离开审批会放弃这些修改，是否继续？')
  expect(within(nav).getByRole('button', { name: /^审批/ }).getAttribute('aria-current')).toBe('page')
  expect(body.value).toBe('# 保留这段修改')

  confirm.mockReturnValue(true)
  fireEvent.click(within(nav).getByRole('button', { name: '项目' }))
  expect(await screen.findByRole('heading', { name: '项目' })).toBeTruthy()
  fireEvent.click(within(nav).getByRole('button', { name: /^审批/ }))
  expect(await screen.findByRole('region', { name: '审批清单' })).toBeTruthy()
  expect(screen.queryByRole('region', { name: '稿件审核：需保护的稿件' })).toBeNull()
})

it('待处理为 0 时不显示徽章', async () => {
  vi.stubGlobal('fetch', shellFetch())
  render(<App />)

  const nav = await screen.findByRole('navigation', { name: '主导航' })
  const approval = within(nav).getByRole('button', { name: '审批' })
  expect(approval.querySelector('.nav-badge')).toBeNull()
})

it('Today→Settings→Today keeps cached inbox; a confirmed authorization change refreshes it', async () => {
  let authorized = false
  const baseFetch = shellFetch()
  const fetch = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === '/api/v1/integrations/feishu/status') return Response.json({ ...feishuStatus, authorized })
    return baseFetch(input)
  })
  vi.stubGlobal('fetch', fetch)
  render(<App />)
  await screen.findByText('还没有最近材料。')
  const inboxReads = () => fetch.mock.calls.filter(([input]) => String(input) === '/api/v1/intake/items').length
  const initialReads = inboxReads()

  fireEvent.click(screen.getByRole('button', { name: '设置' }))
  expect(await screen.findByRole('heading', { name: '设置' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '今日' }))
  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  expect(inboxReads()).toBe(initialReads)

  fireEvent.click(screen.getByRole('button', { name: '设置' }))
  await screen.findByRole('button', { name: '重新读取授权状态' })
  authorized = true
  fireEvent.click(screen.getByRole('button', { name: '重新读取授权状态' }))
  await waitFor(() => expect(inboxReads()).toBe(initialReads + 1))
})

it('全局失败提示走 toast（可手关），没有常驻红色横幅', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/intake/items' && init?.method === 'POST') return Response.json({ error: { message: '本机读取出了点问题。' } }, { status: 500 })
    return shellFetch()(input)
  }))
  render(<App />)

  await screen.findByText('还没有最近材料。')
  fireEvent.change(screen.getByLabelText('记下一句话'), { target: { value: '触发提示的合成记录' } })
  fireEvent.click(screen.getByRole('button', { name: '保存原文' }))

  const toast = await screen.findByRole('alert')
  expect(toast.textContent).toContain('本机读取出了点问题。')
  expect(toast.className).toContain('toast-danger')
  expect(document.querySelector('.global-alert')).toBeNull()

  fireEvent.click(screen.getByRole('button', { name: '关闭这条提示' }))
  await waitFor(() => expect(screen.queryByText('本机读取出了点问题。')).toBeNull())
})

it('「切换…」离开当前工作库，回到首次配置向导', async () => {
  vi.stubGlobal('fetch', shellFetch())
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: '切换工作库' }))
  expect(await screen.findByRole('button', { name: '创建本地工作库' })).toBeTruthy()
  expect(screen.queryByRole('navigation', { name: '主导航' })).toBeNull()
})

it('主题三选在运行期写入 data-theme 并持久化（外壳重写后仍然可用）', async () => {
  vi.stubGlobal('fetch', shellFetch())
  render(<App />)

  const select = await screen.findByLabelText('主题')
  fireEvent.change(select, { target: { value: 'dark' } })
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe('dark'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
})
