import { useEffect, useRef } from 'react'
import { JournalView } from './JournalView'
import { useDialogFocus } from './useDialogFocus'
import type { ToastKind } from '../toast'
import { indexUpdateMessage, type MutationResult } from '../api/client'

type Props = { onClose: () => void; onError: (message: string, kind?: ToastKind) => void; onOpenPage: (id: string) => void; initialLineId?: string; initialProjectId?: string; onSaved?: () => void | Promise<void> }

export function JournalDialog({ onClose, onError, onOpenPage, initialLineId, initialProjectId, onSaved }: Props) {
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  const dialogRef = useDialogFocus(onClose)
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialogRef} className="modal-card journal-dialog" role="dialog" aria-modal="true" aria-label="工作日志与思考" tabIndex={-1}>
      <div className="panel-heading"><div><h2>工作日志与思考</h2></div><button className="button secondary" onClick={onClose}>关闭</button></div>
      <JournalView onError={onError} onOpenPage={onOpenPage} initialLineId={initialLineId} initialProjectId={initialProjectId} onSaved={(result: MutationResult) => {
        if (mounted.current) onClose()
        const notice = indexUpdateMessage(result.index_update)
        const kind: ToastKind = result.index_update === 'update_failed' ? 'danger' : result.index_update === 'not_enabled' || result.index_update === 'manual_required' ? 'neutral' : 'success'
        onError(notice ?? '记录已保存到本机。', kind)
        void Promise.resolve().then(() => onSaved?.()).catch((cause) => onError(cause instanceof Error ? `记录已保存；项目目录刷新失败：${cause.message}` : '记录已保存；项目目录刷新失败。'))
      }} />
    </section>
  </div>
}
