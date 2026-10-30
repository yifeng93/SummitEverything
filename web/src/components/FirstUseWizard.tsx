import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import {
  credentialAccountId, feishuCardBadge, smokeCheckDisabled, smokeChecks,
  type CheckOutcome, type FeishuStatusRead, type Settings, type SmokeCheckKey, type SmokeStatus,
  unpreparedLocalModel,
} from './settingsBadges'
import { SmokeCheckConfirm } from './SmokeCheckConfirm'
import { startFeishuAuthorization } from './feishuAuthorization'
import type { FirstUseProgress } from './firstUseProgress'

export type FirstUseWizardProps = {
  settings: Settings
  smokeStatus: SmokeStatus | null
  feishuStatus: FeishuStatusRead
  onClose: () => void
  /** 保存成功后用服务端返回的 Settings 覆盖父级状态，向导不自己保存副本。 */
  onSettingsChanged: (settings: Settings) => void
  onRuntimeSettingsChanged?: () => void
  onSmokeStatusRefresh: () => Promise<void> | void
  onFeishuStatusRefresh: () => Promise<void> | void
  /**
   * 把进度持久化到本机后端。只有 resolve 为 `true` 时向导才允许移动界面：
   * 步骤变化、关闭和完成都必须等这一份写入真的落地，否则不能假装已保存。
   */
  persistProgress: (progress: FirstUseProgress) => Promise<boolean>
  initialStep?: 2 | 3 | 4 | 5
  initialCompleted?: boolean
  onWorkspaceStepBack?: () => void
  onStepChange?: (step: 2 | 3 | 4 | 5) => void
  onFinish?: () => void
}

export type CapabilitySelection = { llm: boolean; embedding: boolean; rerank: boolean }

const steps = [
  { id: 1, label: '工作库' },
  { id: 2, label: '模型与密钥' },
  { id: 3, label: '检查连接' },
  { id: 4, label: '飞书' },
  { id: 5, label: '完成' },
]

const emptyOutcomes: Record<SmokeCheckKey, CheckOutcome> = {
  deepseek_chat: 'none', model_studio_embedding: 'none', model_studio_rerank: 'none',
}

function selectionFromSettings(): CapabilitySelection {
  return {
    llm: true,
    embedding: true,
    rerank: true,
  }
}

function providerPatch() {
  return {
    mode: 'real' as const,
    llm: {
      provider: 'deepseek' as const,
      model: 'deepseek-flash' as const,
      enabled: true,
    },
    embedding: {
      provider: 'local' as const,
      model: 'BAAI/bge-small-zh-v1.5' as const,
      dimensions: 512,
      enabled: true,
    },
    rerank: {
      provider: 'local' as const,
      model: 'BAAI/bge-small-zh-v1.5' as const,
      dimensions: 512,
      enabled: true,
    },
  }
}

