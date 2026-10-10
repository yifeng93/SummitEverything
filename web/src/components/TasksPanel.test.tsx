import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TodayView } from './TodayView'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function boundary(state = 'succeeded', loseExecution = false) {
  let action: Record<string, unknown> | null = null
  const requests: { path: string; method: string; body: Record<string, unknown> }[] = []
  let next = 0
  vi.stubGlobal('crypto', { randomUUID: () => 'intent-' + (++next) })
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input), method = init?.method || 'GET', body = init?.body ? JSON.parse(String(init.body)) : {}
    requests.push({ path, method, body })
    let data: unknown = []
    if (path.endsWith('/status')) data = { mode: 'fake', authorized: true, scopes: [], token_type: 'user' }
    if (path.includes('/action-intents?')) data = { items: action ? [action] : [], next_cursor: null }
    if (path.includes('/tasks?')) data = { items: [{ guid: 'remote-task', summary: '远端任务', description: '保留描述', due: null, completed_at: 0 }], next_cursor: null }
    if (path.endsWith('/projects')) data = [{ id: 'project', name: '模拟项目', progress: '准备中', progress_version: 2 }, { id: 'other-project', name: '另一个模拟项目', progress: '', progress_version: 7 }]
    if (path.endsWith('/actions') && method === 'POST') { action = { ...body, state: 'proposed', payload_sha256: 'hash', confirmation_id: null, evidence: [] }; data = action }
    if (path.includes('/actions/') && method === 'PATCH') { action = { ...action, payload: body.payload, payload_sha256: 'edited-hash', confirmation_id: null, state: 'proposed', evidence: [{ kind: 'invalidated_confirmation', confirmation_id: 'old-confirmation', payload_sha256: 'old-hash', at: '2026-10-10T00:00:00Z' }] }; data = action }
    if (path.endsWith('/confirmations')) { action = { ...action, ...body, state: 'confirmed' }; data = action }
    if (path.endsWith('/executions')) { action = { ...action, state }; data = action; if (loseExecution) throw new TypeError('模拟响应丢失') }
    if (path.includes('/actions/') && method === 'GET') data = action
    if (path.endsWith('/reconciliations')) { action = { ...action, evidence: [{ kind: 'provider_lookup', found: false }], state: 'unknown' }; data = action }
    return { ok: true, status: 200, json: async () => data }
  }))
  return requests
}

it('requires explicit title/date, final values and separate confirmation before execution', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '新建飞书任务' }))
  expect(screen.getByRole('button', { name: '审阅任务内容' }).hasAttribute('disabled')).toBe(true)
  fireEvent.change(screen.getByLabelText('任务标题'), { target: { value: '用户填写任务' } })
  fireEvent.change(screen.getByLabelText('截止日期方式'), { target: { value: 'none' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅任务内容' }))
  expect(await screen.findByText('用户填写任务', { selector: 'dd' })).toBeTruthy()
  expect(screen.getByText('不设截止日期')).toBeTruthy()
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '独立确认此动作' }))
  expect(await screen.findByRole('button', { name: '执行已确认动作' })).toBeTruthy()
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '执行已确认动作' }))
  expect(await screen.findByText('动作已成功')).toBeTruthy()
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(1)
})

it('refresh/completion only propose and edit clears confirmation', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  expect(requests.filter((item) => item.method === 'POST')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: '完成远端任务' }))
  await screen.findByRole('button', { name: '独立确认此动作' })
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(0)
  expect(requests.find((item) => item.path.endsWith('/actions') && item.method === 'POST')?.body).toMatchObject({ kind: 'feishu_task_complete', payload: { task_guid: 'remote-task' } })
  fireEvent.click(screen.getByRole('button', { name: '独立确认此动作' }))
  await screen.findByRole('button', { name: '执行已确认动作' })
  fireEvent.click(screen.getByRole('button', { name: '修改动作内容' }))
  fireEvent.change(screen.getByLabelText('待完成任务标识'), { target: { value: 'other-task' } })
  fireEvent.click(screen.getByRole('button', { name: '保存修改并重新审阅' }))
  expect(await screen.findByRole('button', { name: '独立确认此动作' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: '执行已确认动作' })).toBeNull()
  expect(screen.getByText('确认已失效；修改后的动作需要重新独立确认。')).toBeTruthy()
  expect(screen.queryByText('执行中断，等待核实。')).toBeNull()
})

it('unknown offers read-only lookup evidence without executing again', async () => {
  const requests = boundary('unknown')
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '完成远端任务' }))
  fireEvent.click(await screen.findByRole('button', { name: '独立确认此动作' }))
  fireEvent.click(await screen.findByRole('button', { name: '执行已确认动作' }))
  expect(await screen.findByText('结果未知，请核实；此动作不会重发。')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '只读核实远端结果' }))
  expect(await screen.findByText('未找到明确执行证据，仍为未知。')).toBeTruthy()
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(1)
  expect(screen.queryByRole('button', { name: '执行已确认动作' })).toBeNull()
})

