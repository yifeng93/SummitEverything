import { useEffect, useRef, useState, type ReactNode } from 'react'

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

const focusable = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function ConfirmDialog({
  title, description, consequence, confirmLabel, busyLabel, busy = false, danger = false,
  children, onCancel, onConfirm,
}: Props) {
  const dialogRef = useRef<HTMLElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const cancelAction = useRef(onCancel)
  const busyRef = useRef(busy)
  const [submitting, setSubmitting] = useState(false)
  const isBusy = busy || submitting

  cancelAction.current = onCancel
  busyRef.current = isBusy

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    cancelRef.current?.focus()
    const dialog = dialogRef.current

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (!busyRef.current) cancelAction.current()
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const controls = [...dialog.querySelectorAll<HTMLElement>(focusable)]
      if (controls.length === 0) {
        event.preventDefault()
        dialog.focus()
      } else if (event.shiftKey && document.activeElement === controls[0]) {
        event.preventDefault()
        controls.at(-1)?.focus()
      } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
        event.preventDefault()
        controls[0]?.focus()
      }
    }

    dialog?.addEventListener('keydown', handleKeyDown)
    return () => {
      dialog?.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus()
    }
  }, [])

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
