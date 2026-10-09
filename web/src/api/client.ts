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

type ErrorEnvelope = { error?: { message?: string } }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch('/api/v1' + path, { ...init, headers })
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ErrorEnvelope
    throw new Error(payload.error?.message ?? 'Request failed: ' + response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(payload) }),
  patch: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: 'POST', body: form }),
}

export function newOperationId(): string {
  return crypto.randomUUID()
}
