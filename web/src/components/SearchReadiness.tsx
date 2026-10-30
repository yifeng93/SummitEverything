import { useRef, useState } from 'react'
import { api, type IndexPlan } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'

type IndexStatus = { state: string; fingerprint: string | null; pages: number; chunks: number; current_pages: number; stale_pages: number }
type AcceptancePlan = { plan_id: string; scope_sha256: string; request_limit: number }
type Props = {
  status: IndexStatus
  confirmedPageCount: number | null
  confirmedPagesLoading: boolean
  confirmedPagesError: string
  providerMode: 'fake' | 'real' | null
  configuredFingerprint: string
  localModelReady: boolean
  onComplete: () => Promise<void>
  onRefresh: () => void
  onError: (message: string) => void
}

export function SearchReadiness({ status, confirmedPageCount, confirmedPagesLoading, confirmedPagesError, providerMode, configuredFingerprint, localModelReady, onComplete, onRefresh, onError }: Props) {
  const [plan, setPlan] = useState<IndexPlan | null>(null)
  const [acceptance, setAcceptance] = useState<{ plan: AcceptancePlan; scope: Record<string, unknown> } | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [advancedBusy, setAdvancedBusy] = useState(false)
  const busyRef = useRef(false)
  const fingerprint = configuredFingerprint || status.fingerprint || ''
  const modelChanged = status.state !== 'not_ready' && Boolean(status.fingerprint && configuredFingerprint && status.fingerprint !== configuredFingerprint)
  const unavailable = !providerMode || !fingerprint || !localModelReady

  async function preview(mode: 'initial' | 'full' | 'incremental' | 'model_change', advanced = false) {
    if (busyRef.current) return
    if (mode === 'initial' && confirmedPageCount === null) {
      onError('已确认内容还没读取完成，请先刷新审批内容后再试。')
      return
    }
    if (mode === 'initial' && confirmedPageCount === 0) return
    if (!fingerprint) { onError('当前没有可用的搜索配置，请先在设置中检查向量化配置。'); return }
    busyRef.current = true
    setBusy(true); setAdvancedBusy(advanced); setPlan(null); setAcceptance(null); setConfirm(false)
    try {
      const current = await api.post<IndexPlan>('/index/plans', { mode, fingerprint })
      let reviewed: { plan: AcceptancePlan; scope: Record<string, unknown> } | null = null
      // Embedding and ranking run on-device; only the local index plan is needed.
      setPlan(current); setAcceptance(reviewed)
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取准备范围，请刷新后重试。')
    } finally {
      busyRef.current = false; setBusy(false); setAdvancedBusy(false)
    }
  }

  async function execute() {
    if (!plan || busyRef.current) return
    if (acceptance) { setConfirm(false); onError('本地索引准备不使用外部授权计划，请重新查看准备范围。'); return }
    busyRef.current = true; setBusy(true)
    try {
      if (acceptance) await api.post(`/acceptance-plans/${acceptance.plan.plan_id}/confirm`, { scope_sha256: acceptance.plan.scope_sha256, scope: acceptance.scope })
      await api.post('/index/jobs', { ...plan, ...(acceptance ? { acceptance_plan_id: acceptance.plan.plan_id } : {}) })
      setConfirm(false); setPlan(null); setAcceptance(null); await onComplete()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '准备没有完成，请刷新状态后再试。') }
    finally { busyRef.current = false; setBusy(false) }
  }

  const configurationKnown = providerMode !== null && Boolean(configuredFingerprint)
  const stateKnown = configurationKnown && ['ready', 'stale', 'not_ready', 'manual_required'].includes(status.state) && (status.state !== 'ready' || Boolean(status.fingerprint))
  const mode: 'initial' | 'incremental' | 'model_change' = status.state === 'not_ready' ? 'initial' : modelChanged ? 'model_change' : 'incremental'
  let statusText: string
  let explanation: string
  let actionLabel: string | null = null
  if (!configurationKnown) {
    statusText = '需要刷新状态'
    explanation = '搜索配置还没读取完成或暂不可用，请刷新状态后再决定是否准备。'
  } else if (!stateKnown && status.state !== 'not_ready') {
    statusText = '需要刷新状态'
    explanation = '当前状态还不能判断，请刷新后再决定是否准备。'
  } else if (modelChanged) {
    statusText = '搜索方式已更换'
    explanation = '需要重新准备本地索引，查看范围并确认后才会开始。'
    actionLabel = '查看重新准备范围'
  } else if (status.state === 'ready') {
    statusText = '内容已是最新，无需操作'
    explanation = `已准备 ${status.current_pages} 页。`
  } else if (status.state === 'not_ready' && confirmedPageCount === null) {
    statusText = confirmedPagesError ? '无法读取已确认内容' : '正在读取已确认内容'
    explanation = confirmedPagesError ? '请刷新审批内容；读取成功后才能判断是否可以首次准备。' : confirmedPagesLoading ? '读取成功后才会显示准备入口。' : '请刷新审批内容后再判断是否可以首次准备。'
  } else if (status.state === 'not_ready' && confirmedPageCount === 0) {
    statusText = '还没有可准备的内容'
    explanation = '先添加并确认正式内容，之后才能为搜索和问答做准备。'
  } else if (!stateKnown) {
    statusText = '需要刷新状态'
    explanation = '当前状态还不能判断，请刷新后再决定是否准备。'
  } else if (status.state === 'not_ready') {
    statusText = '首次准备待确认'
    explanation = '已确认内容还没有用于搜索和问答；查看范围并确认后才会开始。'
    actionLabel = '准备已确认的内容'
  } else {
    statusText = status.state === 'manual_required' ? '有更新待处理' : '有内容待更新'
    explanation = '查看待更新范围并确认后才会开始；本地准备只更新有变化的内容。'
    actionLabel = '查看待更新内容'
  }

  const previewMode: 'initial' | 'incremental' | 'model_change' = mode
  const pageCount = plan?.page_ids.length ?? 0
  const incremental = plan?.mode === 'incremental'
  const explanationForPlan = incremental
    ? `将检查 ${pageCount} 页，仅更新有变化的内容，其余沿用现有结果。`
    : `将准备 ${pageCount} 页已确认内容。`

  return <div className="index-status-panel search-readiness-panel">
    <div className="search-readiness-copy">
      <strong className="index-state">{statusText}</strong>
      <p>让搜索和问答能找到已确认的内容。内容没变化时，无需重复准备。</p>
      <p>{explanation}</p>
      {providerMode === 'fake' && <p className="helper-line">真实连接尚未准备好，索引与问答当前不可用。</p>}
    </div>
    <div className="search-readiness-actions">
      {!localModelReady && providerMode === 'real' && <p role="status">请先在设置中准备本地检索模型；准备模型和建立索引都不会发起云端向量化或排序请求。</p>}
      {actionLabel && <button className="button secondary" disabled={busy || unavailable || status.state === 'not_ready' && confirmedPageCount !== null && confirmedPageCount === 0} onClick={() => void preview(previewMode)}>{busy && !advancedBusy ? '正在查看范围…' : actionLabel}</button>}
      {(!stateKnown || status.state === 'not_ready' && confirmedPageCount === null) && <button className="button secondary" disabled={busy} onClick={onRefresh}>刷新状态</button>}
      {stateKnown && status.state !== 'not_ready' && !modelChanged && <details className="search-readiness-advanced">
        <summary>高级维护</summary>
        <p>日常使用无需操作；仅在排查搜索问题时使用。</p>
        <button className="button secondary" disabled={busy || unavailable} onClick={() => void preview('full', true)}>{advancedBusy ? '正在查看范围…' : '重新准备全部内容'}</button>
      </details>}
    </div>
    {plan && <div className="plan-card search-readiness-plan"><div><strong>{explanationForPlan}</strong><details className="technical-details"><summary>查看准备详情</summary><p>计划：{plan.mode === 'initial' ? '首次准备' : plan.mode === 'model_change' ? '搜索方式变更' : plan.mode === 'full' ? '全部重新准备' : '按变化更新'}</p><p>由本机模型向量化并排序；此步骤不调用云端检索服务。</p></details></div><button className="button primary" onClick={() => setConfirm(true)}>查看范围并确认</button></div>}
    {confirm && plan && <ConfirmDialog title="确认准备搜索和问答内容？" description={explanationForPlan} consequence={providerMode === 'real' ? '本机模型将处理本次范围内的页面，建立本机搜索索引；不会向 DeepSeek 或其他云端服务发送索引内容。' : '演示模式只体验本机操作流程，不调用真实模型，也不能据此判断真实搜索和问答效果。'} confirmLabel="确认并开始准备" busyLabel="正在准备…" busy={busy} onCancel={() => { setConfirm(false); setPlan(null); setAcceptance(null) }} onConfirm={execute}>
      <ul>{(plan.page_preview ?? []).map((page, index) => <li key={index}>{page.title ?? '页面'}{page.version ? ` · ${page.version}` : ''}</li>)}</ul>
    </ConfirmDialog>}
  </div>
}
