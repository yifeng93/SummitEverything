import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('copies the same agent setup prompt from settings without opening the manual wizard', async () => {
  const state = {
    mode: 'fake', feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid', enabled: false },
    credential_status: {}, capabilities: {}, keychain_available: false,
  }
  const fetchMock = vi.fn(async (_input: RequestInfo | URL) => ({ ok: true, status: 200, json: async () => state }))
  const writeText = vi.fn().mockResolvedValue(undefined)
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('navigator', { clipboard: { writeText } })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '连接飞书' }))
  expect(await screen.findByRole('button', { name: /已复制/ })).toBeTruthy()
  expect(writeText).toHaveBeenCalledTimes(1)
  expect(fetchMock.mock.calls.some((call) => String(call[0]).includes('/authorization'))).toBe(false)
  expect(screen.queryByText(/步骤指示/)).toBeNull()
})

it('offers an explicit migration from the disabled cloud search provider', async () => {
  const state = {
    mode: 'fake', model_studio_account_id: 'original-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
    embedding: { provider: 'dashscope', model: 'text-embedding-v3', region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: true },
    rerank: { provider: 'dashscope', model: 'gte-rerank-v2', region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: true },
    credential_status: {}, capabilities: {}, keychain_available: false,
  }
  let patch: Record<string, unknown> | null = null
  const fetchMock = vi.fn(async (_url: unknown, init?: RequestInit) => {
    if (init?.method === 'PATCH') {
      patch = JSON.parse(String(init.body))
      Object.assign(state, patch)
    }
    return { ok: true, status: 200, json: async () => state }
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '切换到本地检索' }))
  await waitFor(() => expect(patch).not.toBeNull())
  expect(patch).toMatchObject({
    embedding: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', dimensions: 512, enabled: true },
    rerank: { provider: 'local', model: 'BAAI/bge-small-zh-v1.5', dimensions: 512, enabled: true },
  })
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE' || init?.method === 'PUT')).toBe(false)
  expect(screen.getByText(/原有云端密钥仍留在本机/)).toBeTruthy()
})

it('does not expose legacy cloud search credentials or offer their deletion', async () => {
  const state = {
    mode: 'fake',
    model_studio_account_id: 'original-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false },
    embedding: { provider: 'dashscope', model: 'text-embedding-v3', region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: true },
    rerank: { provider: 'dashscope', model: 'gte-rerank-v2', region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: true },
    credential_status: { feishu_app: false, deepseek: false, dashscope: true },
    capabilities: {},
    keychain_available: true,
  }
  const fetchMock = vi.fn(async (_url: unknown, _init?: RequestInit) => ({ ok: true, status: 200, json: async () => state }))
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.click(await screen.findByText(/高级与自定义/))
  expect(screen.queryByLabelText('Model Studio 账户标识')).toBeNull()
  expect(screen.queryByLabelText(/阿里云 Model Studio API Key/)).toBeNull()
  expect(screen.queryByRole('button', { name: '删除 Model Studio 密钥' })).toBeNull()
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  expect(state.credential_status.dashscope).toBe(true)
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
  fireEvent.click(await screen.findByText(/高级与自定义/))
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

it.each([
  ['deepseek', '删除 DeepSeek 密钥'],
  ['feishu_app', '删除飞书应用密钥'],
] as const)('does not delete the %s credential until destructive confirmation is accepted', async (provider, buttonLabel) => {
  const state = {
    mode: 'fake', model_studio_account_id: 'synthetic-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'synthetic-account', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.invalid/api/v1', enabled: false },
    credential_status: { feishu_app: true, deepseek: true, dashscope: true },
    capabilities: {}, keychain_available: false,
  }
  const fetchMock = vi.fn(async (_url: unknown, _init?: RequestInit) => ({ ok: true, status: 200, json: async () => state }))
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.click(await screen.findByText(/高级与自定义/))
  fireEvent.click(await screen.findByRole('button', { name: buttonLabel }))
  const dialog = await screen.findByRole('dialog', { name: '删除所选本机密钥？' })
  expect(document.activeElement).toBe(within(dialog).getByRole('button', { name: '取消' }))
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  fireEvent.click(within(dialog).getByRole('button', { name: '取消' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: buttonLabel }))
  fireEvent.click(await screen.findByRole('button', { name: '删除密钥' }))
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(1))
  expect(fetchMock.mock.calls.some(([url]) => String(url) === `/api/v1/credentials/${provider}`)).toBe(true)
})
