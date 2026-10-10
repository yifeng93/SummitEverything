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
