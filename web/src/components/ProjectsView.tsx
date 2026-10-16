import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, api, indexUpdateMessage, newOperationId, type Line, type MutationResult, type Page, type Project } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import { ImportDrawer } from './ImportDrawer'
import { JournalDialog } from './JournalDialog'
import { MarkdownText } from './MarkdownText'

type Props = { onError: (message: string) => void; onOpenPage: (id: string, hash?: string) => void }

export function ProjectsView({ onError, onOpenPage }: Props) {
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<Page[]>([])
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
  const detailScrollTop = useRef(0)
  const lastOpenedProjectId = useRef('')

  const refresh = useCallback(async () => {
    try {
      const [nextLines, nextProjects, nextPages] = await Promise.all([
        api.get<Line[]>('/lines'),
        api.get<Project[]>('/projects'),
        api.get<Page[]>('/pages'),
      ])
      setLines(nextLines)
      setProjects(nextProjects)
      setPages(nextPages.filter((page) => page.storage_area === 'formal'))
      setLoaded(true)
      setLoadError('')
      onError('')
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法加载项目'
      setLoaded(true)
      setLoadError(message)
      onError(message)
    }
  }, [onError])

  useEffect(() => { void refresh() }, [refresh])

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
  function projectStatusOf(project: Project): '在推进' | '待建档' | '已归档' {
    if (project.archived) return '已归档'
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
  const overview = selectedProject ? pages.find((page) => page.page_id === selectedProject.overview_id) : undefined

  async function doConfirmedAction() {
    if (!confirmAction) return
    await mutate('', confirmAction.run)
    setConfirmAction(null)
  }

  function openProject(project: Project) {
    detailScrollTop.current = window.scrollY
    lastOpenedProjectId.current = project.id
    setProjectId(project.id)
    setEditingProject(false)
    setDetailOpen(true)
  }

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
    overview={overview}
    status={projectStatusOf(selectedProject)}
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
      <div className="page-heading">
        <div><div className="eyebrow">知识目录</div><h1>项目</h1><p className="lede">这里的每一条线是一个业务方向。点进去看它现在到哪一步、下一步做什么。</p></div>
      </div>
      {!loaded ? <div role="status" className="loading-state">正在读取项目目录…</div> : loadError && projects.length === 0 && lines.length === 0 ? <div className="empty-state"><strong>暂时无法读取项目目录</strong><span>{loadError}</span><button className="button secondary" onClick={() => void refresh()}>重新加载</button></div> : <>
      {loadError && <p role="alert" className="form-error">项目目录读取失败，当前显示的是最近一次读取结果。<button className="text-button" onClick={() => void refresh()}>重试</button></p>}
      <div className="project-list-page">
        <div className="project-list-heading">
          <button className="button primary" disabled={!lines.length} onClick={() => setShowCreateProject((value) => !value)}>＋ 新建项目</button>
        </div>
        <p className="hint project-stats">共 {projects.length} 条 · 在推进 {projects.filter((project) => projectStatusOf(project) === '在推进').length} · 待建档 {projects.filter((project) => projectStatusOf(project) === '待建档').length} · 已归档 {projects.filter((project) => projectStatusOf(project) === '已归档').length}</p>
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
          {showCreateLine ? <form className="create-line-form" onSubmit={createLine}><label className="field"><span>新主线名称</span><input id="new-line" value={lineName} onChange={(event) => setLineName(event.target.value)} /></label><button className="button primary" disabled={busy || !lineName.trim()}>新建主线</button></form> : <button className="text-button" onClick={() => setShowCreateLine(true)}>＋ 新建主线</button>}
        </details>
        <div className="project-list-controls">
          <label className="field"><span>搜索项目</span><input id="project-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索名称…" /></label>
          <label className="field"><span>主线</span><select aria-label="筛选主线" value={lineFilter} onChange={(event) => setLineFilter(event.target.value)}><option value="">全部主线</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
          <label className="field"><span>筛选状态</span><select aria-label="筛选状态" value={projectStatus} onChange={(event) => { setProjectStatus(event.target.value as typeof projectStatus); setProjectId('') }}><option value="all">全部状态</option><option value="in_progress">在推进</option><option value="needs_setup">待建档</option><option value="archived">已归档</option></select></label>
          <span className="sort-note">默认排序：在推进 → 待建档 → 已归档</span>
        </div>
        {projectRows.length === 0 ? (
          <div className="empty-state project-empty"><strong>{search.trim() ? `没有匹配「${search.trim()}」的项目，清空搜索看看` : projectStatus !== 'all' || lineFilter ? '这个状态下还没有项目' : '还没有项目。先建一条主线，再建项目。'}</strong>
            {!projects.length && !lines.length ? <button className="button primary" onClick={() => setShowCreateLine(true)}>新建第一条主线</button> : search.trim() ? <button className="text-button" onClick={() => setSearch('')}>清空搜索</button> : null}
          </div>
        ) : <>
          <div className="project-list">{visibleProjectRows.map((project) => <ProjectRow key={project.id} project={project} lines={lines} pages={pages} statusOf={projectStatusOf} onOpen={openProject} />)}</div>
          {archivedProjectRows.length > 0 && <details className="archived-projects" open={projectStatus === 'archived' || showArchived} onToggle={(event) => setShowArchived(event.currentTarget.open)}><summary>已归档 · {archivedProjectRows.length}</summary><div className="project-list">{archivedProjectRows.map((project) => <ProjectRow key={project.id} project={project} lines={lines} pages={pages} statusOf={projectStatusOf} onOpen={openProject} />)}</div></details>}
        </>}
      </div>
      </>}
      {confirmAction && <ConfirmDialog title={confirmAction.title} description={confirmAction.description} confirmLabel={confirmAction.label} busyLabel="正在处理…" danger onCancel={() => setConfirmAction(null)} onConfirm={doConfirmedAction} />}
    </section>
  )
}

