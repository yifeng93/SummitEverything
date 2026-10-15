import { useSyncExternalStore } from 'react'

/**
 * 保存状态（FRONTEND-GUIDE §0.4、§5.6 与守卫 ①）。
 *
 * 顶栏原来写着永远为真的「本机已保存」。这里给出一个**真实**的三态：
 * `saving`（保存中…）、`saved`（已保存）、`failed`（保存失败，点击重试）。
 * 状态由 web/src/api/client.ts 的写请求（非 GET）驱动，所以任何页面的本机写入都会
 * 反映到顶栏，不需要每个视图各自接线；读请求不影响它。
 *
 * 判定口径：
 * - 只跟踪写请求（POST / PUT / PATCH / DELETE），GET 不算保存；
 * - 费用/外部动作的预览与执行（`/acceptance-plans`、`/integrations/feishu`）有自己的
 *   一次性范围确认流程，不算「保存本机内容」，不计入顶栏；
 * - `retry` 重新发出**同一个请求**（请求载荷不变，后端按幂等编号去重），
 *   所以重试不会产生第二份内容。
 *
 * 首屏尚未发生任何保存时是 `idle`：顶栏不显示保存文案，而不是先撒一个「已保存」。
 */
export type SavePhase = 'idle' | 'saving' | 'saved' | 'failed'

export type SaveSnapshot = {
  phase: SavePhase
  /** 最近一次失败的写请求；`failed` 时由顶栏的「保存失败，点击重试」调用。 */
  retry: (() => void) | null
}

/** 这些前缀是费用/外部动作流程，不算本机保存（见文件头）。 */
const EXCLUDED_PREFIXES = ['/acceptance-plans', '/integrations/feishu']

/** 是否把这次请求计入顶栏保存状态。 */
export function tracksSaveRequest(method: string | undefined, path: string): boolean {
  if (!method || method.toUpperCase() === 'GET') return false
  return !EXCLUDED_PREFIXES.some((prefix) => path.startsWith(prefix))
}

let active = 0
let phase: SavePhase = 'idle'
let retry: (() => void) | null = null
let snapshot: SaveSnapshot = { phase: 'idle', retry: null }
const listeners = new Set<() => void>()

function publish(): void {
  snapshot = { phase, retry: phase === 'failed' ? retry : null }
  for (const listener of listeners) listener()
}

/** 开始一次写请求；`again` 是重试同一请求的闭包。 */
export function beginSave(again: () => void): void {
  active += 1
  retry = again
  if (phase !== 'saving') {
    phase = 'saving'
    publish()
  }
}

/** 写请求成功。 */
export function finishSave(): void {
  active = Math.max(0, active - 1)
  if (active === 0) {
    phase = 'saved'
    retry = null
  }
  publish()
}

/** 写请求失败；失败不自动消失，由用户手关或点击重试。 */
export function failSave(): void {
  active = Math.max(0, active - 1)
  if (active === 0) phase = 'failed'
  publish()
}

export function getSaveSnapshot(): SaveSnapshot {
  return snapshot
}

export function subscribeSave(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** 仅供测试重置；运行期不需要。 */
export function resetSaveStatus(): void {
  active = 0
  phase = 'idle'
  retry = null
  publish()
}

export function useSaveStatus(): SaveSnapshot {
  return useSyncExternalStore(subscribeSave, getSaveSnapshot)
}
