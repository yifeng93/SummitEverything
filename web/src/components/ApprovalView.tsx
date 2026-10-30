import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { FileText, X } from 'lucide-react'
import { api, indexUpdateMessage, type ActionCandidate, type Draft, type IntakeItem, type MutationResult, type Page, type Project, type SourceDetail } from '../api/client'
import type { components } from '../api/generated'
import { draftNeedsAttention, draftStateLabel, intakeNeedsAttention, intakeStateLabel } from '../approval-summary'
import { MarkdownText } from './MarkdownText'
import { DraftReview } from './DraftReview'
import { ConfirmDialog } from './ConfirmDialog'
import { TasksPanel } from './TasksPanel'
import { SourceOrganizer } from './SourceOrganizer'
import { useDialogFocus } from './useDialogFocus'
import { PageHeader } from './PageHeader'
import { newOperationId } from '../api/client'
import type { ApprovalTarget } from '../approvalTarget'
import { SearchReadiness } from './SearchReadiness'

type Action = components['schemas']['Action']
type ActionPage = components['schemas']['ActionPage']
type Resource<T> = { data: T | null; loading: boolean; error: string; lastSuccess: string | null }
type IndexStatus = { state: string; fingerprint: string | null; pages: number; chunks: number; current_pages: number; stale_pages: number }
type IntakeJob = components['schemas']['IntakeJob']
type Props = { onPendingCount: (count: number) => void; onError: (message: string) => void; onOpenPage?: (pageId: string, expectedHash?: string) => void; refreshEpoch?: number; target?: ApprovalTarget | null; onTargetHandled?: () => void; onDirtyChange?: (dirty: boolean) => void; discardEpoch?: number }

const initial = <T,>(): Resource<T> => ({ data: null, loading: true, error: '', lastSuccess: null })
const formalNeedsAttention = (page: Page) => page.approval_state !== 'confirmed'
const actionableAction = (action: Action) => ['proposed', 'confirmed', 'running', 'failed', 'unknown'].includes(action.state)

function organizeResultMessage(state: IntakeJob['state']): string {
  switch (state) {
    case 'failed':
      return '整理没有完成。原来源和已有内容仍然保留；可以选中该来源后点「明确重新整理」。'
    case 'cancelled':
      return '整理已取消，没有生成稿件。'
    case 'unknown':
      return '整理结果待核对，不会自动重发；核对后可再决定是否重新整理。'
    default:
      return '正在处理中。不会重复发起。'
  }
}

function StatePanel<T>({ resource, retry, children }: { resource: Resource<T>; retry: () => void; children: (data: T) => ReactNode }) {
  if (resource.loading && resource.data === null) return <p className="quiet-empty" role="status">正在读取…</p>
  if (resource.error && resource.data === null) return <div className="resource-error" role="alert"><p>{resource.error}</p><button className="button secondary" onClick={retry}>重试</button></div>
  if (resource.data === null) return <p className="quiet-empty" role="status">正在读取…</p>
  return <>{resource.error && <p className="stale-note" role="status">{resource.error}；下方保留上次成功读取的内容。 <button className="text-button" onClick={retry}>重试</button></p>}{children(resource.data)}{resource.loading && <span className="inline-loading" role="status">正在更新…</span>}</>
}

function ApprovalGroup({ id, headingId, title, summary, lastSuccess, hasReadError = false, count, children }: {
  id: string; headingId: string; title: string; summary: string; lastSuccess: string | null; hasReadError?: boolean; count: string | number; children: ReactNode
}) {
  // 五组是并列的待办队列，不是步骤：固定顺序、同等大小，内容多时在卡内滚动。
  return <section className={'panel approval-group' + (Number(count) > 0 ? ' has-pending' : '')} id={id} role="region" aria-label={title}>
    <div className="approval-group-head">
      <div className="approval-group-copy">
        <h2 id={headingId}>{title}</h2>
        {(summary || lastSuccess) && <div className="approval-group-meta">
          {summary && <p>{summary}</p>}
          {lastSuccess && <small>{hasReadError ? '上次成功读取：' : '最近读取：'}{new Date(lastSuccess).toLocaleString('zh-CN')}</small>}
        </div>}
      </div>
      <span className={Number(count) > 0 ? 'count-badge has-items' : 'count-badge'}>{count}</span>
    </div>
    <div className="approval-group-content">
      {children}
    </div>
  </section>
}

