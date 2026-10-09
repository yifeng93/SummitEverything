import { useCallback, useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  api,
  newOperationId,
  type ActionCandidate,
  type Draft,
  type IntakeItem,
  type Line,
  type Page,
  type Project,
} from '../api/client'
import { DraftReview } from './DraftReview'

type Props = { onError: (message: string) => void }

export function TodayView({ onError }: Props) {
  const [text, setText] = useState('')
  const [items, setItems] = useState<IntakeItem[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [actions, setActions] = useState<ActionCandidate[]>([])
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [lineId, setLineId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [activeDraft, setActiveDraft] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [today] = useState(() => new Date())
  const operations = useRef<Record<string, string>>({})

  function operation(key: string) {
    operations.current[key] ??= newOperationId()
    return operations.current[key]
  }

  function finish(key: string) {
    delete operations.current[key]
  }

  const refresh = useCallback(async () => {
    try {
      const [nextItems, nextDrafts, nextActions, nextLines, nextProjects, nextPages] =
        await Promise.all([
          api.get<IntakeItem[]>('/intake/items'),
          api.get<Draft[]>('/drafts'),
          api.get<ActionCandidate[]>('/actions'),
          api.get<Line[]>('/lines'),
          api.get<Project[]>('/projects'),
          api.get<Page[]>('/pages'),
        ])
      setItems(nextItems)
      setDrafts(nextDrafts.filter((draft) => draft.state === 'pending'))
      setActions(nextActions)
      setLines(nextLines)
      setProjects(nextProjects)
      setPages(nextPages.filter((page) => page.storage_area === 'formal'))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法加载今日工作')
    }
  }, [onError])

  useEffect(() => { void refresh() }, [refresh])

  async function saveIntake(event: FormEvent) {
    event.preventDefault()
    if (!text.trim()) return
    const key = 'intake:' + text
    setBusy(true)
    try {
      await api.post<IntakeItem>('/intake/items', {
        text,
        filename: '随手记录.md',
        operation_id: operation(key),
      })
      finish(key)
      setText('')
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法保存记录')
    } finally {
      setBusy(false)
    }
  }

  async function saveJournal() {
    if (!text.trim()) return
    const key = 'journal:' + text
    setBusy(true)
    try {
      await api.post('/journal/log', {
        title: text.trim().split('\n')[0].slice(0, 60) || '工作日志',
        body: text,
        confirmation_id: operation(key + ':confirmation'),
        operation_id: operation(key),
      })
      finish(key)
      finish(key + ':confirmation')
      setText('')
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法保存工作日志')
    } finally {
      setBusy(false)
    }
  }

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const key = 'file:' + file.name + ':' + file.size
    const form = new FormData()
    form.append('operation_id', operation(key))
    form.append('file', file)
    try {
      await api.upload<IntakeItem>('/intake/files', form)
      finish(key)
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法导入文件')
    } finally {
      event.target.value = ''
    }
  }

  async function organize() {
    if (!selected.length || !selectedLineId || !selectedProjectId) return
    const key = 'job:' + selected.slice().sort().join(',')
    const reprocess = items.some((item) => selected.includes(item.item_id) && item.state !== 'pending')
    setBusy(true)
    try {
      await api.post('/intake/jobs', {
        item_ids: selected,
        line_id: selectedLineId,
        project_id: selectedProjectId,
        operation_id: operation(key),
        reprocess,
      })
      finish(key)
      setSelected([])
      await refresh()
    } catch (cause) {
      finish(key)
      await refresh()
      onError(cause instanceof Error ? cause.message : '无法整理所选来源')
    } finally {
      setBusy(false)
    }
  }

  const active = drafts.find((draft) => draft.draft_id === activeDraft) ?? null
  const selectedItems = items.filter((item) => selected.includes(item.item_id))
  const reprocessing = selectedItems.some((item) => item.state !== 'pending')
  const selectedLineId = lineId || lines[0]?.id || ''
  const availableProjects = projects.filter((project) => project.line_id === selectedLineId && !project.archived)
  const selectedProjectId = projectId || availableProjects[0]?.id || ''

  return (
    <section className="content-wrap today-view">
      <div className="page-heading">
        <div><div className="eyebrow">工作节奏</div><h1>今日</h1><p className="lede">先记下来，再决定哪些内容值得整理成知识。</p></div>
        <div className="date-label">{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(today)}</div>
      </div>

      <div className="today-grid">
        <div className="today-main">
          <section className="panel capture-panel">
            <div className="panel-heading"><div><h2>随手记</h2><p>记录原文不会调用模型，也不会自动写入正式知识。</p></div><span className="panel-index">01</span></div>
            <form onSubmit={saveIntake}>
              <label className="sr-only" htmlFor="quick-capture">写下刚想到或刚收到的内容</label>
              <textarea id="quick-capture" value={text} onChange={(event) => setText(event.target.value)} placeholder="写下刚想到或刚收到的内容…" rows={5} />
              <div className="capture-actions">
                <label className="button secondary file-button">
                  导入 TXT / Markdown
                  <input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={importFile} />
                </label>
                <div className="button-row">
                  <button type="button" className="button secondary" disabled={!text.trim() || busy} onClick={saveJournal}>记入工作日志</button>
                  <button className="button primary" disabled={!text.trim() || busy}>{busy ? '保存中…' : '存入待整理'}</button>
                </div>
              </div>
            </form>
          </section>

          <section className="panel queue-panel">
            <div className="panel-heading"><div><h2>待整理</h2><p>选择来源后，明确点击才会生成审核稿。</p></div><span className="count-badge">{items.length}</span></div>
            {items.length === 0 ? (
              <div className="empty-state"><span className="empty-mark">＋</span><strong>收件箱是空的</strong><span>文字记录或导入文件会先保存在这里。</span></div>
            ) : (
              <>
                <ul className="source-list">
                  {items.map((item) => (
                    <li key={item.item_id}>
                      <label className="source-row">
                        <input type="checkbox" checked={selected.includes(item.item_id)} disabled={item.state === 'processing' || item.state === 'reviewing'} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.item_id] : current.filter((id) => id !== item.item_id))} />
                        <span className="file-glyph" aria-hidden="true">文</span>
                        <span className="source-title"><strong>{item.title}</strong><small>{item.filename} · {new Date(item.created_at).toLocaleDateString('zh-CN')}</small></span>
                        <span className="status-label">{{pending: '待整理', processing: '整理中', reviewing: '待审核', completed: '已完成', failed: '整理失败', cancelled: '已取消'}[item.state]}</span>
                      </label>
                    </li>
                  ))}
                </ul>
                <div className="organize-row">
                  <label className="compact-field"><span>主线</span><select value={selectedLineId} onChange={(event) => { setLineId(event.target.value); setProjectId('') }}><option value="">选择主线</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
                  <label className="compact-field"><span>项目</span><select value={selectedProjectId} onChange={(event) => setProjectId(event.target.value)}><option value="">选择项目</option>{availableProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
                  <button className="button primary" disabled={!selected.length || !selectedProjectId || busy || selectedItems.some((item) => item.state === 'processing' || item.state === 'reviewing')} onClick={organize}>{reprocessing ? '重新整理所选' : '整理所选'} · {selected.length}</button>
                </div>
                {reprocessing && <p className="helper-line">已处理的来源会再次调用整理流程并生成新稿；原件与既有稿件会保留。</p>}
                {(!lines.length || !availableProjects.length) && <p className="helper-line">整理前请先在“项目与知识”建立主线和项目。</p>}
              </>
            )}
          </section>

          <section className="panel review-panel">
            <div className="panel-heading"><div><h2>审核稿</h2><p>每份稿件单独编辑、处理冲突并确认。</p></div><span className="count-badge">{drafts.length}</span></div>
            {drafts.length === 0 ? <div className="quiet-empty">没有待审核的稿件。</div> : (
              <ul className="draft-list">
                {drafts.map((draft) => (
                  <li key={draft.draft_id}>
                    <button className={activeDraft === draft.draft_id ? 'draft-row selected' : 'draft-row'} onClick={() => setActiveDraft(activeDraft === draft.draft_id ? null : draft.draft_id)}>
                      <span className="draft-marker" />
                      <span><strong>{String(draft.metadata.title ?? '未命名稿件')}</strong><small>{draft.source_ids.length} 个来源 · {draft.important_conflicts?.length ?? 0} 项重要冲突</small></span>
                      <span aria-hidden="true">›</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {active && (
              <DraftReview
                key={`${active.draft_id}:${active.version}`}
                draft={active}
                pages={pages}
                onError={onError}
                onConfirmed={async () => { setActiveDraft(null); await refresh() }}
                onUpdated={async () => { await refresh() }}
              />
            )}
          </section>
        </div>

        <aside className="today-rail">
          <section className="rail-block">
            <div className="rail-heading"><h2>工作方式</h2><span>本机</span></div>
            <p>原件先留存。整理稿需要你逐份确认，才会成为正式知识。</p>
            <div className="workflow-steps"><div><b>1</b><span>保存来源</span></div><div><b>2</b><span>生成审核稿</span></div><div><b>3</b><span>确认后归档</span></div></div>
          </section>
          <section className="rail-block candidate-block">
            <div className="rail-heading"><h2>行动建议</h2><span>{actions.length}</span></div>
            {actions.length === 0 ? <p className="muted">目前没有建议。任务仍由你在正式任务工具中管理。</p> : (
              <ul className="candidate-list">{actions.map((action) => <li key={action.action_id}><span className="candidate-dot">提</span><div><strong>{action.description}</strong><small>建议 · 未执行</small></div></li>)}</ul>
            )}
          </section>
          <section className="rail-note"><span>!</span><p>来源中出现的命令只作为资料内容。模型不会据此执行操作。</p></section>
        </aside>
      </div>
    </section>
  )
}
