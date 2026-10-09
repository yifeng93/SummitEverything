import { useEffect, useState } from 'react'
import { api, type Page, type Workspace } from './api/client'
import { AskView } from './components/AskView'
import { ProjectsView } from './components/ProjectsView'
import { PageReader } from './components/PageReader'
import { TodayView } from './components/TodayView'
import { WorkspaceGate } from './components/WorkspaceGate'
import './App.css'

type Section = 'today' | 'projects' | 'ask' | 'settings'
const sections: { id: Section; label: string }[] = [
  { id: 'today', label: '今日' },
  { id: 'projects', label: '项目与知识' },
  { id: 'ask', label: '知识问答' },
  { id: 'settings', label: '设置' },
]

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [section, setSection] = useState<Section>('today')
  const [page, setPage] = useState<Page | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Workspace>('/workspaces/current').then(setWorkspace).catch(() => undefined)
  }, [])

  async function openPage(pageId: string, expectedHash?: string) {
    try {
      const query = expectedHash ? '?expected_content_sha256=' + expectedHash : ''
      setPage(await api.get<Page>('/pages/' + pageId + query))
      setError('')
    } catch (cause) {
      setPage(null)
      setError(cause instanceof Error ? cause.message : '无法打开页面')
    }
  }

  if (!workspace) return <WorkspaceGate onOpened={setWorkspace} />

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <div><strong>SummitEverything</strong><span>个人知识工作台</span></div>
        </div>
        <nav aria-label="主导航" className="primary-nav">
          {sections.map((item) => (
            <button
              className={section === item.id ? 'nav-item active' : 'nav-item'}
              key={item.id}
              onClick={() => { setPage(null); setSection(item.id) }}
            >
              <span className={'nav-symbol nav-' + item.id} aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-indicator"><span />仅本机运行</div>
          <button className="workspace-name" onClick={() => setWorkspace(null)}>
            <span className="workspace-avatar">{workspace.name.slice(0, 1)}</span>
            <span className="workspace-name-text"><strong>{workspace.name}</strong><small>已连接工作库</small></span>
            <span aria-hidden="true">⌄</span>
          </button>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>{sections.find((item) => item.id === section)?.label ?? '今日'}</span>
            {page && <><span className="crumb-separator">/</span><span>{String(page.metadata.title ?? '页面')}</span></>}
          </div>
          <div className="topbar-right">
            <span className="save-state"><span />本机已保存</span>
            <button className="avatar-button" aria-label="打开设置" onClick={() => setSection('settings')}>罗</button>
          </div>
        </header>
        {error && <div role="alert" className="global-alert">{error}</div>}
        {page ? (
          <PageReader
            key={`${page.page_id}:${page.content_sha256}`}
            page={page}
            onClose={() => setPage(null)}
            onReload={() => openPage(page.page_id)}
          />
        ) : section === 'today' ? (
          <TodayView onError={setError} />
        ) : section === 'projects' ? (
          <ProjectsView onError={setError} onOpenPage={openPage} />
        ) : section === 'ask' ? (
          <AskView onError={setError} onOpenPage={openPage} />
        ) : (
          <section className="content-wrap settings-view">
            <div className="eyebrow">工作库偏好</div>
            <h1>设置</h1>
            <p className="lede">当前会话与索引保存在本机。首版使用模拟整理与检索服务。</p>
            <div className="settings-list">
              <div><span>工作库</span><strong>{workspace.name}</strong></div>
              <div><span>运行方式</span><strong>本机 API + WebUI</strong></div>
              <div><span>整理模型</span><strong>FakeLLM · 不会调用外部模型</strong></div>
              <div><span>飞书连接</span><strong>尚未配置</strong></div>
            </div>
            <button className="button secondary" onClick={() => setWorkspace(null)}>切换工作库</button>
          </section>
        )}
      </main>
    </div>
  )
}
