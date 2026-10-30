import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react'
import { ChevronDown } from 'lucide-react'
import { api } from '../api/client'
import { FirstUseWizard } from './FirstUseWizard'
import { FeishuAgentSetup } from './FeishuAgentSetup'
import { AskPreferences } from './AskPreferences'
import { SmokeCheckConfirm } from './SmokeCheckConfirm'
import { PageHeader } from './PageHeader'
import { ConfirmDialog } from './ConfirmDialog'
import { LocalModelSetup } from './LocalModelSetup'
import { saveFirstUseProgress, type FirstUseProgress } from './firstUseProgress'
import {
  badgeClass, capabilityLabels, capabilityStatusLabel, checkedCapabilityStatusLabel, credentialAccountId, failedFeishuStatusRead, feishuCardBadge,
  modelCardBadge, parseFeishuStatus, reasonText, settingsPatch, smokeCheckConfigStamp, smokeCheckDisabled, smokeChecks,
  type CardBadge, type CheckOutcome, type CheckResult, type FeishuStatusRead, type SecretProvider, type Settings,
  type SmokeCheckKey, type SmokeStatus,
  unpreparedLocalModel,
} from './settingsBadges'

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
  onRuntimeSettingsChanged?: () => void
  onOpenApproval?: () => void
  onError?: (message: string) => void
}

