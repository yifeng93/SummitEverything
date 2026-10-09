import { useEffect, useState, type FormEvent } from 'react'
import { api, type Workspace } from '../api/client'
import { newOperationId } from '../api/client'

declare global {
  interface Window {
    webkit?: { messageHandlers?: { selectWorkspaceFolder?: { postMessage: (body: null) => void } } }
  }
}

export function WorkspaceGate({ onOpened }: { onOpened: (workspace: Workspace) => void }) {
  const [root, setRoot] = useState('')
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'create' | 'open'>('create')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

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
      }))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法打开工作库')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="setup-screen">
      <div className="setup-card">
        <div className="brand setup-brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <div><strong>SummitEverything</strong><span>本地知识工作台</span></div>
        </div>
        <p className="eyebrow">先连接一个工作库</p>
        <h1>让工作资料成为<br />自己的知识。</h1>
        <p className="lede">工作库保存在你选择的本机文件夹。试用时请使用隔离的模拟资料。</p>
        <form onSubmit={submit} className="setup-form">
          <fieldset className="mode-switch">
            <legend>工作库操作</legend>
            <label><input type="radio" checked={mode === 'create'} onChange={() => setMode('create')} /> 新建</label>
            <label><input type="radio" checked={mode === 'open'} onChange={() => setMode('open')} /> 打开已有</label>
          </fieldset>
          {mode === 'create' && (
            <div className="field">
              <label htmlFor="workspace-name">工作库名称</label>
              <input id="workspace-name" required value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：个人模拟库" />
            </div>
          )}
          <div className="field">
            <label htmlFor="workspace-path">文件夹路径</label>
            <input id="workspace-path" required value={root} onChange={(event) => setRoot(event.target.value)} placeholder="/Users/you/Documents/MyKnowledge" />
            <small id="workspace-path-help">在开发预览中输入完整本机路径。</small>
            {window.webkit?.messageHandlers?.selectWorkspaceFolder && (
              <button className="button secondary" type="button" onClick={chooseFolder}>选择文件夹…</button>
            )}
          </div>
          {error && <p role="alert" className="form-error">{error}</p>}
          <button className="button primary wide" disabled={busy}>
            {busy ? '正在连接…' : mode === 'create' ? '创建本地工作库' : '打开工作库'}
          </button>
        </form>
        <div className="privacy-note"><span aria-hidden="true">●</span> 内容仅写入本机；导入材料不会自动成为正式知识。</div>
      </div>
    </main>
  )
}
