import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { components } from '../api/generated'

type Settings = components['schemas']['SettingsSummary']
type LLMProvider = Settings['llm']['provider']
type ModelProvider = Settings['embedding']['provider']
type SmokeStatus = {
  counts: Record<string, number>
  limits: Record<string, number>
  remaining: Record<string, number>
}

const secretProviders = [
  { id: 'feishu_app', label: '飞书应用密钥' },
  { id: 'deepseek', label: 'DeepSeek API Key' },
  { id: 'dashscope', label: '阿里云 Model Studio API Key' },
]

const capabilityLabels: Record<string, string> = {
  feishu_material_read: '读取已选择的飞书材料',
  feishu_calendar_read: '读取飞书日历',
  feishu_task_read: '读取飞书任务',
  feishu_task_write: '创建或更改飞书任务',
  llm: '整理与问答模型',
  embedding: '知识索引向量化',
  rerank: '检索结果排序',
}

const disabledReasons: Record<string, string> = {
  oauth_protocol_unverified: '飞书授权流程与权限范围尚未核实。',
  protocol_unverified: '接口和时间范围映射尚未核实。',
  date_and_result_proof_unverified: '任务日期语义和写入结果核实方式尚未确认。',
  offline_default: '当前使用离线 Fake；此路径不会访问真实 provider。',
  provider_not_configured: '已选 provider；真实模式与本机密钥尚未完成配置。',
  limited_synthetic_smoke_only: '已配置；仅开放一次合成连接检查，真实业务调用仍关闭。',
}

function credentialAccountId(settings: Settings, provider: string): string {
  if (provider === 'feishu_app') return settings.feishu.app_id || 'default'
  if (provider === 'deepseek') return settings.llm.account_id
  return settings.model_studio_account_id
}

