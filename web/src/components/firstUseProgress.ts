export type FirstUseProgress = { step: 2 | 3 | 4 | 5; completed: boolean; open: boolean }

export function firstUseProgressKey(profileId: string, workspaceId: string): string {
  return `summit:first-use:${encodeURIComponent(profileId)}:${encodeURIComponent(workspaceId)}`
}

export function readFirstUseProgress(key: string): FirstUseProgress | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? 'null')
    if (!value || typeof value !== 'object') return null
    const { step, completed, open } = value as Record<string, unknown>
    if (![2, 3, 4, 5].includes(step as number) || typeof completed !== 'boolean') return null
    return { step: step as FirstUseProgress['step'], completed, open: open === true }
  } catch { return null }
}

export function writeFirstUseProgress(key: string | undefined, progress: FirstUseProgress): void {
  if (!key) return
  try { localStorage.setItem(key, JSON.stringify(progress)) } catch { /* Storage may be disabled; the current session still works. */ }
}
