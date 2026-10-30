import { afterEach, expect, it, vi } from 'vitest'
import { api } from './client'
import { getServiceSnapshot, resetServiceStatus } from '../service-status'

afterEach(() => {
  vi.unstubAllGlobals()
  resetServiceStatus()
})

it('does not report the local API offline when a scoped request is aborted', async () => {
  const controller = new AbortController()
  controller.abort()
  vi.stubGlobal('fetch', vi.fn(async () => { throw new DOMException('Aborted', 'AbortError') }))

  await expect(api.get('/pages/directory', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' })
  expect(getServiceSnapshot().reachable).toBe(true)
})
