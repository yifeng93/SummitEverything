import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, indexUpdateMessage, type ActionCandidate, type Draft, type IntakeItem, type MutationResult, type Page, type Project, type SourceDetail } from '../api/client'
import type { components } from '../api/generated'
import { draftNeedsAttention, intakeNeedsAttention, intakeStateLabel } from '../approval-summary'
import { MarkdownText } from './MarkdownText'
import { DraftReview } from './DraftReview'
import { ConfirmDialog } from './ConfirmDialog'
import { TasksPanel } from './TasksPanel'
import { SourceOrganizer } from './SourceOrganizer'
import { newOperationId } from '../api/client'
import type { ApprovalTarget } from '../approvalTarget'

type Action = components['schemas']['Action']
type ActionPage = components['schemas']['ActionPage']
type Resource<T> = { data: T | null; loading: boolean; error: string; lastSuccess: string | null }
type IndexStatus = { state: string; fingerprint: string | null; pages: number; chunks: number; current_pages: number; stale_pages: number }
type AcceptancePlan = { plan_id: string; scope_sha256: string; request_limit: number }
type IndexPlan = components['schemas']['IndexPlan']
type IntakeJob = components['schemas']['IntakeJob']
type Props = { onPendingCount: (count: number) => void; onError: (message: string) => void; onOpenPage?: (pageId: string, expectedHash?: string) => void; refreshEpoch?: number; target?: ApprovalTarget | null; onTargetHandled?: () => void; onDirtyChange?: (dirty: boolean) => void; discardEpoch?: number }

const initial = <T,>(): Resource<T> => ({ data: null, loading: true, error: '', lastSuccess: null })
const formalNeedsAttention = (page: Page) => page.approval_state !== 'confirmed'
const actionableAction = (action: Action) => ['proposed', 'confirmed', 'running', 'failed', 'unknown'].includes(action.state)

function StatePanel<T>({ resource, retry, children }: { resource: Resource<T>; retry: () => void; children: (data: T) => ReactNode }) {
  if (resource.loading && resource.data === null) return <p className="quiet-empty" role="status">正在读取…</p>
  if (resource.error && resource.data === null) return <div className="resource-error" role="alert"><p>{resource.error}</p><button className="button secondary" onClick={retry}>重试</button></div>
  if (resource.data === null) return <p className="quiet-empty" role="status">正在读取…</p>
  return <>{resource.error && <p className="stale-note" role="status">{resource.error}；下方保留上次成功读取的内容。{resource.lastSuccess ? ` 最近成功读取：${new Date(resource.lastSuccess).toLocaleString('zh-CN')}` : ''} <button className="text-button" onClick={retry}>重试</button></p>}{children(resource.data)}{resource.loading && <span className="inline-loading" role="status">正在更新…</span>}{!resource.error && resource.lastSuccess && <small className="last-success">最近读取：{new Date(resource.lastSuccess).toLocaleString('zh-CN')}</small>}</>
}

function ApprovalGroup({ id, headingId, title, description, count, open, onToggle, children }: {
  id: string; headingId: string; title: string; description: string; count: string | number;
  open: boolean; onToggle: (open: boolean) => void; children: ReactNode
}) {
  return <details className="panel approval-group" id={id} role="region" aria-labelledby={headingId} open={open} onToggle={(event) => onToggle(event.currentTarget.open)}>
    <summary className="panel-heading"><div><h2 id={headingId}>{title}</h2><p>{description}</p></div><span className="count-badge">{count}</span></summary>
    <div className="approval-group-content">{children}</div>
  </details>
}