export function SettingsView({ workspaceName, onSwitchWorkspace }: { workspaceName: string; onSwitchWorkspace: () => void }) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [persistedSettings, setPersistedSettings] = useState<Settings | null>(null)
  const [smokeStatus, setSmokeStatus] = useState<SmokeStatus | null>(null)
  const [secret, setSecret] = useState('')
  const [secretProvider, setSecretProvider] = useState('deepseek')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const accountMatchesSavedSettings = Boolean(
    settings && persistedSettings &&
    credentialAccountId(settings, secretProvider) === credentialAccountId(persistedSettings, secretProvider),
  )

  async function load() {
    try {
      const value = await api.get<Settings>('/settings')
      setSettings(value)
      setPersistedSettings(value)
      setError('')
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : '无法读取本机设置') }
  }

  async function loadSmokeStatus() {
    try { setSmokeStatus(await api.get<SmokeStatus>('/provider-smoke')) }
    catch { setSmokeStatus(null) }
  }

  useEffect(() => {
    let active = true
    api.get<Settings>('/settings')
      .then((value) => {
        if (active) {
          setSettings(value)
          setPersistedSettings(value)
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : '无法读取本机设置')
      })
    api.get<SmokeStatus>('/provider-smoke').then((value) => {
      if (active) setSmokeStatus(value)
    }).catch(() => { if (active) setSmokeStatus(null) })
    return () => { active = false }
  }, [])

  async function runSmoke(path: string, operation: string) {
    setBusy(true); setError(''); setNotice('')
    try {
      await api.post('/provider-smoke/' + path, {})
      setNotice(`${operation} 合成连接检查成功。本次请求已计入授权次数。`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '请求结果未知；此尝试可能已计入次数。')
    } finally {
      await loadSmokeStatus()
      setBusy(false)
    }
  }

  async function saveSecret(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError(''); setNotice('')
    try {
      if (!settings || !persistedSettings) return
      if (!accountMatchesSavedSettings) throw new Error('请先保存账户标识，再为该账户录入密钥。')
      await api.put('/credentials/' + secretProvider, { account_id: credentialAccountId(persistedSettings, secretProvider), secret })
      setSecret('')
      setNotice('密钥已保存到本机钥匙串。页面不会再次显示密钥。')
      await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存密钥') }
    finally { setBusy(false) }
  }

  async function removeSecret() {
    setBusy(true); setError(''); setNotice('')
    try {
      if (!settings || !persistedSettings) return
      if (!accountMatchesSavedSettings) throw new Error('请先保存账户标识，再管理该账户的密钥。')
      await api.delete('/credentials/' + secretProvider, { account_id: credentialAccountId(persistedSettings, secretProvider) })
      setNotice('此工作库 profile 的本应用密钥已从钥匙串删除。')
      await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法删除钥匙串密钥') }
    finally { setBusy(false) }
  }

  async function saveSettings(event: FormEvent) {
    event.preventDefault()
    if (!settings) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api.patch<Settings>('/settings', {
        mode: settings.mode,
        model_studio_account_id: settings.model_studio_account_id,
        feishu: settings.feishu,
        llm: settings.llm,
        embedding: settings.embedding,
        rerank: settings.rerank,
      })
      setSettings(updated)
      setPersistedSettings(updated)
      setNotice('设置已保存在本机。保存过程没有联系 provider。模型变更不会自动重建索引。')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存设置') }
    finally { setBusy(false) }
  }

  return <section className="content-wrap settings-view">
    <div className="eyebrow">本机 profile</div>
    <h1>设置</h1>
    <p className="lede">Provider 设置与密钥按当前工作库保存在这台设备。读取、保存和刷新设置不会连接外部服务。</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status" className="settings-notice">{notice}</p>}
    {!settings ? <p role="status">正在读取本机设置…</p> : <>
      <form className="provider-settings" onSubmit={saveSettings}>
        <div className="settings-section-heading"><h2>Provider 选择</h2><span>{settings.mode === 'fake' ? '离线模式' : '真实 provider 已选择'}</span></div>
        <label className="settings-field"><span>运行模式</span><select value={settings.mode} onChange={(event) => setSettings({ ...settings, mode: event.target.value as Settings['mode'] })}><option value="fake">Fake · 离线</option><option value="real">Real · 显式启用</option></select></label>
        <label className="settings-field"><span>整理模型</span><select value={settings.llm.provider} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, provider: event.target.value as LLMProvider, model: event.target.value === 'fake' ? null : 'deepseek-flash', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="deepseek">DeepSeek · deepseek-flash</option></select></label>
        <label className="settings-field"><span>DeepSeek 账户标识</span><input value={settings.llm.account_id} maxLength={200} onChange={(event) => setSettings({ ...settings, llm: { ...settings.llm, account_id: event.target.value } })} /></label>
        <label className="settings-field"><span>Embedding</span><select value={settings.embedding.provider} onChange={(event) => setSettings({ ...settings, embedding: { ...settings.embedding, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-embedding', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-embedding</option></select></label>
        <label className="settings-field"><span>Embedding Base URL</span><input type="url" value={settings.embedding.base_url} onChange={(event) => setSettings({ ...settings, embedding: { ...settings.embedding, base_url: event.target.value } })} /></label>
        <label className="settings-field"><span>Rerank</span><select value={settings.rerank.provider} onChange={(event) => setSettings({ ...settings, rerank: { ...settings.rerank, provider: event.target.value as ModelProvider, model: event.target.value === 'fake' ? null : 'qwen3.7-text-rerank', enabled: event.target.value !== 'fake' } })}><option value="fake">Fake · 离线</option><option value="dashscope">阿里云 Model Studio · qwen3.7-text-rerank</option></select></label>
        <label className="settings-field"><span>Rerank API Base URL</span><input type="url" value={settings.rerank.base_url} onChange={(event) => setSettings({ ...settings, rerank: { ...settings.rerank, base_url: event.target.value } })} /></label>
        <label className="settings-field"><span>Model Studio 账户标识</span><input value={settings.model_studio_account_id} maxLength={200} onChange={(event) => setSettings({ ...settings, model_studio_account_id: event.target.value })} /></label>
        <div className="settings-field"><span>Model Studio 区域</span><strong>中国大陆（当前已核对 endpoint）</strong></div>
        <label className="settings-field"><span>Feishu App ID</span><input value={settings.feishu.app_id} maxLength={200} onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, app_id: event.target.value } })} /></label>
        <label className="settings-field"><span>注册 callback URI</span><input value={settings.feishu.redirect_uri} placeholder="http://127.0.0.1:5173/api/v1/integrations/feishu/callback" onChange={(event) => setSettings({ ...settings, feishu: { ...settings.feishu, redirect_uri: event.target.value } })} /></label>
        <p className="settings-help">飞书 callback 必须与开发者后台完全一致且使用本机 loopback。Model Studio 只接受其 HTTPS 域名。请勿在聊天中发送密钥。Embedding 参数变化需要显式查看索引计划。</p>
        <button className="button primary" disabled={busy}>保存 provider 设置</button>
      </form>

      <form className="provider-settings credential-form" onSubmit={saveSecret}>
        <div className="settings-section-heading"><h2>本机密钥</h2><span>{settings.keychain_available ? '钥匙串可用' : '钥匙串不可用'}</span></div>
        {!settings.keychain_available && <p className="settings-help">当前运行环境无法访问 macOS 钥匙串。真实模式保存会失败关闭，不会写入文件或内存。</p>}
        <label className="settings-field"><span>Provider</span><select value={secretProvider} onChange={(event) => { setSecretProvider(event.target.value); setSecret('') }}>{secretProviders.map(({ id, label }) => <option key={id} value={id}>{label} · {settings.credential_status[id] ? '已配置' : '未配置'}</option>)}</select></label>
        <div className="settings-field"><span>当前账户标识</span><strong>{credentialAccountId(settings, secretProvider)}</strong></div>
        <label className="settings-field"><span>密钥</span><input type="password" autoComplete="new-password" value={secret} onChange={(event) => setSecret(event.target.value)} maxLength={20_000} /></label>
        <p className="settings-help">密钥只提交给本机 API 与系统钥匙串；不会进入工作库、配置文件或浏览器持久存储。</p>
        <div className="button-row">
          <button className="button secondary" disabled={busy || !secret || !accountMatchesSavedSettings}>保存到钥匙串</button>
          <button className="button secondary" type="button" disabled={busy || !accountMatchesSavedSettings || !settings.credential_status[secretProvider]} onClick={removeSecret}>删除本机密钥</button>
        </div>
      </form>

      <section className="provider-settings capability-list" aria-labelledby="capability-heading">
        <div className="settings-section-heading"><h2 id="capability-heading">能力状态</h2><span>当前不可对外请求</span></div>
        {Object.entries(settings.capabilities).map(([id, capability]) => <div className="capability-row" key={id}><strong>{capabilityLabels[id] ?? id}</strong><span>{capability.available ? '可用' : capability.configured ? '已配置，未启用' : '未启用'}</span><small>{disabledReasons[capability.disabled_reason ?? ''] ?? '需要单独验证。'}</small></div>)}
      </section>

      <section className="provider-settings capability-list" aria-labelledby="smoke-heading">
        <div className="settings-section-heading"><h2 id="smoke-heading">受限合成连接检查</h2><span>每项最多一次</span></div>
        <p className="settings-help">固定短合成 payload，仅检查接口连通与响应结构；失败、超时和未知结果也占用次数，不会自动重试。DeepSeek 最多输出 64 tokens；按当前官方高峰价估算，三项合计低于 ¥0.01（实际账单待服务方核对）。CNY 5 是提示词建议上限，不是用户设定预算。</p>
        <div className="button-row">
          <button className="button secondary" disabled={busy || !settings.keychain_available || !settings.credential_status.deepseek || settings.mode !== 'real' || settings.llm.provider !== 'deepseek' || !settings.llm.enabled || (smokeStatus?.remaining?.deepseek_chat ?? 0) < 1} onClick={() => void runSmoke('deepseek-chat', 'DeepSeek Chat')}>DeepSeek Chat（剩余 {smokeStatus?.remaining?.deepseek_chat ?? '…'}）</button>
          <button className="button secondary" disabled={busy || !settings.keychain_available || !settings.credential_status.dashscope || settings.mode !== 'real' || settings.embedding.provider !== 'dashscope' || !settings.embedding.enabled || (smokeStatus?.remaining?.model_studio_embedding ?? 0) < 1} onClick={() => void runSmoke('model-studio-embedding', 'Embedding')}>Embedding（剩余 {smokeStatus?.remaining?.model_studio_embedding ?? '…'}）</button>
          <button className="button secondary" disabled={busy || !settings.keychain_available || !settings.credential_status.dashscope || settings.mode !== 'real' || settings.rerank.provider !== 'dashscope' || !settings.rerank.enabled || (smokeStatus?.remaining?.model_studio_rerank ?? 0) < 1} onClick={() => void runSmoke('model-studio-rerank', 'Rerank')}>Rerank（剩余 {smokeStatus?.remaining?.model_studio_rerank ?? '…'}）</button>
        </div>
        <small>调用前先保存 Real/provider 设置并通过本机钥匙串录入密钥。检查不会发送工作库材料。</small>
      </section>
    </>}
    <div className="settings-list"><div><span>当前工作库</span><strong>{workspaceName}</strong></div><div><span>运行方式</span><strong>本机 API + WebUI</strong></div></div>
    <button className="button secondary" onClick={onSwitchWorkspace}>切换工作库</button>
  </section>
}
