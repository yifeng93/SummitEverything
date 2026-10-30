import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function settings(credentialStatus = { feishu_app: false, deepseek: false, dashscope: false }, mode = 'real') {
  return {
    mode,
    model_studio_account_id: 'studio-default',
    feishu: { app_id: 'synthetic-app', redirect_uri: '' },
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'team-account', enabled: false },
    embedding: { provider: 'local', model: null, region: 'cn', dimensions: 1024, enabled: false },
    rerank: { provider: 'local', model: null, region: 'cn', dimensions: 1024, enabled: false },
    capabilities: {
      llm: { available: false, configured: mode === 'real', disabled_reason: mode === 'real' ? 'acceptance_plan_required' : 'offline_default' },
    },
    credential_status: credentialStatus,
    keychain_available: true,
    embedding_fingerprint: 'fingerprint',
  }
}

it('explains the one-time real-operation confirmation gate', async () => {
  const saved = settings(undefined, 'real')
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/settings')) return Response.json(saved)
    if (url.endsWith('/provider-smoke')) return Response.json({ counts: {}, limits: {}, remaining: {} })
    throw new Error(`Unexpected request ${url}`)
  }))

  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  expect(await screen.findByText('已配置，待本次确认')).toBeTruthy()
  expect(screen.getByText(/每次使用前需预览并确认本次范围/)).toBeTruthy()
})

it('offers ask settings (index, role, memory) on the settings page', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/settings')) return Response.json(settings())
    if (url.endsWith('/index/status')) return Response.json({ fingerprint: 'fp', pages: 3, chunks: 4, state: 'ready', current_pages: 3, stale_pages: 0 })
    if (url.endsWith('/roles') || url.endsWith('/memory') || url.endsWith('/memory/candidates')) return Response.json([])
    if (url.endsWith('/provider-smoke')) return Response.json({ counts: {}, limits: {}, remaining: {} })
    throw new Error(`Unexpected request ${url}`)
  }))

  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  const heading = await screen.findByRole('heading', { name: '知识问答' })
  const card = heading.closest('.settings-ask-card') as HTMLElement
  expect(card).toBeTruthy()
  expect(within(card).getByRole('heading', { name: '本机索引' })).toBeTruthy()
  expect(await within(card).findByText(/已索引 3 页/)).toBeTruthy()
  expect(within(card).getByRole('heading', { name: '问答角色' })).toBeTruthy()
  expect(within(card).getByRole('heading', { name: '问答记忆' })).toBeTruthy()
})

it('sends the saved account id with the secret and clears the password field', async () => {
  const saved = settings()
  const setItem = vi.spyOn(Storage.prototype, 'setItem')
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
  fireEvent.click(await screen.findByRole('button', { name: '配置 AI 模型与密钥' }))
  const password = await screen.findByLabelText(/DeepSeek API Key/) as HTMLInputElement
  fireEvent.change(password, { target: { value: 'synthetic-secret' } })
  fireEvent.click(screen.getByRole('button', { name: '保存 AI 模型设置' }))

  await waitFor(() => expect(password.value).toBe(''))
  expect(await screen.findByText(/已保存到本机钥匙串/)).toBeTruthy()
  // 密钥既不在页面上回显，也不进入任何浏览器持久存储。
  expect(document.body.textContent ?? '').not.toContain('synthetic-secret')
  expect(setItem).not.toHaveBeenCalled()
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})
