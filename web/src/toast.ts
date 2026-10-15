import { useCallback, useRef, useState } from 'react'

/**
 * 全局提示改为 toast（FRONTEND-GUIDE §5.2、D9、§0.4）。
 *
 * - 三色：success（绿）/ danger（红）/ neutral（中性灰）。
 * - 成功 3.5s 自动消失；失败**不自动消失**，必须手关或走「保存失败，点击重试」；
 *   中性信息 5s 后自动消失（规格只规定了成功与失败，这一条按同样口径取中间值）。
 * - 同屏最多 3 条，超出的挤掉最旧的一条。
 * - 文案由调用方给出，不夹 ID / 路径（§4.3、§5.2）。
 */
export type ToastKind = 'success' | 'danger' | 'neutral'

export type Toast = { id: number; kind: ToastKind; message: string }

export const TOAST_LIMIT = 3

/** 自动消失时长；`null` 表示不自动消失（失败必须手关）。 */
export const TOAST_TIMEOUT_MS: Record<ToastKind, number | null> = {
  success: 3500,
  neutral: 5000,
  danger: null,
}

export type ToastController = {
  toasts: Toast[]
  /** 空文案忽略；与最新一条同类同文时只刷新，不重复堆叠。 */
  notify: (message: string, kind?: ToastKind) => void
  dismiss: (id: number) => void
}

export function useToasts(): ToastController {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback((message: string, kind: ToastKind = 'danger') => {
    const text = message.trim()
    if (!text) return
    setToasts((current) => {
      const newest = current[current.length - 1]
      if (newest && newest.kind === kind && newest.message === text) {
        // 同一条消息再次出现：换一个 id 让它重新计时，不堆第二条。
        return [...current.slice(0, -1), { id: nextId.current++, kind, message: text }]
      }
      return [...current, { id: nextId.current++, kind, message: text }].slice(-TOAST_LIMIT)
    })
  }, [])

  return { toasts, notify, dismiss }
}
