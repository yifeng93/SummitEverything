import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import {
  credentialAccountId, feishuCardBadge, smokeCheckDisabled, smokeChecks,
  type CheckOutcome, type FeishuStatusRead, type Settings, type SmokeCheckKey, type SmokeStatus,
} from './settingsBadges'
import { SmokeCheckConfirm } from './SmokeCheckConfirm'

export type FirstUseWizardProps = {
  settings: Settings
  smokeStatus: SmokeStatus | null
  feishuStatus: FeishuStatusRead
  onClose: () => void
  /** 保存成功后用服务端返回的 Settings 覆盖父级状态，向导不自己保存副本。 */
  onSettingsChanged: (settings: Settings) => void
  onSmokeStatusRefresh: () => Promise<void> | void
  onFeishuStatusRefresh: () => Promise<void> | void
  /** 飞书授权入口；由 App.tsx 接到「今日 / 飞书日常」。向导不复制 OAuth 逻辑。 */
  onOpenFeishuDaily?: () => void
}

export type CapabilitySelection = { llm: boolean; embedding: boolean; rerank: boolean }

const steps = [
  { id: 1, label: '模型与接入地址' },
  { id: 2, label: '录入密钥' },
  { id: 3, label: '检查连接' },
  { id: 4, label: '飞书' },
  { id: 5, label: '完成' },
]

const emptyOutcomes: Record<SmokeCheckKey, CheckOutcome> = {
  deepseek_chat: 'none', model_studio_embedding: 'none', model_studio_rerank: 'none',
}

const DEEPSEEK_ENDPOINT = 'https://api.deepseek.com/chat/completions'

function selectionFromSettings(settings: Settings): CapabilitySelection {
  return {
    llm: settings.llm.provider !== 'deepseek' || settings.llm.enabled,
    embedding: settings.embedding.provider !== 'dashscope' || settings.embedding.enabled,
    rerank: settings.rerank.provider !== 'dashscope' || settings.rerank.enabled,
  }
}

function providerPatch(selection: CapabilitySelection) {
  return {
    mode: 'real' as const,
    llm: {
      provider: selection.llm ? ('deepseek' as const) : ('fake' as const),
      model: selection.llm ? ('deepseek-flash' as const) : null,
      enabled: selection.llm,
    },
    embedding: {
      provider: selection.embedding ? ('dashscope' as const) : ('fake' as const),
      model: selection.embedding ? ('qwen3.7-text-embedding' as const) : null,
      enabled: selection.embedding,
    },
    rerank: {
      provider: selection.rerank ? ('dashscope' as const) : ('fake' as const),
      model: selection.rerank ? ('qwen3.7-text-rerank' as const) : null,
      enabled: selection.rerank,
    },
  }
}

