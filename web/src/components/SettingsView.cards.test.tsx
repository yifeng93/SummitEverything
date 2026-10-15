import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { components } from '../api/generated'
import { feishuCardBadge, modelCardBadge, parseFeishuStatus } from './settingsBadges'
import { SettingsView } from './SettingsView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

type CapabilityState = components['schemas']['CapabilityState']

function capability(overrides: Partial<CapabilityState> = {}): CapabilityState {
  return { available: false, configured: false, disabled_reason: null, ...overrides }
}

function settings(overrides: Record<string, unknown> = {}) {
  return {
    mode: 'fake',
    model_studio_account_id: 'studio-default',
    feishu: { app_id: '', redirect_uri: '' },
    llm: { provider: 'fake', model: null, account_id: 'default', enabled: false, max_output_tokens: 2048, reasoning_effort: 'low' },
    embedding: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.aliyuncs.com/compatible-mode/v1', enabled: false },
    rerank: { provider: 'fake', model: null, region: 'cn', dimensions: 1024, base_url: 'https://example.aliyuncs.com/api/v1', enabled: false },
    capabilities: {},
    credential_status: { feishu_app: false, deepseek: false, dashscope: false },
    keychain_available: true,
    embedding_fingerprint: 'fingerprint',
    ...overrides,
  }
}

const smokeStatus = {
  counts: { deepseek_chat: 0, model_studio_embedding: 0, model_studio_rerank: 0 },
  limits: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 },
  remaining: { deepseek_chat: 1, model_studio_embedding: 1, model_studio_rerank: 1 },
}

/** `GET /integrations/feishu/status` 是本地只读信号，只报告本机凭据状态。 */
function feishuStatus(overrides: Record<string, unknown> = {}) {
  return {
    mode: 'real', authorized: false, app_configured: false, identity: 'app',
    token_type: 'user', scopes: [], user_identity_verified: false, credential_error: null,
    ...overrides,
  }
}

type FeishuStub = { value?: unknown; failure?: 'reject' | 'http' }

function stubSettings(overrides: Record<string, unknown> = {}, feishu: FeishuStub = {}) {
  const saved = settings(overrides)
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/integrations/feishu/status')) {
      if (feishu.failure === 'reject') throw new Error('status unavailable')
      if (feishu.failure === 'http') {
        return { ok: false, status: 503, json: async () => ({ error: { code: 'unavailable', message: '暂时不可用' } }) }
      }
      return { ok: true, status: 200, json: async () => (feishu.value ?? feishuStatus()) }
    }
    if (url.endsWith('/provider-smoke') && (!init?.method || init.method === 'GET')) {
      return { ok: true, status: 200, json: async () => smokeStatus }
    }
    if (url.endsWith('/settings') && (!init?.method || init.method === 'GET')) {
      return { ok: true, status: 200, json: async () => saved }
    }
    if (url.endsWith('/settings') && init?.method === 'PATCH') {
      Object.assign(saved, JSON.parse(String(init.body)))
      return { ok: true, status: 200, json: async () => saved }
    }
    if (url.includes('/credentials/') && init?.method === 'PUT') {
      const provider = url.split('/').at(-1) as string
      ;(saved.credential_status as Record<string, boolean>)[provider] = true
      return { ok: true, status: 200, json: async () => ({ provider, configured: true }) }
    }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { saved, fetchMock }
}

function smokePosts(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.filter(([url, init]) => (
    String(url).includes('/provider-smoke/') && init?.method === 'POST'
  ))
}

async function waitForSettings() {
  await screen.findByRole('button', { name: '配置 AI 模型与密钥' })
}

