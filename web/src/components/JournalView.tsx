import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, newOperationId, type Line, type Page, type Project } from '../api/client'

type Props = { onError: (message: string) => void; onOpenPage: (id: string) => void }

export function JournalView({ onError, onOpenPage }: Props) {
  const [kind, setKind] = useState<'log' | 'thought'>('log')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [lineId, setLineId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [suggestion, setSuggestion] = useState<{ title: string; body: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const pendingSave = useRef<{ signature: string; operation: string } | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [nextLines, nextProjects, nextPages] = await Promise.all([
        api.get<Line[]>('/lines'), api.get<Project[]>('/projects'), api.get<Page[]>('/pages'),
      ])
      setLines(nextLines)
      setProjects(nextProjects)
      setPages(nextPages.filter((page) => page.storage_area === 'formal' && ['log', 'thought'].includes(String(page.metadata.kind))))
      onError('')
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法加载记录') }
  }, [onError])

  useEffect(() => {
    queueMicrotask(() => { void refresh() })
  }, [refresh])
  const availableProjects = projects.filter((project) => project.line_id === lineId && !project.archived)

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!title.trim() || !body.trim()) return
    const signature = JSON.stringify([kind, title.trim(), body, lineId || null, projectId || null])
    if (pendingSave.current?.signature !== signature) pendingSave.current = { signature, operation: newOperationId() }
    setBusy(true)
    try {
      await api.post(`/journal/${kind}`, {
        title: title.trim(), body, line_id: lineId || null, project_id: projectId || null,
        confirmation_id: pendingSave.current.operation, operation_id: pendingSave.current.operation,
      })
      pendingSave.current = null
      setTitle(''); setBody(''); setSuggestion(null); await refresh()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法保存记录') }
    finally { setBusy(false) }
  }

  async function assist() {
    if (!body.trim()) return
    setBusy(true)
    try { setSuggestion(await api.post<{ title: string; body: string }>('/journal/assist', { text: body })) }
    catch (cause) { onError(cause instanceof Error ? cause.message : 'AI 辅助暂时不可用；已保存内容未更改。') }
    finally { setBusy(false) }
  }

  return <section className="content-wrap journal-view">
    <div className="page-heading"><div><div className="eyebrow">本机知识</div><h1>日志与思考</h1><p className="lede">明确保存后写入正式页面；普通浏览不会请求模型。</p></div></div>
    <div className="journal-editor">
      <div className="journal-kind" aria-label="记录类型">
        <button type="button" aria-pressed={kind === 'log'} onClick={() => setKind('log')}>工作日志</button>
        <button type="button" aria-pressed={kind === 'thought'} onClick={() => setKind('thought')}>工作思考</button>
      </div>
      <form onSubmit={(event) => void save(event)}>
        <label className="field"><span>标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
        <label className="field"><span>正文</span><textarea rows={8} value={body} onChange={(event) => setBody(event.target.value)} placeholder="自由记录 Markdown 内容" required /></label>
        <div className="journal-association">
          <label className="field"><span>主线（可选）</span><select value={lineId} onChange={(event) => { setLineId(event.target.value); setProjectId('') }}><option value="">不关联</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
          {lineId && <label className="field"><span>项目（可选）</span><select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">仅关联主线</option>{availableProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>}
        </div>
        <div className="journal-actions"><button className="button secondary" type="button" disabled={busy || !body.trim()} onClick={() => void assist()}>AI 辅助建议</button><button className="button primary" disabled={busy || !title.trim() || !body.trim()}>确认并保存在本机</button></div>
      </form>
      {suggestion && <section className="journal-suggestion"><h2>可编辑建议 · 尚未保存</h2><button className="text-button" onClick={() => setSuggestion(null)}>取消建议</button><label className="field"><span>建议标题</span><input value={suggestion.title} onChange={(event) => setSuggestion({ ...suggestion, title: event.target.value })} /></label><label className="field"><span>建议正文</span><textarea rows={6} value={suggestion.body} onChange={(event) => setSuggestion({ ...suggestion, body: event.target.value })} /></label><button className="button secondary" onClick={() => { setTitle(suggestion.title); setBody(suggestion.body); setSuggestion(null) }}>采用到编辑区</button></section>}
    </div>
    <section className="journal-history"><h2>已保存的记录</h2>{pages.length === 0 ? <p className="muted">暂无日志或思考。</p> : <ul className="knowledge-page-list">{pages.map((page) => <li key={page.page_id}><button onClick={() => onOpenPage(page.page_id)}><span className="page-type-mark">{page.metadata.kind === 'log' ? '记' : '想'}</span><span><strong>{String(page.metadata.title)}</strong><small>已确认 · 本机保存</small></span><span aria-hidden="true">›</span></button></li>)}</ul>}</section>
  </section>
}
