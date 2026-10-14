import { TasksPanel } from './TasksPanel'
import { FeishuPanel } from './FeishuPanel'
import { useCallback, useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  api,
  newOperationId,
  type ActionCandidate,
  type Draft,
  type IntakeItem,
  type Line,
  type MutationResult,
  type Page,
  type Project,
  indexUpdateMessage,
} from '../api/client'
import { DraftReview } from './DraftReview'
import type { components } from '../api/generated'

type Props = { onError: (message: string) => void }
type PendingOrganize = { plan: { plan_id: string; scope_sha256: string; request_limit: number }; scope: Record<string, unknown>; body: Record<string, unknown>; key: string }
type BatchUpload = { key: string; file: File; path: string; state: 'queued' | 'uploading' | 'succeeded' | 'failed' | 'skipped' | 'blocked'; message?: string }
const MAX_BATCH_FILES = 100
const MAX_BATCH_BYTES = 100 * 1024 * 1024
const MAX_FILE_BYTES = 20 * 1024 * 1024

export function TodayView({ onError }: Props) {
  const [feishuMode, setFeishuMode] = useState<'fake' | 'real' | null>(null)
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
  const [indexNotice, setIndexNotice] = useState('')
  const [pendingOrganize, setPendingOrganize] = useState<PendingOrganize | null>(null)
  const [batchUploads, setBatchUploads] = useState<BatchUpload[]>([])
  const [uploadingBatch, setUploadingBatch] = useState(false)
  const uploadingBatchRef = useRef(false)
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
      const result = await api.post<MutationResult>('/journal/log', {
        title: text.trim().split('\n')[0].slice(0, 60) || '工作日志',
        body: text,
        confirmation_id: operation(key + ':confirmation'),
        operation_id: operation(key),
      })
      setIndexNotice(indexUpdateMessage(result.index_update) ?? '')
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

  function stageFiles(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (uploadingBatchRef.current) return
    if (selectedFiles.length === 0) return
    const batchTooLarge = selectedFiles.length > MAX_BATCH_FILES
      || selectedFiles.reduce((total, file) => total + file.size, 0) > MAX_BATCH_BYTES
    setBatchUploads(selectedFiles.map((file) => {
      const path = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
      if (batchTooLarge) return { key: newOperationId(), file, path, state: 'blocked', message: '所选批次超过 100 个文件或 100 MB；未上传。' }
      const components = path.split('/').filter(Boolean)
      if (components.some((part) => part.startsWith('.') || /\.(app|bundle|framework|pkg)$/i.test(part))) return { key: newOperationId(), file, path, state: 'skipped', message: '隐藏内容或应用包内容已跳过。' }
      if (!/\.(txt|md)$/i.test(file.name)) return { key: newOperationId(), file, path, state: 'skipped', message: '仅支持 TXT / Markdown。' }
      if (file.size > MAX_FILE_BYTES) return { key: newOperationId(), file, path, state: 'blocked', message: '单个文件超过 20 MB；未上传。' }
      if (file.size === 0) return { key: newOperationId(), file, path, state: 'blocked', message: '空文件未上传。' }
      return { key: newOperationId(), file, path, state: 'queued' }
    }))
  }

  async function uploadBatch(rows: BatchUpload[]) {
    const queued = rows.filter((row) => row.state === 'queued' || row.state === 'failed')
    if (queued.length === 0 || uploadingBatchRef.current) return
    uploadingBatchRef.current = true
    setUploadingBatch(true)
    let uploadedAny = false
    try {
      for (const row of queued) {
        setBatchUploads((current) => current.map((item) => item.key === row.key ? { ...item, state: 'uploading', message: undefined } : item))
        const form = new FormData()
        form.append('operation_id', row.key)
        form.append('file', row.file)
        try {
          await api.upload<IntakeItem>('/intake/files', form)
          uploadedAny = true
          setBatchUploads((current) => current.map((item) => item.key === row.key ? { ...item, state: 'succeeded', message: '已保存到待整理' } : item))
        } catch (cause) {
          setBatchUploads((current) => current.map((item) => item.key === row.key ? { ...item, state: 'failed', message: cause instanceof Error ? cause.message : '导入失败；可单独重试此项。' } : item))
        }
      }
      if (uploadedAny) await refresh()
    } finally {
      uploadingBatchRef.current = false
      setUploadingBatch(false)
    }
  }

  function retryUpload(key: string) {
    const row = batchUploads.find((item) => item.key === key)
    if (row) void uploadBatch([row])
  }

  async function organize() {
    if (!selected.length || !selectedLineId || !selectedProjectId) return
    const key = 'job:' + selected.slice().sort().join(',')
    const reprocess = items.some((item) => selected.includes(item.item_id) && item.state !== 'pending')
    setBusy(true)
    try {
      const body: Record<string, unknown> = {
        item_ids: selected,
        line_id: selectedLineId,
        project_id: selectedProjectId,
        operation_id: operation(key),
        reprocess,
      }
      const settings = await api.get<components['schemas']['SettingsSummary']>('/settings')
      if (settings.mode === 'real') {
        const preview = await api.post<{ plan: PendingOrganize['plan']; scope: Record<string, unknown> }>('/acceptance-plans', {
          operation: 'model.organize', scope: body,
        })
        setPendingOrganize({ ...preview, body, key })
        return
      }
      await api.post('/intake/jobs', body)
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

  async function confirmOrganize() {
    if (!pendingOrganize) return
    const pending = pendingOrganize
    setBusy(true)
    try {
      await api.post(`/acceptance-plans/${pending.plan.plan_id}/confirm`, {
        scope_sha256: pending.plan.scope_sha256, scope: pending.scope,
      })
      await api.post('/intake/jobs', { ...pending.body, acceptance_plan_id: pending.plan.plan_id })
      finish(pending.key)
      setPendingOrganize(null)
      setSelected([])
      await refresh()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '本次整理未能完成；请检查计划状态后再决定是否重试')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  async function cancelOrganize() {
    if (!pendingOrganize) return
    try {
      await api.delete(`/acceptance-plans/${pendingOrganize.plan.plan_id}`)
      setPendingOrganize(null)
      onError('已取消本次整理预览，没有发送所选材料。')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法取消本次整理计划')
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

      {pendingOrganize && <section className="plan-card approval-preview" aria-label="真实材料整理发送预览">
        <div><strong>请确认发送所选材料进行整理</strong><span>发送给已配置的 DeepSeek 整理模型 · 最多 {pendingOrganize.plan.request_limit} 次 HTTP 请求（这是调用次数上限，不是金额上限）· 输出上限 {String(pendingOrganize.scope.max_output_tokens)} token；按 2026-10-13 核对价，输出 token 估算不超过 ¥{(Number(pendingOrganize.scope.max_output_tokens) * 8 / 1_000_000).toFixed(4)}，输入 token 与实际账单未知；整理会关闭思考模式。</span></div>
        <p>目标归属：{lines.find((line) => line.id === pendingOrganize.body.line_id)?.name ?? '所选主线'} / {projects.find((project) => project.id === pendingOrganize.body.project_id)?.name ?? '所选项目'}。整理仅生成待审核稿，不会直接写入正式知识。</p>
        {(pendingOrganize.scope.outgoing_inputs as Array<{ item_id: string; text: string }>).map((entry) => <article className="approval-source" key={entry.item_id}><h3>{items.find((item) => item.item_id === entry.item_id)?.title ?? '所选材料'}</h3><pre>{entry.text}</pre></article>)}
        <details><summary>内部操作编号</summary><pre>{String(pendingOrganize.body.operation_id)}</pre></details>
        <div className="button-row"><button className="button primary" disabled={busy} onClick={() => void confirmOrganize()}>确认并整理所选材料</button><button className="button secondary" disabled={busy} onClick={() => void cancelOrganize()}>取消，不发送</button></div>
      </section>}

      <div className="today-grid">
        <div className="today-main">
          <FeishuPanel onImported={refresh} onMode={setFeishuMode} />
          <TasksPanel projects={projects} candidates={actions} mode={feishuMode} />
          <section className="panel capture-panel">
            <div className="panel-heading"><div><h2>随手记</h2><p>记录原文不会调用模型，也不会自动写入正式知识。</p></div><span className="panel-index">01</span></div>
            <form onSubmit={saveIntake}>
              <label className="sr-only" htmlFor="quick-capture">写下刚想到或刚收到的内容</label>
              <textarea id="quick-capture" value={text} onChange={(event) => setText(event.target.value)} placeholder="写下刚想到或刚收到的内容…" rows={5} />
              <div className="capture-actions">
                <div className="batch-import-controls">
                  <label className="button secondary file-button">
                    选择多个文件
                    <input type="file" multiple disabled={uploadingBatch} accept=".txt,.md,text/plain,text/markdown" onChange={stageFiles} />
                  </label>
                  <label className="button secondary file-button">
                    选择文件夹
                    <input type="file" multiple webkitdirectory="" disabled={uploadingBatch} accept=".txt,.md,text/plain,text/markdown" onChange={stageFiles} />
                  </label>
                </div>
                <div className="button-row">
                  <button type="button" className="button secondary" disabled={!text.trim() || busy} onClick={saveJournal}>记入工作日志</button>
                  <button className="button primary" disabled={!text.trim() || busy}>{busy ? '保存中…' : '存入待整理'}</button>
                </div>
              </div>
            </form>
            {batchUploads.length > 0 && <section className="batch-upload-review" aria-label="导入批次">
              <div className="panel-heading"><div><h3>待导入文件</h3><p>最多 100 个 / 100 MB；每个文件不超过 20 MB。隐藏内容和应用包会跳过。只保存原件到待整理区，不会调用模型。</p></div><button type="button" className="text-button" onClick={() => setBatchUploads([])} disabled={uploadingBatch}>清空列表</button></div>
              <ul className="source-list">{batchUploads.map((row) => <li key={row.key}><div className="source-row"><span className="source-title"><strong>{row.path}</strong><small>{(row.file.size / 1024).toFixed(1)} KB · {{ queued: '待导入', uploading: '正在导入', succeeded: '已导入', failed: '导入失败', skipped: '已跳过', blocked: '未导入' }[row.state]}{row.message ? ` · ${row.message}` : ''}</small></span>{row.state === 'failed' && <button type="button" className="text-button" disabled={uploadingBatch} onClick={() => retryUpload(row.key)}>只重试此文件</button>}</div></li>)}</ul>
              <div className="journal-actions"><button type="button" className="button primary" disabled={uploadingBatch || !batchUploads.some((row) => row.state === 'queued')} onClick={() => void uploadBatch(batchUploads)}>{uploadingBatch ? '正在逐项导入…' : '导入可用文件'}</button></div>
            </section>}
            {indexNotice && <p role="status" className={indexNotice.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{indexNotice}</p>}
          </section>

          <section className="panel queue-panel">
            <div className="panel-heading"><div><h2>待整理</h2><p>选择来源后，明确点击才会生成审核稿。</p></div><div className="review-actions"><button className="button secondary" onClick={() => void refresh()}>刷新状态</button><span className="count-badge">{items.length}</span></div></div>
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
                        <span className="status-label">{{pending: '待整理', processing: '整理中', reviewing: '待审核', completed: '已完成', failed: '整理失败', cancelled: '已取消', unknown: '请求状态未知'}[item.state]}</span>
                      </label>
                    </li>
                  ))}
                </ul>
                <div className="organize-row">
                  <label className="compact-field"><span>主线</span><select value={selectedLineId} onChange={(event) => { setLineId(event.target.value); setProjectId('') }}><option value="">选择主线</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>
                  <label className="compact-field"><span>项目</span><select value={selectedProjectId} onChange={(event) => setProjectId(event.target.value)}><option value="">选择项目</option>{availableProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
                  <button className="button primary" disabled={!selected.length || !selectedProjectId || busy || selectedItems.some((item) => item.state === 'processing' || item.state === 'reviewing')} onClick={organize}>{reprocessing ? '重新整理所选' : '整理所选'} · {selected.length}</button>
                </div>
                {reprocessing && selectedItems.some((item) => item.state === 'unknown')
                  ? <p className="helper-line">请求状态未知，不会自动重发。明确重新整理会创建新操作，可能再次调用模型；原件与既有稿件会保留。</p>
                  : reprocessing && <p className="helper-line">已处理的来源会再次调用整理流程并生成新稿；原件与既有稿件会保留。</p>}
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
                onConfirmed={async (indexStatus) => { setIndexNotice(indexStatus); setActiveDraft(null); await refresh() }}
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