export function ApprovalView({ onPendingCount, onError, onOpenPage, refreshEpoch = 0, target = null, onTargetHandled, onDirtyChange, discardEpoch = 0 }: Props) {
  const [sources, setSources] = useState(initial<IntakeItem[]>)
  const [drafts, setDrafts] = useState(initial<Draft[]>)
  const [pages, setPages] = useState(initial<Page[]>)
  const [index, setIndex] = useState(initial<IndexStatus>)
  const [candidates, setCandidates] = useState(initial<ActionCandidate[]>)
  const [intents, setIntents] = useState(initial<ActionPage>)
  const [settingsMode, setSettingsMode] = useState<'fake' | 'real' | null>(null)
  const [configuredFingerprint, setConfiguredFingerprint] = useState('')
  const [filter, setFilter] = useState<'all' | 'pending' | 'complete'>('pending')
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [activeDraft, setActiveDraft] = useState<string | null>(null)
  const [activeSource, setActiveSource] = useState<string | null>(null)
  const [activePage, setActivePage] = useState<string | null>(null)
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null)
  const [sourceDetailLoading, setSourceDetailLoading] = useState(false)
  const [sourceDetailError, setSourceDetailError] = useState('')
  const [organizeResult, setOrganizeResult] = useState<IntakeJob | null>(null)
  const [draftDirty, setDraftDirty] = useState(false)
  const [confirmPage, setConfirmPage] = useState<Page | null>(null)
  const [formalResult, setFormalResult] = useState<{ pageId: string; title: string; indexMessage: string | null } | null>(null)
  const [draftResult, setDraftResult] = useState<{ draftId: string; pageIds: string[]; indexMessage: string | null } | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [loadedEpoch, setLoadedEpoch] = useState(-1)
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const returnScrollRef = useRef(0)
  const previousDiscardEpoch = useRef(discardEpoch)

  useEffect(() => { onDirtyChange?.(draftDirty) }, [draftDirty, onDirtyChange])
  useEffect(() => {
    if (previousDiscardEpoch.current === discardEpoch) return
    previousDiscardEpoch.current = discardEpoch
    setDraftDirty(false)
    setActiveDraft(null); setActiveSource(null); setActivePage(null)
  }, [discardEpoch])

  function openDraftFocus(id: string, trigger: HTMLElement) {
    returnFocusRef.current = trigger
    returnScrollRef.current = window.scrollY
    setActiveSource(null); setActivePage(null)
    setActiveDraft(id)
  }

  function openPageFocus(id: string, trigger: HTMLElement) {
    returnFocusRef.current = trigger
    returnScrollRef.current = window.scrollY
    setActiveDraft(null); setActiveSource(null)
    setActivePage(id)
  }

  function openSourceFocus(item: IntakeItem, trigger: HTMLElement) {
    returnFocusRef.current = trigger
    returnScrollRef.current = window.scrollY
    setActiveDraft(null); setActivePage(null)
    setActiveSource(item.item_id)
    setSelectedSources([item.item_id])
    setSourceDetail(null); setSourceDetailError(''); setSourceDetailLoading(true); setOrganizeResult(null)
    void api.get<SourceDetail>('/sources/' + item.source_id)
      .then(setSourceDetail)
      .catch((cause) => setSourceDetailError(cause instanceof Error ? cause.message : '无法读取原文'))
      .finally(() => setSourceDetailLoading(false))
  }

  async function refreshOrganizeResult() {
    if (!organizeResult) return
    try {
      const updated = await api.get<IntakeJob>('/jobs/' + organizeResult.job_id)
      setOrganizeResult(updated)
      await refreshDrafts()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法读取整理结果') }
  }

  function closeFocus() {
    if (draftDirty && !window.confirm('稿件有未保存的修改。返回清单会放弃这些修改，是否继续？')) return
    setDraftDirty(false)
    setActiveDraft(null); setActiveSource(null); setActivePage(null); setOrganizeResult(null); setDraftResult(null)
    requestAnimationFrame(() => {
      document.documentElement.scrollTop = returnScrollRef.current
      document.body.scrollTop = returnScrollRef.current
      returnFocusRef.current?.focus({ preventScroll: true })
    })
  }

  const load = useCallback(async <T,>(setter: React.Dispatch<React.SetStateAction<Resource<T>>>, request: () => Promise<T>) => {
    setter((current) => ({ ...current, loading: true, error: '' }))
    try {
      const data = await request()
      setter({ data, loading: false, error: '', lastSuccess: new Date().toISOString() })
      return data
    } catch (cause) {
      setter((current) => ({ ...current, loading: false, error: cause instanceof Error ? cause.message : '读取失败，请重试。' }))
      return null
    }
  }, [])

  const refreshSources = useCallback(() => load(setSources, () => api.get<IntakeItem[]>('/intake/items')), [load])
  const refreshDrafts = useCallback(() => load(setDrafts, () => api.get<Draft[]>('/drafts')), [load])
  const refreshPages = useCallback(() => load(setPages, async () => (await api.get<Page[]>('/pages')).filter((page) => page.storage_area === 'formal')), [load])
  const refreshIndex = useCallback(() => load(setIndex, () => api.get<IndexStatus>('/index/status')), [load])
  const refreshCandidates = useCallback(() => load(setCandidates, () => api.get<ActionCandidate[]>('/actions')), [load])
  const refreshIntents = useCallback(() => load(setIntents, () => api.get<ActionPage>('/action-intents?limit=20')), [load])
  const refreshAll = useCallback(async (epoch = 0) => {
    await Promise.allSettled([refreshSources(), refreshDrafts(), refreshPages(), refreshIndex(), refreshCandidates(), refreshIntents(), api.get<components['schemas']['SettingsSummary']>('/settings').then((value) => { setSettingsMode(value.mode); setConfiguredFingerprint(value.embedding_fingerprint) }).catch(() => { setSettingsMode(null); setConfiguredFingerprint('') })])
    setLoadedEpoch(epoch)
  }, [refreshSources, refreshDrafts, refreshPages, refreshIndex, refreshCandidates, refreshIntents])
  // This effect synchronizes the visible approval resources with an external refresh epoch.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void refreshAll(refreshEpoch) }, [refreshAll, refreshEpoch])

  const pendingSources = sources.data?.filter(intakeNeedsAttention) ?? []
  const pendingDraftList = drafts.data?.filter(draftNeedsAttention) ?? []
  const pendingPages = pages.data?.filter(formalNeedsAttention) ?? []
  const pendingActions = intents.data?.items.filter(actionableAction) ?? []
  const firstIndexNeedsReview = index.data?.state === 'not_ready' && (pages.data ?? []).some((page) => page.approval_state === 'confirmed')
  const pendingIndex = index.data && (index.data.state === 'manual_required' || firstIndexNeedsReview || settingsMode === 'real' && index.data.state !== 'ready') ? 1 : 0
  const needsCount = pendingSources.length + pendingDraftList.length + pendingPages.length + pendingIndex + pendingActions.length + (candidates.data?.length ?? 0)
  const pendingCategoryCount = [pendingSources.length, pendingDraftList.length, pendingPages.length, pendingIndex, pendingActions.length + (candidates.data?.length ?? 0)].filter((count) => count > 0).length
  const categoryCount = [sources.data, drafts.data, pages.data, index.data, intents.data !== null && candidates.data !== null ? true : null].filter((data) => data !== null).length
  const dataComplete = categoryCount === 5
  const groupOpen = (id: string, hasPending: boolean) => expandedGroups[id] ?? hasPending
  const setGroupOpen = (id: string, open: boolean) => setExpandedGroups((current) => ({ ...current, [id]: open }))
  useEffect(() => { onPendingCount(dataComplete ? needsCount : 0) }, [dataComplete, needsCount, onPendingCount])

  const rowsForFilter = <T,>(rows: T[], predicate: (row: T) => boolean, settled: (row: T) => boolean) => filter === 'all' ? rows : filter === 'pending' ? rows.filter(predicate) : rows.filter(settled)
  const visibleSources = includeTargets(rowsForFilter(sources.data ?? [], intakeNeedsAttention, (item) => !intakeNeedsAttention(item)), sources.data ?? [], target?.kind === 'source' ? target.itemIds : [], (item) => item.item_id)
  const visibleDrafts = includeTargets(rowsForFilter(drafts.data ?? [], draftNeedsAttention, (draft) => !draftNeedsAttention(draft)), drafts.data ?? [], target?.kind === 'draft' ? target.draftIds : [], (draft) => draft.draft_id)
  const visiblePages = includeTargets(rowsForFilter(pages.data ?? [], formalNeedsAttention, (page) => !formalNeedsAttention(page)), pages.data ?? [], target?.kind === 'formal' ? target.pageIds : [], (page) => page.page_id)
  const visibleIntents = rowsForFilter(intents.data?.items ?? [], actionableAction, (action) => !actionableAction(action))
  const visibleCandidates = filter === 'complete' ? [] : candidates.data ?? []
  const active = drafts.data?.find((draft) => draft.draft_id === activeDraft) ?? null
  const activeSourceItem = sources.data?.find((item) => item.item_id === activeSource) ?? null
  const activeFormalPage = pages.data?.find((page) => page.page_id === activePage) ?? null
  const focused = Boolean(activeDraft || activeSource || activePage)

  // Resolve exact-ID navigation only after the refreshed collections are available.
  useEffect(() => {
    if (!target) return
    if (loadedEpoch < refreshEpoch) return
    const findDestination = (): { element: HTMLElement | null; message: string } | null => {
      if (target.kind === 'source') {
        if (!sources.data || !drafts.data) return null
        const source = sources.data.find((item) => target.itemIds.includes(item.item_id))
        if (!source) return { element: null, message: '这条材料已不在当前工作库中。请刷新来源列表后重新选择。' }
        setSelectedSources(target.itemIds.filter((id) => sources.data?.some((item) => item.item_id === id && item.state !== 'processing' && item.state !== 'reviewing')))
        if (source.state === 'reviewing') {
          const related = drafts.data.find((draft) => draft.source_ids.includes(source.source_id))
          if (related) { setActiveDraft(related.draft_id); return { element: findByData('draftId', related.draft_id), message: '这条材料已有待审核稿，已打开现有稿件。' } }
        }
        setActiveSource(source.item_id); setActiveDraft(null); setActivePage(null)
        setSourceDetail(null); setSourceDetailError(''); setSourceDetailLoading(true); setOrganizeResult(null)
        void api.get<SourceDetail>('/sources/' + source.source_id).then(setSourceDetail).catch((cause) => setSourceDetailError(cause instanceof Error ? cause.message : '无法读取原文')).finally(() => setSourceDetailLoading(false))
        return { element: null, message: target.itemIds.length > 1 ? `已定位到本次成功保存的 ${target.itemIds.length} 项材料。选择归属后可继续整理。` : source.state === 'processing' ? '这条材料正在整理中，不会重复发起。' : source.state === 'completed' ? '这条材料已完成整理。' : '已定位到本次保存的材料。选择归属后可继续整理。' }
      }
      if (target.kind === 'draft') {
        if (!drafts.data) return null
        const draft = drafts.data.find((item) => target.draftIds.includes(item.draft_id))
        if (!draft) return { element: null, message: '这份稿件已不在当前待审核列表中，请刷新后重新选择。' }
        setActiveDraft(draft.draft_id); setActiveSource(null); setActivePage(null)
        return { element: null, message: '已打开本次整理生成的稿件。' }
      }
      if (!pages.data) return null
      const page = pages.data.find((item) => target.pageIds.includes(item.page_id))
      if (!page) return { element: null, message: '这份正式页面已不在当前工作库中，请刷新后重新选择。' }
      setActivePage(page.page_id); setActiveDraft(null); setActiveSource(null)
      return { element: null, message: '已定位到这次整理生成的正式页面。' }
    }
    const destination = findDestination()
    if (!destination) return
    // Keep the resolved destination feedback with its exact-ID navigation action.
    // oxlint-disable-next-line react/set-state-in-effect
    setNotice(destination.message)
    requestAnimationFrame(() => {
      const targetElement = destination.element ?? document.querySelector<HTMLElement>('.source-focus, .draft-focus, .formal-focus')
      targetElement?.scrollIntoView?.({ block: 'center' }); targetElement?.focus({ preventScroll: true })
    })
    onTargetHandled?.()
  }, [target, sources.data, drafts.data, pages.data, loadedEpoch, refreshEpoch, onTargetHandled])

  function toggleSource(id: string) {
    setSelectedSources((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  }

  async function confirmFormal() {
    if (!confirmPage) return
    setBusy(true)
    const page = confirmPage
    try {
      const result = await api.post<MutationResult>(`/pages/${page.page_id}/confirmations`, {
        metadata: page.metadata,
        body: page.body,
        expected_base_sha256: page.content_sha256,
        confirmation_id: newOperationId(),
        operation_id: newOperationId(),
      })
      setConfirmPage(null)
      const message = indexUpdateMessage(result.index_update)
      setFormalResult({ pageId: page.page_id, title: String(page.metadata.title ?? '未命名页面'), indexMessage: message })
      setActivePage(page.page_id); setActiveDraft(null); setActiveSource(null)
      setNotice(message ?? '当前版本已确认并保存。')
      await Promise.allSettled([refreshPages(), refreshIndex()])
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法确认并保存当前版本') }
    finally { setBusy(false) }
  }

  async function loadMoreActions() {
    const cursor = intents.data?.next_cursor
    if (!cursor) return
    await load(setIntents, async () => {
      const page = await api.get<ActionPage>(`/action-intents?limit=20&cursor=${encodeURIComponent(cursor)}`)
      return { items: [...(intents.data?.items ?? []), ...page.items], next_cursor: page.next_cursor }
    })
  }

  return <section className="content-wrap approval-view">
    <div className="page-heading"><div><div className="eyebrow">需要你点一下才算数</div><h1>审批</h1><p className="lede">来源、稿件、正式内容、索引与外部动作分开处理；每次确认都只作用于当前类别。</p></div></div>
    <div className="approval-toolbar" hidden={focused}><p className="hint" role="status">{!dataComplete ? `正在读取审批事项…（${categoryCount} / 5 类已读）` : filter === 'pending' ? `${needsCount} 项待处理 · 共 ${pendingCategoryCount} 类` : filter === 'complete' ? `${visibleSources.length + visibleDrafts.length + visiblePages.length + (intents.data?.items.filter((action) => !actionableAction(action)).length ?? 0)} 项已完成` : '显示全部事项'}</p><div className="approval-toolbar-actions"><label className="compact-field"><span>显示</span><select value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}><option value="all">全部</option><option value="pending">待处理</option><option value="complete">已完成</option></select></label></div></div>
    <p className="how-to-read" hidden={focused}>原件只供整理和追溯，不进入检索；稿件和正式页点击确认时会保存当前版本。索引计划与外部动作各有单独的预览和确认。来源类型来自可信入口，旧材料显示“类型未知”时不会按文件名猜。</p>
    {notice && <p className="success-note" role="status">{notice}</p>}

    <div className="approval-list" role="region" aria-label="审批清单" hidden={focused}>
    <ApprovalGroup id="approval-sources" headingId="approval-sources-heading" title="1 · 来源" description="选中来源后指定主线和项目，再明确发起整理。未知请求不会自动重发。" count={sources.data ? visibleSources.length : '—'} open={groupOpen('sources', pendingSources.length > 0)} onToggle={(open) => setGroupOpen('sources', open)}>
      <StatePanel resource={sources} retry={() => void refreshSources()}>{() => <><SourceList items={visibleSources} selected={selectedSources} onToggle={toggleSource} targetIds={target?.kind === 'source' ? target.itemIds : []} onOpenSource={openSourceFocus} /><SourceOrganizer items={(sources.data ?? []).filter((item) => selectedSources.includes(item.item_id))} onError={onError} onComplete={async (job) => { setOrganizeResult(job); await Promise.allSettled([refreshSources(), refreshDrafts()]) }} /></>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-drafts" headingId="approval-drafts-heading" title="2 · 稿件" description="查看渲染后的正文、冲突和来源；确认会把所选版本保存为正式内容。" count={drafts.data ? visibleDrafts.length : '—'} open={groupOpen('drafts', pendingDraftList.length > 0)} onToggle={(open) => setGroupOpen('drafts', open)}>
      <StatePanel resource={drafts} retry={() => void refreshDrafts()}>{() => visibleDrafts.length === 0 ? <div className="empty-state"><strong>{filter === 'complete' ? '没有已完成的稿件' : '没有待复核的稿件'}</strong></div> : <>
        <ul className="draft-list">{visibleDrafts.map((draft) => <li key={draft.draft_id} data-draft-id={draft.draft_id} tabIndex={-1}><div className="approval-row"><span className="source-title"><strong>{String(draft.metadata.title ?? '未命名稿件')}</strong><small>{draft.source_ids.length} 个来源 · {draft.important_conflicts?.length ?? 0} 项重要冲突</small></span><button type="button" className="button secondary" onClick={(event) => openDraftFocus(draft.draft_id, event.currentTarget)}>打开稿件：{String(draft.metadata.title ?? '未命名稿件')}</button></div></li>)}</ul>
      </>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-formal" headingId="approval-formal-heading" title="3 · 正式内容" description="仅确认当前这一版；文件变化后需要重新确认。确认正文不会批准进度或飞书任务。" count={pages.data ? visiblePages.length : '—'} open={groupOpen('formal', pendingPages.length > 0)} onToggle={(open) => setGroupOpen('formal', open)}>
      <StatePanel resource={pages} retry={() => void refreshPages()}>{() => visiblePages.length === 0 ? <div className="empty-state"><strong>没有待确认的正式内容</strong></div> : <ul className="knowledge-page-list">{visiblePages.map((page) => <li key={page.page_id} data-page-id={page.page_id} tabIndex={-1}><div className="formal-page-row"><button className="formal-open-button" onClick={(event) => openPageFocus(page.page_id, event.currentTarget)}><strong>{String(page.metadata.title ?? '未命名页面')}</strong><small>{formalKindLabel(String(page.metadata.kind ?? ''))} · {page.approval_state === 'invalid' ? '需要重新确认' : '待确认'}</small></button><button className="button secondary" onClick={() => setConfirmPage(page)}>确认并保存当前版本</button></div></li>)}</ul>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-index" headingId="approval-index-heading" title="4 · 索引" description="Fake 活跃索引会在正式内容确认后自动增量；首次建立、Real、模型变更、重建或服务要求手动确认时，需预览独立计划。" count={index.data ? (filter === 'complete' ? 0 : pendingIndex) : '—'} open={groupOpen('index', pendingIndex > 0)} onToggle={(open) => setGroupOpen('index', open)}>
      <StatePanel resource={index} retry={() => void refreshIndex()}>{(status) => <IndexControls status={status} providerMode={settingsMode} configuredFingerprint={configuredFingerprint} onComplete={async () => { await refreshIndex(); setNotice('索引操作已返回结果。') }} onError={onError} />}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-actions" headingId="approval-actions-heading" title="5 · 外部动作" description="候选建议、已保存动作和执行回执分开显示。未知结果只能核对或记录，不能自动重发。" count={intents.data && candidates.data ? visibleIntents.length + visibleCandidates.length : '—'} open={groupOpen('actions', pendingActions.length + (candidates.data?.length ?? 0) > 0)} onToggle={(open) => setGroupOpen('actions', open)}>
      <StatePanel resource={intents} retry={() => void refreshIntents()}>{() => <ActionIntentList items={visibleIntents} mode={settingsMode} onChanged={async () => { await Promise.allSettled([refreshIntents(), refreshCandidates()]) }} onError={onError} />}</StatePanel>
      {intents.data?.next_cursor && <button type="button" className="button secondary" disabled={intents.loading} onClick={() => void loadMoreActions()}>读取更多动作</button>}
      <div className="action-candidate-panel"><h3>尚未转成动作的建议</h3><StatePanel resource={candidates} retry={() => void refreshCandidates()}>{() => visibleCandidates.length ? <CandidateReview candidates={visibleCandidates} mode={settingsMode} /> : <div className="empty-state"><strong>没有待处理的动作建议</strong></div>}</StatePanel></div>
    </ApprovalGroup>
    </div>

    {active && <section className="panel draft-focus" aria-label={`稿件审核：${String(active.metadata.title ?? '未命名稿件')}`} tabIndex={-1}>
      <div className="focus-toolbar"><button className="button secondary" onClick={closeFocus}>返回审批清单</button><span>正在审核一份稿件</span></div>
      {draftResult?.draftId === active.draft_id ? <section className="formal-result" aria-label="稿件确认结果"><p>“{String(active.metadata.title ?? '未命名稿件')}”已确认并写入正式内容。{draftResult.indexMessage}</p>{draftResult.pageIds.length > 0 && <ul>{draftResult.pageIds.map((id) => <li key={id}><button className="button secondary" onClick={() => onOpenPage?.(id)}>打开本次保存的正式页</button></li>)}</ul>}<div className="button-row"><button className="button secondary" disabled={!visibleDrafts.some((draft) => draft.draft_id !== active.draft_id)} onClick={() => { const next = visibleDrafts.find((draft) => draft.draft_id !== active.draft_id); if (next) { setDraftResult(null); setActiveDraft(next.draft_id) } }}>下一份待审核</button><button className="button primary" onClick={closeFocus}>返回清单</button></div></section> : <DraftReview key={active.draft_id} draft={active} pages={pages.data ?? []} onError={onError} onDirtyChange={setDraftDirty} onConfirmed={async (result) => { const indexMessage = indexUpdateMessage(result.index_update); setDraftDirty(false); setDraftResult({ draftId: active.draft_id, pageIds: Object.keys(result.page_versions ?? {}), indexMessage }); await Promise.allSettled([refreshDrafts(), refreshPages(), refreshIndex(), refreshCandidates()]); setNotice(indexMessage ?? '稿件已确认并写入正式内容。') }} onUpdated={async () => { await refreshDrafts() }} />}
    </section>}
    {activeSourceItem && <section className="panel source-focus" aria-label={`来源详情：${activeSourceItem.title}`} tabIndex={-1}>
      <div className="focus-toolbar"><button className="button secondary" onClick={closeFocus}>返回审批清单</button><span>{intakeStateLabel(activeSourceItem.state)}</span></div>
      <h2>{activeSourceItem.title}</h2>
      <p className="source-focus-meta">{activeSourceItem.filename} · {activeSourceItem.created_at ? new Date(activeSourceItem.created_at).toLocaleString('zh-CN') : ''}</p>
      {sourceDetailLoading ? <p role="status">正在读取原文…</p> : sourceDetailError ? <div className="resource-error" role="alert"><p>{sourceDetailError}</p><button className="button secondary" onClick={() => openSourceFocus(activeSourceItem, document.activeElement as HTMLElement)}>重试</button></div> : sourceDetail && <article className="source-reading-body"><MarkdownText content={sourceDetail.text} /></article>}
      {activeSourceItem.state === 'processing' || activeSourceItem.state === 'reviewing' ? <><p className="helper-line">这条材料已有整理任务或稿件，不会再次发起整理。</p>{organizeResult && <button className="button secondary" onClick={() => void refreshOrganizeResult()}>刷新整理结果</button>}</> : <SourceOrganizer items={(sources.data ?? []).filter((item) => selectedSources.includes(item.item_id))} onError={onError} onComplete={async (job) => { setOrganizeResult(job); await Promise.allSettled([refreshSources(), refreshDrafts()]) }} />}
      {organizeResult && <section className="organize-result" aria-label="本次整理结果"><h3>本次整理结果</h3>{organizeResult.state === 'completed' ? <><p>已完成，生成 {organizeResult.draft_ids?.length ?? 0} 份待审核稿。</p>{organizeResult.draft_ids?.length ? <ul>{organizeResult.draft_ids.map((id) => { const draft = drafts.data?.find((item) => item.draft_id === id); return <li key={id}><span>{draft ? String(draft.metadata.title ?? '未命名稿件') : '稿件载入中'}</span>{draft && <button className="button secondary" onClick={(event) => openDraftFocus(id, event.currentTarget)}>打开这份稿件</button>}</li> })}</ul> : null}</> : <><p>整理任务当前状态：{organizeResult.state === 'unknown' ? '结果待核对' : '正在处理中'}。不会重复发起。</p><button className="button secondary" onClick={() => void refreshOrganizeResult()}>刷新整理结果</button></>}</section>}
    </section>}
    {activeFormalPage && <section className="panel formal-focus" aria-label={`正式内容：${String(activeFormalPage.metadata.title ?? '未命名页面')}`} tabIndex={-1}>
      <div className="focus-toolbar"><button className="button secondary" onClick={closeFocus}>返回审批清单</button><span>{activeFormalPage.approval_state === 'confirmed' ? '已确认' : '待确认'}</span></div>
      <h2>{String(activeFormalPage.metadata.title ?? '未命名页面')}</h2>
      <p className="source-focus-meta">{formalKindLabel(String(activeFormalPage.metadata.kind ?? ''))}</p>
      <article className="formal-reading-body"><MarkdownText content={activeFormalPage.body} onOpenPage={onOpenPage} /></article>
      {formalResult?.pageId === activeFormalPage.page_id && <div className="formal-result" role="status"><p>“{formalResult.title}”已保存为当前正式版本。{formalResult.indexMessage}</p><div className="button-row"><button className="button secondary" onClick={() => onOpenPage?.(activeFormalPage.page_id, activeFormalPage.content_sha256)}>打开正式页</button><button className="button secondary" disabled={!visiblePages.some((page) => page.page_id !== activeFormalPage.page_id)} onClick={() => { const next = visiblePages.find((page) => page.page_id !== activeFormalPage.page_id); if (next) { setFormalResult(null); setActivePage(next.page_id) } }}>下一份待确认</button></div></div>}
      {activeFormalPage.approval_state !== 'confirmed' && <button className="button primary" onClick={() => setConfirmPage(activeFormalPage)}>确认并保存当前版本</button>}
    </section>}

    {confirmPage && <ConfirmDialog title="确认并保存当前正式版本？" description={`“${String(confirmPage.metadata.title ?? '未命名页面')}”的正文和页面信息将按当前版本写入正式内容。`} consequence="只确认当前版本；不会创建飞书任务或改变项目进度。Fake 活跃索引按现有规则自动增量。" confirmLabel="确认并保存当前版本" busyLabel="正在保存…" busy={busy} onCancel={() => setConfirmPage(null)} onConfirm={confirmFormal}><MarkdownText content={confirmPage.body} onOpenPage={onOpenPage} /></ConfirmDialog>}
  </section>
}

function includeTargets<T>(filtered: T[], all: T[], ids: string[], key: (value: T) => string) {
  const included = new Set(filtered.map(key))
  return [...filtered, ...all.filter((row) => ids.includes(key(row)) && !included.has(key(row)))]
}
function findByData(name: 'itemId' | 'draftId' | 'pageId', value: string) {
  return Array.from(document.querySelectorAll<HTMLElement>(`[data-${name.replace(/[A-Z]/g, (letter) => '-' + letter.toLowerCase())}]`)).find((node) => node.dataset[name] === value) ?? null
}

function formalKindLabel(kind: string) {
  return ({ decision: '业务决定', log: '工作日志', thought: '工作思考', meeting: '会议纪要', material: '工作材料', overview: '项目主页', knowledge: '知识页', review: '周复盘' } as Record<string, string>)[kind] ?? '知识页'
}

function SourceList({ items, selected, onToggle, targetIds, onOpenSource }: { items: IntakeItem[]; selected: string[]; onToggle: (id: string) => void; targetIds: string[]; onOpenSource: (item: IntakeItem, trigger: HTMLElement) => void }) {
  if (items.length === 0) return <div className="empty-state"><strong>没有待整理的来源</strong><span>记一句或导入材料后会出现在这里。</span></div>
  return <ul className="source-list">{items.map((item) => <li key={item.item_id} data-item-id={item.item_id} tabIndex={-1} className={targetIds.includes(item.item_id) ? 'approval-target' : ''}><div className="source-row"><input aria-label={`选择来源 ${item.title}`} type="checkbox" disabled={item.state === 'processing' || item.state === 'reviewing'} checked={selected.includes(item.item_id)} onChange={() => onToggle(item.item_id)} /><span className="file-glyph" aria-hidden="true">文</span><span className="source-title"><button className="source-open-button" onClick={(event) => onOpenSource(item, event.currentTarget)}>{item.title}</button><small>{({ quick_note: '记一句', file: '文件', feishu_material: '飞书材料', unknown: '来源类型未知' } as Record<string, string>)[item.origin_kind ?? 'unknown']} · {item.filename} · {new Date(item.created_at).toLocaleDateString('zh-CN')}</small></span><span className="status-label">{intakeStateLabel(item.state)}</span></div></li>)}</ul>
}

function IndexControls({ status, providerMode, configuredFingerprint, onComplete, onError }: { status: IndexStatus; providerMode: 'fake' | 'real' | null; configuredFingerprint: string; onComplete: () => Promise<void>; onError: (message: string) => void }) {
  const [plan, setPlan] = useState<IndexPlan | null>(null)
  const [acceptance, setAcceptance] = useState<{ plan: AcceptancePlan; scope: Record<string, unknown> } | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const fingerprint = configuredFingerprint || status.fingerprint || ''
  async function preview(mode: 'initial' | 'full' | 'incremental' | 'model_change') {
    if (busyRef.current) return
    if (!fingerprint) { onError('当前索引状态没有可用配置指纹，请先在设置中检查向量化配置。'); return }
    busyRef.current = true
    setBusy(true); setPlan(null); setAcceptance(null); setConfirm(false)
    try {
      const current = await api.post<IndexPlan>('/index/plans', { mode, fingerprint })
      let reviewed: { plan: AcceptancePlan; scope: Record<string, unknown> } | null = null
      if (providerMode === 'real' || mode === 'full' || mode === 'model_change' || (mode === 'incremental' && status.state === 'manual_required')) {
        reviewed = await api.post<{ plan: AcceptancePlan; scope: Record<string, unknown> }>('/acceptance-plans', { operation: 'model.index', scope: { mode: current.mode, fingerprint: current.fingerprint, page_ids: current.page_ids, page_versions: current.page_versions } })
      }
      setPlan(current); setAcceptance(reviewed)
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法生成索引范围预览') }
    finally { busyRef.current = false; setBusy(false) }
  }
  async function execute() {
    if (!plan || busyRef.current) return
    if (providerMode === 'real' && !acceptance) { setConfirm(false); onError('真实索引范围未完成授权预览，请重新预览后再确认。'); return }
    busyRef.current = true
    setBusy(true)
    try {
      if (acceptance) await api.post(`/acceptance-plans/${acceptance.plan.plan_id}/confirm`, { scope_sha256: acceptance.plan.scope_sha256, scope: acceptance.scope })
      await api.post('/index/jobs', { ...plan, ...(acceptance ? { acceptance_plan_id: acceptance.plan.plan_id } : {}) })
      setConfirm(false); setPlan(null); setAcceptance(null); await onComplete()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '索引操作没有完成') }
    finally { busyRef.current = false; setBusy(false) }
  }
  const indexMode: 'initial' | 'incremental' | 'full' | 'model_change' = status.state === 'not_ready' ? 'initial' : status.fingerprint && configuredFingerprint && status.fingerprint !== configuredFingerprint ? 'model_change' : status.state === 'manual_required' ? 'incremental' : status.state === 'stale' ? 'incremental' : 'full'
  return <><div className="index-status-panel"><div><strong className="index-state">当前状态：{status.state === 'ready' ? '可用' : status.state === 'stale' ? '有内容待更新' : status.state === 'manual_required' ? '需要单独确认' : status.state === 'not_ready' ? '尚未建立' : '状态未知'}</strong><p>当前纳入 {status.current_pages} 页 · 待更新 {status.stale_pages} 页 · 共 {status.pages} 页</p></div><button className="button secondary" disabled={busy || !fingerprint || !providerMode} onClick={() => void preview(indexMode)}>{busy ? '正在准备…' : status.state === 'not_ready' ? '预览首次索引' : '预览索引范围'}</button></div>
    {plan && <div className="plan-card"><div><strong>本次范围：{plan.page_ids.length} 页</strong><span>计划类型：{plan.mode === 'initial' ? '首次建立' : plan.mode === 'model_change' ? '模型变更' : plan.mode === 'full' ? '重建' : '增量更新'} · 预计 {plan.estimated_tokens} token</span></div><button className="button primary" onClick={() => setConfirm(true)}>查看范围并确认</button></div>}
    {confirm && plan && <ConfirmDialog title="确认本次索引范围？" description={`将处理 ${plan.page_ids.length} 个页面版本，预计 ${plan.estimated_tokens} token。`} consequence={providerMode === 'real' ? `真实模式会使用已配置的向量化服务；请求上限 ${acceptance?.plan.request_limit ?? '待确认'} 次。` : 'Fake 模式仅使用本机合成索引。'} confirmLabel="确认并开始索引" busyLabel="正在索引…" busy={busy} onCancel={() => { setConfirm(false); setPlan(null); setAcceptance(null) }} onConfirm={execute}><ul>{(plan.page_preview ?? []).map((page, index) => <li key={index}>{page.title ?? '页面'} · {page.version ?? ''}</li>)}</ul></ConfirmDialog>}
  </>
}

function CandidateReview({ candidates, mode }: { candidates: ActionCandidate[]; mode: 'fake' | 'real' | null }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  useEffect(() => { void api.get<Project[]>('/projects').then(setProjects).catch((cause) => setError(cause instanceof Error ? cause.message : '无法读取项目')) }, [])
  return <>{error && <p role="alert">{error} <button className="text-button" onClick={() => { setError(''); void api.get<Project[]>('/projects').then(setProjects).catch((cause) => setError(cause instanceof Error ? cause.message : '无法读取项目')) }}>重试</button></p>}<TasksPanel projects={projects} candidates={candidates} mode={mode} /></>
}

function ActionIntentList({ items, mode, onChanged, onError }: { items: Action[]; mode: 'fake' | 'real' | null; onChanged: () => Promise<void>; onError: (message: string) => void }) {
  const [current, setCurrent] = useState<Action | null>(null)
  const [busy, setBusy] = useState(false)
  async function act(action: Action, operation: 'confirm' | 'execute' | 'reconcile' | 'outcome', evidence?: string, outcome?: 'succeeded' | 'failed') {
    setBusy(true)
    try {
      if (operation === 'confirm') await api.post(`/actions/${action.action_id}/confirmations`, { payload_sha256: action.payload_sha256, confirmation_id: newOperationId() })
      if (operation === 'execute') await api.post(`/actions/${action.action_id}/executions`, { payload_sha256: action.payload_sha256, confirmation_id: action.confirmation_id })
      if (operation === 'reconcile') await api.post(`/actions/${action.action_id}/reconciliations`, {})
      if (operation === 'outcome') await api.post(`/actions/${action.action_id}/outcomes`, { payload_sha256: action.payload_sha256, confirmation_id: newOperationId(), state: outcome, evidence })
      setCurrent(null); await onChanged()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '动作状态未能更新；请刷新记录核对。') }
    finally { setBusy(false) }
  }
  return <>{items.length === 0 ? <div className="empty-state"><strong>没有已保存的外部动作</strong><span>候选建议会单独列在下方。</span></div> : <ul className="action-intent-list">{items.map((action) => <li key={action.action_id}><div><strong>{({ feishu_task_create: '创建飞书任务', feishu_task_update: '编辑飞书任务', feishu_task_complete: '完成飞书任务', project_progress: '更新项目进度' } as Record<string, string>)[action.kind]}</strong><small>{({ proposed: '待确认', confirmed: '已确认，尚未执行', running: '正在执行', succeeded: '已完成', failed: '执行未成功', unknown: '结果未知，请核对' } as Record<string, string>)[action.state]}</small></div><button className="button secondary" onClick={() => setCurrent(action)}>查看与处理</button></li>)}</ul>}{current && <ActionDialog action={current} mode={mode} busy={busy} onCancel={() => setCurrent(null)} onConfirm={() => void act(current, 'confirm')} onExecute={() => void act(current, 'execute')} onReconcile={() => void act(current, 'reconcile')} onOutcome={(evidence, outcome) => void act(current, 'outcome', evidence, outcome)} />}</>
}

function ActionDialog({ action, mode, busy, onCancel, onConfirm, onExecute, onReconcile, onOutcome }: { action: Action; mode: 'fake' | 'real' | null; busy: boolean; onCancel: () => void; onConfirm: () => void; onExecute: () => void; onReconcile: () => void; onOutcome: (evidence: string, state: 'succeeded' | 'failed') => void }) {
  const [evidence, setEvidence] = useState('')
  const [outcome, setOutcome] = useState<'succeeded' | 'failed'>('succeeded')
  const details = readableAction(action)
  if (action.state === 'unknown') return <ConfirmDialog title="核对结果未知的动作" description="只读取远端结果，不会重新发送动作。" confirmLabel="重新核对" busyLabel="正在核对…" busy={busy} onCancel={onCancel} onConfirm={onReconcile}><ActionDetails details={details} /><p>如核对后仍无法确定，请到对应服务查看，再记录明确结果。</p><label className="field"><span>核实结果</span><select value={outcome} onChange={(event) => setOutcome(event.target.value as typeof outcome)}><option value="succeeded">确认已成功</option><option value="failed">确认未成功</option></select></label><label className="field"><span>人工核实依据</span><textarea rows={3} value={evidence} onChange={(event) => setEvidence(event.target.value)} /></label><button className="button secondary" disabled={busy || !evidence.trim()} onClick={() => onOutcome(evidence, outcome)}>独立确认并记录核实结果</button></ConfirmDialog>
  if (action.state === 'proposed') return <ConfirmDialog title="确认这个外部动作？" description="确认仅记录你的意图，动作还不会发送。下一步需要再次独立确认执行。" confirmLabel="确认动作" busyLabel="正在确认…" busy={busy} onCancel={onCancel} onConfirm={onConfirm}><ActionDetails details={details} /><p>动作类别：{action.kind === 'project_progress' ? '本地项目进度' : '飞书任务'}</p></ConfirmDialog>
  if (action.state === 'confirmed') return mode !== 'fake' && action.kind !== 'project_progress' ? <ConfirmDialog title="真实飞书任务写入不可用" description="此应用当前没有真实飞书任务写入能力。动作不会发送；请在飞书中处理。" confirmLabel="知道了" busyLabel="知道了" onCancel={onCancel} onConfirm={onCancel}><ActionDetails details={details} /></ConfirmDialog> : <ConfirmDialog title="执行已确认的动作？" description="执行会按已保存的内容调用对应动作；结果未知时不会自动重发。" confirmLabel="确认并执行" busyLabel="正在执行…" busy={busy} onCancel={onCancel} onConfirm={onExecute}><ActionDetails details={details} /><p>这是确认后的独立执行步骤。</p></ConfirmDialog>
  return <ConfirmDialog title="动作执行记录" description={`当前状态：${action.state}`} confirmLabel="关闭" busyLabel="关闭" onCancel={onCancel} onConfirm={onCancel}><ActionDetails details={details} /></ConfirmDialog>
}

function readableAction(action: Action) {
  const payload = action.payload
  return [
    ['任务标题', payload.summary ?? (payload.task as Record<string, unknown> | undefined)?.summary],
    ['任务说明', payload.description ?? (payload.task as Record<string, unknown> | undefined)?.description],
    ['截止时间', (payload.due as Record<string, unknown> | undefined)?.value],
    ['项目进度', payload.progress],
    ['更新范围', Array.isArray(payload.update_fields) ? payload.update_fields.map((field) => ({ summary: '标题', description: '说明', due: '截止时间' } as Record<string, string>)[String(field)] ?? '其他').join('、') : undefined],
  ].filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1].length > 0)
}

function ActionDetails({ details }: { details: Array<[string, string]> }) {
  return details.length ? <dl className="action-readable-details">{details.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <p>动作正文暂时没有可展示的摘要。</p>
}
