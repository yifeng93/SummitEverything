import { useSyncExternalStore } from 'react'

/**
 * 本机服务可达性（FRONTEND-GUIDE §0.3、§5.6 与守卫 ①）。
 *
 * 侧栏底部原来是一个装饰性绿点 + 写死的「仅本机运行」。这里改成真实状态：
 * - `reachable`：最近一次请求拿到了本机服务的响应（即使响应是 4xx/5xx，也说明服务在跑）→「仅本机运行」；
 * - `unreachable`：请求在拿到响应前就失败了（服务没启动 / 被关掉）→「本机服务未连接」。
 *
 * 由 web/src/api/client.ts 在每次请求后上报；外壳只读，不自己发探测请求。
 */
export type ServiceSnapshot = { reachable: boolean }

let reachable = true
let snapshot: ServiceSnapshot = { reachable }
const listeners = new Set<() => void>()

function publish(next: boolean): void {
  if (next === reachable) return
  reachable = next
  snapshot = { reachable }
  for (const listener of listeners) listener()
}

/** 拿到了本机服务的响应（任何状态码都算）。 */
export function markServiceReachable(): void {
  publish(true)
}

/** 请求没能到达本机服务（网络层失败）。 */
export function markServiceUnreachable(): void {
  publish(false)
}

export function getServiceSnapshot(): ServiceSnapshot {
  return snapshot
}

export function subscribeService(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** 仅供测试重置；运行期不需要。 */
export function resetServiceStatus(): void {
  reachable = true
  snapshot = { reachable }
  for (const listener of listeners) listener()
}

export function useServiceStatus(): ServiceSnapshot {
  return useSyncExternalStore(subscribeService, getServiceSnapshot)
}