it('renders the three main cards and keeps technical fields inside the collapsed advanced block', async () => {
  stubSettings()
  const { container } = render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()

  const workspaceCard = await screen.findByRole('region', { name: '工作库' })
  const modelCard = screen.getByRole('region', { name: 'AI 模型' })
  const feishuCard = screen.getByRole('region', { name: '飞书' })
  expect(await within(workspaceCard).findByText('Synthetic')).toBeTruthy()
  expect(within(feishuCard).getByRole('button', { name: '连接 / 重新授权飞书' })).toBeTruthy()
  expect(within(feishuCard).queryByLabelText('飞书应用 App ID')).toBeNull()
  expect(within(feishuCard).queryByRole('button', { name: '重新读取授权状态' })).toBeNull()
  expect(within(modelCard).getByText('整理与问答模型')).toBeTruthy()
  expect(within(modelCard).getByText('知识索引向量化')).toBeTruthy()
  expect(within(modelCard).getByRole('button', { name: '配置 AI 模型与密钥' })).toBeTruthy()
  expect(within(modelCard).queryByLabelText(/DeepSeek API Key/)).toBeNull()

  // 技术字段全部在默认收起的「高级与自定义」里，主区不再有全局 Provider 下拉框 + 密钥表单。
  const advanced = container.querySelector('details.settings-advanced-block') as HTMLDetailsElement
  expect(advanced).toBeTruthy()
  expect(advanced.open).toBe(false)
  expect(within(advanced).getByLabelText(/DeepSeek API Key/)).toBeTruthy()
  expect(within(advanced).getByLabelText(/阿里云 Model Studio API Key/)).toBeTruthy()
  expect(within(advanced).getByLabelText('飞书应用 App ID')).toBeTruthy()
  expect(within(advanced).getByRole('button', { name: '重新读取授权状态' })).toBeTruthy()
  expect(within(advanced).getByLabelText('Embedding Base URL')).toBeTruthy()
  expect(within(advanced).getByLabelText('Rerank API Base URL')).toBeTruthy()
  expect(within(advanced).getByLabelText('Model Studio 账户标识')).toBeTruthy()
  expect(within(advanced).getByLabelText('DeepSeek 账户标识')).toBeTruthy()
  expect(within(advanced).getByLabelText('回答长度上限（生成 token）')).toBeTruthy()
  expect(within(advanced).getByLabelText('回答推理预算')).toBeTruthy()
  expect(within(advanced).getByText('中国大陆（当前已核对 endpoint）')).toBeTruthy()
  expect(within(advanced).getByRole('table')).toBeTruthy()
  expect(within(advanced).getByText('Embedding 指纹')).toBeTruthy()
  expect(screen.queryByLabelText('Provider')).toBeNull()
  expect(Array.from(container.querySelectorAll('.settings-cards > .settings-card')).map((card) => card.getAttribute('aria-label')))
    .toEqual(['工作库', 'AI 模型', '飞书'])
})