function earlierSuccessfulRead(first: string | null, second: string | null): string | null {
  if (!first || !second) return null
  return Date.parse(first) <= Date.parse(second) ? first : second
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
  const [localModelReady, setLocalModelReady] = useState(false)
  const [filter, setFilter] = useState<'all' | 'pending' | 'complete'>('pending')
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
  const sourceDetailRequest = useRef(0)
  const targetRouteRequest = useRef(0)
  const settingsRequest = useRef(0)

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
    setSourceDetail(null); setSourceDetailError(''); setSourceDetailLoading(true); setOrganizeResult(null)
    const requestId = ++sourceDetailRequest.current
    void api.get<SourceDetail>('/sources/' + item.source_id)
      .then((detail) => { if (requestId === sourceDetailRequest.current) setSourceDetail(detail) })
      .catch((cause) => { if (requestId === sourceDetailRequest.current) setSourceDetailError(cause instanceof Error ? cause.message : '无法读取原文') })
      .finally(() => { if (requestId === sourceDetailRequest.current) setSourceDetailLoading(false) })
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
  const refreshSettings = useCallback(async () => {
    const requestId = ++settingsRequest.current
    try {
      const value = await api.get<components['schemas']['SettingsSummary']>('/settings')
      if (requestId === settingsRequest.current) {
        setSettingsMode(value.mode)
        setConfiguredFingerprint(value.embedding_fingerprint)
        setLocalModelReady(value.mode === 'fake' || value.local_model?.state === 'ready')
      }
    } catch {
      if (requestId === settingsRequest.current) {
        setSettingsMode(null); setConfiguredFingerprint(''); setLocalModelReady(false)
      }
    }
  }, [])
  useEffect(() => {
    let current = true
    targetRouteRequest.current += 1
    const refresh = async () => {
      await Promise.resolve()
      if (!current) return
      setSources((value) => ({ ...value, loading: true, error: '' }))
      setDrafts((value) => ({ ...value, loading: true, error: '' }))
      setPages((value) => ({ ...value, loading: true, error: '' }))
      setIndex((value) => ({ ...value, loading: true, error: '' }))
      setCandidates((value) => ({ ...value, loading: true, error: '' }))
      setIntents((value) => ({ ...value, loading: true, error: '' }))
      const refreshResource = async <T,>(setter: React.Dispatch<React.SetStateAction<Resource<T>>>, request: () => Promise<T>) => {
        try {
          const data = await request()
          if (current) setter({ data, loading: false, error: '', lastSuccess: new Date().toISOString() })
        } catch (cause) {
          if (current) setter((value) => ({ ...value, loading: false, error: cause instanceof Error ? cause.message : '读取失败，请重试。' }))
        }
      }
      await Promise.all([
        refreshResource(setSources, () => api.get<IntakeItem[]>('/intake/items')),
        refreshResource(setDrafts, () => api.get<Draft[]>('/drafts')),
        refreshResource(setPages, async () => (await api.get<Page[]>('/pages')).filter((page) => page.storage_area === 'formal')),
        refreshResource(setIndex, () => api.get<IndexStatus>('/index/status')),
        refreshResource(setCandidates, () => api.get<ActionCandidate[]>('/actions')),
        refreshResource(setIntents, () => api.get<ActionPage>('/action-intents?limit=20')),
        refreshSettings(),
      ])
      if (!current) return
      setLoadedEpoch(refreshEpoch)
    }
    void refresh()
    return () => { current = false; settingsRequest.current += 1 }
  }, [refreshEpoch, refreshSettings])

  const pendingSources = sources.data?.filter(intakeNeedsAttention) ?? []
  const pendingDraftList = drafts.data?.filter(draftNeedsAttention) ?? []
  const pendingPages = pages.data?.filter(formalNeedsAttention) ?? []
  const pendingActions = intents.data?.items.filter(actionableAction) ?? []
  const confirmedPageCount = pages.data?.filter((page) => page.approval_state === 'confirmed').length ?? null
  const indexContextKey = JSON.stringify({
    state: index.data?.state,
    fingerprint: index.data?.fingerprint,
    currentPages: index.data?.current_pages,
    stalePages: index.data?.stale_pages,
    mode: settingsMode,
    configuredFingerprint,
    confirmedPages: pages.data?.filter((page) => page.approval_state === 'confirmed').map((page) => [page.page_id, page.content_sha256]),
  })
  const pendingIndex = index.data && (
    index.data.state === 'stale' || index.data.state === 'manual_required'
      || index.data.state === 'not_ready' && confirmedPageCount !== null && confirmedPageCount > 0
      || index.data.state === 'ready' && Boolean(configuredFingerprint && index.data.fingerprint && configuredFingerprint !== index.data.fingerprint)
  ) ? 1 : 0
  const needsCount = pendingSources.length + pendingDraftList.length + pendingPages.length + pendingIndex + pendingActions.length + (candidates.data?.length ?? 0)
  const pendingCategoryCount = [pendingSources.length, pendingDraftList.length, pendingPages.length, pendingIndex, pendingActions.length + (candidates.data?.length ?? 0)].filter((count) => count > 0).length
  const categoryCount = [sources.data, drafts.data, pages.data, index.data, intents.data !== null && candidates.data !== null ? true : null].filter((data) => data !== null).length
  const dataComplete = categoryCount === 5
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
  // 来源详情走弹层，清单保持可见；稿件与正式内容仍然是独立专注页。
  const focused = Boolean(activeDraft || activePage)
  const sourceDialogRef = useDialogFocus(closeFocus, Boolean(activeSourceItem))

  // Resolve exact-ID navigation only after the refreshed collections are available.
  useEffect(() => {
    if (!target) return
    if (loadedEpoch < refreshEpoch) return
    let current = true
    const routeId = ++targetRouteRequest.current
    sourceDetailRequest.current += 1
    const route = async () => {
      await Promise.resolve()
      if (!current || routeId !== targetRouteRequest.current) return
      let message: string
      let element: HTMLElement | null = null
      let sourceToLoad: IntakeItem | null = null
      if (target.kind === 'source') {
        if (!sources.data || !drafts.data) return
        const source = sources.data.find((item) => target.itemIds.includes(item.item_id))
        if (!source) message = '这条材料已不在当前工作库中。请刷新来源列表后重新选择。'
        else {
          const related = source.state === 'reviewing' ? drafts.data.find((draft) => draft.source_ids.includes(source.source_id)) : null
          if (related) {
            setActiveDraft(related.draft_id); setActiveSource(null); setActivePage(null)
            element = findByData('draftId', related.draft_id)
            message = '这条材料已有待审核稿，已打开现有稿件。'
          } else {
            setActiveSource(source.item_id); setActiveDraft(null); setActivePage(null)
            setSourceDetail(null); setSourceDetailError(''); setSourceDetailLoading(true); setOrganizeResult(null)
            sourceToLoad = source
            message = target.itemIds.length > 1 ? `已定位到本次成功保存的 ${target.itemIds.length} 项材料。选择归属后可继续整理。` : source.state === 'processing' ? '这条材料正在整理中，不会重复发起。' : source.state === 'completed' ? '这条材料已完成整理。' : '已定位到本次保存的材料。选择归属后可继续整理。'
          }
        }
      } else if (target.kind === 'draft') {
        if (!drafts.data) return
        const draft = drafts.data.find((item) => target.draftIds.includes(item.draft_id))
        if (draft) { setActiveDraft(draft.draft_id); setActiveSource(null); setActivePage(null); message = '已打开本次整理生成的稿件。' }
        else message = '这份稿件已不在当前待审核列表中，请刷新后重新选择。'
      } else {
        if (!pages.data) return
        const page = pages.data.find((item) => target.pageIds.includes(item.page_id))
        if (page) { setActivePage(page.page_id); setActiveDraft(null); setActiveSource(null); message = '已定位到这次整理生成的正式页面。' }
        else message = '这份正式页面已不在当前工作库中，请刷新后重新选择。'
      }
      if (!current) return
      setNotice(message)
      if (sourceToLoad) {
        const requestId = ++sourceDetailRequest.current
        void api.get<SourceDetail>('/sources/' + sourceToLoad.source_id)
          .then((detail) => { if (requestId === sourceDetailRequest.current) setSourceDetail(detail) })
          .catch((cause) => { if (requestId === sourceDetailRequest.current) setSourceDetailError(cause instanceof Error ? cause.message : '无法读取原文') })
          .finally(() => { if (requestId === sourceDetailRequest.current) setSourceDetailLoading(false) })
      }
      requestAnimationFrame(() => {
        if (routeId !== targetRouteRequest.current) return
        const targetElement = element ?? document.querySelector<HTMLElement>('.source-focus, .draft-focus, .formal-focus')
        targetElement?.scrollIntoView?.({ block: 'center' }); targetElement?.focus({ preventScroll: true })
      })
      onTargetHandled?.()
    }
    void route()
    return () => { current = false }
  }, [target, sources.data, drafts.data, pages.data, loadedEpoch, refreshEpoch, onTargetHandled])

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
    <PageHeader title="审批" />
    <div className="toolbar approval-toolbar" hidden={focused}>
      <p className="hint" role="status">{!dataComplete ? `正在读取审批事项…（${categoryCount} / 5 类已读）` : filter === 'pending' ? `${needsCount} 项待处理 · 共 ${pendingCategoryCount} 类` : filter === 'complete' ? `${visibleSources.length + visibleDrafts.length + visiblePages.length + (intents.data?.items.filter((action) => !actionableAction(action)).length ?? 0)} 项已完成` : '显示全部事项'}</p>
      <div className="segmented" role="group" aria-label="显示范围">
        {([['pending', '待处理'], ['all', '全部'], ['complete', '已完成']] as const).map(([value, label]) => <button key={value} type="button" className={filter === value ? 'active' : ''} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}
      </div>
    </div>
    {notice && <p className="success-note" role="status">{notice}</p>}

    <div className="approval-list" role="region" aria-label="审批清单" hidden={focused}>
    <ApprovalGroup id="approval-sources" headingId="approval-sources-heading" title="来源" summary="待整理成稿的材料" lastSuccess={sources.lastSuccess} hasReadError={Boolean(sources.error)} count={sources.data ? visibleSources.length : '—'}>
      <StatePanel resource={sources} retry={() => void refreshSources()}>{() => <><SourceList items={visibleSources} targetIds={target?.kind === 'source' ? target.itemIds : []} onOpenSource={openSourceFocus} /></>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-drafts" headingId="approval-drafts-heading" title="稿件" summary="待复核的整理结果" lastSuccess={drafts.lastSuccess} hasReadError={Boolean(drafts.error)} count={drafts.data ? visibleDrafts.length : '—'}>
      <StatePanel resource={drafts} retry={() => void refreshDrafts()}>{() => visibleDrafts.length === 0 ? <div className="empty-state"><strong>{filter === 'complete' ? '没有已完成的稿件' : '没有待复核的稿件'}</strong><span>整理来源后会生成稿件。</span></div> : <>
        <ul className="draft-list">{visibleDrafts.map((draft) => <li key={draft.draft_id} data-draft-id={draft.draft_id} tabIndex={-1}><div className="approval-row"><span className="source-title"><strong>{String(draft.metadata.title ?? '未命名稿件')}</strong><small>{draft.source_ids.length} 个来源 · {draft.important_conflicts?.length ?? 0} 项重要冲突</small></span><button type="button" className="button secondary" onClick={(event) => openDraftFocus(draft.draft_id, event.currentTarget)}>打开稿件：{String(draft.metadata.title ?? '未命名稿件')}</button></div></li>)}</ul>
      </>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-formal" headingId="approval-formal-heading" title="正式内容" summary="待确认的页面版本" lastSuccess={pages.lastSuccess} hasReadError={Boolean(pages.error)} count={pages.data ? visiblePages.length : '—'}>
      <StatePanel resource={pages} retry={() => void refreshPages()}>{() => visiblePages.length === 0 ? <div className="empty-state"><strong>没有待确认的正式内容</strong><span>稿件确认后会出现在这里。</span></div> : <ul className="knowledge-page-list">{visiblePages.map((page) => <li key={page.page_id} data-page-id={page.page_id} tabIndex={-1}><div className="formal-page-row"><button className="formal-open-button" onClick={(event) => openPageFocus(page.page_id, event.currentTarget)}><strong>{String(page.metadata.title ?? '未命名页面')}</strong><small>{formalKindLabel(String(page.metadata.kind ?? ''))} · {page.approval_state === 'invalid' ? '需要重新确认' : '待确认'}</small></button><button className="button secondary" onClick={() => setConfirmPage(page)}>确认并保存当前版本</button></div></li>)}</ul>}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-index" headingId="approval-index-heading" title="搜索与问答准备" summary="" lastSuccess={index.lastSuccess} hasReadError={Boolean(index.error)} count={index.data ? (filter === 'complete' ? 0 : !settingsMode || !configuredFingerprint || index.data.state === 'unknown' || index.data.state === 'not_ready' && confirmedPageCount === null ? '—' : pendingIndex ? 1 : 0) : '—'}>
      <StatePanel resource={index} retry={() => { void refreshIndex(); void refreshPages(); void refreshSettings() }}>{(status) => <SearchReadiness key={indexContextKey} status={status} confirmedPageCount={confirmedPageCount} confirmedPagesLoading={pages.loading} confirmedPagesError={pages.data === null ? pages.error : ''} providerMode={settingsMode} configuredFingerprint={configuredFingerprint} localModelReady={localModelReady} onComplete={async () => { await refreshIndex(); setNotice('搜索和问答准备已返回结果。') }} onRefresh={() => { void refreshIndex(); void refreshPages(); void refreshSettings() }} onError={onError} />}</StatePanel>
    </ApprovalGroup>

    <ApprovalGroup id="approval-actions" headingId="approval-actions-heading" title="外部动作" summary="待确认或待核对的外部动作" lastSuccess={earlierSuccessfulRead(intents.lastSuccess, candidates.lastSuccess)} hasReadError={Boolean(intents.error || candidates.error)} count={intents.data && candidates.data ? visibleIntents.length + visibleCandidates.length : '—'}>
      {intents.data && candidates.data && visibleIntents.length === 0 && visibleCandidates.length === 0
        ? <div className="empty-state"><strong>没有待处理的外部动作</strong><span>模型建议会先出现在这里，确认后才会执行。</span></div>
        : <>
          <StatePanel resource={intents} retry={() => void refreshIntents()}>{() => <ActionIntentList items={visibleIntents} mode={settingsMode} onChanged={async () => { await Promise.allSettled([refreshIntents(), refreshCandidates()]) }} onError={onError} />}</StatePanel>
          {intents.data?.next_cursor && <button type="button" className="button secondary" disabled={intents.loading} onClick={() => void loadMoreActions()}>读取更多动作</button>}
          {visibleCandidates.length > 0 && <div className="action-candidate-panel"><h3>尚未转成动作的建议</h3><StatePanel resource={candidates} retry={() => void refreshCandidates()}>{() => <CandidateReview candidates={visibleCandidates} mode={settingsMode} />}</StatePanel></div>}
        </>}
    </ApprovalGroup>
    </div>

    {active && <section className="panel draft-focus" aria-label={`稿件审核：${String(active.metadata.title ?? '未命名稿件')}`} tabIndex={-1}>
      <div className="focus-toolbar"><button className="button secondary" onClick={closeFocus}>返回审批清单</button><span>{active.state === 'pending' ? '正在审核一份稿件' : draftStateLabel(active.state)}</span></div>
      {draftResult?.draftId === active.draft_id ? <section className="formal-result" aria-label="稿件确认结果"><p>“{String(active.metadata.title ?? '未命名稿件')}”已确认并写入正式内容。{draftResult.indexMessage}</p>{draftResult.pageIds.length > 0 && <ul>{draftResult.pageIds.map((id) => <li key={id}><button className="button secondary" onClick={() => onOpenPage?.(id)}>打开本次保存的正式页</button></li>)}</ul>}<div className="button-row"><button className="button secondary" disabled={!visibleDrafts.some((draft) => draft.draft_id !== active.draft_id)} onClick={() => { const next = visibleDrafts.find((draft) => draft.draft_id !== active.draft_id); if (next) { setDraftResult(null); setActiveDraft(next.draft_id) } }}>下一份待审核</button><button className="button primary" onClick={closeFocus}>返回清单</button></div></section> : <DraftReview key={active.draft_id} draft={active} pages={pages.data ?? []} onError={onError} onDirtyChange={setDraftDirty} onConfirmed={async (result) => { const indexMessage = indexUpdateMessage(result.index_update); setDraftDirty(false); setDraftResult({ draftId: active.draft_id, pageIds: Object.keys(result.page_versions ?? {}), indexMessage }); await Promise.allSettled([refreshDrafts(), refreshPages(), refreshIndex(), refreshCandidates()]); setNotice(indexMessage ?? '稿件已确认并写入正式内容。') }} onUpdated={async () => { await refreshDrafts() }} />}
    </section>}
    {activeSourceItem && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeFocus() }}>
      <section ref={sourceDialogRef} className="modal-card source-modal" role="dialog" aria-modal="true" aria-label={`来源详情：${activeSourceItem.title}`} tabIndex={-1}>
        <div className="panel-heading">
          <div>
            <h2>{activeSourceItem.title}</h2>
            <p className="source-focus-meta">{activeSourceItem.filename} · {activeSourceItem.created_at ? new Date(activeSourceItem.created_at).toLocaleString('zh-CN') : ''} · {intakeStateLabel(activeSourceItem.state)}</p>
          </div>
          <button className="icon-button modal-close" aria-label="关闭" title="关闭" onClick={closeFocus}><X size={16} strokeWidth={1.75} aria-hidden="true" /></button>
        </div>
        <div className="source-modal-body">
          {sourceDetailLoading
            ? <p role="status" className="empty-row">正在读取原文…</p>
            : sourceDetailError
              ? <div className="resource-error" role="alert"><p>{sourceDetailError}</p><button className="button secondary" onClick={() => openSourceFocus(activeSourceItem, document.activeElement as HTMLElement)}>重试</button></div>
              : sourceDetail && <article className="source-reading-body"><MarkdownText content={sourceDetail.text} /></article>}
        </div>
        <div className="source-modal-foot">
          {activeSourceItem.state === 'processing' || activeSourceItem.state === 'reviewing'
            ? <><p className="helper-line">这条材料已有整理任务或稿件，不会再次发起整理。</p>{organizeResult && <button className="button secondary" onClick={() => void refreshOrganizeResult()}>刷新整理结果</button>}</>
            : <SourceOrganizer items={[activeSourceItem]} onError={(message) => { onError(message); void refreshSources() }} onComplete={async (job) => { setOrganizeResult(job); await Promise.allSettled([refreshSources(), refreshDrafts()]) }} />}
          {!organizeResult && (activeSourceItem.state === 'reviewing' || activeSourceItem.state === 'completed') && <StatePanel resource={drafts} retry={() => void refreshDrafts()}>{(allDrafts) => {
            const linkedDrafts = allDrafts.filter((draft) => draft.source_ids.includes(activeSourceItem.source_id))
            return <section className="organize-result" aria-label="关联稿件">
              <h3>关联稿件</h3>
              {linkedDrafts.length === 0
                ? <p className="helper-line">当前没有可打开的关联稿件。</p>
                : <ul>{linkedDrafts.map((draft) => {
                  const stateLabel = draftStateLabel(draft.state)
                  const actionLabel = draft.state === 'pending' ? '打开这份稿件' : `查看${stateLabel}稿件`
                  return <li key={draft.draft_id}><span>{String(draft.metadata.title ?? '未命名稿件')} · {stateLabel}</span><button className="button secondary" onClick={(event) => openDraftFocus(draft.draft_id, event.currentTarget)}>{actionLabel}</button></li>
                })}</ul>}
            </section>
          }}</StatePanel>}
          {organizeResult && <section className="organize-result" aria-label="本次整理结果"><h3>本次整理结果</h3>{organizeResult.state === 'completed' ? <><p>已完成，生成 {organizeResult.draft_ids?.length ?? 0} 份待审核稿。</p>{organizeResult.draft_ids?.length ? <ul>{organizeResult.draft_ids.map((id) => { const draft = drafts.data?.find((item) => item.draft_id === id); return <li key={id}><span>{draft ? String(draft.metadata.title ?? '未命名稿件') : '稿件载入中'}</span>{draft && <button className="button secondary" onClick={(event) => openDraftFocus(id, event.currentTarget)}>打开这份稿件</button>}</li> })}</ul> : null}</> : <><p>{organizeResultMessage(organizeResult.state)}</p><button className="button secondary" onClick={() => void refreshOrganizeResult()}>刷新整理结果</button></>}</section>}
        </div>
      </section>
    </div>}
    {activeFormalPage && <section className="panel formal-focus" aria-label={`正式内容：${String(activeFormalPage.metadata.title ?? '未命名页面')}`} tabIndex={-1}>
      <div className="focus-toolbar"><button className="button secondary" onClick={closeFocus}>返回审批清单</button><span>{activeFormalPage.approval_state === 'confirmed' ? '已确认' : '待确认'}</span></div>
      <h2>{String(activeFormalPage.metadata.title ?? '未命名页面')}</h2>
      <p className="source-focus-meta">{formalKindLabel(String(activeFormalPage.metadata.kind ?? ''))}</p>
      <article className="formal-reading-body"><MarkdownText content={activeFormalPage.body} onOpenPage={onOpenPage} /></article>
      {formalResult?.pageId === activeFormalPage.page_id && <div className="formal-result" role="status"><p>“{formalResult.title}”已保存为当前正式版本。{formalResult.indexMessage}</p><div className="button-row"><button className="button secondary" onClick={() => onOpenPage?.(activeFormalPage.page_id, activeFormalPage.content_sha256)}>打开正式页</button><button className="button secondary" disabled={!visiblePages.some((page) => page.page_id !== activeFormalPage.page_id)} onClick={() => { const next = visiblePages.find((page) => page.page_id !== activeFormalPage.page_id); if (next) { setFormalResult(null); setActivePage(next.page_id) } }}>下一份待确认</button></div></div>}
      {activeFormalPage.approval_state !== 'confirmed' && <button className="button primary" onClick={() => setConfirmPage(activeFormalPage)}>确认并保存当前版本</button>}
    </section>}

    {confirmPage && <ConfirmDialog title="确认并保存当前正式版本？" description={`“${String(confirmPage.metadata.title ?? '未命名页面')}”的正文和页面信息将按当前版本写入正式内容。`} consequence="只确认当前版本；不会创建飞书任务或改变项目进度。索引按当前真实本机模型与审批规则处理。" confirmLabel="确认并保存当前版本" busyLabel="正在保存…" busy={busy} onCancel={() => setConfirmPage(null)} onConfirm={confirmFormal}><MarkdownText content={confirmPage.body} onOpenPage={onOpenPage} /></ConfirmDialog>}
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

function SourceList({ items, targetIds, onOpenSource }: { items: IntakeItem[]; targetIds: string[]; onOpenSource: (item: IntakeItem, trigger: HTMLElement) => void }) {
  if (items.length === 0) return <div className="empty-state"><strong>没有待整理的来源</strong><span>记一句或导入材料后会出现在这里。</span></div>
  // 整行就是入口：点开弹层看原文并整理，不用先勾选再找按钮。
  return <ul className="source-list">{items.map((item) => <li key={item.item_id} data-item-id={item.item_id} tabIndex={-1} className={targetIds.includes(item.item_id) ? 'approval-target' : ''}><button type="button" className="source-row" onClick={(event) => onOpenSource(item, event.currentTarget)}><span className="file-glyph" aria-hidden="true"><FileText size={14} strokeWidth={1.75} /></span><span className="source-title"><strong>{item.title}</strong><small>{({ quick_note: '记一句', file: '文件', feishu_material: '飞书材料', unknown: '来源类型未知' } as Record<string, string>)[item.origin_kind ?? 'unknown']} · {item.filename} · {new Date(item.created_at).toLocaleDateString('zh-CN')}</small></span><span className="status-label">{intakeStateLabel(item.state)}</span></button></li>)}</ul>
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
  return <>{items.length === 0 ? <div className="empty-state"><strong>没有已保存的外部动作</strong><span>确认后的动作会出现在这里。</span></div> : <ul className="action-intent-list">{items.map((action) => <li key={action.action_id}><div><strong>{({ feishu_task_create: '创建飞书任务', feishu_task_update: '编辑飞书任务', feishu_task_complete: '完成飞书任务', project_progress: '更新项目进度' } as Record<string, string>)[action.kind]}</strong><small>{({ proposed: '待确认', confirmed: '已确认，尚未执行', running: '正在执行', succeeded: '已完成', failed: '执行未成功', unknown: '结果未知，请核对' } as Record<string, string>)[action.state]}</small></div><button className="button secondary" onClick={() => setCurrent(action)}>查看与处理</button></li>)}</ul>}{current && <ActionDialog action={current} mode={mode} busy={busy} onCancel={() => setCurrent(null)} onConfirm={() => void act(current, 'confirm')} onExecute={() => void act(current, 'execute')} onReconcile={() => void act(current, 'reconcile')} onOutcome={(evidence, outcome) => void act(current, 'outcome', evidence, outcome)} />}</>
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
