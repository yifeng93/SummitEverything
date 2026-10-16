import { api, ApiError } from '../api/client'

/**
 * 首次配置进度的持久化真源（repair1）。
 *
 * 旧实现把进度写进浏览器 localStorage。打包后的应用在 WKWebView 里跑，
 * 数据存储是 nonPersistent 的：重启一定丢。结果就是「已经配好」的工作库
 * 每次打开又被拉回向导第 2 步。现在唯一真源是本机后端按 profile + 工作库
 * 隔离保存的非秘密记录，只会读写 step / completed / open 三个字段。
 */

export type FirstUseProgress = { step: 2 | 3 | 4 | 5; completed: boolean; open: boolean }

const STEPS: readonly number[] = [2, 3, 4, 5]
const FIELDS = ['step', 'completed', 'open']

/**
 * 旧版浏览器存储键。localStorage 不再是真源，这个键只为一次性迁移保留。
 */
export function firstUseProgressKey(profileId: string, workspaceId: string): string {
  return `summit:first-use:${encodeURIComponent(profileId)}:${encodeURIComponent(workspaceId)}`
}

/** 只接受白名单形状；多一个字段（比如误写的密钥）就整体作废。 */
function parseProgress(value: unknown): FirstUseProgress | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  if (Object.keys(record).some((key) => !FIELDS.includes(key))) return null
  const { step, completed, open } = record
  if (!STEPS.includes(step as number) || typeof completed !== 'boolean') return null
  if (open !== undefined && typeof open !== 'boolean') return null
  return { step: step as FirstUseProgress['step'], completed, open: open === true }
}

/** 读取旧浏览器副本。迁移用；读失败一律当作没有副本。 */
export function readLegacyFirstUseProgress(key: string): FirstUseProgress | null {
  try {
    return parseProgress(JSON.parse(localStorage.getItem(key) ?? 'null'))
  } catch {
    return null
  }
}

/** 迁移成功后丢弃浏览器副本，避免长期双写。 */
export function clearLegacyFirstUseProgress(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    /* 存储不可用时本来也没有可迁移的副本 */
  }
}

/** 读取本机进度。「还没有记录」是正常答案，不是错误。 */
export async function loadFirstUseProgress(): Promise<FirstUseProgress | null> {
  let payload: unknown
  try {
    payload = await api.get<unknown>('/first-use/progress')
  } catch (cause) {
    if (cause instanceof ApiError && cause.code === 'first_use_progress_absent') return null
    throw cause
  }
  const parsed = parseProgress(payload)
  // 后端返回的形状不对时失败关闭：绝不把一堆看不懂的字段当成「进度」用。
  if (!parsed) throw new Error('本机返回了无法识别的首次配置进度。')
  return parsed
}

/** 只有本机确认写入才会 resolve；失败直接把错误交给调用方，不假装保存。 */
export async function saveFirstUseProgress(progress: FirstUseProgress): Promise<FirstUseProgress> {
  const payload = await api.put<unknown>('/first-use/progress', {
    step: progress.step,
    completed: progress.completed,
    open: progress.open,
  })
  const parsed = parseProgress(payload)
  if (!parsed) throw new Error('本机没有确认首次配置进度已保存。')
  return parsed
}

/**
 * 读本机进度；本机还没有记录时，把旧浏览器副本一次性迁移过去。
 * 迁移写入成功后删除浏览器副本，此后不再有任何 localStorage 写入。
 */
export async function resolveFirstUseProgress(key: string): Promise<FirstUseProgress | null> {
  const durable = await loadFirstUseProgress()
  if (durable) return durable
  const legacy = readLegacyFirstUseProgress(key)
  if (!legacy) return null
  const migrated = await saveFirstUseProgress(legacy)
  clearLegacyFirstUseProgress(key)
  return migrated
}
