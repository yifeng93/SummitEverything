import { useCallback, useEffect, useImperativeHandle, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from 'react'
import { ArrowLeft, BookOpen, ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Plus } from 'lucide-react'
import { ApiError, api, indexUpdateMessage, newOperationId, type IndexStatus, type Line, type MutationResult, type Page, type PageDirectoryEntry, type Project } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import { ImportDrawer } from './ImportDrawer'
import { JournalDialog } from './JournalDialog'
import { PageHeader } from './PageHeader'
import { PageReader } from './PageReader'
import { MarkdownText } from './MarkdownText'
import { buildPageTree, findPageTrail, type PageTreeNode } from '../page-groups'
import type { ToastKind } from '../toast'

type Props = {
  onError: (message: string, kind?: ToastKind) => void
  onOpenPage: (id: string, hash?: string) => void
  /** 侧栏二级入口点某个项目：loaded 后按准确 id 打开详情。 */
  target?: { id: string; nonce: number } | null
  /** 一级导航「项目」用：立即退回列表，不走 effect，避免与行点击抢时序。 */
  handleRef?: { current: { showList: () => void } | null }
  onTargetHandled?: () => void
  /** 报告当前打开的项目，供侧栏高亮；回到列表时为 null。 */
  onActiveProjectChange?: (projectId: string | null) => void
  /** 项目新建/重命名/归档后通知外壳刷新侧栏。 */
  onProjectsChanged?: () => void
}

export function ProjectsView({ onError, onOpenPage, target = null, onTargetHandled, onActiveProjectChange, onProjectsChanged, handleRef }: Props) {
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<PageDirectoryEntry[]>([])
  const [pageDirectoryRevision, setPageDirectoryRevision] = useState(0)
  const [overviewPage, setOverviewPage] = useState<Page | undefined>()
  const [overviewLoadState, setOverviewLoadState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [overviewRequestProjectId, setOverviewRequestProjectId] = useState('')
  const [pagesState, setPagesState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [indexState, setIndexState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [lineId, setLineId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [lineName, setLineName] = useState('')
  const [projectName, setProjectName] = useState('')
  const [overviewTitle, setOverviewTitle] = useState('')
  const [overviewBody, setOverviewBody] = useState('')
  const [editingOverview, setEditingOverview] = useState(false)
  const [editingLine, setEditingLine] = useState(false)
  const [editingProject, setEditingProject] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [projectStatus, setProjectStatus] = useState<'all' | 'in_progress' | 'needs_setup' | 'archived'>('all')
  const [lineFilter, setLineFilter] = useState('')
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [showCreateLine, setShowCreateLine] = useState(false)
  const [showArchived, setShowArchived] = useState(false)
  const [confirmAction, setConfirmAction] = useState<{ title: string; description: string; label: string; run: () => Promise<void> } | null>(null)
  const [showJournal, setShowJournal] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [busy, setBusy] = useState(false)
  const [overviewNotice, setOverviewNotice] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState('')
  const pendingOverview = useRef<{ signature: string; operation: string } | null>(null)
  const refreshRun = useRef(0)
  const auxiliaryRun = useRef(0)
  const refreshController = useRef<AbortController | null>(null)
  const auxiliaryController = useRef<AbortController | null>(null)
  const overviewRun = useRef(0)
  const overviewController = useRef<AbortController | null>(null)
  const detailScrollTop = useRef(0)
  const lastOpenedProjectId = useRef('')

  // 一级导航「项目」：同步关掉详情，避免和行点击抢时序（effect 会晚一拍）。
  useImperativeHandle(handleRef, () => ({ showList: () => { setDetailOpen(false); setEditingOverview(false); setProjectId('') } }))

  const loadAuxiliary = useCallback(async () => {
    const run = ++auxiliaryRun.current
    auxiliaryController.current?.abort()
    const controller = new AbortController()
    auxiliaryController.current = controller
    const timer = window.setTimeout(() => controller.abort(), 5000)
    setPagesState('loading')
    setIndexState('loading')
    const pagesLoad = api.get<PageDirectoryEntry[]>('/pages/directory', { signal: controller.signal }).then((items) => {
      if (run === auxiliaryRun.current) {
        setPages(items.filter((page) => page.storage_area === 'formal'))
        setPagesState('ready')
        setPageDirectoryRevision((revision) => revision + 1)
      }
    }).catch(() => { if (run === auxiliaryRun.current) setPagesState('error') })
    const indexLoad = api.get<IndexStatus>('/index/status', { signal: controller.signal }).then((value) => {
      if (run === auxiliaryRun.current) { setIndexStatus(value); setIndexState('ready') }
    }).catch(() => { if (run === auxiliaryRun.current) { setIndexStatus(null); setIndexState('error') } })
    await Promise.all([pagesLoad, indexLoad])
    window.clearTimeout(timer)
  }, [])

  const refresh = useCallback(async () => {
    const run = ++refreshRun.current
    refreshController.current?.abort()
    const controller = new AbortController()
    refreshController.current = controller
    const timer = window.setTimeout(() => controller.abort(), 5000)
    try {
      const [nextLines, nextProjects] = await Promise.all([
        api.get<Line[]>('/lines', { signal: controller.signal }),
        api.get<Project[]>('/projects', { signal: controller.signal }),
      ])
      if (run !== refreshRun.current) return
      setLines(nextLines)
      setProjects(nextProjects)
      setLoaded(true)
      setLoadError('')
      onError('')
      onProjectsChanged?.()
      void loadAuxiliary()
    } catch (cause) {
      if (run !== refreshRun.current) return
      const message = controller.signal.aborted
        ? '项目目录读取超时，请重试。'
        : cause instanceof ApiError ? cause.message : '无法加载项目目录，请重试。'
      setLoaded(true)
      setLoadError(message)
      onError(message)
    } finally {
      window.clearTimeout(timer)
    }
  }, [loadAuxiliary, onError, onProjectsChanged])

  useEffect(() => {
    void refresh()
    return () => { refreshRun.current += 1; auxiliaryRun.current += 1; overviewRun.current += 1; refreshController.current?.abort(); auxiliaryController.current?.abort(); overviewController.current?.abort() }
  }, [refresh])

  async function createLine(event: FormEvent) {
    event.preventDefault()
    if (!lineName.trim()) return
    setBusy(true)
    try {
      const line = await api.post<Line>('/lines', { name: lineName, operation_id: newOperationId() })
      setLineName('')
      setLineId(line.id)
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法创建主线')
    } finally { setBusy(false) }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault()
    const selectedLineId = lineId || lines[0]?.id || ''
    if (!projectName.trim() || !selectedLineId) return
    setBusy(true)
    try {
      const project = await api.post<Project>('/projects', {
        line_id: selectedLineId,
        name: projectName,
        operation_id: newOperationId(),
      })
      setProjectName('')
      setProjectId(project.id)
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法创建项目')
    } finally { setBusy(false) }
  }

  async function saveLineName(event: FormEvent) {
    event.preventDefault()
    if (!selectedLine || !lineName.trim()) return
    await mutate(`/lines/${selectedLine.id}`, () => api.patch(`/lines/${selectedLine.id}`, { name: lineName.trim(), operation_id: newOperationId() }))
    setEditingLine(false)
    setLineName('')
  }

  async function saveProjectName(event: FormEvent) {
    event.preventDefault()
    const selected = projects.find((project) => project.id === selectedProjectId)
    if (!selected || !projectName.trim()) return
    await mutate(`/projects/${selected.id}`, () => api.patch(`/projects/${selected.id}`, { name: projectName.trim(), operation_id: newOperationId() }))
    setEditingProject(false)
    setProjectName('')
  }

  async function mutate(_path: string, action: () => Promise<unknown>) {
    setBusy(true)
    try { await action(); await refresh() }
    catch (cause) { onError(cause instanceof Error ? cause.message : '无法更新目录') }
    finally { setBusy(false) }
  }

  const selectedLineId = lineId || lines[0]?.id || ''
  const selectedLine = lines.find((line) => line.id === selectedLineId)
  const lineProjects = projects.filter((project) => !lineFilter || project.line_id === lineFilter)
  function projectStatusOf(project: Project): '在推进' | '待建档' | '已归档' | null {
    if (project.archived) return '已归档'
    if (pagesState !== 'ready') return null
    const confirmedOverview = pages.some((page) => page.page_id === project.overview_id && page.approval_state === 'confirmed')
    return confirmedOverview || Boolean(project.progress?.trim()) ? '在推进' : '待建档'
  }
  const projectRows = lineProjects.filter((project) => {
    const status = projectStatusOf(project)
    if (projectStatus !== 'all' && status !== ({ in_progress: '在推进', needs_setup: '待建档', archived: '已归档' } as const)[projectStatus]) return false
    const needle = search.trim().toLocaleLowerCase()
    return !needle || project.name.toLocaleLowerCase().includes(needle)
  }).sort((a, b) => ['在推进', '待建档', '已归档'].indexOf(projectStatusOf(a)) - ['在推进', '待建档', '已归档'].indexOf(projectStatusOf(b)) || a.name.localeCompare(b.name, 'zh-CN'))
  const visibleProjectRows = projectRows.filter((project) => !project.archived)
  const archivedProjectRows = projectRows.filter((project) => project.archived)
  const selectedProjectId = projectId || projectRows[0]?.id || ''
  const selectedProject = projects.find((project) => project.id === selectedProjectId)
  const overview = selectedProject ? (overviewPage?.page_id === selectedProject.overview_id ? overviewPage : undefined) : undefined

  const loadOverview = useCallback(async (project: Project) => {
    const run = ++overviewRun.current
    overviewController.current?.abort()
    const controller = new AbortController()
    overviewController.current = controller
    const timer = window.setTimeout(() => controller.abort(), 5000)
    setOverviewRequestProjectId(project.id)
    setOverviewLoadState('loading')
    try {
      const page = await api.get<Page>(`/pages/${project.overview_id}`, { signal: controller.signal })
      if (run === overviewRun.current) { setOverviewPage(page); setOverviewLoadState('ready') }
    } catch (cause) {
      if (run === overviewRun.current) {
        setOverviewPage(undefined)
        setOverviewLoadState(cause instanceof ApiError && cause.status === 404 ? 'ready' : 'error')
      }
    } finally {
      window.clearTimeout(timer)
    }
  }, [])
  useEffect(() => {
    if (!detailOpen || !selectedProject) { overviewRun.current += 1; overviewController.current?.abort(); setOverviewPage(undefined); setOverviewLoadState('idle'); return }
    void loadOverview(selectedProject)
  }, [detailOpen, selectedProject?.id, selectedProject?.overview_id, loadOverview])

  // 把「当前打开的是哪个项目」告诉外壳，侧栏二级入口据此高亮；回到列表时清空。
  useEffect(() => {
    onActiveProjectChange?.(detailOpen && selectedProject ? selectedProject.id : null)
  }, [detailOpen, selectedProject, onActiveProjectChange])

  async function doConfirmedAction() {
    if (!confirmAction) return
    await mutate('', confirmAction.run)
    setConfirmAction(null)
  }

  const openProject = useCallback((project: Project) => {
    detailScrollTop.current = window.scrollY
    lastOpenedProjectId.current = project.id
    setProjectId(project.id)
    setEditingProject(false)
    setDetailOpen(true)
  }, [])

  // 侧栏二级入口：等目录读取完成后按准确 id 打开；找不到就结束这次跳转，不猜。
  useEffect(() => {
    if (!loaded || !target) return
    const destination = projects.find((project) => project.id === target.id)
    if (destination) openProject(destination)
    onTargetHandled?.()
  }, [loaded, target, projects, onTargetHandled, openProject])

  function returnToProjectList() {
    const projectIdToFocus = lastOpenedProjectId.current
    setShowArchived(projects.some((project) => project.id === projectIdToFocus && project.archived))
    setDetailOpen(false)
    setEditingOverview(false)
    requestAnimationFrame(() => {
      document.documentElement.scrollTop = detailScrollTop.current
      document.body.scrollTop = detailScrollTop.current
      const trigger = Array.from(document.querySelectorAll<HTMLElement>('[data-project-id]')).find((element) => element.dataset.projectId === projectIdToFocus)
      ;(trigger ?? document.querySelector<HTMLElement>('#project-search'))?.focus({ preventScroll: true })
    })
  }

  async function saveOverview(event: FormEvent) {
    event.preventDefault()
    if (!selectedProject || !overviewTitle.trim() || !overviewBody.trim()) return
    const signature = JSON.stringify([selectedProject.id, overviewTitle.trim(), overviewBody, overview?.content_sha256 ?? null])
    if (pendingOverview.current?.signature !== signature) pendingOverview.current = { signature, operation: newOperationId() }
    setBusy(true)
    try {
      const result = await api.post<MutationResult>(`/projects/${selectedProject.id}/overview/confirmations`, {
        title: overviewTitle.trim(), body: overviewBody, confirmation_id: pendingOverview.current.operation,
        operation_id: pendingOverview.current.operation, expected_content_sha256: overview?.content_sha256 ?? null,
      })
      setOverviewNotice(indexUpdateMessage(result.index_update) ?? '')
      pendingOverview.current = null
      setEditingOverview(false)
      await refresh()
      await loadOverview(selectedProject)
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'version_conflict') {
        setOverviewNotice('概览已在其他位置更新；当前编辑内容未覆盖新版本。请取消后重新打开概览，再检查和编辑。')
      } else onError(cause instanceof Error ? cause.message : '无法保存项目概览')
    }
    finally { setBusy(false) }
  }

  if (detailOpen && selectedProject) return <ProjectDetailView
    line={lines.find((line) => line.id === selectedProject.line_id)}
    project={selectedProject}
    pages={pages.filter((candidate) => String(candidate.metadata.project_id ?? '') === selectedProject.id)}
    library={{ pages, projects: projects.filter((project) => !project.archived) }}
    onReloadPages={async () => { await refresh(); if (selectedProject) await loadOverview(selectedProject) }}
    overview={overview}
    status={projectStatusOf(selectedProject)}
    pagesState={pagesState}
    onRetryPages={loadAuxiliary}
    overviewLoadState={overviewRequestProjectId === selectedProject.id ? overviewLoadState : 'loading'}
    pageDirectoryRevision={pageDirectoryRevision}
    onRetryOverview={() => { if (selectedProject) void loadOverview(selectedProject) }}
    overviewNotice={overviewNotice}
    overviewTitle={overviewTitle}
    overviewBody={overviewBody}
    editingOverview={editingOverview}
    busy={busy}
    onBack={returnToProjectList}
    onOpenPage={onOpenPage}
    onEditOverview={() => { setOverviewTitle(overview ? String(overview.metadata.title ?? '') : selectedProject.name + ' 概览'); setOverviewBody(overview?.body ?? ''); setEditingOverview(true) }}
    onCancelOverview={() => setEditingOverview(false)}
    onOverviewTitle={setOverviewTitle}
    onOverviewBody={setOverviewBody}
    onSaveOverview={(event) => void saveOverview(event)}
    onRename={() => { setProjectName(selectedProject.name); setEditingProject(true) }}
    editingProject={editingProject}
    projectName={projectName}
    onProjectName={setProjectName}
    onSaveProjectName={(event) => void saveProjectName(event)}
    onArchive={() => setConfirmAction({ title: selectedProject.archived ? '恢复这个项目？' : '归档这个项目？', description: selectedProject.archived ? '项目会重新出现在未归档列表中，现有内容保持不变。' : '项目会从默认列表隐藏，现有页面和知识仍保留。', label: selectedProject.archived ? '恢复项目' : '归档项目', run: async () => { await api.patch(`/projects/${selectedProject.id}`, { archived: !selectedProject.archived, operation_id: newOperationId() }); if (!selectedProject.archived) { setDetailOpen(false); setProjectId('') } } })}
    onDelete={() => setConfirmAction({ title: '删除这个空项目？', description: '删除只适用于没有关联页面的项目，且无法撤销。', label: '删除空项目', run: async () => { await api.delete(`/projects/${selectedProject.id}?operation_id=${newOperationId()}`); setDetailOpen(false); setProjectId(''); await refresh() } })}
    onJournal={() => setShowJournal(true)}
    onImport={() => setShowImport(true)}
    journal={showJournal && <JournalDialog onClose={() => setShowJournal(false)} onError={onError} onOpenPage={onOpenPage} initialLineId={selectedProject.line_id} initialProjectId={selectedProject.id} onSaved={async () => { await refresh() }} />}
    importer={showImport && <ImportDrawer onClose={() => setShowImport(false)} onImported={async () => { await refresh() }} contextMessage="材料只会进入待整理收件箱；需在审批中另行选择归属，不会自动创建正式页面或关联到本项目。仅支持 TXT、Markdown 和飞书材料，不支持 PDF/OCR。" />}
    confirmation={confirmAction && <ConfirmDialog title={confirmAction.title} description={confirmAction.description} confirmLabel={confirmAction.label} busyLabel="正在处理…" danger onCancel={() => setConfirmAction(null)} onConfirm={doConfirmedAction} />}
  />

  return (
    <section className="content-wrap projects-view">
      <PageHeader
        title="项目"
        actions={<button className="button primary" disabled={!lines.length} onClick={() => setShowCreateProject((value) => !value)}><Plus size={15} strokeWidth={2} aria-hidden="true" />新建项目</button>}
      />
      {!loaded ? <div role="status" className="loading-state">正在读取项目目录…</div> : loadError && projects.length === 0 && lines.length === 0 ? <div className="empty-state"><strong>暂时无法读取项目目录</strong><span>{loadError}</span><button className="button secondary" onClick={() => void refresh()}>重新加载</button></div> : <>
      {loadError && <p role="alert" className="form-error">项目目录读取失败，当前显示的是最近一次读取结果。<button className="text-button" onClick={() => void refresh()}>重试</button></p>}
      <div className="project-list-page">
        <KnowledgeSummary pages={pages} index={indexStatus} pagesState={pagesState} indexState={indexState} onRetryPages={loadAuxiliary} />
        {pagesState === 'ready' ? <p className="hint project-stats">共 {projects.length} 条 · 在推进 {projects.filter((project) => projectStatusOf(project) === '在推进').length} · 待建档 {projects.filter((project) => projectStatusOf(project) === '待建档').length} · 已归档 {projects.filter((project) => projectStatusOf(project) === '已归档').length}</p> : pagesState === 'loading' ? <p className="hint project-stats">共 {projects.length} 条 · 项目状态读取中</p> : <p className="hint project-stats">共 {projects.length} 条 · 项目状态暂不可用</p>}
        {showCreateProject && <form className="project-create-form" onSubmit={createProject}>
          <label className="field"><span>主线</span><select aria-label="新项目主线" value={selectedLineId} onChange={(event) => setLineId(event.target.value)}>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
          <label className="field"><span>项目名称</span><input id="new-project" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="输入项目名称" /></label>
          <button className="button primary" disabled={busy || !projectName.trim()}>创建项目</button>
          <button type="button" className="button secondary" onClick={() => setShowCreateProject(false)}>取消</button>
        </form>}
        <details className="line-management" open={showCreateLine}>
          <summary>主线管理 · {lines.length}</summary>
          {lines.length > 0 && <label className="field"><span>选择主线</span><select aria-label="管理主线" value={selectedLineId} onChange={(event) => { setLineId(event.target.value); setEditingLine(false) }}>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>}
          {selectedLine && <div className="line-management-actions">
            {editingLine ? <form onSubmit={saveLineName}><label className="field"><span>主线名称</span><input id="line-name" value={lineName} onChange={(event) => setLineName(event.target.value)} /></label><button className="button secondary" disabled={busy || !lineName.trim()} aria-label="保存主线">保存</button></form> : <button className="button secondary" aria-label="重命名主线" onClick={() => { setLineName(selectedLine.name); setEditingLine(true) }}>重命名主线</button>}
            <button className="button secondary" onClick={() => setConfirmAction({ title: '删除这条空主线？', description: '只能删除没有项目的主线；删除后无法撤销。', label: '删除空主线', run: async () => { await api.delete(`/lines/${selectedLine.id}?operation_id=${newOperationId()}`); setLineId(''); await refresh() } })}>删除空主线</button>
          </div>}
          {showCreateLine ? <form className="create-line-form" onSubmit={createLine}><label className="field"><span>新主线名称</span><input id="new-line" value={lineName} onChange={(event) => setLineName(event.target.value)} /></label><button className="button primary" disabled={busy || !lineName.trim()}>新建主线</button></form> : <button className="text-button" onClick={() => setShowCreateLine(true)}><Plus size={14} strokeWidth={2} aria-hidden="true" />新建主线</button>}
        </details>
        <div className="project-list-controls">
          <label className="field"><span>搜索项目</span><input id="project-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索名称…" /></label>
          <label className="field"><span>主线</span><select aria-label="筛选主线" value={lineFilter} onChange={(event) => setLineFilter(event.target.value)}><option value="">全部主线</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
          <label className="field"><span>筛选状态</span><select aria-label="筛选状态" value={projectStatus} onChange={(event) => { setProjectStatus(event.target.value as typeof projectStatus); setProjectId('') }}><option value="all">全部状态</option><option value="in_progress">在推进</option><option value="needs_setup">待建档</option><option value="archived">已归档</option></select></label>
        </div>
          {projectRows.length === 0 ? (
          <div className="empty-state project-empty"><strong>{pagesState === 'loading' && projectStatus !== 'all' ? '正在读取项目状态…' : pagesState === 'error' && projectStatus !== 'all' ? '项目状态暂不可用' : search.trim() ? `没有匹配「${search.trim()}」的项目，清空搜索看看` : projectStatus !== 'all' || lineFilter ? '这个状态下还没有项目' : '还没有项目。先建一条主线，再建项目。'}</strong>
            {!projects.length && !lines.length ? <button className="button primary" onClick={() => setShowCreateLine(true)}>新建第一条主线</button> : search.trim() ? <button className="text-button" onClick={() => setSearch('')}>清空搜索</button> : null}
          </div>
        ) : <>
          <div className="project-list">{visibleProjectRows.map((project) => <ProjectRow key={project.id} project={project} lines={lines} pages={pages} pagesState={pagesState} statusOf={projectStatusOf} onOpen={openProject} />)}</div>
          {archivedProjectRows.length > 0 && <details className="archived-projects" open={projectStatus === 'archived' || showArchived} onToggle={(event) => setShowArchived(event.currentTarget.open)}><summary>已归档 · {archivedProjectRows.length}</summary><div className="project-list">{archivedProjectRows.map((project) => <ProjectRow key={project.id} project={project} lines={lines} pages={pages} pagesState={pagesState} statusOf={projectStatusOf} onOpen={openProject} />)}</div></details>}
        </>}
      </div>
      </>}
      {confirmAction && <ConfirmDialog title={confirmAction.title} description={confirmAction.description} confirmLabel={confirmAction.label} busyLabel="正在处理…" danger onCancel={() => setConfirmAction(null)} onConfirm={doConfirmedAction} />}
    </section>
  )
}

/**
 * 知识库概览：先给覆盖范围，再看目录；缺数据时显示 —，不假装有索引。
 * 索引正常时不追加状态句：四个指标已经说明覆盖范围，「仿真/真实向量」又只是
 * 设置里的运行模式的复述，工程词不该出现在日常界面。这里只在需要用户处理时说话。
 */
function KnowledgeSummary({ pages, index, pagesState, indexState, onRetryPages }: { pages: PageDirectoryEntry[]; index: IndexStatus | null; pagesState: 'loading' | 'ready' | 'error'; indexState: 'loading' | 'ready' | 'error'; onRetryPages: () => void }) {
  const confirmed = pages.filter((page) => page.approval_state === 'confirmed').length
  const state = indexState === 'loading'
    ? '正在读取索引状态…'
    : indexState === 'error' || !index
    ? '索引状态暂不可用；目录仍可查看。'
    : index.state === 'not_ready'
      ? '尚未建立索引'
      : index.state === 'stale'
        ? `索引待更新 · ${index.stale_pages} 页`
        : ''
  return <div className="knowledge-summary">
    <div className="knowledge-metrics">
      <div className="knowledge-metric"><span>已确认页</span><strong>{pagesState === 'ready' ? confirmed : '—'}</strong></div>
      <div className="knowledge-metric"><span>已索引页</span><strong>{index ? index.pages : '—'}</strong></div>
      <div className="knowledge-metric"><span>分块</span><strong>{index ? index.chunks : '—'}</strong></div>
      <div className="knowledge-metric"><span>待更新</span><strong>{index ? index.stale_pages : '—'}</strong></div>
    </div>
    {pagesState === 'error' && <p className="knowledge-summary-state">页面目录读取失败。<button className="text-button" onClick={onRetryPages}>重试</button></p>}
    {state && <p className={index?.state === 'stale' ? 'knowledge-summary-state warn' : 'knowledge-summary-state'}>{state}{indexState === 'error' && <> <button className="text-button" onClick={onRetryPages}>重试</button></>}</p>}
  </div>
}

/** 时间线只给一句正文摘要：跳过标题、HTML 注释、代码围栏和空行。 */

function pageBusinessDate(page: PageDirectoryEntry): { label: string; timestamp: number } | null {
  for (const key of ['date', 'created_at', 'updated_at']) {
    const raw = page.metadata[key]
    if (typeof raw !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?$/.test(raw)) continue
    const timestamp = Date.parse(raw.length === 10 ? `${raw}T00:00:00Z` : raw)
    if (!Number.isFinite(timestamp)) continue
    return { label: new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeZone: 'UTC' }).format(timestamp), timestamp }
  }
  return null
}

type ProjectDetailProps = {
  line?: Line
  project: Project
  status: '在推进' | '待建档' | '已归档' | null
  pages: PageDirectoryEntry[]
  /** 全库正式页面与项目：右侧阅读面板解析内部链接、切换归属时用。 */
  library: { pages: PageDirectoryEntry[]; projects: Project[] }
  onReloadPages: () => Promise<void>
  pageDirectoryRevision: number
  overview?: Page
  pagesState: 'loading' | 'ready' | 'error'
  onRetryPages: () => void
  overviewLoadState: 'idle' | 'loading' | 'ready' | 'error'
  onRetryOverview: () => void
  overviewNotice: string
  overviewTitle: string
  overviewBody: string
  editingOverview: boolean
  busy: boolean
  onBack: () => void
  onOpenPage: (id: string, hash?: string) => void
  onEditOverview: () => void
  onCancelOverview: () => void
  onOverviewTitle: (value: string) => void
  onOverviewBody: (value: string) => void
  onSaveOverview: (event: FormEvent) => void
  onRename: () => void
  editingProject: boolean
  projectName: string
  onProjectName: (value: string) => void
  onSaveProjectName: (event: FormEvent) => void
  onArchive: () => void
  onDelete: () => void
  onJournal: () => void
  onImport: () => void
  journal: ReactNode
  importer: ReactNode
  confirmation: ReactNode
}

function explicitOverviewSections(body: string): Record<string, string> {
  const names = ['下一步', '阻塞', '跟进事项', '决策记录']
  const output: Record<string, string> = Object.fromEntries(names.map((name) => [name, '']))
  let active = ''
  let fence: { marker: '`' | '~'; length: number } | null = null
  for (const line of body.split(/\r?\n/)) {
    const fenceLine = /^\s{0,3}(`{3,}|~{3,})(.*)$/.exec(line)
    if (fence) {
      if (fenceLine && fenceLine[1][0] === fence.marker && fenceLine[1].length >= fence.length && !fenceLine[2].trim()) fence = null
      continue
    }
    if (fenceLine) { fence = { marker: fenceLine[1][0] as '`' | '~', length: fenceLine[1].length }; continue }
    const heading = /^#{1,6}\s+(.+?)\s*#*\s*$/.exec(line)?.[1]
    if (heading) { active = names.includes(heading.trim()) ? heading.trim() : ''; continue }
    if (active) output[active] += (output[active] ? '\n' : '') + line
  }
  return output
}

function ProjectRow({ project, lines, pages, pagesState, statusOf, onOpen }: {
  project: Project
  lines: Line[]
  pages: PageDirectoryEntry[]
  pagesState: 'loading' | 'ready' | 'error'
  statusOf: (project: Project) => '在推进' | '待建档' | '已归档' | null
  onOpen: (project: Project) => void
}) {
  const status = statusOf(project)
  const overview = pages.find((page) => page.page_id === project.overview_id && page.approval_state === 'confirmed')
  const nextStep = overview?.body ? explicitOverviewSections(overview.body)['下一步'].trim().split(/\r?\n/).find((line) => line.trim()) : ''
  const summary = pagesState === 'error'
    ? '项目资料暂不可用'
    : project.progress?.trim() || nextStep || (overview ? '项目概览已确认' : pagesState === 'loading' ? '项目资料读取中' : '还没有推进记录')
  return <div className="project-list-row">
    <button data-project-id={project.id} className="project-row-main" onClick={() => onOpen(project)}>
      <span className={`project-status-badge ${status === '在推进' ? 'active' : status === '已归档' ? 'archived' : ''}`}>{pagesState === 'error' && !project.archived ? '暂不可用' : status === null ? '读取中' : status === '待建档' ? '新' : status}</span>
      <span className="project-row-copy"><strong>{project.name}</strong><small>{summary} · {lines.find((line) => line.id === project.line_id)?.name ?? '主线'}</small></span>
      <ChevronRight className="row-chevron" size={15} strokeWidth={1.75} aria-hidden="true" />
    </button>
  </div>
}

function ProjectDetailView(props: ProjectDetailProps) {
  const { project, line, pages, overview } = props
  const confirmedOverview = overview?.approval_state === 'confirmed' ? overview : undefined
  const facts = pages.filter((page) => page.page_id !== overview?.page_id).sort((a, b) => (pageBusinessDate(b)?.timestamp ?? -Infinity) - (pageBusinessDate(a)?.timestamp ?? -Infinity))
  const markdownPages = pages.map((page) => ({ page_id: page.page_id, content_sha256: page.content_sha256, title: String(page.metadata.title ?? ''), relative_path: page.relative_path }))
  const pageTree = buildPageTree(facts)
  const [activePageId, setActivePageId] = useState('')
  const activePage = facts.find((page) => page.page_id === activePageId) ?? facts[0]
  const [activePageDetail, setActivePageDetail] = useState<Page>()
  const [activePageLoad, setActivePageLoad] = useState<'loading' | 'ready' | 'error' | 'updated'>('loading')
  const [activePageRetry, setActivePageRetry] = useState(0)
  // 概览和文档共用右侧同一块区域：默认停在概览（它就是项目首页），没有概览时落到第一篇文档。
  const [view, setView] = useState<'overview' | 'doc'>('overview')
  useEffect(() => {
    if (view !== 'doc' || !activePage) { setActivePageDetail(undefined); setActivePageLoad('loading'); return }
    let current = true
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 5000)
    setActivePageDetail(undefined)
    setActivePageLoad('loading')
    void api.get<Page>(`/pages/${activePage.page_id}?expected_content_sha256=${encodeURIComponent(activePage.content_sha256)}`, { signal: controller.signal }).then((detail) => { if (current) { setActivePageDetail(detail); setActivePageLoad('ready') } }).catch((cause) => { if (current) { setActivePageDetail(undefined); setActivePageLoad(cause instanceof ApiError && cause.status === 409 ? 'updated' : 'error') } }).finally(() => window.clearTimeout(timer))
    return () => { current = false; controller.abort(); window.clearTimeout(timer) }
  }, [view, activePage?.page_id, activePage?.content_sha256, activePageRetry, props.pageDirectoryRevision])
  // 默认只展开当前文档所在的那条路径：树一眼能扫完，又不会把 69 篇全铺开。
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set((findPageTrail(pageTree, facts[0]?.page_id ?? '') ?? []).map((node) => node.key)))
  function toggleFolder(key: string) {
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }
  /** 点了菜单项就收起「更多」，避免浮层挡在页头上。 */
  function closeMenu(event: MouseEvent<HTMLButtonElement>) {
    event.currentTarget.closest('details')?.removeAttribute('open')
  }
  function renderFolder(node: PageTreeNode): ReactNode {
    const open = expanded.has(node.key)
    const hasChildren = node.children.length > 0 || node.pages.length > 0
    return <li key={node.key}>
      <button
        className="knowledge-tree-node"
        aria-expanded={hasChildren ? open : undefined}
        title={node.label}
        onClick={() => { if (hasChildren) toggleFolder(node.key) }}
      >
        {hasChildren
          ? open ? <ChevronDown size={13} strokeWidth={1.75} aria-hidden="true" /> : <ChevronRight size={13} strokeWidth={1.75} aria-hidden="true" />
          : <span className="knowledge-tree-chevron-space" aria-hidden="true" />}
        {open ? <FolderOpen size={14} strokeWidth={1.75} aria-hidden="true" /> : <Folder size={14} strokeWidth={1.75} aria-hidden="true" />}
        <span className="knowledge-tree-label">{node.label}</span>
        <span className="knowledge-tree-count">{node.total}</span>
      </button>
      {open && hasChildren && <ul className="knowledge-tree-list">
        {node.children.map((child) => renderFolder(child))}
        {node.pages.map((page) => <li key={page.page_id}>
          <button
            className="knowledge-tree-page"
            aria-current={activePage?.page_id === page.page_id ? 'page' : undefined}
            title={String(page.metadata.title ?? '未命名页面')}
            onClick={() => { setActivePageId(page.page_id); setView('doc') }}
          >
            <FileText size={14} strokeWidth={1.75} aria-hidden="true" />
            <span>{String(page.metadata.title ?? '未命名页面')}</span>
          </button>
        </li>)}
      </ul>}
    </li>
  }
  return <div className="content-wrap project-detail" role="region" aria-label="项目详情">
    <div className="project-detail-topline">
      <button className="back-link" onClick={props.onBack}><ArrowLeft size={15} strokeWidth={1.75} aria-hidden="true" />返回项目列表</button>
      {line?.name && <span className="project-detail-line">{line.name}</span>}
    </div>
      <div className="project-detail-head">
      <div className="page-heading"><div><h1>{project.name}</h1><span className={`project-status-badge ${project.archived ? 'archived' : props.status === '在推进' ? 'active' : ''}`}>{project.archived ? '已归档' : props.pagesState === 'error' ? '暂不可用' : props.status === null ? '读取中' : props.status === '待建档' ? '新' : props.status}</span></div></div>
      <section className="project-detail-actions" aria-label="项目操作">
        <button className="button primary" onClick={props.onJournal}><Plus size={14} strokeWidth={2} aria-hidden="true" />追加推进日志</button>
        <button className="button secondary" onClick={props.onImport}>存产物</button>
        <details className="project-more-actions"><summary className="button secondary">更多</summary>
          <div className="project-menu">
            {props.editingProject
              ? <form onSubmit={props.onSaveProjectName}><label className="field"><span>项目名称</span><input value={props.projectName} onChange={(event) => props.onProjectName(event.target.value)} /></label><button className="button secondary" disabled={props.busy || !props.projectName.trim()}>保存名称</button></form>
              : <button type="button" onClick={props.onRename}>重命名项目</button>}
            <button type="button" onClick={(event) => { closeMenu(event); props.onArchive() }}>{project.archived ? '恢复项目' : '归档项目'}</button>
            {pages.length === 0 && <button type="button" onClick={(event) => { closeMenu(event); props.onDelete() }}>删除空项目</button>}
          </div>
        </details>
      </section>
    </div>
    <section className="page-list-section project-docs-section">
      <div className="directory-title"><h2>文档</h2><span>{props.pagesState === 'ready' ? facts.length : '—'}</span></div>
      <div className="project-docs">
        <nav className="knowledge-tree project-docs-tree" aria-label="文档目录">
          <ul className="knowledge-tree-list">
            <li>
              <button
                className="knowledge-tree-node"
                aria-current={view === 'overview' ? 'page' : undefined}
                onClick={() => setView('overview')}
              >
                <span className="knowledge-tree-chevron-space" aria-hidden="true" />
                <BookOpen size={14} strokeWidth={1.75} aria-hidden="true" />
                <span className="knowledge-tree-label">项目概览</span>
              </button>
            </li>
            {pageTree.map((node) => renderFolder(node))}
          </ul>
        </nav>
        <div className="project-docs-body">
          {view === 'overview'
            ? <article className={overview ? 'page-reader project-overview-pane' : 'page-reader project-overview-pane is-empty'} aria-label="项目概览">
              {overview && <div className="page-reader-topline">
                <div className="page-meta"><span className={confirmedOverview ? '' : 'page-status-invalid'}>{confirmedOverview ? '已确认概览' : '待确认概览'}</span></div>
                {!props.editingOverview && <button className="text-button quiet" onClick={props.onEditOverview}>编辑</button>}
              </div>}
              <h1>{String(overview?.metadata.title ?? '项目概览')}</h1>
              {overview && <p className="helper-line">{confirmedOverview ? '项目摘要依据这一版；正文可随时修改。' : '待确认概览：正文可读，但不会用于项目摘要。'}</p>}
              {props.editingOverview
                ? <form className="overview-editor" onSubmit={props.onSaveOverview}>
                  <label className="field"><span>概览标题</span><input value={props.overviewTitle} onChange={(event) => props.onOverviewTitle(event.target.value)} /></label>
                  <label className="field"><span>概览正文（Markdown）</span><textarea rows={10} value={props.overviewBody} onChange={(event) => props.onOverviewBody(event.target.value)} /></label>
                  <div className="button-row">
                    <button type="button" className="button secondary" onClick={props.onCancelOverview}>取消</button>
                    <button className="button primary" disabled={props.busy || !props.overviewTitle.trim() || !props.overviewBody.trim()}>{overview ? '保存概览' : '创建概览'}</button>
                  </div>
                </form>
              : props.overviewLoadState === 'loading' ? <p role="status" className="muted">正在读取项目概览…</p>
                : props.overviewLoadState === 'error' ? <p role="alert" className="form-error">项目概览读取失败。<button className="text-button" onClick={props.onRetryOverview}>重试</button></p>
                : overview
                  ? <MarkdownText className="page-body" content={overview.body} sourcePath={overview.relative_path} pageIndex={markdownPages} onOpenPage={props.onOpenPage} />
                  : props.pagesState === 'loading' ? <p role="status" className="muted">正在读取项目页面目录…</p>
                    : props.pagesState === 'error' ? <p role="alert" className="form-error">项目页面目录读取失败。<button className="text-button" onClick={props.onRetryPages}>重试</button></p>
                    : <>
                    <p className="muted">还没有项目概览。写一份用来说明这个项目要达成什么，它会成为项目摘要的依据。</p>
                    <button className="button primary" onClick={props.onEditOverview}>创建概览</button>
                  </>}
              {props.overviewNotice && <p role="status" className={props.overviewNotice.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{props.overviewNotice}</p>}
            </article>
            : activePageDetail && activePageDetail.page_id === activePage?.page_id && activePageDetail.content_sha256 === activePage.content_sha256
              ? <PageReader
                key={activePageDetail.page_id}
                page={activePageDetail}
                pane={props.library}
                onClose={() => undefined}
                onReload={props.onReloadPages}
                onOpenPage={props.onOpenPage}
              />
              : activePage && activePageLoad === 'updated' ? <p role="status" className="form-error">页面内容刚刚更新。请刷新页面目录后重新打开。<button className="text-button" onClick={props.onRetryPages}>刷新目录</button></p> : activePage && activePageLoad !== 'error' ? <p className="muted" role="status">正在读取页面正文…</p> : activePage && activePageLoad === 'error' ? <p role="alert" className="form-error">页面读取失败。<button className="text-button" onClick={() => setActivePageRetry((value) => value + 1)}>重试</button></p> : props.pagesState === 'loading' ? <p className="muted" role="status">正在读取项目页面目录…</p> : props.pagesState === 'error' ? <p role="alert" className="form-error">项目页面目录读取失败。<button className="text-button" onClick={props.onRetryPages}>重试</button></p> : <p className="muted">左侧还没有可读的文档。</p>}
        </div>
      </div>
    </section>
    {props.journal}{props.importer}{props.confirmation}
  </div>
}
