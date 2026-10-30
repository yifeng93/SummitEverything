import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, Lightbulb, RefreshCw } from 'lucide-react'
import { api, newOperationId, type ActionCandidate, type IntakeItem, type Project } from '../api/client'
import type { ToastKind } from '../toast'
import { FeishuPanel } from './FeishuPanel'
import { TasksPanel } from './TasksPanel'
import { ImportDrawer } from './ImportDrawer'
import { JournalDialog } from './JournalDialog'
import { PageHeader } from './PageHeader'
import type { ApprovalTarget } from '../approvalTarget'

type Props = { onError: (message: string, kind?: ToastKind) => void; onOpenPage?: (id: string) => void; onOpenApproval?: (target?: ApprovalTarget) => void; onInboxChanged?: () => void; onAuthorizationChanged?: () => void; onOpenConnectionWizard?: () => void; calendarDedupeScope?: string; profileId?: string; workspaceId?: string }

export function TodayView({ onError, onOpenPage = () => {}, onOpenApproval, onInboxChanged, onAuthorizationChanged, onOpenConnectionWizard, calendarDedupeScope, profileId = 'default', workspaceId = 'default' }: Props) {
  const [inbox, setInbox] = useState<IntakeItem[] | null>(null)
  const [inboxError, setInboxError] = useState('')
  const [receipt, setReceipt] = useState<{ itemIds: string[]; message: string } | null>(null)
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
      setInbox(rows); setInboxError('')
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
      const saved = await api.post<IntakeItem>('/intake/items', { text: value, filename: '快速记录.md', operation_id: operationId })
      quickOperation.current = null
      setQuickText(''); setReceipt({ itemIds: [saved.item_id], message: '原文已保存到待整理。不会调用模型。' }); await refreshInbox(); onInboxChanged?.()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '记录暂未保存') }
    finally { busyRef.current = false; setBusy(false) }
  }

  const suggestions = (actions ?? []).filter((item) => item.state === 'proposed' || item.state === 'pending')
  const recentItems = [...(inbox ?? [])].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, 5)

  return <section className="content-wrap today-view">
    <PageHeader
      title="今日"
      meta={<span className="date-label">{new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(today)}</span>}
    />
    <div className="today-columns">
      <section className="panel today-schedule" role="region" aria-label="今天的安排">
        <div className="schedule-block">
          <FeishuPanel compact view="calendar" showAuthorization={false} onImported={refreshInbox} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} onOpenConnectionWizard={onOpenConnectionWizard} dedupeScope={calendarDedupeScope ?? `${profileId}:${workspaceId}`} />
        </div>
        <div className="schedule-block">
          <TasksPanel projects={projects} candidates={[]} mode={feishuMode} readOnly compact />
        </div>
        {suggestions.length > 0 && <div className="schedule-block">
          <div className="section-head"><h3>需要行动</h3><button className="text-button" onClick={() => onOpenApproval?.()}>去审批查看</button></div>
          <ul className="candidate-list">{suggestions.map((item) => <li key={item.action_id}><span className="candidate-dot" aria-hidden="true"><Lightbulb size={12} strokeWidth={1.75} /></span><div><strong>{item.description}</strong><small>尚未确认，不会自动执行</small></div></li>)}</ul>
        </div>}
      </section>
      <section className="panel capture-panel" role="region" aria-label="记录与导入">
        <div className="section-head">
          <div>
            <h2>记录与导入</h2>
          </div>
          <div className="section-actions">
            <button className="text-button quiet" onClick={() => setImportOpen(true)}>导入材料</button>
            <button className="text-button quiet" onClick={() => setJournalOpen(true)}>工作日志 / 思考</button>
          </div>
        </div>
        <label className="sr-only" htmlFor="today-quick-note">记下一句话</label>
        <textarea id="today-quick-note" value={quickText} disabled={busy} onChange={(event) => setQuickText(event.target.value)} placeholder="写下一句话…" rows={3} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void saveQuickNote() } }} />
        <div className="capture-actions">
          <button className="button primary" disabled={!quickText.trim() || busy} onClick={() => void saveQuickNote()}>{busy ? '保存中…' : '保存原文'}</button>
        </div>
        {receipt && <div className="save-receipt" role="status" aria-label="原文已保存"><span>{receipt.message}</span><button className="text-button" onClick={() => onOpenApproval?.({ kind: 'source', itemIds: receipt.itemIds })}>继续整理</button></div>}
        <section className="recent-materials" aria-labelledby="recent-materials-heading">
          <div className="section-head">
            <div>
              <h3 id="recent-materials-heading">最近材料</h3>
              {inboxError && <p className="section-note">读取失败：{inboxError}；保留已有内容</p>}
            </div>
            <div className="section-actions">
              <button className="text-button quiet" onClick={() => onOpenApproval?.()}>全部材料</button>
              <button className="icon-button" aria-label="刷新最近材料" title="刷新最近材料" onClick={() => void refreshInbox()}><RefreshCw size={15} strokeWidth={1.75} aria-hidden="true" /></button>
            </div>
          </div>
          {inbox === null ? inboxError ? <p role="alert" className="helper-line">材料读取失败：{inboxError}。可重试读取。</p> : <p role="status" className="empty-row">正在读取材料…</p> : recentItems.length === 0 ? <p className="quiet-empty">还没有最近材料。</p> : <ul className="source-list">{recentItems.map((item) => <li key={item.item_id}><div className="source-row"><span className="file-glyph" aria-hidden="true"><FileText size={14} strokeWidth={1.75} /></span><span className="source-title"><strong>{item.title}</strong><small>{{quick_note: '记一句', file: '本机文件', feishu_material: '飞书材料', unknown: '来源类型待核实'}[item.origin_kind ?? 'unknown']} · {{pending: '待整理', processing: '整理中', reviewing: '待审核', completed: '已完成', failed: '整理失败', cancelled: '已取消', unknown: '请求状态未知'}[item.state]}</small></span></div></li>)}</ul>}
        </section>
      </section>
    </div>
    {importOpen && <ImportDrawer onClose={() => setImportOpen(false)} onImported={async (itemIds) => { await refreshInbox(); if (itemIds?.length) setReceipt({ itemIds, message: `${itemIds.length} 项原件已保存到待整理。不会调用模型。` }); onInboxChanged?.() }} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} />}
    {journalOpen && <JournalDialog onClose={() => setJournalOpen(false)} onError={onError} onOpenPage={onOpenPage} />}
  </section>
}
