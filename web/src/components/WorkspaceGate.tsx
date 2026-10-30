import { useEffect, useState, type FormEvent } from 'react'
import { api, type Workspace } from '../api/client'
import { newOperationId } from '../api/client'

declare global {
  interface Window {
    webkit?: { messageHandlers?: { selectWorkspaceFolder?: { postMessage: (body: null) => void } } }
  }
}

/**
 * 第一步只有一个任务：新建或打开一个本机文件夹。
 *
 * `mode` 仍然随结果上抛，因为「新建」是首次使用、「打开已有」是回到旧库，
 * 两者的落点不同（QA D-1）。界面只保留模式、名称、路径和主按钮。
 */
export function WorkspaceGate({ onOpened }: { onOpened: (workspace: Workspace, mode: 'create' | 'open') => void }) {
  const [root, setRoot] = useState('')
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'create' | 'open'>('create')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const canPickFolder = Boolean(window.webkit?.messageHandlers?.selectWorkspaceFolder)

  useEffect(() => {
    function receiveFolder(event: Event) {
      const path = (event as CustomEvent<string>).detail
      if (typeof path === 'string') setRoot(path)
    }
    window.addEventListener('workspace-folder-selected', receiveFolder)
    return () => window.removeEventListener('workspace-folder-selected', receiveFolder)
  }, [])

  function chooseFolder() {
    window.webkit?.messageHandlers?.selectWorkspaceFolder?.postMessage(null)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      onOpened(await api.post<Workspace>('/workspaces', {
        root,
        mode,
        name: mode === 'create' ? name : undefined,
        operation_id: newOperationId(),
      }), mode)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : mode === 'create' ? '工作库没有创建成功。' : '工作库没有打开。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="setup-screen">
      <div className="setup-card">
        <div className="setup-brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <strong>SummitEverything</strong>
        </div>

        <h1>{mode === 'create' ? '新建工作库' : '打开工作库'}</h1>

        <form onSubmit={submit} className="setup-form">
          <fieldset className="setup-modes">
            <legend className="sr-only">工作库操作</legend>
            <label className={mode === 'create' ? 'active' : ''}>
              <input type="radio" name="workspace-mode" checked={mode === 'create'} onChange={() => { setMode('create'); setError('') }} />
              <span>新建</span>
            </label>
            <label className={mode === 'open' ? 'active' : ''}>
              <input type="radio" name="workspace-mode" checked={mode === 'open'} onChange={() => { setMode('open'); setError('') }} />
              <span>打开已有</span>
            </label>
          </fieldset>

          {mode === 'create' && (
            <div className="setup-field">
              <label htmlFor="workspace-name">工作库名称</label>
              <input id="workspace-name" required autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：我的工作库" />
            </div>
          )}

          <div className="setup-field">
            <label htmlFor="workspace-path">文件夹路径</label>
            <div className="setup-path">
              <input id="workspace-path" required autoFocus={mode === 'open'} value={root} onChange={(event) => setRoot(event.target.value)} placeholder="/Users/you/Documents/Knowledge" />
              {canPickFolder && <button className="button secondary" type="button" onClick={chooseFolder}>选择…</button>}
            </div>
          </div>

          {error && <p role="alert" className="form-error">{error}</p>}

          <button className="button primary wide" disabled={busy}>
            {busy ? '正在打开…' : mode === 'create' ? '创建本地工作库' : '打开工作库'}
          </button>
        </form>
      </div>
    </main>
  )
}
