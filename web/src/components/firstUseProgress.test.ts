import { afterEach, expect, it, vi } from 'vitest'
import { firstUseProgressKey, readFirstUseProgress, writeFirstUseProgress } from './firstUseProgress'

afterEach(() => localStorage.clear())

it('isolates progress by local profile and workspace identity', () => {
  const first = firstUseProgressKey('/synthetic/profile-a', 'workspace-a')
  const otherProfile = firstUseProgressKey('/synthetic/profile-b', 'workspace-a')
  const otherWorkspace = firstUseProgressKey('/synthetic/profile-a', 'workspace-b')
  writeFirstUseProgress(first, { step: 3, completed: false, open: true })

  expect(readFirstUseProgress(first)).toEqual({ step: 3, completed: false, open: true })
  expect(readFirstUseProgress(otherProfile)).toBeNull()
  expect(readFirstUseProgress(otherWorkspace)).toBeNull()
  expect(localStorage.getItem(first)).not.toContain('secret')
})

it('treats legacy unfinished progress as manually resumable but closed', () => {
  const key = firstUseProgressKey('profile', 'workspace')
  localStorage.setItem(key, JSON.stringify({ step: 4, completed: false }))
  expect(readFirstUseProgress(key)).toEqual({ step: 4, completed: false, open: false })
})

it('fails closed when browser storage is unavailable', () => {
  const key = firstUseProgressKey('profile', 'workspace')
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('disabled') })
  expect(() => writeFirstUseProgress(key, { step: 2, completed: false, open: true })).not.toThrow()
})
