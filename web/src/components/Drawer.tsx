import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { useDialogFocus } from './useDialogFocus'

type Props = {
  title: string
  description?: string
  /** 覆盖默认的对话框可访问名称（默认用 title）。 */
  label?: string
  /** 有第二层确认弹窗打开时暂停 Esc 与焦点陷阱，避免一次关两层。 */
  paused?: boolean
  onClose: () => void
  children: ReactNode
}

/**
 * 右侧抽屉：详情和整理操作都在这里完成，不替换背后的列表。
 *
 * 只做「一层」抽屉。抽屉里需要确认时，把 ConfirmDialog 放在抽屉外面（同一层级），
 * 由 paused 暂停抽屉自己的 Esc / 焦点陷阱，让确认框独占键盘。
 */
export function Drawer({ title, description, label, paused = false, onClose, children }: Props) {
  const dialogRef = useDialogFocus(onClose, !paused)
  return <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialogRef} className="drawer" role="dialog" aria-modal="true" aria-label={label ?? title} tabIndex={-1}>
      <header className="drawer-head">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        <button className="icon-button drawer-close" aria-label="关闭" title="关闭" onClick={onClose}><X size={16} strokeWidth={1.75} aria-hidden="true" /></button>
      </header>
      <div className="drawer-body">{children}</div>
    </section>
  </div>
}
