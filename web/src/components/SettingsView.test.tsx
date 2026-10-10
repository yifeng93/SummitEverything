import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function settings(credentialStatus = { feishu_app: false, deepseek: false, dashscope: false }) {
  return {
    mode: 'fake',
    model_studio_account_id: 'studio-default',
    feishu: { app_id: 'synthetic-app', redirect_uri: '' },
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'team-account', enabled: false },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, enabled: false },
    capabilities: {
      llm: { available: false, configured: false, disabled_reason: 'adapter_not_wired' },
    },
    credential_status: credentialStatus,
    keychain_available: true,
    embedding_fingerprint: 'fingerprint',
  }
}

it('sends the selected account id with the secret and clears the password field', async () => {
  const saved = settings()
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/settings') && (!init?.method || init.method === 'GET')) {
      return { ok: true, status: 200, json: async () => saved }
    }
    if (url.endsWith('/settings') && init?.method === 'PATCH') {
      Object.assign(saved.llm, JSON.parse(String(init.body)).llm)
      return { ok: true, status: 200, json: async () => saved }
    }
    if (url.endsWith('/credentials/deepseek') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      expect(body.account_id).toBe('team-account')
      expect(body.secret).toBe('synthetic-secret')
      saved.credential_status.deepseek = true
      return { ok: true, status: 200, json: async () => ({ provider: 'deepseek', configured: true }) }
    }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  const password = await screen.findByLabelText('密钥') as HTMLInputElement
  fireEvent.change(password, { target: { value: 'synthetic-secret' } })
  fireEvent.click(screen.getByRole('button', { name: '保存到钥匙串' }))

  await waitFor(() => expect(password.value).toBe(''))
  expect(await screen.findByText('密钥已保存到本机钥匙串。页面不会再次显示密钥。')).toBeTruthy()
})
