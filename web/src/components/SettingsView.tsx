import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { FirstUseWizard } from './FirstUseWizard'
import { FeishuAgentSetup } from './FeishuAgentSetup'
import { SmokeCheckConfirm } from './SmokeCheckConfirm'
import { ConfirmDialog } from './ConfirmDialog'
import { saveFirstUseProgress, type FirstUseProgress } from './firstUseProgress'
import {
  badgeClass, capabilityLabels, capabilityStatusLabel, checkedCapabilityStatusLabel, credentialAccountId, failedFeishuStatusRead, feishuCardBadge,
  modelCardBadge, parseFeishuStatus, reasonText, settingsPatch, smokeCheckConfigStamp, smokeCheckDisabled, smokeChecks,
  type CardBadge, type CheckOutcome, type CheckResult, type FeishuStatusRead, type SecretProvider, type Settings,
  type SmokeCheckKey, type SmokeStatus,
} from './settingsBadges'

type LLMProvider = Settings['llm']['provider']
type ModelProvider = Settings['embedding']['provider']

function CardHead({ title, badge }: { title: string; badge: CardBadge }) {
  return <div className="settings-card-head">
    <h2>{title}</h2>
    <span className={badgeClass(badge.kind)}>{badge.label}</span>
  </div>
}

const emptySecrets: Record<SecretProvider, string> = { feishu_app: '', deepseek: '', dashscope: '' }

/**
 * 没有显式注入时的默认持久化：直接写本机后端。
 * 调用方（App）通常会注入自己的实现，以便把解析出来的进度保持同步；
 * 这里的默认值仍然是真的写盘，不会静默吞掉一次「假保存」。
 */
async function persistWizardProgressDefault(progress: FirstUseProgress): Promise<boolean> {
  try {
    await saveFirstUseProgress(progress)
    return true
  } catch {
    return false
  }
}

type SettingsViewProps = {
  workspaceName: string
  workspaceId?: string
  profileId?: string
  onSwitchWorkspace: () => void
  wizardOnly?: boolean
  initialWizardStep?: 2 | 3 | 4 | 5
  /** 本机已经记住的进度：手动打开向导时从这一步续接。 */
  resumeWizardStep?: 2 | 3 | 4 | 5
  /** 本机记录说首次配置已经完成；向导关闭时要保留这个事实。 */
  initialWizardCompleted?: boolean
  /** 把向导进度写进本机后端；只有确认写入成功才允许界面前进。 */
  persistWizardProgress?: (progress: FirstUseProgress) => Promise<boolean>
  onRequestWizard?: (step: 2 | 3 | 4 | 5) => void
  onWizardStepChange?: (step: 2 | 3 | 4 | 5) => void
  onWizardClose?: () => void
  onFinishFirstUse?: () => void
  onAuthorizationChanged?: () => void
}

