import type { Draft, IntakeItem } from './api/client'

/**
 * 审批页的纯函数口径（FRONTEND-GUIDE §11 ⑧、逐页规格 §3）。
 *
 * 本轮只有两类：**待整理的来源**（原件已保存、还没整理出稿件）与**待复核的稿件**
 * （整理产出、还没被确认）。规格 §3 的另三类分组（待确认的正式内容 / 待确认的索引更新 /
 * 待确认的外部动作）属于 P3 · 信息架构切片，这里的口径先只覆盖前两类，但它就是
 * 侧栏徽章与审批页数量共用的**同一个**计数来源，避免「一处说 N、另一处说 M」。
 */
export const INTAKE_STATE_LABELS: Record<string, string> = {
  pending: '待整理',
  processing: '整理中',
  reviewing: '待审核',
  completed: '已完成',
  failed: '整理失败',
  cancelled: '已取消',
  unknown: '请求状态未知',
}

export const DRAFT_STATE_LABELS: Record<string, string> = {
  pending: '待复核',
  confirmed: '已确认',
  cancelled: '已取消',
}

/** 已收口的来源状态：不再需要用户处理，不进清单也不计数。 */
const SETTLED_INTAKE_STATES = new Set(['completed', 'cancelled'])

/** 这条来源还需要用户处理（整理中/待审核也在清单里，用户能看到进度）。 */
export function intakeNeedsAttention(item: IntakeItem): boolean {
  return !SETTLED_INTAKE_STATES.has(item.state)
}

/** 待复核的稿件：只有 `pending` 需要用户点一下。 */
export function draftNeedsAttention(draft: Draft): boolean {
  return draft.state === 'pending'
}

export function pendingIntakeItems(items: IntakeItem[]): IntakeItem[] {
  return items.filter(intakeNeedsAttention)
}

export function pendingDrafts(drafts: Draft[]): Draft[] {
  return drafts.filter(draftNeedsAttention)
}

/** 侧栏「审批」徽章与审批页顶部状态行共用的待处理总数。 */
export function approvalPendingCount(items: IntakeItem[], drafts: Draft[]): number {
  return pendingIntakeItems(items).length + pendingDrafts(drafts).length
}

export function intakeStateLabel(state: string): string {
  return INTAKE_STATE_LABELS[state] ?? '状态未知'
}

export function draftStateLabel(state: string): string {
  return DRAFT_STATE_LABELS[state] ?? '状态未知'
}