export function FirstUseWizard({
  settings, smokeStatus, feishuStatus, onClose, onSettingsChanged,
  onSmokeStatusRefresh, onFeishuStatusRefresh, onOpenFeishuDaily,
}: FirstUseWizardProps) {
  const [step, setStep] = useState(1)
  const [skippedSteps, setSkippedSteps] = useState<number[]>([])
  const [selection, setSelection] = useState<CapabilitySelection>(() => selectionFromSettings(settings))
  // 密钥只允许停留在组件内存：不写 localStorage / sessionStorage / 草稿，成功提交后立即清空。
  const [secrets, setSecrets] = useState({ deepseek: '', dashscope: '', feishu_app: '' })
  const [feishuAppId, setFeishuAppId] = useState(settings.feishu.app_id)
  const [outcomes, setOutcomes] = useState<Record<SmokeCheckKey, CheckOutcome>>(emptyOutcomes)
  const [pendingCheck, setPendingCheck] = useState<SmokeCheckKey | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const feishuBadge = feishuCardBadge({
    keychainAvailable: Boolean(settings.keychain_available),
    read: feishuStatus,
  })

  function goTo(next: number) {
    setPendingCheck(null)
    setError('')
    setNotice('')
    setStep(next)
  }

  /** 提交成功后前进，同时保留这次成功说明（goTo 会清空提示）。 */
  function advanceWithNotice(next: number, message: string) {
    setPendingCheck(null)
    setError('')
    setStep(next)
    setNotice(message)
  }

  function skipStep() {
    setSkippedSteps((current) => (current.includes(step) ? current : [...current, step]))
    goTo(step + 1)
  }

  function close() {
    setPendingCheck(null)
    onClose()
  }

  function setSecret(provider: 'deepseek' | 'dashscope' | 'feishu_app', value: string) {
    setSecrets((current) => ({ ...current, [provider]: value }))
  }

  async function saveModelStep(event: FormEvent) {
    event.preventDefault()
    setError(''); setNotice('')
    const deepseekSecret = secrets.deepseek.trim()
    const dashscopeSecret = secrets.dashscope.trim()
    if (!deepseekSecret && !dashscopeSecret) {
      setNotice('没有填入密钥；这一步不会保存任何内容。可以只填其中一把，或点“稍后再说”跳过。')
      return
    }
    if (!settings.keychain_available) {
      setError('当前运行环境无法访问 macOS 钥匙串。这一步失败关闭：不会保存设置，也不会写入密钥。')
      return
    }
    setBusy(true)
    try {
      // 顺序固定：先 PATCH 落盘配置（切到 Real 并启用所选能力），再用落盘后的账户标识 PUT 密钥。
      const updated = await api.patch<Settings>('/settings', providerPatch(selection))
      onSettingsChanged(updated)
      const saved: string[] = []
      if (deepseekSecret) {
        await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret })
        setSecret('deepseek', '')
        saved.push('DeepSeek API Key')
      }
      if (dashscopeSecret) {
        await api.put('/credentials/dashscope', { account_id: credentialAccountId(updated, 'dashscope'), secret: dashscopeSecret })
        setSecret('dashscope', '')
        saved.push('阿里云 Model Studio API Key')
      }
      advanceWithNotice(3, `已将运行模式切到 Real 并启用所选能力；${saved.join('、')} 已保存到本机钥匙串，输入框已清空。这一步没有联网检查。`)
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
      }
      await onFeishuStatusRefresh()
      advanceWithNotice(5, appSecret
        ? '飞书应用标识与应用密钥已保存在本机，密钥输入框已清空。这一步不会发起授权，也不会联网。'
        : '飞书应用标识已保存在本机。这一步不会发起授权，也不会联网。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存飞书应用配置') }
    finally { setBusy(false) }
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
          <div className="eyebrow">首次配置</div>
          <h2>连接向导</h2>
        </div>
        <button className="text-button" type="button" onClick={close}>关闭向导</button>
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
      {notice && <p role="status" className="settings-notice">{notice}</p>}

      <div className="wizard-body">
        <h3>第 {step} 步 · {stepLabel}</h3>

        {step === 1 && <div className="wizard-section">
          <p className="settings-card-desc">勾选这次要启用的能力；地址由本机配置提供，已内置，无需填写。这一步只改本机设置，不联网。</p>
          {([
            ['llm', '整理与问答', 'DeepSeek · deepseek-flash', DEEPSEEK_ENDPOINT],
            ['embedding', '知识索引向量化（embedding）', '阿里云 Model Studio · qwen3.7-text-embedding', settings.embedding.base_url],
            ['rerank', '检索结果排序（rerank）', '阿里云 Model Studio · qwen3.7-text-rerank', settings.rerank.base_url],
          ] as const).map(([key, title, model, endpoint]) => <div className="wizard-capability" key={key}>
            <label>
              <input
                type="checkbox"
                checked={selection[key]}
                onChange={(event) => setSelection((current) => ({ ...current, [key]: event.target.checked }))}
              />
              <span><strong>{title}</strong><small>{model}</small></span>
            </label>
            <div className="wizard-endpoint">
              <code>{endpoint || '（本机未提供）'}</code>
              <span>已内置，无需填写</span>
            </div>
          </div>)}
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" type="button" disabled={busy} onClick={() => goTo(2)}>下一步</button>
          </div>
        </div>}

        {step === 2 && <form className="wizard-section" onSubmit={saveModelStep}>
          <p className="settings-card-desc">这一步会把运行模式切到 Real 并启用第 1 步勾选的能力；保存设置本身不联网，也不会自动发起任何连接检查。</p>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。这一步会失败关闭：不能保存设置，也不能写入密钥。</p>}
          <div className="secret-slot">
            <label htmlFor="wizard-secret-deepseek">DeepSeek API Key<span>用于整理与问答。只保存在本机钥匙串，页面不会回显。</span></label>
            <input id="wizard-secret-deepseek" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.deepseek} onChange={(event) => setSecret('deepseek', event.target.value)} />
          </div>
          <div className="secret-slot">
            <label htmlFor="wizard-secret-dashscope">阿里云 Model Studio API Key<span>Embedding 与 Rerank 共用。只保存在本机钥匙串，页面不会回显。</span></label>
            <input id="wizard-secret-dashscope" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.dashscope} onChange={(event) => setSecret('dashscope', event.target.value)} />
          </div>
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => goTo(1)}>上一步</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" disabled={busy}>保存密钥并继续</button>
          </div>
        </form>}

        {step === 3 && <div className="wizard-section">
          <p className="settings-card-desc">每项最多一次合成检查，用于确认接口连通与响应结构；不发送工作库材料。点击后需确认本次范围才会联网，失败或超时同样计数且不会自动重发。</p>
          <div className="button-row">
            {(Object.keys(smokeChecks) as SmokeCheckKey[]).map((key) => <button
              key={key}
              className="button secondary"
              type="button"
              disabled={smokeCheckDisabled(settings, smokeStatus, key, busy)}
              onClick={() => onCheckButton(key)}
            >检查 {smokeChecks[key].operation}（剩余 {smokeStatus?.remaining?.[key] ?? '…'}）</button>)}
          </div>
          {pendingCheck && <SmokeCheckConfirm
            check={pendingCheck}
            smokeStatus={smokeStatus}
            busy={busy}
            onConfirm={() => void confirmCheck()}
            onCancel={() => setPendingCheck(null)}
          />}
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => goTo(2)}>上一步</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" type="button" disabled={busy} onClick={() => goTo(4)}>下一步</button>
          </div>
        </div>}

        {step === 4 && <form className="wizard-section" onSubmit={saveFeishuStep}>
          <p className="settings-card-desc">保存飞书应用标识与应用密钥。这一步不会发起授权，也不会联网；授权需要你到「今日 / 飞书日常」手动完成。</p>
          <p className="settings-card-next">当前授权状态：{feishuBadge.label}。{feishuBadge.hint}</p>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。这一步会失败关闭：不能保存设置，也不能写入密钥。</p>}
          <label className="settings-field"><span>飞书应用 App ID</span><input value={feishuAppId} maxLength={200} placeholder="cli_…（非秘密）" onChange={(event) => setFeishuAppId(event.target.value)} /></label>
          <div className="secret-slot">
            <label htmlFor="wizard-secret-feishu">飞书应用密钥<span>App Secret，只保存在本机钥匙串，页面不会回显。</span></label>
            <input id="wizard-secret-feishu" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.feishu_app} onChange={(event) => setSecret('feishu_app', event.target.value)} />
          </div>
          <div className="button-row">
            <button className="button secondary" type="button" disabled={!onOpenFeishuDaily} onClick={() => { close(); onOpenFeishuDaily?.() }}>前往今日 / 飞书日常完成授权</button>
          </div>
          {!onOpenFeishuDaily && <p className="settings-help">授权入口在「今日 / 飞书日常」；本页不提供授权操作。</p>}
          <div className="wizard-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => goTo(3)}>上一步</button>
            <button className="button secondary" type="button" disabled={busy} onClick={skipStep}>稍后再说</button>
            <button className="button primary" disabled={busy}>保存飞书设置并继续</button>
          </div>
        </form>}

        {step === 5 && <div className="wizard-section">
          <p className="settings-card-desc">以下是本机保存后的实际状态（来自本机设置与授权状态，不做客户端记录）。</p>
          <div className="settings-diag wizard-summary">
            <span>运行模式</span><strong>{settings.mode === 'real' ? 'Real · 显式启用' : 'Fake · 离线'}</strong>
            <span>整理与问答</span><strong>{settings.llm.provider === 'deepseek' && settings.llm.enabled ? '已启用（DeepSeek · deepseek-flash）' : '未启用（离线 Fake）'}</strong>
            <span>知识索引 embedding</span><strong>{settings.embedding.provider === 'dashscope' && settings.embedding.enabled ? '已启用（qwen3.7-text-embedding）' : '未启用（离线 Fake）'}</strong>
            <span>检索排序 rerank</span><strong>{settings.rerank.provider === 'dashscope' && settings.rerank.enabled ? '已启用（qwen3.7-text-rerank）' : '未启用（离线 Fake）'}</strong>
            <span>DeepSeek 密钥</span><strong>{settings.credential_status?.deepseek ? '已保存在本机钥匙串' : '未配置'}</strong>
            <span>Model Studio 密钥</span><strong>{settings.credential_status?.dashscope ? '已保存在本机钥匙串' : '未配置'}</strong>
            <span>飞书应用标识</span><strong>{settings.feishu.app_id ? '已保存' : '未设置'}</strong>
            <span>飞书应用密钥</span><strong>{settings.credential_status?.feishu_app ? '已保存在本机钥匙串' : '未配置'}</strong>
            <span>飞书授权状态</span><strong>{feishuBadge.label}</strong>
          </div>
          <p className="settings-card-next">本向导内完成的合成检查：{
            (Object.keys(smokeChecks) as SmokeCheckKey[])
              .map((key) => `${smokeChecks[key].operation} ${outcomes[key] === 'succeeded' ? '已通过' : outcomes[key] === 'failed' ? '未通过' : '未执行'}`)
              .join('、')
          }。</p>
          {skippedSteps.length > 0 && <p className="settings-help">本次跳过或稍后处理的步骤：{skippedSteps.map((id) => `第 ${id} 步 ${steps.find((item) => item.id === id)?.label ?? ''}`).join('、')}。可随时从设置页重新打开向导。</p>}
          <p className="settings-card-next">仍未验证的边界：真实业务调用仍需在每次操作前预览并独立确认范围；飞书任务写回仍不可用（缺少可独立核实写结果的方式）；真实账户、OAuth 授权范围与 macOS 钥匙串生命周期仍未验证。以上都不是「已验证」。</p>
          <div className="wizard-actions">
            <button className="button secondary" type="button" onClick={() => goTo(4)}>上一步</button>
            <button className="button primary" type="button" onClick={close}>返回设置页</button>
          </div>
        </div>}
      </div>
    </section>
  </div>
}
