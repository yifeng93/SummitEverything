import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, api, newOperationId } from '../api/client'
import type { components } from '../api/generated'
import { startFeishuAuthorization } from './feishuAuthorization'
import { ConfirmDialog } from './ConfirmDialog'

type Status = components['schemas']['FeishuStatus']
type Materials = components['schemas']['MaterialPage']
type Calendar = components['schemas']['CalendarPage']
type Imports = components['schemas']['ImportResult']
type AcceptancePlan = { plan_id: string; scope_sha256: string; request_limit: number; state: string }
type PendingApproval = { plan: AcceptancePlan; operation: string; scope: Record<string, unknown>; execute: (planId: string) => Promise<void> }
const prefix = '/integrations/feishu'
const localDate = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`

export function FeishuPanel({ onImported, onMode, onAuthorizationChanged, onBusyChange, onClose, view = 'all', showAuthorization = true }: { onImported: (itemIds?: string[]) => Promise<void>; onMode?: (mode: "fake" | "real" | null) => void; onAuthorizationChanged?: () => void; onBusyChange?: (busy: boolean) => void; onClose?: () => void; view?: 'all' | 'calendar' | 'materials'; showAuthorization?: boolean }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [authorizationUrl, setAuthorizationUrl] = useState<string | null>(null)
  const [authProblem, setAuthProblem] = useState<'expired' | 'scope' | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmDisconnect, setConfirmDisconnect] = useState(false)
  const [query, setQuery] = useState('')
  const [visibility, setVisibility] = useState('')
  const [materials, setMaterials] = useState<Materials | null>(null)
  const [materialsSuccess, setMaterialsSuccess] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [imports, setImports] = useState<Imports | null>(null)
  const [unknownImportKey, setUnknownImportKey] = useState<string | null>(null)
  const [calendar, setCalendar] = useState<Calendar | null>(null)
  const [calendarSuccess, setCalendarSuccess] = useState<string | null>(null)
  const [calendarError, setCalendarError] = useState('')
  const [start, setStart] = useState(() => localDate(new Date()))
  const [end, setEnd] = useState(() => { const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); return localDate(tomorrow) })
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai')
  const [titles, setTitles] = useState<Record<string, string>>({})
  const [approval, setApproval] = useState<PendingApproval | null>(null)
  const operation = useRef<{ key: string; id: string } | null>(null)
  const statusRef = useRef<Status | null>(null)
  useEffect(() => { onBusyChange?.(busy) }, [busy, onBusyChange])

  const publishStatus = useCallback((value: Status, notify = true) => {
    const previous = statusRef.current
    statusRef.current = value
    setStatus(value)
    if (notify && previous && (previous.authorized !== value.authorized || previous.identity !== value.identity || previous.mode !== value.mode || previous.app_configured !== value.app_configured || previous.scopes.join(',') !== value.scopes.join(','))) onAuthorizationChanged?.()
  }, [onAuthorizationChanged])

  useEffect(() => {
    let alive = true
    api.get<Status>(prefix + '/status').then((value) => { if (alive) { publishStatus(value, false); onMode?.(value.mode === "fake" || value.mode === "real" ? value.mode : null) } })
      .catch((cause: unknown) => { if (alive) { onMode?.(null); setError(cause instanceof Error ? cause.message : '无法读取授权状态') } })
    return () => { alive = false }
  }, [onMode, publishStatus])

  function recordAuthProblem(code?: string) {
    if (code === 'token_expired' || code === 'not_authorized') {
      if (statusRef.current) publishStatus({ ...statusRef.current, authorized: false, scopes: [] })
      setAuthProblem(code === 'token_expired' ? 'expired' : null)
      setSelected([]); setMaterials(null); setCalendar(null); setMaterialsSuccess(null); setCalendarSuccess(null)
    } else if (code === 'missing_scope') {
      setAuthProblem((current) => current === 'expired' ? current : 'scope')
    }
  }

  function recordFailure(cause: unknown) {
    if (cause instanceof ApiError) recordAuthProblem(cause.code ?? (cause.status === 401 ? 'not_authorized' : undefined))
  }

  async function preparePlan(operation: string, scope: Record<string, unknown>, execute: (planId: string) => Promise<void>) {
    setBusy(true); setError('')
    try {
      const result = await api.post<{ plan: AcceptancePlan; scope: Record<string, unknown> }>('/acceptance-plans', { operation, scope })
      setApproval({ ...result, operation, execute })
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法生成本次授权预览') }
    finally { setBusy(false) }
  }

  async function confirmPlan() {
    if (!approval) return
    const current = approval
    setBusy(true); setError('')
    try {
      await api.post('/acceptance-plans/' + current.plan.plan_id + '/confirm', { scope_sha256: current.plan.scope_sha256 })
      setApproval(null)
      await current.execute(current.plan.plan_id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : '执行结果未知；计划不会重发') }
    finally { setBusy(false) }
  }

  async function cancelPlan() {
    if (!approval) return
    const current = approval
    setBusy(true)
    try { await api.delete('/acceptance-plans/' + current.plan.plan_id); setApproval(null) }
    catch (cause) { setError(cause instanceof Error ? cause.message : '无法撤销本次计划') }
    finally { setBusy(false) }
  }

  async function authorize() {
    setBusy(true); setError(''); setAuthorizationUrl(null)
    try {
      if (status?.mode === 'real') {
        const result = await startFeishuAuthorization('real')
        // No fetch to the external authorization endpoint and no automatic code
        // exchange. The user opens the official page in a separate browser.
        setAuthorizationUrl(result.authorizationUrl)
      } else {
        const result = await startFeishuAuthorization('fake')
        publishStatus(result.status); setAuthProblem(null)
      }
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '授权失败') }
    finally { setBusy(false) }
  }

  async function refreshAuthorization() {
    setBusy(true); setError('')
    try {
      const value = await api.get<Status>(prefix + '/status')
      publishStatus(value); onMode?.(value.mode === 'fake' || value.mode === 'real' ? value.mode : null)
      if (value.authorized) { setAuthorizationUrl(null); setAuthProblem(null) }
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '无法读取授权状态') }
    finally { setBusy(false) }
  }

  async function logout() {
    setBusy(true); setError('')
    try {
      await api.delete<void>(prefix + '/authorizations')
      if (statusRef.current) publishStatus({ ...statusRef.current, authorized: false, scopes: [] })
      setAuthorizationUrl(null); setAuthProblem(null); setMaterials(null); setCalendar(null); setMaterialsSuccess(null); setCalendarSuccess(null); setSelected([])
    } catch (cause) { setError(cause instanceof Error ? cause.message : '断开飞书授权失败') }
    finally { setBusy(false) }
  }

  async function loadMaterials(cursor?: string) {
    setBusy(true); setError('')
    try {
      const params = new URLSearchParams({ query, limit: '20' })
      if (visibility) params.set('visibility', visibility)
      if (cursor) params.set('cursor', cursor)
      const execute = async (planId?: string) => {
        const plannedParams = new URLSearchParams(params)
        if (planId) plannedParams.set('plan_id', planId)
        const value = await api.get<Materials>(prefix + '/materials?' + plannedParams)
        setTitles((current) => ({ ...current, ...Object.fromEntries(value.items.map((item) => [item.material_id, item.title])) }))
          setMaterials(value); setMaterialsSuccess(new Date().toISOString())
      }
      if (status?.mode === 'real') {
        await preparePlan('feishu.materials.read', { query, visibility: visibility || null, cursor: cursor ?? null, limit: 20 }, async (planId) => {
          try { await execute(planId) } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '无法读取材料') }
        })
        return
      }
      await execute()
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '无法读取材料') }
    finally { setBusy(false) }
  }

  async function importSelected() {
    const key = [...selected].sort().join(',')
    if (unknownImportKey === key) return
    if (!operation.current || operation.current.key !== key) operation.current = { key, id: newOperationId() }
    setBusy(true); setError('')
    try {
      const execute = async (planId?: string) => {
        let result: Imports
        try { result = await api.post<Imports>(prefix + '/imports' + (planId ? '?plan_id=' + planId : ''), { material_ids: selected, operation_id: operation.current!.id }) }
        catch (cause) {
          if (!(cause instanceof ApiError) || cause.status >= 500) setUnknownImportKey(key)
          throw cause
        }
        setImports(result); setSelected([]); operation.current = null
        for (const outcome of result.outcomes) recordAuthProblem(outcome.error_code ?? undefined)
        await onImported(result.outcomes.filter((outcome) => outcome.state === 'succeeded' && outcome.item_id).map((outcome) => outcome.item_id!))
      }
      if (status?.mode === 'real') {
        await preparePlan('feishu.materials.import', { material_ids: [...selected], operation_id: operation.current.id }, async (planId) => {
          try { await execute(planId) } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '导入结果未知；不要新建重试计划') }
        })
        return
      }
      await execute()
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '导入失败，请重试同一选择') }
    finally { setBusy(false) }
  }

  async function loadCalendar(event?: FormEvent, cursor?: string) {
    event?.preventDefault(); setBusy(true); setCalendarError('')
    try {
      const atStartOfDay = (day: string) => timezone === 'UTC' ? day + 'T00:00:00Z' : new Date(day + 'T00:00:00').toISOString()
      const startAt = atStartOfDay(start), endAt = atStartOfDay(end)
      const params = new URLSearchParams({ start: startAt, end: endAt, timezone, limit: '20' })
      if (cursor) params.set('cursor', cursor)
      const execute = async (planId?: string) => {
        const plannedParams = new URLSearchParams(params)
        if (planId) plannedParams.set('plan_id', planId)
        setCalendar(await api.get<Calendar>(prefix + '/calendar?' + plannedParams)); setCalendarSuccess(new Date().toISOString())
      }
      if (status?.mode === 'real') {
        await preparePlan('feishu.calendar.read', { start: startAt, end: endAt, timezone, cursor: cursor ?? null, limit: 20 }, async (planId) => {
          try { await execute(planId) } catch (cause) { recordFailure(cause); setCalendarError(cause instanceof Error ? cause.message : '日历请求结果未知') }
        })
        return
      }
      await execute()
    } catch (cause) { recordFailure(cause); setCalendarError(cause instanceof Error ? cause.message : '无法读取日历') }
    finally { setBusy(false) }
  }

  const calendarReady = status?.mode === 'fake' ? status.authorized : status?.mode === 'real'
    ? status.identity === 'app' ? status.app_configured : status.authorized : false

  return <section className="panel feishu-panel">
    {showAuthorization && <>
    {view === 'all' && <div className="panel-heading"><div><h2>飞书日常</h2><p>{status?.mode === 'real' ? '真实模式 · 应用身份优先；仅妙记搜索与任务列表需要一次性用户授权。' : '模拟模式 · 仅使用合成材料和日程。真实飞书尚未接入。'}</p></div><span className="status-label">{authProblem === 'expired' ? '授权已过期' : authProblem === 'scope' ? '权限不足' : status?.authorized ? '用户已授权' : '用户未授权'}</span></div>}
    <div className="button-row"><button className="button secondary" disabled={busy} onClick={authorize}>{status?.mode === 'real' ? '授权飞书用户身份' : '模拟授权飞书'}</button>{status?.authorized && <button className="button secondary" disabled={busy} onClick={() => setConfirmDisconnect(true)}>断开飞书授权</button>}</div>
    {status?.mode === 'real' && <p className="quiet-empty" role="status">{status.app_configured ? '应用密钥已配置。' : '尚未配置应用密钥。'}{!status.user_identity_verified && ' 用户身份尚未验证。'}</p>}
    {status?.mode === 'real' && <div className="button-row">
      {authorizationUrl && <><a className="button secondary" href={authorizationUrl} target="_blank" rel="noopener noreferrer">打开飞书授权页面</a><span>在浏览器完成后刷新本机授权状态；入口有效期5分钟。注册callback的本机端口须正在运行。刷新只反映当前凭据，不代表用户身份已核验。</span></>}
      <button className="button secondary" disabled={busy} onClick={refreshAuthorization}>刷新用户授权状态</button>
    </div>}
    </>}
    {error && <p role="alert" className="helper-line">{error}</p>}
    {confirmDisconnect && <ConfirmDialog title="断开飞书用户授权？" description="这会清除保存在本机的飞书用户授权。" consequence="不会删除已导入的本机材料；取消不会修改授权状态。" confirmLabel="确认断开授权" busyLabel="正在断开…" busy={busy} danger onCancel={() => setConfirmDisconnect(false)} onConfirm={async () => { await logout(); setConfirmDisconnect(false) }} />}
    {approval && <section className="provider-settings" aria-label="本次真实飞书操作确认"><h3>本次范围预览</h3><p>确认后只执行以下范围。最多 {approval.plan.request_limit} 次 HTTP 请求（包含必要的授权刷新或备用读取）；这是调用次数上限，不是金额上限。失败和未知结果都计入本次额度，不会自动重发。</p>
      {approval.operation === 'feishu.materials.read' && <p>搜索飞书材料：“{String(approval.scope.query || '全部材料')}”；可见范围：{approval.scope.visibility === 'owner' ? '我拥有的' : approval.scope.visibility === 'shared' ? '共享给我的' : '全部可见'}；最多一页、{String(approval.scope.limit)} 条。</p>}
      {approval.operation === 'feishu.materials.import' && <><p>读取并保存以下所选材料正文，仍需之后单独整理和审核：</p><ul>{(approval.scope.material_ids as string[]).map((id) => <li key={id}>{titles[id] ?? '所选材料'}</li>)}</ul></>}
      {approval.operation === 'feishu.calendar.read' && <p>读取日历：{String(approval.scope.start)} 至 {String(approval.scope.end)}（{String(approval.scope.timezone)}），最多一页。</p>}
      {approval.operation === 'feishu.tasks.read' && <p>读取飞书未完成任务，最多 {String(approval.scope.limit)} 条。</p>}
      {approval.operation === 'feishu.task.read' && <p>读取指定任务详情。</p>}
      <div className="button-row"><button className="button primary" disabled={busy} onClick={() => void confirmPlan()}>确认并执行本次读取</button><button className="button secondary" disabled={busy} onClick={() => void cancelPlan()}>取消计划</button></div></section>}
    {(view === 'all' || view === 'materials') && <><h3>材料</h3>{materialsSuccess && <p className="helper-line">上次成功读取：{new Date(materialsSuccess).toLocaleString('zh-CN')}{error ? ' · 本次失败，保留上次结果' : ''}</p>}
    <form className="organize-row" onSubmit={(event) => { event.preventDefault(); setSelected([]); void loadMaterials() }}>
      <label className="compact-field"><span>搜索材料</span><input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <label className="compact-field"><span>可见范围</span><select value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="">全部可见</option><option value="owner">我拥有的</option><option value="shared">共享给我的</option></select></label>
      <button className="button secondary" disabled={!status?.authorized || busy}>搜索 / 刷新材料</button>
    </form>
    {materials && <>
      {materials.items.length === 0 ? <p className="quiet-empty">没有匹配的材料。</p> : <ul className="source-list">{materials.items.map((item) => <li key={item.material_id}><label className="source-row"><input type="checkbox" checked={selected.includes(item.material_id)} disabled={busy} onChange={(event) => setSelected((value) => event.target.checked ? [...value, item.material_id] : value.filter((id) => id !== item.material_id))} /><span className="source-title"><strong>{item.title}</strong><small>{item.visibility === 'owner' ? '我拥有的' : '共享给我的'}</small></span></label></li>)}</ul>}
      <div className="button-row"><button className="button secondary" disabled={busy || !materials.next_cursor} onClick={() => void loadMaterials(materials.next_cursor ?? undefined)}>下一页材料</button><button className="button secondary" disabled={busy || !selected.length} onClick={() => { setSelected([]); operation.current = null }}>取消选择</button><button className="button primary" disabled={busy || !selected.length || unknownImportKey === [...selected].sort().join(',')} onClick={importSelected}>{unknownImportKey === [...selected].sort().join(',') ? '结果未知，先核对收件箱' : `导入所选 · ${selected.length}`}</button></div>
      <p className="helper-line">只读取所选正文并保存原件；导入后仍需明确整理与逐稿审核。</p>
      {selected.length > 0 && unknownImportKey === [...selected].sort().join(',') && <div className="resource-error"><p>本次导入结果未知，不会重发。关闭抽屉并刷新收件箱核对是否已保存。</p><button className="button secondary" onClick={() => void onImported().then(() => onClose?.())}>刷新收件箱并关闭</button></div>}
    </>}
    {imports && <div aria-live="polite"><p>{imports.state === 'succeeded' ? '所选材料已保存到待整理。' : imports.state === 'partial' ? '部分材料导入失败，请查看逐项结果。' : '材料导入失败。'}</p><ul>{imports.outcomes.map((row) => <li key={row.material_id}>{titles[row.material_id] ?? '所选材料'}：{row.state === 'succeeded' ? '已保存原件与待整理项' : row.message}</li>)}</ul></div>}</>}
    {(view === 'all' || view === 'calendar') && <><div className="panel-heading calendar-heading"><div><h3>日历</h3>{calendarSuccess && <p className="helper-line">最近成功读取：{new Date(calendarSuccess).toLocaleString('zh-CN')}{calendarError ? ' · 本次失败，保留上次结果' : ''}</p>}</div><button className="button secondary" disabled={!calendarReady || busy} onClick={() => void loadCalendar()}>{busy ? '正在读取…' : '刷新日历'}</button></div>
    <details className="calendar-range"><summary>调整范围</summary><form className="organize-row" onSubmit={(event) => void loadCalendar(event)}>
      <label className="compact-field"><span>开始日期</span><input type="date" required value={start} onChange={(event) => setStart(event.target.value)} /></label>
      <label className="compact-field"><span>结束日期（不含）</span><input type="date" required value={end} onChange={(event) => setEnd(event.target.value)} /></label>
      <label className="compact-field"><span>时区</span><select value={timezone} onChange={(event) => setTimezone(event.target.value)}>{[...new Set([timezone, 'Asia/Shanghai', 'UTC'])].map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="button secondary" disabled={!calendarReady || busy}>按此范围刷新</button>
    </form></details>
    {calendarError && <p role="alert">{calendarError}；保留已有结果，读取失败不表示没有日程。</p>}
    {!calendar && !calendarError && <p className="quiet-empty">尚未读取日历。</p>}
    {calendar && <>{calendar.items.length === 0 ? <p className="quiet-empty">所选时间内没有日程。</p> : <ul className="source-list">{calendar.items.map((row) => <li key={row.event_id}><div className="source-row"><span className="source-title"><strong>{row.title}</strong><small>{new Date(row.start).toLocaleString('zh-CN', { timeZone: timezone })} — {new Date(row.end).toLocaleString('zh-CN', { timeZone: timezone })}</small></span></div></li>)}</ul>}{calendar.truncated && <p role="status">仅显示部分日程，请缩小时间范围。</p>}{!calendar.truncated && <button className="button secondary" disabled={busy || !calendar.next_cursor} onClick={() => void loadCalendar(undefined, calendar.next_cursor ?? undefined)}>下一页日程</button>}</>}</>}
  </section>
}
