import { useCallback, useEffect, useRef, useState } from 'react'
import { api, newOperationId, type ActionCandidate, type IntakeItem, type Project } from '../api/client'
import type { ToastKind } from '../toast'
import { FeishuPanel } from './FeishuPanel'
import { TasksPanel } from './TasksPanel'
import { ImportDrawer } from './ImportDrawer'
import { JournalDialog } from './JournalDialog'
import type { ApprovalTarget } from '../approvalTarget'

type Props = { onError: (message: string, kind?: ToastKind) => void; onOpenPage?: (id: string) => void; onOpenApproval?: (target?: ApprovalTarget) => void; onInboxChanged?: () => void; onAuthorizationChanged?: () => void }

export function TodayView({ onError, onOpenPage = () => {}, onOpenApproval, onInboxChanged, onAuthorizationChanged }: Props) {
  const [inbox, setInbox] = useState<IntakeItem[] | null>(null)
  const [inboxError, setInboxError] = useState('')
  const [inboxSuccess, setInboxSuccess] = useState<string | null>(null)
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
      const saved = await api.post<IntakeItem>('/intake/items', { text: value, filename: '快速记录.md', operation_id: operationId })
      quickOperation.current = null
      setQuickText(''); setReceipt({ itemIds: [saved.item_id], message: '原文已保存到待整理。不会调用模型。' }); await refreshInbox(); onInboxChanged?.()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '记录暂未保存') }
    finally { busyRef.current = false; setBusy(false) }
  }

  const suggestions = (actions ?? []).filter((item) => item.state === 'proposed' || item.state === 'pending')
  const recentItems = [...(inbox ?? [])].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, 5)
  const stamp = (value: string | null) => value ? `最近成功读取 ${new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}` : '尚未成功读取'

  return <section className="content-wrap today-view">
    <div className="page-heading"><div><div className="eyebrow">工作节奏</div><h1>今日</h1><p className="lede">今天的会和待办在左边，右边可以记下原文或导入材料。</p></div><div className="date-label">{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(today)}</div></div>
    <div className="today-columns">
      <div className="today-schedule" role="region" aria-label="今天的安排">
        <section className="panel today-section"><div className="panel-heading"><div><h2>会议</h2><p>查看日程；读取真实日历前会先预览并确认范围。</p></div></div><FeishuPanel view="calendar" showAuthorization={false} onImported={refreshInbox} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} /><p className="helper-line">需要授权时，可到设置里的连接向导处理。</p></section>
        <section className="panel today-section"><div className="panel-heading"><div><h2>待办任务</h2><p>任务事实来自飞书；这里仅供查看，真实任务修改请在飞书处理。</p></div></div><TasksPanel projects={projects} candidates={[]} mode={feishuMode} readOnly /><p className="helper-line">模拟环境中的动作复演可在审批中查看；项目进度变化仍需单独确认。</p></section>
        {suggestions.length > 0 && <section className="panel today-section"><div className="panel-heading"><div><h2>需要行动</h2><p>以下是已保存的待确认建议。</p></div><button className="button secondary" onClick={() => onOpenApproval?.()}>去审批查看</button></div><ul className="candidate-list">{suggestions.map((item) => <li key={item.action_id}><span className="candidate-dot">提</span><div><strong>{item.description}</strong><small>尚未确认，不会自动执行</small></div></li>)}</ul></section>}
      </div>
      <section className="panel today-section capture-panel" aria-label="记录与导入"><div className="panel-heading"><div><h2>记录与导入</h2><p>先保存原文；整理和模型调用由你之后主动发起。</p></div></div>
        <div className="today-tools"><button className="button secondary" onClick={() => document.getElementById('today-quick-note')?.focus()}>记一句</button><button className="button secondary" onClick={() => setImportOpen(true)}>导入材料</button><button className="button secondary" onClick={() => setJournalOpen(true)}>工作日志 / 思考</button></div>
        <label className="sr-only" htmlFor="today-quick-note">记下一句话</label><textarea id="today-quick-note" value={quickText} disabled={busy} onChange={(event) => setQuickText(event.target.value)} placeholder="写下一句话…" rows={3} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void saveQuickNote() } }} />
        <div className="button-row"><button className="button primary" disabled={!quickText.trim() || busy} onClick={() => void saveQuickNote()}>{busy ? '保存中…' : '保存原文'}</button></div>
        {receipt && <div className="save-receipt" role="status" aria-label="原文已保存"><span>{receipt.message}</span><button className="button secondary" onClick={() => onOpenApproval?.({ kind: 'source', itemIds: receipt.itemIds })}>继续整理</button></div>}
        <section className="recent-materials" aria-labelledby="recent-materials-heading"><div className="panel-heading"><div><h3 id="recent-materials-heading">最近材料</h3><p>{stamp(inboxSuccess)}{inboxError ? ` · 读取失败：${inboxError}；保留已有内容` : ''}</p></div><div className="review-actions"><button className="text-button" onClick={() => void refreshInbox()}>刷新</button><button className="text-button" onClick={() => onOpenApproval?.()}>全部材料</button></div></div>
          {inbox === null ? inboxError ? <p role="alert">材料读取失败：{inboxError}。可重试读取。</p> : <p role="status">正在读取材料…</p> : recentItems.length === 0 ? <p className="quiet-empty">还没有最近材料。</p> : <ul className="source-list">{recentItems.map((item) => <li key={item.item_id}><div className="source-row"><span className="file-glyph" aria-hidden="true">文</span><span className="source-title"><strong>{item.title}</strong><small>{{quick_note: '记一句', file: '本机文件', feishu_material: '飞书材料', unknown: '来源类型待核实'}[item.origin_kind ?? 'unknown']} · {{pending: '待整理', processing: '整理中', reviewing: '待审核', completed: '已完成', failed: '整理失败', cancelled: '已取消', unknown: '请求状态未知'}[item.state]}</small></span></div></li>)}</ul>}
        </section>
      </section>
    </div>
    {importOpen && <ImportDrawer onClose={() => setImportOpen(false)} onImported={async (itemIds) => { await refreshInbox(); if (itemIds?.length) setReceipt({ itemIds, message: `${itemIds.length} 项原件已保存到待整理。不会调用模型。` }); onInboxChanged?.() }} onMode={setFeishuMode} onAuthorizationChanged={onAuthorizationChanged} />}
    {journalOpen && <JournalDialog onClose={() => setJournalOpen(false)} onError={(message) => onError(message)} onOpenPage={onOpenPage} />}
  </section>
}
