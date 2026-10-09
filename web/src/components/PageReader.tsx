import { useEffect, useState } from 'react'
import { api, newOperationId, type Page, type Project } from '../api/client'

type Props = { page: Page; onClose: () => void; onReload: () => Promise<void> }

export function PageReader({ page, onClose, onReload }: Props) {
  const [title, setTitle] = useState(String(page.metadata.title ?? ''))
  const [body, setBody] = useState(page.body)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [moveProject, setMoveProject] = useState('')
  const [linkPage, setLinkPage] = useState('')
  const needsConfirmation = page.approval_state !== 'confirmed'

  useEffect(() => {
    void Promise.all([api.get<Project[]>('/projects'), api.get<Page[]>('/pages')]).then(([nextProjects, nextPages]) => {
      setProjects(nextProjects.filter((project) => !project.archived))
      setPages(nextPages.filter((candidate) => candidate.page_id !== page.page_id && candidate.approval_state === 'confirmed'))
    }).catch((cause) => setError(cause instanceof Error ? cause.message : '无法加载页面操作'))
  }, [page.page_id])

  async function confirmCurrentVersion() {
    setBusy(true)
    setError('')
    try {
      await api.post('/pages/' + page.page_id + '/confirmations', {
        metadata: { ...page.metadata, title },
        body,
        confirmation_id: newOperationId(),
        operation_id: newOperationId(),
        expected_base_sha256: page.content_sha256,
      })
      await onReload()
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法确认此页面'
      setError(message.includes('changed since it was reviewed')
        ? '页面确认期间又发生了变化。请重新读取当前正文，检查后再确认。'
        : message)
    } finally {
      setBusy(false)
    }
  }

  async function moveToProject() {
    const destination = projects.find((project) => project.id === moveProject)
    if (!destination) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/pages/${page.page_id}/moves`, {
        destination_relative_path: `${destination.directory}/${page.relative_path.split('/').at(-1)}`,
        operation_id: newOperationId(),
        ...(destination.id !== String(page.metadata.project_id ?? '') ? { structure_confirmation_id: newOperationId() } : {}),
      })
      await onReload()
      onClose()
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法移动页面') }
    finally { setBusy(false) }
  }

  async function addLink() {
    const target = pages.find((candidate) => candidate.page_id === linkPage)
    if (!target) return
    const from = page.relative_path.split('/').slice(0, -1)
    const to = target.relative_path.split('/')
    while (from.length && to.length && from[0] === to[0]) { from.shift(); to.shift() }
    const relative = [...from.map(() => '..'), ...to].join('/')
    setTitle(String(page.metadata.title ?? ''))
    setBody(`${page.body.trimEnd()}\n\n[${String(target.metadata.title ?? '相关页面')}](${relative})\n`)
    setLinkPage('')
    setNotice('链接已加入正文，请检查后确认新版本。')
  }

  return (
    <article className="page-reader">
      <button className="back-link" onClick={onClose}>← 返回目录</button>
      <div className="page-meta">
        <span className={needsConfirmation ? 'page-status-invalid' : ''}>{needsConfirmation ? '待确认' : '已确认知识'}</span>
        <span>{page.relative_path}</span>
      </div>
      <h1>{needsConfirmation ? '检查页面当前版本' : String(page.metadata.title ?? '未命名页面')}</h1>
      {needsConfirmation ? (
        <section className="page-reconfirmation" aria-label="重新确认当前页面">
          <p role="status">此页面自上次确认后已有变化，目前不会用于知识问答。请核对当前正文；只有点击确认后，新版本才会恢复检索资格。</p>
          {error && <p role="alert" className="form-error">{error}</p>}
          {error && <button className="text-button" onClick={() => void onReload()}>重新读取当前版本</button>}
          <label className="field"><span>页面标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <label className="field"><span>页面正文</span><textarea aria-label="页面正文" rows={18} value={body} onChange={(event) => setBody(event.target.value)} /></label>
          <div className="button-row">
            <button className="button primary" disabled={busy || !title.trim() || !body.trim()} onClick={() => void confirmCurrentVersion()}>
              {busy ? '正在确认…' : '确认当前版本'}
            </button>
          </div>
        </section>
      ) : <>
        {error && <p role="alert" className="form-error">{error}</p>}
        {notice && <p role="status" className="success-note">{notice}</p>}
        <pre className="page-body">{page.body}</pre>
        <section className="page-structure-actions" aria-label="页面组织操作">
          <label className="field"><span>移动到项目</span><select aria-label="移动到项目" value={moveProject} onChange={(event) => setMoveProject(event.target.value)}><option value="">选择项目</option>{projects.filter((project) => project.id !== String(page.metadata.project_id ?? '')).map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
          <button className="button secondary" disabled={busy || !moveProject} onClick={() => void moveToProject()}>移动页面</button>
          <label className="field"><span>添加页面链接</span><select aria-label="链接到页面" value={linkPage} onChange={(event) => setLinkPage(event.target.value)}><option value="">选择已确认页面</option>{pages.map((candidate) => <option key={candidate.page_id} value={candidate.page_id}>{String(candidate.metadata.title ?? candidate.relative_path)}</option>)}</select></label>
          <button className="button secondary" disabled={busy || !linkPage} onClick={() => void addLink()}>插入链接</button>
          {body !== page.body && <div className="page-reconfirmation"><p>正文已增加指向已确认页面的相对链接。确认后保存为新版本。</p><label className="field"><span>检查并确认正文</span><textarea aria-label="页面正文" rows={10} value={body} onChange={(event) => setBody(event.target.value)} /></label><button className="button primary" disabled={busy} onClick={() => void confirmCurrentVersion()}>确认新版本</button></div>}
        </section>
      </>}
    </article>
  )
}
