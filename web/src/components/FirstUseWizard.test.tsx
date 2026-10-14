import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { FirstUseWizard } from './FirstUseWizard'
import { parseFeishuStatus, type FeishuStatusRead, type Settings, type SmokeStatus } from './settingsBadges'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const smokeStatus: SmokeStatus = {
  counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 },
  limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 },
  remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 },
}

function fixture(overrides: Record<string, unknown> = {}): Settings {
  return {
    mode: 'fake',
    model_studio_account_id: 'stale-studio',
    feishu: { app_id: '', redirect_uri: '', identity: 'app', calendar_id: '', material_content: 'transcript', real_data_enabled: false },
    llm: { provider: 'fake', model: null, account_id: 'stale-account', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://ws-demo.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://ws-demo.cn-beijing.maas.aliyuncs.com/api/v1', enabled: false },
    capabilities: {},
    credential_status: { feishu_app: false, deepseek: false, dashscope: false },
    keychain_available: true,
    embedding_fingerprint: 'fingerprint',
    ...overrides,
  } as unknown as Settings
}

const loadedFeishu: FeishuStatusRead = {
  state: 'loaded',
  status: { mode: 'real', authorized: false, app_configured: false, credential_error: null, user_identity_verified: false },
}

type WizardHarness = {
  state: Settings
  fetchMock: ReturnType<typeof vi.fn>
  onClose: ReturnType<typeof vi.fn>
  onOpenFeishuDaily: ReturnType<typeof vi.fn>
  onSmokeStatusRefresh: ReturnType<typeof vi.fn>
  onFeishuStatusRefresh: ReturnType<typeof vi.fn>
}

/** 与 SettingsView 一样由父级持有 settings 状态；保存后用服务端返回的响应覆盖。 */
function Harness({ initial, feishuStatus, onClose, onOpenFeishuDaily, onSmokeStatusRefresh, onFeishuStatusRefresh }: {
  initial: Settings
  feishuStatus: FeishuStatusRead
  onClose: () => void
  onOpenFeishuDaily?: () => void
  onSmokeStatusRefresh: () => void
  onFeishuStatusRefresh: () => void
}) {
  const [settings, setSettings] = useState(initial)
  return <FirstUseWizard
    settings={settings}
    smokeStatus={smokeStatus}
    feishuStatus={feishuStatus}
    onClose={onClose}
    onSettingsChanged={setSettings}
    onSmokeStatusRefresh={onSmokeStatusRefresh}
    onFeishuStatusRefresh={onFeishuStatusRefresh}
    onOpenFeishuDaily={onOpenFeishuDaily}
  />
}

function stubBackend(initial: Settings) {
  const state = initial
  const calls: { method: string; url: string; body: Record<string, unknown> | null }[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : null
    calls.push({ method, url, body })
    if (method === 'PATCH' && url.endsWith('/settings')) {
      for (const [key, value] of Object.entries(body ?? {})) {
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          Object.assign((state as unknown as Record<string, Record<string, unknown>>)[key], value)
        } else {
          (state as unknown as Record<string, unknown>)[key] = value
        }
      }
      // 模拟服务端/注入默认值补全账户标识：界面必须用落盘后的值，而不是自己表单里的旧值。
      const patch = (body ?? {}) as { llm?: { account_id?: unknown }, model_studio_account_id?: unknown }
      if (patch.llm && patch.llm.account_id === undefined) state.llm.account_id = 'server-assigned-account'
      if (patch.model_studio_account_id === undefined) state.model_studio_account_id = 'server-assigned-studio'
      return { ok: true, status: 200, json: async () => state }
    }
    if (method === 'PUT' && url.includes('/credentials/')) {
      const provider = url.split('/').at(-1) as string
      ;(state.credential_status as Record<string, boolean>)[provider] = true
      return { ok: true, status: 200, json: async () => ({ provider, configured: true }) }
    }
    if (method === 'POST' && url.includes('/provider-smoke/')) {
      return { ok: true, status: 200, json: async () => ({ state: 'succeeded' }) }
    }
    throw new Error(`Unexpected request ${method} ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { state, calls, fetchMock }
}

function renderWizard(initial: Settings, feishuStatus: FeishuStatusRead = loadedFeishu) {
  const backend = stubBackend(initial)
  const onClose = vi.fn()
  const onOpenFeishuDaily = vi.fn()
  const onSmokeStatusRefresh = vi.fn()
  const onFeishuStatusRefresh = vi.fn()
  const view = render(<Harness
    initial={initial}
    feishuStatus={feishuStatus}
    onClose={onClose}
    onOpenFeishuDaily={onOpenFeishuDaily}
    onSmokeStatusRefresh={onSmokeStatusRefresh}
    onFeishuStatusRefresh={onFeishuStatusRefresh}
  />)
  const harness: WizardHarness = { state: backend.state, fetchMock: backend.fetchMock, onClose, onOpenFeishuDaily, onSmokeStatusRefresh, onFeishuStatusRefresh }
  return { ...harness, calls: backend.calls, view }
}

function smokePosts(calls: { method: string; url: string }[]) {
  return calls.filter((call) => call.method === 'POST' && call.url.includes('/provider-smoke/'))
}

function settingsStub(overrides: Record<string, unknown> = {}) {
  const saved = fixture(overrides)
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/integrations/feishu/status')) {
      return { ok: true, status: 200, json: async () => ({ mode: 'fake', authorized: false, app_configured: false, credential_error: null, user_identity_verified: false }) }
    }
    if (url.endsWith('/provider-smoke')) return { ok: true, status: 200, json: async () => smokeStatus }
    if (url.endsWith('/settings')) return { ok: true, status: 200, json: async () => saved }
    void init
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { saved, fetchMock }
}

// --- 入口与自动打开 ---------------------------------------------------------

it('opens automatically once for an unconfigured profile and stops after the user closes it', async () => {
  settingsStub()
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  const wizard = await screen.findByRole('dialog', { name: '首次配置向导' })
  expect(within(wizard).getByText(/第 1 步/)).toBeTruthy()
  fireEvent.click(within(wizard).getByRole('button', { name: '关闭向导' }))
  await waitFor(() => expect(screen.queryByRole('dialog', { name: '首次配置向导' })).toBeNull())
  // 关闭后本次挂载不再自动打开。
  fireEvent.click(screen.getByRole('button', { name: '重新读取授权状态' }))
  await waitFor(() => expect(screen.getByRole('region', { name: 'AI 模型' })).toBeTruthy())
  expect(screen.queryByRole('dialog', { name: '首次配置向导' })).toBeNull()
})

it('does not open automatically when a credential is already configured, and reopens manually', async () => {
  settingsStub({ credential_status: { feishu_app: false, deepseek: true, dashscope: false } })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await screen.findByRole('region', { name: '工作库' })
  expect(screen.queryByRole('dialog', { name: '首次配置向导' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '重新打开连接向导' }))
  expect(await screen.findByRole('dialog', { name: '首次配置向导' })).toBeTruthy()
})

// --- 步骤导航 ---------------------------------------------------------------

it('moves forward, backward and skips steps without any request', async () => {
  const { fetchMock } = renderWizard(fixture())
  expect(screen.getByRole('heading', { name: /第 1 步 · 模型与接入地址/ })).toBeTruthy()
  expect(document.querySelector('[aria-current="step"]')?.textContent).toContain('模型与接入地址')

  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  expect(screen.getByRole('heading', { name: /第 2 步 · 录入密钥/ })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '上一步' }))
  expect(screen.getByRole('heading', { name: /第 1 步 · 模型与接入地址/ })).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  expect(screen.getByRole('heading', { name: /第 2 步 · 录入密钥/ })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  expect(screen.getByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeTruthy()
  expect(document.querySelector('[aria-current="step"]')?.textContent).toContain('检查连接')

  // 打开、切步骤都不产生任何请求（包括 provider 请求）。
  expect(fetchMock).not.toHaveBeenCalled()
})

it('shows built-in read-only addresses on step 1', () => {
  renderWizard(fixture())
  expect(screen.getByText('整理与问答')).toBeTruthy()
  expect(screen.getByText('知识索引向量化（embedding）')).toBeTruthy()
  expect(screen.getByText('检索结果排序（rerank）')).toBeTruthy()
  expect(screen.getByText('https://api.deepseek.com/chat/completions')).toBeTruthy()
  expect(screen.getByText('https://ws-demo.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')).toBeTruthy()
  expect(screen.getAllByText('已内置，无需填写')).toHaveLength(3)
  // 地址只读：页面上没有可编辑的 Base URL 输入。
  expect(screen.queryByLabelText(/Base URL/)).toBeNull()
})

// --- 第 2 步：密钥 ----------------------------------------------------------

it('saves settings before credentials, uses the persisted account ids, and clears the secret fields', async () => {
  const setItem = vi.spyOn(Storage.prototype, 'setItem')
  const { calls, state } = renderWizard(fixture())
  // 取消勾选整理能力，验证第 1 步的勾选会影响落盘配置。
  fireEvent.click(screen.getByRole('checkbox', { name: /整理与问答/ }))
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))

  fireEvent.change(screen.getByLabelText(/DeepSeek API Key/), { target: { value: 'synthetic-deepseek' } })
  fireEvent.change(screen.getByLabelText(/阿里云 Model Studio API Key/), { target: { value: 'synthetic-dashscope' } })
  fireEvent.click(screen.getByRole('button', { name: '保存密钥并继续' }))

  await waitFor(() => expect(state.credential_status.deepseek).toBe(true))
  expect(state.credential_status.dashscope).toBe(true)
  const patched = calls.find((call) => call.method === 'PATCH')
  expect(patched?.body).toMatchObject({ mode: 'real', llm: { provider: 'fake', model: null, enabled: false } })
  expect(patched?.body).toMatchObject({ embedding: { provider: 'dashscope', enabled: true }, rerank: { provider: 'dashscope', enabled: true } })

  const puts = calls.filter((call) => call.method === 'PUT')
  expect(puts.map((call) => call.body?.account_id)).toEqual(['server-assigned-account', 'server-assigned-studio'])
  expect(puts.map((call) => call.body?.secret)).toEqual(['synthetic-deepseek', 'synthetic-dashscope'])
  const methods = calls.map((call) => call.method)
  expect(methods.indexOf('PATCH')).toBeLessThan(methods.indexOf('PUT'))

  // 保存本身不联网检查。
  expect(smokePosts(calls)).toHaveLength(0)
  // 保存成功后前进到检查连接步骤，且页面上不再出现任何密钥值。
  expect(screen.getByRole('heading', { name: /第 3 步 · 检查连接/ })).toBeTruthy()
  expect(document.body.textContent ?? '').not.toContain('synthetic-deepseek')
  expect(document.body.textContent ?? '').not.toContain('synthetic-dashscope')
  // 回到第 2 步可见输入框已被清空（组件内存里也没有保留明文）。
  fireEvent.click(screen.getByRole('button', { name: '上一步' }))
  expect((screen.getByLabelText(/DeepSeek API Key/) as HTMLInputElement).value).toBe('')
  expect((screen.getByLabelText(/阿里云 Model Studio API Key/) as HTMLInputElement).value).toBe('')
  expect(setItem).not.toHaveBeenCalled()
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})

it('does not save anything when the key fields are left empty', () => {
  const { fetchMock } = renderWizard(fixture())
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  fireEvent.click(screen.getByRole('button', { name: '保存密钥并继续' }))
  expect(screen.getByRole('status').textContent).toContain('没有填入密钥')
  expect(fetchMock).not.toHaveBeenCalled()
  expect(screen.getByRole('heading', { name: /第 2 步 · 录入密钥/ })).toBeTruthy()
})

it('blocks step 2 entirely when the keychain is unavailable', () => {
  const { state, fetchMock } = renderWizard(fixture({ keychain_available: false }))
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  fireEvent.change(screen.getByLabelText(/DeepSeek API Key/), { target: { value: 'synthetic-deepseek' } })
  fireEvent.click(screen.getByRole('button', { name: '保存密钥并继续' }))

  expect(screen.getByRole('alert').textContent).toContain('钥匙串')
  expect(state.mode).toBe('fake')
  expect(state.credential_status.deepseek).toBe(false)
  expect(fetchMock).not.toHaveBeenCalled()
  expect(screen.getByRole('heading', { name: /第 2 步 · 录入密钥/ })).toBeTruthy()
})

// --- 第 3 步：连接检查 ------------------------------------------------------

function realFixture() {
  return fixture({
    mode: 'real',
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'default', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
    embedding: { provider: 'dashscope', model: 'qwen3.7-text-embedding', region: 'cn', dimensions: 1024, base_url: 'https://ws-demo.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', enabled: true },
    rerank: { provider: 'dashscope', model: 'qwen3.7-text-rerank', region: 'cn', dimensions: 1024, base_url: 'https://ws-demo.cn-beijing.maas.aliyuncs.com/api/v1', enabled: true },
    credential_status: { feishu_app: false, deepseek: true, dashscope: true },
  })
}

async function goToStep3() {
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 3 步 · 检查连接/ })
}

it('requires an explicit confirmation before the connection check, and cancel sends nothing', async () => {
  const { calls } = renderWizard(realFixture())
  await goToStep3()
  const button = screen.getByRole('button', { name: '检查 DeepSeek Chat（剩余 1）' })
  expect((button as HTMLButtonElement).disabled).toBe(false)

  fireEvent.click(button)
  const dialog = await screen.findByRole('dialog', { name: '确认本次连接检查' })
  expect(dialog.textContent).toContain('不发送工作库材料')
  expect(dialog.textContent).toContain('累计已用 0/1')
  expect(dialog.textContent).toContain('跨运行不重置')
  expect(dialog.textContent).toContain('不会自动重发')
  expect(smokePosts(calls)).toHaveLength(0)

  fireEvent.click(within(dialog).getByRole('button', { name: '取消' }))
  await waitFor(() => expect(screen.queryByRole('dialog', { name: '确认本次连接检查' })).toBeNull())
  expect(smokePosts(calls)).toHaveLength(0)
})

it('sends exactly the confirmed check and nothing when the step is skipped', async () => {
  const { calls } = renderWizard(realFixture())
  await goToStep3()
  fireEvent.click(screen.getByRole('button', { name: '检查 Embedding（剩余 1）' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认发送本次检查' }))
  await waitFor(() => expect(smokePosts(calls)).toHaveLength(1))
  expect(smokePosts(calls)[0].url).toContain('/provider-smoke/model-studio-embedding')

  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 4 步 · 飞书/ })
  expect(smokePosts(calls)).toHaveLength(1)
})

// --- 第 4 步：飞书 ----------------------------------------------------------

it('saves the feishu app secret, clears it, and never starts OAuth on its own', async () => {
  const { calls } = renderWizard(fixture({ feishu: { app_id: 'cli_injected', redirect_uri: 'http://127.0.0.1:18793/api/v1/integrations/feishu/callback' } }), {
    state: 'loaded',
    status: { mode: 'real', authorized: false, app_configured: true, credential_error: null, user_identity_verified: false },
  })
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 4 步 · 飞书/ })

  // App ID 预填自注入的非秘密默认值，且授权状态复用同一状态机。
  expect((screen.getByLabelText('飞书应用 App ID') as HTMLInputElement).value).toBe('cli_injected')
  expect(screen.getByText(/当前授权状态：已配置，尚未授权/)).toBeTruthy()

  fireEvent.change(screen.getByLabelText(/飞书应用密钥/), { target: { value: 'synthetic-app-secret' } })
  fireEvent.click(screen.getByRole('button', { name: '保存飞书设置并继续' }))

  await waitFor(() => expect(calls.some((call) => call.method === 'PUT' && call.url.endsWith('/credentials/feishu_app'))).toBe(true))
  const put = calls.find((call) => call.method === 'PUT')
  expect(put?.body?.secret).toBe('synthetic-app-secret')
  expect(document.body.textContent ?? '').not.toContain('synthetic-app-secret')
  // 向导不复制 OAuth：不会请求授权端点。
  expect(calls.filter((call) => call.url.includes('/authorizations'))).toHaveLength(0)
  expect(calls.filter((call) => call.url.includes('/integrations/feishu/') && call.method !== 'GET')).toHaveLength(0)
  // 保存后前进到完成页；回到第 4 步可见密钥输入框已清空。
  expect(screen.getByRole('heading', { name: /第 5 步 · 完成/ })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '上一步' }))
  expect((screen.getByLabelText(/飞书应用密钥/) as HTMLInputElement).value).toBe('')
})

it('routes the authorization button through the injected callback instead of doing OAuth itself', async () => {
  const { calls, onOpenFeishuDaily, onClose } = renderWizard(fixture())
  fireEvent.click(screen.getByRole('button', { name: '下一步' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 4 步 · 飞书/ })

  fireEvent.click(screen.getByRole('button', { name: '前往今日 / 飞书日常完成授权' }))
  expect(onOpenFeishuDaily).toHaveBeenCalledTimes(1)
  expect(onClose).toHaveBeenCalledTimes(1)
  expect(calls.filter((call) => call.method !== 'GET')).toHaveLength(0)
})

// --- 第 5 步：完成 ----------------------------------------------------------

it('summarizes saved and skipped items with the remaining unverified boundaries', async () => {
  const { fetchMock } = renderWizard(fixture())
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  fireEvent.click(screen.getByRole('button', { name: '稍后再说' }))
  await screen.findByRole('heading', { name: /第 5 步 · 完成/ })
  const panel = screen.getByRole('dialog', { name: '首次配置向导' })

  expect(within(panel).getByText(/本次跳过或稍后处理的步骤/)).toBeTruthy()
  expect(panel.textContent).toContain('仍未验证的边界')
  expect(panel.textContent).toContain('真实业务调用仍需在每次操作前预览并独立确认范围')
  expect(panel.textContent).toContain('飞书任务写回仍不可用')
  expect(panel.textContent).toContain('钥匙串生命周期仍未验证')
  expect(panel.textContent ?? '').not.toMatch(/可以(写回|修改)/)
  expect(panel.textContent).not.toContain('已验证通过')
  // 全部跳过时如实显示仍是离线 Fake。
  expect(panel.textContent).toContain('Fake · 离线')
  expect(fetchMock).not.toHaveBeenCalled()
})

// --- 联网边界 ---------------------------------------------------------------

it('only ever calls local settings, smoke-status and credential routes', async () => {
  const { calls } = renderWizard(realFixture())
  const allowed = [
    /^\/api\/v1\/settings$/,
    /^\/api\/v1\/provider-smoke$/,
    /^\/api\/v1\/provider-smoke\/[a-z-]+$/,
    /^\/api\/v1\/credentials\/[a-z_]+$/,
    /^\/api\/v1\/integrations\/feishu\/status$/,
  ]
  await goToStep3()
  fireEvent.click(screen.getByRole('button', { name: '检查 DeepSeek Chat（剩余 1）' }))
  fireEvent.click(await screen.findByRole('button', { name: '确认发送本次检查' }))
  await waitFor(() => expect(smokePosts(calls)).toHaveLength(1))
  for (const call of calls) {
    expect(allowed.some((pattern) => pattern.test(call.url))).toBe(true)
  }
})

it('parses the injected feishu status helper the same way the cards do', () => {
  expect(parseFeishuStatus({ mode: 'real', authorized: true, app_configured: true })?.authorized).toBe(true)
  expect(parseFeishuStatus({ mode: 'real' })).toBeNull()
})