it('keeps internal identifiers, hashes, paths, and raw JSON out of the three visible settings cards', async () => {
  stubSettings({
    embedding_fingerprint: 'synthetic-internal-hash',
    model_studio_account_id: 'synthetic-internal-account',
  })
  const { container } = render(<SettingsView workspaceName="模拟工作库" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  const visibleCards = container.querySelector('.settings-cards')?.textContent ?? ''
  expect(visibleCards).not.toContain('synthetic-internal-hash')
  expect(visibleCards).not.toContain('synthetic-internal-account')
  expect(visibleCards).not.toContain('/tmp/')
  expect(visibleCards).not.toContain('{')
})

it('shows settings read failure as an error state with per-card fallbacks and retry', async () => {
  let settingsReads = 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/settings')) {
      settingsReads += 1
      throw new Error('synthetic read failure')
    }
    if (url.endsWith('/provider-smoke')) return { ok: true, status: 200, json: async () => smokeStatus }
    if (url.endsWith('/integrations/feishu/status')) return { ok: true, status: 200, json: async () => feishuStatus() }
    throw new Error(`Unexpected request ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<SettingsView workspaceName="模拟工作库" onSwitchWorkspace={vi.fn()} />)
  expect((await screen.findByRole('alert')).textContent).toContain('synthetic read failure')
  const cards = screen.getByLabelText('设置读取状态')
  expect(within(cards).getAllByText('暂时无法读取')).toHaveLength(3)
  expect(within(cards).queryByText('已连接')).toBeNull()
  const retries = screen.getAllByRole('button', { name: '重新读取本机设置' })
  expect(retries).toHaveLength(3)
  fireEvent.click(retries[0])
  await waitFor(() => expect(settingsReads).toBeGreaterThan(1))
})

it('maps the four backend capability codes to business language with a next action', async () => {
  stubSettings({
    mode: 'real',
    capabilities: {
      llm: capability({ configured: true, disabled_reason: 'acceptance_plan_required' }),
      embedding: capability({ disabled_reason: 'offline_default' }),
      rerank: capability({ disabled_reason: 'provider_not_configured' }),
      feishu_task_write: capability({ configured: true, disabled_reason: 'result_proof_unavailable' }),
    },
  })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  expect(await screen.findByText(/每次使用前需预览并确认本次范围/)).toBeTruthy()
  expect(screen.getByText(/下一步：在对应操作中先查看本次范围预览/)).toBeTruthy()
  expect(screen.getByText(/当前使用离线 Fake；此路径不会访问真实 provider/)).toBeTruthy()
  expect(screen.getByText(/已选 provider；真实模式与本机密钥尚未完成配置/)).toBeTruthy()
  expect(screen.getByText(/缺少可独立核实写入结果的方式，飞书任务写回保持关闭/)).toBeTruthy()
  expect(screen.getByText(/下一步：写回继续禁用/)).toBeTruthy()
  expect(screen.getByText('已配置，待本次确认')).toBeTruthy()
})

it('falls back to a next-action message for an unknown capability code', async () => {
  stubSettings({ capabilities: { llm: capability({ disabled_reason: 'some_future_code' }) } })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  expect(await screen.findByText(/需要单独验证/)).toBeTruthy()
  expect(screen.getByText(/下一步：先查看能力详情确认门禁原因/)).toBeTruthy()
})

it('maps AI model card badges for unconfigured, configured, verified and failed states', () => {
  const empty = { mode: 'fake' as const, credentials: {}, capabilities: {}, lastCheck: 'none' as const }
  expect(modelCardBadge(empty).kind).toBe('unconfigured')

  const configured = modelCardBadge({
    mode: 'real',
    credentials: { deepseek: true },
    capabilities: { llm: capability({ configured: true, disabled_reason: 'acceptance_plan_required' }) },
    lastCheck: 'none',
  })
  expect(configured.kind).toBe('configured')
  expect(configured.label).toBe('已配置（尚未验证）')

  expect(modelCardBadge({
    mode: 'real', credentials: { deepseek: true }, capabilities: {}, lastCheck: 'succeeded',
  }).kind).toBe('verified')

  expect(modelCardBadge({
    mode: 'real', credentials: { deepseek: true }, capabilities: {}, lastCheck: 'failed',
  }).kind).toBe('failed')
})

it('maps the feishu card badge from the local status payload', () => {
  // 已授权：不声称身份已验证，且写明每次读取仍需预览确认。
  const authorized = feishuCardBadge({
    keychainAvailable: true,
    read: { state: 'loaded', status: feishuStatus({ authorized: true, app_configured: true }) },
  })
  expect(authorized.kind).toBe('authorized')
  expect(authorized.label).toBe('已授权')
  expect(authorized.hint).toContain('读取仍需在每次操作前预览并独立确认范围')
  expect(authorized.hint).toContain('不表示身份已核实')

  // 已配置应用密钥但还没有用户授权。
  const appOnly = feishuCardBadge({
    keychainAvailable: true,
    read: { state: 'loaded', status: feishuStatus({ authorized: false, app_configured: true }) },
  })
  expect(appOnly.kind).toBe('configured')
  expect(appOnly.label).toBe('已配置，尚未授权')

  // 只有凭据存在但读不出来才可以说「需重新授权」。
  const unreadableCredential = feishuCardBadge({
    keychainAvailable: true,
    read: { state: 'loaded', status: feishuStatus({ app_configured: true, credential_error: 'credential_unreadable' }) },
  })
  expect(unreadableCredential.kind).toBe('reauth')
  expect(unreadableCredential.label).toBe('需重新授权')

  // 离线模式与完全未配置。
  const offline = feishuCardBadge({
    keychainAvailable: true,
    read: { state: 'loaded', status: feishuStatus({ mode: 'fake' }) },
  })
  expect(offline.kind).toBe('unconfigured')
  expect(offline.hint).toContain('离线模式')

  const nothing = feishuCardBadge({
    keychainAvailable: true,
    read: { state: 'loaded', status: feishuStatus() },
  })
  expect(nothing.kind).toBe('unconfigured')

  // 状态读取失败：不默认成已授权。
  const failedRead = feishuCardBadge({ keychainAvailable: true, read: { state: 'unreadable' } })
  expect(failedRead.kind).toBe('unreadable')
  expect(failedRead.label).toBe('授权状态暂时无法读取')

  // 钥匙串不可用时不得把读不到的凭据说成「需重新授权」。
  const noKeychain = feishuCardBadge({
    keychainAvailable: false,
    read: { state: 'loaded', status: feishuStatus({ app_configured: true, credential_error: 'credential_unreadable' }) },
  })
  expect(noKeychain.kind).toBe('unreadable')
  expect(noKeychain.label).toBe('钥匙串不可用')
  expect(noKeychain.label).not.toBe('需重新授权')

  // 受损/未知响应不当作已授权。
  expect(parseFeishuStatus({ mode: 'real' })).toBeNull()
  expect(parseFeishuStatus(null)).toBeNull()
  expect(parseFeishuStatus({ mode: 'real', authorized: true, app_configured: true })?.authorized).toBe(true)
})

it('shows the authorized feishu badge without claiming identity verification or task write-back', async () => {
  const { fetchMock } = stubSettings({}, { value: feishuStatus({ authorized: true, app_configured: true }) })
  const { container } = render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  const feishuCard = await screen.findByRole('region', { name: '飞书' })
  expect(await within(feishuCard).findByText('已授权')).toBeTruthy()
  expect(feishuCard.textContent).toContain('不表示身份已核实')
  expect(feishuCard.textContent).toContain('飞书任务写回仍不可用')
  expect(feishuCard.textContent ?? '').not.toMatch(/可以(写回|修改)/)
  // 读取授权状态本身不联网、不发连接检查、也不占额度。
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/integrations/feishu/status'))).toHaveLength(1)
  expect(smokePosts(fetchMock)).toHaveLength(0)
  const advanced = container.querySelector('details.settings-advanced-block') as HTMLDetailsElement
  for (const cell of Array.from(advanced.querySelectorAll('.smoke-quota tbody tr td:nth-child(2)'))) {
    expect(cell.textContent).toBe('0')
  }
})

it('shows "需重新授权" only for an unreadable credential', async () => {
  stubSettings({}, { value: feishuStatus({ mode: 'real', app_configured: true, credential_error: 'credential_unreadable' }) })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  const feishuCard = await screen.findByRole('region', { name: '飞书' })
  expect(await within(feishuCard).findByText('需重新授权')).toBeTruthy()
})

it('shows an unreadable authorization status when the status request fails, without consuming smoke quota', async () => {
  const { fetchMock } = stubSettings({}, { failure: 'http' })
  const { container } = render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  const feishuCard = await screen.findByRole('region', { name: '飞书' })
  expect(await within(feishuCard).findByText('授权状态暂时无法读取')).toBeTruthy()
  // 徽章本身不得落在「已授权」状态。
  const badge = feishuCard.querySelector('.conn-badge')
  expect(badge?.textContent).toBe('授权状态暂时无法读取')
  expect(badge?.className).not.toContain('ok')

  // 状态读取不算连接检查：没有 smoke POST，额度保持 0/1。
  expect(smokePosts(fetchMock)).toHaveLength(0)
  const advanced = container.querySelector('details.settings-advanced-block') as HTMLDetailsElement
  const used = Array.from(advanced.querySelectorAll('.smoke-quota tbody tr td:nth-child(2)'))
  expect(used).toHaveLength(3)
  for (const cell of used) expect(cell.textContent).toBe('0')
})

it('treats a rejected status request the same way and keeps the reload affordance', async () => {
  const { fetchMock } = stubSettings({}, { failure: 'reject' })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  const feishuCard = await screen.findByRole('region', { name: '飞书' })
  expect(await within(feishuCard).findByText('授权状态暂时无法读取')).toBeTruthy()
  const statusCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/integrations/feishu/status'))
  expect(statusCalls.length).toBeGreaterThanOrEqual(1)
  fireEvent.click(document.querySelector('.settings-advanced-block > summary')!)
  fireEvent.click(screen.getByRole('button', { name: '重新读取授权状态' }))
  await waitFor(() => {
    const after = fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/integrations/feishu/status'))
    expect(after.length).toBeGreaterThan(statusCalls.length)
  })
  expect(smokePosts(fetchMock)).toHaveLength(0)
})

it('does not start any provider check after saving a secret', async () => {
  const setItem = vi.spyOn(Storage.prototype, 'setItem')
  const { saved, fetchMock } = stubSettings({
    mode: 'real',
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'team-account', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
    capabilities: { llm: capability({ configured: false, disabled_reason: 'provider_not_configured' }) },
  })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  fireEvent.click(await screen.findByRole('button', { name: '配置 AI 模型与密钥' }))
  const password = await screen.findByLabelText(/DeepSeek API Key/) as HTMLInputElement
  fireEvent.change(password, { target: { value: 'synthetic-secret' } })
  fireEvent.click(screen.getByRole('button', { name: '保存 AI 模型设置' }))

  await waitFor(() => expect(saved.credential_status.deepseek).toBe(true))
  expect(password.value).toBe('')
  expect(smokePosts(fetchMock)).toHaveLength(0)
  // 提交成功后密钥立即清空，且没有进入任何浏览器持久存储。
  expect(setItem).not.toHaveBeenCalled()
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
  expect(JSON.stringify(localStorage)).not.toContain('synthetic-secret')
})

it('keeps the confirmation dialog open until the user confirms or cancels', async () => {
  const { fetchMock } = stubSettings({
    mode: 'real',
    llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'default', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
    credential_status: { feishu_app: false, deepseek: true, dashscope: false },
    capabilities: {},
  })
  render(<SettingsView workspaceName="Synthetic" onSwitchWorkspace={vi.fn()} />)
  await waitForSettings()
  fireEvent.click(document.querySelector('.settings-advanced-block > summary')!)
  const button = await screen.findByRole('button', { name: 'DeepSeek Chat（剩余 1）' })
  fireEvent.click(button)
  const dialog = await screen.findByRole('dialog', { name: /确认本次连接检查/ })
  expect(dialog.textContent).toContain('不会发送工作库材料')
  expect(dialog.textContent).toContain('累计已用 0/1')
  expect(dialog.textContent).toContain('跨运行不重置')
  expect(dialog.textContent).toContain('不会自动重发')
  // 未确认前不发出任何检查请求。
  expect(smokePosts(fetchMock)).toHaveLength(0)
  fireEvent.click(within(dialog).getByRole('button', { name: '取消' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  expect(smokePosts(fetchMock)).toHaveLength(0)
})
