import { useRef, useState, type FormEvent } from 'react'
import { api, newOperationId, type ActionCandidate, type Project } from '../api/client'
import type { components } from '../api/generated'

type Action = components['schemas']['Action']
type ActionPage = components['schemas']['ActionPage']
type Tasks = components['schemas']['TaskPage']
type Task = components['schemas']['FeishuTask']
type Kind = Action['kind']

const labels: Record<Kind, string> = { feishu_task_create: '创建飞书任务', feishu_task_update: '编辑飞书任务', feishu_task_complete: '完成飞书任务', project_progress: '改变项目进度' }
const states: Record<Action['state'], string> = { proposed: '待独立确认', confirmed: '已确认，尚未执行', running: '动作正在执行，请刷新结果', succeeded: '动作已成功', failed: '动作未成功，查看核实结果', unknown: '结果未知，请核实；此动作不会重发。' }

function evidenceSummary(item: Record<string, unknown>) {
  if (item.kind === 'provider_lookup') return item.found ? '已找到明确的远端执行证据。' : '未找到明确执行证据，仍为未知。'
  if (item.kind === 'local_writer_receipt') return '本地项目进度写入凭据已确认成功。'
  if (item.kind === 'user_outcome') return '人工结果记录：' + String(item.text)
  if (item.kind === 'invalidated_confirmation') return '确认已失效；修改后的动作需要重新独立确认。'
  if (item.kind === 'interrupted') return '执行中断，等待核实。'
  return '动作审计证据已记录。'
}

