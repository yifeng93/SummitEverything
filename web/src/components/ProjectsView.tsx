import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, newOperationId, type Line, type Page, type Project } from '../api/client'

type Props = { onError: (message: string) => void; onOpenPage: (id: string) => void }

export function ProjectsView({ onError, onOpenPage }: Props) {
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [lineId, setLineId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [lineName, setLineName] = useState('')
  const [projectName, setProjectName] = useState('')
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [nextLines, nextProjects, nextPages] = await Promise.all([
        api.get<Line[]>('/lines'),
        api.get<Project[]>('/projects'),
        api.get<Page[]>('/pages'),
      ])
      setLines(nextLines)
      setProjects(nextProjects.filter((project) => !project.archived))
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

  const selectedLineId = lineId || lines[0]?.id || ''
  const selectedLine = lines.find((line) => line.id === selectedLineId)
  const projectRows = projects.filter((project) => project.line_id === selectedLineId)
  const selectedProjectId = projectId || projectRows[0]?.id || ''
  const visiblePages = pages.filter((page) => String(page.metadata.project_id ?? '') === selectedProjectId)

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
            <button key={line.id} className={selectedLineId === line.id ? 'directory-item active' : 'directory-item'} onClick={() => { setLineId(line.id); setProjectId('') }}>
              <span className="line-mark">{line.name.slice(0, 1)}</span><span>{line.name}</span><small>{projects.filter((project) => project.line_id === line.id).length}</small>
            </button>
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
          {projectRows.length === 0 ? (
            <div className="empty-state project-empty"><span className="empty-mark">＋</span><strong>这条主线还没有项目</strong><span>创建一个项目，开始保存正式知识。</span></div>
          ) : (
            <div className="project-list">
              {projectRows.map((project) => {
                const projectPages = pages.filter((page) => String(page.metadata.project_id ?? '') === project.id)
                return (
                  <button key={project.id} className={project.id === selectedProjectId ? 'project-card selected' : 'project-card'} onClick={() => setProjectId(project.id)}>
                    <span className="project-card-icon">▤</span>
                    <span className="project-card-copy"><strong>{project.name}</strong><small>{projectPages.length} 个页面 · 主线：{selectedLine?.name}</small></span>
                    <span aria-hidden="true">›</span>
                  </button>
                )
              })}
            </div>
          )}
          {selectedProjectId && (
            <section className="page-list-section">
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
