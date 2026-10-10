import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, api, newOperationId } from '../api/client'
import type { components } from '../api/generated'

type Status = components['schemas']['FeishuStatus']
type Materials = components['schemas']['MaterialPage']
type Calendar = components['schemas']['CalendarPage']
type Imports = components['schemas']['ImportResult']
type Authorization = components['schemas']['AuthorizationStart']
const prefix = '/integrations/feishu'

export function FeishuPanel({ onImported }: { onImported: () => Promise<void> }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [authProblem, setAuthProblem] = useState<'expired' | 'scope' | null>(null)
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [visibility, setVisibility] = useState('')
  const [materials, setMaterials] = useState<Materials | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [imports, setImports] = useState<Imports | null>(null)
  const [calendar, setCalendar] = useState<Calendar | null>(null)
  const [calendarError, setCalendarError] = useState('')
  const [start, setStart] = useState(() => new Date().toLocaleDateString('en-CA'))
  const [end, setEnd] = useState(() => new Date(Date.now() + 86400000).toLocaleDateString('en-CA'))
  const [timezone, setTimezone] = useState('Asia/Shanghai')
  const [titles, setTitles] = useState<Record<string, string>>({})
  const operation = useRef<{ key: string; id: string } | null>(null)

  useEffect(() => {
    let alive = true
    api.get<Status>(prefix + '/status').then((value) => { if (alive) setStatus(value) })
      .catch((cause: unknown) => { if (alive) setError(cause instanceof Error ? cause.message : '无法读取授权状态') })
    return () => { alive = false }
  }, [])

  function recordAuthProblem(code?: string) {
    if (code === 'token_expired' || code === 'not_authorized') {
      setStatus((current) => current ? { ...current, authorized: false, scopes: [] } : null)
      setAuthProblem(code === 'token_expired' ? 'expired' : null)
      setSelected([]); setMaterials(null); setCalendar(null)
    } else if (code === 'missing_scope') {
      setAuthProblem((current) => current === 'expired' ? current : 'scope')
    }
  }

  function recordFailure(cause: unknown) {
    if (cause instanceof ApiError) recordAuthProblem(cause.code)
  }

  async function authorize() {
    setBusy(true); setError('')
    try {
      const result = await api.post<Authorization>(prefix + '/authorizations', {})
      const value = await api.oauthCallback<Status>(result.authorization_url)
      setStatus(value); setAuthProblem(null)
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '授权失败') }
    finally { setBusy(false) }
  }

  async function loadMaterials(cursor?: string) {
    setBusy(true); setError('')
    try {
      const params = new URLSearchParams({ query, limit: '20' })
      if (visibility) params.set('visibility', visibility)
      if (cursor) params.set('cursor', cursor)
      const value = await api.get<Materials>(prefix + '/materials?' + params)
      setTitles((current) => ({ ...current, ...Object.fromEntries(value.items.map((item) => [item.material_id, item.title])) }))
      setMaterials(value)
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '无法读取材料'); setMaterials(null) }
    finally { setBusy(false) }
  }

  async function importSelected() {
    const key = [...selected].sort().join(',')
    if (!operation.current || operation.current.key !== key) operation.current = { key, id: newOperationId() }
    setBusy(true); setError('')
    try {
      const result = await api.post<Imports>(prefix + '/imports', { material_ids: selected, operation_id: operation.current.id })
      setImports(result); setSelected([]); operation.current = null
      for (const outcome of result.outcomes) recordAuthProblem(outcome.error_code ?? undefined)
      await onImported()
    } catch (cause) { recordFailure(cause); setError(cause instanceof Error ? cause.message : '导入失败，请重试同一选择') }
    finally { setBusy(false) }
  }

  async function loadCalendar(event?: FormEvent, cursor?: string) {
    event?.preventDefault(); setBusy(true); setCalendarError('')
    try {
      const params = new URLSearchParams({ start: start + 'T00:00:00' + (timezone === 'UTC' ? 'Z' : '+08:00'), end: end + 'T00:00:00' + (timezone === 'UTC' ? 'Z' : '+08:00'), timezone, limit: '20' })
      if (cursor) params.set('cursor', cursor)
      setCalendar(await api.get<Calendar>(prefix + '/calendar?' + params))
    } catch (cause) { recordFailure(cause); setCalendar(null); setCalendarError(cause instanceof Error ? cause.message : '无法读取日历') }
    finally { setBusy(false) }
  }

  return <section className="panel feishu-panel">
    <div className="panel-heading"><div><h2>飞书日常</h2><p>模拟模式 · 仅使用合成材料和日程。真实飞书尚未接入。</p></div><span className="status-label">{authProblem === 'expired' ? '授权已过期' : authProblem === 'scope' ? '权限不足' : status?.authorized ? '已授权' : '未授权'}</span></div>
    <div className="button-row"><button className="button secondary" disabled={busy} onClick={authorize}>模拟授权飞书</button></div>
    {error && <p role="alert" className="helper-line">{error}</p>}
    <h3>材料</h3>
    <form className="organize-row" onSubmit={(event) => { event.preventDefault(); setSelected([]); void loadMaterials() }}>
      <label className="compact-field"><span>搜索材料</span><input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <label className="compact-field"><span>可见范围</span><select value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="">全部可见</option><option value="owner">我拥有的</option><option value="shared">共享给我的</option></select></label>
      <button className="button secondary" disabled={!status?.authorized || busy}>搜索 / 刷新材料</button>
    </form>
    {materials && <>
      {materials.items.length === 0 ? <p className="quiet-empty">没有匹配的材料。</p> : <ul className="source-list">{materials.items.map((item) => <li key={item.material_id}><label className="source-row"><input type="checkbox" checked={selected.includes(item.material_id)} disabled={busy} onChange={(event) => setSelected((value) => event.target.checked ? [...value, item.material_id] : value.filter((id) => id !== item.material_id))} /><span className="source-title"><strong>{item.title}</strong><small>{item.visibility === 'owner' ? '我拥有的' : '共享给我的'}</small></span></label></li>)}</ul>}
      <div className="button-row"><button className="button secondary" disabled={busy || !materials.next_cursor} onClick={() => void loadMaterials(materials.next_cursor ?? undefined)}>下一页材料</button><button className="button secondary" disabled={busy || !selected.length} onClick={() => { setSelected([]); operation.current = null }}>取消选择</button><button className="button primary" disabled={busy || !selected.length} onClick={importSelected}>导入所选 · {selected.length}</button></div>
      <p className="helper-line">只读取所选正文并保存原件；导入后仍需明确整理与逐稿审核。</p>
    </>}
    {imports && <div aria-live="polite"><p>{imports.state === 'succeeded' ? '所选材料已保存到待整理。' : imports.state === 'partial' ? '部分材料导入失败，请查看逐项结果。' : '材料导入失败。'}</p><ul>{imports.outcomes.map((row) => <li key={row.material_id}>{titles[row.material_id] ?? '所选材料'}：{row.state === 'succeeded' ? '已保存原件与待整理项' : row.message}<details><summary>来源标识</summary><code>{row.material_id}</code></details></li>)}</ul></div>}
    <h3>日历</h3>
    <form className="organize-row" onSubmit={(event) => void loadCalendar(event)}>
      <label className="compact-field"><span>开始日期</span><input type="date" required value={start} onChange={(event) => setStart(event.target.value)} /></label>
      <label className="compact-field"><span>结束日期（不含）</span><input type="date" required value={end} onChange={(event) => setEnd(event.target.value)} /></label>
      <label className="compact-field"><span>时区</span><select value={timezone} onChange={(event) => setTimezone(event.target.value)}><option>Asia/Shanghai</option><option>UTC</option></select></label>
      <button className="button secondary" disabled={!status?.authorized || busy}>刷新日历</button>
    </form>
    {calendarError && <p role="alert">{calendarError}</p>}
    {calendar && <>{calendar.items.length === 0 ? <p className="quiet-empty">所选时间内没有日程。</p> : <ul className="source-list">{calendar.items.map((row) => <li key={row.event_id}><div className="source-row"><span className="source-title"><strong>{row.title}</strong><small>{new Date(row.start).toLocaleString('zh-CN', { timeZone: timezone })} — {new Date(row.end).toLocaleString('zh-CN', { timeZone: timezone })}</small></span></div></li>)}</ul>}<button className="button secondary" disabled={busy || !calendar.next_cursor} onClick={() => void loadCalendar(undefined, calendar.next_cursor ?? undefined)}>下一页日程</button></>}
  </section>
}
