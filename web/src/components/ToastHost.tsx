import { useEffect } from 'react'
import { X } from 'lucide-react'
import { TOAST_TIMEOUT_MS, type Toast } from '../toast'

/**
 * toast 容器（FRONTEND-GUIDE §5.2、D9）。
 *
 * - 右下角固定一列，最多同时 3 条（上限由 useToasts 保证）。
 * - 失败用 `role="alert"`（会被读屏立即播报）；成功与中性用 `role="status"`。
 * - 自动消失只作用于 success / neutral；danger 必须由用户点关闭按钮（§5.2）。
 * - 关闭按钮有 `aria-label` + `title`，最小 36px（粗指针 44px，见 App.css）。
 */
function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const timeout = TOAST_TIMEOUT_MS[toast.kind]

  useEffect(() => {
    if (timeout === null) return
    const timer = window.setTimeout(() => onDismiss(toast.id), timeout)
    return () => window.clearTimeout(timer)
  }, [onDismiss, timeout, toast.id])

  return (
    <div className={'toast toast-' + toast.kind} role={toast.kind === 'danger' ? 'alert' : 'status'}>
      <span className="toast-message">{toast.message}</span>
      <button
        type="button"
        className="toast-close"
        aria-label="关闭这条提示"
        title="关闭这条提示"
        onClick={() => onDismiss(toast.id)}
      >
        <span aria-hidden="true"><X size={14} strokeWidth={2} /></span>
      </button>
    </div>
  )
}

export function ToastHost({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) return null
  return (
    <div className="toast-region" aria-label="提示">
      {toasts.map((toast) => <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />)}
    </div>
  )
}
