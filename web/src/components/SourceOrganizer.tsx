import { useEffect, useState } from 'react'
import { api, newOperationId, type IntakeItem, type Line, type Project } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import type { components } from '../api/generated'

type Plan = { plan_id: string; scope_sha256: string; request_limit: number }
type Pending = { body: Record<string, unknown>; plan: Plan | null; scope: Record<string, unknown> | null; real: boolean }

export function SourceOrganizer({ items, onComplete, onError }: { items: IntakeItem[]; onComplete: () => Promise<void>; onError: (message: string) => void }) {
  const [lines, setLines] = useState<Line[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [lineId, setLineId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [pending, setPending] = useState<Pending | null>(null)
  const [busy, setBusy] = useState(false)
  const selectedLine = lineId || lines[0]?.id || ''
  const availableProjects = projects.filter((project) => project.line_id === selectedLine && !project.archived)
  const selectedProject = projectId || availableProjects[0]?.id || ''
  const reprocess = items.some((item) => item.state !== 'pending')

  useEffect(() => {
    if (items.length === 0 || lines.length) return
    void api.get<Line[]>('/lines').then(setLines).catch((cause) => onError(cause instanceof Error ? cause.message : '无法读取主线'))
    void api.get<Project[]>('/projects').then(setProjects).catch((cause) => onError(cause instanceof Error ? cause.message : '无法读取项目'))
  }, [items.length, lines.length, onError])

  async function prepare() {
    if (items.length === 0 || !selectedLine || !selectedProject) return
    setBusy(true)
    const body = { item_ids: items.map((item) => item.item_id), line_id: selectedLine, project_id: selectedProject, operation_id: newOperationId(), reprocess }
    try {
      const settings = await api.get<components['schemas']['SettingsSummary']>('/settings')
      const real = settings.mode === 'real'
      if (!real && !reprocess) {
        setPending({ body, plan: null, scope: null, real: false })
        return
      }
      let plan: Plan | null = null
      let scope: Record<string, unknown> | null = null
      if (real) {
        const preview = await api.post<{ plan: Plan; scope: Record<string, unknown> }>('/acceptance-plans', { operation: 'model.organize', scope: body })
        plan = preview.plan; scope = preview.scope
      }
      setPending({ body, plan, scope, real })
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法准备整理范围') }
    finally { setBusy(false) }
  }

  async function confirm() {
    if (!pending) return
    setBusy(true)
    try {
      if (pending.plan && pending.scope) await api.post(`/acceptance-plans/${pending.plan.plan_id}/confirm`, { scope_sha256: pending.plan.scope_sha256, scope: pending.scope })
      await api.post('/intake/jobs', { ...pending.body, ...(pending.plan ? { acceptance_plan_id: pending.plan.plan_id } : {}) })
      setPending(null)
      await onComplete()
    } catch (cause) { onError(cause instanceof Error ? cause.message : '整理没有完成；请检查当前状态后再决定是否重试') }
    finally { setBusy(false) }
  }

  async function cancel() {
    if (pending?.plan) {
      try { await api.delete(`/acceptance-plans/${pending.plan.plan_id}`) }
      catch (cause) { onError(cause instanceof Error ? cause.message : '无法取消整理范围预览'); return }
    }
    setPending(null)
  }

  if (!items.length) return null
  return <div className="source-organizer">
    <div className="organize-row"><label className="compact-field"><span>主线</span><select value={selectedLine} onChange={(event) => { setLineId(event.target.value); setProjectId('') }}><option value="">选择主线</option>{lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label><label className="compact-field"><span>项目</span><select value={selectedProject} onChange={(event) => setProjectId(event.target.value)}><option value="">选择项目</option>{availableProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label><button className="button primary" disabled={!selectedProject || busy || items.some((item) => ['processing', 'reviewing'].includes(item.state))} onClick={() => void prepare()}>{reprocess ? '明确重新整理' : '整理所选'} · {items.length}</button></div>
    {reprocess && items.some((item) => item.state === 'unknown') && <p className="helper-line">请求结果未知，不会自动重发。重新整理会创建新操作，可能再次调用模型；原件和既有稿件会保留。</p>}
    {(!lines.length || !availableProjects.length) && <p className="helper-line">整理前请先在“项目与知识”建立主线和项目。</p>}
    {pending && <ConfirmDialog title={reprocess ? '明确重新整理所选来源？' : '确认整理所选来源？'} description={`将把 ${items.length} 条原件发送给整理流程，在选定项目下生成待审核稿。不会直接写入正式知识。`} consequence={pending.real ? `真实模式将发送所选原件；请求上限 ${pending.plan?.request_limit ?? '待确认'} 次。` : 'Fake 模式使用本机合成整理流程。'} confirmLabel="确认并整理所选材料" busyLabel="正在整理…" busy={busy} onCancel={() => void cancel()} onConfirm={confirm}><ul>{items.map((item) => <li key={item.item_id}>{item.title} · {({ quick_note: '记一句', file: '文件', feishu_material: '飞书材料', unknown: '来源类型未知' } as Record<string, string>)[item.origin_kind ?? 'unknown']}</li>)}</ul>{pending.scope && <details><summary>查看本次范围</summary><p>范围已在本机生成，确认后才发送。</p></details>}</ConfirmDialog>}
  </div>
}
