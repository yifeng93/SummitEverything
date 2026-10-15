import { JournalView } from './JournalView'
import { useDialogFocus } from './useDialogFocus'

type Props = { onClose: () => void; onError: (message: string) => void; onOpenPage: (id: string) => void; initialLineId?: string; initialProjectId?: string }

export function JournalDialog({ onClose, onError, onOpenPage, initialLineId, initialProjectId }: Props) {
  const dialogRef = useDialogFocus(onClose)
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialogRef} className="modal-card journal-dialog" role="dialog" aria-modal="true" aria-label="工作日志与思考" tabIndex={-1}>
      <div className="panel-heading"><div><h2>工作日志与思考</h2><p>保存到本机；需要时再单独确认辅助建议。</p></div><button className="button secondary" onClick={onClose}>关闭</button></div>
      <JournalView onError={onError} onOpenPage={onOpenPage} initialLineId={initialLineId} initialProjectId={initialProjectId} />
    </section>
  </div>
}
