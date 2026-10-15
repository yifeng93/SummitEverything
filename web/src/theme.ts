import { useCallback, useEffect, useState } from 'react'

/**
 * 主题偏好（FRONTEND-GUIDE §5.6、§6.2）。
 *
 * - 三选：跟随系统 / 浅色 / 深色；持久化在 localStorage 的 `sx:theme-preference`。
 * - 主题由 `<html data-theme="light|dark">` 驱动；`system` 先解析成 light/dark 再写入。
 * - 首屏前由 index.html 的引导脚本读同一个键并写入 data-theme，避免闪白/闪黑；
 *   本模块负责运行期的切换与系统偏好变化。
 */
export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

/** 与 index.html 引导脚本共用的键名；改名必须同时改那里。 */
export const THEME_STORAGE_KEY = 'sx:theme-preference'
export const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)'
export const THEME_LABELS: Record<ThemePreference, string> = {
  system: '跟随系统',
  light: '浅色',
  dark: '深色',
}
export const THEME_PREFERENCES: ThemePreference[] = ['system', 'light', 'dark']

export function normalizePreference(value: string | null | undefined): ThemePreference {
  return value === 'light' || value === 'dark' ? value : 'system'
}

export function resolveTheme(preference: ThemePreference, systemPrefersDark: boolean): ResolvedTheme {
  return preference === 'system' ? (systemPrefersDark ? 'dark' : 'light') : preference
}

type ThemeStorage = Pick<Storage, 'getItem' | 'setItem'>

function browserStorage(): ThemeStorage | undefined {
  try {
    return window.localStorage
  } catch {
    // 隐私模式等场景下 localStorage 可能不可用；主题退回跟随系统，不阻塞界面。
    return undefined
  }
}

export function readStoredPreference(storage: ThemeStorage | undefined = browserStorage()): ThemePreference {
  if (!storage) return 'system'
  try {
    return normalizePreference(storage.getItem(THEME_STORAGE_KEY))
  } catch {
    return 'system'
  }
}

export function storePreference(preference: ThemePreference, storage: ThemeStorage | undefined = browserStorage()): void {
  if (!storage) return
  try {
    storage.setItem(THEME_STORAGE_KEY, preference)
  } catch {
    // 存不下就只在本次会话生效；不因为持久化失败打断切换。
  }
}

export function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia(DARK_MEDIA_QUERY).matches
}

export function applyTheme(root: HTMLElement, theme: ResolvedTheme): void {
  root.dataset.theme = theme
}

/** 挂载时按偏好（含系统偏好）写入 data-theme；切换时持久化。 */
export function useThemePreference(): [ThemePreference, (next: ThemePreference) => void] {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredPreference())

  useEffect(() => {
    applyTheme(document.documentElement, resolveTheme(preference, systemPrefersDark()))
    if (preference !== 'system' || typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(DARK_MEDIA_QUERY)
    if (typeof media.addEventListener !== 'function') return
    const followSystem = () => applyTheme(document.documentElement, resolveTheme('system', media.matches))
    media.addEventListener('change', followSystem)
    return () => media.removeEventListener('change', followSystem)
  }, [preference])

  const choose = useCallback((next: ThemePreference) => {
    setPreference(next)
    storePreference(next)
  }, [])

  return [preference, choose]
}
