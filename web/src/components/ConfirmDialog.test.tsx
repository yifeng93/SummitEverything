import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, it } from 'vitest'
import { ConfirmDialog } from './ConfirmDialog'

afterEach(cleanup)

function DialogHarness({ onConfirm }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false)
  return <>
    <button type="button" onClick={() => setOpen(true)}>打开</button>
    {open && <ConfirmDialog
      title="删除密钥"
      description="会删除所选应用的本机密钥。"
      consequence="删除后需要重新录入，无法从本地恢复。"
      confirmLabel="删除"
      busyLabel="正在删除…"
      busy={false}
      danger
      onCancel={() => setOpen(false)}
      onConfirm={() => onConfirm?.()}
    />}
  </>
}

it('focuses cancel, traps keyboard focus, closes on Escape, and restores the trigger', () => {
  render(<DialogHarness />)
  const trigger = screen.getByRole('button', { name: '打开' })
  trigger.focus()
  fireEvent.click(trigger)
  const dialog = screen.getByRole('dialog', { name: '删除密钥' })
  const cancel = screen.getByRole('button', { name: '取消' })
  const confirm = screen.getByRole('button', { name: '删除' })
  expect(dialog.getAttribute('aria-modal')).toBe('true')
  expect(document.activeElement).toBe(cancel)
  fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true })
  expect(document.activeElement).toBe(confirm)
  fireEvent.keyDown(confirm, { key: 'Tab' })
  expect(document.activeElement).toBe(cancel)
  fireEvent.keyDown(dialog, { key: 'Escape' })
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(document.activeElement).toBe(trigger)
})

it('places cancel before the destructive action and states its impact', () => {
  render(<DialogHarness />)
  fireEvent.click(screen.getByRole('button', { name: '打开' }))
  const dialog = screen.getByRole('dialog', { name: '删除密钥' })
  const actions = Array.from(dialog.querySelectorAll('button')).map((button) => button.textContent)
  expect(actions).toEqual(['取消', '删除'])
  expect(dialog.textContent).toContain('会删除所选应用的本机密钥。')
  expect(dialog.textContent).toContain('删除后需要重新录入，无法从本地恢复。')
})
