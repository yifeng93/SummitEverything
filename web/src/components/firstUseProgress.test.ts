import { afterEach, expect, it, vi } from 'vitest'
import {
  clearLegacyFirstUseProgress,
  firstUseProgressKey,
  loadFirstUseProgress,
  readLegacyFirstUseProgress,
  resolveFirstUseProgress,
  saveFirstUseProgress,
} from './firstUseProgress'

/**
 * 首次配置进度的持久化真源在后端（repair1）。
 *
 * 打包后的 WKWebView 使用 nonPersistent 存储，localStorage 在重启后必然丢失，
 * 所以这里只保留一次性迁移用的旧键读取；所有写入都必须走 typed API。
 */

afterEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
})

function absent() {
  return Response.json({ error: { code: 'first_use_progress_absent', message: '本机还没有保存首次配置进度。' } }, { status: 404 })
}

function stub(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => handler(String(input), init))
  vi.stubGlobal('fetch', mock)
  return mock
}

it('keeps the legacy key isolated by local profile and workspace identity', () => {
  const first = firstUseProgressKey('/synthetic/profile-a', 'workspace-a')
  expect(firstUseProgressKey('/synthetic/profile-b', 'workspace-a')).not.toBe(first)
  expect(firstUseProgressKey('/synthetic/profile-a', 'workspace-b')).not.toBe(first)
})

it('reads only the whitelisted legacy shape', () => {
  const key = firstUseProgressKey('profile', 'workspace')
  localStorage.setItem(key, JSON.stringify({ step: 4, completed: false }))
  expect(readLegacyFirstUseProgress(key)).toEqual({ step: 4, completed: false, open: false })

  localStorage.setItem(key, JSON.stringify({ step: 9, completed: true, open: true }))
  expect(readLegacyFirstUseProgress(key)).toBeNull()

  localStorage.setItem(key, JSON.stringify({ step: 3, completed: false, open: true, secret: 'sk-synthetic' }))
  expect(readLegacyFirstUseProgress(key)).toBeNull()

  localStorage.setItem(key, '{not json')
  expect(readLegacyFirstUseProgress(key)).toBeNull()
})

it('treats the backend "absent" answer as no progress rather than an error', async () => {
  stub(() => absent())
  await expect(loadFirstUseProgress()).resolves.toBeNull()
})

it('surfaces a real read failure instead of pretending there is no progress', async () => {
  stub(() => Response.json({ error: { code: 'progress_unavailable', message: '无法读写。' } }, { status: 503 }))
  await expect(loadFirstUseProgress()).rejects.toThrow('无法读写。')
})

it('writes only the three non-secret fields through the typed endpoint', async () => {
  const mock = stub(() => Response.json({ step: 3, completed: false, open: true }))
  await saveFirstUseProgress({ step: 3, completed: false, open: true })

  expect(mock).toHaveBeenCalledTimes(1)
  const [url, init] = mock.mock.calls[0]
  expect(url).toBe('/api/v1/first-use/progress')
  expect(init?.method).toBe('PUT')
  expect(init?.body).toBe(JSON.stringify({ step: 3, completed: false, open: true }))
  expect(localStorage.length).toBe(0)
})

it('migrates a legacy browser copy exactly once', async () => {
  const key = firstUseProgressKey('/synthetic/profile', 'workspace-a')
  localStorage.setItem(key, JSON.stringify({ step: 4, completed: true, open: false }))
  const mock = stub((_url, init) => (init?.method === 'PUT'
    ? Response.json({ step: 4, completed: true, open: false })
    : absent()))

  await expect(resolveFirstUseProgress(key)).resolves.toEqual({ step: 4, completed: true, open: false })

  const writes = mock.mock.calls.filter((call) => call[1]?.method === 'PUT')
  expect(writes).toHaveLength(1)
  expect(writes[0][1]?.body).toBe(JSON.stringify({ step: 4, completed: true, open: false }))
  // 迁移成功后浏览器副本被丢弃，后端成为唯一真源，不做长期双写。
  expect(localStorage.getItem(key)).toBeNull()
})

it('does not migrate when the durable record already exists', async () => {
  const key = firstUseProgressKey('/synthetic/profile', 'workspace-a')
  localStorage.setItem(key, JSON.stringify({ step: 2, completed: false, open: true }))
  const mock = stub(() => Response.json({ step: 5, completed: true, open: false }))

  await expect(resolveFirstUseProgress(key)).resolves.toEqual({ step: 5, completed: true, open: false })
  expect(mock.mock.calls.filter((call) => call[1]?.method === 'PUT')).toHaveLength(0)
})

it('reports no progress when neither the backend nor the browser has a record', async () => {
  const key = firstUseProgressKey('/synthetic/profile', 'workspace-a')
  stub(() => absent())
  await expect(resolveFirstUseProgress(key)).resolves.toBeNull()
})

it('drops the legacy copy without touching the backend', () => {
  const key = firstUseProgressKey('/synthetic/profile', 'workspace-a')
  localStorage.setItem(key, JSON.stringify({ step: 3, completed: false, open: true }))
  clearLegacyFirstUseProgress(key)
  expect(localStorage.getItem(key)).toBeNull()
})
