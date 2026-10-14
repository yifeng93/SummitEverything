import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { FirstUseWizard } from './FirstUseWizard'
import { SmokeCheckConfirm } from './SmokeCheckConfirm'
import {
  badgeClass, capabilityLabels, capabilityStatusLabel, credentialAccountId, feishuCardBadge,
  modelCardBadge, parseFeishuStatus, reasonText, settingsPatch, smokeCheckDisabled, smokeChecks,
  type CardBadge, type CheckOutcome, type FeishuStatusRead, type SecretProvider, type Settings,
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

type SettingsViewProps = {
  workspaceName: string
  onSwitchWorkspace: () => void
  /** 首次配置向导的飞书授权入口；由 App.tsx 接到「今日 / 飞书日常」。 */
  onOpenFeishuDaily?: () => void
}

export function SettingsView({ workspaceName, onSwitchWorkspace, onOpenFeishuDaily }: SettingsViewProps) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [smokeStatus, setSmokeStatus] = useState<SmokeStatus | null>(null)
  // 密钥只允许停留在组件内存 state：不写 localStorage / sessionStorage / 工作库，
  // 提交成功后立即清空输入框，页面永不回显。
  const [secrets, setSecrets] = useState<Record<SecretProvider, string>>(emptySecrets)
  // 只记录最近一次已完成的合成检查结果，用于卡片徽章；不当作真实业务验证。
  const [lastCheck, setLastCheck] = useState<CheckOutcome>('none')
  // 飞书授权状态来自本地只读接口；读取失败时保持「无法读取」，绝不默认成已授权。
  const [feishuStatus, setFeishuStatus] = useState<FeishuStatusRead>({ state: 'loading' })
  const [pendingCheck, setPendingCheck] = useState<SmokeCheckKey | null>(null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function load(): Promise<Settings | null> {
    try {
      const value = await api.get<Settings>('/settings')
      setSettings(value)
      setError('')
      return value
    }
    catch (cause) {
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
      setFeishuStatus(parsed ? { state: 'loaded', status: parsed } : { state: 'unreadable' })
    }
    catch { setFeishuStatus({ state: 'unreadable' }) }
  }

  useEffect(() => {
    let active = true
    api.get<Settings>('/settings')
      .then((value) => {
        if (!active) return
        setSettings(value)
        // 首次进入设置页且三种凭据都没有配置时自动打开一次向导。判定只读本次
        // /settings 结果，不额外发请求，也不做任何客户端持久化；关闭后本次挂载
        // 不会再自动打开（这段逻辑只在挂载时执行一次）。
        const credentials = value.credential_status ?? {}
        if (!credentials.deepseek && !credentials.dashscope && !credentials.feishu_app) setWizardOpen(true)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : '无法读取本机设置')
      })
    api.get<SmokeStatus>('/provider-smoke').then((value) => {
      if (active) setSmokeStatus(value)
    }).catch(() => { if (active) setSmokeStatus(null) })
    api.get<unknown>('/integrations/feishu/status').then((value) => {
      if (!active) return
      const parsed = parseFeishuStatus(value)
      setFeishuStatus(parsed ? { state: 'loaded', status: parsed } : { state: 'unreadable' })
    }).catch(() => { if (active) setFeishuStatus({ state: 'unreadable' }) })
    return () => { active = false }
  }, [])

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

  async function removeSecret(provider: SecretProvider) {
    setBusy(true); setError(''); setNotice('')
    try {
      // 先读回落盘的账户标识，避免用界面上未保存的值去删除钥匙串条目。
      const fresh = await api.get<Settings>('/settings')
      await api.delete('/credentials/' + provider, { account_id: credentialAccountId(fresh, provider) })
      await load()
      if (provider === 'feishu_app') await loadFeishuStatus()
      setNotice('此工作库 profile 的本应用密钥已从钥匙串删除。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法删除钥匙串密钥') }
    finally { setBusy(false) }
  }

  async function confirmSmoke() {
    if (!pendingCheck) return
    const key = pendingCheck
    const { path, operation } = smokeChecks[key]
    setPendingCheck(null)
    setBusy(true); setError(''); setNotice('')
    try {
      await api.post('/provider-smoke/' + path, {})
      setLastCheck('succeeded')
      setNotice(`${operation} 合成连接检查成功。本次请求已计入授权次数。`)
    } catch (cause) {
      setLastCheck('failed')
      setError(cause instanceof Error ? cause.message : '请求结果未知；此尝试可能已计入次数。')
    } finally {
      await loadSmokeStatus()
      setBusy(false)
    }
  }

  const capabilities = settings?.capabilities ?? {}
  const credentials = settings?.credential_status ?? {}
  const modelBadge = modelCardBadge({
    mode: settings?.mode ?? 'fake',
    credentials,
    capabilities,
    lastCheck,
  })
  const feishuBadge = feishuCardBadge({
    keychainAvailable: Boolean(settings?.keychain_available),
    read: feishuStatus,
  })

  return <section className="content-wrap settings-view">
    <div className="eyebrow">本机 profile</div>
    <h1>设置</h1>
    <p className="lede">常用连接在下面三张卡里完成，技术字段默认收在「高级与自定义」。读取、保存和刷新设置不会连接外部服务，保存后也不会自动发起任何联网检查。</p>
    <p className="settings-mode-line">当前运行模式：<strong>{settings?.mode === 'real' ? 'Real · 显式启用' : 'Fake · 离线（默认）'}</strong><span>真实调用仍需一次性范围预览与独立确认。</span></p>
    <div className="settings-wizard-entry">
      <button className="button secondary" type="button" disabled={!settings} onClick={() => setWizardOpen(true)}>重新打开连接向导</button>
      <span>按步完成模型、密钥、连接检查与飞书接入；每步都可以跳过。</span>
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status" className="settings-notice">{notice}</p>}
    {!settings ? <p role="status">正在读取本机设置…</p> : <>
      <div className="settings-cards">
        <section className="settings-card" aria-label="工作库">
          <CardHead title="工作库" badge={{ kind: 'verified', label: '已连接', hint: '' }} />
          <p className="settings-card-desc">知识、原件与索引都放在这个工作库里；本机历史、凭据和诊断日志不随库迁移。</p>
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
          <p className="settings-card-desc">整理与问答用整理模型；知识索引向量化和检索排序用 Model Studio。密钥只保存在本机钥匙串，页面不会回显。</p>
          <p className="settings-card-next">{modelBadge.hint}</p>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。</p>}
          <form className="settings-card-form" onSubmit={saveModelCard}>
            <label className="settings-field"><span>整理模型</span><select value={settings.llm.provider} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, provider: event.target.value as LLMProvider, model: event.target.value === 'fake' ? null : 'deepseek-flash', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="deepseek">DeepSeek · deepseek-flash</option></select></label>
            <div className="secret-slot">
              <label htmlFor="secret-deepseek">DeepSeek API Key<span>用于整理与问答。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-deepseek" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.deepseek} onChange={(event) => setSecret('deepseek', event.target.value)} />
              <div className="secret-slot-actions">
                <small>{credentials.deepseek ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
                <button className="text-button" type="button" disabled={busy || !credentials.deepseek} onClick={() => void removeSecret('deepseek')}>删除本机密钥</button>
              </div>
            </div>
            <label className="settings-field"><span>Embedding</span><select value={settings.embedding.provider} onChange={(event) => setSettings({ ...settings, embedding: { ...settings.embedding, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-embedding', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-embedding</option></select></label>
            <label className="settings-field"><span>Rerank</span><select value={settings.rerank.provider} onChange={(event) => setSettings({ ...settings, rerank: { ...settings.rerank, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-rerank', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-rerank</option></select></label>
            <div className="secret-slot">
              <label htmlFor="secret-dashscope">阿里云 Model Studio API Key<span>Embedding 与 Rerank 共用此密钥。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-dashscope" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.dashscope} onChange={(event) => setSecret('dashscope', event.target.value)} />
              <div className="secret-slot-actions">
                <small>{credentials.dashscope ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
                <button className="text-button" type="button" disabled={busy || !credentials.dashscope} onClick={() => void removeSecret('dashscope')}>删除本机密钥</button>
              </div>
            </div>
            <div className="button-row">
              <button className="button primary" disabled={busy}>保存 AI 模型设置</button>
            </div>
          </form>
          <div className="settings-check-block">
            <h3>受限合成连接检查</h3>
            <p className="settings-help">先用固定短合成 payload 检查接口连通与响应结构，不发送工作库材料。每项最多一次，失败、超时与未知结果同样计数且不会自动重发；点击后需确认本次范围才会发出请求。</p>
            <div className="button-row">
              <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'deepseek_chat', busy)} type="button" onClick={() => setPendingCheck('deepseek_chat')}>DeepSeek Chat（剩余 {smokeStatus?.remaining?.deepseek_chat ?? '…'}）</button>
              <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'model_studio_embedding', busy)} type="button" onClick={() => setPendingCheck('model_studio_embedding')}>Embedding（剩余 {smokeStatus?.remaining?.model_studio_embedding ?? '…'}）</button>
              <button className="button secondary" disabled={smokeCheckDisabled(settings, smokeStatus, 'model_studio_rerank', busy)} type="button" onClick={() => setPendingCheck('model_studio_rerank')}>Rerank（剩余 {smokeStatus?.remaining?.model_studio_rerank ?? '…'}）</button>
            </div>
            {pendingCheck && <SmokeCheckConfirm
              check={pendingCheck}
              smokeStatus={smokeStatus}
              busy={busy}
              onConfirm={() => void confirmSmoke()}
              onCancel={() => setPendingCheck(null)}
            />}
          </div>
        </section>

        <section className="settings-card" aria-label="飞书">
          <CardHead title="飞书" badge={feishuBadge} />
          <p className="settings-card-desc">保存应用标识与应用密钥后，在「今日 / 飞书日常」完成授权，才能按已确认范围只读材料、日历与任务。</p>
          <p className="settings-card-next">{feishuBadge.hint}</p>
          <p className="settings-card-next">飞书任务写回仍不可用：缺少可独立核实写结果的方式，本页不提供任何修改飞书任务的入口。</p>
          <div className="button-row">
            <button className="text-button" type="button" disabled={busy} onClick={() => void loadFeishuStatus()}>重新读取授权状态</button>
          </div>
          {!settings.keychain_available && <p className="settings-help" role="status">当前运行环境无法访问 macOS 钥匙串。真实模式保存密钥会失败关闭，不会写入文件或内存。</p>}
          <form className="settings-card-form" onSubmit={saveFeishuCard}>
            <label className="settings-field"><span>飞书应用 App ID</span><input value={settings.feishu.app_id} maxLength={200} placeholder="cli_…（非秘密，用于本机凭据槽）" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, app_id: event.target.value } })} /></label>
            <div className="secret-slot">
              <label htmlFor="secret-feishu">飞书应用密钥<span>App Secret，仅保存在本机钥匙串。已保存的密钥不会显示，留空表示不修改。</span></label>
              <input id="secret-feishu" type="password" autoComplete="new-password" maxLength={20_000} value={secrets.feishu_app} onChange={(event) => setSecret('feishu_app', event.target.value)} />
              <div className="secret-slot-actions">
                <small>{credentials.feishu_app ? '本机钥匙串：已配置' : '本机钥匙串：未配置'}</small>
                <button className="text-button" type="button" disabled={busy || !credentials.feishu_app} onClick={() => void removeSecret('feishu_app')}>删除本机密钥</button>
              </div>
            </div>
            <div className="button-row">
              <button className="button primary" disabled={busy}>保存飞书设置</button>
            </div>
          </form>
        </section>
      </div>

      <details className="settings-advanced-block">
        <summary>高级与自定义（Endpoint · 账户标识 · 输出预算 · 能力状态 · 检查额度 · 诊断）</summary>

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

        <section className="provider-settings capability-list" aria-labelledby="capability-heading">
          <div className="settings-section-heading"><h2 id="capability-heading">能力状态</h2><span>当前不可对外请求</span></div>
          {Object.entries(capabilities).map(([id, capability]) => {
            const reason = reasonText(capability.disabled_reason)
            return <div className="capability-row" key={id}>
              <strong>{capabilityLabels[id] ?? id}</strong>
              <span>{capabilityStatusLabel(capability)}</span>
              <small>{reason.text}</small>
              <small className="capability-next">下一步：{reason.next}</small>
            </div>
          })}
        </section>

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
            <span>Embedding 指纹</span><strong>{settings.embedding_fingerprint ?? '—'}</strong>
          </div>
        </section>
      </details>

      {wizardOpen && <FirstUseWizard
        settings={settings}
        smokeStatus={smokeStatus}
        feishuStatus={feishuStatus}
        onClose={() => setWizardOpen(false)}
        onSettingsChanged={(updated) => setSettings(updated)}
        onSmokeStatusRefresh={loadSmokeStatus}
        onFeishuStatusRefresh={loadFeishuStatus}
        onOpenFeishuDaily={onOpenFeishuDaily}
      />}
    </>}
  </section>
}
