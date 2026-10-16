import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { firstUseProgressKey } from './components/firstUseProgress'
import { resetSaveStatus } from './save-status'
import { resetServiceStatus } from './service-status'

/**
 * 里程碑 D repair1 的核心回归：首次配置进度必须存在本机后端。
 *
 * 修复前 `App.onOpened` 无条件打开向导第 2 步，而进度只写在 localStorage；
 * 生产 WKWebView 是 nonPersistent 存储，重启后进度消失，于是「已经配好」的
 * 工作库每次打开都被再次拉回模型与密钥步骤，今日页不可达。
 *
 * 这里用真实外壳 + 模拟本机 API 复现那条用户路径。
 */

const workspace = {
  workspace_id: 'workspace-1',
  root: '/tmp/workspace',
  local_profile_dir: '/tmp/profile',
  name: '模拟工作库',
  read_only: false,
}

type Progress = { step: 2 | 3 | 4 | 5; completed: boolean; open: boolean }

function progressResponse(body: unknown, status = 200) {
  return Response.json(body, { status })
}

const absent = () => progressResponse(
  { error: { code: 'first_use_progress_absent', message: '本机还没有保存首次配置进度。' } }, 404,
)

/** 一个可写的模拟后端：GET/PUT 首次配置进度，其余端点给出外壳需要的最小夹具。 */
function backend(options: { alreadyOpen?: boolean; stored?: Progress | null } = {}) {
  const state: { stored: Progress | null; writes: Progress[]; failWrite: boolean } = {
    stored: options.stored ?? null,
    writes: [],
    failWrite: false,
  }
  const table: Record<string, unknown> = {
    '/api/v1/index/status': { fingerprint: null, pages: 0, chunks: 0, state: 'not_ready', current_pages: 0, stale_pages: 0 },
    '/api/v1/intake/items': [],
    '/api/v1/drafts': [],
    '/api/v1/actions': [],
    '/api/v1/lines': [],
    '/api/v1/projects': [],
    '/api/v1/pages': [],
    '/api/v1/today': { items: [] },
    '/api/v1/journal': { items: [] },
    '/api/v1/action-intents?limit=20': { items: [], next_cursor: null },
    '/api/v1/roles': [],
    '/api/v1/memory': [],
    '/api/v1/memory/candidates': [],
    '/api/v1/conversations?limit=20': { items: [], next_cursor: null },
    '/api/v1/integrations/feishu/status': {
      mode: 'fake', authorized: false, app_configured: false, user_identity_verified: false, scopes: [],
    },
    '/api/v1/settings': {
      mode: 'fake', model_studio_account_id: 'studio-default',
      feishu: { app_id: 'synthetic-app', redirect_uri: '' },
      llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
      embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
      rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
      capabilities: {},
      credential_status: { feishu_app: false, deepseek: false, dashscope: false },
      keychain_available: true,
      embedding_fingerprint: null,
    },
  }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/v1/workspaces/current') {
      return options.alreadyOpen
        ? Response.json(workspace)
        : progressResponse({ error: { code: 'workspace_not_open', message: '还没有打开工作库' } }, 409)
    }
    if (url === '/api/v1/workspaces') return Response.json(workspace)
    if (url === '/api/v1/first-use/progress') {
      if ((init?.method ?? 'GET') === 'PUT') {
        if (state.failWrite) {
          return progressResponse(
            { error: { code: 'progress_unavailable', message: '首次配置进度无法读写，请检查本机 profile 后重试。' } }, 503,
          )
        }
        const written = JSON.parse(String(init?.body)) as Progress
        state.writes.push(written)
        state.stored = written
        return Response.json(written)
      }
      return state.stored ? Response.json(state.stored) : absent()
    }
    if (url in table) return Response.json(table[url])
    return progressResponse({ error: { code: 'not_found', message: '本机没有这个接口。' } }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return state
}

/** 走过真实的工作库 gate：选「打开已有」并提交。 */
async function openExistingWorkspace() {
  fireEvent.click(await screen.findByLabelText('打开已有'))
  fireEvent.change(screen.getByLabelText('文件夹路径'), { target: { value: '/tmp/workspace' } })
  fireEvent.click(screen.getByRole('button', { name: '打开工作库' }))
}