function pageBusinessDate(page: Page): { label: string; timestamp: number } | null {
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
  status: '在推进' | '待建档' | '已归档'
  pages: Page[]
  overview?: Page
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

function ProjectRow({ project, lines, pages, statusOf, onOpen }: {
  project: Project
  lines: Line[]
  pages: Page[]
  statusOf: (project: Project) => '在推进' | '待建档' | '已归档'
  onOpen: (project: Project) => void
}) {
  const status = statusOf(project)
  const overview = pages.find((page) => page.page_id === project.overview_id && page.approval_state === 'confirmed')
  const nextStep = overview ? explicitOverviewSections(overview.body)['下一步'].trim().split(/\r?\n/).find((line) => line.trim()) : ''
  const summary = project.progress?.trim() || nextStep || '还没有推进记录'
  return <div className="project-list-row">
    <button data-project-id={project.id} className="project-row-main" onClick={() => onOpen(project)}>
      <span className={`project-status-badge ${status === '在推进' ? 'active' : status === '已归档' ? 'archived' : ''}`}>{status === '待建档' ? '新' : status}</span>
      <span className="project-row-copy"><strong>{project.name}</strong><small>{summary} · {lines.find((line) => line.id === project.line_id)?.name ?? '主线'}</small></span>
    </button>
  </div>
}

function ProjectDetailView(props: ProjectDetailProps) {
  const { project, line, pages, overview } = props
  const confirmedOverview = overview?.approval_state === 'confirmed' ? overview : undefined
  const sections = explicitOverviewSections(confirmedOverview?.body ?? '')
  const facts = pages.filter((page) => page.page_id !== overview?.page_id).sort((a, b) => (pageBusinessDate(b)?.timestamp ?? -Infinity) - (pageBusinessDate(a)?.timestamp ?? -Infinity))
  const markdownPages = pages.map((page) => ({ page_id: page.page_id, content_sha256: page.content_sha256, title: String(page.metadata.title ?? ''), relative_path: page.relative_path }))
  return <div className="content-wrap project-detail" role="region" aria-label="项目详情">
    <button className="back-link" onClick={props.onBack}>← 返回项目列表</button>
    <div className="page-heading"><div><div className="eyebrow">{line?.name ?? '项目'}</div><h1>{project.name}</h1><span className={`project-status-badge ${project.archived ? 'archived' : props.status === '在推进' ? 'active' : ''}`}>{props.status === '待建档' ? '新' : props.status}</span></div></div>
    <section className="project-detail-actions" aria-label="项目操作">
      <button className="button primary" onClick={props.onJournal}>＋ 追加推进日志</button>
      <button className="button secondary" onClick={props.onImport}>存产物</button>
      <details className="project-more-actions"><summary>更多</summary>
        {props.editingProject ? <form onSubmit={props.onSaveProjectName}><label className="field"><span>项目名称</span><input value={props.projectName} onChange={(event) => props.onProjectName(event.target.value)} /></label><button className="button secondary" disabled={props.busy || !props.projectName.trim()}>保存名称</button></form> : <button className="text-button" onClick={props.onRename}>重命名项目</button>}
        <button className="text-button" onClick={props.onArchive}>{project.archived ? '恢复项目' : '归档项目'}</button>
        {pages.length === 0 && <button className="text-button" onClick={props.onDelete}>删除空项目</button>}
      </details>
    </section>
    <section className="project-dossier" aria-label="项目档案">
      <article><h2>当前状态</h2>{project.progress?.trim() ? <MarkdownText content={project.progress.trim()} pageIndex={markdownPages} onOpenPage={props.onOpenPage} /> : <p>还没有记录</p>}</article>
      {['下一步', '阻塞', '跟进事项', '决策记录'].map((name) => <article key={name}><h2>{name}</h2>{sections[name].trim() ? <MarkdownText content={sections[name]} sourcePath={confirmedOverview?.relative_path} pageIndex={markdownPages} onOpenPage={props.onOpenPage} /> : <p>还没有记录</p>}</article>)}
    </section>
    {props.overviewNotice && <p role="status" className={props.overviewNotice.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{props.overviewNotice}</p>}
    <section className="page-list-section project-overview-section">
      <div className="directory-title"><h2>项目概览</h2>{overview && <button className="text-button" onClick={() => props.onOpenPage(overview.page_id)}>打开概览</button>}</div>
      {overview ? <>
        {confirmedOverview ? <p className="page-validity-note">已确认概览 · 项目摘要依据</p> : <p role="status" className="page-validity-note">待确认概览 · 正文可读，但不会用于项目摘要</p>}
        <h3>{String(overview.metadata.title ?? '项目概览')}</h3>
        <MarkdownText className="project-overview-body" content={overview.body} sourcePath={overview.relative_path} pageIndex={markdownPages} onOpenPage={props.onOpenPage} />
        <button className="button secondary" onClick={props.onEditOverview}>编辑自由 Markdown 概览</button>
      </> : <><p className="muted">还没有项目概览。</p><button className="button secondary" onClick={props.onEditOverview}>创建项目概览</button></>}
      {props.editingOverview && <form className="overview-editor" onSubmit={props.onSaveOverview}><label className="field"><span>概览标题</span><input value={props.overviewTitle} onChange={(event) => props.onOverviewTitle(event.target.value)} /></label><label className="field"><span>自由 Markdown 正文</span><textarea rows={10} value={props.overviewBody} onChange={(event) => props.onOverviewBody(event.target.value)} /></label><div className="journal-actions"><button type="button" className="button secondary" onClick={props.onCancelOverview}>取消</button><button className="button primary" disabled={props.busy || !props.overviewTitle.trim() || !props.overviewBody.trim()}>{overview ? '确认并保存概览' : '确认并创建概览'}</button></div></form>}
    </section>
    <section className="page-list-section"><div className="directory-title"><h2>时间线</h2><span>{facts.length}</span></div>{facts.length ? <ul className="knowledge-page-list">{facts.map((page) => <li key={page.page_id}><div className="project-timeline-item"><button onClick={() => props.onOpenPage(page.page_id, page.content_sha256)}><span className="page-type-mark">{page.approval_state === 'confirmed' ? '知' : '待'}</span><span><small>{pageBusinessDate(page)?.label ?? '日期未记录'} · {page.metadata.kind === 'journal' ? '推进日志' : page.metadata.kind === 'meeting' ? '关联会议' : '产物'}</small><strong>{String(page.metadata.title ?? '未命名页面')}</strong></span><span aria-hidden="true">›</span></button>{page.approval_state === 'confirmed' ? <MarkdownText className="project-timeline-summary" content={page.body.trim().split(/\r?\n/).find((line) => line.trim())?.slice(0, 120) || '还没有摘要'} sourcePath={page.relative_path} pageIndex={markdownPages} onOpenPage={props.onOpenPage} /> : <small>待确认内容</small>}</div></li>)}</ul> : <p className="muted">还没有关联页面。</p>}</section>
    {props.journal}{props.importer}{props.confirmation}
  </div>
}
