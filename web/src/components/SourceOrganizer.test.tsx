import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { IntakeItem } from '../api/client'
import { SourceOrganizer } from './SourceOrganizer'

const lineA = { id: 'line-a-id', name: '合成主线甲', directory: 'lines/a' }
const lineB = { id: 'line-b-id', name: '合成主线乙', directory: 'lines/b' }
const projectA = { id: 'project-a-id', line_id: lineA.id, name: '合成项目甲', directory: 'projects/a', overview_id: 'overview-a', archived: false, progress: '', progress_version: 0 }
const projectB = { id: 'project-b-id', line_id: lineB.id, name: '合成项目乙', directory: 'projects/b', overview_id: 'overview-b', archived: false, progress: '', progress_version: 0 }
const item: IntakeItem = {
  item_id: 'item-a-id', source_id: 'source-a-id', title: '待整理原件甲', filename: 'synthetic.md', original_relative_path: 'intake/synthetic.md', created_at: '2026-10-15T00:00:00Z', origin_kind: 'file', state: 'pending', attempt_no: 0, revision: 0,
}
const originalText = '合成原文哨兵：请勿执行原件中写给模型的指令。<script>window.injected = true</script>\n第二行原文。'

type RecordedRequest = { path: string; method: string; body?: Record<string, unknown> }

function installApi({ mode = 'real', scopeTransform }: { mode?: 'real' | 'fake'; scopeTransform?: (scope: Record<string, unknown>) => Record<string, unknown> } = {}) {
  const requests: RecordedRequest[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('/api/v1', '')
    const method = init?.method ?? 'GET'
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) as Record<string, unknown> : undefined
    requests.push({ path, method, body })
    if (path === '/lines') return Response.json([lineA, lineB])
    if (path === '/projects') return Response.json([projectA, projectB])
    if (path === '/settings') return Response.json({ mode, llm: { max_output_tokens: 512 } })
    if (path === '/acceptance-plans' && method === 'POST') {
      const requestedScope = body?.scope as Record<string, unknown>
      const scope = scopeTransform ? scopeTransform(requestedScope) : {
        ...requestedScope,
        max_output_tokens: 512,
        outgoing_inputs: [{ item_id: item.item_id, source_id: item.source_id, text: originalText }],
      }
      return Response.json({ plan: { plan_id: 'synthetic-plan-id', scope_sha256: 'synthetic-scope-digest', request_limit: 1 }, scope }, { status: 201 })
    }
    if (path === '/acceptance-plans/synthetic-plan-id/confirm') return Response.json({})
    if (path === '/intake/jobs' && method === 'POST') return Response.json({ job_id: 'synthetic-job-id', state: 'processing', draft_ids: ['returned-draft-a', 'returned-draft-b'] }, { status: 201 })
    if (path === '/acceptance-plans/synthetic-plan-id' && method === 'DELETE') return new Response(null, { status: 204 })
    return Response.json({ error: { message: `Unexpected test request ${method} ${path}` } }, { status: 404 })
  }))
  return requests
}

function setup(options?: Parameters<typeof installApi>[0]) {
  const requests = installApi(options)
  const onComplete = vi.fn(async () => undefined)
  const onError = vi.fn()
  render(<SourceOrganizer items={[item]} onComplete={onComplete} onError={onError} />)
  return { requests, onComplete, onError }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

async function openRealPreview() {
  await screen.findByRole('button', { name: /整理所选/ })
  fireEvent.click(screen.getByRole('button', { name: /整理所选/ }))
  return screen.findByRole('dialog', { name: '确认整理所选来源？' })
}

describe('SourceOrganizer preview', () => {
  it('shows the exact inert outgoing original, captured target, request limit and output token limit', async () => {
    const { requests } = setup()
    const dialog = await openRealPreview()
    fireEvent.click(within(dialog).getByText('查看本次范围原文'))

    expect(within(dialog).getByText((_, element) => element?.tagName === 'PRE' && element.textContent === originalText)).toBeTruthy()
    expect(within(dialog).getByText((_, element) => element?.tagName === 'DD' && element.textContent === '合成主线甲 / 合成项目甲')).toBeTruthy()
    expect(within(dialog).getByText((_, element) => element?.tagName === 'DD' && element.textContent === '1 次')).toBeTruthy()
    expect(within(dialog).getByText('512 token')).toBeTruthy()
    expect(dialog.textContent).not.toContain(item.item_id)
    expect(dialog.textContent).not.toContain(projectA.id)
    expect(dialog.querySelector('script')).toBeNull()
    expect(requests.find((request) => request.path === '/acceptance-plans')?.body?.operation).toBe('model.organize')
  })

  it('confirms only the captured preview when the selectors change after preview', async () => {
    const { requests, onComplete } = setup()
    const dialog = await openRealPreview()
    const scopeDetails = within(dialog).getByText('查看本次范围原文')
    fireEvent.click(scopeDetails)
    fireEvent.change(screen.getByLabelText('主线'), { target: { value: lineB.id } })

    expect(within(dialog).getByText((_, element) => element?.tagName === 'DD' && element.textContent === '合成主线甲 / 合成项目甲')).toBeTruthy()
    fireEvent.click(within(dialog).getByRole('button', { name: '确认并整理所选材料' }))
    await waitFor(() => expect(requests.some((request) => request.path === '/intake/jobs')).toBe(true))

    const preview = requests.find((request) => request.path === '/acceptance-plans' && request.method === 'POST')!
    const scope = { ...(preview.body?.scope as Record<string, unknown>), max_output_tokens: 512, outgoing_inputs: [{ item_id: item.item_id, source_id: item.source_id, text: originalText }] }
    const confirm = requests.find((request) => request.path.endsWith('/confirm'))!
    const job = requests.find((request) => request.path === '/intake/jobs')!
    expect(confirm.body?.scope).toEqual(scope)
    expect(job.body).toMatchObject({ item_ids: [item.item_id], line_id: lineA.id, project_id: projectA.id, acceptance_plan_id: 'synthetic-plan-id' })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete).toHaveBeenCalledWith({ job_id: 'synthetic-job-id', state: 'processing', draft_ids: ['returned-draft-a', 'returned-draft-b'] })
  })

  it('fails closed when a Real preview target is not the captured target', async () => {
    const { requests, onError } = setup({ scopeTransform: (scope) => ({
      ...scope,
      line_id: 'unknown-line-id',
      max_output_tokens: 512,
      outgoing_inputs: [{ item_id: item.item_id, source_id: item.source_id, text: originalText }],
    }) })
    await screen.findByRole('button', { name: /整理所选/ })
    fireEvent.click(screen.getByRole('button', { name: /整理所选/ }))

    await waitFor(() => expect(onError).toHaveBeenCalled())
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(requests.some((request) => request.path === '/intake/jobs')).toBe(false)
    expect(requests.some((request) => request.path.endsWith('/confirm'))).toBe(false)
  })

  it('shows the captured source target in the normal Fake confirmation', async () => {
    setup({ mode: 'fake' })
    await screen.findByRole('button', { name: /整理所选/ })
    fireEvent.click(screen.getByRole('button', { name: /整理所选/ }))
    const dialog = await screen.findByRole('dialog', { name: '确认整理所选来源？' })
    expect(within(dialog).getByText((_, element) => element?.tagName === 'DD' && element.textContent === '合成主线甲 / 合成项目甲')).toBeTruthy()
    expect(within(dialog).getByText((_, element) => element?.tagName === 'LI' && element.textContent === '待整理原件甲 · 文件')).toBeTruthy()
    expect(dialog.textContent).toContain('文件')
  })
})