/** 走过真实的工作库 gate：保持默认的「新建」并提交。 */
async function createNewWorkspace() {
  fireEvent.change(await screen.findByLabelText('工作库名称'), { target: { value: '新模拟库' } })
  fireEvent.change(screen.getByLabelText('文件夹路径'), { target: { value: '/tmp/workspace' } })
  fireEvent.click(screen.getByRole('button', { name: '创建本地工作库' }))
}

const wizard = () => screen.queryByRole('dialog', { name: '首次配置向导' })

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
})

it('已完成的首次配置：打开同一工作库直接进入今日，不再弹向导', async () => {
  backend({ stored: { step: 5, completed: true, open: false } })
  render(<App />)

  await openExistingWorkspace()

  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  expect(wizard()).toBeNull()
  expect(screen.queryByRole('heading', { name: /第 2 步 · 模型与密钥/ })).toBeNull()
})

it('未完成但向导仍开着的记录：恢复到保存的步骤', async () => {
  backend({ stored: { step: 3, completed: false, open: true } })
  render(<App />)

  await openExistingWorkspace()

  expect(await screen.findByRole('dialog', { name: '首次配置向导' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeTruthy()
})

it('用户明确关闭过向导：重启不自动出现，设置里仍能手动续接原步骤', async () => {
  backend({ stored: { step: 3, completed: false, open: false } })
  render(<App />)

  await openExistingWorkspace()

  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  expect(wizard()).toBeNull()

  fireEvent.click(screen.getByRole('button', { name: '设置' }))
  fireEvent.click(await screen.findByRole('button', { name: '打开连接向导' }))

  expect(await screen.findByRole('dialog', { name: '首次配置向导' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeTruthy()
})

it('本机没有记录：新建工作库仍从第 2 步开始首次配置', async () => {
  backend()
  render(<App />)

  await createNewWorkspace()

  expect(await screen.findByRole('dialog', { name: '首次配置向导' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: /第 2 步 · 模型与密钥/ })).toBeTruthy()
})

it('打开已有工作库但没有本机记录：落到今日并给出非阻塞提示，不遮挡今日（QA D-1）', async () => {
  backend()
  render(<App />)

  await openExistingWorkspace()

  // 旧版本配好的工作库在本机没有记录时不再被 onboarding 挡住：今日直接可达。
  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  expect(wizard()).toBeNull()
  expect(await screen.findByText(/还没有首次配置记录/)).toBeTruthy()
})

it('旧的浏览器副本迁移一次后，后端成为唯一真源', async () => {
  const state = backend()
  const key = firstUseProgressKey('/tmp/profile', 'workspace-1')
  window.localStorage.setItem(key, JSON.stringify({ step: 5, completed: true, open: false }))
  render(<App />)

  await openExistingWorkspace()

  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  await waitFor(() => expect(state.writes).toEqual([{ step: 5, completed: true, open: false }]))
  expect(window.localStorage.getItem(key)).toBeNull()
})

it('durable 写入失败时停在当前步骤并给出重试，重试成功后继续', async () => {
  const state = backend({ stored: { step: 2, completed: false, open: true } })
  state.failWrite = true
  render(<App />)

  await openExistingWorkspace()
  await screen.findByRole('dialog', { name: '首次配置向导' })

  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))

  // 没有写成功就不能假装前进。
  expect(await screen.findByText(/还没有保存到本机/)).toBeTruthy()
  expect(screen.getByRole('heading', { name: /第 2 步 · 模型与密钥/ })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeNull()
  expect(state.writes).toEqual([])

  state.failWrite = false
  fireEvent.click(screen.getByRole('button', { name: '重试保存' }))

  expect(await screen.findByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeTruthy()
  expect(state.writes).toEqual([{ step: 3, completed: false, open: true }])
})

it('完成向导会先把 completed 写进本机，再进入今日', async () => {
  const state = backend({ stored: { step: 2, completed: false, open: true } })
  render(<App />)

  await openExistingWorkspace()
  await screen.findByRole('dialog', { name: '首次配置向导' })
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 3 步 · 检查连接/ })
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 4 步 · 飞书/ })
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 5 步 · 完成/ })
  fireEvent.click(screen.getByRole('button', { name: '完成并进入今日' }))

  expect(await screen.findByRole('heading', { name: '今日' })).toBeTruthy()
  expect(wizard()).toBeNull()
  expect(state.stored).toEqual({ step: 5, completed: true, open: false })
})