export function SettingsView({ workspaceName, workspaceId = workspaceName, profileId = 'default', onSwitchWorkspace, wizardOnly = false, initialWizardStep = 2, resumeWizardStep = 2, initialWizardCompleted = false, persistWizardProgress, onRequestWizard, onWizardStepChange, onWizardClose, onFinishFirstUse, onAuthorizationChanged }: SettingsViewProps) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [smokeStatus, setSmokeStatus] = useState<SmokeStatus | null>(null)
  // 密钥只允许停留在组件内存 state：不写 localStorage / sessionStorage / 工作库，
  // 提交成功后立即清空输入框，页面永不回显。
  const [secrets, setSecrets] = useState<Record<SecretProvider, string>>(emptySecrets)
  // 每项结果只对产生它的本机配置有效；配置变更后由指纹失配自动过期。
  const [checkResults, setCheckResults] = useState<CheckResult>({})
  // 读取失败可保留最后一次成功只读状态，但必须显著标记为可能过时。
  const [feishuStatus, setFeishuStatus] = useState<FeishuStatusRead>({ state: 'loading' })
  const feishuStatusRef = useRef<FeishuStatusRead>({ state: 'loading' })
  const [pendingCheck, setPendingCheck] = useState<SmokeCheckKey | null>(null)
  const [pendingRemoval, setPendingRemoval] = useState<SecretProvider | null>(null)
  const [settingsReadFailed, setSettingsReadFailed] = useState(false)
  const [settingsReadAt, setSettingsReadAt] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  async function load(): Promise<Settings | null> {
    try {
      const value = await api.get<Settings>('/settings')
      setSettings(value)
      setSettingsReadAt(new Date().toISOString())
      setSettingsReadFailed(false)
      setError('')
      return value
    }
    catch (cause) {
      setSettingsReadFailed(true)
      setError(cause instanceof Error ? cause.message : '无法读取本机设置')
      return null
    }
  }

  async function loadSmokeStatus() {
    try { setSmokeStatus(await api.get<SmokeStatus>('/provider-smoke')) }
    catch { setSmokeStatus(null) }
  }

  /** 本地只读授权状态：只读本机 vault，不联网，也不占用合成检查额度。 */
  async function loadFeishuStatus() {
    try {
      const parsed = parseFeishuStatus(await api.get<unknown>('/integrations/feishu/status'))
      if (parsed) {
        const previous = feishuStatusRef.current
        const next: FeishuStatusRead = { state: 'loaded', status: parsed, readAt: new Date().toISOString() }
        feishuStatusRef.current = next; setFeishuStatus(next)
        if ((previous.state === 'loaded' || previous.state === 'stale') && (previous.status.authorized !== parsed.authorized || previous.status.mode !== parsed.mode || previous.status.app_configured !== parsed.app_configured || previous.status.user_identity_verified !== parsed.user_identity_verified)) onAuthorizationChanged?.()
      }
      else setFeishuStatus((previous) => failedFeishuStatusRead(previous))
    }
    catch { setFeishuStatus((previous) => failedFeishuStatusRead(previous)) }
  }

  useEffect(() => {
    let active = true
    api.get<Settings>('/settings')
      .then((value) => {
        if (!active) return
        setSettings(value)
        setSettingsReadAt(new Date().toISOString())
        setSettingsReadFailed(false)
      })
      .catch((cause: unknown) => {
        if (active) { setSettingsReadFailed(true); setError(cause instanceof Error ? cause.message : '无法读取本机设置') }
      })
    api.get<SmokeStatus>('/provider-smoke').then((value) => {
      if (active) setSmokeStatus(value)
    }).catch(() => { if (active) setSmokeStatus(null) })
    api.get<unknown>('/integrations/feishu/status').then((value) => {
      if (!active) return
      const parsed = parseFeishuStatus(value)
      if (parsed) { const next: FeishuStatusRead = { state: 'loaded', status: parsed, readAt: new Date().toISOString() }; feishuStatusRef.current = next; setFeishuStatus(next) }
      else setFeishuStatus((previous) => failedFeishuStatusRead(previous))
    }).catch(() => { if (active) setFeishuStatus((previous) => failedFeishuStatusRead(previous)) })
    return () => { active = false }
    // 换工作库（profile 或 workspace 身份）时重新读取本机状态；
    // 首次配置进度已经是后端按活动工作库解析，不再依赖浏览器存储键。
  }, [profileId, workspaceId])

  /** 手动打开向导：没有指定步骤时从本机记住的那一步续接。 */
  function openWizard(step: 2 | 3 | 4 | 5 = resumeWizardStep) { onRequestWizard?.(step) }

  function openAdvanced() {
    setAdvancedOpen(true)
    requestAnimationFrame(() => {
      const advanced = document.querySelector('.settings-advanced-block')
      if (advanced && typeof advanced.scrollIntoView === 'function') advanced.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  function setSecret(provider: SecretProvider, value: string) {
    setSecrets((current) => ({ ...current, [provider]: value }))
  }

  function requireKeychain() {
    if (!settings?.keychain_available) {
      throw new Error('当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。')
    }
  }

  async function patchSettings(patch: Record<string, unknown>): Promise<Settings> {
    const updated = await api.patch<Settings>('/settings', patch)
    setSettings(updated)
    return updated
  }

  /** 卡片内一次提交：先落盘配置，再用落盘后的账户标识保存密钥，不再要求先手工保存账户标识。 */
  async function saveModelCard(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const deepseekSecret = secrets.deepseek.trim()
      const dashscopeSecret = secrets.dashscope.trim()
      if (deepseekSecret || dashscopeSecret) requireKeychain()
      const updated = await patchSettings(settingsPatch(settings))
      const saved: string[] = []
      if (deepseekSecret) {
        await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret })
        saved.push('DeepSeek API Key')
        setSecret('deepseek', '')
      }
      if (dashscopeSecret) {
        await api.put('/credentials/dashscope', { account_id: credentialAccountId(updated, 'dashscope'), secret: dashscopeSecret })
        saved.push('阿里云 Model Studio API Key')
        setSecret('dashscope', '')
      }
      await load()
      setNotice(saved.length
        ? `设置已保存在本机；${saved.join('、')} 已保存到本机钥匙串。密钥已清空且不会再次显示，本次没有发起任何联网检查。`
        : '设置已保存在本机。保存过程没有联系 provider；模型变更不会自动重建索引。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存设置') }
    finally { setBusy(false) }
  }

  async function saveFeishuCard(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const appSecret = secrets.feishu_app.trim()
      if (appSecret) requireKeychain()
      const updated = await patchSettings(settingsPatch(settings))
      // A confirmed configuration change makes any previous authorization summary stale by definition.
      setFeishuStatus({ state: 'unreadable' })
      if (appSecret) {
        await api.put('/credentials/feishu_app', { account_id: credentialAccountId(updated, 'feishu_app'), secret: appSecret })
        setSecret('feishu_app', '')
      }
      await load()
      await loadFeishuStatus()
      setNotice(appSecret
        ? '飞书应用配置已保存在本机；飞书应用密钥已保存到本机钥匙串。密钥已清空且不会再次显示，本次没有发起任何联网检查或授权。'
        : '飞书应用配置已保存在本机。保存过程没有联系飞书，也没有发起授权。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存飞书应用配置') }
    finally { setBusy(false) }
  }

  async function saveAdvancedSettings(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api.patch<Settings>('/settings', settingsPatch(settings))
      setSettings(updated)
      setNotice('高级设置已保存在本机。保存过程没有联系 provider。模型变更不会自动重建索引。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存设置') }
    finally { setBusy(false) }
  }

  async function confirmRemoveSecret() {
    if (!pendingRemoval) return
    const provider = pendingRemoval
    setBusy(true); setError(''); setNotice('')
    try {
      // 先读回落盘的账户标识，避免用界面上未保存的值去删除钥匙串条目。
      const fresh = await api.get<Settings>('/settings')
      await api.delete('/credentials/' + provider, { account_id: credentialAccountId(fresh, provider) })
      await load()
      if (provider === 'feishu_app') setFeishuStatus({ state: 'invalidated' })
      setNotice('所选应用密钥已从本机钥匙串删除；需要重新录入后才能使用对应能力。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法删除钥匙串密钥') }
    finally { setBusy(false); setPendingRemoval(null) }
  }

  async function confirmSmoke() {
    if (!pendingCheck) return
    const key = pendingCheck
    const { path, operation } = smokeChecks[key]
    setPendingCheck(null)
    setBusy(true); setError(''); setNotice('')
    try {
      await api.post('/provider-smoke/' + path, {})
      if (settings) setCheckResults((current) => ({ ...current, [key]: { outcome: 'succeeded', configStamp: smokeCheckConfigStamp(settings, key) } }))
      setNotice(`${operation} 合成连接检查成功。本次请求已计入授权次数。`)
    } catch (cause) {
      if (settings) setCheckResults((current) => ({ ...current, [key]: { outcome: 'failed', configStamp: smokeCheckConfigStamp(settings, key) } }))
      setError(cause instanceof Error ? cause.message : '请求结果未知；此尝试可能已计入次数。')
    } finally {
      await loadSmokeStatus()
      setBusy(false)
    }
  }

  const capabilities = settings?.capabilities ?? {}
  const credentials = settings?.credential_status ?? {}
  const checkOutcomes = Object.fromEntries((Object.keys(smokeChecks) as SmokeCheckKey[]).map((key) => {
    const result = checkResults[key]
    return [key, settings && result?.configStamp === smokeCheckConfigStamp(settings, key) ? result.outcome : 'none']
  })) as Record<SmokeCheckKey, CheckOutcome>
  const modelBadge = modelCardBadge({
    mode: settings?.mode ?? 'fake',
    credentials,
    capabilities,
    checkOutcomes,
  })
  const feishuBadge = feishuCardBadge({
    keychainAvailable: Boolean(settings?.keychain_available),
    read: feishuStatus,
  })

  const wizard = settings && <FirstUseWizard
    settings={settings}
    smokeStatus={smokeStatus}
    feishuStatus={feishuStatus}
    onClose={() => onWizardClose?.()}
    onSettingsChanged={(updated) => setSettings(updated)}
    onSmokeStatusRefresh={loadSmokeStatus}
    onFeishuStatusRefresh={loadFeishuStatus}
    persistProgress={persistWizardProgress ?? persistWizardProgressDefault}
    initialStep={initialWizardStep}
    initialCompleted={initialWizardCompleted}
    onWorkspaceStepBack={() => { onWizardClose?.(); onSwitchWorkspace() }}
    onStepChange={onWizardStepChange}
    onFinish={onFinishFirstUse}
  />

  if (wizardOnly) return settings ? <main className="onboarding-host">{wizard}</main> : <main className="setup-screen">
    <section className="setup-card" role={settingsReadFailed ? 'alert' : 'status'}>
      <h1>{settingsReadFailed ? '暂时无法读取本机设置' : '正在读取本机设置…'}</h1>
      {error && <p>{error}</p>}
      {settingsReadFailed && <button className="button secondary" type="button" onClick={() => void load()}>重新读取本机设置</button>}
    </section>
  </main>

  return <section className="content-wrap settings-view">
    <div className="eyebrow">本机 profile</div>
    <h1>设置</h1>
    <p className="lede">常用连接在下面三张卡里完成，技术字段默认收在「高级与自定义」。读取、保存和刷新设置不会连接外部服务，保存后也不会自动发起任何联网检查。</p>
    <p className="settings-mode-line">当前运行模式：<strong>{settings?.mode === 'real' ? 'Real · 显式启用' : 'Fake · 离线（默认）'}</strong><span>真实调用仍需一次性范围预览与独立确认。</span></p>
    <div className="settings-wizard-entry">
      <button className="button secondary" type="button" disabled={!settings} onClick={() => openWizard()}>打开连接向导</button>
      <span>按步完成工作库、模型与密钥、连接检查和飞书设置；可保存进度后继续。</span>
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status" className="settings-notice">{notice}</p>}
    {settingsReadAt && <p className="settings-help">本机设置最近读取于 {new Date(settingsReadAt).toLocaleString()}</p>}
    {!settings ? <div className="settings-cards" aria-label="设置读取状态">
      {(['工作库', 'AI 模型', '飞书'] as const).map((title) => <section className="settings-card" aria-label={title} key={title}>
        <CardHead title={title} badge={{ kind: 'unreadable', label: settingsReadFailed ? '暂时无法读取' : '正在读取', hint: '' }} />
        <p className="settings-card-desc">{settingsReadFailed ? '本机没有返回可用状态；此处不会推测已连接或可用。' : '正在读取本机保存的状态。'}</p>
        {settingsReadFailed && <button className="button secondary" type="button" onClick={() => void load()}>重新读取本机设置</button>}
      </section>)}
    </div> : <>
      <div className="settings-cards">
        <section className="settings-card" aria-label="工作库">
          <CardHead title="工作库" badge={{ kind: 'verified', label: '已连接', hint: '' }} />
          <p className="settings-card-desc">知识正文保存在这个工作库；索引、聊天历史、凭据与诊断记录按本机 profile 管理。</p>
          <div className="settings-list">
            <div><span>当前工作库</span><strong>{workspaceName}</strong></div>
            <div><span>运行方式</span><strong>本机 API + WebUI</strong></div>
          </div>
          <div className="button-row">
            <button className="button secondary" type="button" onClick={onSwitchWorkspace}>切换工作库</button>
          </div>
        </section>

        <section className="settings-card" aria-label="AI 模型">
          <CardHead title="AI 模型" badge={modelBadge} />
          <p className="settings-card-desc">按业务能力查看状态。模型名称、账户与密钥放在高级配置中；密钥只保存在本机钥匙串，页面不会回显。</p>
          <div className="settings-capability-summary">
            {(['llm', 'embedding', 'rerank'] as const).map((id) => {
              const capability = capabilities[id]
              const reason = reasonText(capability?.disabled_reason)
              return <div className="settings-capability-item" key={id}>
                <strong>{capabilityLabels[id]}</strong>
                <span>{checkedCapabilityStatusLabel(capability, checkOutcomes[
                  id === 'llm' ? 'deepseek_chat' : id === 'embedding' ? 'model_studio_embedding' : 'model_studio_rerank'
                ])}</span>
                {capability?.disabled_reason && <small>{reason.text} 下一步：{reason.next}</small>}
              </div>
            })}
          </div>
          <button className="button primary" type="button" onClick={openAdvanced}>配置 AI 模型与密钥</button>
        </section>

        <section className="settings-card" aria-label="飞书">
          <CardHead title="飞书" badge={feishuBadge} />
          <p className="settings-card-desc">状态来自本机授权记录。材料、日历与任务仍只读，并按已确认范围访问。</p>
          <p className="settings-card-next">{feishuBadge.hint}</p>
          {feishuStatus.state === 'stale' && <div className="settings-read-warning" role="alert">
            <p>本次读取失败；以下保留最近一次成功读取的结果，可能已过时{feishuStatus.readAt ? `（成功读取于 ${new Date(feishuStatus.readAt).toLocaleString()}）` : ''}。</p>
            <button className="button secondary" type="button" onClick={() => void loadFeishuStatus()}>重试读取</button>
          </div>}
          {feishuStatus.state === 'unreadable' && <button className="button secondary" type="button" onClick={() => void loadFeishuStatus()}>重试读取</button>}
          <div className="settings-capability-summary">
            {(['feishu_material_read', 'feishu_calendar_read', 'feishu_task_read', 'feishu_task_write'] as const).map((id) => {
              const capability = capabilities[id]
              const reason = reasonText(capability?.disabled_reason)
              return <div className="settings-capability-item" key={id}>
                <strong>{capabilityLabels[id]}</strong>
                <span>{capabilityStatusLabel(capability)}</span>
                {capability?.disabled_reason && <small>{reason.text} 下一步：{reason.next}</small>}
              </div>
            })}
          </div>
          <p className="settings-card-next">飞书任务写回仍不可用；本页不提供任何修改飞书任务的入口。</p>
          <FeishuAgentSetup className="button primary" />
        </section>
      </div>

      <details className="settings-advanced-block" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}>
        <summary>高级与自定义（模型配置、密钥、端点、账户标识、检查额度与诊断）</summary>

        <section className="provider-settings" aria-labelledby="model-config-heading">
          <div className="settings-section-heading"><h2 id="model-config-heading">AI 模型与密钥</h2><span>仅保存在本机</span></div>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。</p>}
          <form className="settings-card-form" onSubmit={saveModelCard}>
            <label className="settings-field"><span>整理与问答模型</span><select value={settings.llm.provider} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, provider: event.target.value as LLMProvider, model: event.target.value === 'fake' ? null : 'deepseek-flash', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="deepseek">DeepSeek · deepseek-flash</option></select></label>
            <div className="secret-slot">
              <label htmlFor="secret-deepseek">DeepSeek API Key<span>用于整理与问答。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-deepseek" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.deepseek} onChange={(event) => setSecret('deepseek', event.target.value)} />
              <small>{credentials.deepseek ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
            </div>
            <label className="settings-field"><span>知识索引向量化模型</span><select value={settings.embedding.provider} onChange={(event) => setSettings({ ...settings, embedding: { ...settings.embedding, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-embedding', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-embedding</option></select></label>
            <label className="settings-field"><span>检索结果排序模型</span><select value={settings.rerank.provider} onChange={(event) => setSettings({ ...settings, rerank: { ...settings.rerank, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-rerank', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-rerank</option></select></label>
            <div className="secret-slot">
              <label htmlFor="secret-dashscope">阿里云 Model Studio API Key<span>向量化与排序共用此密钥。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-dashscope" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.dashscope} onChange={(event) => setSecret('dashscope', event.target.value)} />
              <small>{credentials.dashscope ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
            </div>
            <div className="button-row"><button className="button primary" disabled={busy}>保存 AI 模型设置</button></div>
          </form>
        </section>

        <section className="provider-settings" aria-labelledby="feishu-config-heading">
          <div className="settings-section-heading"><h2 id="feishu-config-heading">飞书应用设置</h2><span>{feishuBadge.label}</span></div>
          <p className="settings-help">重新读取只检查本机保存状态，不连接飞书，也不占用连接检查额度。</p>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void loadFeishuStatus()}>重新读取授权状态</button>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。</p>}
          <form className="settings-card-form" onSubmit={saveFeishuCard}>
            <label className="settings-field"><span>飞书应用 App ID</span><input value={settings.feishu.app_id} maxLength={200} placeholder="cli_…（非秘密，用于本机凭据槽）" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, app_id: event.target.value } })} /></label>
            <label className="settings-field"><span>日历读取身份</span><select value={settings.feishu.identity} onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, identity: event.target.value as Settings['feishu']['identity'] } })}><option value="app">应用身份（默认；需要应用有可用主日历）</option><option value="user">用户身份（使用已授权用户的主日历）</option></select></label>
            <label className="settings-field"><span>日历 ID（可选）</span><input value={settings.feishu.calendar_id} maxLength={200} placeholder="留空则解析主日历；多候选时填写具体 ID" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, calendar_id: event.target.value } })} /></label>
            <p className="settings-help">应用身份没有主日历或返回多个候选时，改用用户身份，或填写具体日历 ID。保存后不会被模型设置覆盖。</p>
            <div className="secret-slot">
              <label htmlFor="secret-feishu">飞书应用密钥<span>App Secret，仅保存在本机钥匙串。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-feishu" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.feishu_app} onChange={(event) => setSecret('feishu_app', event.target.value)} />
              <small>{credentials.feishu_app ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
            </div>
            <div className="button-row"><button className="button primary" disabled={busy}>保存飞书设置</button></div>
          </form>
        </section>

        <section className="provider-settings settings-check-block">
          <div className="settings-section-heading"><h2>受限合成连接检查</h2><span>每项需单独确认</span></div>
          <p className="settings-help">先用固定短合成 payload 检查接口连通与响应结构，不发送工作库材料。每项最多一次，失败、超时与未知结果同样计数且不会自动重发；点击后需确认本次范围才会发出请求。</p>
          <div className="button-row">
            <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'deepseek_chat', busy)} type="button" onClick={() => setPendingCheck('deepseek_chat')}>DeepSeek Chat（剩余 {smokeStatus?.remaining?.deepseek_chat ?? '…'}）</button>
            <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'model_studio_embedding', busy)} type="button" onClick={() => setPendingCheck('model_studio_embedding')}>Embedding（剩余 {smokeStatus?.remaining?.model_studio_embedding ?? '…'}）</button>
            <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'model_studio_rerank', busy)} type="button" onClick={() => setPendingCheck('model_studio_rerank')}>Rerank（剩余 {smokeStatus?.remaining?.model_studio_rerank ?? '…'}）</button>
          </div>
          {pendingCheck && <SmokeCheckConfirm check={pendingCheck} smokeStatus={smokeStatus} busy={busy} onConfirm={() => void confirmSmoke()} onCancel={() => setPendingCheck(null)} />}
        </section>

        <form className="provider-settings" onSubmit={saveAdvancedSettings}>
          <div className="settings-section-heading"><h2>运行模式与账户标识</h2><span>{settings.mode === 'fake' ? '离线模式' : '真实 provider 已选择'}</span></div>
          <label className="settings-field"><span>运行模式</span><select value={settings.mode} onChange={(event) => setSettings({ ...settings, mode: event.target.value as Settings['mode'] })}><option value="fake">Fake · 离线</option><option value="real">Real · 显式启用</option></select></label>
          <label className="settings-field"><span>DeepSeek 账户标识</span><input value={settings.llm.account_id} maxLength={200} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, account_id: event.target.value } })} /></label>
          <label className="settings-field"><span>Model Studio 账户标识</span><input value={settings.model_studio_account_id} maxLength={200} onChange={(event) => setSettings({ ...settings, model_studio_account_id: event.target.value })} /></label>
          <div className="settings-field"><span>Model Studio 区域</span><strong>中国大陆（当前已核对 endpoint）</strong></div>
          <label className="settings-field"><span>Embedding Base URL</span><input type="url" value={settings.embedding.base_url ?? ''} onChange={(event) => setSettings({ ...settings, embedding: { ...settings.embedding, base_url: event.target.value } })} /></label>
          <label className="settings-field"><span>Rerank API Base URL</span><input type="url" value={settings.rerank.base_url ?? ''} onChange={(event) => setSettings({ ...settings, rerank: { ...settings.rerank, base_url: event.target.value } })} /></label>
          <label className="settings-field"><span>注册 callback URI</span><input value={settings.feishu.redirect_uri} placeholder="http://127.0.0.1:5173/api/v1/integrations/feishu/callback" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, redirect_uri: event.target.value } })} /></label>
          <details className="settings-help"><summary>问答输出预算</summary><label className="settings-field"><span>回答长度上限（生成 token）</span><input type="number" min={256} max={16384} step={256} value={settings.llm.max_output_tokens ?? ''} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, max_output_tokens: Number(event.target.value) } })} /></label><label className="settings-field"><span>回答推理预算</span><select value={settings.llm.reasoning_effort} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, reasoning_effort: event.target.value as Settings['llm']['reasoning_effort'] } })}><option value="low">低 · 默认</option><option value="high">高</option></select></label><p>整理固定关闭思考；此设置只影响问答。上限会进入真实操作预览与配置绑定。</p></details>
          <p className="settings-help">飞书 callback 必须与开发者后台完全一致且使用本机 loopback。Model Studio 只接受其 HTTPS 域名。请勿在聊天中发送密钥。</p>
          <div className="button-row"><button className="button primary" disabled={busy}>保存 provider 设置</button></div>
        </form>

        <section className="provider-settings" aria-labelledby="smoke-quota-heading">
          <div className="settings-section-heading"><h2 id="smoke-quota-heading">受限合成连接检查的额度细节</h2><span>跨运行不重置</span></div>
          {!smokeStatus ? <p className="settings-help">暂时无法读取本机调用记录；在恢复读取前不要假设额度仍可用。</p> : <table className="smoke-quota">
            <thead><tr><th>检查</th><th>累计已用</th><th>上限</th><th>剩余</th></tr></thead>
            <tbody>{(Object.keys(smokeChecks) as SmokeCheckKey[]).map((key) => <tr key={key}>
              <td>{smokeChecks[key].operation}</td>
              <td>{smokeStatus.counts?.[key] ?? '未知'}</td>
              <td>{smokeStatus.limits?.[key] ?? '未知'}</td>
              <td>{smokeStatus.remaining?.[key] ?? '未知'}</td>
            </tr>)}</tbody>
          </table>}
          <p className="settings-help">DeepSeek 检查最多输出 64 tokens；按当前官方高峰价估算，三项合计低于 ¥0.01（实际账单待服务方核对）。CNY 5 是提示词建议上限，不是用户设定预算。</p>
        </section>

        <section className="provider-settings" aria-labelledby="diagnostics-heading">
          <div className="settings-section-heading"><h2 id="diagnostics-heading">诊断信息</h2><span>只读</span></div>
          <div className="settings-diag">
            <span>当前工作库</span><strong>{workspaceName}</strong>
            <span>运行方式</span><strong>本机 API + WebUI</strong>
            <span>运行模式</span><strong>{settings.mode === 'real' ? 'Real · 显式启用' : 'Fake · 离线'}</strong>
            <span>macOS 钥匙串</span><strong>{settings.keychain_available ? '可用' : '不可用（密钥保存失败关闭）'}</strong>
            <span>Embedding 配置</span><strong>{settings.embedding_fingerprint ? '已配置' : '未配置'}</strong>
          </div>
        </section>

        <section className="provider-settings settings-danger-zone" aria-labelledby="danger-zone-heading">
          <div className="settings-section-heading"><h2 id="danger-zone-heading">危险操作</h2><span>仅影响所选应用密钥</span></div>
          <p className="settings-help">删除后无法从本机恢复；对应能力需要重新录入密钥才能使用。</p>
          <div className="button-row">
            <button className="button danger-secondary" type="button" disabled={busy || !credentials.deepseek} onClick={() => setPendingRemoval('deepseek')}>删除 DeepSeek 密钥</button>
            <button className="button danger-secondary" type="button" disabled={busy || !credentials.dashscope} onClick={() => setPendingRemoval('dashscope')}>删除 Model Studio 密钥</button>
            <button className="button danger-secondary" type="button" disabled={busy || !credentials.feishu_app} onClick={() => setPendingRemoval('feishu_app')}>删除飞书应用密钥</button>
          </div>
        </section>
      </details>

      {pendingRemoval && <ConfirmDialog
        title="删除所选本机密钥？"
        description="只会删除这张设置卡上所选应用的密钥。"
        consequence="删除后无法从本机恢复；对应能力需要重新录入密钥才能使用。"
        confirmLabel="删除密钥"
        busyLabel="正在删除…"
        busy={busy}
        danger
        onCancel={() => setPendingRemoval(null)}
        onConfirm={confirmRemoveSecret}
      />}
    </>}
  </section>
}