export function SettingsView({ workspaceName, workspaceId = workspaceName, profileId = 'default', onSwitchWorkspace, wizardOnly = false, initialWizardStep = 2, resumeWizardStep = 2, initialWizardCompleted = false, persistWizardProgress, onRequestWizard, onWizardStepChange, onWizardClose, onFinishFirstUse, onAuthorizationChanged, onRuntimeSettingsChanged, onOpenApproval, onError }: SettingsViewProps) {
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
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const persistedLocalModelStamp = useRef('')

  function localModelStamp(value: Settings['local_model'] | undefined) {
    return JSON.stringify({ model: value?.model, revision: value?.revision, state: value?.state })
  }

  function acceptSavedSettings(updated: Settings) {
    persistedLocalModelStamp.current = localModelStamp(updated.local_model)
    onRuntimeSettingsChanged?.()
    setSettings(updated)
  }

  async function load(): Promise<Settings | null> {
    try {
      const value = await api.get<Settings>('/settings')
      persistedLocalModelStamp.current = localModelStamp(value.local_model)
      setSettings(value)
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
        persistedLocalModelStamp.current = localModelStamp(value.local_model)
        setSettings(value)
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
    acceptSavedSettings(updated)
    return updated
  }

  /** 卡片内一次提交：先落盘配置，再用落盘后的账户标识保存密钥，不再要求先手工保存账户标识。 */
  async function saveModelCard(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const deepseekSecret = secrets.deepseek.trim()
      if (deepseekSecret) requireKeychain()
      const updated = await patchSettings(settingsPatch(settings))
      const saved: string[] = []
      if (deepseekSecret) {
        await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret })
        onRuntimeSettingsChanged?.()
        saved.push('DeepSeek API Key')
        setSecret('deepseek', '')
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
        onRuntimeSettingsChanged?.()
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

  async function switchToLocalRetrieval() {
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api.patch<Settings>('/settings', {
        embedding: { ...settings.embedding, provider: 'local', model: 'BAAI/bge-small-zh-v1.5', dimensions: 512, enabled: true },
        rerank: { ...settings.rerank, provider: 'local', model: 'BAAI/bge-small-zh-v1.5', dimensions: 512, enabled: true },
      })
      acceptSavedSettings(updated)
      setNotice('检索配置已切换到本地模型。原有云端密钥仍留在本机；新索引需要查看范围并确认准备。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法切换本地检索配置') }
    finally { setBusy(false) }
  }

  async function saveAdvancedSettings(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api.patch<Settings>('/settings', settingsPatch(settings))
      acceptSavedSettings(updated)
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
      if (provider === 'deepseek') onRuntimeSettingsChanged?.()
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
    mode: settings?.mode ?? 'real',
    credentials,
    capabilities,
    checkOutcomes,
  })
  const feishuBadge = feishuCardBadge({
    keychainAvailable: Boolean(settings?.keychain_available),
    read: feishuStatus,
  })
  const aiCapabilityIds = ['llm', 'embedding', 'rerank'] as const
  const aiReasonTexts = aiCapabilityIds
    .map((id) => capabilities[id]?.disabled_reason ? reasonText(capabilities[id].disabled_reason).text : '')
    .filter(Boolean)
  // 三项常常是同一句“离线 Fake”，逐行重复没有信息量；相同就只留一句脚注。
  const sharedAiReason = new Set(aiReasonTexts).size === 1 ? aiReasonTexts[0] : ''
  const feishuReadIds = ['feishu_material_read', 'feishu_calendar_read', 'feishu_task_read'] as const
  const feishuReadReasonTexts = feishuReadIds
    .map((id) => capabilities[id]?.disabled_reason ? reasonText(capabilities[id].disabled_reason).text : '')
    .filter(Boolean)
  const sharedFeishuReadReason = new Set(feishuReadReasonTexts).size === 1 ? feishuReadReasonTexts[0] : ''

  const wizard = settings && <FirstUseWizard
    settings={settings}
    smokeStatus={smokeStatus}
    feishuStatus={feishuStatus}
    onClose={() => onWizardClose?.()}
    onSettingsChanged={acceptSavedSettings}
    onRuntimeSettingsChanged={onRuntimeSettingsChanged}
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
    <PageHeader
      title="设置"
      actions={<button className="button secondary" type="button" disabled={!settings} onClick={() => openWizard()}>打开连接向导</button>}
    />
    <p className="settings-mode-line">
      <span className="pill">真实连接</span>
      {settings?.legacy_provider_migration_required && <span role="status" className="helper-line">旧 provider 设置已转为真实服务。请检查 DeepSeek 密钥、本地模型状态，并在审批中重建旧索引。</span>}
    </p>
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status" className="settings-notice">{notice}</p>}
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
          <div className="settings-list">
            <div><span>当前工作库</span><strong>{workspaceName}</strong></div>
          </div>
          <div className="button-row">
            <button className="button secondary" type="button" onClick={onSwitchWorkspace}>切换工作库</button>
          </div>
        </section>

        <section className="settings-card" aria-label="AI 模型">
          <CardHead title="AI 模型" badge={modelBadge} />
          <div className="cap-list">
            {aiCapabilityIds.map((id) => {
              const capability = capabilities[id]
              const reason = reasonText(capability?.disabled_reason)
              return <div className="cap-row" key={id}>
                <strong>{capabilityLabels[id]}</strong>
                  <span className="cap-state">{id === 'llm' ? checkedCapabilityStatusLabel(capability, checkOutcomes.deepseek_chat) : capabilityStatusLabel(capability)}</span>
                {capability?.disabled_reason && !sharedAiReason && <p className="cap-reason">{reason.text}</p>}
              </div>
            })}
          </div>
          {sharedAiReason && <p className="card-footnote">{sharedAiReason}</p>}
          <LocalModelSetup key={`${profileId}:${workspaceId}`} status={settings.local_model ?? unpreparedLocalModel} onStatus={(local_model) => {
            const updated = { ...settings, local_model }
            const nextStamp = localModelStamp(local_model)
            if (persistedLocalModelStamp.current !== nextStamp) onRuntimeSettingsChanged?.()
            persistedLocalModelStamp.current = nextStamp
            setSettings(updated)
          }} />
          {(settings.embedding.provider === 'dashscope' || settings.rerank.provider === 'dashscope') && <div className="settings-read-warning" role="status"><p>旧云端检索设置已停用。原密钥会保留在本机，切换时不会删除。</p><button className="button secondary" type="button" disabled={busy} onClick={() => void switchToLocalRetrieval()}>切换到本地检索</button></div>}
          <details className="card-more">
            <summary>如何启用真实模型</summary>
            <ul>
              {aiCapabilityIds.map((id) => {
                const capability = capabilities[id]
                const reason = reasonText(capability?.disabled_reason)
                return capability?.disabled_reason ? <li key={id}><strong>{capabilityLabels[id]}</strong>下一步：{reason.next}</li> : null
              })}
            </ul>
          </details>
          <button className="button primary" type="button" onClick={openAdvanced}>配置 AI 模型与密钥</button>
        </section>

        <section className="settings-card" aria-label="飞书">
          <CardHead title="飞书" badge={feishuBadge} />
          {feishuStatus.state === 'loaded' && feishuStatus.status.authorized && <p className="card-footnote">已授权读取；不表示身份已核实，也不能写回飞书任务。</p>}
          {feishuStatus.state === 'stale' && <div className="settings-read-warning" role="alert">
            <p>本次读取失败；以下保留最近一次成功读取的结果，可能已过时{feishuStatus.readAt ? `（成功读取于 ${new Date(feishuStatus.readAt).toLocaleString()}）` : ''}。</p>
            <button className="button secondary" type="button" onClick={() => void loadFeishuStatus()}>重试读取</button>
          </div>}
          {feishuStatus.state === 'unreadable' && <button className="button secondary" type="button" onClick={() => void loadFeishuStatus()}>重试读取</button>}
          <div className="cap-list">
            {(['feishu_material_read', 'feishu_calendar_read', 'feishu_task_read', 'feishu_task_write'] as const).map((id, index) => {
              const capability = capabilities[id]
              const reason = reasonText(capability?.disabled_reason)
              return <Fragment key={id}>
                <div className="cap-row">
                  <strong>{capabilityLabels[id]}</strong>
                  <span className="cap-state">{capabilityStatusLabel(capability)}</span>
                  {capability?.disabled_reason && !(sharedFeishuReadReason && id !== 'feishu_task_write') && <p className="cap-reason">{reason.text}</p>}
                </div>
                {index === 2 && sharedFeishuReadReason && <p className="card-footnote">读取类能力：{sharedFeishuReadReason}</p>}
              </Fragment>
            })}
          </div>
          <details className="card-more">
            <summary>各项能力为什么还不能用</summary>
            <ul>
              {(['feishu_material_read', 'feishu_calendar_read', 'feishu_task_read', 'feishu_task_write'] as const).map((id) => {
                const capability = capabilities[id]
                const reason = reasonText(capability?.disabled_reason)
                return capability?.disabled_reason ? <li key={id}><strong>{capabilityLabels[id]}</strong>下一步：{reason.next}</li> : null
              })}
            </ul>
          </details>
          <p className="card-footnote">飞书任务写回仍不可用；本页不提供任何修改飞书任务的入口。</p>
          <FeishuAgentSetup className="button primary" />
        </section>
      </div>

      <section className="settings-card settings-ask-card" aria-label="知识问答">
        <div className="settings-section-heading"><h2>知识问答</h2><span>索引、角色与记忆只保存在本机</span></div>
        <AskPreferences onOpenApproval={onOpenApproval} onError={onError} />
      </section>

      <details className="settings-advanced-block" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}>
        <summary>高级与自定义<ChevronDown className="advanced-chevron" size={15} strokeWidth={1.75} aria-hidden="true" /></summary>

        <section className="provider-settings" aria-labelledby="model-config-heading">
          <div className="settings-section-heading"><h2 id="model-config-heading">AI 模型与密钥</h2><span>仅保存在本机</span></div>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。</p>}
          <form className="settings-card-form" onSubmit={saveModelCard}>
            <div className="settings-field"><span>整理与问答模型</span><strong>DeepSeek · deepseek-flash</strong></div>
            <div className="secret-slot">
              <label htmlFor="secret-deepseek">DeepSeek API Key<span>用于整理与问答。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-deepseek" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.deepseek} onChange={(event) => setSecret('deepseek', event.target.value)} />
              <small>{credentials.deepseek ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
            </div>
            {(settings.local_model ?? unpreparedLocalModel).state === 'ready'
              ? <p className="settings-help">向量化和结果排序均使用本地检索模型。</p>
              : <p className="settings-help">向量化和结果排序均使用本地检索模型。首次准备需在设置卡中明确点击下载。</p>}
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
          </div>
          {pendingCheck && <SmokeCheckConfirm check={pendingCheck} smokeStatus={smokeStatus} busy={busy} onConfirm={() => void confirmSmoke()} onCancel={() => setPendingCheck(null)} />}
        </section>

        <form className="provider-settings" onSubmit={saveAdvancedSettings}>
          <div className="settings-section-heading"><h2>运行模式与账户标识</h2><span>真实连接</span></div>
          <div className="settings-field"><span>运行模式</span><strong>真实连接</strong></div>
          <label className="settings-field"><span>DeepSeek 账户标识</span><input value={settings.llm.account_id} maxLength={200} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, account_id: event.target.value } })} /></label>
          <label className="settings-field"><span>注册 callback URI</span><input value={settings.feishu.redirect_uri} placeholder="http://127.0.0.1:5173/api/v1/integrations/feishu/callback" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, redirect_uri: event.target.value } })} /></label>
          <details className="settings-help"><summary>问答输出预算</summary><label className="settings-field"><span>回答长度上限（生成 token）</span><input type="number" min={256} max={16384} step={256} value={settings.llm.max_output_tokens ?? ''} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, max_output_tokens: Number(event.target.value) } })} /></label><label className="settings-field"><span>回答推理预算</span><select value={settings.llm.reasoning_effort} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, reasoning_effort: event.target.value as Settings['llm']['reasoning_effort'] } })}><option value="low">低 · 默认</option><option value="high">高</option></select></label><p>整理固定关闭思考；此设置只影响问答。上限会进入真实操作预览与配置绑定。</p></details>
          <p className="settings-help">飞书 callback 必须与开发者后台完全一致且使用本机 loopback。请勿在聊天中发送密钥。</p>
          <div className="button-row"><button className="button primary" disabled={busy}>保存 provider 设置</button></div>
        </form>

        <section className="provider-settings" aria-label="DeepSeek 合成连接检查"><p className="settings-help">DeepSeek 检查需单独确认，只发送固定短合成内容；不会发送工作库材料。</p></section>

        <section className="provider-settings" aria-labelledby="diagnostics-heading">
          <div className="settings-section-heading"><h2 id="diagnostics-heading">诊断信息</h2><span>只读</span></div>
          <div className="settings-diag">
            <span>当前工作库</span><strong>{workspaceName}</strong>
            <span>运行方式</span><strong>本机 API + WebUI</strong>
            <span>运行模式</span><strong>真实连接</strong>
            <span>macOS 钥匙串</span><strong>{settings.keychain_available ? '可用' : '不可用（密钥保存失败关闭）'}</strong>
            <span>本地检索模型</span><strong>{(settings.local_model ?? unpreparedLocalModel).state === 'ready' ? '已准备好' : (settings.local_model ?? unpreparedLocalModel).state === 'preparing' ? '正在准备' : '尚未准备'}</strong>
          </div>
        </section>

        <section className="provider-settings settings-danger-zone" aria-labelledby="danger-zone-heading">
          <div className="settings-section-heading"><h2 id="danger-zone-heading">危险操作</h2><span>仅影响所选应用密钥</span></div>
          <p className="settings-help">删除后无法从本机恢复；对应能力需要重新录入密钥才能使用。</p>
          <div className="button-row">
            <button className="button danger-secondary" type="button" disabled={busy || !credentials.deepseek} onClick={() => setPendingRemoval('deepseek')}>删除 DeepSeek 密钥</button>
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
