import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, indexUpdateMessage, newOperationId, type Line, type MutationResult, type Page, type Project } from '../api/client'

type Props = { onError: (message: string) => void; onOpenPage: (id: string) => void }

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
  const [showArchived, setShowArchived] = useState(false)
  const [busy, setBusy] = useState(false)
  const [overviewNotice, setOverviewNotice] = useState('')
  const pendingOverview = useRef<{ signature: string; operation: string } | null>(null)

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
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法加载项目')
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
  const projectRows = projects.filter((project) => project.line_id === selectedLineId && (showArchived || !project.archived))
  const selectedProjectId = projectId || projectRows[0]?.id || ''
  const visiblePages = pages.filter((page) => String(page.metadata.project_id ?? '') === selectedProjectId)
  const selectedProject = projects.find((project) => project.id === selectedProjectId)
  const overview = selectedProject ? pages.find((page) => page.page_id === selectedProject.overview_id) : undefined

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
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法保存项目概览') }
    finally { setBusy(false) }
  }

  return (
    <section className="content-wrap projects-view">
      <div className="page-heading">
        <div><div className="eyebrow">知识目录</div><h1>项目与知识</h1><p className="lede">围绕主线与项目组织正式确认的页面。</p></div>
        <span className="record-count">{pages.filter((page) => page.approval_state === 'confirmed').length} 个正式页面</span>
      </div>
      <div className="directory-layout">
        <aside className="directory-sidebar">
          <div className="directory-title"><h2>主线</h2><span>{lines.length}</span></div>
          {lines.length === 0 ? <p className="muted">还没有主线。</p> : lines.map((line) => (
            <div key={line.id}>
              <button className={selectedLineId === line.id ? 'directory-item active' : 'directory-item'} onClick={() => { setLineId(line.id); setProjectId(''); setEditingLine(false) }}>
                <span className="line-mark">{line.name.slice(0, 1)}</span><span>{line.name}</span><small>{projects.filter((project) => project.line_id === line.id).length}</small>
              </button>
              {line.id === selectedLineId && <div className="directory-actions">
                {editingLine ? <form onSubmit={saveLineName}><label className="sr-only" htmlFor="line-name">主线名称</label><input id="line-name" value={lineName} onChange={(event) => setLineName(event.target.value)} /><button disabled={busy || !lineName.trim()} aria-label="保存主线">保存</button></form> : <button className="text-button" aria-label="重命名主线" onClick={() => { setLineName(line.name); setEditingLine(true) }}>重命名主线</button>}
                <button className="text-button" onClick={() => void mutate(`/lines/${line.id}`, () => api.delete(`/lines/${line.id}?operation_id=${newOperationId()}`))}>删除空主线</button>
              </div>}
            </div>
          ))}
          <form className="create-inline" onSubmit={createLine}>
            <label className="sr-only" htmlFor="new-line">新主线名称</label>
            <input id="new-line" value={lineName} onChange={(event) => setLineName(event.target.value)} placeholder="新增主线名称" />
            <button className="icon-button" disabled={busy || !lineName.trim()} aria-label="创建主线">＋</button>
          </form>
        </aside>

        <div className="project-browser">
          <div className="project-browser-header">
            <div><span className="eyebrow">{selectedLine?.name ?? '选择主线'}</span><h2>项目</h2></div>
            {selectedLine && <form className="create-project" onSubmit={createProject}>
              <label className="sr-only" htmlFor="new-project">新项目名称</label>
              <input id="new-project" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="新项目名称" />
              <button className="button secondary" disabled={busy || !projectName.trim()}>创建项目</button>
            </form>}
          </div>
          <label className="archive-toggle"><input type="checkbox" checked={showArchived} onChange={(event) => { setShowArchived(event.target.checked); setProjectId('') }} />显示已归档项目</label>
          {projectRows.length === 0 ? (
            <div className="empty-state project-empty"><span className="empty-mark">＋</span><strong>这条主线还没有项目</strong><span>创建一个项目，开始保存正式知识。</span></div>
          ) : (
            <div className="project-list">
              {projectRows.map((project) => {
                const projectPages = pages.filter((page) => String(page.metadata.project_id ?? '') === project.id)
                return <div key={project.id} className="project-card-wrap">
                  <button className={project.id === selectedProjectId ? 'project-card selected' : 'project-card'} onClick={() => { setProjectId(project.id); setEditingProject(false) }}>
                    <span className="project-card-icon">▤</span><span className="project-card-copy"><strong>{project.name}{project.archived ? ' · 已归档' : ''}</strong><small>{projectPages.length} 个页面 · 主线：{selectedLine?.name}</small></span><span aria-hidden="true">›</span>
                  </button>
                  {project.id === selectedProjectId && <div className="directory-actions project-actions">
                    {editingProject ? <form onSubmit={saveProjectName}><label className="sr-only" htmlFor="project-name">项目名称</label><input id="project-name" value={projectName} onChange={(event) => setProjectName(event.target.value)} /><button disabled={busy || !projectName.trim()} aria-label="保存项目">保存</button></form> : <button className="text-button" aria-label="重命名项目" onClick={() => { setProjectName(project.name); setEditingProject(true) }}>重命名项目</button>}
                    <button className="text-button" onClick={() => { void mutate(`/projects/${project.id}`, async () => { await api.patch(`/projects/${project.id}`, { archived: !project.archived, operation_id: newOperationId() }); if (!project.archived) setProjectId('') }) }}>{project.archived ? '恢复项目' : '归档项目'}</button>
                    <button className="text-button" onClick={() => void mutate(`/projects/${project.id}`, () => api.delete(`/projects/${project.id}?operation_id=${newOperationId()}`))}>删除空项目</button>
                  </div>}
                </div>
              })}
            </div>
          )}
          {selectedProjectId && (
            <section className="page-list-section">
              <div className="directory-title"><h2>项目概览</h2>{overview ? <button className="text-button" onClick={() => onOpenPage(overview.page_id)}>打开概览</button> : <span>尚未创建</span>}</div>
              {overviewNotice && <p role="status" className={overviewNotice.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{overviewNotice}</p>}
              {!editingOverview ? <div className="overview-actions"><p className="muted">概述项目目标、判断与进展背景，并链接到事实页面。</p><button className="button secondary" onClick={() => { setOverviewTitle(overview ? String(overview.metadata.title ?? '') : selectedProject?.name + ' 概览'); setOverviewBody(overview?.body ?? ''); setEditingOverview(true) }}>{overview ? '编辑项目概览' : '创建项目概览'}</button></div> : <form className="overview-editor" onSubmit={(event) => void saveOverview(event)}><label className="field"><span>概览标题</span><input value={overviewTitle} onChange={(event) => setOverviewTitle(event.target.value)} /></label><label className="field"><span>目标、整体判断、进展背景与事实链接</span><textarea rows={8} value={overviewBody} onChange={(event) => setOverviewBody(event.target.value)} placeholder="自由编写 Markdown；事实请链接到对应权威页面。" /></label><div className="journal-actions"><button type="button" className="button secondary" onClick={() => setEditingOverview(false)}>取消</button><button className="button primary" disabled={busy || !overviewTitle.trim() || !overviewBody.trim()}>{overview ? '确认并保存概览' : '确认并创建概览'}</button></div></form>}
              <div className="directory-title"><h2>页面</h2><span>{visiblePages.length}</span></div>
              {visiblePages.length === 0 ? <p className="muted">这个项目还没有知识页面。已确认的整理稿会显示在这里。</p> : (
                <ul className="knowledge-page-list">
                  {visiblePages.map((page) => (
                    <li key={page.page_id}>
                      <button onClick={() => onOpenPage(page.page_id)}>
                        <span className="page-type-mark">{page.approval_state === 'confirmed' ? '知' : '待'}</span>
                        <span><strong>{String(page.metadata.title ?? '未命名页面')}</strong><small>{page.approval_state === 'confirmed' ? '已确认' : '需要确认'} · {page.relative_path}</small></span>
                        <span aria-hidden="true">›</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      </div>
    </section>
  )
}
