import { useEffect, useRef } from 'react'

const focusable = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function useDialogFocus(onEscape: () => void, enabled = true) {
  const dialogRef = useRef<HTMLElement>(null)
  const escapeAction = useRef(onEscape)
  useEffect(() => { escapeAction.current = onEscape }, [onEscape])

  useEffect(() => {
    if (!enabled) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = dialogRef.current
    const first = dialog?.querySelector<HTMLElement>(focusable)
    ;(first ?? dialog)?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        escapeAction.current()
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const controls = Array.from(dialog.querySelectorAll<HTMLElement>(focusable))
      if (controls.length === 0) {
        event.preventDefault()
        dialog.focus()
      } else if (event.shiftKey && (document.activeElement === controls[0] || !dialog.contains(document.activeElement))) {
        event.preventDefault()
        controls.at(-1)?.focus()
      } else if (!event.shiftKey && (document.activeElement === controls.at(-1) || !dialog.contains(document.activeElement))) {
        event.preventDefault()
        controls[0]?.focus()
      }
    }

    dialog?.addEventListener('keydown', handleKeyDown)
    return () => {
      dialog?.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus()
    }
  }, [enabled])

  return dialogRef
}
