import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ApprovalView } from './ApprovalView'
import { approvalPendingCount } from '../approval-summary'
import type { Draft, IntakeItem } from '../api/client'

/**
 * 审批页 · 最小可用版（逐页规格 §3 的分组 1/2）。
 * 边界：五类分组里的 3/4/5、视图筛选与「检查并应用」属于 P3，见 ApprovalView.tsx 顶部注释。
 */

afterEach(cleanup)

const RULE_LOADING = '守卫④（GUIDE §11 ④）：加载中必须显示「正在读取…」，不得画成空态或 0 项'

function intake(overrides: Partial<IntakeItem> & { item_id: string }): IntakeItem {
  return {
    source_id: 'source-1',
    title: '合成来源',
    filename: 'synthetic.txt',
    original_relative_path: '原件/synthetic.txt',
    created_at: '2026-10-14T00:00:00Z',
    state: 'pending',
    ...overrides,
  } as IntakeItem
}

function draft(overrides: Partial<Draft> & { draft_id: string }): Draft {
  return {
    metadata: { title: '合成稿件' },
    source_ids: ['source-1'],
    important_conflicts: [],
    state: 'pending',
    version: 1,
    ...overrides,
  } as unknown as Draft
}

it('加载中显示「正在读取…」，不出现空态文案，也不先报 0 项', () => {
  render(<ApprovalView items={[]} drafts={[]} loading error="" onRetry={vi.fn()} />)

  expect(screen.getAllByText('正在读取…')).toHaveLength(2)
  expect(screen.getByText('正在读取待处理的来源和稿件…')).toBeTruthy()
  expect(screen.queryByText(/待处理 \d+ 项/)).toBeNull()
  expect(screen.queryByText('没有待整理的来源')).toBeNull()
  expect(screen.queryByText('没有待复核的稿件')).toBeNull()
  expect(document.body.textContent, RULE_LOADING).not.toContain('0')
})

it('按现有数据列出两类与数量，已完成/已取消的来源不进清单', () => {
  const items = [
    intake({ item_id: 'a', title: '待整理的会议纪要', state: 'pending' }),
    intake({ item_id: 'b', title: '整理中的材料', state: 'processing' }),
    intake({ item_id: 'c', title: '已经处理完的材料', state: 'completed' }),
    intake({ item_id: 'd', title: '取消掉的材料', state: 'cancelled' }),
  ]
  const drafts = [
    draft({ draft_id: 'x', metadata: { title: '待复核稿件' }, source_ids: ['a', 'b'], important_conflicts: [{}], state: 'pending' }),
    draft({ draft_id: 'y', metadata: { title: '已确认稿件' }, state: 'confirmed' }),
  ]
  render(<ApprovalView items={items} drafts={drafts} loading={false} error="" onRetry={vi.fn()} />)

  expect(screen.getByText(/待处理 3 项 · 共 2 类/)).toBeTruthy()
  expect(approvalPendingCount(items, drafts)).toBe(3)

  const intakeGroup = screen.getByRole('region', { name: '待整理的来源' })
  expect(within(intakeGroup).getByText('待整理的会议纪要')).toBeTruthy()
  expect(within(intakeGroup).getByText('整理中')).toBeTruthy()
  expect(within(intakeGroup).getByText('整理中的材料')).toBeTruthy()
  expect(within(intakeGroup).queryByText('已经处理完的材料')).toBeNull()
  expect(within(intakeGroup).queryByText('取消掉的材料')).toBeNull()
  expect(intakeGroup.querySelector('.count-badge')?.textContent).toBe('2')

  const draftGroup = screen.getByRole('region', { name: '待复核的稿件' })
  expect(within(draftGroup).getByText('待复核稿件')).toBeTruthy()
  expect(within(draftGroup).getByText('2 个来源 · 1 项重要冲突')).toBeTruthy()
  expect(within(draftGroup).queryByText('已确认稿件')).toBeNull()
  expect(draftGroup.querySelector('.count-badge')?.textContent).toBe('1')
})

it('每类都有自己的空态文案', () => {
  render(<ApprovalView items={[]} drafts={[]} loading={false} error="" onRetry={vi.fn()} />)

  expect(screen.getByText('没有待整理的来源')).toBeTruthy()
  expect(screen.getByText('导入的材料会先出现在这里。')).toBeTruthy()
  expect(screen.getByText('没有待复核的稿件')).toBeTruthy()
  expect(screen.getByText(/待处理 0 项 · 共 2 类/)).toBeTruthy()
})

it('读取失败就地提示并提供重试，不把失败画成空态', () => {
  const onRetry = vi.fn()
  render(<ApprovalView items={[]} drafts={[]} loading={false} error="现在读不出待处理的清单。本机服务可能刚刚重启。" onRetry={onRetry} />)

  expect(screen.getByRole('alert').textContent).toContain('现在读不出待处理的清单')
  expect(screen.queryByText('没有待整理的来源'), '守卫④：错误态不得画成空态').toBeNull()
  expect(screen.queryByText('没有待复核的稿件')).toBeNull()
  expect(screen.queryByText(/待处理 0 项/)).toBeNull()
  expect(screen.getAllByText('这一类这次没有读到；点上面的「重试」再看。')).toHaveLength(2)
  fireEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: '重试' }))
  expect(onRetry).toHaveBeenCalledTimes(1)
})

it('页头按 §4.1 给出 eyebrow + h1 + 白话 lede，不写占位文案', () => {
  render(<ApprovalView items={[]} drafts={[]} loading={false} error="" onRetry={vi.fn()} />)

  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('审批')
  expect(document.querySelector('.eyebrow')?.textContent).toBeTruthy()
  expect(document.body.textContent).toContain('先整理来源，再复核稿件，最后确认正式内容。')
  expect(document.body.textContent, '本轮不写「即将推出」这类占位文案').not.toContain('即将推出')
})
