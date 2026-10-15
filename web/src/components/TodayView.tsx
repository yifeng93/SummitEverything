import { useCallback, useEffect, useRef, useState } from 'react'
import { api, newOperationId, type ActionCandidate, type IntakeItem, type Project } from '../api/client'
import type { ToastKind } from '../toast'
import { FeishuPanel } from './FeishuPanel'
import { TasksPanel } from './TasksPanel'
import { ImportDrawer } from './ImportDrawer'
import { JournalDialog } from './JournalDialog'

type Props = { onError: (message: string, kind?: ToastKind) => void; onOpenPage?: (id: string) => void; onOpenApproval?: () => void; onInboxChanged?: () => void; onAuthorizationChanged?: () => void }

export function TodayView({ onError, onOpenPage = () => {}, onOpenApproval, onInboxChanged, onAuthorizationChanged }: Props) {
  const [inbox, setInbox] = useState<IntakeItem[] | null>(null)
  const [inboxError, setInboxError] = useState('')
  const [inboxSuccess, setInboxSuccess] = useState<string | null>(null)
  const [actions, setActions] = useState<ActionCandidate[] | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [feishuMode, setFeishuMode] = useState<'fake' | 'real' | null>(null)
  const [quickText, setQuickText] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const [importOpen, setImportOpen] = useState(false)
  const [journalOpen, setJournalOpen] = useState(false)
  const [today] = useState(() => new Date())
  const quickOperation = useRef<{ text: string; id: string } | null>(null)

  const refreshInbox = useCallback(async () => {
    try {
      const rows = await api.get<IntakeItem[]>('/intake/items')
      setInbox(rows); setInboxError(''); setInboxSuccess(new Date().toISOString())
    } catch (cause) { setInboxError(cause instanceof Error ? cause.message : '收件箱读取失败') }
  }, [])

  useEffect(() => {
    let alive = true
    queueMicrotask(() => {
      void api.get<Project[]>('/projects').then((nextProjects) => { if (alive) setProjects(nextProjects) }).catch(() => { /* Optional local context. */ })
      void api.get<ActionCandidate[]>('/actions').then((value) => { if (alive) setActions(value) }).catch(() => { if (alive) setActions(null) })
      void refreshInbox()
    })
    return () => { alive = false }
  }, [refreshInbox])

  async function saveQuickNote() {
    if (!quickText.trim() || busyRef.current) return
    const value = quickText
    if (!quickOperation.current || quickOperation.current.text !== value) quickOperation.current = { text: value, id: newOperationId() }
    const operationId = quickOperation.current.id
    busyRef.current = true
    setBusy(true)
    try {
      await api.post<IntakeItem>('/intake/items', { text: value, filename: '快速记录.md', operation_id: operationId })
      quickOperation.current = null
      setQuickText(''); await refreshInbox(); onInboxChanged?.()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '记录暂未保存') }
    finally { busyRef.current = false; setBusy(false) }
  }

  const suggestions = (actions ?? []).filter((item) => item.state === 'proposed' || item.state === 'pending')
  const inboxCounts = inbox?.reduce<Record<string, number>>((all, item) => { all[item.origin_kind ?? 'unknown'] = (all[item.origin_kind ?? 'unknown'] ?? 0) + 1; return all }, {}) ?? {}
  const stamp = (value: string | null) => value ? `最近成功读取 ${new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}` : '尚未成功读取'

  return <section className="content-wrap today-view">
    <div className="page-heading"><div><div className="eyebrow">工作节奏</div><h1>今日</h1><p className="lede">先看今天的安排，再把新材料放进收件箱。</p></div><div className="date-label">{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(today)}</div></div>
    <div className="today-stack">
      <section className="panel today-section"><div className="panel-heading"><div><h2>会议</h2><p>只读日历；刷新真实日历前会先预览并确认范围。</p></div></div><FeishuPanel view="calendar" showAuthorization={false} onImported={refreshInbox} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} /><p className="helper-line">需要授权时，请到设置向导第 4 步处理。</p></section>
      <section className="panel today-section"><div className="panel-heading"><div><h2>待办任务</h2><p>任务事实来自飞书；这里仅供查看，真实任务修改请在飞书处理。</p></div></div><TasksPanel projects={projects} candidates={[]} mode={feishuMode} readOnly /><p className="helper-line">模拟环境中的完整动作复演可在“审批”中查看；项目进度变化仍需单独确认。</p></section>
      {suggestions.length > 0 && <section className="panel today-section"><div className="panel-heading"><div><h2>需要行动</h2><p>以下是已保存的待确认建议。</p></div><button className="button secondary" onClick={onOpenApproval}>去审批查看</button></div><ul className="candidate-list">{suggestions.map((item) => <li key={item.action_id}><span className="candidate-dot">提</span><div><strong>{item.description}</strong><small>尚未确认，不会自动执行</small></div></li>)}</ul></section>}
      <section className="panel today-section capture-panel"><div className="panel-heading"><div><h2>收件箱</h2><p>记一句只保存原文；导入会议用于本机文件或飞书材料。两者都会先进入待整理。</p></div><div className="review-actions"><span className="count-badge">{inbox === null ? '…' : inbox.length}</span><button className="text-button" onClick={() => void refreshInbox()}>刷新收件箱</button></div></div>
        <div className="today-tools"><button className="button secondary" onClick={() => document.getElementById('today-quick-note')?.focus()}>记一句</button><button className="button secondary" onClick={() => setImportOpen(true)}>导入会议</button></div>
        <label className="sr-only" htmlFor="today-quick-note">记下一句话</label><textarea id="today-quick-note" value={quickText} disabled={busy} onChange={(event) => setQuickText(event.target.value)} placeholder="写下一句话…" rows={3} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void saveQuickNote() } }} />
        <div className="button-row"><button className="button primary" disabled={!quickText.trim() || busy} onClick={() => void saveQuickNote()}>{busy ? '保存中…' : '保存到收件箱'}</button><button className="button secondary" onClick={() => setJournalOpen(true)}>工作日志 / 思考</button></div>
        <p className="helper-line">{stamp(inboxSuccess)}{inboxError ? ` · 上次读取失败：${inboxError}；保留已有内容` : ''}</p>
        {inbox === null ? inboxError ? <p role="alert">收件箱读取失败：{inboxError}。尚未获得可显示的数据。</p> : <p role="status">正在读取收件箱…</p> : inbox.length === 0 ? <p className="quiet-empty">收件箱目前没有内容。</p> : <ul className="source-list">{inbox.slice(0, 8).map((item) => <li key={item.item_id}><div className="source-row"><span className="file-glyph" aria-hidden="true">文</span><span className="source-title"><strong>{item.title}</strong><small>{{quick_note: '记一句', file: '本机文件', feishu_material: '飞书材料', unknown: '来源类型待核实'}[item.origin_kind ?? 'unknown']} · {{pending: '待整理', processing: '整理中', reviewing: '待审核', completed: '已完成', failed: '整理失败', cancelled: '已取消', unknown: '请求状态未知'}[item.state]}</small></span></div></li>)}</ul>}
        <div className="inbox-counts" aria-label="收件箱来源分类">{(['quick_note', 'file', 'feishu_material', 'unknown'] as const).map((kind) => <span key={kind}>{ { quick_note: '记一句', file: '本机文件', feishu_material: '飞书材料', unknown: '待核实' }[kind] } {inboxCounts[kind] ?? 0}</span>)}</div>
      </section>
    </div>
    {importOpen && <ImportDrawer onClose={() => setImportOpen(false)} onImported={async () => { await refreshInbox(); onInboxChanged?.() }} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} />}
    {journalOpen && <JournalDialog onClose={() => setJournalOpen(false)} onError={(message) => onError(message)} onOpenPage={onOpenPage} />}
  </section>
}
