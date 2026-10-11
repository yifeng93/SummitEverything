import type { components } from './generated'

export type Workspace = components['schemas']['WorkspaceContext']
export type Line = components['schemas']['LineRecord']
export type Project = components['schemas']['ProjectRecord']
export type Page = components['schemas']['PageSnapshot']
export type IntakeItem = components['schemas']['IntakeItem']
export type Draft = components['schemas']['Draft']
export type ActionCandidate = components['schemas']['ActionCandidate']
export type SourceDetail = components['schemas']['SourceDetail']
export type Citation = components['schemas']['Citation']
export type IndexPlan = components['schemas']['IndexPlan']
export type IndexResult = components['schemas']['IndexResult']
export type MutationResult = components['schemas']['MutationResult']

export function indexUpdateMessage(status: MutationResult['index_update']): string | null {
  if (status === 'updated') return '本机索引已更新。'
  if (status === 'update_failed') return '内容已保存；索引更新未完成，旧版本内容不会作为当前依据。'
  if (status === 'not_enabled') return '内容已保存；首次索引仍需你在知识问答中确认。'
  if (status === 'manual_required') return '内容已保存；真实 embedding 需要你在知识问答中查看并确认索引计划。'
  return null
}

type ErrorEnvelope = { error?: { code?: string; message?: string } }

export class ApiError extends Error {
  readonly code?: string
  readonly status: number
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ErrorEnvelope
    throw new ApiError(payload.error?.message ?? 'Request failed: ' + response.status, response.status, payload.error?.code)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

async function oauthCallback<T>(destination: string): Promise<T> {
  const url = new URL(destination)
  const keys: string[] = []
  url.searchParams.forEach((_value, key) => { keys.push(key) })
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)
    || url.username || url.password || url.hash || !['/api/v1/integrations/feishu/callback', '/callback'].includes(url.pathname)
    || !url.searchParams.get('state') || url.searchParams.getAll('state').length !== 1
    || keys.some((key) => !['code', 'state', 'error'].includes(key) || url.searchParams.getAll(key).length !== 1)
    || (!url.searchParams.has('code') && !url.searchParams.has('error'))
    || (url.searchParams.has('code') && url.searchParams.has('error'))) {
    throw new ApiError('授权回调地址无效，请检查本机配置。', 400, 'invalid_redirect')
  }
  // Narrow Fake callback: preserve the registered destination, send no credentials,
  // and never follow a redirect to another endpoint.
  return readResponse<T>(await fetch(destination, { credentials: 'omit', redirect: 'error', cache: 'no-store' }))
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch('/api/v1' + path, { ...init, headers })
  return readResponse<T>(response)
}

export const api = {
  oauthCallback,
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(payload) }),
  put: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(payload) }),
  patch: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: <T>(path: string, payload?: unknown) => request<T>(path, { method: 'DELETE', ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: 'POST', body: form }),
}

export function newOperationId(): string {
  return crypto.randomUUID()
}