it('progress shows exact version and requires its own confirmation', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '拟定项目进度变化' }))
  fireEvent.change(screen.getByLabelText('进度项目'), { target: { value: 'project' } })
  fireEvent.change(screen.getByLabelText('新的项目进度'), { target: { value: '已完成准备' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅进度变化' }))
  expect(await screen.findByText('已完成准备', { selector: 'dd' })).toBeTruthy()
  expect(screen.getByText('准备中 → 已完成准备')).toBeTruthy()
  expect(requests.find((item) => item.path.endsWith('/actions') && item.method === 'POST')?.body).toMatchObject({ kind: 'project_progress', payload: { project_id: 'project', expected_version: 2, progress: '已完成准备' } })
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(0)
})

it('completion starts a separate intent while another action is being edited', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '新建飞书任务' }))
  fireEvent.change(screen.getByLabelText('任务标题'), { target: { value: '待审标题' } })
  fireEvent.change(screen.getByLabelText('截止日期方式'), { target: { value: 'none' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅任务内容' }))
  fireEvent.click(await screen.findByRole('button', { name: '修改动作内容' }))
  fireEvent.click(screen.getByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '完成远端任务' }))
  await screen.findByRole('button', { name: '独立确认此动作' })
  const proposals = requests.filter((item) => item.path.endsWith('/actions') && item.method === 'POST')
  expect(proposals).toHaveLength(2)
  expect(proposals[1]?.body).toMatchObject({ kind: 'feishu_task_complete', payload: { task_guid: 'remote-task' }, candidate_id: null })
  expect(requests.filter((item) => item.method === 'PATCH')).toHaveLength(0)
})

it('task edits send only selected due semantics and preserve other fields', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '编辑远端任务' }))
  fireEvent.click(screen.getByLabelText('截止日期', { selector: 'input[type="checkbox"]' }))
  fireEvent.change(screen.getByLabelText('截止日期方式'), { target: { value: 'time' } })
  fireEvent.change(screen.getByLabelText('截止日期', { selector: 'input[type="text"]' }), { target: { value: '2026-10-13T09:00:00+08:00' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅任务内容' }))
  expect(await screen.findByRole('button', { name: '独立确认此动作' })).toBeTruthy()
  expect(requests.find((item) => item.path.endsWith('/actions') && item.method === 'POST')?.body).toMatchObject({ kind: 'feishu_task_update', payload: { task_guid: 'remote-task', task: { due: { value: '2026-10-13T09:00:00+08:00', is_all_day: false, timezone: 'Asia/Shanghai' } }, update_fields: ['due'] } })
})


it('lost execution response reads the same intent and never posts another execution', async () => {
  const requests = boundary('succeeded', true)
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '完成远端任务' }))
  fireEvent.click(await screen.findByRole('button', { name: '独立确认此动作' }))
  fireEvent.click(await screen.findByRole('button', { name: '执行已确认动作' }))
  expect(await screen.findByText('动作已成功')).toBeTruthy()
  expect(requests.filter((item) => item.path.endsWith('/executions'))).toHaveLength(1)
  const execution = requests.find((item) => item.path.endsWith('/executions'))!
  expect(requests.some((item) => item.path === execution.path.replace('/executions', '') && item.method === 'GET')).toBe(true)
  expect(screen.queryByRole('button', { name: '执行已确认动作' })).toBeNull()
})

it('completion review reflects edited target rather than a stale task title', async () => {
  boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '完成远端任务' }))
  fireEvent.click(await screen.findByRole('button', { name: '修改动作内容' }))
  fireEvent.change(screen.getByLabelText('待完成任务标识'), { target: { value: 'other-task' } })
  fireEvent.click(screen.getByRole('button', { name: '保存修改并重新审阅' }))
  await screen.findByRole('button', { name: '独立确认此动作' })
  expect(screen.queryByText('远端任务', { selector: 'dd' })).toBeNull()
  expect(screen.getByText('other-task', { selector: 'dd' })).toBeTruthy()
})

it('edit review identifies unchanged task title when only due is selected', async () => {
  boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '刷新飞书任务' }))
  await screen.findByText('远端任务')
  fireEvent.click(screen.getByRole('button', { name: '编辑远端任务' }))
  fireEvent.click(screen.getByLabelText('截止日期', { selector: 'input[type="checkbox"]' }))
  fireEvent.change(screen.getByLabelText('截止日期方式'), { target: { value: 'none' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅任务内容' }))
  await screen.findByRole('button', { name: '独立确认此动作' })
  expect(screen.getByText('远端任务', { selector: 'dd' })).toBeTruthy()
})

it('changing the progress target reviews the selected project version', async () => {
  const requests = boundary()
  render(<TodayView onError={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: '拟定项目进度变化' }))
  fireEvent.change(screen.getByLabelText('进度项目'), { target: { value: 'project' } })
  fireEvent.change(screen.getByLabelText('新的项目进度'), { target: { value: '已完成准备' } })
  fireEvent.click(screen.getByRole('button', { name: '审阅进度变化' }))
  fireEvent.click(await screen.findByRole('button', { name: '修改动作内容' }))
  fireEvent.change(screen.getByLabelText('进度项目'), { target: { value: 'other-project' } })
  fireEvent.click(screen.getByRole('button', { name: '保存修改并重新审阅' }))
  await screen.findByRole('button', { name: '独立确认此动作' })
  expect(requests.find((item) => item.method === 'PATCH')?.body).toMatchObject({ payload: { project_id: 'other-project', expected_version: 7 } })
})
