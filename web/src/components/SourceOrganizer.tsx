import { useEffect, useState } from 'react'
import { api, newOperationId, type IntakeItem, type Line, type Project } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import type { components } from '../api/generated'

type Plan = { plan_id: string; scope_sha256: string; request_limit: number }
type OutgoingInput = { item_id: string; source_id: string; text: string }
type OrganizeScope = {
  item_ids: string[]; operation_id: string; line_id: string; project_id: string; reprocess: boolean
  max_output_tokens: number; outgoing_inputs: OutgoingInput[]
}
type Pending = {
  body: Record<string, unknown>; plan: Plan | null; scope: OrganizeScope | null; real: boolean
  lineName: string; projectName: string; items: IntakeItem[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validatePreview(plan: Plan, scopeValue: unknown, body: Record<string, unknown>, capturedItems: IntakeItem[]): OrganizeScope {
  if (!plan || typeof plan.plan_id !== 'string' || !plan.plan_id || typeof plan.scope_sha256 !== 'string' || !plan.scope_sha256 || !Number.isInteger(plan.request_limit) || plan.request_limit < 1) {
    throw new Error('无法确认整理范围，请重新预览')
  }
  if (!isRecord(scopeValue)) throw new Error('整理范围缺少原件内容，请重新预览')
  const scope = scopeValue
  const expectedIds = body.item_ids as string[]
  const matches = scope.operation_id === body.operation_id && scope.line_id === body.line_id && scope.project_id === body.project_id && scope.reprocess === body.reprocess
    && Array.isArray(scope.item_ids) && scope.item_ids.length === expectedIds.length && scope.item_ids.every((id, index) => id === expectedIds[index])
    && Number.isInteger(scope.max_output_tokens) && (scope.max_output_tokens as number) > 0
    && Array.isArray(scope.outgoing_inputs) && scope.outgoing_inputs.length === capturedItems.length
  if (!matches) throw new Error('整理范围与所选原件或目标不一致，请重新预览')

  const inputs = scope.outgoing_inputs as unknown[]
  const byId = new Map(capturedItems.map((item) => [item.item_id, item]))
  const seen = new Set<string>()
  for (const value of inputs) {
    if (!isRecord(value) || typeof value.item_id !== 'string' || typeof value.source_id !== 'string' || typeof value.text !== 'string') {
      throw new Error('整理范围缺少完整原件内容，请重新预览')
    }
    const item = byId.get(value.item_id)
    if (!item || item.source_id !== value.source_id || seen.has(value.item_id)) throw new Error('整理范围原件与当前选择不一致，请重新预览')
    seen.add(value.item_id)
  }
  if (seen.size !== capturedItems.length) throw new Error('整理范围原件不完整，请重新预览')
  return scope as unknown as OrganizeScope
}

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
    const capturedLine = lines.find((line) => line.id === selectedLine)
    const capturedProject = projects.find((project) => project.id === selectedProject)
    const capturedItems = [...items]
    if (!capturedLine || !capturedProject || capturedProject.line_id !== selectedLine || capturedProject.archived) {
      onError('所选主线或项目已不可用，请重新选择后预览')
      return
    }
    setBusy(true)
    const capturedReprocess = capturedItems.some((item) => item.state !== 'pending')
    const body = { item_ids: capturedItems.map((item) => item.item_id), line_id: selectedLine, project_id: selectedProject, operation_id: newOperationId(), reprocess: capturedReprocess }
    try {
      const settings = await api.get<components['schemas']['SettingsSummary']>('/settings')
      const real = settings.mode === 'real'
      if (!real && !reprocess) {
        setPending({ body, plan: null, scope: null, real: false, lineName: capturedLine.name, projectName: capturedProject.name, items: capturedItems })
        return
      }
      let plan: Plan | null = null
      let scope: OrganizeScope | null = null
      if (real) {
        const preview = await api.post<{ plan: Plan; scope: unknown }>('/acceptance-plans', { operation: 'model.organize', scope: body })
        plan = preview.plan
        scope = validatePreview(preview.plan, preview.scope, body, capturedItems)
      }
      setPending({ body, plan, scope, real, lineName: capturedLine.name, projectName: capturedProject.name, items: capturedItems })
    } catch (cause) { onError(cause instanceof Error ? cause.message : '无法准备整理范围') }
    finally { setBusy(false) }
  }

  async function confirm() {
    if (!pending) return
    if (pending.real && (!pending.plan || !pending.scope)) {
      onError('整理范围未能完整确认，请关闭后重新预览')
      return
    }
    setBusy(true)
    try {
      if (pending.real && pending.plan && pending.scope) await api.post(`/acceptance-plans/${pending.plan.plan_id}/confirm`, { scope_sha256: pending.plan.scope_sha256, scope: pending.scope })
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
    {pending && <ConfirmDialog title={pending.body.reprocess ? '明确重新整理所选来源？' : '确认整理所选来源？'} description={`将把 ${pending.items.length} 条原件发送给整理流程，在选定项目下生成待审核稿。不会直接写入正式知识。`} consequence={pending.real ? `真实模式将发送所选原件；请求上限 ${pending.plan!.request_limit} 次。` : 'Fake 模式使用本机合成整理流程。'} confirmLabel="确认并整理所选材料" busyLabel="正在整理…" busy={busy} onCancel={() => void cancel()} onConfirm={confirm}>
      <dl className="organize-preview-target"><div><dt>整理到</dt><dd>{pending.lineName} / {pending.projectName}</dd></div>{pending.scope && <><div><dt>请求上限</dt><dd>{pending.plan!.request_limit} 次</dd></div><div><dt>输出上限</dt><dd>{pending.scope.max_output_tokens} token</dd></div></>}</dl>
      <ul>{pending.items.map((item) => <li key={item.item_id}>{item.title} · {({ quick_note: '记一句', file: '文件', feishu_material: '飞书材料', unknown: '来源类型未知' } as Record<string, string>)[item.origin_kind ?? 'unknown']}</li>)}</ul>
      {pending.scope && <details><summary>查看本次范围原文</summary><div className="organize-preview-inputs">{pending.scope.outgoing_inputs.map((input) => {
        const source = pending.items.find((item) => item.item_id === input.item_id)!
        const kind = ({ quick_note: '记一句', file: '文件', feishu_material: '飞书材料', unknown: '来源类型未知' } as Record<string, string>)[source.origin_kind ?? 'unknown']
        return <section key={input.item_id}><h3>{source.title} · {kind}</h3><pre>{input.text}</pre></section>
      })}</div></details>}
    </ConfirmDialog>}
  </div>
}
