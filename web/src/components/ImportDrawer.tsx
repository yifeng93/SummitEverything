import { useRef, useState, type ChangeEvent } from 'react'
import { ApiError, api, newOperationId, type IntakeItem } from '../api/client'
import { FeishuPanel } from './FeishuPanel'
import { useDialogFocus } from './useDialogFocus'

type Row = { key: string; file: File; path: string; state: 'queued' | 'uploading' | 'succeeded' | 'failed' | 'unknown' | 'skipped' | 'blocked'; message?: string }
type Props = { onClose: () => void; onImported: (itemIds?: string[]) => Promise<void>; onMode?: (mode: 'fake' | 'real' | null) => void; onAuthorizationChanged?: () => void; contextMessage?: string }
const MAX_FILES = 100, MAX_BATCH = 100 * 1024 * 1024, MAX_FILE = 20 * 1024 * 1024

export function ImportDrawer({ onClose, onImported, onMode, onAuthorizationChanged, contextMessage }: Props) {
  const [rows, setRows] = useState<Row[]>([])
  const [sourceTab, setSourceTab] = useState<'local' | 'feishu'>('local')
  const [busy, setBusy] = useState(false)
  const [remoteBusy, setRemoteBusy] = useState(false)
  const busyRef = useRef(false)
  const requestClose = () => { if (!busyRef.current && !remoteBusy) onClose() }
  const dialogRef = useDialogFocus(requestClose)
  function stage(files: File[]) {
    if (!files.length || busyRef.current) return
    const tooLarge = files.length > MAX_FILES || files.reduce((sum, f) => sum + f.size, 0) > MAX_BATCH
    setRows(files.map((file) => {
      const path = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
      if (tooLarge) return { key: newOperationId(), file, path, state: 'blocked', message: '批次超过 100 个文件或 100 MB。' }
      if (path.split('/').some((part) => part.startsWith('.') || /\.(app|bundle|framework|pkg)$/i.test(part))) return { key: newOperationId(), file, path, state: 'skipped', message: '隐藏内容或应用包已跳过。' }
      if (!/\.(txt|md)$/i.test(file.name)) return { key: newOperationId(), file, path, state: 'skipped', message: '仅支持 TXT / Markdown。' }
      if (file.size > MAX_FILE || file.size === 0) return { key: newOperationId(), file, path, state: 'blocked', message: file.size ? '单个文件超过 20 MB。' : '空文件未上传。' }
      return { key: newOperationId(), file, path, state: 'queued' }
    }))
  }
  function choose(event: ChangeEvent<HTMLInputElement>) { const files = Array.from(event.target.files ?? []); event.target.value = ''; stage(files) }
  async function upload(selected = rows.filter((row) => row.state === 'queued')) {
    if (!selected.length || busyRef.current) return
    busyRef.current = true; setBusy(true)
    let imported = false
    const itemIds: string[] = []
    try {
      for (const row of selected) {
        setRows((all) => all.map((item) => item.key === row.key ? { ...item, state: 'uploading' } : item))
        const body = new FormData(); body.append('operation_id', row.key); body.append('file', row.file)
        try {
          const saved = await api.upload<IntakeItem>('/intake/files', body); imported = true; itemIds.push(saved.item_id)
          setRows((all) => all.map((item) => item.key === row.key ? { ...item, state: 'succeeded', message: '原件已保存到收件箱' } : item))
        } catch (error) {
          const unknown = !(error instanceof ApiError) || error.status >= 500
          setRows((all) => all.map((item) => item.key === row.key ? { ...item, state: unknown ? 'unknown' : 'failed', message: unknown ? '结果未知；不会自动重发。请关闭抽屉并刷新收件箱核对。' : error instanceof Error ? error.message : '导入失败' } : item))
        }
      }
      if (imported) await onImported(itemIds)
    } finally { busyRef.current = false; setBusy(false) }
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) requestClose() }}>
    <section ref={dialogRef} className="modal-card import-drawer" role="dialog" aria-modal="true" aria-label="导入材料" tabIndex={-1}>
      <div className="panel-heading"><div><h2>导入材料</h2><p>选择本机文件，或搜索飞书材料；导入只保存原件，不会调用模型。</p></div><button className="button secondary" onClick={requestClose} disabled={busy || remoteBusy}>关闭</button></div>
      {contextMessage && <p className="helper-line">{contextMessage}</p>}
      <div className="import-tabs" role="tablist" aria-label="材料来源"><button role="tab" aria-selected={sourceTab === 'local'} className={sourceTab === 'local' ? 'active' : ''} onClick={() => setSourceTab('local')}>本机文件</button><button role="tab" aria-selected={sourceTab === 'feishu'} className={sourceTab === 'feishu' ? 'active' : ''} onClick={() => setSourceTab('feishu')}>飞书材料</button></div>
      {sourceTab === 'local' && <><div className="capture-actions">
        <label className="button secondary file-button">本机文件<input aria-label="选择多个文件" type="file" multiple accept=".txt,.md,text/plain,text/markdown" onChange={choose} disabled={busy} /></label>
        <label className="button secondary file-button">选择文件夹<input type="file" multiple webkitdirectory="" accept=".txt,.md,text/plain,text/markdown" onChange={choose} disabled={busy} /></label>
        <span className="helper-line">也可将文件拖到此处。每批最多 100 个 / 100 MB，单个不超过 20 MB。</span>
      </div>
      <div className="drop-zone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); stage(Array.from(event.dataTransfer.files)) }}>将 TXT 或 Markdown 文件拖到这里</div>
      {rows.length > 0 && <section className="batch-upload-review" aria-label="导入文件状态"><ul className="source-list">{rows.map((row) => <li key={row.key}><div className="source-row"><span className="source-title"><strong>{row.path}</strong><small>{(row.file.size / 1024).toFixed(1)} KB · {{ queued: '待导入', uploading: '正在导入', succeeded: '已导入', failed: '导入失败', unknown: '结果未知', skipped: '已跳过', blocked: '未导入' }[row.state]}{row.message ? ` · ${row.message}` : ''}</small></span>{row.state === 'failed' && <button className="text-button" disabled={busy} onClick={() => void upload([row])}>只重试此文件</button>}</div></li>)}</ul><button className="button primary" disabled={busy || !rows.some((row) => row.state === 'queued')} onClick={() => void upload()}>{busy ? '正在逐项导入…' : '导入可用文件'}</button><button className="button secondary" disabled={busy || !rows.some((row) => row.state === 'failed')} onClick={() => void upload(rows.filter((row) => row.state === 'failed'))}>重试失败项</button></section>}</>}
      {(busy || remoteBusy) && <p className="helper-line" role="status">正在处理导入；请等待结果可核对后再关闭。</p>}
      {sourceTab === 'feishu' && <><FeishuPanel view="materials" showAuthorization={false} onImported={onImported} onMode={onMode} onAuthorizationChanged={onAuthorizationChanged} onBusyChange={setRemoteBusy} onClose={requestClose} /><p className="helper-line">需要授权时，可到设置里的连接向导处理。</p></>}
    </section>
  </div>
}