export function TasksPanel({ projects, candidates }: { projects: Project[]; candidates: ActionCandidate[] }) {
  const [tasks, setTasks] = useState<Tasks | null>(null)
  const [records, setRecords] = useState<ActionPage | null>(null)
  const [action, setAction] = useState<Action | null>(null)
  const [form, setForm] = useState<Kind | null>(null)
  const [summary, setSummary] = useState('')
  const [description, setDescription] = useState('')
  const [dateMode, setDateMode] = useState('')
  const [dateValue, setDateValue] = useState('')
  const [timezone, setTimezone] = useState('Asia/Shanghai')
  const [guid, setGuid] = useState('')
  const [projectId, setProjectId] = useState('')
  const [progress, setProgress] = useState('')
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [candidate, setCandidate] = useState<ActionCandidate | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [outcome, setOutcome] = useState<'succeeded' | 'failed'>('succeeded')
  const [evidence, setEvidence] = useState('')
  const intentId = useRef<string | null>(null)
  const confirmationId = useRef<string | null>(null)
  const outcomeId = useRef<string | null>(null)
  const inFlight = useRef(false)

  async function run(work: () => Promise<void>) {
    if (inFlight.current) return
    inFlight.current = true; setBusy(true); setError('')
    try { await work() }
    catch (cause) { setError(cause instanceof Error ? cause.message : '操作未得到明确结果，请刷新动作记录。') }
    finally { inFlight.current = false; setBusy(false) }
  }

  function open(kind: Kind, remote?: Task, suggestion?: ActionCandidate) {
    setForm(kind); setAction(null); setCandidate(suggestion ?? null)
    setSummary(remote?.summary ?? ''); setDescription(remote?.description ?? '')
    setGuid(remote?.guid ?? ''); setDateMode(''); setDateValue(''); setSelectedFields([])
    setProjectId(suggestion?.related_project_id ?? ''); setProgress(''); setError('')
    intentId.current = newOperationId(); confirmationId.current = null
  }

  async function loadTasks(cursor?: string) {
    await run(async () => {
      const params = new URLSearchParams({ limit: '20' }); if (cursor) params.set('cursor', cursor)
      setTasks(await api.get<Tasks>('/integrations/feishu/tasks?' + params))
    })
  }

  async function loadRecords(cursor?: string) {
    await run(async () => {
      const params = new URLSearchParams({ limit: '20' }); if (cursor) params.set('cursor', cursor)
      setRecords(await api.get<ActionPage>('/action-intents?' + params))
      if (intentId.current) {
        try { setAction(await api.get<Action>('/actions/' + intentId.current)); setForm(null) } catch { /* No saved proposal yet. */ }
      }
    })
  }

  async function prepareCompletion(task: Task) {
    if (inFlight.current) return
    open('feishu_task_complete', task)
    const id = intentId.current
    await run(async () => {
      setAction(await api.post<Action>('/actions', { action_id: id, kind: 'feishu_task_complete', payload: { task_guid: task.guid }, candidate_id: null }))
      setForm(null)
    })
  }

  async function propose(kind: Kind, payload: Record<string, unknown>, remoteTitle?: string) {
    intentId.current ??= newOperationId()
    confirmationId.current = null
    const next = action && form ? await api.patch<Action>('/actions/' + action.action_id, { expected_payload_sha256: action.payload_sha256, payload }) : await api.post<Action>('/actions', { action_id: intentId.current, kind, payload, candidate_id: candidate?.action_id ?? null })
    setAction(next); setForm(null)
    if (remoteTitle) setSummary(remoteTitle)
  }

  function due() {
    return dateMode === 'none' ? null : { value: dateValue, is_all_day: dateMode === 'all_day', timezone }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    await run(async () => {
      if (form === 'project_progress') {
        const project = projects.find((row) => row.id === projectId)
        await propose(form, { project_id: projectId, expected_version: action?.payload.project_id === projectId ? action.payload.expected_version : project?.progress_version ?? 0, progress })
      } else if (form === 'feishu_task_complete') {
        await propose(form, { task_guid: guid })
      } else if (form === 'feishu_task_update') {
        const values: Record<string, unknown> = {}
        if (selectedFields.includes('summary')) values.summary = summary
        if (selectedFields.includes('description')) values.description = description
        if (selectedFields.includes('due')) values.due = due()
        await propose(form, { task_guid: guid, task: values, update_fields: selectedFields })
      } else {
        await propose(form, { summary, description, due: due() })
      }
    })
  }

  function edit() {
    if (!action) return
    setForm(action.kind); intentId.current = action.action_id
    if (action.kind === 'project_progress') { setProjectId(String(action.payload.project_id)); setProgress(String(action.payload.progress)) }
    if (action.kind === 'feishu_task_complete' || action.kind === 'feishu_task_update') setGuid(String(action.payload.task_guid))
    const fields = action.kind === 'feishu_task_update' ? action.payload.task as Record<string, unknown> : action.payload
    setSummary(String(fields?.summary ?? '')); setDescription(String(fields?.description ?? ''))
    if (action.kind === 'feishu_task_update') setSelectedFields(action.payload.update_fields as string[])
    const value = fields?.due as Record<string, unknown> | null
    setDateMode(value ? value.is_all_day ? 'all_day' : 'time' : 'none')
    setDateValue(String(value?.value ?? '')); setTimezone(String(value?.timezone ?? 'Asia/Shanghai'))
  }

  async function confirm() {
    if (!action) return
    confirmationId.current ??= newOperationId()
    await run(async () => setAction(await api.post<Action>('/actions/' + action.action_id + '/confirmations', { payload_sha256: action.payload_sha256, confirmation_id: confirmationId.current })))
  }

  async function execute() {
    if (!action || action.state !== 'confirmed') return
    await run(async () => {
      try { setAction(await api.post<Action>('/actions/' + action.action_id + '/executions', { payload_sha256: action.payload_sha256, confirmation_id: action.confirmation_id })) }
      catch (cause) {
        // A lost response is inspected using the same durable intent, never a new POST.
        setAction(await api.get<Action>('/actions/' + action.action_id))
        throw cause
      }
    })
  }

  const needsDate = form === 'feishu_task_create' || form === 'feishu_task_update' && selectedFields.includes('due')
  const needsTitle = form === 'feishu_task_create' || form === 'feishu_task_update' && selectedFields.includes('summary')
  const valid = !!form && (!needsTitle || !!summary.trim()) && (!needsDate || !!dateMode && (dateMode === 'none' || !!dateValue && !!timezone)) && (form !== 'project_progress' || !!projectId && !!progress.trim()) && (form !== 'feishu_task_update' || !!selectedFields.length && !!guid) && (form !== 'feishu_task_complete' || !!guid)
  const shown = action?.kind === 'feishu_task_update' ? action.payload.task as Record<string, unknown> : action?.payload
  const targetTask = tasks?.items.find((task) => task.guid === action?.payload.task_guid)
  const shownDate = shown?.due as Record<string, unknown> | null
  const selectedProject = projects.find((row) => row.id === String(action?.payload.project_id ?? projectId))
  const recoveredLocalProgress = action?.kind === 'project_progress' && action.state === 'succeeded' && action.evidence?.some((item) => item.kind === 'local_writer_receipt')

  return <section className="panel tasks-panel" aria-busy={busy}>
    <div className="panel-heading"><div><h2>飞书任务与独立动作</h2><p>Fake 模拟远端 · 任务事实由飞书提供。每项任务和进度变化单独确认。</p></div></div>
    <div className="button-row">
      <button className="button secondary" disabled={busy} onClick={() => void loadTasks()}>刷新飞书任务</button>
      <button className="button secondary" disabled={busy} onClick={() => open('feishu_task_create')}>新建飞书任务</button>
      <button className="button secondary" disabled={busy} onClick={() => open('project_progress')}>拟定项目进度变化</button>
      <button className="button secondary" disabled={busy} onClick={() => void loadRecords()}>查看动作记录</button>
    </div>
    {error && <p role="alert" className="error-banner">{error}</p>}
    {tasks && <><ul className="source-list">{tasks.items.map((task) => <li className="task-row" key={task.guid}><div><strong>{task.summary}</strong><small>{task.completed_at ? '飞书已完成' : '飞书未完成'}{task.due ? ' · 截止 ' + new Date(task.due.timestamp).toLocaleString('zh-CN') + (task.due.is_all_day ? '（全天）' : '') : ' · 不设截止日期'}</small></div><div className="button-row"><button className="button secondary" disabled={busy} onClick={() => open('feishu_task_update', task)}>编辑{task.summary}</button><button className="button secondary" disabled={busy} onClick={() => void prepareCompletion(task)}>完成{task.summary}</button></div></li>)}</ul>{tasks.items.length === 0 && <p className="muted">飞书暂无任务。</p>}{tasks.next_cursor && <button className="button secondary" disabled={busy} onClick={() => void loadTasks(tasks.next_cursor!)}>下一页任务</button>}</>}
    {candidates.length > 0 && <div className="action-candidates"><h3>审阅行动建议</h3>{candidates.map((suggestion) => <div key={suggestion.action_id}><p>{suggestion.description}</p><button className="button secondary" disabled={busy} onClick={() => open(suggestion.kind === 'todo' ? 'feishu_task_create' : 'project_progress', undefined, suggestion)}>将建议填写为待确认动作</button></div>)}</div>}
    {records && <div><h3>动作记录</h3><ul className="candidate-list">{records.items.map((item) => <li key={item.action_id}><button className="button secondary" disabled={busy} onClick={() => { setAction(item); setForm(null); intentId.current = item.action_id }}>{labels[item.kind]} · {states[item.state]}</button></li>)}</ul>{records.items.length === 0 && <p>没有已保存的动作。</p>}{records.next_cursor && <button className="button secondary" disabled={busy} onClick={() => void loadRecords(records.next_cursor!)}>下一页动作</button>}</div>}
    {form && <form className="action-form" onSubmit={(event) => void submit(event)}>
      <h3>{labels[form]}</h3>
      {candidate && <p className="helper-line">建议：{candidate.description}。请亲自填写最终值；建议尚未执行。</p>}
      {form === 'feishu_task_update' && <fieldset><legend>只修改选中的字段</legend>{[['summary', '标题'], ['description', '描述'], ['due', '截止日期']].map(([key, label]) => <label key={key}><input type="checkbox" checked={selectedFields.includes(key!)} onChange={(event) => setSelectedFields((current) => event.target.checked ? [...current, key!] : current.filter((value) => value !== key))} />{label}</label>)}</fieldset>}
      {needsTitle && <label>任务标题<input value={summary} onChange={(event) => setSummary(event.target.value)} maxLength={500} required /></label>}
      {(form === 'feishu_task_create' || form === 'feishu_task_update' && selectedFields.includes('description')) && <label>任务描述<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} /></label>}
      {needsDate && <><label>截止日期方式<select value={dateMode} onChange={(event) => { setDateMode(event.target.value); setDateValue('') }} required><option value="">明确选择日期方式</option><option value="none">不设截止日期</option><option value="all_day">全天日期</option><option value="time">具体时间</option></select></label>{dateMode && dateMode !== 'none' && <><label>截止日期<input type={dateMode === 'all_day' ? 'date' : 'text'} value={dateValue} onChange={(event) => setDateValue(event.target.value)} placeholder={dateMode === 'time' ? '带时区偏移的时间，例如 2026-10-13T09:00:00+08:00' : undefined} required /></label><label>日期时区<input value={timezone} onChange={(event) => setTimezone(event.target.value)} required /></label><p className="helper-line">时间按您填写的偏移量与时区核对，不猜开始或截止日期。</p></>}</>}
      {form === 'feishu_task_complete' && <label>待完成任务标识<input value={guid} onChange={(event) => setGuid(event.target.value)} required /></label>}
      {form === 'project_progress' && <><label>进度项目<select value={projectId} onChange={(event) => setProjectId(event.target.value)} required><option value="">选择项目</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label><p>当前进度：{projects.find((row) => row.id === projectId)?.progress || '尚未记录'}</p><label>新的项目进度<textarea value={progress} onChange={(event) => setProgress(event.target.value)} required rows={3} /></label></>}
      <button className="button primary" disabled={!valid || busy}>{action ? '保存修改并重新审阅' : form === 'project_progress' ? '审阅进度变化' : '审阅任务内容'}</button>
    </form>}
    {action && !form && <div className="action-detail"><h3>最终动作：{labels[action.kind]}</h3><dl>
      {shown?.summary !== undefined && <><dt>任务标题</dt><dd>{String(shown.summary)}</dd></>}
      {shown?.description !== undefined && <><dt>任务描述</dt><dd>{String(shown.description) || '空描述'}</dd></>}
      {shown && Object.hasOwn(shown, 'due') && <><dt>截止日期</dt><dd>{shownDate ? String(shownDate.value) + (shownDate.is_all_day ? ' · 全天' : ' · 具体时间') + ' · ' + String(shownDate.timezone) : '不设截止日期'}</dd></>}
      {action.kind === 'feishu_task_update' && <><dt>修改范围</dt><dd>{(action.payload.update_fields as string[]).map((field) => ({summary: '标题', description: '描述', due: '截止日期'}[field])).join('、')}</dd></>}
      {(action.kind === 'feishu_task_complete' || action.kind === 'feishu_task_update') && <><dt>目标任务</dt><dd>{targetTask?.summary ?? String(action.payload.task_guid)}</dd></>}
      {action.kind === 'project_progress' && <><dt>项目</dt><dd>{selectedProject?.name ?? '项目'}</dd><dt>新的项目进度</dt><dd>{String(action.payload.progress)}</dd></>}
    </dl>{action.kind === 'project_progress' && <p>{selectedProject?.progress || '尚未记录'} → {String(action.payload.progress)}</p>}
    <p role="status">{states[action.state]}</p><div className="button-row">
      {action.state === 'proposed' && <button className="button primary" disabled={busy} onClick={() => void confirm()}>独立确认此动作</button>}
      {action.state === 'confirmed' && <button className="button primary" disabled={busy} onClick={() => void execute()}>执行已确认动作</button>}
      {['proposed', 'confirmed'].includes(action.state) && <button className="button secondary" disabled={busy} onClick={edit}>修改动作内容</button>}
      {['running', 'unknown'].includes(action.state) && <button className="button secondary" disabled={busy} onClick={() => void run(async () => setAction(await api.get<Action>('/actions/' + action.action_id)))}>刷新动作结果</button>}
      {action.state === 'unknown' && <button className="button secondary" disabled={busy} onClick={() => void run(async () => setAction(await api.post<Action>('/actions/' + action.action_id + '/reconciliations', {})))}>只读核实远端结果</button>}
    </div>
    {action.evidence?.filter((item) => !(recoveredLocalProgress && item.kind === 'provider_lookup' && !item.found)).map((item, index) => <p key={index}>{evidenceSummary(item)}</p>)}
    {action.state === 'unknown' && <div className="action-form"><label>核实结果<select value={outcome} onChange={(event) => setOutcome(event.target.value as 'succeeded' | 'failed')}><option value="succeeded">确认已成功</option><option value="failed">确认未成功</option></select></label><label>人工核实依据<textarea value={evidence} onChange={(event) => setEvidence(event.target.value)} rows={3} /></label><button className="button secondary" disabled={busy || !evidence.trim()} onClick={() => void run(async () => { outcomeId.current ??= newOperationId(); setAction(await api.post<Action>('/actions/' + action.action_id + '/outcomes', { payload_sha256: action.payload_sha256, confirmation_id: outcomeId.current, state: outcome, evidence })) })}>独立确认并记录核实结果</button></div>}
    <details><summary>动作与执行证据详情</summary><pre>{JSON.stringify(action, null, 2)}</pre></details>
    </div>}
  </section>
}
