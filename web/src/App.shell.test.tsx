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
      '/api/v1/intake/items': [],
      '/api/v1/drafts': [],
      '/api/v1/actions': [],
      '/api/v1/lines': [],
      '/api/v1/projects': [],
      '/api/v1/pages': [],
      '/api/v1/today': { items: [] },
      '/api/v1/journal': { items: [] },
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
  expect(await screen.findByText(/待处理 2 项 · 共 2 类/)).toBeTruthy()
  expect(await screen.findByText('合成会议纪要')).toBeTruthy()
  expect(screen.getByText('合成稿件')).toBeTruthy()
  expect(screen.queryByText('已经处理完的材料')).toBeNull()
  expect(screen.queryByText('已确认稿件')).toBeNull()
})

it('待处理为 0 时不显示徽章', async () => {
  vi.stubGlobal('fetch', shellFetch())
  render(<App />)

  const nav = await screen.findByRole('navigation', { name: '主导航' })
  const approval = within(nav).getByRole('button', { name: '审批' })
  expect(approval.querySelector('.nav-badge')).toBeNull()
})

it('全局失败提示走 toast（可手关），没有常驻红色横幅', async () => {
  vi.stubGlobal('fetch', shellFetch({ '/api/v1/intake/items': { error: { message: '本机读取出了点问题。' } } }, 500))
  render(<App />)

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