export function FirstUseWizard({
  settings, smokeStatus, feishuStatus, onClose, onSettingsChanged, onRuntimeSettingsChanged,
  onSmokeStatusRefresh, onFeishuStatusRefresh, persistProgress, initialStep = 2,
  initialCompleted = false, onWorkspaceStepBack, onStepChange, onFinish,
}: FirstUseWizardProps) {
  // 步骤由父级解析出来的本机记录决定；向导不再自己读浏览器存储。
  const [step, setStep] = useState<number>(initialStep)
  const [completed, setCompleted] = useState(initialCompleted)
  // 写入失败的那一次跳转：保留下来让用户重试，而不是丢掉这次操作。
  const [failedTransition, setFailedTransition] = useState<{ progress: FirstUseProgress; apply: () => void } | null>(null)
  const [skippedSteps, setSkippedSteps] = useState<number[]>([])
  const [selection] = useState<CapabilitySelection>(() => selectionFromSettings())
  // 密钥只允许停留在组件内存：不写 localStorage / sessionStorage / 草稿，成功提交后立即清空。
  const [secrets, setSecrets] = useState({ deepseek: '', feishu_app: '' })
  const [feishuAppId, setFeishuAppId] = useState(settings.feishu.app_id)
  const [outcomes, setOutcomes] = useState<Record<SmokeCheckKey, CheckOutcome>>(emptyOutcomes)
  const [pendingCheck, setPendingCheck] = useState<SmokeCheckKey | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [authorizationUrl, setAuthorizationUrl] = useState<string | null>(null)
  const missingDeepSeekCredential = selection.llm && !secrets.deepseek.trim() && !settings.credential_status?.deepseek
  const missingCredentialTitle = missingDeepSeekCredential
    ? '请填写 DeepSeek API Key；真实问答需要此密钥。'
    : secrets.deepseek.trim() && !settings.keychain_available
        ? '当前无法访问 macOS 钥匙串，不能保存新密钥。'
        : undefined

  const feishuBadge = feishuCardBadge({
    keychainAvailable: Boolean(settings.keychain_available),
    read: feishuStatus,
  })

  /**
   * 所有会改变持久化状态的界面变化都必须经过这里：先写本机，写成功了才动界面。
   * 写失败时保留这次跳转、说明情况并让用户重试；界面停在原步骤，绝不假装保存。
   */
  async function commit(progress: FirstUseProgress, apply: () => void): Promise<boolean> {
    setBusy(true)
    setError('')
    setNotice('')
    let saved = false
    try {
      saved = await persistProgress(progress)
    } finally {
      setBusy(false)
    }
    if (!saved) {
      setFailedTransition({ progress, apply })
      setError('这一步还没有保存到本机，界面停留在当前步骤。请重试。')
      return false
    }
    setFailedTransition(null)
    apply()
    return true
  }

  function retryCommit() {
    if (!failedTransition) return
    void commit(failedTransition.progress, failedTransition.apply)
  }

  function goTo(next: number) {
    const target = (next === 1 ? 2 : next) as 2 | 3 | 4 | 5
    void commit({ step: target, completed, open: true }, () => {
      setPendingCheck(null)
      setStep(next)
      onStepChange?.(target)
    })
  }

  /** 提交成功后前进，同时保留这次成功说明（commit 会清空提示）。 */
  function advanceWithNotice(next: number, message: string): Promise<boolean> {
    const target = next as 2 | 3 | 4 | 5
    return commit({ step: target, completed, open: true }, () => {
      setPendingCheck(null)
      setStep(next)
      onStepChange?.(target)
      setNotice(message)
    })
  }

  function skipStep() {
    setSkippedSteps((current) => (current.includes(step) ? current : [...current, step]))
    goTo(step + 1)
  }

  /** 明确关闭：先把 open=false 落到本机，再收起向导。 */
  async function close(): Promise<boolean> {
    return commit({ step: step as FirstUseProgress['step'], completed, open: false }, () => {
      setPendingCheck(null)
      onClose()
    })
  }

  function setSecret(provider: 'deepseek' | 'feishu_app', value: string) {
    setSecrets((current) => ({ ...current, [provider]: value }))
  }

  async function saveModelStep(event: FormEvent) {
    event.preventDefault()
    setError(''); setNotice('')
    const deepseekSecret = secrets.deepseek.trim()
    if (deepseekSecret && !settings.keychain_available) {
      setError('当前运行环境无法访问 macOS 钥匙串。这一步失败关闭：不会保存设置，也不会写入密钥。')
      return
    }
    const missingDeepSeek = selection.llm && !deepseekSecret && !settings.credential_status?.deepseek
    if (missingDeepSeek) {
      setError('所选模型能力需要先配置对应密钥，或取消该能力。')
      return
    }
    setBusy(true)
    try {
      // 顺序固定：先 PATCH 落盘配置（切到 Real 并启用所选能力），再用落盘后的账户标识 PUT 密钥。
      const updated = await api.patch<Settings>('/settings', providerPatch())
      onSettingsChanged(updated)
      const saved: string[] = []
      if (deepseekSecret) {
        await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret })
        setSecret('deepseek', '')
        try { onSettingsChanged(await api.get<Settings>('/settings')) }
        catch { onRuntimeSettingsChanged?.() }
        saved.push('DeepSeek API Key')
      }
      await advanceWithNotice(3, saved.length
        ? `${saved.join('、')} 已保存到本机钥匙串，输入框已清空。运行模式按所选能力更新；这一步没有联网检查。`
        : '模型选择已保存在本机；没有新密钥需要保存。这一步没有联网检查。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存设置') }
    finally { setBusy(false) }
  }

  async function confirmCheck() {
    if (!pendingCheck) return
    const key = pendingCheck
    const { path, operation } = smokeChecks[key]
    setPendingCheck(null)
    setBusy(true); setError(''); setNotice('')
    try {
      await api.post('/provider-smoke/' + path, {})
      setOutcomes((current) => ({ ...current, [key]: 'succeeded' }))
      setNotice(`${operation} 合成连接检查成功。本次请求已计入授权次数。`)
    } catch (cause) {
      setOutcomes((current) => ({ ...current, [key]: 'failed' }))
      setError(cause instanceof Error ? cause.message : '请求结果未知；此尝试可能已计入次数。')
    } finally {
      await onSmokeStatusRefresh()
      setBusy(false)
    }
  }

  async function saveFeishuStep(event: FormEvent) {
    event.preventDefault()
    setError(''); setNotice('')
    const appSecret = secrets.feishu_app.trim()
    const appIdChanged = feishuAppId !== settings.feishu.app_id
    if (!appSecret && !appIdChanged) {
      setNotice('没有变更；这一步不会保存任何内容。')
      return
    }
    if (appSecret && !settings.keychain_available) {
      setError('当前运行环境无法访问 macOS 钥匙串。这一步失败关闭：不会保存设置，也不会写入密钥。')
      return
    }
    setBusy(true)
    try {
      const updated = await api.patch<Settings>('/settings', {
        feishu: { app_id: feishuAppId, redirect_uri: settings.feishu.redirect_uri },
      })
      onSettingsChanged(updated)
      if (appSecret) {
        await api.put('/credentials/feishu_app', { account_id: credentialAccountId(updated, 'feishu_app'), secret: appSecret })
        setSecret('feishu_app', '')
        try { onSettingsChanged(await api.get<Settings>('/settings')) }
        catch { onRuntimeSettingsChanged?.() }
      }
      await onFeishuStatusRefresh()
      await advanceWithNotice(5, appSecret
        ? '飞书应用标识与应用密钥已保存在本机，密钥输入框已清空。这一步不会发起授权，也不会联网。'
        : '飞书应用标识已保存在本机。这一步不会发起授权，也不会联网。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存飞书应用配置') }
    finally { setBusy(false) }
  }

  async function authorizeFeishu() {
    setBusy(true); setError(''); setNotice(''); setAuthorizationUrl(null)
    try {
      if (settings.mode !== 'real') throw new Error('真实连接尚未配置；不能使用模拟授权。')
      const result = await startFeishuAuthorization('real')
      setAuthorizationUrl(result.authorizationUrl)
      setNotice('已准备好飞书官方授权页面。打开后按页面提示操作；本机不会自动访问该地址或交换授权码。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法开始飞书授权') }
    finally { setBusy(false) }
  }

  /** 完成：先把 completed=true 落到本机，再离开向导进入今日。 */
  function finish() {
    void commit({ step: 5, completed: true, open: false }, () => {
      setCompleted(true)
      onFinish?.()
    })
  }

  function onCheckButton(key: SmokeCheckKey) {
    setError(''); setNotice('')
    setPendingCheck(key)
  }

  const stepLabel = steps.find((item) => item.id === step)?.label ?? ''

  return <div className="wizard-backdrop">
    <section className="wizard-panel" role="dialog" aria-modal="false" aria-label="首次配置向导">
      <header className="wizard-head">
        <div>
          <h2>连接向导</h2>
        </div>
        <button className="text-button" type="button" disabled={busy} onClick={() => void close()}>关闭向导</button>
      </header>

      <ol className="wizard-steps">
        {steps.map((item) => <li
          key={item.id}
          className={item.id === step ? 'wizard-step active' : 'wizard-step'}
          aria-current={item.id === step ? 'step' : undefined}
        >
          <span>{item.id}</span>{item.label}
        </li>)}
      </ol>

      {error && <p role="alert" className="form-error">{error}</p>}
      {failedTransition && <div className="button-row">
        <button className="button secondary" type="button" disabled={busy} onClick={retryCommit}>重试保存</button>
      </div>}
      {notice && <p role="status" className="settings-notice">{notice}</p>}

      <div className="wizard-body">
        <h3>第 {step} 步 · {stepLabel}</h3>

        {step === 2 && <form className="wizard-section" onSubmit={saveModelStep}>
          <div className="wizard-capability">
              <span><strong>整理与问答</strong><small>DeepSeek · deepseek-flash（真实服务）</small></span>
          </div>
          <div className="wizard-capability"><span><strong>知识索引与检索排序</strong><small>本地模型 · BAAI/bge-small-zh-v1.5</small></span></div>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。这一步会失败关闭：不能保存设置，也不能写入密钥。</p>}
          <div className="secret-slot">
            <label htmlFor="wizard-secret-deepseek">DeepSeek API Key<span>只保存在本机钥匙串，不会回显。</span></label>
            <input id="wizard-secret-deepseek" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.deepseek} aria-invalid={Boolean(missingDeepSeekCredential)} aria-describedby={missingDeepSeekCredential ? 'wizard-secret-deepseek-guidance' : undefined} onChange={(event) => setSecret('deepseek', event.target.value)} />
            {missingDeepSeekCredential && <small className="form-error" id="wizard-secret-deepseek-guidance">请填写 DeepSeek API Key。此能力不能改为离线模拟。</small>}
          </div>
          <p className="settings-help">向量化和结果排序由本地模型完成。首次下载约 95 MB，可在设置中明确开始；准备模型不会调用云端检索服务。</p>
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => { void (async () => { if (await close()) onWorkspaceStepBack?.() })() }}>上一步：工作库</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" disabled={busy || Boolean(missingCredentialTitle)} title={missingCredentialTitle}>保存密钥并继续</button>
          </div>
        </form>}

        {step === 3 && <div className="wizard-section">
          <div className="button-row">
            <button
              className="button secondary"
              type="button"
              disabled={smokeCheckDisabled(settings, smokeStatus, 'deepseek_chat', busy)}
              onClick={() => onCheckButton('deepseek_chat')}
            >检查 DeepSeek（剩余 {smokeStatus?.remaining?.deepseek_chat ?? '…'}）</button>
          </div>
          {pendingCheck && <SmokeCheckConfirm
            check={pendingCheck}
            smokeStatus={smokeStatus}
            busy={busy}
            onConfirm={() => void confirmCheck()}
            onCancel={() => setPendingCheck(null)}
          />}
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => void goTo(2)}>上一步</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" type="button" disabled={busy} onClick={() => void goTo(4)}>下一步</button>
          </div>
        </div>}

        {step === 4 && <form className="wizard-section" onSubmit={saveFeishuStep}>
          <p className="settings-card-next">当前授权状态：{feishuBadge.label}。{feishuBadge.hint}</p>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。这一步会失败关闭：不能保存设置，也不能写入密钥。</p>}
          <label className="settings-field"><span>飞书应用 App ID</span><input value={feishuAppId} maxLength={200} placeholder="cli_…（非秘密）" onChange={(event) => setFeishuAppId(event.target.value)} /></label>
          <div className="secret-slot">
            <label htmlFor="wizard-secret-feishu">飞书应用密钥<span>App Secret，只保存在本机钥匙串，页面不会回显。</span></label>
            <input id="wizard-secret-feishu" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.feishu_app} onChange={(event) => setSecret('feishu_app', event.target.value)} />
          </div>
          <div className="button-row"><button className="button secondary" type="button" disabled={busy || !settings.feishu.app_id} onClick={() => void authorizeFeishu()}>{feishuBadge.label === '已授权' ? '重新授权飞书' : '连接飞书'}</button>
            {authorizationUrl && <a className="button secondary" href={authorizationUrl} target="_blank" rel="noopener noreferrer">打开飞书官方授权页</a>}</div>
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => void goTo(3)}>上一步</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" disabled={busy}>保存飞书设置并继续</button>
          </div>
        </form>}

        {step === 5 && <div className="wizard-section">
          <div className="settings-diag wizard-summary">
            <span>运行模式</span><strong>真实连接</strong>
            <span>整理与问答</span><strong>DeepSeek · deepseek-flash</strong>
            <span>本地检索模型</span><strong>{(settings.local_model ?? unpreparedLocalModel).state === 'ready' ? '已准备好' : '尚未准备，可稍后下载'}</strong>
            <span>DeepSeek 密钥</span><strong>{settings.credential_status?.deepseek ? '已保存在本机钥匙串' : '未配置'}</strong>
            <span>飞书应用标识</span><strong>{settings.feishu.app_id ? '已保存' : '未设置'}</strong>
            <span>飞书应用密钥</span><strong>{settings.credential_status?.feishu_app ? '已保存在本机钥匙串' : '未配置'}</strong>
            <span>飞书授权状态</span><strong>{feishuBadge.label}</strong>
          </div>
          <p className="settings-card-next">本向导内完成的合成检查：{
            `DeepSeek ${outcomes.deepseek_chat === 'succeeded' ? '已通过' : outcomes.deepseek_chat === 'failed' ? '未通过' : '未执行'}`
          }。</p>
          {skippedSteps.length > 0 && <p className="settings-help">本次跳过或稍后处理的步骤：{skippedSteps.map((id) => `第 ${id} 步 ${steps.find((item) => item.id === id)?.label ?? ''}`).join('、')}。可随时从设置页重新打开向导。</p>}
          <p className="settings-card-next">仍未验证的边界：真实业务调用仍需在每次操作前预览并独立确认范围；飞书任务写回仍不可用（缺少可独立核实写结果的方式）；真实账户、OAuth 授权范围与 macOS 钥匙串生命周期仍未验证。以上都不是「已验证」。</p>
          <div className="wizard-actions">
            <button className="button secondary" type="button" onClick={() => void goTo(4)}>上一步</button>
            <button className="button primary" type="button" onClick={() => finish()}>完成并进入今日</button>
          </div>
        </div>}
      </div>
    </section>
  </div>
}
