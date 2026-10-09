import { useState } from 'react'
import { api, newOperationId, type Page } from '../api/client'

type Props = { page: Page; onClose: () => void; onReload: () => Promise<void> }

export function PageReader({ page, onClose, onReload }: Props) {
  const [title, setTitle] = useState(String(page.metadata.title ?? ''))
  const [body, setBody] = useState(page.body)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const needsConfirmation = page.approval_state !== 'confirmed'

  async function confirmCurrentVersion() {
    setBusy(true)
    setError('')
    try {
      await api.post('/pages/' + page.page_id + '/confirmations', {
        metadata: { ...page.metadata, title },
        body,
        confirmation_id: newOperationId(),
        operation_id: newOperationId(),
        expected_base_sha256: page.content_sha256,
      })
      await onReload()
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法确认此页面'
      setError(message.includes('changed since it was reviewed')
        ? '页面确认期间又发生了变化。请重新读取当前正文，检查后再确认。'
        : message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="page-reader">
      <button className="back-link" onClick={onClose}>← 返回目录</button>
      <div className="page-meta">
        <span className={needsConfirmation ? 'page-status-invalid' : ''}>{needsConfirmation ? '待确认' : '已确认知识'}</span>
        <span>{page.relative_path}</span>
      </div>
      <h1>{needsConfirmation ? '检查页面当前版本' : String(page.metadata.title ?? '未命名页面')}</h1>
      {needsConfirmation ? (
        <section className="page-reconfirmation" aria-label="重新确认当前页面">
          <p role="status">此页面自上次确认后已有变化，目前不会用于知识问答。请核对当前正文；只有点击确认后，新版本才会恢复检索资格。</p>
          {error && <p role="alert" className="form-error">{error}</p>}
          {error && <button className="text-button" onClick={() => void onReload()}>重新读取当前版本</button>}
          <label className="field"><span>页面标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <label className="field"><span>页面正文</span><textarea aria-label="页面正文" rows={18} value={body} onChange={(event) => setBody(event.target.value)} /></label>
          <div className="button-row">
            <button className="button primary" disabled={busy || !title.trim() || !body.trim()} onClick={() => void confirmCurrentVersion()}>
              {busy ? '正在确认…' : '确认当前版本'}
            </button>
          </div>
        </section>
      ) : <pre className="page-body">{page.body}</pre>}
    </article>
  )
}
