import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useDialogFocus } from './useDialogFocus'

type Props = {
  title: string
  description: string
  consequence?: string
  confirmLabel: string
  busyLabel: string
  busy?: boolean
  danger?: boolean
  children?: ReactNode
  onCancel: () => void
  onConfirm: () => void | Promise<void>
}

export function ConfirmDialog({
  title, description, consequence, confirmLabel, busyLabel, busy = false, danger = false,
  children, onCancel, onConfirm,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const cancelAction = useRef(onCancel)
  const busyRef = useRef(busy)
  const [submitting, setSubmitting] = useState(false)
  const isBusy = busy || submitting
  const dialogRef = useDialogFocus(() => { if (!busyRef.current) cancelAction.current() })

  useEffect(() => {
    cancelAction.current = onCancel
    busyRef.current = isBusy
  }, [isBusy, onCancel])

  async function confirm() {
    if (isBusy) return
    busyRef.current = true
    setSubmitting(true)
    try { await onConfirm() }
    finally { busyRef.current = busy; setSubmitting(false) }
  }

  return <div className="confirm-backdrop">
    <section ref={dialogRef} className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-description" tabIndex={-1}>
      <h2 id="confirm-dialog-title">{title}</h2>
      <p id="confirm-dialog-description">{description}</p>
      {consequence && <p className="confirm-consequence">{consequence}</p>}
      {children}
      <div className="confirm-actions">
        <button ref={cancelRef} className="button secondary" type="button" disabled={isBusy} onClick={onCancel}>取消</button>
        <button className={danger ? 'button danger' : 'button primary'} type="button" disabled={isBusy} onClick={() => void confirm()}>
          {isBusy ? busyLabel : confirmLabel}
        </button>
      </div>
    </section>
  </div>
}
