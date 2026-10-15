import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('persists a changed Model Studio account id through the settings form', async () => {
  const state = {
    mode: 'fake', model_studio_account_id: 'original-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: false },
    credential_status: {}, capabilities: {}, keychain_available: false,
  }
  let patch: Record<string, unknown> | null = null
  vi.stubGlobal('fetch', vi.fn(async (_url: unknown, init?: RequestInit) => {
    if (init?.method === 'PATCH') {
      patch = JSON.parse(String(init.body))
    }
    return { ok: true, status: 200, json: async () => state }
  }))
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  const field = await screen.findByLabelText('Model Studio 账户标识')
  fireEvent.change(field, { target: { value: 'new-account' } })
  fireEvent.click(screen.getByRole('button', { name: '保存 provider 设置' }))
  await waitFor(() => expect(patch).not.toBeNull())
  expect(patch).toHaveProperty('model_studio_account_id', 'new-account')
})

it('saves the account id and the matching API key in one card submit', async () => {
  const state = {
    mode: 'fake',
    model_studio_account_id: 'original-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: false },
    credential_status: { feishu_app: false, deepseek: false, dashscope: false },
    capabilities: {},
    keychain_available: true,
  }
  let accountId: string | null = null
  const methods: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (_url: unknown, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    methods.push(method)
    if (method === 'PATCH') {
      Object.assign(state, JSON.parse(String(init.body)))
    }
    if (method === 'PUT') {
      accountId = JSON.parse(String(init.body)).account_id
      state.credential_status.dashscope = true
    }
    return { ok: true, status: 200, json: async () => state }
  }))
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('Model Studio 账户标识'), { target: { value: 'new-account' } })
  fireEvent.change(screen.getByLabelText(/阿里云 Model Studio API Key/), { target: { value: 'synthetic-key' } })
  // 录入密钥不再需要先单独保存账户标识。
  expect(methods).not.toContain('PUT')
  fireEvent.click(screen.getByRole('button', { name: '保存 AI 模型设置' }))
  await waitFor(() => expect(accountId).toBe('new-account'))
  expect(methods.indexOf('PATCH')).toBeGreaterThanOrEqual(0)
  expect(methods.indexOf('PATCH')).toBeLessThan(methods.indexOf('PUT'))
})

it('asks for an explicit range confirmation before calling the fixed DeepSeek smoke route', async () => {
  const state = {
    mode: 'real', model_studio_account_id: 'synthetic-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'default', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: false },
    credential_status: { feishu_app: false, deepseek: true, dashscope: false },
    capabilities: {}, keychain_available: true,
  }
  const smoke = { counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 } }
  const smokePosts = () => fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/provider-smoke/deepseek-chat'))
  const fetchMock = vi.fn(async (url: unknown, init?: RequestInit) => {
    void init
    if (String(url).endsWith('/provider-smoke/deepseek-chat')) return { ok: true, status: 200, json: async () => ({ state: 'succeeded' }) }
    if (String(url).endsWith('/provider-smoke')) return { ok: true, status: 200, json: async () => smoke }
    return { ok: true, status: 200, json: async () => state }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  const button = await screen.findByRole('button', { name: 'DeepSeek Chat（剩余 1）' })
  expect((button as HTMLButtonElement).disabled).toBe(false)
  fireEvent.click(button)
  const dialog = await screen.findByRole('dialog', { name: '确认本次连接检查：DeepSeek Chat' })
  expect(dialog.textContent).toContain('累计已用 0/1')
  expect(dialog.textContent).toContain('不会自动重发')
  expect(smokePosts()).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(smokePosts()).toHaveLength(0)
  fireEvent.click(button)
  fireEvent.click(await screen.findByRole('button', { name: '确认发送本次检查' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/provider-smoke/deepseek-chat', expect.objectContaining({ method: 'POST' })))
})

it('does not delete a credential until the destructive confirmation is accepted', async () => {
  const state = {
    mode: 'fake', model_studio_account_id: 'synthetic-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
    credential_status: { feishu_app: false, deepseek: true, dashscope: false },
    capabilities: {}, keychain_available: false,
  }
  const fetchMock = vi.fn(async (_url: unknown, init?: RequestInit) => ({ ok: true, status: 200, json: async () => {
    void init
    return state
  } }))
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await screen.findAllByRole('button', { name: '删除本机密钥' })
  const modelCard = screen.getByRole('region', { name: 'AI 模型' })
  fireEvent.click(within(modelCard).getAllByRole('button', { name: '删除本机密钥' })[0]!)
  const dialog = await screen.findByRole('dialog', { name: '删除所选本机密钥？' })
  expect(document.activeElement).toBe(within(dialog).getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  fireEvent.click(within(dialog).getByRole('button', { name: '取消' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  fireEvent.click(within(modelCard).getAllByRole('button', { name: '删除本机密钥' })[0]!)
  fireEvent.click(await screen.findByRole('button', { name: '删除密钥' }))
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(1))
})
