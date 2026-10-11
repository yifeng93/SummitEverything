import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

it('waits for the saved account id before storing its API key', async () => {
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
  vi.stubGlobal('fetch', vi.fn(async (_url: unknown, init?: RequestInit) => {
    if (init?.method === 'PATCH') {
      Object.assign(state, JSON.parse(String(init.body)))
    }
    if (init?.method === 'PUT') {
      accountId = JSON.parse(String(init.body)).account_id
      state.credential_status.dashscope = true
    }
    return { ok: true, status: 200, json: async () => state }
  }))
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('Model Studio 账户标识'), { target: { value: 'new-account' } })
  fireEvent.change(screen.getByLabelText('Provider'), { target: { value: 'dashscope' } })
  fireEvent.change(screen.getByLabelText('密钥'), { target: { value: 'synthetic-key' } })
  const saveKey = screen.getByRole('button', { name: '保存到钥匙串' })
  expect((saveKey as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '保存 provider 设置' }))
  await waitFor(() => expect((saveKey as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(saveKey)
  await waitFor(() => expect(accountId).toBe('new-account'))
})

it('calls only the fixed DeepSeek smoke route when one attempt remains', async () => {
  const state = {
    mode: 'real', model_studio_account_id: 'synthetic-account',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'default', enabled: true },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: false },
    credential_status: { feishu_app: false, deepseek: true, dashscope: false },
    capabilities: {}, keychain_available: true,
  }
  const smoke = { counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 }, limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 }, remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 } }
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
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/provider-smoke/deepseek-chat', expect.objectContaining({ method: 'POST' })))
})
